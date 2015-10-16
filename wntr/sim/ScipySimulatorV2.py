from wntr import *
import numpy as np
import scipy.sparse as sparse
import warnings
from WaterNetworkSimulator import *
from ScipyModel import *
from wntr.network.WaterNetworkModel import *
from NewtonSolverV2 import *
from NetworkResults import *
import time
import copy

class ScipySimulatorV2(WaterNetworkSimulator):
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

        super(ScipySimulatorV2, self).__init__(wn)
        self._get_demand_dict()

        # Timing
        self.prep_time_before_main_loop = 0
        self.solve_step_time = {}

    def run_sim(self):
        """
        Method to run an extended period simulation
        """

        start_run_sim_time = time.time()

        model = ScipyModel(self._wn)
        model.initialize_results_dict()

        self.solver = NewtonSolverV2()

        results = NetResults()
        results.time = np.arange(0, self._wn.options.duration+self._wn.options.hydraulic_timestep, self._wn.options.hydraulic_timestep)

        # Initialize X
        # Vars will be ordered:
        #    1.) head
        #    2.) demand
        #    3.) flow
        model.set_network_status_by_id()
        head0 = model.initialize_head()
        demand0 = model.initialize_demand()
        flow0 = model.initialize_flow()
        
        X_init = np.concatenate((head0, demand0, flow0))

        start_main_loop_time = time.time()
        self.prep_time_before_main_loop = start_main_loop_time - start_run_sim_time

        first_step = True
        trial = 0

        while self._wn.sim_time <= self._wn.options.duration:
            print 'simulation time = ',self._wn.sim_time

            # Prepare for solve
            if not first_step:
                model.update_tank_heads(self._X)
            model.update_junction_demands(self._demand_dict)
            model.set_network_status_by_id()
            model.set_jacobian_constants()

            # Solve
            start_solve_step = time.time()
            [self._X,num_iters] = self.solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            end_solve_step = time.time()
            first_step = False
            X_init = copy.copy(self._X)
            self.solve_step_time[int(self._wn.sim_time/self._wn.options.hydraulic_timestep)] = end_solve_step - start_solve_step

            # Update previous inputs
            self._update_previous_inputs()

            # Controls
            backup_time, controls_to_activate = self._check_controls()
            self._fire_controls(controls_to_activate)

            # Choose next time and save results if needed
            if self._check_inputs_changed():
                print 'inputs changed'
                if trial == 0:
                    self._wn.sim_time -= backup_time
                trial += 1
            else:
                trial = 0
                if float(self._wn.sim_time)%self._wn.options.hydraulic_timestep == 0:
                    print 'saving_results at ',self._wn.sim_time
                    model.save_results(self._X, results)
                self._wn.prev_sim_time = self._wn.sim_time
                self._wn.sim_time += self._wn.options.hydraulic_timestep
                overstep = float(self._wn.sim_time)%self._wn.options.hydraulic_timestep
                self._wn.sim_time -= overstep

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

    def _check_controls(self):
        backup_time = 0.0
        controls_to_activate = []
        for i in xrange(len(self._wn.controls)):
            control = self._wn.controls[i]
            control_tuple = control.IsControlActionRequired(self._wn)
            assert type(control_tuple[1]) == int or control_tuple[1] == None, 'control backup time should be an int'
            if control_tuple[0] and control_tuple[1] > backup_time:
                controls_to_activate = [i]
                backup_time = control_tuple[1]
            elif control_tuple[0] and control_tuple[1] == backup_time:
                controls_to_activate.append(i)
        assert backup_time <= self._wn.options.hydraulic_timestep, 'Backup time is larger than hydraulic timestep'

        return backup_time, controls_to_activate

    def _fire_controls(self, controls_to_activate):
        for i in controls_to_activate:
            control = self._wn.controls[i]
            control.FireControlAction(self._wn)

    def _check_inputs_changed(self):
        for junction_name, junction in self._wn.junctions():
            if junction.prev_expected_demand != junction.expected_demand:
                return True
        for tank_name, tank in self._wn.tanks():
            if tank.prev_expected_level != tank.expected_level:
                return True
        for reservoir_name, reservoir in self._wn.reservoirs():
            if reservoir.prev_expected_head != reservoir.expected_head:
                return True

        for pipe_name, pipe in self._wn.pipes():
            if pipe.prev_status != pipe.status:
                return True
        for pump_name, pump in self._wn.pumps():
            if pump.prev_status != pump.status:
                return True
            if pump.prev_speed != pump.speed:
                return True
        for valve_name, valve in self._wn.valves():
            if valve.prev_status != valve.status:
                return True
            if valve.prev_setting != valve.setting:
                return True

        return False

    def _update_previous_inputs(self):
        for junction_name, junction in self._wn.junctions():
            junction.prev_expected_demand = junction.expected_demand
        for tank_name, tank in self._wn.tanks():
            tank.prev_expected_level = tank.expected_level
        for reservoir_name, reservoir in self._wn.reservoirs():
            reservoir.prev_expected_head = reservoir.expected_head

        for pipe_name, pipe in self._wn.pipes():
            pipe.prev_status = pipe.status
        for pump_name, pump in self._wn.pumps():
            pump.prev_status = pump.status
            pump.prev_speed = pump.speed
        for valve_name, valve in self._wn.valves():
            valve.prev_status = valve.status
            valve.prev_setting = valve.setting
