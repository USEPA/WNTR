import wntr.sim.hydraulics
from wntr.sim.solvers import NewtonSolver, SolverStatus
import wntr.sim.results
from wntr.network.controls import ControlManager, _ControlType
import numpy as np
import warnings
import time
import sys
import logging
import scipy.optimize
import scipy.sparse
import scipy.sparse.csr
import itertools
from collections import OrderedDict
from wntr.utils.ordered_set import OrderedSet
from wntr.network import Junction, Pipe, Valve, Pump, Tank, Reservoir
from wntr.sim.network_isolation import check_for_isolated_junctions

logger = logging.getLogger(__name__)


# TODO: allow user to turn of demand status and leak model status controls
# TODO: allow user to switch between wntr and ipopt models


class WaterNetworkSimulator(object):
    """
    Base water network simulator class.

    wn : WaterNetworkModel object
        Water network model

    mode: string (optional)
        Specifies whether the simulation will be demand-driven (DD) or
        pressure dependent demand (PDD), default = DD
    """

    def __init__(self, wn=None, mode='DD'):

        self._wn = wn
        self.mode = mode

    def _get_link_type(self, name):
        if isinstance(self._wn.get_link(name), Pipe):
            return 'pipe'
        elif isinstance(self._wn.get_link(name), Valve):
            return 'valve'
        elif isinstance(self._wn.get_link(name), Pump):
            return 'pump'
        else:
            raise RuntimeError('Link name ' + name + ' was not recognised as a pipe, valve, or pump.')

    def _get_node_type(self, name):
        if isinstance(self._wn.get_node(name), Junction):
            return 'junction'
        elif isinstance(self._wn.get_node(name), Tank):
            return 'tank'
        elif isinstance(self._wn.get_node(name), Reservoir):
            return 'reservoir'
        else:
            raise RuntimeError('Node name ' + name + ' was not recognised as a junction, tank, reservoir, or leak.')


def _get_control_managers(wn, pdd=False):
    """

    Parameters
    ----------
    wn: wntr.network.WaterNetworkModel
    pdd: bool

    Returns
    -------
    managers: tuple of wntr.network.ControlManager
    """
    presolve_controls = ControlManager()
    postsolve_controls = ControlManager()
    rules = ControlManager()

    def categorize_control(control):
        """

        Parameters
        ----------
        control: wntr.network.Control or wntr.network.Rule

        Returns
        -------

        """
        if control.epanet_control_type in {_ControlType.presolve, _ControlType.pre_and_postsolve}:
            presolve_controls.register_control(control)
        if control.epanet_control_type in {_ControlType.postsolve, _ControlType.pre_and_postsolve}:
            postsolve_controls.register_control(control)
        if control.epanet_control_type == _ControlType.rule:
            rules.register_control(control)

    for c_name, c in wn.controls():
        categorize_control(c)
    for c in wn._get_all_tank_controls():
        categorize_control(c)
    for c in wn._get_cv_controls():
        categorize_control(c)
    for c in wn._get_pump_controls():
        categorize_control(c)
    for c in wn._get_valve_controls():
        categorize_control(c)
    #if pdd:
    #    for c in wn._get_demand_status_controls():
    #        categorize_control(c)
    #for c in wn._get_leak_model_status_controls():
    #    categorize_control(c)

    return presolve_controls, postsolve_controls, rules


class WNTRSimulator(WaterNetworkSimulator):
    """
    WNTR simulator class.
    The WNTR simulator uses a custom newton solver and linear solvers from scipy.sparse.

    Parameters
    ----------
    wn : WaterNetworkModel object
        Water network model

    mode: string (optional)
        Specifies whether the simulation will be demand-driven (DD) or
        pressure dependent demand (PDD), default = DD
    """

    def __init__(self, wn, mode='DD'):

        super(WNTRSimulator, self).__init__(wn, mode)
        self._internal_graph = None
        self._node_pairs_with_multiple_links = None
        self._presolve_controls = ControlManager()
        self._rules = ControlManager()
        self._postsolve_controls = ControlManager()
        self._time_per_step = []
        self._solver = None
        self._model = None
        self._link_name_to_id = OrderedDict()
        self._link_id_to_name = OrderedDict()
        self._node_name_to_id = OrderedDict()
        self._node_id_to_name = OrderedDict()
        self._prev_isolated_junctions = OrderedSet()
        self._prev_isolated_links = OrderedSet()
        self._model_updater = None
        self._source_ids = None

        self._initialize_name_id_maps()
        self._initialize_internal_graph()

    def _get_time(self):
        s = int(self._wn.sim_time)
        h = int(s/3600)
        s -= h*3600
        m = int(s/60)
        s -= m*60
        s = int(s)
        return str(h)+':'+str(m)+':'+str(s)

    def run_sim(self, solver=NewtonSolver, backup_solver=None, solver_options=None,
                backup_solver_options=None, convergence_error=True):
        """
        Run an extended period simulation (hydraulics only).

        Parameters
        ----------
        solver: object
            wntr.sim.solvers.NewtonSolver or Scipy solver
        backup_solver: object
            wntr.sim.solvers.NewtonSolver or Scipy solver
        solver_options: dict
            Solver options are specified using the following dictionary keys:

            * MAXITER: the maximum number of iterations for each hydraulic solve (each timestep and trial) (default = 100)
            * TOL: tolerance for the hydraulic equations (default = 1e-6)
            * BT_RHO: the fraction by which the step length is reduced at each iteration of the line search (default = 0.5)
            * BT_MAXITER: the maximum number of iterations for each line search (default = 20)
            * BACKTRACKING: whether or not to use a line search (default = True)
            * BT_START_ITER: the newton iteration at which a line search should start being used (default = 2)
            * THREADS: the number of threads to use in constraint and jacobian computations
        backup_solver_options: dict
        convergence_error: bool (optional)
            If convergence_error is True, an error will be raised if the
            simulation does not converge. If convergence_error is False,
            a warning will be issued and results.error_code will be set to 2
            if the simulation does not converge.  Default = True.
        """
        if solver_options is None:
            solver_options = {}
        if backup_solver_options is None:
            backup_solver_options = {}

        logger_level = logger.getEffectiveLevel()

        if logger_level <= 1:
            logger.log(1, 'beginning of run_sim')

        report_timestep = self._wn.options.time.report_timestep
        hydraulic_timestep = self._wn.options.time.hydraulic_timestep
        if type(report_timestep) is str:
            if report_timestep.upper() != 'ALL':
                raise ValueError('report timestep must be either an integer number of seconds or "ALL".')
        else:
            if report_timestep < hydraulic_timestep:
                msg = 'The report timestep must be an integer multiple of the hydraulic timestep. Reducing the hydraulic timestep from {0} seconds to {1} seconds for this simulation.'.format(hydraulic_timestep, report_timestep)
                logger.warning(msg)
                warnings.warn(msg)
                hydraulic_timestep = report_timestep
            elif report_timestep%hydraulic_timestep != 0:
                new_report = report_timestep - (report_timestep%hydraulic_timestep)
                msg = 'The report timestep must be an integer multiple of the hydraulic timestep. Reducing the report timestep from {0} seconds to {1} seconds for this simulation.'.format(report_timestep, new_report)
                logger.warning(msg)
                warnings.warn(msg)
                report_timestep = new_report

        orig_report_timestep = self._wn.options.time.report_timestep
        orig_hydraulic_timestep = self._wn.options.time.hydraulic_timestep

        self._wn.options.time.report_timestep = report_timestep
        self._wn.options.time.hydraulic_timestep = hydraulic_timestep

        self._time_per_step = []

        wn = self._wn

        self._presolve_controls, self._postsolve_controls, self._rules = _get_control_managers(wn, pdd=(self.mode == 'PDD'))

        if logger_level <= 1:
            logger.log(1, 'collected presolve controls:')
            for c in self._presolve_controls:
                logger.log(1, '\t' + str(c))
            logger.log(1, 'collected rules:')
            for c in self._rules:
                logger.log(1, '\t' + str(c))
            logger.log(1, 'collected postsolve controls:')
            for c in self._postsolve_controls:
                logger.log(1, '\t' + str(c))

            logger.log(1, 'initializing hydraulic model')

        model, model_updater = wntr.sim.hydraulics.create_hydraulic_model(wn=wn, mode=self.mode)
        self._model = model
        self._model_updater = model_updater
        node_res, link_res = wntr.sim.hydraulics.initialize_results_dict(wn)

        results = wntr.sim.results.SimulationResults()
        results.error_code = None
        results.time = []
        results.network_name = wn.name

        self._initialize_internal_graph()

        if self._wn.sim_time == 0:
            first_step = True
        else:
            first_step = False
        trial = -1
        max_trials = self._wn.options.solver.trials
        resolve = False
        rule_iter = 0  # this is used to determine the rule timestep

        if first_step:
            wntr.sim.hydraulics.update_network_previous_values(wn)
            self._wn._prev_sim_time = -1

        if logger_level <= 1:
            logger.log(1, 'starting simulation')

        if solver is scipy.optimize.fsolve:
            solver_options.pop('fprime', False)
            solver_options['full_output'] = True
            use_jac = solver_options.pop('use_jac', False)
            if use_jac:
                dense_jac = _DenseJac(model)
                solver_options['fprime'] = dense_jac.eval

        if backup_solver is scipy.optimize.fsolve:
            backup_solver_options.pop('fprime', False)
            backup_solver_options['full_output'] = True
            use_jac = backup_solver_options.pop('use_jac', False)
            if use_jac:
                dense_jac = _DenseJac(model)
                backup_solver_options['fprime'] = dense_jac.eval

        while True:
            if logger_level <= logging.DEBUG:
                logger.debug('\n\n')

            if not resolve:
                """
                Within this if statement:
                    1) Determine the next time step. This depends on both presolve controls and rules. Note that 
                       (unless this is the first time step) the current value of wn.sim_time is the next hydraulic 
                       timestep. If there are presolve controls or rules that need activated before the next hydraulic
                       timestep, then the wn.sim_time will be adjusted within this if statement.
                       
                        a) check the presolve controls to see which ones need activated.
                        b) if there is a presolve control(s) that need activated and it needs activated at a time
                           that is earlier than the next rule timestep, then the next simulation time is determined
                           by that presolve controls
                        c) if there are any rules that need activated before the next hydraulic timestep, then 
                           wn.sim_time will be adjusted to the appropriate rule timestep.
                    2) Activate the appropriate controls
                """
                start_step_time = time.time()  # this is just for timing

                if not first_step:
                    """
                    The tank levels/heads must be done before checking the controls because the TankLevelControls
                    depend on the tank levels. These will be updated again after we determine the next actual timestep.
                    """
                    wntr.sim.hydraulics.update_tank_heads(wn)
                trial = 0

                self._presolve_controls.reset()
                self._rules.reset()

                # check which presolve controls need to be activated before the next hydraulic timestep
                presolve_controls_to_run = self._presolve_controls.check()
                presolve_controls_to_run.sort(key=lambda i: i[0]._priority)  # sort them by priority
                # now sort them from largest to smallest "backtrack"; this way they are in the time-order
                # in which they need to be activated
                presolve_controls_to_run.sort(key=lambda i: i[1], reverse=True)
                if first_step:  # we don't want to backtrack if the sim time is 0
                    presolve_controls_to_run = [(c, 0) for c, b in presolve_controls_to_run]
                if logger_level <= 1:
                    logger.log(1, 'presolve_controls that need activated before the next hydraulic timestep:')
                    for pctr in presolve_controls_to_run:
                        logger.log(1, '\tcontrol: {0} \tbacktrack: {1}'.format(pctr[0], pctr[1]))
                cnt = 0

                # loop until we have checked all of the presolve_controls_to_run and all of the rules prior to the next
                # hydraulic timestep
                while cnt < len(presolve_controls_to_run) or rule_iter * self._wn.options.time.rule_timestep <= self._wn.sim_time:
                    if cnt >= len(presolve_controls_to_run):
                        # We have already checked all of the presolve_controls_to_run, and nothing changed
                        # Now we just need to check the rules
                        if logger_level <= 1:
                            logger.log(1, 'no presolve controls need activated; checking rules at rule timestep {0}'.format(rule_iter * self._wn.options.time.rule_timestep))
                        old_time = self._wn.sim_time
                        self._wn.sim_time = rule_iter * self._wn.options.time.rule_timestep
                        if not first_step:
                            wntr.sim.hydraulics.update_tank_heads(wn)
                        rule_iter += 1
                        rules_to_run = self._rules.check()
                        rules_to_run.sort(key=lambda i: i[0]._priority)
                        for rule, rule_back in rules_to_run:  # rule_back is the "backtrack" which is not actually used for rules
                            if logger_level <= 1:
                                logger.log(1, '\tactivating rule {0}'.format(rule))
                            rule.run_control_action()
                        if self._rules.changes_made():
                            # If changes were made, then we found the next timestep; break
                            break
                        # if no changes were made, then set the wn.sim_time back
                        if logger_level <= 1:
                            logger.log(1, 'no changes made by rules at rule timestep {0}'.format((rule_iter - 1) * self._wn.options.time.rule_timestep))
                        self._wn.sim_time = old_time
                    else:
                        # check the next presolve control in presolve_controls_to_run
                        control, backtrack = presolve_controls_to_run[cnt]
                        if logger_level <= 1:
                            logger.log(1, 'checking control {0}; backtrack: {1}'.format(control, backtrack))
                        if self._wn.sim_time - backtrack < rule_iter * self._wn.options.time.rule_timestep:
                            # The control needs activated before the next rule timestep; Activate the control and
                            # any controls with the samve value for backtrack
                            if logger_level <= 1:
                                logger.log(1, 'control {0} needs run before the next rule timestep.'.format(control))
                            control.run_control_action()
                            cnt += 1
                            while cnt < len(presolve_controls_to_run) and presolve_controls_to_run[cnt][1] == backtrack:
                                # Also activate all of the controls that have the same value for backtrack
                                if logger_level <= 1:
                                    logger.log(1, '\talso activating control {0}; backtrack: {1}'.format(presolve_controls_to_run[cnt][0],
                                                                                                   presolve_controls_to_run[cnt][1]))
                                presolve_controls_to_run[cnt][0].run_control_action()
                                cnt += 1
                            if self._presolve_controls.changes_made():
                                # changes were actually made; we found the next timestep; update wn.sim_time and break
                                self._wn.sim_time -= backtrack
                                break
                            if logger_level <= 1:
                                logger.log(1, 'controls with backtrack {0} did not make any changes'.format(backtrack))
                        elif self._wn.sim_time - backtrack == rule_iter * self._wn.options.time.rule_timestep:
                            # the control needs activated at the same time as the next rule timestep;
                            # activate the control, any controls with the same value for backtrack, and any rules at
                            # this rule timestep
                            # the rules need run first (I think to match epanet)
                            if logger_level <= 1:
                                logger.log(1, 'control has backtrack equivalent to next rule timestep')
                            rule_iter += 1
                            self._wn.sim_time -= backtrack
                            if not first_step:
                                wntr.sim.hydraulics.update_tank_heads(wn)
                            rules_to_run = self._rules.check()
                            rules_to_run.sort(key=lambda i: i[0]._priority)
                            for rule, rule_back in rules_to_run:
                                if logger_level <= 1:
                                    logger.log(1, '\tactivating rule {0}'.format(rule))
                                rule.run_control_action()
                            if logger_level <= 1:
                                logger.log(1, '\tactivating control {0}; backtrack: {1}'.format(control, backtrack))
                            control.run_control_action()
                            cnt += 1
                            while cnt < len(presolve_controls_to_run) and presolve_controls_to_run[cnt][1] == backtrack:
                                if logger_level <= 1:
                                    logger.log(1, '\talso activating control {0}; backtrack: {1}'.format(presolve_controls_to_run[cnt][0], presolve_controls_to_run[cnt][1]))
                                presolve_controls_to_run[cnt][0].run_control_action()
                                cnt += 1
                            if self._presolve_controls.changes_made() or self._rules.changes_made():
                                break
                            if logger_level <= 1:
                                logger.log(1, 'no changes made by presolve controls or rules at backtrack {0}'.format(backtrack))
                            self._wn.sim_time += backtrack
                        else:
                            if logger_level <= 1:
                                logger.log(1, 'The next rule timestep is before this control needs activated; checking rules')
                            old_time = self._wn.sim_time
                            self._wn.sim_time = rule_iter * self._wn.options.time.rule_timestep
                            rule_iter += 1
                            if not first_step:
                                wntr.sim.hydraulics.update_tank_heads(wn)
                            rules_to_run = self._rules.check()
                            rules_to_run.sort(key=lambda i: i[0]._priority)
                            for rule, rule_back in rules_to_run:
                                if logger_level <= 1:
                                    logger.log(1, '\tactivating rule {0}'.format(rule))
                                rule.run_control_action()
                            if self._rules.changes_made():
                                break
                            if logger_level <= 1:
                                logger.log(1, 'no changes made by rules at rule timestep {0}'.format((rule_iter - 1) * self._wn.options.time.rule_timestep))
                            self._wn.sim_time = old_time
                if logger_level <= logging.DEBUG:
                    logger.debug('changes made by rules: ')
                    for obj, attr in self._rules.get_changes():
                        logger.debug('\t{0}.{1} changed to {2}'.format(obj, attr, getattr(obj, attr)))
                    logger.debug('changes made by presolve controls:')
                    for obj, attr in self._presolve_controls.get_changes():
                        logger.debug('\t{0}.{1} changed to {2}'.format(obj, attr, getattr(obj, attr)))

            logger.info('simulation time = %s, trial = %d', self._get_time(), trial)

            # Prepare for solve
            self._update_internal_graph()
            self._get_isolated_junctions_and_links()
            if not first_step and not resolve:
                wntr.sim.hydraulics.update_tank_heads(wn)
            wntr.sim.hydraulics.update_model_for_controls(model, wn, model_updater, self._presolve_controls)
            wntr.sim.hydraulics.update_model_for_controls(model, wn, model_updater, self._rules)
            wntr.models.param.source_head_param(model, wn)
            wntr.models.param.expected_demand_param(model, wn)

            # Solve
            solver_status, mesg = _solver_helper(model, solver, solver_options)
            if solver_status == 0 and backup_solver is not None:
                solver_status, mesg = _solver_helper(model, backup_solver, backup_solver_options)
            if solver_status == 0:
                if convergence_error:
                    logger.error('Simulation did not converge. ' + mesg)
                    raise RuntimeError('Simulation did not converge. ' + mesg)
                warnings.warn('Simulation did not converge. ' + mesg)
                logger.warning('Simulation did not converge at time ' + str(self._get_time()) + '. ' + mesg)
                wntr.sim.hydraulics.get_results(wn, results, node_res, link_res)
                results.error_code = wntr.sim.results.ResultsStatus.error
                break

            # Enter results in network and update previous inputs
            logger.debug('storing results in network')
            wntr.sim.hydraulics.store_results_in_network(wn, model, mode=self.mode)

            logger.debug('checking postsolve controls')
            self._postsolve_controls.reset()
            postsolve_controls_to_run = self._postsolve_controls.check()
            postsolve_controls_to_run.sort(key=lambda i: i[0]._priority)
            for control, unused in postsolve_controls_to_run:
                if logger_level <= 1:
                    logger.log(1, '\tactivating control {0}'.format(control))
                control.run_control_action()
            if self._postsolve_controls.changes_made():
                if logger_level <= logging.DEBUG:
                    logger.debug('postsolve controls made changes:')
                    for obj, attr in self._postsolve_controls.get_changes():
                        logger.debug('\t{0}.{1} changed to {2}'.format(obj, attr, getattr(obj, attr)))
                resolve = True
                self._update_internal_graph()
                wntr.sim.hydraulics.update_model_for_controls(model, wn, model_updater, self._postsolve_controls)
                self._postsolve_controls.reset()
                trial += 1
                if trial > max_trials:
                    if convergence_error:
                        logger.error('Exceeded maximum number of trials.')
                        raise RuntimeError('Exceeded maximum number of trials.')
                    results.error_code = wntr.sim.results.ResultsStatus.error
                    warnings.warn('Exceeded maximum number of trials.')
                    logger.warning('Exceeded maximum number of trials at time %s', self._get_time())
                    break
                continue

            logger.debug('no changes made by postsolve controls; moving to next timestep')

            resolve = False
            if type(self._wn.options.time.report_timestep) == float or type(self._wn.options.time.report_timestep) == int:
                if self._wn.sim_time % self._wn.options.time.report_timestep == 0:
                    wntr.sim.hydraulics.save_results(wn, node_res, link_res)
                    if len(results.time) > 0 and int(self._wn.sim_time) == results.time[-1]:
                        raise RuntimeError('Simulation already solved this timestep')
                    results.time.append(int(self._wn.sim_time))
            elif self._wn.options.time.report_timestep.upper() == 'ALL':
                wntr.sim.hydraulics.save_results(wn, node_res, link_res)
                if len(results.time) > 0 and int(self._wn.sim_time) == results.time[-1]:
                    raise RuntimeError('Simulation already solved this timestep')
                results.time.append(int(self._wn.sim_time))
            wntr.sim.hydraulics.update_network_previous_values(wn)
            first_step = False
            self._wn.sim_time += self._wn.options.time.hydraulic_timestep
            overstep = float(self._wn.sim_time) % self._wn.options.time.hydraulic_timestep
            self._wn.sim_time -= overstep

            if self._wn.sim_time > self._wn.options.time.duration:
                break

            self._time_per_step.append(time.time()-start_step_time)

        wntr.sim.hydraulics.get_results(wn, results, node_res, link_res)
        self._wn.options.time.report_timestep = orig_report_timestep
        self._wn.options.time.hydraulic_timestep = orig_hydraulic_timestep
        return results

    def _initialize_name_id_maps(self):
        n = 0
        for link_name, link in self._wn.links():
            self._link_name_to_id[link_name] = n
            self._link_id_to_name[n] = link_name
            n += 1
        n = 0
        for node_name, node in self._wn.nodes():
            self._node_name_to_id[node_name] = n
            self._node_id_to_name[n] = node_name
            n += 1

    def _initialize_internal_graph(self):
        n_links = OrderedDict()
        rows = []
        cols = []
        vals = []
        for link_name, link in itertools.chain(self._wn.pipes(), self._wn.pumps(), self._wn.valves()):
            from_node_name = link.start_node_name
            to_node_name = link.end_node_name
            from_node_id = self._node_name_to_id[from_node_name]
            to_node_id = self._node_name_to_id[to_node_name]
            if (from_node_id, to_node_id) not in n_links:
                n_links[(from_node_id, to_node_id)] = 0
                n_links[(to_node_id, from_node_id)] = 0
            n_links[(from_node_id, to_node_id)] += 1
            n_links[(to_node_id, from_node_id)] += 1
            rows.append(from_node_id)
            cols.append(to_node_id)
            rows.append(to_node_id)
            cols.append(from_node_id)
            if link.status == wntr.network.LinkStatus.closed:
                vals.append(0)
                vals.append(0)
            else:
                vals.append(1)
                vals.append(1)

        self._internal_graph = scipy.sparse.csr_matrix((vals, (rows, cols)))

        ndx_map = OrderedDict()
        for link_name, link in self._wn.links():
            from_node_name = link.start_node_name
            to_node_name = link.end_node_name
            from_node_id = self._node_name_to_id[from_node_name]
            to_node_id = self._node_name_to_id[to_node_name]
            ndx1 = _get_csr_data_index(self._internal_graph, from_node_id, to_node_id)
            ndx2 = _get_csr_data_index(self._internal_graph, to_node_id, from_node_id)
            ndx_map[link] = (ndx1, ndx2)
        self._map_link_to_internal_graph_data_ndx = ndx_map

        self._number_of_connections = [0 for i in range(self._wn.num_nodes)]
        for node_id in self._node_id_to_name.keys():
            self._number_of_connections[node_id] = self._internal_graph.indptr[node_id+1] - self._internal_graph.indptr[node_id]
        self._number_of_connections = np.array(self._number_of_connections, dtype=np.int64)

        self._node_pairs_with_multiple_links = OrderedDict()
        for from_node_id, to_node_id in n_links.keys():
            if n_links[(from_node_id, to_node_id)] > 1:
                if (to_node_id, from_node_id) in self._node_pairs_with_multiple_links:
                    continue
                self._internal_graph[from_node_id, to_node_id] = 0
                self._internal_graph[to_node_id, from_node_id] = 0
                from_node_name = self._node_id_to_name[from_node_id]
                to_node_name = self._node_id_to_name[to_node_id]
                tmp_list = self._node_pairs_with_multiple_links[(from_node_id, to_node_id)] = []
                for link_name in self._wn.get_links_for_node(from_node_name):
                    link = self._wn.get_link(link_name)
                    if link.start_node_name == to_node_name or link.end_node_name == to_node_name:
                        tmp_list.append(link)
                        if link.status != wntr.network.LinkStatus.closed:
                            ndx1, ndx2 = ndx_map[link]
                            self._internal_graph.data[ndx1] = 1
                            self._internal_graph.data[ndx2] = 1

        self._source_ids = []
        for node_name, node in self._wn.tanks():
            node_id = self._node_name_to_id[node_name]
            self._source_ids.append(node_id)
        for node_name, node in self._wn.reservoirs():
            node_id = self._node_name_to_id[node_name]
            self._source_ids.append(node_id)
        self._source_ids = np.array(self._source_ids, dtype=np.int64)

    def _update_internal_graph(self):
        data = self._internal_graph.data
        ndx_map = self._map_link_to_internal_graph_data_ndx
        for mgr in [self._presolve_controls, self._rules, self._postsolve_controls]:
            for obj, attr in mgr.get_changes():
                if 'status' == attr:
                    if obj.status == wntr.network.LinkStatus.closed:
                        ndx1, ndx2 = ndx_map[obj]
                        data[ndx1] = 0
                        data[ndx2] = 0
                    else:
                        ndx1, ndx2 = ndx_map[obj]
                        data[ndx1] = 1
                        data[ndx2] = 1

        for key, link_list in self._node_pairs_with_multiple_links.items():
            first_link = link_list[0]
            ndx1, ndx2 = ndx_map[first_link]
            data[ndx1] = 0
            data[ndx2] = 0
            for link in link_list:
                if link.status != wntr.network.LinkStatus.closed:
                    ndx1, ndx2 = ndx_map[link]
                    data[ndx1] = 1
                    data[ndx2] = 1

    def _get_isolated_junctions_and_links(self):
        logger_level = logger.getEffectiveLevel()

        if logger_level <= logging.DEBUG:
            logger.debug('checking for isolated junctions and links')
        for j in self._prev_isolated_junctions:
            junction = self._wn.get_node(j)
            junction._is_isolated = False
        for l in self._prev_isolated_links:
            link = self._wn.get_link(l)
            link._is_isolated = False

        node_indicator = np.ones(self._wn.num_nodes, dtype=np.int64)
        check_for_isolated_junctions(self._source_ids, node_indicator, self._internal_graph.indptr,
                                     self._internal_graph.indices, self._internal_graph.data,
                                     self._number_of_connections)

        isolated_junction_ids = [i for i in range(len(node_indicator)) if node_indicator[i] == 1]
        isolated_junctions = OrderedSet()
        isolated_links = OrderedSet()
        for j_id in isolated_junction_ids:
            j = self._node_id_to_name[j_id]
            junction = self._wn.get_node(j)
            junction._is_isolated = True
            isolated_junctions.add(j)
            connected_links = self._wn.get_links_for_node(j)
            for l in connected_links:
                link = self._wn.get_link(l)
                link._is_isolated = True
                isolated_links.add(l)

        logger.info('Number of isolated junctions: ' + str(len(isolated_junctions)))
        logger.info('Number of isolated links: ' + str(len(isolated_links)))
        if logger_level <= logging.DEBUG:
            if len(isolated_junctions) > 0 or len(isolated_links) > 0:
                logger.debug('isolated junctions: {0}'.format(isolated_junctions))
                logger.debug('isolated links: {0}'.format(isolated_links))
        wntr.sim.hydraulics.update_model_for_isolated_junctions_and_links(self._model, self._wn, self._model_updater,
                                                                          self._prev_isolated_junctions,
                                                                          self._prev_isolated_links,
                                                                          isolated_junctions, isolated_links)
        self._prev_isolated_junctions = isolated_junctions
        self._prev_isolated_links = isolated_links


def _get_csr_data_index(a, row, col):
    """
    Parameters:
    a: scipy.sparse.csr.csr_matrix
    row: int
    col: int
    """
    row_indptr = a.indptr[row]
    num = a.indptr[row+1] - row_indptr
    cols = a.indices[row_indptr:row_indptr+num]
    n = 0
    for j in cols:
        if j == col:
            return row_indptr + n
        n += 1
    raise RuntimeError('Unable to find csr data index.')


def _solver_helper(model, solver, solver_options):
    """

    Parameters
    ----------
    model: wntr.aml.Model
    solver: class or function
    solver_options: dict

    Returns
    -------
    solver_status: int
    message: str
    """
    logger.debug('solving')
    model.set_structure()
    if solver is NewtonSolver:
        _solver = NewtonSolver(solver_options)
        sol = _solver.solve(model)
    elif solver is scipy.optimize.fsolve:
        x, infodict, ier, mesg = solver(model.evaluate_residuals, model.get_x(), **solver_options)
        if ier != 1:
            sol = SolverStatus.error, mesg
        else:
            model.load_var_values_from_x(x)
            sol = SolverStatus.converged, mesg
    elif solver in {scipy.optimize.newton_krylov, scipy.optimize.anderson, scipy.optimize.broyden1,
                            scipy.optimize.broyden2, scipy.optimize.excitingmixing, scipy.optimize.linearmixing,
                            scipy.optimize.diagbroyden}:
        try:
            x = solver(model.evaluate_residuals, model.get_x(), **solver_options)
            model.load_var_values_from_x(x)
            sol = SolverStatus.converged, ''
        except:
            sol = SolverStatus.error, ''
    else:
        raise ValueError('Solver not recognized.')
    return sol


class _DenseJac(object):
    def __init__(self, model):
        self.model = model

    def eval(self, x):
        return self.model.get_jacobian(x).toarray()
