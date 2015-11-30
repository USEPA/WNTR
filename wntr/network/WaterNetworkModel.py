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
from wntr.utils import convert
import wntr.network
import numpy as np
import warnings
import sys

class WaterNetworkModel(object):

    """
    The base water network model class.
    """
    def __init__(self, inp_file_name = None):
        """
        Examples
        ---------
        >>> wn = WaterNetworkModel()
        
        Parameters
        ----------
        inp_file_name: string
           directory and filename of inp file to load into the WaterNetworkModel object.

        """

        # Network name
        self.name = None

        # Time parameters
        self.sim_time = 0.0
        self.prev_sim_time = -np.inf # the last time at which results were accepted

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
        self._junctions = {}
        self._tanks = {}
        self._reservoirs = {}
        self._pipes = {}
        self._pumps = {}
        self._valves = {}

        # Initialize pattern and curve dictionaries
        # Dictionary of pattern or curves indexed by their names
        self._patterns = {}
        self._curves = {}

        # Initialize options object
        self.options = WaterNetworkOptions()

        # A list of control objects
        self._controls = []

        # Name of pipes that are check valves
        self._check_valves = []

        # NetworkX Graph to store the pipe connectivity and node coordinates
        #self._graph = nx.MultiDiGraph(data=None)
        self._graph = wntr.network.WntrMultiDiGraph()

        self._Htol = 0.00015 # Head tolerance in meters.
        self._Qtol = 2.8e-5 # Flow tolerance in m^3/s.

        if inp_file_name:
            parser = wntr.network.ParseWaterNetwork()
            parser.read_inp_file(self, inp_file_name)

    def add_junction(self, name, base_demand=0.0, demand_pattern_name=None, elevation=0.0, coordinates=None):
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
        base_demand = float(base_demand)
        elevation = float(elevation)
        junction = Junction(name, base_demand, demand_pattern_name, elevation)
        self._nodes[name] = junction
        self._junctions[name] = junction
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        nx.set_node_attributes(self._graph, 'type', {name:'junction'})
        self._num_junctions += 1

    def add_tank(self, name, elevation=0.0, init_level=3.048,
                 min_level=0.0, max_level=6.096, diameter=15.24,
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
        vol_curve_name : Curve object
            Curve object
        coordinates : tuple of floats
            X-Y coordinates of the node location
        """
        elevation = float(elevation)
        init_level = float(init_level)
        min_level = float(min_level)
        max_level = float(max_level)
        diameter = float(diameter)
        if min_vol is not None:
            min_vol = float(min_vol)
        assert init_level >= min_level, "Initial tank level must be greater than or equal to the tank minimum level."
        assert init_level <= max_level, "Initial tank level must be less than or equal to the tank maximum level."
        tank = Tank(name, elevation, init_level,
                 min_level, max_level, diameter,
                 min_vol, vol_curve)
        self._nodes[name] = tank
        self._tanks[name] = tank
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        nx.set_node_attributes(self._graph, 'type', {name:'tank'})
        self._num_tanks += 1

    def _get_all_tank_controls(self):

        tank_controls = []

        for tank_name, tank in self.tanks():

            # add the tank controls
            all_links = self.get_links_for_node(tank_name,'ALL')

            # First take care of the min level
            min_head = tank.min_level+tank.elevation
            for link_name in all_links:
                link = self.get_link(link_name)
                if isinstance(link, Pipe):
                    if link.cv:
                        if link.end_node()==tank_name:
                            continue
                if isinstance(link, Pump):
                    if link.end_node()==tank_name:
                        continue
            
                close_control_action = wntr.network.TargetAttributeControlAction(link, 'status', LinkStatus.closed)
                open_control_action = wntr.network.TargetAttributeControlAction(link, 'status', LinkStatus.opened)
            
                control = wntr.network.MultiConditionalControl([(tank,'head'),(tank,'prev_head')],[np.greater,np.less_equal],[min_head+self._Htol,min_head+self._Htol],open_control_action)
                control._partial_step_for_tanks = False
                control._priority = 0
                control.name = tank.name()+link_name+' opened because head is greater than min head'
                tank_controls.append(control)
            
                control = wntr.network.ConditionalControl((tank,'head'),np.less_equal,min_head,close_control_action)
                control._priority = 1
                control.name = tank.name()+link_name+' closed because head is less than min head'
                tank_controls.append(control)
            
                if link.start_node() == tank_name:
                    other_node_name = link.end_node()
                else:
                    other_node_name = link.start_node()
                other_node = self.get_node(other_node_name)
                control = wntr.network.MultiConditionalControl([(tank,'head'),(tank,'head')],[np.less_equal,np.less],[min_head+self._Htol,(other_node,'head')],open_control_action)
                control._priority = 2
                control.name = tank.name()+link_name+' opened because tank head is below min head but flow should be in'
                tank_controls.append(control)
            
                #control = wntr.network.MultiConditionalControl([(tank,'head'),(other_node,'head')],[np.less,np.less],[min_head+self._Htol,min_head+self._Htol], close_control_action)
                #control._priority = 2
                #self.add_control(control)
            
            # Now take care of the max level
            max_head = tank.max_level+tank.elevation
            for link_name in all_links:
                link = self.get_link(link_name)
                if isinstance(link, Pipe):
                    if link.cv:
                        if link.start_node()==tank_name:
                            continue
                if isinstance(link, Pump):
                    if link.start_node()==tank_name:
                        continue
            
                close_control_action = wntr.network.TargetAttributeControlAction(link, 'status', LinkStatus.closed)
                open_control_action = wntr.network.TargetAttributeControlAction(link, 'status', LinkStatus.opened)
            
                control = wntr.network.MultiConditionalControl([(tank,'head'),(tank,'prev_head')],[np.less,np.greater_equal],[max_head-self._Htol,max_head-self._Htol],open_control_action)
                control._partial_step_for_tanks = False
                control._priority = 0
                control.name = tank.name()+link_name+'opened because head is less than max head'
                tank_controls.append(control)
            
                control = wntr.network.ConditionalControl((tank,'head'),np.greater_equal,max_head,close_control_action)
                control._priority = 1
                control.name = tank.name()+link_name+' closed because head is greater than max head'
                tank_controls.append(control)
            
                if link.start_node() == tank_name:
                    other_node_name = link.end_node()
                else:
                    other_node_name = link.start_node()
                other_node = self.get_node(other_node_name)
                control = wntr.network.MultiConditionalControl([(tank,'head'),(tank,'head')],[np.greater_equal,np.greater],[max_head-self._Htol,(other_node,'head')],open_control_action)
                control._priority = 2
                control.name = tank.name()+link_name+' opened because head above max head but flow should be out'
                tank_controls.append(control)
            
                #control = wntr.network.MultiConditionalControl([(tank,'head'),(other_node,'head')],[np.greater,np.greater],[max_head-self._Htol,max_head-self._Htol], close_control_action)
                #control._priority = 2
                #self.add_control(control)

        return tank_controls

    def add_reservoir(self, name, base_head=0.0, head_pattern_name=None, coordinates=None):
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
        base_head = float(base_head)
        reservoir = Reservoir(name, base_head, head_pattern_name)
        self._nodes[name] = reservoir
        self._reservoirs[name] = reservoir
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        nx.set_node_attributes(self._graph, 'type', {name:'reservoir'})
        self._num_reservoirs += 1

    def add_pipe(self, name, start_node_name, end_node_name, length=304.8,
                 diameter=0.3048, roughness=100, minor_loss=0.0, status='OPEN', check_valve_flag=False):
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
            Pipe status. Options are 'Open' or 'Closed'
        check_valve_flag : bool
            True if the pipe has a check valve
            False if the pipe does not have a check valve
        """
        length = float(length)
        diameter = float(diameter)
        roughness = float(roughness)
        minor_loss = float(minor_loss)
        pipe = Pipe(name, start_node_name, end_node_name, length,
                    diameter, roughness, minor_loss, status, check_valve_flag)
        # Add to list of cv
        if check_valve_flag:
            self._check_valves.append(name)

        self._links[name] = pipe
        self._pipes[name] = pipe
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        nx.set_edge_attributes(self._graph, 'type', {(start_node_name, end_node_name, name):'pipe'})
        self._num_pipes += 1

    def _get_cv_controls(self):
        cv_controls = []
        for pipe_name in self._check_valves:
            pipe = self.get_link(pipe_name)

            close_control_action = wntr.network.TargetAttributeControlAction(pipe, 'status', LinkStatus.closed)
            open_control_action = wntr.network.TargetAttributeControlAction(pipe, 'status', LinkStatus.opened)
            
            control = wntr.network._CheckValveHeadControl(self, pipe, np.greater, self._Htol, open_control_action)
            control._priority = 0
            control.name = pipe.name()+'opened because of cv head control'
            cv_controls.append(control)

            control = wntr.network._CheckValveHeadControl(self, pipe, np.less, -self._Htol, close_control_action)
            control._priority = 3
            control.name = pipe.name()+' closed because of cv head control'
            cv_controls.append(control)

            control = wntr.network.ConditionalControl((pipe,'flow'),np.less, -self._Qtol, close_control_action)
            control._priority = 3
            control.name = pipe.name()+' closed because negative flow in cv'
            cv_controls.append(control)

        return cv_controls

    def add_pump(self, name, start_node_name, end_node_name, info_type='POWER', info_value=50.0):
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
        self._pumps[name] = pump
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        nx.set_edge_attributes(self._graph, 'type', {(start_node_name, end_node_name, name):'pump'})
        self._num_pumps += 1

    def _get_pump_controls(self):
        pump_controls = []
        for pump_name, pump in self.pumps():

            close_control_action = wntr.network.TargetAttributeControlAction(pump, '_cv_status', LinkStatus.closed)
            open_control_action = wntr.network.TargetAttributeControlAction(pump, '_cv_status', LinkStatus.opened)
        
            control = wntr.network._CheckValveHeadControl(self, pump, np.greater, self._Htol, open_control_action)
            control._priority = 0
            control.name = pump.name()+' opened because of cv head control'
            pump_controls.append(control)
        
            control = wntr.network._CheckValveHeadControl(self, pump, np.less, -self._Htol, close_control_action)
            control._priority = 3
            control.name = pump.name()+' closed because of cv head control'
            pump_controls.append(control)
        
            control = wntr.network.ConditionalControl((pump,'flow'),np.less, -self._Qtol, close_control_action)
            control._priority = 3
            control.name = pump.name()+' closed because negative flow in pump'
            pump_controls.append(control)

        return pump_controls

    def add_valve(self, name, start_node_name, end_node_name,
                 diameter=0.3048, valve_type='PRV', minor_loss=0.0, setting=0.0):
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
        setting : float or string
            pressure setting for PRV, PSV, or PBV
            flow setting for FCV
            loss coefficient for TCV
            name of headloss curve for GPV
        """
        valve = Valve(name, start_node_name, end_node_name,
                      diameter, valve_type, minor_loss, setting)
        self._links[name] = valve
        self._valves[name] = valve
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        nx.set_edge_attributes(self._graph, 'type', {(start_node_name, end_node_name, name):'valve'})
        self._num_valves += 1

    def _get_valve_controls(self):
        valve_controls = []
        for valve_name, valve in self.valves():

            close_control_action = wntr.network.TargetAttributeControlAction(valve, '_status', LinkStatus.closed)
            open_control_action = wntr.network.TargetAttributeControlAction(valve, '_status', LinkStatus.opened)
            active_control_action = wntr.network.TargetAttributeControlAction(valve, '_status', LinkStatus.active)
        
            control = wntr.network._PRVControl(self, valve, self._Htol, self._Qtol, close_control_action, open_control_action, active_control_action)
            control.name = valve.name()+' prv control'
            valve_controls.append(control)

        return valve_controls
        
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

    def add_control(self, control_object):
        """
        Add a control to the network.

        Parameters
        ----------
        control_object : An object derived from the Control object
        """
        self._controls.append(control_object)

    def remove_control(self, control_object):
        """
        A method to remove a control from the network. If the control
        is not present, an exception is raised.

        Parameters
        ----------
        control_object : An object derived from the Control object
        """
        self._controls.remove(control_object)

    def discard_control(self, control_object):
        """
        A method to remove a control from the network if it is
        present. If the control is not present, an exception is not
        raised.

        Parameters
        ----------
        control_object : An object derived from the Control object
        """
        try:
            self._controls.remove(control_object)
        except ValueError:
            pass

    def add_pump_outage(self, pump_name, start_time, end_time):
        pump = self.get_link(pump_name)
        opened_action_obj = wntr.network.TargetAttributeControlAction(pump, 'status', LinkStatus.opened)
        closed_action_obj = wntr.network.TargetAttributeControlAction(pump, 'status', LinkStatus.closed)

        control = wntr.network.TimeControl(self, end_time, 'SIM_TIME', False, opened_action_obj)
        control._priority = 0
        self.add_control(control)

        control = wntr.network.TimeControl(self, start_time, 'SIM_TIME', False, closed_action_obj)
        control._priority = 3
        self.add_control(control)

    def all_pump_outage(self, start_time, end_time):
        for pump_name, pump in self.pumps():
            self.add_pump_outage(pump_name, start_time, end_time)

    def remove_link(self, name):
        """
        Method to remove a link from the water network object. Note
        that any controls associated with this link will be discarded.

        Parameters
        ----------
        name: string
           Name of the link to be removed
        """
        link = self.get_link(name)
        if link.cv:
            self._check_valves.remove(name)
            warnings.warn('You are removing a pipe with a check valve.')
        self._graph.remove_edge(link.start_node(), link.end_node(), key=name)
        self._links.pop(name)
        if isinstance(link, Pipe):
            self._num_pipes -= 1
            self._pipes.pop(name)
        elif isinstance(link, Pump):
            self._num_pumps -= 1
            self._pumps.pop(name)
        elif isinstance(link, Valve):
            self._num_valves -= 1
            self._valves.pop(name)
        else:
            raise RuntimeError('Link Type not Recognized')

        warnings.warn('Michael needs to update the remove_link method')
        # remove controls
        #if name in self.time_controls.keys():
        #    self.time_controls.pop(name)
        #    warnings.warn('A time control associated with link '+name+' has been removed as well as the link.')
        #
        #if name in self.conditional_controls.keys():
        #    self.conditional_controls.pop(name)
        #    warnings.warn('A conditional control associated with link '+name+' has been removed as well as the link.')

    def remove_node(self, name):
        """
        Method to remove a node from the water network object. Note
        that any controls associated with this link will be discarded.

        Parameters
        ----------
        name: string
            Name of the node to be removed
        """
        node = self.get_node(name)
        self._nodes.pop(name)
        self._graph.remove_node(name)
        if isinstance(node, Junction):
            self._num_junctions -= 1
            self._junctions.pop(name)
        elif isinstance(node, Tank):
            self._num_tanks -= 1
            self._tanks.pop(name)
        elif isinstance(node, Reservoir):
            self._num_reservoirs -= 1
            self._reservoirs.pop(name)
        else:
            raise RuntimeError('Node type is not recognized.')

        # Remove controls associated with the node
        controls_to_remove = []
        for key, val in self.conditional_controls.iteritems():
            for key2, val2 in val.iteritems():
                for entry in val2:
                    if entry[0] == name:
                        controls_to_remove.append((key, key2, entry))
        for key in controls_to_remove:
            self.conditional_controls[key[0]][key[1]].remove(key[2])
            warnings.warn('One or more conditional controls associated with node '+name+' has been removed as well as the node.')

    def split_pipe_with_junction(self, pipe_name_to_split, pipe_name_on_start_node_side, pipe_name_on_end_node_side, junction_name):
        """
        Method to "split" a pipe with a junction. This will remove
        pipe_name_to_split, add a junction named junction_name, and
        add two new pipes. The first pipe to be added will be named
        pipe_name_on_start_node_side and will start at the start node
        of the original pipe and end at the new junction. The second
        pipe to be added will be named pipe_name_on_end_node_side and
        will start at the new junction and end at the end node of the
        original pipe. The new pipes will have the same diameter,
        roughness, minor loss, and base status of the original
        pipe. The new pipes will have one-half of the length of the
        original pipe. The new junction will have a base demand of 0,
        an elevation equal the the average of the elevations of the
        original start and end nodes, coordinates at the midpoint
        between the original start and end nodes, and will use the
        default demand pattern. These attributes may be changed after
        splitting the pipe. E.g.,

        j = wn.get_node(junction_name)
        j.elevation = 20.0

        Note that if the original pipe has a check valve, both new
        pipes will have a check valve. Additionally, any controls
        associated with the original pipe will be discarded.

        Parameters
        ----------
        pipe_name_to_split: string
            The name of the pipe to split. This pipe will be removed.

        pipe_name_on_start_node_side: string
            The name of the new pipe to be located between the start node of the original pipe and the new junction. 

        pipe_name_on_end_node_side: string
            The name of the new pipe to be located between the new junction and the end node of the original pipe.

        junction_name: string
            The name of the new junction to be added.
        """

        pipe = self.get_link(pipe_name_to_split)
        if not isinstance(pipe, Pipe):
            raise RuntimeError('You can only split pipes.')

        node_list = [node_name for node_name, node in self.nodes()]
        link_list = [link_name for link_name, link in self.links()]

        if junction_name in node_list:
            raise RuntimeError('The junction name you provided is already being used for another node.')
        if pipe_name_on_start_node_side in link_list or pipe_name_on_end_node_side in link_list:
            raise RuntimeError('One of the new link names you provided is already being used for another link.')

        # Get start and end node info
        start_node = self.get_node(pipe.start_node())
        end_node = self.get_node(pipe.end_node())
        if isinstance(start_node, Reservoir):
            junction_elevation = end_node.elevation
        elif isinstance(end_node, Reservoir):
            junction_elevation = start_node.elevation
        else:
            junction_elevation = (start_node.elevation + end_node.elevation)/2.0
        
        junction_coordinates = ((self._graph.node[pipe.start_node()]['pos'][0] + self._graph.node[pipe.end_node()]['pos'][0])/2.0,(self._graph.node[pipe.start_node()]['pos'][1] + self._graph.node[pipe.end_node()]['pos'][1])/2.0)

        self.remove_link(pipe_name_to_split)
        self.add_junction(junction_name, base_demand=0.0, demand_pattern_name=None, elevation=junction_elevation, coordinates=junction_coordinates)
        self.add_pipe(pipe_name_on_start_node_side, pipe.start_node(), junction_name, pipe.length/2.0, pipe.diameter, pipe.roughness, pipe.minor_loss, LinkStatus.status_to_str(pipe.status), pipe.cv)
        self.add_pipe(pipe_name_on_end_node_side, junction_name, pipe.end_node(), pipe.length/2.0, pipe.diameter, pipe.roughness, pipe.minor_loss, LinkStatus.status_to_str(pipe.status), pipe.cv)

        if pipe.cv:
            warnings.warn('You are splitting a pipe with a check valve. Both new pipes will have check valves.')

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

    def get_all_nodes_deep_copy(self):
        """
        Return a deep copy of the dictionary with all nodes.

        Parameters
        ----------

        Returns
        -------
        dictionary
            Node name to node.
        """
        return copy.deepcopy(self._nodes)

    def get_all_links_deep_copy(self):
        """
        Return a deep copy of the dictionary with all links.

        Parameters
        ----------

        Returns
        -------
        dictionary
            Link name to link.
        """
        return copy.deepcopy(self._links)

    def get_links_for_node(self, node_name, flag='ALL'):
        """
        Returns a list of links connected to a node.

        Parameters
        ----------
        node_name : string
            Name of the node.
        flag : string
            Options are 'ALL','INLET','OUTLET'
            'ALL' returns all links connected to the node.
            'INLET' returns links that have the specified node as an end node.
            'OUTLET' returns links that have the specified node as a start node.

        Returns
        -------
        A list of link names connected to the node
        """
        if flag.upper() == 'ALL':
            in_edges = self._graph.in_edges(node_name, data=False, keys=True)
            out_edges = self._graph.out_edges(node_name, data=False, keys=True)
            edges = in_edges + out_edges
        if flag.upper() == 'INLET':
            in_edges = self._graph.in_edges(node_name, data=False, keys=True)
            edges = in_edges
        if flag.upper() == 'OUTLET':
            out_edges = self._graph.out_edges(node_name, data=False, keys=True)
            edges = out_edges
        list_of_links = []
        for edge_tuple in edges:
            list_of_links.append(edge_tuple[2])

        return list_of_links

    def get_node_coordinates(self, name=None):
        """
        Method to get the coordinates of a node

        Parameters
        ----------
        name: string
            name of the node

        Returns
        -------
        A tuple containing the coordinates of the specified node.
        Note: If name is None, this method will return a dictionary
              with the coordinates of all nodes keyed by node name.
        """
        if name is not None:
            return self._graph.node[name]['pos']
        else:
            coordinates_dict = nx.get_node_attributes(self._graph, 'pos')
            return coordinates_dict

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

    def get_graph_deep_copy(self):
        """
        Returns a deep copy of the WaterNetworkModel networkx graph.
        """
        return copy.deepcopy(self._graph)
        
    def query_node_attribute(self, attribute, operation=None, value=None, node_type=None):
        """ Query node attributes, for example get all nodes with elevation <= threshold

        Parameters
        ----------
        attribute: string
            Node attribute

        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

        value: float or int
            threshold

        node_type: class
            options = Node, Junction, Reservoir, Tank, or None, default = None
            Note None and Node produce the same results

        Returns
        -------
        dictionary
            dictionary of node names to attribute for nodes of node_type satisfying operation threshold

        Notes
        -----
        If operation and value are both None, the dictionary being returned will contain the attributes
        for all nodes with the specified attribute.

        """
        node_attribute_dict = {}
        for name, node in self.nodes(node_type):
            try:
                if operation == None and value == None:
                    node_attribute_dict[name] = getattr(node, attribute)
                else:
                    node_attribute = getattr(node, attribute)
                    if operation(node_attribute, value):
                        node_attribute_dict[name] = node_attribute
            except AttributeError:
                pass
        return node_attribute_dict

    def query_link_attribute(self, attribute, operation=None, value=None, link_type=None):
        """ Query link attributes, for example get all pipe diameters > threshold

        Parameters
        ----------
        attribute: string
            link attribute

        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

        value: float or int
            threshold

        link_type: class
            options = Link, Pipe, Pump, Valve, or None, default = None
            Note: None and Link produce the same results

        Returns
        -------
        dictionary
            dictionary of link names to attributes for links of link_type  satisfying operation threshold

        Notes
        -----
        If operation and value are both None, the dictionary being returned will contain the attributes
        for all links with the specified attribute.

        """
        link_attribute_dict = {}
        for name, link in self.links(link_type):
            try:
                if operation == None and value == None:
                    link_attribute_dict[name] = getattr(link, attribute)
                else:
                    link_attribute = getattr(link, attribute)
                    if operation(link_attribute, value):
                        link_attribute_dict[name] = link_attribute
            except AttributeError:
                pass
        return link_attribute_dict

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

    def junctions(self):
        for name, node in self._junctions.iteritems():
            yield name, node

    def tanks(self):
        for name, node in self._tanks.iteritems():
            yield name, node

    def reservoirs(self):
        for name, node in self._reservoirs.iteritems():
            yield name, node

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

    def pipes(self):
        for name, link in self._pipes.iteritems():
            yield name, link

    def pumps(self):
        for name, link in self._pumps.iteritems():
            yield name, link

    def valves(self):
        for name, link in self._valves.iteritems():
            yield name, link

    def curves(self):
        """
        A generator to iterate over all curves

        Returns
        -------
        curve_name, curve
        """
        for curve_name, curve in self._curves.iteritems():
            yield curve_name, curve

    def set_node_coordinates(self, name, coordinates):
        """
        Method to set the node coordinates in the network x graph.

        Parameters
        ----------
        name : name of the node
        coordinates : tuple of X-Y coordinates
        """
        nx.set_node_attributes(self._graph, 'pos', {name: coordinates})

    def shifted_time(self):
        """ 
        Returns the time in seconds shifted by the
        simulation start time (e.g. as specified in the
        inp file). This is, this is the time since 12 AM
        on the first day.
        """
        return self.sim_time + self.options.start_clocktime

    def prev_shifted_time(self):
        """
        Returns the time in seconds of the previous solve shifted by
        the simulation start time. That is, this is the time from 12
        AM on the first day to the time at the prevous hydraulic
        timestep.
        """
        return self.prev_sim_time + self.options.start_clocktime

    def clock_time(self):
        """
        Return the current time of day in seconds from 12 AM
        """
        return self.shifted_time_sec() % (24*3600)

    def _get_isolated_junctions(self):
        starting_recursion_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(50000)
        groups = {}
        has_tank_or_res = {}
        G = self._graph

        def grab_group(node_name):
            groups[grp].add(node_name)
            if G.node[node_name]['type'] == 'tank' or G.node[node_name]['type']=='reservoir':
                has_tank_or_res[grp] = True
            suc = G.successors(node_name)
            pre = G.predecessors(node_name)
            for s in suc:
                connected_to_s = False
                link_names_list = G.edge[node_name][s].keys()
                for link_name in link_names_list:
                    link = self.get_link(link_name)
                    if link.status!=LinkStatus.closed:
                        connected_to_s = True
                if connected_to_s:
                    if s not in groups[grp]:
                        grab_group(s)
            for p in pre:
                connected_to_p = False
                link_names_list = G.edge[p][node_name].keys()
                for link_name in link_names_list:
                    link = self.get_link(link_name)
                    if link.status!=LinkStatus.closed:
                        connected_to_p = True
                if connected_to_p:
                    if p not in groups[grp]:
                        grab_group(p)

        grp = -1
        for node_name in G.nodes():
            already_in_grp = False
            for key in groups.keys():
                if node_name in groups[key]:
                    already_in_grp = True
            if not already_in_grp:
                grp += 1
                groups[grp] = set()
                has_tank_or_res[grp] = False
                grab_group(node_name)

        for grp,check in has_tank_or_res.iteritems():
            if check:
                del groups[grp]

        isolated_junctions = set()
        for grp, junctions in groups.iteritems():
            isolated_junctions = isolated_junctions.union(junctions)
        isolated_junctions = list(isolated_junctions)

        isolated_links = set()
        for j in isolated_junctions:
            connected_links = self.get_links_for_node(j)
            for l in connected_links:
                isolated_links.add(l)
        isolated_links = list(isolated_links)

        sys.setrecursionlimit(starting_recursion_limit)
        return isolated_junctions, isolated_links

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
            print >> f, text_format.format(pipe_name, pipe.start_node(), pipe.end_node(), pipe.length, pipe.diameter*1000, pipe.roughness, pipe.minor_loss, LinkStatus.status_to_str(pipe.get_base_status()), ';')

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
            if link.get_base_status() is not None and link.get_base_status() != LinkStatus.cv:
                print >> f, text_format.format(link_name, LinkStatus.status_to_str(link.get_base_status()))

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
        text_format_string = '{:20s} {:20s}'
        text_format_float = '{:20s} {:<20.8f}'
        print >>f, text_format_string.format('UNITS', 'LPS')
        print >>f, text_format_string.format('HEADLOSS', self.options.headloss)
        if self.options.hydraulics_option is not None:
            print >>f, '{:20s} {:20s} {:<30s}'.format('HYDRAULICS', self.options.hydraulics_option, self.options.hydraulics_filename)
        if self.options.quality_value is None:
            print >>f, text_format_string.format('QUALITY', self.options.quality_option)
        else:
            print >>f, '{:20s} {:20s} {:20s}'.format('QUALITY', self.options.quality_option, self.options.quality_value)
        print >>f, text_format_float.format('VISCOSITY', self.options.viscosity)
        print >>f, text_format_float.format('DIFFUSIVITY', self.options.diffusivity)
        print >>f, text_format_float.format('SPECIFIC GRAVITY', self.options.specific_gravity)
        print >>f, text_format_float.format('TRIALS', self.options.trials)
        print >>f, text_format_float.format('ACCURACY', self.options.accuracy)
        if self.options.unbalanced_value is None:
            print >>f, text_format_string.format('UNBALANCED', self.options.unbalanced_option)
        else:
            print >>f, '{:20s} {:20s} {:20d}'.format('UNBALANCED', self.options.unbalanced_option, self.options.unbalanced_value)
        if self.options.pattern is not None:
            print >>f, text_format_string.format('PATTERN', self.options.pattern)
        print >>f, text_format_float.format('DEMAND MULTIPLIER', self.options.demand_multiplier)
        print >>f, text_format_float.format('EMITTER EXPONENT', self.options.emitter_exponent)
        print >>f, text_format_float.format('TOLERANCE', self.options.tolerance)
        if self.options.map is not None:
            print >>f, text_format_string.format('MAP', self.options.map)

        print >> f, ''

        # Reaction Options
        print >> f, '[REACTIONS]'
        text_format_float = '{:15s}{:15s}{:<10.8f}'
        print >>f, text_format_float.format('ORDER','BULK',self.options.bulk_rxn_order)
        print >>f, text_format_float.format('ORDER','WALL',self.options.wall_rxn_order)
        print >>f, text_format_float.format('ORDER','TANK',self.options.tank_rxn_order)
        print >>f, text_format_float.format('GLOBAL','BULK',self.options.bulk_rxn_coeff)
        print >>f, text_format_float.format('GLOBAL','WALL',self.options.wall_rxn_coeff)
        if self.options.limiting_potential is not None:
            print >>f, text_format_float.format('LIMITING','POTENTIAL',self.options.limiting_potential)
        if self.options.roughness_correlation is not None:
            print >>f, text_format_float.format('ROUGHNESS','CORRELATION',self.options.roughness_correlation)
        for tank_name, tank in self.nodes(Tank):
            if tank.bulk_rxn_coeff is not None:
                print >>f, text_format_float.format('TANK',tank_name,tank.bulk_rxn_coeff)
        for pipe_name, pipe in self.links(Pipe):
            if pipe.bulk_rxn_coeff is not None:
                print >>f, text_format_float.format('BULK',pipe_name,pipe.bulk_rxn_coeff)
            if pipe.wall_rxn_coeff is not None:
                print >>f, text_format_float.format('WALL',pipe_name,pipe.wall_rxn_coeff)

        print >> f, ''

        # Time options
        print >> f, '[TIMES]'
        text_format = '{:20s} {:10s}'
        time_text_format = '{:20s} {:d}:{:d}:{:d}'
        hrs, mm, sec = self._sec_to_string(self.options.duration)
        print >>f, time_text_format.format('DURATION', hrs, mm, sec)
        hrs, mm, sec = self._sec_to_string(self.options.hydraulic_timestep)
        print >>f, time_text_format.format('HYDRAULIC TIMESTEP', hrs, mm, sec)
        hrs, mm, sec = self._sec_to_string(self.options.pattern_timestep)
        print >>f, time_text_format.format('PATTERN TIMESTEP', hrs, mm, sec)
        hrs, mm, sec = self._sec_to_string(self.options.pattern_start)
        print >>f, time_text_format.format('PATTERN START', hrs, mm, sec)
        hrs, mm, sec = self._sec_to_string(self.options.report_timestep)
        print >>f, time_text_format.format('REPORT TIMESTEP', hrs, mm, sec)
        hrs, mm, sec = self._sec_to_string(self.options.report_start)
        print >>f, time_text_format.format('REPORT START', hrs, mm, sec)

        hrs, mm, sec = self._sec_to_string(self.options.start_clocktime)
        if hrs < 12:
            time_format = ' AM'
        else:
            hrs -= 12
            time_format = ' PM'
        print >>f, '{:20s} {:d}:{:d}:{:d}{:s}'.format('START CLOCKTIME', hrs, mm, sec, time_format)

        hrs, mm, sec = self._sec_to_string(self.options.quality_timestep)
        print >>f, time_text_format.format('QUALITY TIMESTEP', hrs, mm, sec)
        hrs, mm, sec = self._sec_to_string(self.options.rule_timestep)
        print >>f, time_text_format.format('RULE TIMESTEP', hrs, mm, int(sec))
        print >>f, text_format.format('STATISTIC', self.options.statistic)

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

    def _sec_to_string(self, sec):
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        return (hours, mm, sec)
 
class WaterNetworkOptions(object):
    """
    A class to manage options.
    """

    def __init__(self):
        # Time related options
        self.duration = 0.0
        "Simulation duration in seconds."

        self.hydraulic_timestep = 3600.0
        "Hydraulic timestep in seconds."

        self.pattern_timestep = 3600.0
        "Pattern timestep in seconds."

        self.pattern_start = 0.0
        "Time offset in seconds at which all patterns will start. E.g., a value of 7200 would start the simulation with each pattern in the time period that corresponds to hour 2."

        self.report_timestep = 3600.0
        "Reporting timestep in seconds."

        self.report_start = 0.0
        "Start time of the report in seconds from the start of the simulation."

        self.start_clocktime = 0.0
        "Time of day in seconds from 12 am at which the simulation begins."

        self.quality_timestep = 360.0
        self.rule_timestep = 360.0
        self.statistic = 'NONE'

        # general options
        self.pattern = None
        "Name of the default pattern for junction demands. If None, the junctions without patterns will be held constant."
       
        self.units = 'GPM'
        self.headloss = 'H-W'
        self.hydraulics_option = None #string 
        self.hydraulics_filename = None #string
        self.quality_option = 'NONE'
        self.quality_value = None #string
        self.viscosity = 1.0
        self.diffusivity = 1.0
        self.specific_gravity = 1.0
        self.trials = 40
        self.accuracy = 0.001
        self.unbalanced_option = 'STOP'
        self.unbalanced_value = None #int
        self.demand_multiplier = 1.0
        self.emitter_exponent = 0.5
        self.tolerance = 0.01
        self.map = None

        # Reaction Options
        self.bulk_rxn_order = 1.0
        self.wall_rxn_order = 1.0
        self.tank_rxn_order = 1.0
        self.bulk_rxn_coeff = 0.0
        self.wall_rxn_coeff = 0.0
        self.limiting_potential = None
        self.roughness_correlation = None

class NodeTypes(object):
    """
    An enum class for types of nodes.
    """
    junction = 0
    "An enum member for junctions"
    tank = 1
    "An enum member for tanks"
    reservoir = 2
    "An enum member for reservoirs"

    def __init__(self):
        pass

    @classmethod
    def node_type_to_str(self, value):
        """
        A method to convert a NodeTypes enum member to a string.

        Parameters
        ----------
        value: A NodeTypes enum member

        Returns
        -------
        A string corresponding to the enum member

        Examples
        --------
        >>> NodeTypes.node_type_to_str(NodeTypes.junction)
        'Junction'
        """
        if value == self.junction:
            return 'Junction'
        elif value == self.tank:
            return 'Tank'
        elif value == self.reservoir:
            return 'Reservoir'

class LinkTypes(object):
    """
    An enum class for types of links.
    """
    pipe = 0
    "An enum member for pipes"
    pump = 1
    "An enum member for pumps"
    valve = 2
    "An enum member for valves"

    def __init__(self):
        pass

    @classmethod
    def link_type_to_str(self, value):
        """
        A method to convert a LinkTypes enum member to a string.

        Parameters
        ----------
        value: A Linktypes enum member

        Returns
        -------
        A string corresponding to the enum member
        
        Examples
        --------
        >>> Linktypes.link_type_to_str(LinkTypes.pump)
        'Pump'
        """
        if value == self.pipe:
            return 'Pipe'
        elif value == self.pump:
            return 'Pump'
        elif value == self.valve:
            return 'Valve'

class LinkStatus(object):
    """
    An enum class for link statuses.
    """
    closed = 0
    "An enum member for closed links"
    opened = 1
    "An enum member for open links"
    active = 2
    "An enum member for active valves"

    def __init__(self):
        pass

    @classmethod
    def str_to_status(self, value):
        """
        A method to convert a string to an enum member value.

        Parameters
        ----------
        value: string
           Options are 'OPEN', 'CLOSED', or 'ACTIVE'.
        """
        if type(value) == int:
            return value
        elif value.upper() == 'OPEN':
            return self.opened
        elif value.upper() == 'CLOSED':
            return self.closed
        elif value.upper() == 'ACTIVE':
            return self.active

    @classmethod
    def status_to_str(self, value):
        """
        A method to convert a LinkStatus enum member to a string.

        Parameters
        ----------
        value: A LinkStatus enum member

        Returns
        -------
        A string corresponding to the enum member

        Examples
        --------
        >>> LinkStatus.status_to_str(LinkStatus.active)
        'ACTIVE'
        """
        if value == self.opened:
            return 'OPEN'
        elif value == self.closed:
            return 'CLOSED'
        elif value == self.active:
            return 'ACTIVE'

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
        self.prev_head = None
        self.head = None
        self.prev_demand = None
        self.demand = None
        self.leak_demand = None
        self.prev_leak_demand = None

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
        self.prev_status = None
        self.status = LinkStatus.opened
        self.prev_flow = None
        self.flow = None

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

    def name(self):
        """
        Returns the name of the link
        """
        return self._link_name

class Junction(Node):
    """
    Junction class that is inherited from Node
    """
    def __init__(self, name, base_demand=0.0, demand_pattern_name=None, elevation=0.0):
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
        super(Junction, self).__init__(name)
        self.base_demand = base_demand
        self.prev_expected_demand = None
        self.expected_demand = base_demand
        self.demand_pattern_name = demand_pattern_name
        self.elevation = elevation
        self.nominal_pressure = 20.0
        "The nominal pressure attribute is used for pressure-dependent demand. This is the lowest pressure at which the customer receives the full requested demand."
        self.minimum_pressure = 0.0
        "The minimum pressure attribute is used for pressure-dependent demand simulations. Below this pressure, the customer will not receive any water."
        self._leak = False
        self.leak_status = False
        self.leak_area = 0.0
        self.leak_discharge_coeff = 0.0

    def add_leak(self, area, discharge_coeff = 0.75):
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
        start_time: float
           Start time of the leak in seconds. 
           Default is the start of the simulation.
        end_time: float
           Time at which the leak is fixed in seconds. 
           Default is that the leak does not
           get repaired during the simulation.
        """

        self._leak = True
        self.leak_area = area
        self.leak_discharge_coeff = discharge_coeff

    def remove_leak(self):
        """
        Method to remove a leak from a tank.
        """
        self._leak = False

    def leak_present(self):
        """
        Method to check if the tank has a leak or not. Note that this
        does not check whether or not the leak is active (i.e., if the
        current time is between leak_start_time and leak_end_time).

        Returns
        -------
        bool: True if a leak is is present, False if a leak is not present
        """
        return self._leak

class Tank(Node):
    """
    Tank class that is inherited from Node
    """
    def __init__(self, name, elevation=0.0, init_level=3.048,
                 min_level=0.0, max_level=6.096, diameter=15.24,
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
        vol_curve : Curve object
            Curve object
        """
        super(Tank, self).__init__(name)
        self.elevation = elevation
        self.init_level = init_level
        self.head = init_level+elevation
        self.min_level = min_level
        self.max_level = max_level
        self.diameter = diameter
        self.min_vol = min_vol
        self.vol_curve = vol_curve
        self._leak = False
        self.leak_status = False
        self.leak_area = 0.0
        self.leak_discharge_coeff = 0.0
        self.bulk_rxn_coeff = None

    def add_leak(self, area, discharge_coeff = 0.75):
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
        start_time: float
           Start time of the leak in seconds. 
           Default is the start of the simulation.
        end_time: float
           Time at which the leak is fixed in seconds. 
           Default is that the leak does not
           get repaired.
        """

        self._leak = True
        self.leak_area = area
        self.leak_discharge_coeff = discharge_coeff
        
    def remove_leak(self):
        """
        Method to remove a leak from a tank.
        """
        self._leak = False

    def leak_present(self):
        """
        Method to check if the tank has a leak or not. Note that this
        does not check whether or not the leak is active (i.e., if the
        current time is between leak_start_time and leak_end_time).

        Returns
        -------
        bool: True if a leak is is present, False if a leak is not present
        """
        return self._leak
        

class Reservoir(Node):
    """
    Reservoir class that is inherited from Node
    """
    def __init__(self, name, base_head=0.0, head_pattern_name=None):
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
        super(Reservoir, self).__init__(name)
        self.base_head = base_head
        self.head = base_head
        self.head_pattern_name = head_pattern_name

class Pipe(Link):
    """
    Pipe class that is inherited from Link
    """
    def __init__(self, name, start_node_name, end_node_name, length=304.8,
                 diameter=0.3048, roughness=100, minor_loss=0.00, status='OPEN', check_valve_flag=False):
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
            Pipe status. Options are 'Open' or 'Closed'
        check_valve_flag : bool
            True if the pipe has a check valve
            False if the pipe does not have a check valve
        """
        super(Pipe, self).__init__(name, start_node_name, end_node_name)
        self.length = length
        self.diameter = diameter
        self.roughness = roughness
        self.minor_loss = minor_loss
        self.cv = check_valve_flag
        if status is not None:
            self.status = LinkStatus.str_to_status(status)
        self.bulk_rxn_coeff = None
        self.wall_rxn_coeff = None


class Pump(Link):
    """
    Pump class that is inherited from Link
    """
    def __init__(self, name, start_node_name, end_node_name, info_type='POWER', info_value=50.0):
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
        super(Pump, self).__init__(name, start_node_name, end_node_name)
        self._cv_status = LinkStatus.opened
        self.prev_speed = None
        self.speed = 1.0
        self.curve = None
        self.power = None
        self.info_type = info_type.upper()
        if self.info_type == 'HEAD':
            self.curve = info_value
        elif self.info_type == 'POWER':
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
                 diameter=0.3048, valve_type='PRV', minor_loss=0.0, setting=0.0):
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
        valve_type : string
            Type of valve. Options are 'PRV', etc
        minor_loss : float
            Pipe minor loss coefficient
        setting : float or string
            Valve setting or name of headloss curve for GPV
        """
        super(Valve, self).__init__(name, start_node_name, end_node_name)
        self.diameter = diameter
        self.valve_type = valve_type
        self.minor_loss = minor_loss
        self.prev_setting = None
        self.setting = setting
        self.status = LinkStatus.active
        self._status = LinkStatus.active

class Curve(object):
    """
    Curve class.
    """
    def __init__(self, name, curve_type, points):
        """
        Parameters
        ----------
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
