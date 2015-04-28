# -*- coding: utf-8 -*-
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

"""
TODO 1. Volume curve object should be an attribute of the tank.
TODO 2. Conditional controls are only supported for Tank pump relation. Other control should be added.
TODO 3. Multi-point curve.
"""

import copy
import networkx as nx
import math
from scipy.optimize import fsolve


class WaterNetworkModel(object):

    """
    The base water network model class.
    """
    def __init__(self):
        """
        Example
        ---------
        >>> wn = WaterNetworkModel()
        
        """

        # Network name
        self.name = None

        # Initialize Network size parameters
        self._num_junctions = 0
        self._num_reservoirs = 0
        self._num_tanks = 0
        self._num_pipes = 0
        self._num_pumps = 0
        self._num_valves = 0

        # Initialize node an link lists
        # Dictionary of node or link objects indexed by their names
        self._nodes = {}
        self._links = {}

        # Initialize pattern and curve dictionaries
        # Dictionary of pattern or curves indexed by their names
        self._patterns = {}

        # Initialize Options dictionaries
        self.time_options = {}
        self.options = {}

        # Time controls are saved as a dictionary as follows:
        # {'Link name': {'open_times': [1, 5, ...], 'closed_times': [3, 7, ...]}},
        # where times are in minutes
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

    def copy(self):
        """
        Copy a water network object
        Return
        ------
        A copy of the water network

        Example
        ------
        >>> wn = WaterNetwork()
        >>> wn2 = wn.copy()
        """
        return copy.deepcopy(self)

    def get_node(self, name):
        """
        Returns node object of a provided name

        Parameter
        --------
        name : string
            name of the node
        """
        return self._nodes[name]

    def get_link(self, name):
        """
        Returns link object of a provided name

        Parameter
        --------
        name : string
            name of the link
        """
        return self._links[name]

    def get_curve(self, name):
        """
        Returns curve object of a provided name

        Parameter
        --------
        name : string
            name of the curve
        """
        return self._curves[name]

    def get_pattern(self, name):
        """
        Returns pattern object of a provided name

        Parameter
        --------
        name : string
            name of the pattern
        """
        return self._patterns[name]

    def add_junction(self, name, base_demand=None, demand_pattern_name=None, elevation=None, coordinates=None):
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
        coordinates : tuple of floats
            X-Y coordinates of the node location

        """
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
        coordinates : tuple of floats
            X-Y coordinates of the node location
        """
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
        coordinates : tuple of floats
            X-Y coordinates of the node location
        """
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
        # Add to list of cv
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
        self._graph.remove_edge(self._links[name]._start_node_name, self._links[name]._end_node_name, key=name)
        self._links.pop(name)
        self._num_pipes -= 1

    def add_leak(self, leak_name, pipe_name, area, leak_discharge_coeff = 0.75):
        """
        Method to add a leak to the water network object.

        Parameters
        ----------
        leak_name: string
           Name of the leak
        pipe_name: string
           Name of the pipe where the leak ocurrs.
           Currently assuming the leak ocurrs halfway between nodes.
        area: float
           Area of the leak in m^2
        """

        # Get attributes of original pipe
        start_node_name = self.get_link(pipe_name)._start_node_name
        end_node_name = self.get_link(pipe_name)._end_node_name
        base_status = self.get_link(pipe_name)._base_status
        open_times = self.get_link(pipe_name)._open_times
        closed_times = self.get_link(pipe_name)._closed_times
        length = self.get_link(pipe_name).length
        diameter = self.get_link(pipe_name).diameter
        roughness = self.get_link(pipe_name).roughness
        minor_loss = self.get_link(pipe_name).minor_loss

        # Remove original pipe
        self.remove_pipe(pipe_name)

        # Add a leak node
        leak = Leak(leak_name, pipe_name, area, leak_discharge_coeff)
        self._nodes[leak_name] = leak
        self._graph.add_node(leak_name)
        self._num_junctions +=1

        # Add pipe from start node to leak
        self.add_pipe(pipe_name+'a',start_node_name, leak_name, length/2.0, diameter, roughness, minor_loss)

        # Add pipe from leak to end node
        self.add_pipe(pipe_name+'b', leak_name, end_node_name, length/2.0, diameter, roughness, minor_loss)

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

        Optional Parameters
        ----------
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
        ---------
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
        ---------
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
        -------
        name : string
            Name of the time option.
        value:
            Value of the time option. Must be in minutes.

        Example
        -------
        START CLOCKTIME = 6 PM can be set using
        >>> wn.add_time_parameter('START CLOCKTIME', 1080)
        """
        self.time_options[name.upper()] = value

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
        self.options[name.upper()] = value
    
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

        Return
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

        Parameter
        -------
        link_name : string
            Name of the link
        open_times : list of integers
            List of times (in minutes) when the link is opened
        closed_times : list of integers
            List of times (in minutes) when the link is closed

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

        Return:
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


        Return:
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

        Return
        ------
        Number of nodes.
        """
        return len(self._nodes)

    def num_links(self):
        """
        Number of links.

        Return
        ------
        """
        return len(self._links)

    def curves(self):
        """
        A generator to iterate over all curves

        Return:
        curve_name, curve
        """
        for curve_name, curve in self._curves.iteritems():
            yield curve_name, curve

    def get_all_nodes_copy(self):
        """
        Return a copy of the dictionary with all nodes.

        Parameters
        -------

        Return
        -------
        node : dictionary
            Node name to node.
        """
        return copy.deepcopy(self._nodes)

    def get_all_links_copy(self):
        """
        Return a copy of the dictionary with all nodes.

        Parameters
        -------

        Return
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
        ---------
        node_name : string
            Name of the node.

        Return
        ------
        A list of link names connected to the node
        """
        in_edges = self._graph.in_edges(node_name, data=False, keys=True)
        out_edges = self._graph.out_edges(node_name, data=False, keys=True)
        edges = in_edges + out_edges
        list_of_links = []
        for edge_tuple in edges:
            list_of_links.append(edge_tuple[2])

        return list_of_links

    def set_nominal_pressures(self, res = None, constant_nominal_pressure = None):
        """
        Takes a results object and adds nominal pressures to each junction.
        """
        if res is not None and constant_nominal_pressure is None:
            for junction_name,junction in self.nodes(Junction):
                if res.node['pressure'][junction_name][0] < 0.0:
                    print 'error: base case had negative pressure at junction ',junction_name
                    quit()
                else:
                    min_P = res.node['pressure'][junction_name][0]
                for i in xrange(1,len(res.node['pressure'][junction_name])):
                    if res.node['pressure'][junction_name][i] < 0.0:
                        print 'error: base case had negative pressure at junction ',junction_name
                        quit()
                    elif res.node['pressure'][junction_name][i] < min_P:
                        min_P = res.node['pressure'][junction_name][i]
                junction.PF = 0.8*min_P
                junction.P0 = 0.0
        elif constant_nominal_pressure is not None and res is None:
            for junction_name,junction in self.nodes(Junction):
                junction.PF = constant_nominal_pressure
                junction.P0 = 0.0
        else:
            print 'error: either you have not specified any nominal pressure or you have tried to specify in multiple ways'
            quit()

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
        self._base_status = 'OPEN'
        self._open_times = list()
        self._closed_times = list()

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
        return self._base_status

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

class Leak(Node):
    """
    Leak class that is inherited from Node
    """
    def __init__(self, leak_name, pipe_name, area, leak_discharge_coeff):
        """
        Parameters
        ----------
        leak_name: string
           Name of the leak.
        pipe_name: string
           Name of the pipe where the leak ocurrs
        area: float
           Area of the leak in m^2
        """
        Node.__init__(self, leak_name)
        self.pipe_name = pipe_name
        self.area = area
        self.leak_discharge_coeff = leak_discharge_coeff
        self.elevation = 0.0

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
        if status is not None:
            self._base_status = status.upper()


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

        Optional Parameters
        ----------
        info_type : string
            Type of information provided about the pump. Options are 'POWER' or 'HEAD'.
        info_value : float or curve type
            Where power is a fixed value in KW, while a head curve is a Curve object.
        """
        Link.__init__(self, name, start_node_name, end_node_name)
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
        -------
        pump_name : string
            Name of the pump

        Return
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

        Optional Parameters
        ----------
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
        self.setting = setting
        self._base_status = 'OPEN'


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






