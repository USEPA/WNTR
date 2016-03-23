from wntr import *
import numpy as np
import scipy.sparse as sparse
import warnings
from WaterNetworkSimulator import *
from HydraulicModel import *
from wntr.network.WaterNetworkModel import *
from NewtonSolver import *
from NetworkResults import *
import time
import copy

import logging
logger = logging.getLogger(__name__)

class WNTRSimulator(WaterNetworkSimulator):
    """
    Run simulation using custom newton solver and linear solvers from scipy.sparse.
    """

    def __init__(self, wn, pressure_driven=False):
        """
        Simulator object to be used for running scipy simulations.

        Parameters
        ----------
        wn : WaterNetworkModel
            A water network
        """

        super(WNTRSimulator, self).__init__(wn, pressure_driven)

    def get_time(self):
        s = int(self._wn.sim_time)
        h = s/3600
        s -= h*3600
        m = s/60
        s-=m*60
        return str(h)+':'+str(m)+':'+str(s)

    def run_sim(self,solver_options={}):
        """
        Method to run an extended period simulation
        """

        self.time_per_step = []

        self._get_demand_dict()

        tank_controls = self._wn._get_all_tank_controls()
        cv_controls = self._wn._get_cv_controls()
        pump_controls = self._wn._get_pump_controls()
        valve_controls = self._wn._get_valve_controls()

        self._controls = self._wn._control_dict.values()+tank_controls+cv_controls+pump_controls+valve_controls

        model = HydraulicModel(self._wn, self.pressure_driven)
        model.initialize_results_dict()

        self.solver = NewtonSolver(options=solver_options)

        results = NetResults()
        if self._wn.sim_time%self._wn.options.hydraulic_timestep!=0:
            results_start_time = int(round((self._wn.options.hydraulic_timestep-(self._wn.sim_time%self._wn.options.hydraulic_timestep))+self._wn.sim_time))
        else:
            results_start_time = int(round(self._wn.sim_time))
        results.time = np.arange(results_start_time, self._wn.options.duration+self._wn.options.hydraulic_timestep, self._wn.options.hydraulic_timestep)

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

        if self._wn.sim_time==0:
            first_step = True
        else:
            first_step = False
        trial = -1
        max_trials = self._wn.options.trials
        resolve = False

        while True:

            #print ' '
            #print ' '
            
            if not resolve:
                start_step_time = time.time()

            if not resolve:
                trial = 0
                #print 'presolve = True'
                last_backup_time = np.inf
                while True:
                    backup_time, controls_to_activate = self._check_controls(presolve=True,last_backup_time=last_backup_time)
                    changes_made_flag = self._fire_controls(controls_to_activate)
                    if changes_made_flag:
                        self._wn.sim_time -= backup_time
                        break
                    if backup_time == 0:
                        break
                    last_backup_time = backup_time

            logger.info('simulation time = %s, trial = %d',self.get_time(),trial)

            # Prepare for solve
            model.identify_isolated_junctions()
            if not first_step:
                model.update_tank_heads()
            model.update_junction_demands(self._demand_dict)
            model.set_network_inputs_by_id()
            model.set_jacobian_constants()

            # Solve
            [self._X,num_iters,solver_status] = self.solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            if solver_status == 0:
                model.check_infeasibility(self._X)
                raise RuntimeError('No solution found.')
            X_init = copy.copy(self._X)

            # Enter results in network and update previous inputs
            model.store_results_in_network(self._X)

            #print 'presolve = False'
            resolve, resolve_controls_to_activate = self._check_controls(presolve=False)
            if resolve or solver_status==0:
                trial += 1
                all_controls_to_activate = controls_to_activate+resolve_controls_to_activate
                changes_made_flag = self._fire_controls(all_controls_to_activate)
                if changes_made_flag:
                    if trial > max_trials:
                        raise RuntimeError('Exceeded maximum number of trials!')
                    continue
                else:
                    if solver_status==0:
                        raise RuntimeError('failed to converge')
                    resolve = False

            if self._wn.sim_time%self._wn.options.hydraulic_timestep == 0:
                model.save_results(self._X, results)
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
            for i in xrange(len(self._controls)):
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
            for i in xrange(len(self._controls)):
                control = self._controls[i]
                control_tuple = control.IsControlActionRequired(self._wn, presolve)
                if control_tuple[0]:
                    resolve = True
                    resolve_controls_to_activate.append(i)
            return resolve, resolve_controls_to_activate

    def _fire_controls(self, controls_to_activate):
        changes_made = False
        change_dict = {}
        for i in controls_to_activate:
            control = self._controls[i]
            change_flag, change_tuple, orig_value = control.FireControlAction(self._wn, 0)
            if change_flag:
                if change_tuple not in change_dict.keys():
                    change_dict[change_tuple] = orig_value

        for i in controls_to_activate:
            control = self._controls[i]
            change_flag, change_tuple, orig_value = control.FireControlAction(self._wn, 1)
            if change_flag:
                if change_tuple not in change_dict.keys():
                    change_dict[change_tuple] = orig_value

        for i in controls_to_activate:
            control = self._controls[i]
            change_flag, change_tuple, orig_value = control.FireControlAction(self._wn, 2)
            if change_flag:
                if change_tuple not in change_dict.keys():
                    change_dict[change_tuple] = orig_value

        for i in controls_to_activate:
            control = self._controls[i]
            change_flag, change_tuple, orig_value = control.FireControlAction(self._wn, 3)
            if change_flag:
                if change_tuple not in change_dict.keys():
                    change_dict[change_tuple] = orig_value

        self._align_valve_statuses()

        for change_tuple, orig_value in change_dict.iteritems():
            if orig_value!=getattr(change_tuple[0],change_tuple[1]):
                changes_made = True
                #print 'setting ',change_tuple[0].name(),change_tuple[1],' to ',getattr(change_tuple[0],change_tuple[1])

        return changes_made

    def _align_valve_statuses(self):
        for valve_name, valve in self._wn.links(Valve):
            if valve.status==wntr.network.LinkStatus.opened:
                valve._status = valve.status
                #print 'setting ',valve.name(),' _status to ',valve.status
            elif valve.status==wntr.network.LinkStatus.closed:
                valve._status = valve.status
                #print 'setting ',valve.name(),' _status to ',valve.status
