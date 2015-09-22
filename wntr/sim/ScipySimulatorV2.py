from wntr import *
import numpy as np
import scipy.sparse as sparse
import warnings


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

        WaterNetworkSimulator.__init__(wn)
        self._initialize_results_dict()


    def run_sim(self):
        """
        Method to run an extended period simulation
        """

        model = ScipyModel(self._wn)
        self.solver = NewtonSolver()

        results = NetRestuls()
        self._load_general_results(results)

        # Initialize X
        # Vars will be ordered:
        #    1.) head
        #    2.) demand
        #    3.) flow
        self.head0 = np.zeros(self.num_nodes)
        self.demand0 = np.zeros(self.num_nodes)
        self.flow0 = np.zeros(self.num_links)
        self._initialize_head(net_status)
        self._initialize_demand(net_status)
        self._initialize_flow(net_status)
        self._X_init = np.concatenate((self.head0, self.demand0, self.flow0))

        while self._wn.time_sec <= self._wn.time_options['DURATION']:
            events_to_make_changes = []
            events_to back_up = []
            for event in event_list:
                status = event.EventNeeedsToMakeChanges()
                if status == SimulationEventStatus.ChangesRequired:
            model.set_network_statuses_by_id()
            self.set_jacobian_constants()
            self._X = self.solve_hydraulics(net_status)
            results = self.save_results(self._X)
            net_status.update_network_status(results)

    def solve_hydraulics(self, x0, net_status):
        """
        Method to solve the hydraulic equations given the network status

        Parameters
        ----------
        net_status: a NetworkStatus object
        """

        self.solver.solve(self._hydraulic_equations, self.get_jacobian, x0)

    def _initialize_flow(self, net_status):
        for link_name in net_status.links_closed:
            self.flow0[self._link_name_to_id[link_name]] = 0.0

    def _initialize_head(self, net_status):
        for node_id in self._junction_ids:
            self.head0[node_id] = self.node_elevations[node_id]
        for tank_name in net_status.tank_heads.keys():
            tank_id = self._node_name_to_id[tank_name]
            self.head0[tank_id] = net_status.tank_heads[tank_name]
        for reservoir_name in net_status.reservoir_heads.keys():
            reservoir_id = self._node_name_to_id[reservoir_name]
            self.head0[reservoir_id] = net_status.reservoir_heads[reservoir_name]

    def _initialize_demand(self, net_status):
        for junction_name in net_status.expected_demands.keys():
            junction_id = self._node_name_to_id[junction_name]
            self.demand0[junction_id] = net_status.expected_demands[junction_name]
            

