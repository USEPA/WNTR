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
    def __init__(self, water_network=None, PD_or_DD = 'DEMAND DRIVEN'):
        """
        Water Network Simulator class.

        water_network: WaterNetwork object 

        PD_or_DD: string, specifies whether the simulation will be
                  demand driven or pressure driven Options are 'DEMAND
                  DRIVEN' or 'PRESSURE DRIVEN'

        """
        self._wn = water_network

        # Create an internal time controls dictionary. This is needed
        # because the time controls dictionary must be corrected for
        # the given hydraulic timestep. We do not want to modify the
        # water network object in any way.
        self._time_controls = {}
        self._init_time_controls()

        # A dictionary containing pump outage information
        # format is PUMP_NAME: (start time in sec, end time in sec)
        self._pump_outage = {}

        # A dictionary containing information to stop flow from a tank once
        # the minimum head is reached. This dict contains the pipes connected to the tank,
        # the node connected to the tank, and the minimum allowable head in the tank.
        # The index of each link must match the index of it's corresponding node.
        # e.g. : 'Tank-2': {'node_names': ['Junction-1','Junction-3'],
        #                   'link_names': ['Pipe-3', 'Pipe-8'],
        #                   'min_head': 100}
        self._tank_controls = {}

        # A dictionary containing links connected to reservoir
        # 'Pump-2':'Lake-1'
        self._reservoir_links = {}

        if water_network is not None:
            self.init_time_params_from_model()
            self._init_tank_controls()
            self._init_reservoir_links()
            # Pressure driven demand parameters
            if PD_or_DD == 'PRESSURE DRIVEN':
                self._pressure_driven = True
            elif PD_or_DD == 'DEMAND DRIVEN':
                self._pressure_driven = False
            else:
                raise RuntimeError("Argument for specifying demand driven or pressure driven is not recognized. Please use \'PRESSURE DRIVEN\' or \'DEMAND DRIVEN\'.")

        else:
            # Time parameters
            self._sim_start_sec = None
            self._sim_duration_sec = None
            self._pattern_start_sec = None
            self._hydraulic_step_sec = None
            self._pattern_step_sec = None
            self._hydraulic_times_sec = None
            self._report_step_sec = None

    def _init_time_controls(self):
        for link_name in self._wn.time_controls.keys():
            self._time_controls[link_name] = {'open_times':[], 'closed_times':[], 'active_times':[]}
            for t in self._wn.time_controls[link_name]['open_times']:
                self._time_controls[link_name]['open_times'].append(t)
            for t in self._wn.time_controls[link_name]['closed_times']:
                self._time_controls[link_name]['closed_times'].append(t)
            for t in self._wn.time_controls[link_name]['active_times']:
                self._time_controls[link_name]['active_times'].append(t)

    def _init_reservoir_links(self):
        # Creating the _reservoir_links dictionary

        for reserv_name, reserv in self._wn.nodes(Reservoir):
            links_next_to_reserv = self._wn.get_links_for_node(reserv_name)
            for l in links_next_to_reserv:
                self._reservoir_links[l] = reserv_name

    def _init_tank_controls(self):
        # Setting the links and nodes next to tanks, min heads, and max heads

        for tank_name, tank in self._wn.nodes(Tank):

            self._tank_controls[tank_name] = {}
            self._tank_controls[tank_name]['node_names'] = []
            self._tank_controls[tank_name]['link_names'] = []

            # Set minimum head and maximum head
            self._tank_controls[tank_name]['min_head'] = tank.elevation + tank.min_level
            self._tank_controls[tank_name]['max_head'] = tank.elevation + tank.max_level

            # Get links next to the tank
            links_next_to_tank = self._wn.get_links_for_node(tank_name)

            # store the link names and node names
            for link_name in links_next_to_tank:
                link = self._wn.get_link(link_name)
                node_next_to_tank = link.start_node()
                if node_next_to_tank == tank_name:
                    node_next_to_tank = link.end_node()
                self._tank_controls[tank_name]['node_names'].append(node_next_to_tank)
                self._tank_controls[tank_name]['link_names'].append(link_name)

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


    def add_leak(self, *args, **kwargs):
        raise RuntimeError('The interface to the add_leak method has been moved to WaterNetworkModel.')

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

    def link_action(self, link_name, time):
        """
        Check what should happen to a link at a particular time according to the time controls.
    
        Parameters
        ----------
        link_name: string
            Name of link that is being checked for an open or closed status
    
        time: int
            time at which the link is being checked for an open or closed status
            units: Seconds
    
        Returns
        -------
        0 if link should be closed
        1 if link should be opened
        2 if no action should be taken
        """
        link = self._wn.get_link(link_name)
        base_status = False if link.get_base_status() == LinkStatus.closed else True
        if link_name not in self._time_controls:
            if time == 0:
                if base_status:
                    return 2
                else:
                    return 0
            else:
                return 2
        else:
            if time == 0:
                if base_status and time not in self._time_controls[link_name]['closed_times']:
                    return 2
                elif base_status and time in self._time_controls[link_name]['closed_times']:
                    return 0
                elif not base_status and time not in self._time_controls[link_name]['open_times']:
                    return 0
                elif not base_status and time in self._time_controls[link_name]['open_times']:
                    return 2
                else:
                    raise RuntimeError('There appears to be a bug. Please report this error to the developers.')
            else:
                if time in self._time_controls[link_name]['open_times']:
                    return 1
                elif time in self._time_controls[link_name]['closed_times']:
                    return 0
                else:
                    return 2

    def sec_to_timestep(self, sec):
        """
        Convert a number of seconds to a number of hydraulic timesteps.

        Parameters
        ----------
        sec : int
            Seconds to convert to number of hydraulic timesteps.

        Returns
        -------
        number of hydraulic timesteps
        """
        return sec/self._hydraulic_step_sec

    def init_time_params_from_model(self):
        """
        Load simulation time parameters from the water network time options.
        """
        self._check_model_specified()
        try:
            self._sim_start_sec = self._wn.options.start_clocktime
            self._sim_duration_sec = self._wn.options.duration
            self._pattern_start_sec = self._wn.options.pattern_start
            self._hydraulic_step_sec = self._wn.options.hydraulic_timestep
            self._pattern_step_sec = self._wn.options.pattern_timestep
            self._report_step_sec = self._wn.options.report_timestep

        except KeyError:
            KeyError("Water network model used for simulation should contain time parameters. "
                     "Consider initializing the network model data. e.g. Use parser to read EPANET"
                     "inp file into the model.")

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
            end_time = self._sim_duration_sec

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

        demand_times_minutes = range(start_time, end_time + self._hydraulic_step_sec, self._hydraulic_step_sec)
        demand_pattern_values = [base_demand*i for i in pattern_list]

        demand_values = []
        for t in demand_times_minutes:
            # Modulus with the last pattern time to get time within pattern range
            pattern_index = t / self._pattern_step_sec
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

    def _correct_time_controls_for_timestep(self):
        """
        This method should only be used until the simulator can take
        partial timesteps. The idea here is to correct the time
        controls in case the user specified a time between hydraulic
        timesteps. If so, the time control is delayed until the
        following hydraulic timestep. For example, suppose a user
        specified this control in the inp file:

             LINK Pipe-12 CLOSED AT TIME 8:35

        Also suppose that the hydraulic timestep is 1 hour. This
        control would be modified so that Pipe-12 is closed at 9:00.
        """
        for link_name in self._time_controls.keys():
            assert type(self._hydraulic_step_sec) == int
            for i in xrange(len(self._time_controls[link_name]['open_times'])):
                time = self._time_controls[link_name]['open_times'][i]
                assert type(time) == int
                if time%self._hydraulic_step_sec != 0:
                    new_time = (time/self._hydraulic_step_sec + 1)*self._hydraulic_step_sec
                    self._time_controls[link_name]['open_times'][i] = new_time

            for i in xrange(len(self._time_controls[link_name]['closed_times'])):
                time = self._time_controls[link_name]['closed_times'][i]
                assert type(time) == int
                if time%self._hydraulic_step_sec != 0:
                    new_time = (time/self._hydraulic_step_sec + 1)*self._hydraulic_step_sec
                    self._time_controls[link_name]['closed_times'][i] = new_time

            for i in xrange(len(self._time_controls[link_name]['active_times'])):
                time = self._time_controls[link_name]['active_times'][i]
                assert type(time) == int
                if time%self._hydraulic_step_sec != 0:
                    new_time = (time/self._hydraulic_step_sec + 1)*self._hydraulic_step_sec
                    self._time_controls[link_name]['active_times'][i] = new_time

