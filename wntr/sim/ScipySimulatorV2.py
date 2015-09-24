from wntr import *
import numpy as np
import scipy.sparse as sparse
import warnings
from WaterNetworkSimulator import *
from ScipyModel import *
from wntr.network.WaterNetworkModel import *
from NewtonSolverV2 import *
from NetworkResults import *

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

        WaterNetworkSimulator.__init__(self, wn)
        self._get_demand_dict()

    def run_sim(self):
        """
        Method to run an extended period simulation
        """

        model = ScipyModel(self._wn)
        model.initialize_results_dict()

        self.solver = NewtonSolverV2()

        results = NetResults()
        self._load_general_results(results)

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

        while self._wn.time_sec <= self._wn.time_options['DURATION']:
            print self._wn.time_sec
            model.set_network_status_by_id()
            model.set_jacobian_constants()
            [self._X,num_iters] = self.solver.solve(model.get_hydraulic_equations, model.get_jacobian, X_init)
            model.save_results(self._X, results)
            self._wn.time_sec += self._wn.time_options['HYDRAULIC TIMESTEP']
            if self._wn.time_sec <= self._wn.time_options['DURATION']:
                model.update_network(self._X, self._demand_dict)

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
        self._n_timesteps = int(round(self._wn.time_options['DURATION'] / self._wn.time_options['HYDRAULIC TIMESTEP'])) + 1

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

    def _load_general_results(self, results):
        """
        Load general simulation options into the results object.

        Parameters
        ----------
        results : NetworkResults object
        """
        # Load general results
        results.network_name = self._wn.name
        results.time = pd.timedelta_range(start='0 minutes',
                                          end=str(self._sim_duration_sec) + ' seconds',
                                          freq=str(self._hydraulic_step_sec/60) + 'min')

