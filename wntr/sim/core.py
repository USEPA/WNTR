from wntr import *
from wntr.sim.hydraulics import *
from wntr.network.model import *
from wntr.sim.solvers import *
from wntr.sim.results import *
from wntr.network.model import *
from wntr.network.controls import ControlManager, _ControlType
import numpy as np
import warnings
import time
import sys
import logging
import scipy.sparse
import scipy.sparse.csr
import itertools

logger = logging.getLogger(__name__)


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

    def get_node_demand(self, node_name, start_time=None, end_time=None):
        """
        Calculates the demands at a node based on the demand pattern.

        Parameters
        ----------
        node_name : string
            Name of the node.
        start_time : float
            The start time of the demand values requested. Default is 0 sec.
        end_time : float
            The end time of the demand values requested. Default is the simulation end time in sec.

        Returns
        -------
        demand_list : list of floats
           A list of demand values at each hydraulic timestep.
        """

        # Set start and end time for demand values to be returned
        if start_time is None:
            start_time = 0
        if end_time is None:
            end_time = self._wn.options.time.duration

        # Get node object
        try:
            node = self._wn.get_node(node_name)
        except KeyError:
            raise KeyError("Not a valid node name")
        # Make sure node object is a Junction
        assert(isinstance(node, Junction)), "Demands can only be calculated for Junctions"
        # Calculate demand pattern values
        return node.demands.get_values(start_time, end_time, self._wn.options.time.hydraulic_timestep)

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
        elif isinstance(self._wn.get_node(name), Leak):
            return 'leak'
        else:
            raise RuntimeError('Node name ' + name + ' was not recognised as a junction, tank, reservoir, or leak.')


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

    def _get_time(self):
        s = int(self._wn.sim_time)
        h = int(s/3600)
        s -= h*3600
        m = int(s/60)
        s -= m*60
        s = int(s)
        return str(h)+':'+str(m)+':'+str(s)

    def run_sim(self, solver_options={}, convergence_error=True):
        """
        Run an extended period simulation (hydraulics only).

        Parameters
        ----------
        solver_options: dict
            Solver options are specified using the following dictionary keys:

            * MAXITER: the maximum number of iterations for each hydraulic solve (each timestep and trial) (default = 100)
            * TOL: tolerance for the hydraulic equations (default = 1e-6)
            * BT_RHO: the fraction by which the step length is reduced at each iteration of the line search (default = 0.5)
            * BT_MAXITER: the maximum number of iterations for each line search (default = 20)
            * BACKTRACKING: whether or not to use a line search (default = True)
            * BT_START_ITER: the newton iteration at which a line search should start being used (default = 2)

        convergence_error: bool (optional)
            If convergence_error is True, an error will be raised if the
            simulation does not converge. If convergence_error is False,
            a warning will be issued and results.error_code will be set to 2
            if the simulation does not converge.  Default = True.
        """
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

        self._presolve_controls = ControlManager()
        self._postsolve_controls = ControlManager()
        self._rules = ControlManager()

        def categorize_control(control):
            if control.epanet_control_type in {_ControlType.presolve, _ControlType.pre_and_postsolve}:
                self._presolve_controls.register_control(control)
            if control.epanet_control_type in {_ControlType.postsolve, _ControlType.pre_and_postsolve}:
                self._postsolve_controls.register_control(control)
            if control.epanet_control_type == _ControlType.rule:
                self._rules.register_control(control)

        for c_name, c in self._wn.controls():
            categorize_control(c)
        for c in (self._wn._get_all_tank_controls() + self._wn._get_cv_controls() + self._wn._get_pump_controls() +
                  self._wn._get_valve_controls()):
            categorize_control(c)

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

        model = HydraulicModel(self._wn, self.mode)
        self._model = model
        model.initialize_results_dict()

        self._solver = NewtonSolver(model.num_nodes, model.num_links, model.num_leaks, model, options=solver_options)

        results = SimulationResults()
        results.error_code = 0
        results.time = []
        results.network_name = model._wn.name

        # Initialize X
        # Vars will be ordered:
        #    1.) head
        #    2.) demand
        #    3.) flow
        #    4.) leak_demand
        model.set_network_inputs_by_id()
        head0 = model.initialize_head()
        demand0 = model.initialize_demand()
        flow0 = model.initialize_flow()
        leak_demand0 = model.initialize_leak_demand()

        X_init = np.concatenate((head0, demand0, flow0, leak_demand0))

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
            self._model.update_network_previous_values()
            self._wn._prev_sim_time = -1

        if logger_level <= 1:
            logger.log(1, 'starting simulation')

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
                    self._model.update_tank_heads()
                trial = 0

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
                            self._model.update_tank_heads()
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
                                self._model.update_tank_heads()
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
                                self._model.update_tank_heads()
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
                self._update_internal_graph()
                if logger_level <= logging.DEBUG:
                    logger.debug('changes made by rules: ')
                    for obj, attr in self._rules.get_changes():
                        logger.debug('\t{0}.{1} changed to {2}'.format(obj, attr, getattr(obj, attr)))
                    logger.debug('changes made by presolve controls:')
                    for obj, attr in self._presolve_controls.get_changes():
                        logger.debug('\t{0}.{1} changed to {2}'.format(obj, attr, getattr(obj, attr)))
                self._presolve_controls.reset()
                self._rules.reset()

            logger.info('simulation time = %s, trial = %d', self._get_time(), trial)

            # Prepare for solve
            if logger_level <= logging.DEBUG:
                logger.debug('checking for isolated junctions and links')
            isolated_junctions, isolated_links = self._get_isolated_junctions_and_links()
            if logger_level <= logging.DEBUG:
                if len(isolated_junctions) > 0 or len(isolated_links) > 0:
                    logger.debug('isolated junctions: {0}'.format(isolated_junctions))
                    logger.debug('isolated links: {0}'.format(isolated_links))
                else:
                    logger.debug('no isolated junctions or links found')
            model.set_isolated_junctions_and_links(isolated_junctions, isolated_links)
            if not first_step and not resolve:
                model.update_tank_heads()
            model.set_network_inputs_by_id()
            model.set_jacobian_constants()

            # Solve
            if logger_level <= logging.DEBUG:
                logger.debug('solving')
            [self._X, num_iters, solver_status, message] = self._solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            if solver_status == 0:
                if convergence_error:
                    logger.error('Simulation did not converge. ' + message)
                    raise RuntimeError('Simulation did not converge. ' + message)
                warnings.warn('Simulation did not converge. ' + message)
                logger.warning('Simulation did not converge at time ' + str(self._get_time()) + '. ' + message)
                results.error_code = 2
                break
            X_init = np.array(self._X)

            # Enter results in network and update previous inputs
            if logger_level <= logging.DEBUG:
                logger.debug('storing results in network')
            model.store_results_in_network(self._X)

            if logger_level <= logging.DEBUG:
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
                self._postsolve_controls.reset()
                trial += 1
                if trial > max_trials:
                    if convergence_error:
                        logger.error('Exceeded maximum number of trials.')
                        raise RuntimeError('Exceeded maximum number of trials.')
                    results.error_code = 2
                    warnings.warn('Exceeded maximum number of trials.')
                    logger.warning('Exceeded maximum number of trials at time %s', self._get_time())
                    break
                continue

            logger.debug('no changes made by postsolve controls; moving to next timestep')

            resolve = False
            if type(self._wn.options.time.report_timestep) == float or type(self._wn.options.time.report_timestep) == int:
                if self._wn.sim_time % self._wn.options.time.report_timestep == 0:
                    model.save_results(self._X, results)
                    if len(results.time) > 0 and int(self._wn.sim_time) == results.time[-1]:
                        raise RuntimeError('Simulation already solved this timestep')
                    results.time.append(int(self._wn.sim_time))
            elif self._wn.options.time.report_timestep.upper() == 'ALL':
                model.save_results(self._X, results)
                if len(results.time) > 0 and int(self._wn.sim_time) == results.time[-1]:
                    raise RuntimeError('Simulation already solved this timestep')
                results.time.append(int(self._wn.sim_time))
            model.update_network_previous_values()
            first_step = False
            self._wn.sim_time += self._wn.options.time.hydraulic_timestep
            overstep = float(self._wn.sim_time) % self._wn.options.time.hydraulic_timestep
            self._wn.sim_time -= overstep

            if self._wn.sim_time > self._wn.options.time.duration:
                break

            self._time_per_step.append(time.time()-start_step_time)

        model.get_results(results)
        self._wn.options.time.report_timestep = orig_report_timestep
        self._wn.options.time.hydraulic_timestep = orig_hydraulic_timestep
        return results

    def _initialize_internal_graph(self):
        n_links = {}
        rows = []
        cols = []
        vals = []
        for link_name, link in itertools.chain(self._wn.pipes(), self._wn.pumps(), self._wn.valves()):
            from_node_name = link.start_node_name
            to_node_name = link.end_node_name
            from_node_id = self._model._node_name_to_id[from_node_name]
            to_node_id = self._model._node_name_to_id[to_node_name]
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

        ndx_map = {}
        for link_name, link in self._wn.links():
            ndx1 = None
            ndx2 = None
            from_node_name = link.start_node_name
            to_node_name = link.end_node_name
            from_node_id = self._model._node_name_to_id[from_node_name]
            to_node_id = self._model._node_name_to_id[to_node_name]
            ndx1 = _get_csr_data_index(self._internal_graph, from_node_id, to_node_id)
            ndx2 = _get_csr_data_index(self._internal_graph, to_node_id, from_node_id)
            ndx_map[link] = (ndx1, ndx2)
        self._map_link_to_internal_graph_data_ndx = ndx_map

        self._number_of_connections = [0 for i in range(self._model.num_nodes)]
        for node_id in self._model._node_ids:
            self._number_of_connections[node_id] = self._internal_graph.indptr[node_id+1] - self._internal_graph.indptr[node_id]

        self._node_pairs_with_multiple_links = {}
        for from_node_id, to_node_id in n_links.keys():
            if n_links[(from_node_id, to_node_id)] > 1:
                if (to_node_id, from_node_id) in self._node_pairs_with_multiple_links:
                    continue
                self._internal_graph[from_node_id, to_node_id] = 0
                self._internal_graph[to_node_id, from_node_id] = 0
                from_node_name = self._model._node_id_to_name[from_node_id]
                to_node_name = self._model._node_id_to_name[to_node_id]
                tmp_list = self._node_pairs_with_multiple_links[(from_node_id, to_node_id)] = []
                for link_name in self._wn.get_links_for_node(from_node_name):
                    link = self._wn.get_link(link_name)
                    if link.start_node_name == to_node_name or link.end_node_name == to_node_name:
                        tmp_list.append(link)
                        if link.status != wntr.network.LinkStatus.closed:
                            ndx1, ndx2 = ndx_map[link]
                            self._internal_graph.data[ndx1] = 1
                            self._internal_graph.data[ndx2] = 1

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
            from_node_id = key[0]
            to_node_id = key[1]
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

        node_set = [1 for i in range(self._model.num_nodes)]

        def grab_group(node_id):
            node_set[node_id] = 0
            nodes_to_explore = set()
            nodes_to_explore.add(node_id)
            indptr = self._internal_graph.indptr
            indices = self._internal_graph.indices
            data = self._internal_graph.data
            num_connections = self._number_of_connections

            while len(nodes_to_explore) != 0:
                node_being_explored = nodes_to_explore.pop()
                ndx = indptr[node_being_explored]
                number_of_connections = num_connections[node_being_explored]
                vals = data[ndx:ndx+number_of_connections]
                cols = indices[ndx:ndx+number_of_connections]
                for i, val in enumerate(vals):
                    if val == 1:
                        col = cols[i]
                        if node_set[col] ==1:
                            node_set[col] = 0
                            nodes_to_explore.add(col)

        for tank_name, tank in self._wn.nodes(wntr.network.Tank):
            tank_id = self._model._node_name_to_id[tank_name]
            if node_set[tank_id] == 1:
                grab_group(tank_id)
            else:
                continue

        for reservoir_name, reservoir in self._wn.nodes(wntr.network.Reservoir):
            reservoir_id = self._model._node_name_to_id[reservoir_name]
            if node_set[reservoir_id] == 1:
                grab_group(reservoir_id)
            else:
                continue

        isolated_junction_ids = [i for i in range(len(node_set)) if node_set[i] == 1]
        isolated_junctions = set()
        isolated_links = set()
        for j_id in isolated_junction_ids:
            j = self._model._node_id_to_name[j_id]
            isolated_junctions.add(j)
            connected_links = self._wn.get_links_for_node(j)
            for l in connected_links:
                isolated_links.add(l)
        isolated_junctions = list(isolated_junctions)
        isolated_links = list(isolated_links)

        return isolated_junctions, isolated_links


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
