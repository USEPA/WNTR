import numpy as np
import warnings
from wntr.network.WaterNetworkModel import *
from scipy.optimize import fsolve
import math
from NetworkResults import NetResults
import time
import copy

class WaterNetworkSimulator(object):
    def __init__(self, water_network=None, pressure_driven=False):
        """
        Water Network Simulator class.

        water_network: WaterNetwork object 

        pressure_dependent: bool 
            Specifies whether the simulation will be demand-driven or
            pressure-driven. True means the simulation will be
            pressure-driven.

        """
        self._wn = water_network
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
            demand_values.append(demand_pattern_values[pattern_index])

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
