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
        self._control_log = None

    def _get_time(self):
        s = int(self._wn.sim_time)
        h = int(s/3600)
        s -= h*3600
        m = int(s/60)
        s -= m*60
        s = int(s)
        return str(h)+':'+str(m)+':'+str(s)

    def run_sim(self,solver_options={}, convergence_error=True):
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
        self.time_per_step = []

        self._presolve_controls = ControlManager()
        self._postsolve_controls = ControlManager()
        self._rules = ControlManager()

        def categorize_control(control):
            if control._control_type in {_ControlType.presolve, _ControlType.pre_and_postsolve}:
                self._presolve_controls.register_control(control)
            if control._control_type in {_ControlType.postsolve, _ControlType.pre_and_postsolve}:
                self._postsolve_controls.register_control(control)
            if control._control_type == _ControlType.rule:
                self._rules.register_control(control)

        for c_name, c in self._wn.controls():
            categorize_control(c)
        for c in self._wn._get_all_tank_controls() + self._wn._get_cv_controls() + self._wn._get_pump_controls() + self._wn._get_valve_controls():
            categorize_control(c)

        model = HydraulicModel(self._wn, self.mode)
        self._model = model
        model.initialize_results_dict()

        self.solver = NewtonSolver(model.num_nodes, model.num_links, model.num_leaks, model, options=solver_options)

        results = NetResults()
        results.error_code = 0
        results.time = []

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

        X_init = np.concatenate((head0, demand0, flow0,leak_demand0))

        self._initialize_internal_graph()

        if self._wn.sim_time == 0:
            first_step = True
        else:
            first_step = False
        trial = -1
        max_trials = self._wn.options.solver.trials
        resolve = False
        rule_iter = 0

        while True:
            logger.debug(' ')
            logger.debug(' ')

            if not resolve:
                start_step_time = time.time()

            if not resolve:
                if not first_step:
                    self._model.update_tank_heads()
                trial = 0
                presolve_controls_to_run = self._presolve_controls.check()
                presolve_controls_to_run.sort(key=lambda i: i[0]._priority)
                presolve_controls_to_run.sort(key=lambda i: i[1], reverse=True)
                logger.debug('presolve_controls_to_run:')
                if logger.getEffectiveLevel() <= logging.DEBUG:
                    for pctr in presolve_controls_to_run:
                        logger.debug('\t' + str(pctr[0]) + '\t' + str(pctr[1]))
                cnt = 0
                while cnt < len(presolve_controls_to_run) or rule_iter * self._wn.options.time.rule_timestep <= self._wn.sim_time:
                    if cnt >= len(presolve_controls_to_run):
                        logger.debug('no presolve controls need activated; checking rules')
                        old_time = self._wn.sim_time
                        self._wn.sim_time = rule_iter * self._wn.options.time.rule_timestep
                        rule_iter += 1
                        rules_to_run = self._rules.check()
                        rules_to_run.sort(key=lambda i: i[0]._priority)
                        for rule, rule_back in rules_to_run:
                            rule.run_control_action()
                        if self._rules.changes_made():
                            logger.debug('changes made by rules; solving rule timestep')
                            break
                        self._wn.sim_time = old_time
                    else:
                        control, backtrack = presolve_controls_to_run[cnt]
                        if self._wn.sim_time - backtrack < rule_iter * self._wn.options.time.rule_timestep:
                            if logger.getEffectiveLevel() <= logging.DEBUG:
                                logger.debug('running presolve controls:')
                                logger.debug('\t' + str(control))
                            control.run_control_action()
                            cnt += 1
                            while cnt < len(presolve_controls_to_run) and presolve_controls_to_run[cnt][1] == backtrack:
                                if logger.getEffectiveLevel() <= logging.DEBUG:
                                    logger.debug('\t' + str(presolve_controls_to_run[cnt][0]))
                                presolve_controls_to_run[cnt][0].run_control_action()
                                cnt += 1
                            if self._presolve_controls.changes_made():
                                if logger.getEffectiveLevel() <= logging.DEBUG:
                                    logger.debug('\tchanges were made; backtracking by {0}'.format(backtrack))
                                self._wn.sim_time -= backtrack
                                break
                        elif self._wn.sim_time - backtrack == rule_iter * self._wn.options.time.rule_timestep:
                            rule_iter += 1
                            self._wn.sim_time -= backtrack
                            rules_to_run = self._rules.check()
                            rules_to_run.sort(key=lambda i: i[0]._priority)
                            for rule, rule_back in rules_to_run:
                                rule.run_control_action()
                            control.run_control_action()
                            cnt += 1
                            while cnt < len(presolve_controls_to_run) and presolve_controls_to_run[cnt][1] == backtrack:
                                presolve_controls_to_run[cnt][0].run_control_action()
                                cnt += 1
                            if self._presolve_controls.changes_made() or self._rules.changes_made():
                                break
                            self._wn.sim_time += backtrack
                        else:
                            old_time = self._wn.sim_time
                            self._wn.sim_time = rule_iter * self._wn.options.time.rule_timestep
                            rule_iter += 1
                            rules_to_run = self._rules.check()
                            rules_to_run.sort(key=lambda i: i[0]._priority)
                            for rule, rule_back in rules_to_run:
                                rule.run_control_action()
                            if self._rules.changes_made():
                                break
                            self._wn.sim_time = old_time
                self._update_internal_graph()
                self._presolve_controls.reset()
                self._rules.reset()

            logger.info('simulation time = %s, trial = %d',self._get_time(),trial)

            # Prepare for solve
            isolated_junctions, isolated_links = self._get_isolated_junctions_and_links()
            model.set_isolated_junctions_and_links(isolated_junctions, isolated_links)
            if not first_step and not resolve:
                model.update_tank_heads()
            model.set_network_inputs_by_id()
            model.set_jacobian_constants()

            # Solve
            [self._X,num_iters,solver_status] = self.solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            if solver_status == 0:
                if convergence_error:
                    raise RuntimeError('Simulation did not converge!')
                warnings.warn('Simulation did not converge!')
                logger.warning('Simulation did not converge at time %s',self._get_time())
                model.get_results(results)
                results.error_code = 2
                return results
            X_init = np.array(self._X)

            # Enter results in network and update previous inputs
            model.store_results_in_network(self._X)

            postsolve_controls_to_run = self._postsolve_controls.check()
            postsolve_controls_to_run.sort(key=lambda i: i[0]._priority)
            for control, unused in postsolve_controls_to_run:
                control.run_control_action()
            if self._postsolve_controls.changes_made():
                logger.debug('postsolve controls made changes; resolving...')
                resolve = True
                self._update_internal_graph()
                self._postsolve_controls.reset()
                trial += 1
                if trial > max_trials:
                    if convergence_error:
                        raise RuntimeError('Exceeded maximum number of trials.')
                    results.error_code = 2
                    warnings.warn('Exceeded maximum number of trials.')
                    logger.warning('Exceeded maximum number of trials at time %s', self._get_time())
                    model.get_results(results)
                    return results
                continue

            logger.debug('no changes made by postsolve controls; moving to next timestep')

            resolve = False
            if type(self._wn.options.time.report_timestep) == float or type(self._wn.options.time.report_timestep) == int:
                if self._wn.sim_time % self._wn.options.time.report_timestep == 0:
                    model.save_results(self._X, results)
                    results.time.append(int(self._wn.sim_time))
            elif self._wn.options.time.report_timestep.upper() == 'ALL':
                model.save_results(self._X, results)
                results.time.append(int(self._wn.sim_time))
            model.update_network_previous_values()
            first_step = False
            self._wn.sim_time += self._wn.options.time.hydraulic_timestep
            overstep = float(self._wn.sim_time) % self._wn.options.time.hydraulic_timestep
            logger.debug('overstep: {0}'.format(overstep))
            self._wn.sim_time -= overstep
            logger.debug('new sim time: {0}'.format(self._wn.sim_time))

            if self._wn.sim_time > self._wn.options.time.duration:
                break

            self.time_per_step.append(time.time()-start_step_time)

        model.get_results(results)
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
