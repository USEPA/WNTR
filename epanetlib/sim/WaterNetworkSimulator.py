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
"""

import numpy as np
import warnings
from epanetlib.network.WaterNetworkModel import *
from scipy.optimize import fsolve
import math
from NetworkResults import NetResults
import pandas as pd
import time
import copy


class WaterNetworkSimulator(object):
    def __init__(self, water_network=None, PD_or_DD = 'DEMAND DRIVEN'):
        """
        Water Network Simulator class.

        water_network: WaterNetwork object
        PD_or_DD: string, specifies whether the simulation will be demand driven or pressure driven
                  Options are 'DEMAND DRIVEN' or 'PRESSURE DRIVEN'

        """
        self._wn = copy.deepcopy(water_network)

        # A dictionary containing pump outage information
        # format is PUMP_NAME: (start time in sec, end time in sec)
        self._pump_outage = {}

        # A dictionary containg leak time information
        # format is LEAK_NAME: (start time in sec, end time in sec)
        self._leak_times = {}

        # A dictionary containing leak characteristics
        # format is LEAK_NAME: {'original_pipe':copy_of_original_pipe, 'leak_area':leak_area, 'leak_discharge_coeff':leak_discharge_coeff, 'shutoff_valve_loc':shutoff_valve_loc}
        self._leak_info = {}

        # A dictionary containing pipe names and associated leak names
        # format is PIPE_NAME: LEAK_NAME
        self._pipes_with_leaks = {}

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

            #if 'NOMINAL PRESSURE' in self._wn.options:
            #    self._PF = self._wn.options['NOMINAL PRESSURE']
            #else:
            #    self._PF = None
            #if 'MINIMUM PRESSURE' in self._wn.options:
            #    self._P0 = self._wn.options['MINIMUM PRESSURE']
            #else:
            #    self._P0 = 0 # meters head
        else:
            # Time parameters
            self._sim_start_sec = None
            self._sim_duration_sec = None
            self._pattern_start_sec = None
            self._hydraulic_step_sec = None
            self._pattern_step_sec = None
            self._hydraulic_times_sec = None
            self._report_step_sec = None

    def _init_reservoir_links(self):

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
            self._tank_controls[tank_name]['min_head'] = tank.elevation #+ tank.min_level
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

    def timedelta_to_sec(self, timedelta):
        """
        Converts timedelta to seconds.

        Parameters
        ----------
        timedelta : Pandas tmedelta object.

        Returns
        -------
        seconds as integer
        """

        return int(timedelta.components.days*24*60*60 + timedelta.components.hours*60*60 + timedelta.components.minutes*60 + timedelta.components.seconds)

    def add_pump_outage(self, pump_name, start_time, end_time):
        """
        Add time of pump outage for a particular pump.

        Parameters
        ----------

        pump_name: String
            Name of the pump.
        start_time: String
            Start time of the pump outage. Pandas Timedelta format: e.g. '0 days 00:00:00'
        end_time: String
            End time of the pump outage. Pandas Timedelta format: e.g. '0 days 05:00:00'

        Examples
        --------
        >>> sim.add_pump_outage('PUMP-3845', pd.Timedelta('0 days 11:00:00'), pd.Timedelta('1 days 02:00:00'))

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

        # Check if atart time and end time are valid
        try:
            start = pd.Timedelta(start_time)
            end = pd.Timedelta(end_time)
        except RuntimeError:
            raise RuntimeError("The format of start or end time is not valid Pandas Timedelta format.")

        start_sec = self.timedelta_to_sec(start)
        end_sec = self.timedelta_to_sec(end)

        if pump_name in self._pump_outage.keys():
            warnings.warn("Pump name " + pump_name + " already has a pump outage time defined."
                                                     " Old time range is being overridden.")
            self._pump_outage[pump_name] = (start_sec, end_sec)
        else:
            self._pump_outage[pump_name] = (start_sec, end_sec)

    def all_pump_outage(self, start_time, end_time):
        """
        Add time of outage for all pumps in the network.

        Parameters
        ----------
        start_time: String
            Start time of the pump outage. Pandas Timedelta format: e.g. '0 days 00:00:00'
        end_time: String
            End time of the pump outage. Pandas Timedelta format: e.g. '0 days 05:00:00'

        Examples
        --------
        >>> sim.add_pump_outage('PUMP-3845', pd.Timedelta('0 days 11:00:00'), pd.Timedelta('1 days 02:00:00'))

        """

        if self._wn is None:
            raise RuntimeError("All pump outage time cannot be defined before a network object is"
                               "defined in the simulator.")

        #if 'NOMINAL PRESSURE' not in self._wn.options:
        #    raise RuntimeError("Pump outage analysis requires nominal pressure to be provided"
        #                       "for the water network model.")

        try:
            start = pd.Timedelta(start_time)
            end = pd.Timedelta(end_time)
        except RuntimeError:
            raise RuntimeError("The format of start or end time is not valid Pandas Timedelta format.")

        start_sec = self.timedelta_to_sec(start)
        end_sec = self.timedelta_to_sec(end)

        for pump_name, pump in self._wn.links(Pump):
            if pump_name in self._pump_outage.keys():
                warnings.warn("Pump name " + pump_name + " already has a pump outage time defined."
                                                         " Old time range is being overridden.")
                self._pump_outage[pump_name] = (start_sec, end_sec)
            else:
                self._pump_outage[pump_name] = (start_sec, end_sec)

    def add_leak(self, leak_name, pipe_name, leak_area = None, leak_diameter = None, leak_discharge_coeff = 0.75, start_time = '0 days 00:00:00', fix_time = None, shutoff_valve_loc = 'ISOLATE'):
        """
        Method to add a leak to the simulation. Leaks are modeled by:

        Q = leak_discharge_coeff*leak_area*sqrt(2*g*h)
        where:
        
        Q is the volumetric flow rate of water out of the leak
        g is the acceleration due to gravity
        h is the gauge head at the leak, P_g/(rho*g); Note that this is not the hydraulic head (P_g + elevation)

        Parameters
        ----------
        leak_name: string
           Name of the leak
        pipe_name: string
           Name of the pipe where the leak ocurrs.
           Assumes the leak ocurrs halfway between nodes.
        leak_area: float
           Area of the leak in m^2. Either the leak area or the leak diameter must be specified, but not both.
        leak_diameter: float
           Diameter of the leak in m. The area of the leak is calculated with leak_diameter assuming the leak is in the shape of a circle.
           Either the leak area or the leak diameter must be specified, but not both.
        leak_discharge_coeff: float
           Leak discharge coefficient; Takes on values between 0 and 1
        start_time: string
           Start time of the leak. Pandas Timedelta format: e.g. '0 days 00:00:00'. Default is the start of the simulation.
        fix_time: string
           Time at which the leak is fixed. Pandas Timedelta format: e.g. '0 days 05:00:00'. Default is that the leak does not get 
           fixed during the simulation.
        shutoff_valve_loc: string
           Location of pipe shutoff valve. Options are 'START_NODE', 'END_NODE', or 'ISOLATE'. 'START_NODE' indicates that the 
           shutoff valve is between the start node and the leak. 'END_NODE' indicates that the shutoff valve is between the leak 
           and the end node. 'ISOLATE' indicates that there is a shutoff valve on both sides of the leak, so a closed pipe means 
           an isolated leak. The default is 'ISOLATE'. This is used for time controls and conditional controls. If tank levels
           fall too low, the link closest to the tank is closed.
        """

        # Check if water network is specified
        if self._wn is None:
            raise RuntimeError("Leaks cannot be defined before a network object is"
                               "defined in the simulator.")

        # Check if pipe_name is valid
        try:
            pipe = self._wn.get_link(pipe_name)
        except KeyError:
            raise KeyError(pipe_name + " is not a valid link in the network.")
        if not isinstance(pipe, Pipe):
            raise RuntimeError(pipe_name + " is not a valid pipe in the network.")

        # Check if start time and end time are valid
        try:
            start = pd.Timedelta(start_time)
            end = pd.Timedelta(fix_time)
        except RuntimeError:
            raise RuntimeError("The format of start or fix time is not valid Pandas Timedelta format.")
        start_sec = self.timedelta_to_sec(start)
        end_sec = self.timedelta_to_sec(end)

        # Set leak_area if leak_diameter was passed as an argument
        if leak_diameter is not None:
            if leak_area is not None:
                raise RuntimeError('When trying to add a leak, you may only specify the area or diameter, not both.')
            else:
                leak_area = math.pi/4.0*leak_diameter**2
        elif leak_area is None:
            raise RuntimeError('When trying to add a leak, you must specify either the area or the diameter.')

        # Ensure pipe does not already have a leak and leak does not already exist
        if pipe_name in self._pipes_with_leaks.keys():
            warning.warn('Pipe '+pipe_name+' already has a leak. Old leak is being overridden.')
            tmp_leak_name = self._pipes_with_leaks[pipe_name]
            self._leak_times.pop(tmp_leak_name)
            self._leak_info.pop(tmp_leak_name)
        if leak_name in self._pipes_with_leaks.values():
            warnings.warn('Leak '+leak_name+' is already associated with a pipe. Old pipe will no longer have a leak.')
            for tmp_pipe_name, tmp_leak_name in self._pipes_with_leaks.iteritems():
                if tmp_leak_name == leak_name:
                    self._pipes_with_leaks.pop(tmp_pipe_name)


        # Store leak information
        self._pipes_with_leaks[pipe_name] = leak_name
        self._leak_times[leak_name] = (start_sec, end_sec)
        self._leak_info[leak_name] = {'original_pipe':copy.deepcopy(pipe), 'leak_area':leak_area, 'leak_discharge_coeff':leak_discharge_coeff, 'shutoff_valve_loc':shutoff_valve_loc.upper()}

        # Check if the leak area is larger than the pipe area
        orig_pipe_area = math.pi/4.0*pipe.diameter**2
        if leak_area > orig_pipe_area:
            raise RuntimeError('You specified a leak area (or diameter) that is larger than the area (or diameter) of the original pipe')

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

    def is_link_open(self, link_name, time):
        """
        Check if a link is open or closed.

        Parameters
        ----------
        link_name: string
            Name of link that is being checked for an open or closed status

        time: int or float ???
            time at which the link is being checked for an open or closed status
            units: Seconds

        Returns
        -------
        True if the link is open
        False if the link is closed
        """
        link = self._wn.get_link(link_name)
        base_status = False if link.get_base_status() == 'CLOSED' else True
        if link_name not in self._wn.time_controls:
            return base_status
        else:
            open_times = self._wn.time_controls[link_name]['open_times']
            closed_times = self._wn.time_controls[link_name]['closed_times']
            if len(open_times) == 0 and len(closed_times) == 0:
                return base_status
            if len(open_times) == 0 and len(closed_times) != 0:
                return base_status if time < closed_times[0] else False
            elif len(open_times) != 0 and len(closed_times) == 0:
                return base_status if time < open_times[0] else True
            elif time < open_times[0] and time < closed_times[0]:
                return base_status
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
                    min_closed = time-closed_times[left]

                return True if min_open < min_closed else False


    def give_link_status(self,link_name,time):
        link = self._wn.get_link(link_name)
    
        base_status = link.get_base_status()
        if link_name not in self._wn.time_controls:
            return base_status
        else:
            count_base = 1
            time_diff_values = dict()
            time_controls = self._wn.time_controls[link_name]
            for key in time_controls.keys():
                list_times = self._wn.time_controls[link_name][key]
                time_diff_values[key] = float("inf");
                if list_times:
                    if time < list_times[0]:
                        count_base+=1
                    else:
                        left = 0
                        right = len(list_times)-1
                        if time >= list_times[right]:
                            min_diff = time-list_times[right];
                        elif time < list_times[left]:
                            min_diff = float("inf");
                        else:
                            middle = int(0.5*(right+left))
                            while(right-left>1):
                                if(list_times[middle]>time):
                                    right = middle
                                else:
                                    left = middle
                                middle = int(0.5*(right+left))
                            min_diff = time-list_times[left]
                        time_diff_values[key] = min_diff
            
            if count_base>=len(time_controls.keys()):
                return base_status
            else:
                name_list = min(time_diff_values, key=lambda k: time_diff_values[k]) 
                return name_list.split('_')[0].upper()
                    

    def sec_to_timestep(self, sec):
        """
        Convert seconds to hydraulic timestep.

        Parameters
        ----------
        sec : int
            Seconds to convert to hydraulic timestep.

        Returns
        -------
        hydraulic timestep
        """
        return sec/self._hydraulic_step_sec

    def init_time_params_from_model(self):
        """
        Load simulation time parameters from the water network time options.
        """
        self._check_model_specified()
        try:
            self._sim_start_sec = self._wn.time_options['START CLOCKTIME']
            self._sim_duration_sec = self._wn.time_options['DURATION']
            self._pattern_start_sec = self._wn.time_options['PATTERN START']
            self._hydraulic_step_sec = self._wn.time_options['HYDRAULIC TIMESTEP']
            self._pattern_step_sec = self._wn.time_options['PATTERN TIMESTEP']
            self._report_step_sec = self._wn.time_options['REPORT TIMESTEP']
            # I don't think that this line is used: self._hydraulic_times_sec = np.linspace(0, self._sim_duration_sec, self._sim_duration_sec/self._hydraulic_step_sec)

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
            pattern_name = self._wn.options['PATTERN']
        pattern_list = self._wn.get_pattern(pattern_name)
        pattern_length = len(pattern_list)
        offset = self._wn.time_options['PATTERN START']

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
