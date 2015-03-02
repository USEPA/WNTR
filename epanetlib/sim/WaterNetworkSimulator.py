# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 10:07:42 2015

@author: aseth
"""

"""
QUESTIONS
- Should WaterNetworkSimulator base class be abstract?
- Should a WNM be a required attribute for derived classes?
- Requirements on a WNM for being able to simulate.
- Does the Pyepanet simulator read info from water network object? Or do we simply write an inp file?
- Whats the interface to pyepanet simulator? User can provide either a WNM or an inp_file_name?
"""

"""
TODO
1. Use in_edges and out_edges to write node balances on the pyomo model.
2. Parse valve settings. Fix usage.
3. Check for rule based controls in pyomo model and throw an exception.
4. _check_model_specified has to be extended to check for parameters in the model that must be specified.
5.
"""


import numpy as np
from epanetlib.network.WaterNetworkModel import *
from scipy.optimize import fsolve
import math
from NetworkResults import NetResults
import pandas as pd
import time


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

    def is_link_open(self,link_name,time):
        link = self._wn.get_link(link_name)
        if link_name not in self._wn.time_controls:
            return False if link.get_base_status() == 'CLOSED' else True
        else:
            open_times = self._wn.time_controls[link_name]['open_times']
            closed_times = self._wn.time_controls[link_name]['closed_times']
            if time<open_times[0] and time<closed_times[0]:
                return False if link.get_base_status() == 'CLOSED' else True
            else:

                #Check open times
                left = 0
                right = len(open_times)-1
                if time >= open_times[right]:
                    min_open = time-open_times[right];
                elif time < open_times[left]:
                    min_open = float("inf");
                else:
                    middle = int(0.5*(right+left))
                    while(right-left>1):
                        if(open_times[middle]>time):
                            right = middle
                        else:
                            left = middle
                        middle = int(0.5*(right+left))
                    min_open = time-open_times[left];

                #Check Closed times
                left = 0
                right = len(closed_times)-1
                if time >= closed_times[right]:
                    min_closed = time-closed_times[right]
                elif time < closed_times[left]:
                    min_closed = float("inf")
                else:
                    middle = int(0.5*(right+left))
                    while(right-left>1):
                        if(closed_times[middle]>time):
                            right = middle
                        else:
                            left = middle
                        middle = int(0.5*(right+left))
                    min_closed = time-closed_times[left];
                """
                min_open = float("inf")
                for t in open_times:
                    if time>=t and min_open>=time-t:
                        min_open = time-t
                min_closed = float("inf")
                for t in closed_times:
                    if time>=t and min_closed>=time-t:
                        min_closed = time-t
                """
                return True if min_open<min_closed else False

    def min_to_timestep(self, min):
        """
        Convert minutes to hydraulic timestep.

        Parameters
        -------
        min : int
            Minutes to convert to hydraulic timestep.

        Return
        -------
        hydraulic timestep
        """
        return min/self._hydraulic_step_min

    def init_time_params_from_model(self):
        """
        Load simulation time parameters from the water network time options.
        """
        self._check_model_specified()
        try:
            self._sim_start_min = self._wn.time_options['START CLOCKTIME']
            self._sim_duration = self._wn.time_options['DURATION']
            self._pattern_start_min = self._wn.time_options['PATTERN START']
            self._hydraulic_step_min = self._wn.time_options['HYDRAULIC TIMESTEP']
            self._pattern_step_min = self._wn.time_options['PATTERN TIMESTEP']
            self._hydraulic_times_min = range(0, self._sim_duration, self._hydraulic_step_min)
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
        demand_list : list of floats
           A list of demand values at each hydraulic timestep
        """

        self._check_model_specified()

        # Set start and end time for demand values to be returned
        if start_time is None:
            start_time = 0
        if end_time is None:
            end_time = self._sim_duration

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
            pattern_name = self._wn.options['PATTERN']
        pattern_list = self._wn.get_pattern(pattern_name)
        pattern_length = len(pattern_list)
        offset = self._wn.time_options['PATTERN START']

        assert(offset == 0.0), "Only 0.0 Pattern Start time is currently supported. "

        demand_times_minutes = range(start_time, end_time + self._hydraulic_step_min, self._hydraulic_step_min)
        demand_pattern_values = [base_demand*i for i in pattern_list]

        demand_values = []
        for t in demand_times_minutes:
            # Modulus with the last pattern time to get time within pattern range
            pattern_index = t / self._pattern_step_min
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
        else:
            raise RuntimeError('Node name ' + name + ' was not recognised as a junction, tank, or reservoir.')

class PyEpanetSimulator(WaterNetworkSimulator):
    """
    Simulator class thats a wrapper around PyEPANET
    """
    try:
        from epanetlib import pyepanet
    except ImportError:
        raise ImportError('Could not import PyEPANET')

    def __init__(self, wn=None, inp_file_name=None):
        """
        Simulator object to be used for running pyepanet simulations.

        Optional Parameters
        ---------
        AT LEAST ONE OF THESE PARAMETERS MUST BE SPECIFIED
        wn : WaterNetworkModel
            A water network
        inp_file_name: string
            Epanet inp file name
        """
        WaterNetworkSimulator.__init__(self, wn)

    def run_sim(self, ):
        pass
