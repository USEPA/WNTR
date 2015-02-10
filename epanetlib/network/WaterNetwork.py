# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 10:07:42 2015

@author: aseth
"""
import copy
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
        self._nodes = {}
        self._links = {}
        
        # Initialize pattern and curve dictionaries
        self._patterns = {}
        self._curves = {}

        # Initialize Options dictionaries
        self._time_options = {}
        self._options = {}

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
        self._nodes[name] = junction
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
        self._nodes[name] = tank
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
        self._nodes[name] = reservoir
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
        self._links[name] = pipe
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
        self._links[name] = pump
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
        self._links[name] = valve
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
        self._patterns[name] = pattern_list

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
        self._curves[name] = xy_tuples_list

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
        self._time_options[name] = value

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
        self._options[name] = value

    def get_node(self, name):
        """
        Return the node object for a node name.

        Parameters
        -------
        name : string
            Name of the node.

        Return
        -------
        node : Node object
            Node object corresponding to "name".
        """
        return self._nodes[name]

    def get_link(self, name):
        """
        Return the link object for a link name.

        Parameters
        -------
        name : string
            Name of the link.

        Return
        -------
        link : Link object
            Link object corresponding to "name".
        """
        return self._links[name]


    def query_node_attribute(self, attribute, operation, value):
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
        nodes = []
        for i in self._nodes:
            node_attribute = self._nodes[i].get_attribute(attribute)
            if node_attribute is not None:
                if operation(node_attribute, value):
                    nodes.append(self._nodes[i])
        return nodes

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
        links = []
        for i in self._links:
            link_attribute = self._links[i].get_attribute(attribute)
            if link_attribute is not None:
                if operation(link_attribute, value):
                    links.append(self._links[i])
        return links

    def get_option(self, option_name):
        """
         Returns network option.

         Parameter
         -------
         option_name : string
             option name
        """
        for n in [option_name, option_name.upper()]:
            try:
                option_value = self._options[n]
                return option_value
            except KeyError:
                continue
        return None

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
        self._name = name

    def __str__(self):
        """
        Returns the name of the node when printing to a stream.
        """
        return self._name

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

    def name(self):
        """
        Returns the name of the node when printing to a stream.
        """
        return self._name


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
        self._link_name = link_name
        self._start_node_name = start_node_name
        self._end_node_name = end_node_name

    def __str__(self):
        """
        Returns the name of the link when printing to a stream.
        """
        return self._link_name

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

    def name(self):
        """
        Returns the name of the link.
        """
        return self._name


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
        self._base_demand = base_demand
        self._demand_pattern_name = demand_pattern_name
        self._elevation = elevation

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

    def get_attribute(self, attribute):
        """
        Returns a queried attribute of a junction.
        If attribute is not specified for that junction, returns None.

        Parameters
        ---------
        attribute : string
           Attribute to be returned

        Return
        -------
        attribute_value : float or string or None
           Value of the queried attribute
        """
        attribute_u = attribute.upper()
        if attribute_u == 'BASE_DEMAND':
            return self._base_demand
        elif attribute_u == 'DEMAND_PATTERN_NAME':
            return self._demand_pattern_name
        elif attribute_u == 'ELEVATION':
            return self._elevation
        else:
            return None

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
        self._base_head = base_head
        self._head_pattern_name = head_pattern_name

    def get_attribute(self, attribute):
        """
        Returns a queried attribute of a reservoir.
        If attribute is not specified for that reservoir, returns None.

        Parameters
        ---------
        attribute : string
           Attribute to be returned

        Return
        -------
        attribute_value : float or string or None
           Value of the queried attribute
        """
        attribute_u = attribute.upper()
        if attribute_u == 'BASE_HEAD':
            return self._base_head
        elif attribute_u == 'HEAD_PATTERN_NAME':
            return self._head_pattern_name
        else:
            return None

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
        self._elevation = elevation
        self._init_level = init_level
        self._min_level = min_level
        self._max_level = max_level
        self._diameter = diameter
        self._min_vol = min_vol
        self._vol_curve = vol_curve

    def get_attribute(self, attribute):
        """
        Returns a queried attribute of a tank.
        If attribute is not specified for that tank, returns None.

        Parameters
        ---------
        attribute : string
           Attribute to be returned

        Return
        -------
        attribute_value : float or string or None
           Value of the queried attribute
        """
        attribute_u = attribute.upper()
        if attribute_u == 'ELEVATION':
            return self._elevation
        elif attribute_u == 'INIT_LEVEL':
            return self._init_level
        elif attribute_u == 'MIN_LEVEL':
            return self._min_level
        elif attribute_u == 'MAX_LEVEL':
            return self._max_level
        elif attribute_u == 'DIAMETER':
            return self._diameter
        elif attribute_u == 'MIN_VOL':
            return self._min_vol
        elif attribute_u == 'VOL_CURVE':
            return self._vol_curve
        else:
            return None

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
        self._length = length
        self._diameter = diameter
        self._roughness = roughness
        self._minor_loss = minor_loss
        self._status = status

    def get_attribute(self, attribute):
        """
        Returns a queried attribute of a pipe.
        If attribute is not specified for that pipe, returns None.

        Parameters
        ---------
        attribute : string
           Attribute to be returned

        Return
        -------
        attribute_value : float or string or None
           Value of the queried attribute
        """
        attribute_u = attribute.upper()
        if attribute_u == 'LENGTH':
            return self._length
        elif attribute_u == 'DIAMETER':
            return self._diameter
        elif attribute_u == 'ROUGHNESS':
            return self._roughness
        elif attribute_u == 'MINOR_LOSS':
            return self._minor_loss
        elif attribute_u == 'STATUS':
            return self._status
        else:
            return None


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
        self._curve_name = curve_name

    def get_attribute(self, attribute):
        """
        Returns a queried attribute of a pump.
        If attribute is not specified for that pump, returns None.

        Parameters
        ---------
        attribute : string
           Attribute to be returned

        Return
        -------
        attribute_value : float or string or None
           Value of the queried attribute
        """
        attribute_u = attribute.upper()
        if attribute_u == 'START_NODE_NAME':
            return self._start_node_name
        elif attribute_u == 'END_NODE_NAME':
            return self._end_node_name
        elif attribute_u == 'CURVE_NAME':
            return self._curve_name
        else:
            return None

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
        self._diameter = diameter
        self._valve_type = valve_type
        self._minor_loss = minor_loss
        self._setting = setting

    def get_attribute(self, attribute):
        """
        Returns a queried attribute of a valve.
        If attribute is not specified for that valve, returns None.

        Parameters
        ---------
        attribute : string
           Attribute to be returned

        Return
        -------
        attribute_value : float or string or None
           Value of the queried attribute
        """
        attribute_u = attribute.upper()
        if attribute_u == 'START_NODE_NAME':
            return self._start_node_name
        elif attribute_u == 'END_NODE_NAME':
            return self._end_node_name
        elif attribute_u == 'DIAMETER':
            return self._diameter
        elif attribute_u == 'VALVE_TYPE':
            return self._valve_type
        elif attribute_u == 'MINOR_LOSS':
            return self._minor_loss
        elif attribute_u == 'SETTING':
            return self._setting
        else:
            return None


