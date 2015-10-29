from wntr import *
import numpy as np
import scipy.sparse as sparse
import warnings
from WaterNetworkSimulator import *
from ScipyModel import *
from wntr.network.WaterNetworkModel import *
from NewtonSolver import *
from NetworkResults import *
import time
import copy

class ScipySimulator(WaterNetworkSimulator):
    """
    Run simulation using custom newton solver and linear solvers from scipy.sparse.
    """

    def __init__(self, wn):
        """
        Simulator object to be used for running scipy simulations.

        Parameters
        ----------
        wn : WaterNetworkModel
            A water network
        """

        super(ScipySimulator, self).__init__(wn)
        self._get_demand_dict()

    def run_sim(self):
        """
        Method to run an extended period simulation
        """

        model = ScipyModel(self._wn)
        model.initialize_results_dict()

        self.solver = NewtonSolver()

        results = NetResults()
        results.time = np.arange(0, self._wn.options.duration+self._wn.options.hydraulic_timestep, self._wn.options.hydraulic_timestep)

        # Initialize X
        # Vars will be ordered:
        #    1.) head
        #    2.) demand
        #    3.) flow
        model.set_network_inputs_by_id()
        head0 = model.initialize_head()
        demand0 = model.initialize_demand()
        flow0 = model.initialize_flow()
        
        X_init = np.concatenate((head0, demand0, flow0))

        first_step = True
        trial = -1
        max_trials = self._wn.options.trials
        resolve = False

        while True:
            if not resolve:
                trial = 0
                backup_time, controls_to_activate = self._check_controls(presolve=True)
                changes_made_flag = self._fire_controls(controls_to_activate)
                if changes_made_flag:
                    self._wn.sim_time -= backup_time

            print 'simulation time = ',self._wn.sim_time,', trial = ',trial

            # Prepare for solve
            if not first_step:
                model.update_tank_heads()
            model.update_junction_demands(self._demand_dict)
            model.set_network_inputs_by_id()
            model.set_jacobian_constants()

            # Solve
            [self._X,num_iters] = self.solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            X_init = copy.copy(self._X)

            # Enter results in network and update previous inputs
            model.store_results_in_network(self._X)

            resolve, resolve_controls_to_activate = self._check_controls(presolve=False)
            if resolve:
                trial += 1
                all_controls_to_activate = controls_to_activate+resolve_controls_to_activate
                changes_made_flag = self._fire_controls(all_controls_to_activate)
                if changes_made_flag:
                    continue
                else:
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

            if trial > max_trials:
                raise RuntimeError('Exceeded maximum number of trials!')

        model.get_results(results)
        return results

    def _get_demand_dict(self):

        # Number of hydraulic timesteps
        self._n_timesteps = int(round(self._wn.options.duration / self._wn.options.hydraulic_timestep)) + 1

        # Get all demand for complete time interval
        self._demand_dict = {}
        for node_name, node in self._wn.junctions():
            demand_values = self.get_node_demand(node_name)
            for t in range(self._n_timesteps):
                self._demand_dict[(node_name, t)] = demand_values[t]
        for node_name, node in self._wn.tanks():
            for t in range(self._n_timesteps):
                self._demand_dict[(node_name, t)] = 0.0
        for node_name, node in self._wn.reservoirs():
            for t in range(self._n_timesteps):
                self._demand_dict[(node_name, t)] = 0.0

    def _check_controls(self, presolve):
        if presolve:
            backup_time = 0.0
            controls_to_activate = []
            controls_to_activate_regardless_of_time = []
            for i in xrange(len(self._wn.controls)):
                control = self._wn.controls[i]
                control_tuple = control.IsControlActionRequired(self._wn, presolve)
                assert type(control_tuple[1]) == int or control_tuple[1] == None, 'control backup time should be an int. back up time = '+str(control_tuple[1])
                if control_tuple[0] and control_tuple[1]==None:
                    controls_to_activate_regardless_of_time.append(i)
                elif control_tuple[0] and control_tuple[1] > backup_time:
                    controls_to_activate = [i]
                    backup_time = control_tuple[1]
                elif control_tuple[0] and control_tuple[1] == backup_time:
                    controls_to_activate.append(i)
            assert backup_time <= self._wn.options.hydraulic_timestep, 'Backup time is larger than hydraulic timestep'
            return backup_time, (controls_to_activate+controls_to_activate_regardless_of_time)

        else:
            resolve = False
            resolve_controls_to_activate = []
            for i in xrange(len(self._wn.controls)):
                control = self._wn.controls[i]
                control_tuple = control.IsControlActionRequired(self._wn, presolve)
                if control_tuple[0]:
                    resolve = True
                    resolve_controls_to_activate.append(i)
            return resolve, resolve_controls_to_activate

    def _fire_controls(self, controls_to_activate):
        changes_made = False
        for i in controls_to_activate:
            control = self._wn.controls[i]
            change_flag = control.FireControlAction(self._wn, 0)
            if change_flag:
                changes_made = True
        for i in controls_to_activate:
            control = self._wn.controls[i]
            change_flag = control.FireControlAction(self._wn, 1)
            if change_flag:
                changes_made = True
        for i in controls_to_activate:
            control = self._wn.controls[i]
            change_flag = control.FireControlAction(self._wn, 2)
            if change_flag:
                changes_made = True
        for i in controls_to_activate:
            control = self._wn.controls[i]
            change_flag = control.FireControlAction(self._wn, 3)
            if change_flag:
                changes_made = True
        return changes_made

