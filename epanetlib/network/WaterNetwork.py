# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 10:07:42 2015

@author: aseth
"""
import copy
import networkx as nx
import numpy as np

class WaterNetwork(object):
    """
    The base water network class. 
    """
    def __init__(self, inp_file_name=None):
        """
        Optional Parameters
        ----------
        inp_file_name : string
            Name of the epanet inp file to load network parameters.
        
        Example
        ---------
        >>> wn = WaterNetwork()
        
        >>> wn2 = WaterNetwork('Net3.inp')
        """

        # Initialize Network size parameters
        self._num_nodes = 0
        self._num_links = 0
        self._num_junctions = 0
        self._num_reservoirs = 0
        self._num_tanks = 0
        self._num_pipes = 0
        self._num_pumps = 0
        self._num_valves = 0

        # Initialize node an link lists
        # Dictionary of node or link objects indexed by their names
        self.nodes = {}
        self.links = {}

        # Initialize pattern and curve dictionaries
        # Dictionary of pattern or curves indexed by their names
        self.patterns = {}
        self.curves = {}

        # Initialize Options dictionaries
        self.time_options = {}
        self.options = {}

        # Time controls are saved as a dictionary as follows:
        # {'Link name': {'open_times': [1, 5, ...], 'closed_times': [3, 7, ...]}},
        # where times are in minutes
        self.time_controls = {}

        # NetworkX Graph to store the pipe connectivity and node coordinates
        self.graph = nx.MultiDiGraph(data=None)

    def copy(self):
        """
        Copy a water network object
        Return
        ------
        A copy of the water network

        Example
        ------
        >>> wn = WaterNetwork('Net3.inp')
        >>> wn2 = wn.copy()
        """
        return copy.deepcopy(self)

    def add_junction(self, name, base_demand=None, demand_pattern_name=None, elevation=None):
        """
        Add a junction to the network.
        Parameters
        -------
        name : string
            Name of the junction.

        Optional Parameters
        -------
        base_demand : float
            Base demand at the junction.
            Internal units must be cubic meters per second (m^3/s).
        demand_pattern_name : string
            Name of the demand pattern.
        elevation : float
            Elevation of the junction.
            Internal units must be meters (m).

        """
        junction = Junction(name, base_demand, demand_pattern_name, elevation)
        self.nodes[name] = junction
        self._num_nodes += 1
        self._num_junctions += 1

    def add_tank(self, name, elevation=None, init_level=None,
                 min_level=None, max_level=None, diameter=None,
                 min_vol=None, vol_curve=None):
        """
        Method to add tank to a water network object.

        Parameters
        ------
        name : string
            Name of the tank.

        Optional Parameters
        -------
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
        """
        tank = Tank(name, elevation, init_level,
                 min_level, max_level, diameter,
                 min_vol, vol_curve)
        self.nodes[name] = tank
        self._num_nodes += 1
        self._num_tanks += 1


    def add_reservoir(self, name, base_head=None, head_pattern_name=None):
        """
        Method to add reservoir to a water network object.

        Parameters
        ------
        name : string
            Name of the reservoir.

        Optional Parameters
        -------
        base_head : float
            Base head at the reservoir.
            Internal units must be meters (m).
        head_pattern_name : string
            Name of the head pattern.
        """
        reservoir = Reservoir(name, base_head, head_pattern_name)
        self.nodes[name] = reservoir
        self._num_nodes += 1
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

        Optional Parameters
        -----------
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
        pipe = Pipe(name, start_node_name, end_node_name, length,
                    diameter, roughness, minor_loss, status)
        self.links[name] = pipe
        self._num_links += 1
        self._num_pipes += 1

    def add_pump(self, name, start_node_name, end_node_name, curve_name=None):
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

        Optional Parameters
        ----------
        curve_name : string
            Name of the pump curve.
        """
        pump = Pump(name, start_node_name, end_node_name, curve_name)
        self.links[name] = pump
        self._num_links += 1
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

        Optional Parameters
        ----------
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
        valve = Valve(self, name, start_node_name, end_node_name,
                      diameter, valve_type, minor_loss, setting)
        self.links[name] = valve
        self._num_links += 1
        self._num_valves += 1

    def add_pattern(self, name, pattern_list):
        """
        Method to add pattern to a water network object.

        Parameters
        ---------
        name : string
            name of the pattern
        pattern_list : list of floats
            A list of floats that make up the pattern.
        """
        self.patterns[name] = pattern_list

    def add_curve(self, name, xy_tuples_list):
        """
        Method to add a curve to a water network object.

        Parameters
        ---------
        name : string
            Name of the curve
        xy_tuples_list : list of tuples
            List of X-Y coordinate tuples on the curve.
        """
        self.curves[name] = xy_tuples_list

    def add_time_parameter(self, name, value):
        """
        Method to add a time parameter to a water network object.

        Parameters
        -------
        name : string
            Name of the time option.
        value:
            Value of the time option. Can be tuple representing (Hours, Minutes) or (Hours, AM/PM).
        """
        self.time_options[name] = value

    def add_option(self, name, value):
        """
        Method to add a options to a water network object.

        Parameters
        -------
        name : string
            Name of the option.
        value:
            Value of the option.
        """
        self.options[name] = value


    def query_node_attribute(self, attribute, operation, value=0.0):
        """ Query node attributes, for example get all nodes with elevation <= threshold

        Parameters
        ----------
        attribute: string
            Pipe attribute

        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

        value: scalar
            threshold

        Returns
        -------
        nodes : list of Node objects
            list of nodes
        """
        node_attribute_dict = {}
        for name, node in self.nodes.iteritems():
            try:
                node_attribute = getattr(node, attribute)
            except AttributeError:
                node_attribute = None
            if operation(node_attribute, value):
                node_attribute_dict[name] = node_attribute
        return node_attribute_dict

    def query_link_attribute(self, attribute, operation, value):
        """ Query pipe attributes, for example get all pipe diameters > threshold

        Parameters
        ----------
        attribute: string
            Pipe attribute

        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

        value: scalar
            threshold

        Return
        -------
        pipes : list
            list of links
        """
        link_attribute_dict = {}
        for name, link in self.links.iteritems():
            try:
                link_attribute = getattr(link, attribute)
            except AttributeError:
                link_attribute = None
            if operation(link_attribute, value):
                link_attribute_dict[name] = link_attribute
        return link_attribute_dict

    def set_graph_node_attribute(self, attribute, operation, value=0.0):
        """ Set node attribute in the networkX graph, for example get all nodes with elevation <= threshold

        Parameters
        ----------
        attribute: string
            Pipe attribute

        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

        value: scalar
            threshold

        """
        node_attribute_dict = {}
        for name, node in self.nodes.iteritems():
            try:
                node_attribute = getattr(node, attribute)
            except AttributeError:
                node_attribute = None
            if operation(node_attribute, value):
                node_attribute_dict[name] = node_attribute
        nx.set_node_attributes(self.graph, attribute, node_attribute_dict)

    def set_graph_link_attribute(self, attribute, operation, value):
        """ Set link attributes in the networkX graph, for example get all pipe diameters > threshold

        Parameters
        ----------
        attribute: string
            Pipe attribute

        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

        value: scalar
            threshold

        """
        link_attribute_dict = {}
        for name, link in self.links.iteritems():
            try:
                link_attribute = getattr(link, attribute)
            except AttributeError:
                link_attribute = None
            if operation(link_attribute, value):
                link_attribute_dict[(link.start_node_name, link.end_node_name, name)] = link_attribute
        nx.set_edge_attributes(self.graph, attribute, link_attribute_dict)


    def add_time_control(self, link, open_times=[], closed_times=[]):
        """
        Add time controls to the network.

        Parameter
        -------
        link : string
            Name of the link
        open_times : list of integers
            List of times (in minutes) when the link is opened
        closed_times : list of integers
            List of times (in minutes) when the link is closed

        """
        if link not in self.time_controls:
            self.time_controls[link] = {'open_times': [i for i in open_times], 'closed_times': [i for i in closed_times]}
        else:
            self.time_controls[link]['open_times'] += open_times
            self.time_controls[link]['closed_times'] += closed_times


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

        Example
        ---------
        >>> node2 = Node('North Lake','Reservoir')
        """
        self.name = name

    def __str__(self):
        """
        Returns the name of the node when printing to a stream.
        """
        return self.name

    def copy(self):
        """
        Copy a node object

        Return
        ------
        A copy of the node.

        Example
        ------
        >>> node1 = Node('North Lake', 'Reservoir')
        >>> node2 = node1.copy()

        """
        return copy.deepcopy(self)


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

        Example
        ---------
        >>> link1 = Link('Pipe 1','Pipe', 'Node 153', 'Node 159')
        """
        self.link_name = link_name
        self.start_node_name = start_node_name
        self.end_node_name = end_node_name

    def __str__(self):
        """
        Returns the name of the link when printing to a stream.
        """
        return self.link_name

    def copy(self):
        """
        Copy a link object

        Return
        ------
        A copy of the link.

        Example
        ------
        >>> link1 = Link('Pipe 1','Pipe', 'Node 153', 'Node 159')
        >>> link2 = link1.copy()
        """
        return copy.deepcopy(self)


class Junction(Node):
    """
    Junction class that is inherited from Node
    """
    def __init__(self, name, base_demand=None, demand_pattern_name=None, elevation=None):
        """
        Parameters
        ------
        name : string
            Name of the junction.

        Optional Parameters
        -------
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
        self.demand_pattern_name = demand_pattern_name
        self.elevation = elevation

    def copy(self):
        """
        Copy a junction object

        Return
        ------
        A copy of the junction.

        Example
        ------
        >>> junction1 = Junction('Node 1')
        >>>
        """
        return copy.deepcopy(self)

class Reservoir(Node):
    """
    Reservoir class that is inherited from Node
    """
    def __init__(self, name, base_head=None, head_pattern_name=None):
        """
        Parameters
        ------
        name : string
            Name of the reservoir.

        Optional Parameters
        -------
        base_head : float
            Base head at the reservoir.
            Internal units must be meters (m).
        head_pattern_name : string
            Name of the head pattern.
        """
        Node.__init__(self, name)
        self.base_head = base_head
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
        ------
        name : string
            Name of the tank.

        Optional Parameters
        -------
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
        self.min_level = min_level
        self.max_level = max_level
        self.diameter = diameter
        self.min_vol = min_vol
        self.vol_curve = vol_curve

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

        Optional Parameters
        -----------
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
        self.status = status


class Pump(Link):
    """
    Pump class that is inherited from Link
    """
    def __init__(self, name, start_node_name, end_node_name, curve_name=None):
        """
        Parameters
        ----------
        name : string
            Name of the pump
        start_node_name : string
             Name of the start node
        end_node_name : string
             Name of the end node

        Optional Parameters
        ----------
        curve_name : string
            Name of the pump curve.
        """
        Link.__init__(self, name, start_node_name, end_node_name)
        self.curve_name = curve_name

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

        Optional Parameters
        ----------
        diameter : float
            Diameter of the valve.
            Internal units must be meters (m)
        valve_type : float
            Type of valve. Options are 'PRV', etc
        minor_loss : float
            Pipe minor loss coefficient
        setting : string
            Valve status. Options are 'Open', 'Closed', etc
        """
        Link.__init__(self, name, start_node_name, end_node_name)
        self.diameter = diameter
        self.valve_type = valve_type
        self.minor_loss = minor_loss
        self.setting = setting


