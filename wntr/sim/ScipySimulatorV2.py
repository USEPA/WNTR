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
        self.solve_step = {}

    def run_sim(self):
        """
        Method to run an extended period simulation
        """

        start_run_sim_time = time.time()

        model = ScipyModel(self._wn)
        model.initialize_results_dict()

        self.solver = NewtonSolverV2()

        results = NetResults()
        results.time = np.arange(0, self._sim_duration_sec+self._hydraulic_step_sec, self._hydraulic_step_sec)

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
        self.prep_time_before_main_loop - start_main_loop_time - start_run_sim_time

        while self._wn.sim_time_sec <= self._wn.options.duration:
            print self._wn.sim_time_sec
            model.update_junction_demands(self._demand_dict)
            model.set_network_status_by_id()
            model.set_jacobian_constants()
            start_solve_step = time.time()
            [self._X,num_iters] = self.solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            end_solve_step = time.time()
            X_init = copy.copy(self._X)
            self.solve_step[int(self._wn.sim_time_sec/self._wn.options.hydraulic_timestep)] = end_solve_step - start_solve_step
            model.save_results(self._X, results)
            self._wn.sim_time_sec += self._wn.options.hydraulic_timestep
            if self._wn.sim_time_sec <= self._wn.options.duration:
                model.update_tank_heads(self._X)

        model.get_results(results)
        return results

    def solve_hydraulics(self, x0, net_status):
        """
        Method to solve the hydraulic equations given the network status

        Parameters
        ----------
        net_status: a NetworkStatus object
        """

        self.solver.solve(self._hydraulic_equations, self.get_jacobian, x0)

    def _get_demand_dict(self):

        # Number of hydraulic timesteps
        self._n_timesteps = int(round(self._wn.options.duration / self._wn.options.hydraulic_timestep)) + 1

        # Get all demand for complete time interval
        self._demand_dict = {}
        for node_name, node in self._wn.nodes():
            if isinstance(node, Junction):
                demand_values = self.get_node_demand(node_name)
                for t in range(self._n_timesteps):
                    self._demand_dict[(node_name, t)] = demand_values[t]
            else:
                for t in range(self._n_timesteps):
                    self._demand_dict[(node_name, t)] = 0.0
