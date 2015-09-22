# -*- coding: utf-8 -*-
"""
Classes and methods used for specifying a water network model.
"""

"""
Created on Fri Jan 23 10:07:42 2015

@author: aseth
"""

"""
QUESTIONS
1. Are the start end node attributes of a link only stored in the networkx graph?
2. Node coordinates are only stored in the graph. Therefore, set_node_coordinates is a method on the WaterNetworkModel.
3. Getting connectivity for a node using get_links_for_node. Okay name?
"""

import copy
import networkx as nx
import math
from scipy.optimize import fsolve
from wntr.units import convert
from wntr.misc import *
import wntr.network
import pandas as pd
import numpy as np

class WaterNetworkModel(object):

    """
    The base water network model class.
    """
    def __init__(self, inp_file_name = None):
        """
        Examples
        ---------
        >>> wn = WaterNetworkModel()
        
        """

        # Network name
        self.name = None
        self.time_sec = 0.0

        # Initialize Network size parameters
        self._num_junctions = 0
        self._num_reservoirs = 0
        self._num_tanks = 0
        self._num_pipes = 0
        self._num_pumps = 0
        self._num_valves = 0

        # Initialize node and link lists
        # Dictionary of node or link objects indexed by their names
        self._nodes = {}
        self._links = {}
        self._curves = {}

        # Initialize pattern and curve dictionaries
        # Dictionary of pattern or curves indexed by their names
        self._patterns = {}

        # Initialize Options dictionaries
        self.time_options = {}
        self.options = {}
        self.reaction_options = {}

        # Time controls are saved as a dictionary as follows:
        # {'Link name': {'open_times': [1, 5, ...], 'closed_times': [3, 7, ...], 'active_times':[1,4,7,...]}},
        # where times are in seconds
        self.time_controls = {}

        # Conditional controls are saved as a dictionary as follows:
        # {'Link name': {'open_below': [('node_name', level_value), ...],
        #                'open_above': [('node_name', level_value), ...],
        #                'closed_below': [('node_name', level_value), ...],
        #                'closed_above': [('node_name', level_value), ...]}}
        self.conditional_controls = {}

        # Name of pipes that are check valves
        self._check_valves = []

        # NetworkX Graph to store the pipe connectivity and node coordinates
        self._graph = nx.MultiDiGraph(data=None)

        # A dictionary containing pipe names and associated leak names
        # format is PIPE_NAME: LEAK_NAME
        self._pipes_with_leaks = {}

        if inp_file_name:
            parser = wntr.network.ParseWaterNetwork()
            parser.read_inp_file(self, inp_file_name)

    def copy(self):
        
        r"""Copy a water network object

        Returns
        -------
        A copy of the water network

        Examples
        --------
        >>> wn = WaterNetwork()
        >>> wn2 = wn.copy()
        """
        return copy.deepcopy(self)

    def get_node(self, name):
        """
        Returns node object of a provided name

        Parameters
        ----------
        name : string
            name of the node
        """
        return self._nodes[name]

    def get_link(self, name):
        """
        Returns link object of a provided name

        Parameters
        ----------
        name : string
            name of the link
        """
        return self._links[name]

    def get_curve(self, name):
        """
        Returns curve object of a provided name

        Parameters
        ----------
        name : string
            name of the curve
        """
        return self._curves[name]

    def get_pattern(self, name):
        """
        Returns pattern object of a provided name

        Parameters
        ----------
        name : string
            name of the pattern
        """
        return self._patterns[name]

    def add_junction(self, name, base_demand=None, demand_pattern_name=None, elevation=None, coordinates=None):
        """
        Add a junction to the network.
        
        Parameters
        ----------
        name : string
            Name of the junction.

        Other Parameters
        -------------------
        base_demand : float
            Base demand at the junction.
            Internal units must be cubic meters per second (m^3/s).
        demand_pattern_name : string
            Name of the demand pattern.
        elevation : float
            Elevation of the junction.
            Internal units must be meters (m).
        coordinates : tuple of floats
            X-Y coordinates of the node location

        """
        if base_demand is not None:
            base_demand = float(base_demand)
        if elevation is not None:
            elevation = float(elevation)
        junction = Junction(name, base_demand, demand_pattern_name, elevation)
        self._nodes[name] = junction
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        self.set_node_type(name, 'junction')
        self._num_junctions += 1

    def add_tank(self, name, elevation=None, init_level=None,
                 min_level=None, max_level=None, diameter=None,
                 min_vol=None, vol_curve=None, coordinates=None):
        """
        Method to add tank to a water network object.

        Parameters
        ----------
        name : string
            Name of the tank.

        Other Parameters
        ----------------
        elevation : float
            Elevation at the Tank.
            Internal units must be meters (m).
        init_level : float
            Initial tank level.
            Internal units must be meters (m).
        min_level : float
            Minimum tank level.
            Internal units must be meters (m)
        max_level : float
            Maximum tank level.
            Internal units must be meters (m)
        diameter : float
            Tank diameter.
            Internal units must be meters (m)
        min_vol : float
            Minimum tank volume.
            Internal units must be cubic meters (m^3)
        vol_curve_name : string
            Name of the tank volume curve.
        coordinates : tuple of floats
            X-Y coordinates of the node location
        """
        if elevation is not None:
            elevation = float(elevation)
        if init_level is not None:
            init_level = float(init_level)
        if min_level is not None:
            min_level = float(min_level)
        if max_level is not None:
            max_level = float(max_level)
        if diameter is not None:
            diameter = float(diameter)
        if min_vol is not None:
            min_vol = float(min_vol)
        if init_level is not None and min_level is not None:
            assert init_level >= min_level, "Initial tank level must be greater than or equal to the tank minimum level."
        if init_level is not None and max_level is not None:
            assert init_level <= max_level, "Initial tank level must be less than or equal to the tank maximum level."
        if min_level is not None and max_level is not None:
            assert min_level <= max_level, "Tank minimum level must be less than or equal to the tank maximum level."
        tank = Tank(name, elevation, init_level,
                 min_level, max_level, diameter,
                 min_vol, vol_curve)
        self._nodes[name] = tank
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        self.set_node_type(name, 'tank')
        self._num_tanks += 1

    def get_graph_copy(self):
        return copy.deepcopy(self._graph)
    
    def get_weighted_graph_copy(self, node_attribute={}, link_attribute={}):
        
        G = copy.deepcopy(self._graph)
        
        for index, value in node_attribute.iteritems():
            if type(index) is tuple:
                node_name = index[0] # if the index is taken from a pivot table, it's indexed by (node, time)
            else:
                node_name = index
            nx.set_node_attributes(G, 'weight', {node_name: value})
            
        for index, value in link_attribute.iteritems():
            if type(index) is tuple:
                link_name = index[0] # if the index is taken from a pivot table, it's indexed by (link, time)
            else:
                link_name = index
            link = self.get_link(link_name)
            if value < 0: # change the direction of the link and value
                link_type = G[link.start_node()][link.end_node()][link_name]['type'] # 'type' should be the only other attribute on G.edge
                G.remove_edge(link.start_node(), link.end_node(), link_name)
                G.add_edge(link.end_node(), link.start_node(), link_name)
                nx.set_edge_attributes(G, 'type', {(link.end_node(), link.start_node(), link_name): link_type})
                nx.set_edge_attributes(G, 'weight', {(link.end_node(), link.start_node(), link_name): -value})
            else:
                nx.set_edge_attributes(G, 'weight', {(link.start_node(), link.end_node(), link_name): value})
        
        return G
        
    def add_reservoir(self, name, base_head=None, head_pattern_name=None, coordinates=None):
        """
        Method to add reservoir to a water network object.

        Parameters
        ----------
        name : string
            Name of the reservoir.

        Other Parameters
        -------------------
        base_head : float
            Base head at the reservoir.
            Internal units must be meters (m).
        head_pattern_name : string
            Name of the head pattern.
        coordinates : tuple of floats
            X-Y coordinates of the node location
        """
        if base_head is not None:
            base_head = float(base_head)
        reservoir = Reservoir(name, base_head, head_pattern_name)
        self._nodes[name] = reservoir
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        self.set_node_type(name, 'reservoir')
        self._num_reservoirs += 1

    def add_pipe(self, name, start_node_name, end_node_name, length=None,
                 diameter=None, roughness=None, minor_loss=None, status=None):
        """
        Method to add pipe to a water network object.

        Parameters
        ----------
        name : string
            Name of the pipe
        start_node_name : string
             Name of the start node
        end_node_name : string
             Name of the end node

        Other Parameters
        -------------------
        length : float
            Length of the pipe.
            Internal units must be meters (m)
        diameter : float
            Diameter of the pipe.
            Internal units must be meters (m)
        roughness : float
            Pipe roughness coefficient
        minor_loss : float
            Pipe minor loss coefficient
        status : string
            Pipe status. Options are 'Open', 'Closed', and 'CV'
        """
        if length is not None:
            length = float(length)
        if diameter is not None:
            diameter = float(diameter)
        if roughness is not None:
            roughness = float(roughness)
        if minor_loss is not None:
            minor_loss = float(minor_loss)
        pipe = Pipe(name, start_node_name, end_node_name, length,
                    diameter, roughness, minor_loss, status)
        # Add to list of cv
        if status is not None:
            if status.upper() == 'CV':
                self._check_valves.append(name)
        self._links[name] = pipe
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        self.set_link_type((start_node_name, end_node_name, name), 'pipe')
        self._num_pipes += 1

    def remove_pipe(self, name):
        """
        Method to remove a pipe from the water network object.

        Parameters
        ----------
        name: string
           Name of the pipe
        """
        pipe = self.get_link(name)
        status = pipe.get_base_status()
        if status == 'CV':
            self._check_valves.remove(name)
        self._graph.remove_edge(pipe.start_node(), pipe.end_node(), key=name)
        self._links.pop(name)
        self._num_pipes -= 1

    def add_pump(self, name, start_node_name, end_node_name, info_type='HEAD', info_value=None):
        """
        Method to add pump to a water network object.

        Parameters
        ----------
        name : string
            Name of the pump
        start_node_name : string
             Name of the start node
        end_node_name : string
             Name of the end node

        Other Parameters
        -------------------
        info_type : string
            Type of information provided for a pump. Options are 'POWER' or 'HEAD'.
        info_value : float or Curve object
            Float value of power in KW. Head curve object.
        """
        pump = Pump(name, start_node_name, end_node_name, info_type, info_value)
        self._links[name] = pump
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        self.set_link_type((start_node_name, end_node_name, name), 'pump')
        self._num_pumps += 1

    def add_valve(self, name, start_node_name, end_node_name,
                 diameter=None, valve_type=None, minor_loss=None, setting=None):
        """
        Method to add valve to a water network object.

        Parameters
        ----------
        name : string
            Name of the valve
        start_node_name : string
             Name of the start node
        end_node_name : string
             Name of the end node

        Other Parameters
        -------------------
        diameter : float
            Diameter of the valve.
            Internal units must be meters (m)
        valve_type : string
            Type of valve. Options are 'PRV', etc
        minor_loss : float
            Pipe minor loss coefficient
        setting : string
            Valve status. Options are 'Open', 'Closed', etc
        """
        valve = Valve(name, start_node_name, end_node_name,
                      diameter, valve_type, minor_loss, setting)
        self._links[name] = valve
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        self.set_link_type((start_node_name, end_node_name, name), 'valve')
        self._num_valves += 1

    def add_pattern(self, name, pattern_list):
        """
        Method to add pattern to a water network object.

        Parameters
        ----------
        name : string
            name of the pattern
        pattern_list : list of floats
            A list of floats that make up the pattern.
        """
        self._patterns[name] = pattern_list

    def add_curve(self, name, curve_type, xy_tuples_list):
        """
        Method to add a curve to a water network object.

        Parameters
        ----------
        name : string
            Name of the curve
        curve_type : string
            Type of curve. Options are HEAD, EFFICIENCY, VOLUME, HEADLOSS
        xy_tuples_list : list of tuples
            List of X-Y coordinate tuples on the curve.
        """
        curve = Curve(name, curve_type, xy_tuples_list)
        self._curves[name] = curve

    def add_time_parameter(self, name, value):
        """
        Method to add a time parameter to a water network object.

        Parameters
        ----------
        name : string
            Name of the time option.
        value:
            Value of the time option. Must be in minutes.

        Examples
        --------
        START CLOCKTIME = 6 PM can be set using
        >>> wn.add_time_parameter('START CLOCKTIME', 1080)
        """
        self.time_options[name.upper()] = value

    def add_option(self, name, value):
        """
        Method to add a options to a water network object.

        Parameters
        ----------
        name : string
            Name of the option.
        value:
            Value of the option.
        """
        self.options[name.upper()] = value

    def add_reaction_option(self, name, value):
        """
        Method to add a reaction option to a water network object.

        Parameters
        ----------
        name : string
            Name of the option.
        value:
            Value of the option.
        """
        self.reaction_options[name.upper()] = value
    
    def get_node_attribute(self, attribute, node_type=None):
        """ Get node attributes

        Parameters
        ----------
        attribute: string
            Node attribute

        node_type: string
            options = Node, Junction, Reservoir, Tank, default = Node

        Returns
        -------
        node_attribute : dictionary of nodes
            dictionary of node names to attribute
        """
        node_attribute = {}
        for node_name, node in self.nodes(node_type):
            try:
                node_attribute[node_name] = getattr(node, attribute)
            except AttributeError:
                pass
            
        return node_attribute
    
    def get_link_attribute(self, attribute, link_type=None):
        """ Get link attributes

        Parameters
        ----------
        attribute: string
            Link attribute

        node_type: string
            options = Link, Pipe, Pump, Valve, default = Link

        Returns
        -------
        link_attribute : dictionary of links
            dictionary of link names to attribute
        """
        link_attribute = {}
        for link_name, link in self.links(link_type):
            try:
               link_attribute[link_name] = getattr(link, attribute)
            except AttributeError:
                pass
            
        return link_attribute
        
    def query_node_attribute(self, attribute, operation, value, node_type=None):
        """ Query node attributes, for example get all nodes with elevation <= threshold

        Parameters
        ----------
        attribute: string
            Node attribute

        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

        value: scalar
            threshold

        Returns
        -------
        nodes : dictionary of nodes
            dictionary of node names to node objects satisfying operation threshold
        """
        node_attribute_dict = {}
        for name, node in self.nodes(node_type):
            try:
                node_attribute = getattr(node, attribute)
                if operation(node_attribute, value):
                    node_attribute_dict[name] = node_attribute
            except AttributeError:
                pass
        return node_attribute_dict

    def query_link_attribute(self, attribute, operation, value, link_type=None):
        """ Query link attributes, for example get all pipe diameters > threshold

        Parameters
        ----------
        attribute: string
            link attribute

        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

        value: scalar
            threshold

        Returns
        -------
        links : dictionary of links
            dictionary of link names to link objects satisfying operation threshold
        """
        link_attribute_dict = {}
        for name, link in self.links(link_type):
            try:
                link_attribute = getattr(link, attribute)
                if operation(link_attribute, value):
                    link_attribute_dict[name] = link_attribute
            except AttributeError:
                pass
        return link_attribute_dict

    def add_time_control(self, link_name, open_times=[], closed_times=[], active_times=[]):
        """
        Add time controls to the network.

        Parameters
        ----------
        link_name : string
            Name of the link
        open_times : list of integers
            List of times (in seconds) when the link is opened
        closed_times : list of integers
            List of times (in seconds) when the link is closed

        """
        #link = self.get_link(link_name)
        if link_name not in self.time_controls:
            #self.time_controls[link_name] = {'open_times': [i for i in open_times], 'closed_times': [i for i in closed_times]}
            self.time_controls[link_name] = {'open_times': [i for i in open_times], 'closed_times': [i for i in closed_times], 'active_times': [i for i in active_times]}
        else:
            self.time_controls[link_name]['open_times'] += open_times
            self.time_controls[link_name]['closed_times'] += closed_times
            self.time_controls[link_name]['active_times'] += active_times

        self.time_controls[link_name]['open_times'].sort()
        self.time_controls[link_name]['closed_times'].sort()
        self.time_controls[link_name]['active_times'].sort()

    def add_conditional_controls(self, link_name, node_name, level_value, open_or_closed, above_or_below):
        """
        Add conditional controls to the network.
        
        Parameters
        ----------
        link_name : string
            Name of the link.
        node_name : string
            Name of the node.
        level_value : string
             level value in meters for the control to activate.
        open_or_closed : string
            Link would open or close. Options are 'OPEN'. 'CLOSED'
        above_or_below : string
            Control will activate if head value is below or above. Options are 'ABOVE', 'BELOW'
        """
        if link_name not in self.conditional_controls:
            self.conditional_controls[link_name] = {'open_above':[],
                                                    'open_below':[],
                                                    'closed_above':[],
                                                    'closed_below':[]}
        # Add conditional control
        upper_open_or_closed = open_or_closed.upper()
        upper_above_or_below = above_or_below.upper()
        if upper_open_or_closed == 'OPEN' and upper_above_or_below == 'ABOVE':
            self.conditional_controls[link_name]['open_above'].append((node_name, level_value))
        elif upper_open_or_closed == 'OPEN' and upper_above_or_below == 'BELOW':
            self.conditional_controls[link_name]['open_below'].append((node_name, level_value))
        elif upper_open_or_closed == 'CLOSED' and upper_above_or_below == 'ABOVE':
            self.conditional_controls[link_name]['closed_above'].append((node_name, level_value))
        elif upper_open_or_closed == 'CLOSED' and upper_above_or_below == 'BELOW':
            self.conditional_controls[link_name]['closed_below'].append((node_name, level_value))
        else:
            raise RuntimeError("String option open_or_closed or above_or_below not recognized: "
                               + open_or_closed + " " + above_or_below)

    def nodes(self, node_type=None):
        """
        A generator to iterate over all nodes of node_type.
        If no node_type is passed, this method iterates over all nodes.

        Returns
        -------
        node_name, node
        """
        for node_name, node in self._nodes.iteritems():
            if node_type is None:
                yield node_name, node
            elif isinstance(node, node_type):
                yield node_name, node

    def links(self, link_type=None):
        """
        A generator to iterate over all links of link_type.
        If no link_type is passed, this method iterates over all links.


        Returns
        -------
        link_name, link
        """
        for link_name, link in self._links.iteritems():
            if link_type is None:
                yield link_name, link
            elif isinstance(link, link_type):
                yield link_name, link

    def num_nodes(self):
        """
        Number of nodes.

        Returns
        -------
        Number of nodes.
        """
        return len(self._nodes)

    def num_links(self):
        """
        Number of links.

        Returns
        -------
        """
        return len(self._links)

    def curves(self):
        """
        A generator to iterate over all curves

        Returns
        -------
        curve_name, curve
        """
        for curve_name, curve in self._curves.iteritems():
            yield curve_name, curve

    def get_all_nodes_copy(self):
        """
        Return a copy of the dictionary with all nodes.

        Parameters
        ----------

        Returns
        -------
        node : dictionary
            Node name to node.
        """
        return copy.deepcopy(self._nodes)

    def get_all_links_copy(self):
        """
        Return a copy of the dictionary with all nodes.

        Parameters
        ----------

        Returns
        -------
        node : dictionary
            Node name to node.
        """
        return copy.deepcopy(self._links)

    def set_node_coordinates(self, name, coordinates):
        """
        Method to set the node coordinates in the network x graph.

        Parameters
        ----------
        name : name of the node
        coordinates : tuple of X-Y coordinates
        """
        nx.set_node_attributes(self._graph, 'pos', {name: coordinates})
    
    def set_node_type(self, name, nodetype):
        """
        Method to set the node type in the network x graph.

        Parameters
        ----------
        name : name of the node
        nodetype : string
        """
        nx.set_node_attributes(self._graph, 'type', {name: nodetype})
        
    def set_link_type(self, name, linktype):
        """
        Method to set the link type in the network x graph.

        Parameters
        ----------
        name : name of the link (u,v,k)
        linktype : string
        """
        nx.set_edge_attributes(self._graph, 'type', {name: linktype})

    def get_links_for_node(self, node_name):
        """
        Returns a list of links connected to a node.

        Parameters
        ----------
        node_name : string
            Name of the node.

        Returns
        -------
        A list of link names connected to the node
        """
        in_edges = self._graph.in_edges(node_name, data=False, keys=True)
        out_edges = self._graph.out_edges(node_name, data=False, keys=True)
        edges = in_edges + out_edges
        list_of_links = []
        for edge_tuple in edges:
            list_of_links.append(edge_tuple[2])

        return list_of_links

    def set_nominal_pressures(self, res = None, fraction_of_min = 0.8, constant_nominal_pressure = None, units = 'm', minimum_pressure = 0.0):
        """
        A method for setting nominal pressures (hydraulic head - elevation) for pressure driven simulations.

        Parameters
        ----------
        res: results object
            Use the res parameter if you want to set nominal pressures based on the results of
            another simulation. For each junction, the nominal pressure will be the product of fraction_of_min
            and the minimum pressure for that junction in the results. The results object should use
            internal units (SI units).
        fraction_of_min: float, 0<=fraction_of_min<=1
            Specifies the fraction of the minimum pressure for that junction from the results to set the 
            nominal pressure to. Must be between 0 and 1.
        constant_nominal_pressure: float
            Use the constant_nominal pressure parameter if you want all junctions to have the same 
            nominal pressure.
        units: string
            The units parameter is used if you use the constant_nominal_pressure. It specifies
            the units of the constant_nominal_pressure parameter. Default is meters. Supported units:
            meters and psi.
        minimum_pressure: float
            Value to set the minimum pressure to. Below this pressure, the acual demand will be 0.
        """
        if res is not None and constant_nominal_pressure is None:
            if units.upper() not in ['PSI','M']:
                raise ValueError('The only units currently supported for the set_nominal_pressures method are \'psi\'(pounds per square inch) and \'m\'(meters).')
            minimum_pressure = float(minimum_pressure)
            if units.upper()=='PSI':
                minimum_pressure = convert('Pressure',0,minimum_pressure)
            for junction_name,junction in self.nodes(Junction):
                min_P = res.node['pressure'][junction_name].min()
                if min_P <= 0.0:
                    raise RuntimeError('error: Results had negative pressure at a junction')
                else:
                    assert fraction_of_min >= 0.0, "fraction_of_min must be between 0 and 1."
                    assert fraction_of_min <= 1.0, "fraction_of_min must be between 0 and 1."
                    junction.PF = fraction_of_min*min_P
                    junction.P0 = minimum_pressure
                    assert junction.PF >= junction.P0, "Nominal pressure must be greater than minimum pressure."
        elif constant_nominal_pressure is not None and res is None:
            if units.upper() not in ['PSI','M']:
                raise ValueError('The only units currently supported for the set_nominal_pressures method are \'psi\'(pounds per square inch) and \'m\'(meters).')
            constant_nominal_pressure = float(constant_nominal_pressure)
            minimum_pressure = float(minimum_pressure)
            if units.upper()=='PSI':
                constant_nominal_pressure = convert('Pressure',0,constant_nominal_pressure)
                minimum_pressure = convert('Pressure',0,minimum_pressure)
            for junction_name,junction in self.nodes(Junction):
                junction.PF = constant_nominal_pressure
                junction.P0 = minimum_pressure
                assert junction.PF >= junction.P0, "Nominal pressure must be greater than minimum pressure."
        else:
            raise RuntimeError('error: either you have not specified any nominal pressure or you have tried to specify the nominal pressure in multiple ways')


    def _sec_to_string(self, sec):
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        return (hours, mm, sec)

    def add_leak(self, leak_name, pipe_name, leak_area = None, leak_diameter = None, leak_discharge_coeff = 0.75, start_time = '0 days 00:00:00', fix_time = None, control_dest = 'ISOLATE'):
        """
        Method to add a pipe leak to the network. Leaks are modeled by:

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
           Area of the leak in m^2. Either the leak area or the leak
           diameter must be specified, but not both.
        leak_diameter: float
           Diameter of the leak in m. The area of the leak is
           calculated with leak_diameter assuming the leak is in the
           shape of a circle.  Either the leak area or the leak
           diameter must be specified, but not both.
        leak_discharge_coeff: float
           Leak discharge coefficient; Takes on values between 0 and 1
        start_time: string
           Start time of the leak. Pandas Timedelta format: e.g. '0
           days 00:00:00'. Default is the start of the simulation.
        fix_time: string
           Time at which the leak is fixed. Pandas Timedelta format:
           e.g. '0 days 05:00:00'. Default is that the leak does not
           get fixed during the simulation.
        control_dest: string
           Control destination. Options are 'REMOVE', 'START_NODE',
           'END_NODE', or 'ISOLATE'. This argument is used to update
           time and conditional controls. When a leak is added to a
           pipe, the pipe is replaced with a leak node and two new
           pipes on either side of the leak node. If there is a time
           or conditional control associated with the original pipe,
           it must be either removed or associated with one (or both)
           of the new pipes. 'REMOVE' indicates that the control will
           be discarded. 'START_NODE' indicates that the control will
           be associated with the pipe between the start node and the
           leak. 'END_NODE' indicates that the control will be
           associated with the pipe between the leak and the end
           node. 'ISOLATE' indicates that control will affect both
           pipes on either side of the leak. The default is
           'ISOLATE'. If tank levels fall too low, the link closest to
           the tank is closed.
        """
        # Ensure pipe does not already have a leak and leak does not already exist
        if pipe_name in self._pipes_with_leaks.keys():
            warnings.warn('Pipe '+pipe_name+' already has a leak. Old leak is being overridden.')
            tmp_leak_name = self._pipes_with_leaks[pipe_name]
            self.remove_leak(tmp_leak_name)
        if leak_name in [name for name,node in self.nodes(Leak)]:
            warnings.warn('Leak '+leak_name+' is already associated with a pipe. Old pipe will no longer have a leak.')
            self.remove_leak(leak_name)

        # Check if pipe_name is valid
        try:
            pipe = self.get_link(pipe_name)
        except KeyError:
            raise KeyError(pipe_name + " is not a valid link in the network.")
        if not isinstance(pipe, Pipe):
            raise RuntimeError(pipe_name + " is not a valid pipe in the network.")

        # Check if start time and end time are valid
        try:
            start = pd.Timedelta(start_time)
            if fix_time is not None:
                end = pd.Timedelta(fix_time)
        except RuntimeError:
            raise RuntimeError("The format of start or fix time is not valid Pandas Timedelta format.")

        # Convert start time and end time to seconds
        start_sec = timedelta_to_sec(start)
        if fix_time is not None:
            end_sec = timedelta_to_sec(end)
        else:
            end_sec = self.time_options['DURATION'] + self.time_options['START CLOCKTIME'] + self.time_options['HYDRAULIC TIMESTEP']

        # Set leak_area if leak_diameter was passed as an argument
        if leak_diameter is not None:
            if leak_area is not None:
                raise RuntimeError('When trying to add a leak, you may only specify the area or diameter, not both.')
            else:
                leak_area = math.pi/4.0*leak_diameter**2
        elif leak_area is None:
            raise RuntimeError('When trying to add a leak, you must specify either the area or the diameter.')

        # Ensure the name of the leak is not already used for another node
        if leak_name in self.get_all_nodes_copy().keys():
            raise ValueError('The leak name you provided, '+leak_name+', is already being used for another node.')

        # Check if the leak area is larger than the pipe area
        orig_pipe_area = math.pi/4.0*pipe.diameter**2
        if leak_area > orig_pipe_area:
            raise RuntimeError('You specified a leak area (or diameter) that is larger than the area (or diameter) of the original pipe.')

        # Get start and end node info
        start_node = self.get_node(pipe.start_node())
        end_node = self.get_node(pipe.end_node())
        if isinstance(start_node, Reservoir):
            leak_elevation = end_node.elevation
        elif isinstance(end_node, Reservoir):
            leak_elevation = start_node.elevation
        else:
            leak_elevation = (start_node.elevation + end_node.elevation)/2.0

        # Store leak information
        self._pipes_with_leaks[pipe_name] = leak_name

        # Remove original pipe
        self.remove_pipe(pipe_name)

        # Add a leak node
        leak = Leak(leak_name, pipe_name, leak_area, leak_discharge_coeff, leak_elevation, start_sec, end_sec, pipe, control_dest)
        self._nodes[leak_name] = leak
        self._graph.add_node(leak_name)
        self.set_node_type(leak_name, 'leak')
        leak_coordinates = ((self._graph.node[pipe.start_node()]['pos'][0] + self._graph.node[pipe.end_node()]['pos'][0])/2.0,(self._graph.node[pipe.start_node()]['pos'][1] + self._graph.node[pipe.end_node()]['pos'][1])/2.0)
        self.set_node_coordinates(leak_name, leak_coordinates)

        # Add new pipes
        self.add_pipe(pipe_name+'__A', pipe.start_node(), leak_name, pipe.length/2.0, pipe.diameter, pipe.roughness, pipe.minor_loss, pipe.get_base_status())
        self.add_pipe(pipe_name+'__B', leak_name, pipe.end_node(), pipe.length/2.0, pipe.diameter, pipe.roughness, pipe.minor_loss, pipe.get_base_status())

        # Update time and conditional controls
        self._update_time_controls_for_leak(leak_name)
        self._update_conditional_controls_for_leak(leak_name)

    def remove_leak(self, leak_name):
        """
        Method to remove a leak from the WaterNetworkModel object. The
        original pipe will be placed back in the network. The
        control_dest argument passed to the add_leak method will be
        used in a similar manner here. If 'REMOVE' was passed to the
        control_dest argument, then any time or conditional control
        associated with either pipe (on either side of the leak) will
        be discarded. If 'ISOLATE' or 'START NODE' was passed, then
        any time or conditional control associated with the pipe on
        the start node side of the leak will be moved to the original
        pipe. If 'END NODE' was passed, then any time or conditional
        control associated with the pipe on the end node side of the
        leak will be moved to the original pipe.

        Parameters
        ----------
        leak_name: string
             name of the leak to be removed

        """
        # Get the leak node
        leak = self.get_node(leak_name)

        # Get the original pipe and pipe name
        pipe = leak.original_pipe
        pipe_name = pipe.name()

        # Remove the changes to the time controls dictionary and the conditional controls dictionary
        self._update_time_controls_for_leak(leak_name, remove = True)
        self._update_conditional_controls_for_leak(leak_name, remove = True)

        # Remove the leak information
        self._pipes_with_leaks.pop(pipe_name)

        # Remove the pipes on either side of the leak
        self.remove_pipe(pipe_name+'__A')
        self.remove_pipe(pipe_name+'__B')

        # Remove the leak node from the network
        self._nodes.pop(leak_name)
        self._graph.remove_node(leak_name)

        # Place the original pipe back in the network
        self.add_pipe(pipe.name(), pipe.start_node(), pipe.end_node(), pipe.length, pipe.diameter, pipe.roughness, pipe.minor_loss, pipe.get_base_status())

    def _update_time_controls_for_leak(self, leak_name, remove = False):
        # Update time controls in consideration of leaks
        #
        # The remove argument specifies whether the leak is being
        # added or removed. If remove is True, the leak is being
        # removed. If remove is False, the leak is being added.

        leak = self.get_node(leak_name)

        # If the leak is being added
        if not remove:
            # If the pipe with the leak has a time control
            pipe_name = leak.orig_pipe_name
            if pipe_name in self.time_controls.keys():
                control_dict = self.time_controls[pipe_name]
                # Replace the time control for the original link with a time control
                # for either original_link__A, original_link__B, or both, depending
                # on the control_dest argument provided to the add_leak method.
                if leak.control_dest == 'REMOVE':
                    #warnings.warn('The time controls for pipe '+pipe_name+' are being removed permanently.'+ 
                    #'Try help(wntr.network.add_leak) to change what happens to the time controls when adding a leak to a pipe with time controls.'+
                    #              'Alternatively, you can use the methods add_time_control and/or remove_time_control.')
                    self.time_controls.pop(pipe_name)
                elif leak.control_dest == 'START_NODE':
                    self.time_controls[pipe_name+'__A'] = control_dict
                    self.time_controls.pop(pipe_name)
                elif leak.control_dest == 'END_NODE':
                    self.time_controls[pipe_name+'__B'] = control_dict
                    self.time_controls.pop(pipe_name)
                elif leak.control_dest == 'ISOLATE':
                    self.time_controls[pipe_name+'__A'] = control_dict
                    self.time_controls[pipe_name+'__B'] = control_dict
                    self.time_controls.pop(pipe_name)
                else:
                    raise ValueError('control dest argument for leak is not recognized.')

        # If the leak is being removed
        else:
            # Get the name of the original pipe
            pipe_name = leak.orig_pipe_name
            # Depending on the control_dest argument provided to
            # the add_leak method, remove the time control for either
            # original_pipe__A, original_pipe__B, or both. Then add
            # the time control for the original pipe.
            if leak.control_dest == 'START_NODE':
                if (pipe_name+'__A') in self.time_controls.keys():
                    control_dict = self.time_controls[pipe_name+'__A']
                    self.time_controls[pipe_name] = control_dict
                    self.time_controls.pop(pipe_name+'__A')
                if (pipe_name+'__B') in self.time_controls.keys():
                    self.time_controls.pop(pipe_name+'__B')
            elif leak.control_dest == 'END_NODE':
                if (pipe_name+'__B') in self.time_controls.keys():
                    control_dict = self.time_controls[pipe_name+'__B']
                    self.time_controls[pipe_name] = control_dict
                    self.time_controls.pop(pipe_name+'__B')
                if (pipe_name+'__A') in self.time_controls.keys():
                    self.time_controls.pop(pipe_name+'__A')
            elif leak.control_dest == 'ISOLATE':
                if (pipe_name+'__A') in self.time_controls.keys():
                    control_dict = self.time_controls[pipe_name+'__A']
                    self.time_controls[pipe_name] = control_dict
                    self.time_controls.pop(pipe_name+'__A')
                if (pipe_name+'__B') in self.time_controls.keys():
                    self.time_controls.pop(pipe_name+'__B')
            elif leak.control_dest == 'REMOVE':
                if (pipe_name+'__A') in self.time_controls.keys():
                    self.time_controls.pop(pipe_name+'__A')
                if (pipe_name+'__B') in self.time_controls.keys():
                    self.time_controls.pop(pipe_name+'__B')                
            else:
                raise ValueError('control_dest argument for leak is not recognized.')


    def _update_conditional_controls_for_leak(self, leak_name, remove = False):
        # Update conditional controls in consideration of leaks
        #
        # The remove argument specifies whether the leak is being
        # added or removed. If remove is True, the leak is being
        # removed. If remove is False, the leak is being added.

        leak = self.get_node(leak_name)

        # If the leak is being added
        if not remove:
            # If the pipe with the leak has a conditional control
            pipe_name = leak.orig_pipe_name
            if pipe_name in self.conditional_controls.keys():
                control_dict = self.conditional_controls[pipe_name]
                # Replace the conditional control for the original link with a conditional control
                # for either original_link__A, original_link__B, or both, depending
                # on the control_dest argument provided to the add_leak method.
                if leak.control_dest == 'REMOVE':
                    self.conditional_controls.pop(pipe_name)
                elif leak.control_dest == 'START_NODE':
                    self.conditional_controls[pipe_name+'__A'] = control_dict
                    self.conditional_controls.pop(pipe_name)
                elif leak.control_dest == 'END_NODE':
                    self.conditional_controls[pipe_name+'__B'] = control_dict
                    self.conditional_controls.pop(pipe_name)
                elif leak.control_dest == 'ISOLATE':
                    self.conditional_controls[pipe_name+'__A'] = control_dict
                    self.conditional_controls[pipe_name+'__B'] = control_dict
                    self.conditional_controls.pop(pipe_name)
                else:
                    raise ValueError('control_dest argument for leak is not recognized.')

        # If the leak is being removed
        else:
            # If the pipe with the leak has a conditional control
            pipe_name = leak.orig_pipe_name
            if leak.control_dest == 'START_NODE':
                if (pipe_name+'__A') in self.conditional_controls.keys():
                    control_dict = self.conditional_controls[pipe_name+'__A']
                    self.conditional_controls[pipe_name] = control_dict
                    self.conditional_controls.pop(pipe_name+'__A')
                if (pipe_name+'__B') in self.conditional_controls.keys():
                    self.conditional_controls.pop(pipe_name+'__B')
            elif leak.control_dest == 'END_NODE':
                if (pipe_name+'__B') in self.conditional_controls.keys():
                    control_dict = self.conditional_controls[pipe_name+'__B']
                    self.conditional_controls[pipe_name] = control_dict
                    self.conditional_controls.pop(pipe_name+'__B')
                if (pipe_name+'__A') in self.conditional_controls.keys():
                    self.conditional_controls.pop(pipe_name+'__A')
            elif leak.control_dest == 'ISOLATE':
                if (pipe_name+'__A') in self.conditional_controls.keys():
                    control_dict = self.conditional_controls[pipe_name+'__A']
                    self.conditional_controls[pipe_name] = control_dict
                    self.conditional_controls.pop(pipe_name+'__A')
                if (pipe_name+'__B') in self.conditional_controls.keys():
                    self.conditional_controls.pop(pipe_name+'__B')
            elif leak.control_dest == 'REMOVE':
                if (pipe_name+'__A') in self.conditional_controls.keys():
                    self.conditional_controls.pop(pipe_name+'__A')
                if (pipe_name+'__B') in self.conditional_controls.keys():
                    self.conditional_controls.pop(pipe_name+'__B')
            else:
                raise ValueError('control_dest argument for leak is not recognized.')


    def write_inpfile(self, filename):
        """
         Write the current network into an EPANET inp file.

         Parameters
         ----------
         filename : String
            Name of the inp file. example - Net3_adjusted_demands.inp
        """
        # TODO: This is still a very alpha version with hard coded unit conversions to LPS (among other things).

        f = open(filename, 'w')

        # Print title
        print >> f, '[TITLE]'
        if self.name is not None:
            print >> f, self.name

        # Print junctions information
        print >> f, '[JUNCTIONS]'
        text_format = '{:10s} {:15f} {:15f} {:>10s} {:>3s}'
        label_format = '{:10s} {:>15s} {:>15s} {:>10s}'
        print >> f, label_format.format(';ID', 'Elevation', 'Demand', 'Pattern')
        for junction_name, junction in self.nodes(Junction):
            if junction.demand_pattern_name is not None:
                print >> f, text_format.format(junction_name, junction.elevation, junction.base_demand*1000.0, junction.demand_pattern_name, ';')
            else:
                print >> f, text_format.format(junction_name, junction.elevation, junction.base_demand*1000.0, '', ';')

        # Print reservoir information
        print >> f, '[RESERVOIRS]'
        text_format = '{:10s} {:15f} {:>10s} {:>3s}'
        label_format = '{:10s} {:>15s} {:>10s}'
        print >> f, label_format.format(';ID', 'Head', 'Pattern')
        for reservoir_name, reservoir in self.nodes(Reservoir):
            if reservoir.head_pattern_name is not None:
                print >> f, text_format.format(reservoir_name, reservoir.base_head, reservoir.head_pattern_name, ';')
            else:
                print >> f, text_format.format(reservoir_name, reservoir.base_head, '', ';')

        # Print tank information
        print >> f, '[TANKS]'
        text_format = '{:10s} {:15f} {:15f} {:15f} {:15f} {:15f} {:15f} {:>10s} {:>3s}'
        label_format = '{:10s} {:>15s} {:>15s} {:>15s} {:>15s} {:>15s} {:>15s} {:>10s}'
        print >> f, label_format.format(';ID', 'Elevation', 'Initial Level', 'Minimum Level', 'Maximum Level', 'Diameter', 'Minimum Volume', 'Volume Curve')
        for tank_name, tank in self.nodes(Tank):
            if tank.vol_curve is not None:
                print >> f, text_format.format(tank_name, tank.elevation, tank.init_level, tank.min_level, tank.max_level, tank.diameter, tank.min_vol, tank.vol_curve, ';')
            else:
                print >> f, text_format.format(tank_name, tank.elevation, tank.init_level, tank.min_level, tank.max_level, tank.diameter, tank.min_vol, '', ';')

        # Print pipe information
        print >> f, '[PIPES]'
        text_format = '{:10s} {:10s} {:10s} {:15f} {:15f} {:15f} {:15f} {:>10s} {:>3s}'
        label_format = '{:10s} {:>10s} {:>10s} {:>15s} {:>15s} {:>15s} {:>15s} {:>10s}'
        print >> f, label_format.format(';ID', 'Node1', 'Node2', 'Length', 'Diameter', 'Roughness', 'Minor Loss', 'Status')
        for pipe_name, pipe in self.links(Pipe):
            print >> f, text_format.format(pipe_name, pipe.start_node(), pipe.end_node(), pipe.length, pipe.diameter*1000, pipe.roughness, pipe.minor_loss, pipe.get_base_status(), ';')

        # Print pump information
        print >> f, '[PUMPS]'
        text_format = '{:10s} {:10s} {:10s} {:10s} {:10s} {:>3s}'
        label_format = '{:10s} {:>10s} {:>10s} {:>10s}'
        print >> f, label_format.format(';ID', 'Node1', 'Node2', 'Parameters')
        for pump_name, pump in self.links(Pump):
            if pump.info_type == 'HEAD':
                print >> f, text_format.format(pump_name, pump.start_node(), pump.end_node(), pump.info_type, pump.curve.name, ';')
            elif pump.info_type == 'POWER':
                print >> f, text_format.format(pump_name, pump.start_node(), pump.end_node(), pump.info_type, str(pump.power), ';')
            else:
                raise RuntimeError('Only head or power info is supported of pumps.')
        # Print valve information
        print >> f, '[VALVES]'
        text_format = '{:10s} {:10s} {:10s} {:10f} {:10s} {:10f} {:10f} {:>3s}'
        label_format = '{:10s} {:10s} {:10s} {:10s} {:10s} {:10s} {:10s}'
        print >> f, label_format.format(';ID', 'Node1', 'Node2', 'Diameter', 'Type', 'Setting', 'Minor Loss')
        for valve_name, valve in self.links(Valve):
            print >> f, text_format.format(valve_name, valve.start_node(), valve.end_node(), valve.diameter*1000, valve.valve_type, valve.setting, valve.minor_loss, ';')

        # Print status information
        print >> f, '[STATUS]'
        text_format = '{:10s} {:10s}'
        label_format = '{:10s} {:10s}'
        print >> f, label_format.format(';ID', 'Setting')
        for link_name, link in self.links():
            if link.get_base_status() is not None and link.get_base_status() != 'CV':
                print >> f, text_format.format(link_name, link.get_base_status())

        # Print pattern information
        num_columns = 8
        print >> f, '[PATTERNS]'
        label_format = '{:10s} {:10s}'
        print >> f, label_format.format(';ID', 'Multipliers')
        for pattern_name, pattern in self._patterns.iteritems():
            count = 0
            for i in pattern:
                if count%8 == 0:
                    print >>f, '\n', pattern_name, i,
                else:
                    print >>f, i,
                count += 1
            print >>f, ''

        # Print curves
        print >> f, '[CURVES]'
        text_format = '{:10s} {:10f} {:10f} {:>3s}'
        label_format = '{:10s} {:10s} {:10s}'
        print >> f, label_format.format(';ID', 'X-Value', 'Y-Value')
        for pump_name, pump in self.links(Pump):
            if pump.info_type == 'HEAD':
                curve = pump.curve
                curve_name = curve.name
                for i in curve.points:
                    print >>f, text_format.format(curve_name, 1000*i[0], i[1], ';')
                print >>f, ''

        # Print Controls
        print >> f, '[CONTROLS]'
        # Time controls
        for link_name, all_control in self.time_controls.iteritems():
            open_times = all_control.get('open_times')
            closed_times = all_control.get('closed_times')
            if open_times is not None:
                for i in open_times:
                    print >> f, 'Link', link_name, 'OPEN AT TIME', int(i/3600.0)
            if closed_times is not None:
                for i in closed_times:
                    print >> f, 'Link', link_name, 'CLOSED AT TIME', int(i/3600.0)

        print >> f, ''
        # Conditional controls
        for link_name, all_control in self.conditional_controls.iteritems():
            open_below = all_control.get('open_below')
            closed_above = all_control.get('closed_above')
            open_above = all_control.get('open_above')
            closed_below = all_control.get('closed_below')
            if open_below is not None:
                for i in open_below:
                    print >> f, 'Link', link_name, 'OPEN IF Node', i[0], 'BELOW', i[1]
            if closed_above is not None:
                for i in closed_above:
                    print >> f, 'Link', link_name, 'CLOSED IF Node', i[0], 'ABOVE', i[1]
            if open_above is not None:
                for i in open_above:
                    print >> f, 'Link', link_name, 'OPEN IF Node', i[0], 'ABOVE', i[1]
            if closed_below is not None:
                for i in closed_below:
                    print >> f, 'Link', link_name, 'CLOSED IF Node', i[0], 'BELOW', i[1]

            print >> f,''

        # Options
        print >> f, '[OPTIONS]'
        text_format_string = '{:20s} {:10s}'
        text_format_float = '{:20s} {:<10.8f}'
        for key, val in self.options.iteritems():
            if key == 'UNITS':
                print >>f, text_format_string.format('UNITS', 'LPS')
            elif isinstance(val, float):
                print >>f, text_format_float.format(key, val)
            elif isinstance(val, str):
                print >>f, text_format_string.format(key, val)
            else:
                raise RuntimeError('Options value not recognised')

        print >> f, ''

        # Reaction Options
        print >> f, '[REACTIONS]'
        text_format_float = '{:20s} {:<10.8f}'
        for key, val in self.reaction_options.iteritems():
            print >>f, text_format_float.format(key, val)

        print >> f, ''

        # Time options
        print >> f, '[TIMES]'
        text_format = '{:20s} {:10s}'
        time_text_format = '{:20s} {:d}:{:d}:{:d}'
        for key, val in self.time_options.iteritems():
            if key == 'START CLOCKTIME':
                hrs, mm, sec = self._sec_to_string(val)
                if hrs < 12:
                    time_format = ' AM'
                else:
                    time_format = ' PM'
                print >>f, text_format.format(key, str(hrs)+time_format)
            elif isinstance(val, float) or isinstance(val, int):
                hrs, mm, sec = self._sec_to_string(val)
                print >>f, time_text_format.format(key, hrs, mm, sec)
            elif isinstance(val, str):
                print >>f, text_format.format(key, val)
            else:
                raise RuntimeError('Time options value not recognised')

        print >> f, ''

        # Coordinates
        print >> f, '[COORDINATES]'
        text_format = '{:10s} {:<10.2f} {:<10.2f}'
        label_format = '{:10s} {:10s} {:10s}'
        print >>f, label_format.format(';Node', 'X-Coord', 'Y-Coord')
        coord = nx.get_node_attributes(self._graph, 'pos')
        for key, val in coord.iteritems():
            print >>f, text_format.format(key, val[0], val[1])

        f.close()


class Node(object):
    """
    The base node class.
    """
    def __init__(self, name):
        """
        Parameters
        -----------
        name : string
            Name of the node
        node_type : string
            Type of the node. Options are 'Junction', 'Tank', or 'Reservoir'

        Examples
        ---------
        >>> node2 = Node('North Lake','Reservoir')
        """
        self._name = name

    def __str__(self):
        """
        Returns the name of the node when printing to a stream.
        """
        return self._name

    def name(self):
        """
        Returns the name of the node.
        """
        return self._name

class LinkStatus(object):
    def __init__(self):
        self.closed = 0
        self.open = 1
        self.active = 2
        self.cv = 3

    def str_to_status(self, value):
        if value.upper() == 'OPEN':
            return self.open
        elif value.upper() == 'CLOSED':
            return self.closed
        elif value.upper() == 'ACTIVE':
            return self.active
        elif value.upper() == 'CV':
            return self.cv

class Link(object):
    """
    The base link class.
    """
    def __init__(self, link_name, start_node_name, end_node_name):
        """
        Parameters
        ----------
        link_name : string
            Name of the link
        link_type : string
            Type of the link. Options are 'Pipe', 'Valve', or 'Pump'
        start_node_name : string
             Name of the start node
        end_node_name : string
             Name of the end node

        Examples
        ---------
        >>> link1 = Link('Pipe 1','Pipe', 'Node 153', 'Node 159')
        """
        self._link_name = link_name
        self._start_node_name = start_node_name
        self._end_node_name = end_node_name
        status_options = LinkStatus()
        self._base_status = status_options.open
        self.current_status = status_options.open

    def __str__(self):
        """
        Returns the name of the link when printing to a stream.
        """
        return self._link_name

    def start_node(self):
        """
        Returns name of start node
        """
        return self._start_node_name

    def end_node(self):
        """
        Returns name of end node
        """
        return self._end_node_name

    def get_base_status(self):
        """
        Returns the base status of the link
        """
        return self._base_status

    def name(self):
        """
        Returns the name of the link
        """
        return self._link_name

class Junction(Node):
    """
    Junction class that is inherited from Node
    """
    def __init__(self, name, base_demand=None, demand_pattern_name=None, elevation=None):
        """
        Parameters
        ----------
        name : string
            Name of the junction.

        Other Parameters
        ----------------
        base_demand : float
            Base demand at the junction.
            Internal units must be cubic meters per second (m^3/s).
        demand_pattern_name : string
            Name of the demand pattern.
        elevation : float
            Elevation of the junction.
            Internal units must be meters (m).
        """
        Node.__init__(self, name)
        self.base_demand = base_demand
        self.current_demand = base_demand
        self.demand_pattern_name = demand_pattern_name
        self.elevation = elevation
        self.PF = 20.0
        self.P0 = 0.0
        self.leak = False
        self.leak_area = 0.0
        self.leak_discharge_coeff = 0.0
        self.leak_start_time = 0
        self.leak_fix_time = None

    def add_leak(self, area, discharge_coeff = 0.75, start_time = '0 days 00:00:00', fix_time = None):
        """
        Method to add a leak to a tank. Leaks are modeled by:

        Q = discharge_coeff*area*sqrt(2*g*h)

        where:
           Q is the volumetric flow rate of water out of the leak
           g is the acceleration due to gravity
           h is the guage head at the bottom of the tank, P_g/(rho*g); Note that this is not the hydraulic head (P_g + elevation)

        Note that WNTR assumes the leak is at the bottom of the tank.

        Parameters
        ----------
        area: float
           Area of the leak in m^2.
        discharge_coeff: float
           Leak discharge coefficient; Takes on values between 0 and 1.
        start_time: string
           Start time of the leak. Pandas Timedelta format: e.g. '0
           days 00:00:00'. Default is the start of the simulation.
        fix_time: string
           Time at which the leak is fixed. pandas Timedelta format:
           e.g. '0 days 05:00:00'. Default is that the leak does not
           get repaired during the simulation.
        """

        self.leak = True
        self.leak_area = area
        self.leak_discharge_coeff = discharge_coeff
        
        start = pd.Timedelta(start_time)
        self.leak_start_time = timedelta_to_sec(start)
        if fix_time is not None:
            end = pd.Timedelta(fix_time)
            self.leak_fix_time = timedelta_to_sec(end)
        else:
            self.leak_fix_time = np.inf

    def remove_leak(self):
        """
        Method to remove a leak from a tank.
        """
        self.leak = False


class Leak(Node):
    """
    Leak class that is inherited from Node
    """
    def __init__(self, leak_name, pipe_name, area, leak_discharge_coeff, elevation, start_sec, end_sec, pipe, control_dest):
        """
        Parameters
        ----------
        leak_name: string
           Name of the leak.
        pipe_name: string
           Name of the pipe where the leak ocurrs
        area: float
           Area of the leak in m^2
        leak_discharge_coeff: float
           Discharge coefficient
        elevation: float
           Elevation of the leak
        start_sec: int
           The time at which the leak starts in seconds.
        end_sec: int
           The time at which the leak is repaired in seconds.
        pipe: Pipe
           Pipe object for the pipe on which the leak occurs.
        control_dest: string
           Control destination. Options are 'REMOVE', 'START_NODE',
           'END_NODE', or 'ISOLATE'. This argument is used to update
           time and conditional controls. When a leak is added to a
           pipe, the pipe is replaced with a leak node and two new
           pipes on either side of the leak node. If there is a time
           or conditional control associated with the original pipe,
           it must be either removed or associated with one (or both)
           of the new pipes. 'REMOVE' indicates that the control will
           be discarded. 'START_NODE' indicates that the control will
           be associated with the pipe between the start node and the
           leak. 'END_NODE' indicates that the control will be
           associated with the pipe between the leak and the end
           node. 'ISOLATE' indicates that control will affect both
           pipes on either side of the leak. The default is
           'ISOLATE'. If tank levels fall too low, the link closest to
           the tank is closed.
        """
        Node.__init__(self, leak_name)
        self.orig_pipe_name = pipe_name
        self.area = area
        self.leak_discharge_coeff = leak_discharge_coeff
        self.elevation = elevation
        self.start_sec = start_sec
        self.end_sec = end_sec
        self.original_pipe = pipe
        self.control_dest = control_dest.upper()

    def set_start_time(self, start_time):
        """
        Method to set the time at which the leak starts.

        Parameters
        ----------
        start_time: string
           Start time of the leak. Pandas Timedelta format: e.g. '0
           days 00:00:00'.
        """
        start = pd.Timedelta(start_time)
        self.start_sec = timedelta_to_sec(start)

    def set_fix_time(self, fix_time):
        """
        Method to set the time at which the leak is repaired.

        Parameters
        ----------
        fix_time: string
           Time at which the leak is repaired. Pandas Timedelta
           format: e.g., '0 days 00:00:00'.
        """
        end = pd.Timedelta(fix_time)
        self.end_sec = timedelta_to_sec(end)

    def set_area(self, area):
        """
        Method to set the orifice area of the leak.

        Parameters
        ----------
        area: float
           Area of the leak in m^2.
        """
        self.area = area

    def set_diameter(self, d):
        """
        Method to set the orifice area of the leak.

        Parameters
        ----------
        d: float
           Diameter of the leak in meters. The leak area will be set
           by area = 0.25*pi*d^2.
        """
        self.area = math.pi/4.0*d**2.0

    def set_discharge_coefficient(self, c):
        """
        Method to set the discharge coefficient of the leak.

        Parameters
        ----------
        c: float
           Discharge coefficient
        """
        self.leak_discharge_coeff = c

class Reservoir(Node):
    """
    Reservoir class that is inherited from Node
    """
    def __init__(self, name, base_head=None, head_pattern_name=None):
        """
        Parameters
        ----------
        name : string
            Name of the reservoir.

        Other Parameters
        ----------------
        base_head : float
            Base head at the reservoir.
            Internal units must be meters (m).
        head_pattern_name : string
            Name of the head pattern.
        """
        Node.__init__(self, name)
        self.base_head = base_head
        self.current_head = base_head
        self.head_pattern_name = head_pattern_name


class Tank(Node):
    """
    Tank class that is inherited from Node
    """
    def __init__(self, name, elevation=None, init_level=None,
                 min_level=None, max_level=None, diameter=None,
                 min_vol=None, vol_curve=None):
        """
        Parameters
        ----------
        name : string
            Name of the tank.

        Other Parameters
        ----------------
        elevation : float
            Elevation at the Tank.
            Internal units must be meters (m).
        init_level : float
            Initial tank level.
            Internal units must be meters (m).
        min_level : float
            Minimum tank level.
            Internal units must be meters (m)
        max_level : float
            Maximum tank level.
            Internal units must be meters (m)
        diameter : float
            Tank diameter.
            Internal units must be meters (m)
        min_vol : float
            Minimum tank volume.
            Internal units must be cubic meters (m^3)
        vol_curve : string
            Name of the tank volume curve.
        """
        Node.__init__(self, name)
        self.elevation = elevation
        self.init_level = init_level
        self.current_level = init_level
        self.min_level = min_level
        self.max_level = max_level
        self.diameter = diameter
        self.min_vol = min_vol
        self.vol_curve = vol_curve
        self.leak = False
        self.leak_area = 0.0
        self.leak_discharge_coeff = 0.0
        self.leak_start_time = 0
        self.leak_fix_time = None

    def add_leak(self, area, discharge_coeff = 0.75, start_time = '0 days 00:00:00', fix_time = None):
        """
        Method to add a leak to a tank. Leaks are modeled by:

        Q = discharge_coeff*area*sqrt(2*g*h)

        where:
           Q is the volumetric flow rate of water out of the leak
           g is the acceleration due to gravity
           h is the guage head at the bottom of the tank, P_g/(rho*g); Note that this is not the hydraulic head (P_g + elevation)

        Note that WNTR assumes the leak is at the bottom of the tank.

        Parameters
        ----------
        area: float
           Area of the leak in m^2.
        discharge_coeff: float
           Leak discharge coefficient; Takes on values between 0 and 1.
        start_time: string
           Start time of the leak. Pandas Timedelta format: e.g. '0
           days 00:00:00'. Default is the start of the simulation.
        fix_time: string
           Time at which the leak is fixed. pandas Timedelta format:
           e.g. '0 days 05:00:00'. Default is that the leak does not
           get repaired during the simulation.
        """

        self.leak = True
        self.leak_area = area
        self.leak_discharge_coeff = discharge_coeff
        
        start = pd.Timedelta(start_time)
        self.leak_start_time = timedelta_to_sec(start)
        if fix_time is not None:
            end = pd.Timedelta(fix_time)
            self.leak_fix_time = timedelta_to_sec(end)
        else:
            self.leak_fix_time = np.inf

    def remove_leak(self):
        """
        Method to remove a leak from a tank.
        """
        self.leak = False

class Pipe(Link):
    """
    Pipe class that is inherited from Link
    """
    def __init__(self, name, start_node_name, end_node_name, length=None,
                 diameter=None, roughness=None, minor_loss=None, status=None):
        """
        Parameters
        ----------
        name : string
            Name of the pipe
        start_node_name : string
             Name of the start node
        end_node_name : string
             Name of the end node

        Other Parameters
        ----------------
        length : float
            Length of the pipe.
            Internal units must be meters (m)
        diameter : float
            Diameter of the pipe.
            Internal units must be meters (m)
        roughness : float
            Pipe roughness coefficient
        minor_loss : float
            Pipe minor loss coefficient
        status : string
            Pipe status. Options are 'Open', 'Closed', and 'CV'
        """
        Link.__init__(self, name, start_node_name, end_node_name)
        self.length = length
        self.diameter = diameter
        self.roughness = roughness
        self.minor_loss = minor_loss
        status_options = LinkStatus()
        if status is not None:
            self._base_status = status_options.str_to_status(status)
            if self._base_status == status_options.cv:
                self.current_status = status_options.open
            else:
                self.current_status = self._base_status


class Pump(Link):
    """
    Pump class that is inherited from Link
    """
    def __init__(self, name, start_node_name, end_node_name, info_type, info_value):
        """
        Parameters
        ----------
        name : string
            Name of the pump
        start_node_name : string
             Name of the start node
        end_node_name : string
             Name of the end node

        Other Parameters
        ----------------
        info_type : string
            Type of information provided about the pump. Options are 'POWER' or 'HEAD'.
        info_value : float or curve type
            Where power is a fixed value in KW, while a head curve is a Curve object.
        """
        Link.__init__(self, name, start_node_name, end_node_name)
        self.base_speed = 1.0
        self.current_speed = 1.0
        self.curve = None
        self.power = None
        self.info_type = info_type
        if info_type == 'HEAD':
            self.curve = info_value
        elif info_type == 'POWER':
            self.power = info_value
        else:
            raise RuntimeError('Pump info type not recognized. Options are HEAD or POWER.')

    def get_head_curve_coefficients(self):
        """
        Returns the A, B, C coefficients for a 1-point or a 3-point pump curve.
        Coefficient can only be calculated for pump curves.

        For a single point curve the coefficients are generated according to the following equation:

        A = 4/3 * H_1
        B = 1/3 * H_1/Q_1^2
        C = 2

        For a three point curve the coefficients are generated according to the following equation:
             When the first point is a zero flow: (All INP files we have come across)

             A = H_1
             C = ln((H_1 - H_2)/(H_1 - H_3))/ln(Q_2/Q_3)
             B = (H_1 - H_2)/Q_2^C

             When the first point is not zero, numpy fsolve is called to solve the following system of
             equation:

             H_1 = A - B*Q_1^C
             H_2 = A - B*Q_2^C
             H_3 = A - B*Q_3^C

        Multi point curves are currently not supported

        Parameters
        ----------
        pump_name : string
            Name of the pump

        Returns
        -------
        Tuple of pump curve coefficient (A, B, C). All floats.
        """


        # 1-Point curve
        if self.curve.num_points == 1:
            H_1 = self.curve.points[0][1]
            Q_1 = self.curve.points[0][0]
            A = (4.0/3.0)*H_1
            B = (1.0/3.0)*(H_1/(Q_1**2))
            C = 2
        # 3-Point curve
        elif self.curve.num_points == 3:
            Q_1 = self.curve.points[0][0]
            H_1 = self.curve.points[0][1]
            Q_2 = self.curve.points[1][0]
            H_2 = self.curve.points[1][1]
            Q_3 = self.curve.points[2][0]
            H_3 = self.curve.points[2][1]

            # When the first points is at zero flow
            if Q_1 == 0.0:
                A = H_1
                C = math.log((H_1 - H_2)/(H_1 - H_3))/math.log(Q_2/Q_3)
                B = (H_1 - H_2)/(Q_2**C)
            else:
                def curve_fit(x):
                    eq_array = [H_1 - x[0] + x[1]*Q_1**x[2],
                                H_2 - x[0] + x[1]*Q_2**x[2],
                                H_3 - x[0] + x[1]*Q_3**x[2]]
                    return eq_array
                coeff = fsolve(curve_fit, [200, 1e-3, 1.5])
                A = coeff[0]
                B = coeff[1]
                C = coeff[2]

        # Multi-point curve
        else:
            raise RuntimeError("Coefficient for Multipoint pump curves cannot be generated. ")

        return (A, B, C)

    def get_design_flow(self):
        """
        Returns the design flow value for the pump.
        Equals to the first point on the pump curve.

        """
        try:
            return self.curve.points[-1][0]
        except IndexError:
            raise IndexError("Curve point does not exist")


class Valve(Link):
    """
    Valve class that is inherited from Link
    """
    def __init__(self, name, start_node_name, end_node_name,
                 diameter=None, valve_type=None, minor_loss=None, setting=None):
        """
        Parameters
        ----------
        name : string
            Name of the valve
        start_node_name : string
             Name of the start node
        end_node_name : string
             Name of the end node

        Other Parameters
        ----------------
        diameter : float
            Diameter of the valve.
            Internal units must be meters (m)
        valve_type : float
            Type of valve. Options are 'PRV', etc
        minor_loss : float
            Pipe minor loss coefficient
        setting : float
            Valve setting.
        """
        Link.__init__(self, name, start_node_name, end_node_name)
        self.diameter = diameter
        self.valve_type = valve_type
        self.minor_loss = minor_loss
        self.base_setting = setting
        self.current_setting = setting
        status_options = LinkStatus()
        self._base_status = status_options.active
        self.current_status = status_options.active


class Curve(object):
    """
    Curve class.
    """
    def __init__(self, name, curve_type, points):
        """
        Parameters
        -------
        name : string
             Name of the curve
        curve_type :
             Type of curve. Options are Volume, Pump, Efficiency, Headloss.
        points :
             List of tuples with X-Y points.
        """
        self.name = name
        self.curve_type = curve_type
        self.points = points
        self.num_points = len(points)






