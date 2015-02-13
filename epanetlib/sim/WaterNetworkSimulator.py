import numpy as np
from epanetlib.network.WaterNetworkModel import Junction
from epanetlib.network.WaterNetworkModel import WaterNetworkModel
from scipy.optimize import fsolve
import math

class WaterNetworkSimulator(object):
    def __init__(self, water_network=None):
        """
        Water Network Simulator class.

        water_network: WaterNetwork object

        """
        self._wn = water_network
        if water_network is not None:
            self.init_time_params_from_model()

    def set_water_network_model(self, water_network):
        """
        Set the WaterNetwork model for the simulator.

        Parameters
        ---------
        water_network : WaterNetwork object
            Water network model object
        """
        self._wn = water_network
        self.init_time_params_from_model()

    def _check_model_specified(self):
        assert (isinstance(self._wn, WaterNetworkModel)), "Water network model has not been set for the simulator" \
                                                      "use method set_water_network_model to set model."

    def min_to_timestep(self, min):
        """
        Convert minutes to hydraulic timestep.

        Parameters
        --------
        min : int
            Minutes to convert to hydraulic timestep.

        Return
        -------
        hydraulic timestep
        """
        return min/self._hydraulic_step_min

    def init_time_params_from_model(self):
        self._check_model_specified()
        try:
            self._sim_start_min = self._wn.time_options['START CLOCKTIME']
            self._sim_end_min = self._wn.time_options['DURATION'] + self._wn.time_options['HYDRAULIC TIMESTEP']
            self._pattern_start_min = self._wn.time_options['PATTERN START']
            self._hydraulic_step_min = self._wn.time_options['HYDRAULIC TIMESTEP']
            self._pattern_step_min = self._wn.time_options['PATTERN TIMESTEP']
            self._hydraulic_times_min = range(self._sim_start_min, self._sim_end_min, self._hydraulic_step_min)
        except KeyError:
            KeyError("Water network model used for simulation should contain time parameters. "
                     "Consider initializing the network model data. e.g. Use parser to read EPANET"
                     "inp file into the model.")

    def get_node_demand(self, node_name, start_time=None, end_time=None):
        """
        Calculates the demands at a node based on the demand pattern.

        Parameters
        ---------
        node_name : string
            Name of the node.
        start_time : float
            The start time of the demand values requested. Default is 0 min.
        end_time : float
            The end time of the demand values requested. Default is the simulation end time.

        Return
        -------
        demand_list : dictionary of floats indexed by floats
            A dictionary of demand values indexed by each hydraulic timestep(min) between
            start_time and end_time.
        """

        self._check_model_specified()

        # Set start and end time for demand values to be returned
        if start_time is None:
            start_time = 0
        if end_time is None:
            end_time = self._sim_end_min

        # Get node object
        try:
            node = self._wn.nodes[node_name]
        except KeyError:
            raise KeyError("Not a valid node name")
        # Make sure node object is a Junction
        assert(isinstance(node, Junction)), "Demands can only be calculated for Junctions"
        # Calculate demand pattern values
        base_demand = node.base_demand
        pattern_name = node.demand_pattern_name
        if pattern_name is None:
            pattern_name = self._wn.options['PATTERN']
        pattern_list = self._wn.patterns[pattern_name]
        pattern_length = len(pattern_list)
        #offset = self._wn.time_options['PATTERN START']

        demand_times_minutes = range(start_time, end_time, self._hydraulic_step_min)
        demand_pattern_values = [base_demand*i for i in pattern_list]

        demand_values = []
        for t in demand_times_minutes:
            # Modulus with the last pattern time to get time within pattern range
            pattern_index = t / self._pattern_step_min
            # Modulus with the pattern time step to get the pattern index
            pattern_index = pattern_index % pattern_length
            demand_values.append(demand_pattern_values[pattern_index])

        return demand_values
