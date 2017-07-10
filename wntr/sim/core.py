from wntr import *
from wntr.sim.hydraulics import *
from wntr.network.model import *
from wntr.sim.solvers import *
from wntr.sim.results import *
from wntr.network.model import *
import numpy as np
import warnings
import time
import sys
import logging
import scipy.sparse
import scipy.sparse.csr

logger = logging.getLogger(__name__)

class WaterNetworkSimulator(object):
    """
    Base water network simulator class.

    wn : WaterNetworkModel object
        Water network model

    pressure_driven: bool (optional)
        Specifies whether the simulation will be demand-driven or
        pressure-driven, default = False
    """

    def __init__(self, wn=None, pressure_driven=False):

        self._wn = wn
        self.pressure_driven = pressure_driven

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
            end_time = self._wn.options.duration

        # Get node object
        try:
            node = self._wn.get_node(node_name)
        except KeyError:
            raise KeyError("Not a valid node name")
        # Make sure node object is a Junction
        assert(isinstance(node, Junction)), "Demands can only be calculated for Junctions"
        # Calculate demand pattern values
        base_demand = node.base_demand
        pattern_name = node.demand_pattern_name
        if pattern_name is None:
            pattern_name = self._wn.options.pattern
        if pattern_name is None:
            demand_values = []
            demand_times_minutes = range(start_time, end_time + self._wn.options.hydraulic_timestep,
                                         self._wn.options.hydraulic_timestep)
            for t in demand_times_minutes:
                demand_values.append(base_demand)
            return demand_values
        pattern_list = self._wn.get_pattern(pattern_name)
        pattern_length = len(pattern_list)
        offset = self._wn.options.pattern_start

        assert(offset == 0.0), "Only 0.0 Pattern Start time is currently supported. "

        demand_times_minutes = range(start_time, end_time + self._wn.options.hydraulic_timestep, self._wn.options.hydraulic_timestep)
        demand_pattern_values = [base_demand*i for i in pattern_list]

        demand_values = []
        for t in demand_times_minutes:
            # Modulus with the last pattern time to get time within pattern range
            pattern_index = t / self._wn.options.pattern_timestep
            # Modulus with the pattern time step to get the pattern index
            pattern_index = pattern_index % pattern_length
            demand_values.append(demand_pattern_values[int(pattern_index)])

        return demand_values

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

    pressure_driven: bool (optional)
        Specifies whether the simulation will be demand-driven or
        pressure-driven, default = False
    """

    def __init__(self, wn, pressure_driven=False):

        super(WNTRSimulator, self).__init__(wn, pressure_driven)
        self._internal_graph = None
        self._node_pairs_with_multiple_links = None
        self._control_log = None

    def _get_time(self):
        s = int(self._wn.sim_time)
        h = s/3600
        s -= h*3600
        m = s/60
        s-=m*60
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

        self._get_demand_dict()

        tank_controls = self._wn._get_all_tank_controls()
        cv_controls = self._wn._get_cv_controls()
        pump_controls = self._wn._get_pump_controls()
        valve_controls = self._wn._get_valve_controls()

        self._controls = list(self._wn._control_dict.values())+tank_controls+cv_controls+pump_controls+valve_controls

        model = HydraulicModel(self._wn, self.pressure_driven)
        self._model = model
        model.initialize_results_dict()

        self.solver = NewtonSolver(model.num_nodes, model.num_links, model.num_leaks, model, options=solver_options)

        results = NetResults()
        results.error_code = 0
        results.time = []
        # if self._wn.sim_time%self._wn.options.hydraulic_timestep!=0:
        #     results_start_time = int(round((self._wn.options.hydraulic_timestep-(self._wn.sim_time%self._wn.options.hydraulic_timestep))+self._wn.sim_time))
        # else:
        #     results_start_time = int(round(self._wn.sim_time))
        # results.time = np.arange(results_start_time, self._wn.options.duration+self._wn.options.hydraulic_timestep, self._wn.options.hydraulic_timestep)

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
        self._control_log = wntr.network.ControlLogger()

        if self._wn.sim_time==0:
            first_step = True
        else:
            first_step = False
        trial = -1
        max_trials = self._wn.options.trials
        resolve = False

        while True:

            logger.debug(' ')
            logger.debug(' ')

            if not resolve:
                start_step_time = time.time()

            if not resolve:
                trial = 0
                #print 'presolve = True'
                last_backup_time = np.inf
                while True:
                    backup_time, controls_to_activate = self._check_controls(presolve=True,last_backup_time=last_backup_time)
                    changes_made_flag = self._run_controls(controls_to_activate)
                    if changes_made_flag:
                        self._wn.sim_time -= backup_time
                        break
                    if backup_time == 0:
                        break
                    last_backup_time = backup_time

            logger.info('simulation time = %s, trial = %d',self._get_time(),trial)

            # Prepare for solve
            #model.reset_isolated_junctions()
            isolated_junctions, isolated_links = self._get_isolated_junctions_and_links()
            model.identify_isolated_junctions(isolated_junctions, isolated_links)
            # model.identify_isolated_junctions()
            if not first_step:
                model.update_tank_heads()
            model.update_junction_demands(self._demand_dict)
            model.set_network_inputs_by_id()
            model.set_jacobian_constants()

            # Solve
            #X_init = model.update_initializations(X_init)
            [self._X,num_iters,solver_status] = self.solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            #if solver_status == 0:
            #    model.identify_isolated_junctions()
            #    model.set_network_inputs_by_id()
            #    model.set_jacobian_constants()
            #    [self._X,num_iters,solver_status] = self.solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            if solver_status == 0:
                #model.check_infeasibility(self._X)
                #raise RuntimeError('No solution found.')
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

            #print 'presolve = False'
            resolve, resolve_controls_to_activate = self._check_controls(presolve=False)
            if resolve or solver_status==0:
                trial += 1
                all_controls_to_activate = controls_to_activate+resolve_controls_to_activate
                changes_made_flag = self._run_controls(all_controls_to_activate)
                if changes_made_flag:
                    if trial > max_trials:
                        if convergence_error:
                            raise RuntimeError('Exceeded maximum number of trials.')
                        results.error_code = 2
                        warnings.warn('Exceeded maximum number of trials.')
                        logger.warning('Exceeded maximum number of trials at time %s',self._get_time())
                        model.get_results(results)
                        return results
                    continue
                else:
                    if solver_status==0:
                        results.error_code = 2
                        raise RuntimeError('failed to converge')
                    resolve = False

            if type(self._wn.options.report_timestep)==float or type(self._wn.options.report_timestep)==int:
                if self._wn.sim_time%self._wn.options.report_timestep == 0:
                    model.save_results(self._X, results)
                    results.time.append(int(self._wn.sim_time))
            elif self._wn.options.report_timestep.upper()=='ALL':
                model.save_results(self._X, results)
                results.time.append(int(self._wn.sim_time))
            model.update_network_previous_values()
            first_step = False
            self._wn.sim_time += self._wn.options.hydraulic_timestep
            overstep = float(self._wn.sim_time)%self._wn.options.hydraulic_timestep
            self._wn.sim_time -= overstep

            if self._wn.sim_time > self._wn.options.duration:
                break

            if not resolve:
                self.time_per_step.append(time.time()-start_step_time)

        model.get_results(results)
        return results

    def _get_demand_dict(self):

        # Number of hydraulic timesteps
        self._n_timesteps = int(round(self._wn.options.duration / self._wn.options.hydraulic_timestep)) + 1

        # Get all demand for complete time interval
        self._demand_dict = {}
        for node_name, node in self._wn.nodes(Junction):
            demand_values = self.get_node_demand(node_name)
            for t in range(self._n_timesteps):
                self._demand_dict[(node_name, t)] = demand_values[t]

    def _check_controls(self, presolve, last_backup_time=None):
        if presolve:
            assert last_backup_time is not None
            backup_time = 0.0
            controls_to_activate = []
            controls_to_activate_regardless_of_time = []
            for i in range(len(self._controls)):
                control = self._controls[i]
                control_tuple = control.IsControlActionRequired(self._wn, presolve)
                assert type(control_tuple[1]) == int or control_tuple[1] == None, 'control backup time should be an int. back up time = '+str(control_tuple[1])
                if control_tuple[0] and control_tuple[1]==None:
                    controls_to_activate_regardless_of_time.append(i)
                elif control_tuple[0] and control_tuple[1] > backup_time and control_tuple[1]<last_backup_time:
                    controls_to_activate = [i]
                    backup_time = control_tuple[1]
                elif control_tuple[0] and control_tuple[1] == backup_time:
                    controls_to_activate.append(i)
            assert backup_time <= self._wn.options.hydraulic_timestep, 'Backup time is larger than hydraulic timestep'
            return backup_time, (controls_to_activate+controls_to_activate_regardless_of_time)

        else:
            resolve = False
            resolve_controls_to_activate = []
            for i, control in enumerate(self._controls):
                control_tuple = control.IsControlActionRequired(self._wn, presolve)
                if control_tuple[0]:
                    resolve = True
                    resolve_controls_to_activate.append(i)
            return resolve, resolve_controls_to_activate

    def _run_controls(self, controls_to_activate):
        changes_made = False
        change_dict = {}
        for i in controls_to_activate:
            control = self._controls[i]
            change_flag, change_tuple, orig_value = control.RunControlAction(self._wn, 0)
            if change_flag:
                if isinstance(change_tuple, list):
                    for ct in range(len(change_tuple)):
                        if change_tuple[ct] not in change_dict:
                            change_dict[change_tuple[ct]] = (orig_value[ct], control.name)
                elif change_tuple not in change_dict:
                    change_dict[change_tuple] = (orig_value, control.name)

        for i in controls_to_activate:
            control = self._controls[i]
            change_flag, change_tuple, orig_value = control.RunControlAction(self._wn, 1)
            if change_flag:
                if isinstance(change_tuple, list):
                    for ct in range(len(change_tuple)):
                        if change_tuple[ct] not in change_dict:
                            change_dict[change_tuple[ct]] = (orig_value[ct], control.name)
                elif change_tuple not in change_dict:
                    change_dict[change_tuple] = (orig_value, control.name)

        for i in controls_to_activate:
            control = self._controls[i]
            change_flag, change_tuple, orig_value = control.RunControlAction(self._wn, 2)
            if change_flag:
                if isinstance(change_tuple, list):
                    for ct in range(len(change_tuple)):
                        if change_tuple[ct] not in change_dict:
                            change_dict[change_tuple[ct]] = (orig_value[ct], control.name)
                elif change_tuple not in change_dict:
                    change_dict[change_tuple] = (orig_value, control.name)

        for i in controls_to_activate:
            control = self._controls[i]
            change_flag, change_tuple, orig_value = control.RunControlAction(self._wn, 3)
            if change_flag:
                if isinstance(change_tuple, list):
                    for ct in range(len(change_tuple)):
                        if change_tuple[ct] not in change_dict:
                            change_dict[change_tuple[ct]] = (orig_value[ct], control.name)
                elif change_tuple not in change_dict:
                    change_dict[change_tuple] = (orig_value, control.name)

        self._control_log.reset()

        self._align_valve_statuses()

        for change_tuple, orig_value_control_name in change_dict.items():
            orig_value = orig_value_control_name[0]
            control_name = orig_value_control_name[1]
            if orig_value!=getattr(change_tuple[0],change_tuple[1]):
                changes_made = True
                self._control_log.add(change_tuple[0],change_tuple[1])
                logger.debug('setting {0} {1} to {2} because of control {3}'.format(change_tuple[0].name,change_tuple[1],getattr(change_tuple[0],change_tuple[1]),control_name))

        self._update_internal_graph()

        return changes_made

    def _align_valve_statuses(self):
        for valve_name, valve in self._wn.links(Valve):
            if valve.valve_type == 'TCV':
                valve._status = valve.status
            else:
                if valve.status==wntr.network.LinkStatus.opened:
                    valve._status = valve.status
                    #print 'setting ',valve.name(),' _status to ',valve.status
                elif valve.status==wntr.network.LinkStatus.closed:
                    valve._status = valve.status
                    #print 'setting ',valve.name(),' _status to ',valve.status

    def _initialize_internal_graph(self):
        n_links = {}
        rows = []
        cols = []
        vals = []
        for link_name, link in self._wn.links(wntr.network.Pipe):
            from_node_name = link.start_node
            to_node_name = link.end_node
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

        for link_name, link in self._wn.links(wntr.network.Pump):
            from_node_name = link.start_node
            to_node_name = link.end_node
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
            if link.status == wntr.network.LinkStatus.closed or link._cv_status == wntr.network.LinkStatus.closed:
                vals.append(0)
                vals.append(0)
            else:
                vals.append(1)
                vals.append(1)

        for link_name, link in self._wn.links(wntr.network.Valve):
            from_node_name = link.start_node
            to_node_name = link.end_node
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
            if link.status == wntr.network.LinkStatus.closed or link._status == wntr.network.LinkStatus.closed:
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
            from_node_name = link.start_node
            to_node_name = link.end_node
            from_node_id = self._model._node_name_to_id[from_node_name]
            to_node_id = self._model._node_name_to_id[to_node_name]
            ndx1 = _get_csr_data_index(self._internal_graph, from_node_id, to_node_id)
            ndx2 = _get_csr_data_index(self._internal_graph, to_node_id, from_node_id)
            ndx_map[link] = (ndx1, ndx2)
        self._map_link_to_internal_graph_data_ndx = ndx_map

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
                    if link.start_node == to_node_name or link.end_node == to_node_name:
                        tmp_list.append(link)
                        if isinstance(link, wntr.network.Pipe):
                            if link.status != wntr.network.LinkStatus.closed:
                                ndx1, ndx2 = ndx_map[link]
                                self._internal_graph.data[ndx1] = 1
                                self._internal_graph.data[ndx2] = 1
                        elif isinstance(link, wntr.network.Pump):
                            if link.status != wntr.network.LinkStatus.closed and link._cv_status != wntr.network.LinkStatus.closed:
                                ndx1, ndx2 = ndx_map[link]
                                self._internal_graph.data[ndx1] = 1
                                self._internal_graph.data[ndx2] = 1
                        elif isinstance(link, wntr.network.Valve):
                            if link.status != wntr.network.LinkStatus.closed and link._status != wntr.network.LinkStatus.closed:
                                ndx1, ndx2 = ndx_map[link]
                                self._internal_graph.data[ndx1] = 1
                                self._internal_graph.data[ndx2] = 1
                        else:
                            raise RuntimeError('Unrecognized link type.')

    def _update_internal_graph(self):
        data = self._internal_graph.data
        ndx_map = self._map_link_to_internal_graph_data_ndx
        for obj_name, obj in self._control_log.changed_objects.items():
            changed_attrs = self._control_log.changed_attributes[obj_name]
            if type(obj) == wntr.network.Pipe:
                if 'status' in changed_attrs:
                    if obj.status == wntr.network.LinkStatus.opened:
                        ndx1, ndx2 = ndx_map[obj]
                        data[ndx1] = 1
                        data[ndx2] = 1
                    elif obj.status == wntr.network.LinkStatus.closed:
                        ndx1, ndx2 = ndx_map[obj]
                        data[ndx1] = 0
                        data[ndx2] = 0
                    else:
                        raise RuntimeError('Pipe status not recognized: %s', getattr(obj, 'status'))
            elif type(obj) == wntr.network.Pump:
                if 'status' in changed_attrs and '_cv_status' in changed_attrs:
                    if obj.status == wntr.network.LinkStatus.closed and obj._cv_status == wntr.network.LinkStatus.closed:
                        ndx1, ndx2 = ndx_map[obj]
                        data[ndx1] = 0
                        data[ndx2] = 0
                    elif obj.status == wntr.network.LinkStatus.opened and obj._cv_status == wntr.network.LinkStatus.opened:
                        ndx1, ndx2 = ndx_map[obj]
                        data[ndx1] = 1
                        data[ndx2] = 1
                    else:
                        pass
                elif 'status' in changed_attrs:
                    if obj.status == wntr.network.LinkStatus.closed:
                        if obj._cv_status == wntr.network.LinkStatus.opened:
                            ndx1, ndx2 = ndx_map[obj]
                            data[ndx1] = 0
                            data[ndx2] = 0
                    elif obj.status == wntr.network.LinkStatus.opened:
                        if obj._cv_status == wntr.network.LinkStatus.opened:
                            ndx1, ndx2 = ndx_map[obj]
                            data[ndx1] = 1
                            data[ndx2] = 1
                elif '_cv_status' in changed_attrs:
                    if obj._cv_status == wntr.network.LinkStatus.closed:
                        if obj.status == wntr.network.LinkStatus.opened:
                            ndx1, ndx2 = ndx_map[obj]
                            data[ndx1] = 0
                            data[ndx2] = 0
                    elif obj._cv_status == wntr.network.LinkStatus.opened:
                        if obj.status == wntr.network.LinkStatus.opened:
                            ndx1, ndx2 = ndx_map[obj]
                            data[ndx1] = 1
                            data[ndx2] = 1
            elif type(obj) == wntr.network.Valve:
                if ((obj.status == wntr.network.LinkStatus.opened or
                             obj.status == wntr.network.LinkStatus.active) and
                        (obj._status == wntr.network.LinkStatus.opened or
                                 obj._status == wntr.network.LinkStatus.active)):
                    ndx1, ndx2 = ndx_map[obj]
                    data[ndx1] = 1
                    data[ndx2] = 1
                elif obj.status == wntr.network.LinkStatus.closed:
                    ndx1, ndx2 = ndx_map[obj]
                    data[ndx1] = 0
                    data[ndx2] = 0
                elif obj.status == wntr.network.LinkStatus.active and obj._status == wntr.network.LinkStatus.closed:
                    ndx1, ndx2 = ndx_map[obj]
                    data[ndx1] = 0
                    data[ndx2] = 0

        for key, link_list in self._node_pairs_with_multiple_links.items():
            from_node_id = key[0]
            to_node_id = key[1]
            first_link = link_list[0]
            ndx1, ndx2 = ndx_map[first_link]
            data[ndx1] = 0
            data[ndx2] = 0
            for link in link_list:
                if isinstance(link, wntr.network.Pipe):
                    if link.status != wntr.network.LinkStatus.closed:
                        ndx1, ndx2 = ndx_map[link]
                        data[ndx1] = 1
                        data[ndx2] = 1
                elif isinstance(link, wntr.network.Pump):
                    if link.status != wntr.network.LinkStatus.closed and link._cv_status != wntr.network.LinkStatus.closed:
                        ndx1, ndx2 = ndx_map[link]
                        data[ndx1] = 1
                        data[ndx2] = 1
                elif isinstance(link, wntr.network.Valve):
                    if link.status != wntr.network.LinkStatus.closed and link._status != wntr.network.LinkStatus.closed:
                        ndx1, ndx2 = ndx_map[link]
                        data[ndx1] = 1
                        data[ndx2] = 1
                else:
                    raise RuntimeError('Unrecognized link type.')

    def _get_isolated_junctions_and_links(self):

        # isolated_junctions = set()
        # isolated_links = set()
        # n = 1
        # for subG in nx.connected_component_subgraphs(self._internal_graph):
        #     print 'subgraph ',n
        #     n += 1
        #     # print subG.nodes()
        #     type_list = [i[1]['type'] for i in subG.nodes_iter(data=True)]
        #     if 'tank' in type_list or 'reservoir' in type_list:
        #         continue
        #     else:
        #         isolated_junctions = isolated_junctions.union(set(subG.nodes()))
        #         for start_node, end_node, key in subG.edges_iter(keys=True):
        #             isolated_links.add(key)
        # return isolated_junctions, isolated_links

        node_set = set(range(self._model.num_nodes))

        def grab_group(node_id):
            node_set.remove(node_id)
            nodes_to_explore = set()
            nodes_to_explore.add(node_id)

            while len(nodes_to_explore) != 0:
                node_being_explored = nodes_to_explore.pop()
                number_of_connections = (self._internal_graph.indptr[node_being_explored+1] -
                                         self._internal_graph.indptr[node_being_explored])
                ndx = self._internal_graph.indptr[node_being_explored]
                vals = self._internal_graph.data[ndx:ndx+number_of_connections]
                cols = self._internal_graph.indices[ndx:ndx+number_of_connections]
                for val, col in zip(vals, cols):
                    if val == 1:
                        if col in node_set:
                            node_set.remove(col)
                            nodes_to_explore.add(col)

        for tank_name, tank in self._wn.nodes(wntr.network.Tank):
            tank_id = self._model._node_name_to_id[tank_name]
            if tank_id in node_set:
                grab_group(tank_id)
            else:
                continue

        for reservoir_name, reservoir in self._wn.nodes(wntr.network.Reservoir):
            reservoir_id = self._model._node_name_to_id[reservoir_name]
            if reservoir_id in node_set:
                grab_group(reservoir_id)
            else:
                continue

        isolated_junction_ids = list(node_set)
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
