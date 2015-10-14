#-*- coding: utf-8 -*-
"""
Created on Fri Jan 23 10:07:42 2015

@author: aseth
"""

"""
QUESTIONS
- Should WaterNetworkSimulator base class be abstract?
- Should a WNM be a required attribute for derived classes?
- Requirements on a WNM for being able to simulate.
"""

import numpy as np
import warnings
from wntr.network.WaterNetworkModel import *
from scipy.optimize import fsolve
import math
from NetworkResults import NetResults
import time
import copy


class WaterNetworkSimulator(object):
    def __init__(self, water_network=None, pressure_dependent=False):
        """
        Water Network Simulator class.

        water_network: WaterNetwork object 

        pressure_dependent: bool 
            Specifies whether the simulation will be demand-driven or
            pressure-driven. True means the simulation will be
            pressure-driven.

        """
        self._wn = water_network
        if pressure_dependent:
            self.pressure_dependent = True
        else:
            self.pressure_dependent = False

        # A dictionary containing links connected to reservoir
        # 'Pump-2':'Lake-1'
        self._reservoir_links = {}

        if water_network is not None:
            self._init_reservoir_links()
            # Pressure driven demand parameters

    def _init_reservoir_links(self):
        # Creating the _reservoir_links dictionary

        for reserv_name, reserv in self._wn.nodes(Reservoir):
            links_next_to_reserv = self._wn.get_links_for_node(reserv_name)
            for l in links_next_to_reserv:
                self._reservoir_links[l] = reserv_name

    def add_pump_outage(self, pump_name, start_time, end_time):
        """
        Add time of pump outage for a particular pump.

        Parameters
        ----------

        pump_name: String
            Name of the pump.
        start_time: float
            Start time of the pump outage in seconds.
        end_time: float
            End time of the pump outage in seconds.

        Examples
        --------
        >>> sim.add_pump_outage('PUMP-3845', 11*3600, 26*3600)

        """
        if self._wn is None:
            raise RuntimeError("Pump outage time cannot be defined before a network object is"
                               "defined in the simulator.")


        # Check if pump_name is valid
        try:
            pump = self._wn.get_link(pump_name)
        except KeyError:
            raise KeyError(pump_name + " is not a valid link in the network.")
        if not isinstance(pump, Pump):
            raise RuntimeError(pump_name + " is not a valid pump in the network.")

        # Add the pump outage information (start time and end time) to the _pump_outage dictionary
        if pump_name in self._pump_outage.keys():
            warnings.warn("Pump name " + pump_name + " already has a pump outage time defined."
                                                     " Old time range is being overridden.")
            self._pump_outage[pump_name] = (start_time, end_time)
        else:
            self._pump_outage[pump_name] = (start_time, end_time)

    def all_pump_outage(self, start_time, end_time):
        """
        Add time of outage for all pumps in the network.

        Parameters
        ----------
        start_time: float
            Start time of the pump outage in seconds.
        end_time: float
            End time of the pump outage in seconds.

        Examples
        --------
        >>> sim.add_pump_outage('PUMP-3845', 11*3600, 26*3600)

        """

        if self._wn is None:
            raise RuntimeError("All pump outage time cannot be defined before a network object is"
                               "defined in the simulator.")

        # Add the pump outage information (start time and end time) to the _pump_outage dictionary
        for pump_name, pump in self._wn.links(Pump):
            if pump_name in self._pump_outage.keys():
                warnings.warn("Pump name " + pump_name + " already has a pump outage time defined."
                                                         " Old time range is being overridden.")
                self._pump_outage[pump_name] = (start_time, end_time)
            else:
                self._pump_outage[pump_name] = (start_time, end_time)


    def set_water_network_model(self, water_network):
        """
        Set the WaterNetwork model for the simulator.

        Parameters
        ----------
        water_network : WaterNetwork object
            Water network model object
        """
        self._wn = water_network
        self.init_time_params_from_model()
        self._init_tank_controls()

    def _check_model_specified(self):
        assert (isinstance(self._wn, WaterNetworkModel)), "Water network model has not been set for the simulator" \
                                                          "use method set_water_network_model to set model."

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

        self._check_model_specified()

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

    def _verify_conditional_controls_for_tank(self):
        for link_name in self._wn.conditional_controls:
            for control in self._wn.conditional_controls[link_name]:
                for i in self._wn.conditional_controls[link_name][control]:
                    node_name = i[0]
                    node = self._wn.get_node(node_name)
                    assert(isinstance(node, Tank)), "Scipy simulator only supports conditional controls on Tank level."

