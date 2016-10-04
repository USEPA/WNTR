"""
Classes and methods used for specifying a water network model.
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
import logging

logger = logging.getLogger('wntr.network.WaterNetworkModel')

class WaterNetworkModel(object):

    """
    Base water network model class.
    """
    def __init__(self, inp_file_name=None):
        """
        Examples
        ---------
        >>> wn = WaterNetworkModel()
        
        Optional Parameters
        -------------------
        inp_file_name: string
           directory and filename of inp file to load into the WaterNetworkModel object.

        """

        # Network name
        self.name = None
        
        # Time parameters
        self.sim_time = 0.0
        self.prev_sim_time = -np.inf  # the last time at which results were accepted

        # Initialize Network size parameters
        self._num_junctions = 0
        self._num_reservoirs = 0
        self._num_tanks = 0
        self._num_pipes = 0
        self._num_pumps = 0
        self._num_valves = 0

        # Initialize node and link dictionaries
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
        self._control_dict = {}

        # Name of pipes that are check valves
        self._check_valves = []

        # NetworkX Graph to store the pipe connectivity and node coordinates
        self._graph = wntr.network.WntrMultiDiGraph()

        self._Htol = 0.00015  # Head tolerance in meters.
        self._Qtol = 2.8e-5  # Flow tolerance in m^3/s.

        if inp_file_name:
            parser = wntr.network.ParseWaterNetwork()
            parser.read_inp_file(self, inp_file_name)

    def __eq__(self, other):
        if self._num_junctions  == other._num_junctions  and \
           self._num_reservoirs == other._num_reservoirs and \
           self._num_tanks      == other._num_tanks      and \
           self._num_pipes      == other._num_pipes      and \
           self._num_pumps      == other._num_pumps      and \
           self._num_valves     == other._num_valves     and \
           self._nodes          == other._nodes          and \
           self._links          == other._links          and \
           self._junctions      == other._junctions      and \
           self._tanks          == other._tanks          and \
           self._reservoirs     == other._reservoirs     and \
           self._pipes          == other._pipes          and \
           self._pumps          == other._pumps          and \
           self._valves         == other._valves         and \
           self._patterns       == other._patterns       and \
           self._curves         == other._curves         and \
           self._control_dict   == other._control_dict   and \
           self._check_valves   == other._check_valves:
            return True
        return False
        
    def add_junction(self, name, base_demand=0.0, demand_pattern_name=None, elevation=0.0, coordinates=None):
        """
        Add a junction to the network.
        
        Required Parameters
        -------------------
        name : string
            Name of the junction.

        Optional Parameters
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

        Required Parameters
        -------------------
        name : string
            Name of the tank.

        Optional Parameters
        -------------------
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
        tank = Tank(name, elevation, init_level, min_level, max_level, diameter, min_vol, vol_curve)
        self._nodes[name] = tank
        self._tanks[name] = tank
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        nx.set_node_attributes(self._graph, 'type', {name: 'tank'})
        self._num_tanks += 1

    def _get_all_tank_controls(self):

        tank_controls = []

        for tank_name, tank in self.nodes(Tank):

            # add the tank controls
            all_links = self.get_links_for_node(tank_name, 'ALL')

            # First take care of the min level
            min_head = tank.min_level+tank.elevation
            for link_name in all_links:
                link = self.get_link(link_name)
                link_has_cv = False
                if isinstance(link, Pipe):
                    if link.cv:
                        if link.end_node() == tank_name:
                            continue
                        else:
                            link_has_cv = True
                if isinstance(link, Pump):
                    if link.end_node() == tank_name:
                        continue
                    else:
                        link_has_cv = True
            
                close_control_action = wntr.network.ControlAction(link, 'status', LinkStatus.closed)
                open_control_action = wntr.network.ControlAction(link, 'status', LinkStatus.opened)

                control = wntr.network.ConditionalControl((tank,'head'), np.less_equal, min_head,close_control_action)
                control._priority = 1
                control.name = link_name+' closed because tank '+tank.name()+' head is less than min head'
                tank_controls.append(control)

                if not link_has_cv:
                    control = wntr.network.MultiConditionalControl([(tank,'head'), (tank, 'prev_head'),
                                                                    (self, 'sim_time')],
                                                                   [np.greater, np.less_equal,np.greater],
                                                                   [min_head+self._Htol, min_head+self._Htol, 0.0],
                                                                   open_control_action)
                    control._partial_step_for_tanks = False
                    control._priority = 0
                    control.name = link_name+' opened because tank '+tank.name()+' head is greater than min head'
                    tank_controls.append(control)

                    if link.start_node() == tank_name:
                        other_node_name = link.end_node()
                    else:
                        other_node_name = link.start_node()
                    other_node = self.get_node(other_node_name)
                    control = wntr.network.MultiConditionalControl([(tank,'head'),(tank,'head')],
                                                                   [np.less_equal,np.less_equal],
                                                                   [min_head+self._Htol,(other_node,'head')],
                                                                   open_control_action)
                    control._priority = 2
                    control.name = (link_name+' opened because tank '+tank.name()+
                                    ' head is below min head but flow should be in')
                    tank_controls.append(control)
            
            # Now take care of the max level
            max_head = tank.max_level+tank.elevation
            for link_name in all_links:
                link = self.get_link(link_name)
                link_has_cv = False
                if isinstance(link, Pipe):
                    if link.cv:
                        if link.start_node()==tank_name:
                            continue
                        else:
                            link_has_cv = True
                if isinstance(link, Pump):
                    if link.start_node()==tank_name:
                        continue
                    else:
                        link_has_cv = True
            
                close_control_action = wntr.network.ControlAction(link, 'status', LinkStatus.closed)
                open_control_action = wntr.network.ControlAction(link, 'status', LinkStatus.opened)
            
                control = wntr.network.ConditionalControl((tank,'head'),np.greater_equal,max_head,close_control_action)
                control._priority = 1
                control.name = link_name+' closed because tank '+tank.name()+' head is greater than max head'
                tank_controls.append(control)

                if not link_has_cv:
                    control = wntr.network.MultiConditionalControl([(tank,'head'),(tank,'prev_head'),(self,'sim_time')],[np.less,np.greater_equal,np.greater],[max_head-self._Htol,max_head-self._Htol,0.0],open_control_action)
                    control._partial_step_for_tanks = False
                    control._priority = 0
                    control.name = link_name+'opened because tank '+tank.name()+' head is less than max head'
                    tank_controls.append(control)
            
                    if link.start_node() == tank_name:
                        other_node_name = link.end_node()
                    else:
                        other_node_name = link.start_node()
                    other_node = self.get_node(other_node_name)
                    control = wntr.network.MultiConditionalControl([(tank,'head'),(tank,'head')],[np.greater_equal,np.greater_equal],[max_head-self._Htol,(other_node,'head')],open_control_action)
                    control._priority = 2
                    control.name = link_name+' opened because tank '+tank.name()+' head above max head but flow should be out'
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

            close_control_action = wntr.network.ControlAction(pipe, 'status', LinkStatus.closed)
            open_control_action = wntr.network.ControlAction(pipe, 'status', LinkStatus.opened)
            
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
        for pump_name, pump in self.links(Pump):

            close_control_action = wntr.network.ControlAction(pump, '_cv_status', LinkStatus.closed)
            open_control_action = wntr.network.ControlAction(pump, '_cv_status', LinkStatus.opened)
        
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
        start_node = self.get_node(start_node_name)
        end_node = self.get_node(end_node_name)
        if type(start_node)==Tank or type(end_node)==Tank:
            warnings.warn('Valves should not be connected to tanks! Please add a pipe between the tank and valve. Note that this will be an error in the next release.')

        valve = Valve(name, start_node_name, end_node_name,
                      diameter, valve_type, minor_loss, setting)
        self._links[name] = valve
        self._valves[name] = valve
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        nx.set_edge_attributes(self._graph, 'type', {(start_node_name, end_node_name, name):'valve'})
        self._num_valves += 1

    def _get_valve_controls(self):
        valve_controls = []
        for valve_name, valve in self.links(Valve):

            close_control_action = wntr.network.ControlAction(valve, '_status', LinkStatus.closed)
            open_control_action = wntr.network.ControlAction(valve, '_status', LinkStatus.opened)
            active_control_action = wntr.network.ControlAction(valve, '_status', LinkStatus.active)
        
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

    def add_control(self, name, control_object):
        """
        Add a control to the network.

        Parameters
        ----------
        name : string
           The name used to identify the control object
        control_object : An object derived from the Control object
        """
        if name in self._control_dict:
            raise ValueError('The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control.')

        target = control_object._control_action._target_obj_ref
        target_type = type(target)
        if target_type == wntr.network.Valve:
            warnings.warn('Controls should not be added to valves! Note that this will become an error in the next release.')
        if target_type == wntr.network.Link:
            start_node_name = target_obj.start_node()
            end_node_name = target_obj.end_node()
            start_node = self.get_node(start_node_name)
            end_node = self.get_node(end_node_name)
            if type(start_node)==Tank or type(end_node)==Tank:
                warnings.warn('Controls should not be added to links that are connected to tanks. Consider adding an additional link and using the control on it. Note that this will become an error in the next release.')

        self._control_dict[name] = control_object
        control_object.name = name

    def add_pump_outage(self, pump_name, start_time, end_time):
        """
        Add a pump outage to the network.

        Parameters
        ----------
        pump_name : string
           The name of the pump to be affected by an outage
        start_time : int
           The time at which the outage starts.
           Internal units must be in seconds (s)
        end_time : int
           The time at which the outage stops.
           Internal units must be in seconds (s)
        """
        pump = self.get_link(pump_name)

        end_power_outage_action = wntr.network.ControlAction(pump, '_power_outage', False)
        start_power_outage_action = wntr.network.ControlAction(pump, '_power_outage', True)

        control = wntr.network.TimeControl(self, end_time, 'SIM_TIME', False, end_power_outage_action)
        control._priority = 0
        self.add_control(pump_name+'PowerOn'+str(end_time),control)

        control = wntr.network.TimeControl(self, start_time, 'SIM_TIME', False, start_power_outage_action)
        control._priority = 3
        self.add_control(pump_name+'PowerOff'+str(start_time),control)


        opened_action_obj = wntr.network.ControlAction(pump, 'status', LinkStatus.opened)
        closed_action_obj = wntr.network.ControlAction(pump, 'status', LinkStatus.closed)

        control = wntr.network.MultiConditionalControl([(pump,'_power_outage')],[np.equal],[True], closed_action_obj)
        control._priority = 3
        self.add_control(pump_name+'PowerOffStatus'+str(end_time),control)

        control = wntr.network.MultiConditionalControl([(pump,'_prev_power_outage'),(pump,'_power_outage')],[np.equal,np.equal],[True,False],opened_action_obj)
        control._priority = 0
        self.add_control(pump_name+'PowerOnStatus'+str(start_time),control)

    def all_pump_outage(self, start_time, end_time):
        """
        Add a pump outage to the network that affects all pumps.

        Parameters
        ----------
        start_time : int
           The time at which the outage starts
        end_time : int
           The time at which the outage stops.
           Internal units must be in seconds (s)
        """
        for pump_name, pump in self.links(Pump):
            self.add_pump_outage(pump_name, start_time, end_time)

    def remove_link(self, name, with_control=True):
        """Method to remove a link from the water network object.

        Parameters
        ----------
        name: string
           Name of the link to be removed
        with_control: bool
           If with_control is True, then any controls that target the
           link being removed will also be removed. If with_control is
           False, no controls will be removed.
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

        if with_control:
            x=[]
            for control_name, control in self._control_dict.iteritems():
                if type(control)==wntr.network._PRVControl:
                    if link==control._close_control_action._target_obj_ref:
                        warnings.warn('Control '+control_name+' is being removed along with link '+name)
                        x.append(control_name)
                else:
                    if link == control._control_action._target_obj_ref:
                        warnings.warn('Control '+control_name+' is being removed along with link '+name)
                        x.append(control_name)
            for i in x:
                self.remove_control(i)
        else:
            for control_name, control in self._control_dict.iteritems():
                if type(control)==wntr.network._PRVControl:
                    if link==control._close_control_action._target_obj_ref:
                        warnings.warn('A link is being removed that is the target object of a control. However, the control is not being removed.')
                else:
                    if link == control._control_action._target_obj_ref:
                        warnings.warn('A link is being removed that is the target object of a control. However, the control is not being removed.')

    def remove_node(self, name, with_control=True):
        """
        Method to remove a node from the water network object.

        Parameters
        ----------
        name: string
            Name of the node to be removed
        with_control: bool
           If with_control is True, then any controls that target the
           link being removed will also be removed. If with_control is
           False, no controls will be removed.
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

        if with_control:
            x = []
            for control_name, control in self._control_dict.iteritems():
                if type(control)==wntr.network._PRVControl:
                    if node==control._close_control_action._target_obj_ref:
                        warnings.warn('Control '+control_name+' is being removed along with node '+name)
                        x.append(control_name)
                else:
                    if node == control._control_action._target_obj_ref:
                        warnings.warn('Control '+control_name+' is being removed along with node '+name)
                        x.append(control_name)
            for i in x:
                self.remove_control(i)
        else:
            for control_name, control in self._control_dict.iteritems():
                if type(control)==wntr.network._PRVControl:
                    if node==control._close_control_action._target_obj_ref:
                        warnings.warn('A node is being removed that is the target object of a control. However, the control is not being removed.')
                else:
                    if node == control._control_action._target_obj_ref:
                        warnings.warn('A node is being removed that is the target object of a control. However, the control is not being removed.')

    def remove_control(self, name):
        """
        A method to remove a control from the network. If the control
        is not present, an exception is raised.

        Parameters
        ----------
        name : string
           The name of the control object to be removed.
        """
        del self._control_dict[name]

    def discard_control(self, name):
        """
        A method to remove a control from the network if it is
        present. If the control is not present, an exception is not
        raised.

        Parameters
        ----------
        name : string
           The name of the control object to be removed.
        """
        try:
            del self._control_dict[name]
        except KeyError:
            pass

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

    def get_control(self, name):
        """
        Returns the control object for the provided name.

        Parameters
        ----------
        name: string
           name of the control
        """
        return self._control_dict[name]

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

    def get_all_controls_deed_copy(self):
        """
        Return a deep copy of the dictionary with all controls.

        Parameters
        ----------

        Returns
        -------
        dictionary
           Control name to control.
        """
        return copy.deepcopy(self._control_dict)

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

    def num_junctions(self):
        """
        Number of junctions.

        Returns
        -------
        Number of junctions.
        """
        return self._num_junctions
    
    def num_tanks(self):
        """
        Number of tanks.

        Returns
        -------
        Number of tanks.
        """
        return self._num_tanks
    
    def num_reservoirs(self):
        """
        Number of reservoirs.

        Returns
        -------
        Number of reservoirs.
        """
        return self._num_reservoirs
    
    def num_links(self):
        """
        Number of links.

        Returns
        -------
        """
        return len(self._links)

    def num_pipes(self):
        """
        Number of pipes.

        Returns
        -------
        Number of pipes.
        """
        return self._num_pipes
    
    def num_pumps(self):
        """
        Number of pumps.

        Returns
        -------
        Number of pumps.
        """
        return self._num_pumps
    
    def num_valves(self):
        """
        Number of valves.

        Returns
        -------
        Number of valves.
        """
        return self._num_valves
    
    def nodes(self, node_type=None):
        """
        A generator to iterate over all nodes of node_type.
        If no node_type is passed, this method iterates over all nodes.

        Parameters
        ----------
        node_type : Junction, Tank, Reservoir, or None (default: None)
           The type of node that will be iterated over.

        Returns
        -------
        node_name, node
        """
        if node_type==None:
            for node_name, node in self._nodes.iteritems():
                yield node_name, node
        elif node_type==Junction:
            for node_name, node in self._junctions.iteritems():
                yield node_name, node
        elif node_type==Tank:
            for node_name, node in self._tanks.iteritems():
                yield node_name, node
        elif node_type==Reservoir:
            for node_name, node in self._reservoirs.iteritems():
                yield node_name, node
        else:
            raise RuntimeError('node_type, '+str(node_type)+', not recognized.')

    def junctions(self):
        """
        A generator  to iterate over all junctions.

        Returns
        -------
        name, node
        """
        for name, node in self._junctions.iteritems():
            yield name, node

    def tanks(self):
        """
        A generator  to iterate over all tanks.
        
        Returns
        -------
        name, node
        """
        for name, node in self._tanks.iteritems():
            yield name, node

    def reservoirs(self):
        """
        A generator to iterate over all reservoirs.

        Returns
        -------
        name, node
        """
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
        if link_type==None:
            for link_name, link in self._links.iteritems():
                yield link_name, link
        elif link_type==Pipe:
            for link_name, link in self._pipes.iteritems():
                yield link_name, link
        elif link_type==Pump:
            for link_name, link in self._pumps.iteritems():
                yield link_name, link
        elif link_type==Valve:
            for link_name, link in self._valves.iteritems():
                yield link_name, link
        else:
            raise RuntimeError('link_type, '+str(link_type)+', not recognized.')

    def pipes(self):
        """
        A generator to iterate over all pipes.

        Returns
        -------
        name, link
        """
        for name, link in self._pipes.iteritems():
            yield name, link

    def pumps(self):
        """
        A generator to iterate over all pumps.

        Returns
        -------
        name, link
        """
        for name, link in self._pumps.iteritems():
            yield name, link

    def valves(self):
        """
        A generator to iterate over all valves.

        Returns
        -------
        name, link
        """
        for name, link in self._valves.iteritems():
            yield name, link

    def node_name_list(self):
        """
        Returns a list of the names of all nodes.
        """
        return self._nodes.keys()

    def junction_name_list(self):
        """
        Returns a list of the names of all junctions.
        """
        return self._junctions.keys()

    def tank_name_list(self):
        """
        Returns a list of the names of all tanks.
        """
        return self._tanks.keys()

    def reservoir_name_list(self):
        """
        Returns a list of the names of all reservoirs.
        """
        return self._reservoirs.keys()

    def link_name_list(self):
        """
        Returns a list of the names of all links.
        """
        return self._links.keys()

    def pipe_name_list(self):
        """
        Returns a list of the names of all pipes.
        """
        return self._pipes.keys()

    def pump_name_list(self):
        """
        Returns a list of the names of all pumps.
        """
        return self._pumps.keys()

    def valve_name_list(self):
        """
        Returns a list of the names of all valves.
        """
        return self._valves.keys()

    def control_name_list(self):
        """
        Returns a list of the names of all controls.
        """
        return self._control_dict.keys()
            
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

    def scale_node_coordinates(self, scale):
        """
        Scale node coordinates, using 1:scale.  Scale should be in meters.
        
        Parameters
        -----------
        scale : float
            Coordinate scale multiplier
        """
        pos = nx.get_node_attributes(self._graph, 'pos')
        
        for name, node in self._nodes.iteritems():
            self.set_node_coordinates(name, (pos[name][0]*scale, pos[name][1]*scale))

    def set_edge_attribute_on_graph(self, link_name, attr_name, value):
        """
        Set edge attribute on graph.

        Parameters
        ----------
        link_name: string
            Name of the link used.
        """
        link = self.get_link(link_name)
        self._graph.edge[link.start_node()][link.end_node()][link_name][attr_name] = value
        
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

    def reset_initial_values(self):
        """
        Resets all initial values in the network.
        """
        self.sim_time = 0.0
        self.prev_sim_time = -np.inf

        for name, node in self.nodes(Junction):
            node.prev_head = None
            node.head = None
            node.prev_demand = None
            node.demand = None
            node.prev_leak_demand = None
            node.leak_demand = None
            node.leak_status = False
            
        for name, node in self.nodes(Tank):
            node.prev_head = None
            node.head = node.init_level+node.elevation
            node.prev_demand = None
            node.demand = None
            node.prev_leak_demand = None
            node.leak_demand = None
            node.leak_status = False

        for name, node in self.nodes(Reservoir):
            node.prev_head = None
            node.head = node.base_head
            node.prev_demand = None
            node.demand = None
            node.prev_leak_demand = None
            node.leak_demand = None

        for name, link in self.links(Pipe):
            link.status = link._base_status
            link.prev_status = None
            link.prev_flow = None
            link.flow = None

        for name, link in self.links(Pump):
            link.status = link._base_status
            link.prev_status = None
            link.prev_flow = None
            link.flow = None
            link.power = link._base_power
            link._power_outage = False
            link._prev_power_outage = False

        for name, link in self.links(Valve):
            link.status = link._base_status
            link.prev_status = None
            link.prev_flow = None
            link.flow = None
            link.setting = link._base_setting
            link.prev_setting = None

    def _get_isolated_junctions(self):
        #udG = self._graph.to_undirected()
        #for link_name, link in self.pipes():
        #    if link.status==LinkStatus.closed:
        #        udG.remove_edge(link.start_node(), link.end_node(), key=link_name)
        #for link_name, link in self.pumps():
        #    if link.status==LinkStatus.closed:
        #        udG.remove_edge(link.start_node(), link.end_node(), key=link_name)
        #for link_name, link in self.valves():
        #    if link.status==LinkStatus.closed:
        #        udG.remove_edge(link.start_node(), link.end_node(), key=link_name)
        #        
        #if nx.is_connected(udG):
        #    return set(),set()
        #else:
        #    isolated_junctions = set()
        #    isolated_links = set()
        #    for subG in nx.connected_component_subgraphs(udG):
        #        has_tank_or_res = False
        #        for node_name in subG.nodes_iter():
        #            node_type = subG.node[node_name]['type']
        #            if node_type == 'tank' or node_type == 'reservoir':
        #                has_tank_or_res = True
        #                break
        #        if has_tank_or_res:
        #            continue
        #        else:
        #            isolated_junctions = isolated_junctions.union(set(subG.nodes()))
        #            for edge in subG.edges_iter():
        #                for link_name in subG.edge[edge[0]][edge[1]].keys():
        #                    isolated_links.add(link_name)
        #    return isolated_junctions, isolated_links
                    
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
                        if type(link)==Pipe:
                            connected_to_s = True
                        elif type(link)==Pump:
                            if link._cv_status != LinkStatus.closed:
                                connected_to_s = True
                        elif type(link)==Valve:
                            if link._status != LinkStatus.closed:
                                connected_to_s = True
                        else:
                            raise RuntimeError('Link type not recognized!')
                if connected_to_s:
                    if s not in groups[grp]:
                        grab_group(s)
            for p in pre:
                connected_to_p = False
                link_names_list = G.edge[p][node_name].keys()
                for link_name in link_names_list:
                    link = self.get_link(link_name)
                    if link.status!=LinkStatus.closed:
                        if type(link)==Pipe:
                            connected_to_p = True
                        elif type(link)==Pump:
                            if link._cv_status != LinkStatus.closed:
                                connected_to_p = True
                        elif type(link)==Valve:
                            if link._status != LinkStatus.closed:
                                connected_to_p = True
                        else:
                            raise RuntimeError('Link type not recognized!')
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
        
        #for grp, nodes in groups.iteritems():
        #    logger.debug('group: {0}'.format(grp))
        #    logger.debug('nodes[{0}]: {1}'.format(grp, nodes))
        #    logger.debug('has_tank_or_res[{0}]: {1}'.format(grp,has_tank_or_res[grp]))

        #all_nodes_check = set()
        #for grp, nodes in groups.iteritems():
        #    all_nodes_check = all_nodes_check.union(nodes)
        #if all_nodes_check!=set(self.node_name_list()):
        #    raise RuntimeError('_get_isolated_junctions() did not find all of the nodes!')

        #for grp1, nodes1 in groups.iteritems():
        #    for grp2, nodes2 in groups.iteritems():
        #        if grp1==grp2:
        #            pass
        #        elif len(nodes1.intersection(nodes2))>0:
        #            logger.debug('intersection of group {0} and gropup {1}: {2}'.format(grp1,grp2,nodes1.intersection(nodes2)))
        #            raise RuntimeError('The intersection of two groups is not empty!')

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

    def write_inpfile(self, filename, units='LPS'):
        """
         Write the current network into an EPANET inp file.

         Parameters
         ----------
         filename : string
            Name of the inp file. example - Net3_adjusted_demands.inp
         units : string
            Name of the units being written to the inp file
        """
        # TODO: This is still a very alpha version with hard coded unit conversions to LPS (among other things).

        units=units.upper()
        if units=='CFS':
            flowunit = 0
        elif units=='GPM':
            flowunit = 1
        elif units=='MGD':
            flowunit = 2
        elif units=='IMGD':
            flowunit = 3
        elif units=='AFD':
            flowunit = 4
        elif units=='LPS':
            flowunit = 5
        elif units=='LPM':
            flowunit = 6
        elif units=='MLD':
            flowunit = 7
        elif units=='CMH':
            flowunit = 8
        elif units=='CMD':
            flowunit = 9
        else:
            raise ValueError('units not recognized')

        f = open(filename, 'w')

        # Print title
        f.write('[TITLE]\n')
        if self.name is not None:
            f.write('{0}\n'.format(self.name))

        # Print junctions information
        f.write('[JUNCTIONS]\n')
        label_format = '{:20} {:>12s} {:>12s} {:24}\n'
        f.write(label_format.format(';ID', 'Elevation', 'Demand', 'Pattern'))
        for junction_name, junction in self.nodes(Junction):
            f.write('%s\n'%junction.to_inp_string(flowunit))

        # Print reservoir information
        f.write('[RESERVOIRS]\n')
        text_format = '{:20s} {:12f} {:>12s} {:>3s}\n'
        label_format = '{:20s} {:>12s} {:>12s}\n'
        f.write(label_format.format(';ID', 'Head', 'Pattern'))
        for reservoir_name, reservoir in self.nodes(Reservoir):
            if reservoir.head_pattern_name is not None:
                f.write(text_format.format(reservoir_name, convert('Hydraulic Head',flowunit,reservoir.base_head,False), reservoir.head_pattern_name, ';'))
            else:
                f.write(text_format.format(reservoir_name, convert('Hydraulic Head',flowunit,reservoir.base_head,False), '', ';'))

        # Print tank information
        f.write('[TANKS]\n')
        text_format = '{:20s} {:12f} {:12f} {:12f} {:12f} {:12f} {:12f} {:20s} {:>3s}\n'
        label_format = '{:20s} {:>12s} {:>12s} {:>12s} {:>12s} {:>12s} {:>12s} {:20s}\n'
        f.write(label_format.format(';ID', 'Elevation', 'Init Level', 'Min Level', 'Max Level', 'Diameter', 'Min Volume', 'Volume Curve'))
        for tank_name, tank in self.nodes(Tank):
            if tank.vol_curve is not None:
                f.write(text_format.format(tank_name, convert('Elevation',flowunit,tank.elevation,False), convert('Hydraulic Head',flowunit,tank.init_level,False), convert('Hydraulic Head',flowunit,tank.min_level,False), convert('Hydraulic Head',flowunit,tank.max_level,False), convert('Tank Diameter',flowunit,tank.diameter,False), convert('Volume',flowunit,tank.min_vol,False), tank.vol_curve, ';'))
            else:
                f.write(text_format.format(tank_name, convert('Elevation',flowunit,tank.elevation,False), convert('Hydraulic Head',flowunit,tank.init_level,False), convert('Hydraulic Head',flowunit,tank.min_level,False), convert('Hydraulic Head',flowunit,tank.max_level,False), convert('Tank Diameter',flowunit,tank.diameter,False), convert('Volume',flowunit,tank.min_vol,False), '', ';'))

        # Print pipe information
        f.write('[PIPES]\n')
        text_format = '{:20s} {:20s} {:20s} {:12f} {:12f} {:12f} {:12f} {:>20s} {:>3s}\n'
        label_format = '{:20s} {:20s} {:20s} {:>12s} {:>12s} {:>12s} {:>12s} {:>20s}\n'
        f.write(label_format.format(';ID', 'Node1', 'Node2', 'Length', 'Diameter', 'Roughness', 'Minor Loss', 'Status'))
        for pipe_name, pipe in self.links(Pipe):
            if pipe.cv:
                f.write(text_format.format(pipe_name, pipe.start_node(), pipe.end_node(), convert('Length',flowunit,pipe.length,False), convert('Pipe Diameter',flowunit,pipe.diameter,False), pipe.roughness, pipe.minor_loss, 'CV', ';'))                
            else:
                f.write(text_format.format(pipe_name, pipe.start_node(), pipe.end_node(), convert('Length',flowunit,pipe.length,False), convert('Pipe Diameter',flowunit,pipe.diameter,False), pipe.roughness, pipe.minor_loss, LinkStatus.status_to_str(pipe.get_base_status()), ';'))

        # Print pump information
        f.write('[PUMPS]\n')
        text_format = '{:20s} {:20s} {:20s} {:8s} {:20s} {:>3s}\n'
        label_format = '{:20s} {:20s} {:20s} {:20s}\n'
        f.write(label_format.format(';ID', 'Node1', 'Node2', 'Parameters'))
        for pump_name, pump in self.links(Pump):
            if pump.info_type == 'HEAD':
                f.write(text_format.format(pump_name, pump.start_node(), pump.end_node(), pump.info_type, pump.curve.name, ';'))
            elif pump.info_type == 'POWER':
                f.write(text_format.format(pump_name, pump.start_node(), pump.end_node(), pump.info_type, str(pump.power/1000.0), ';'))
            else:
                raise RuntimeError('Only head or power info is supported of pumps.')
        # Print valve information
        f.write('[VALVES]\n')
        text_format = '{:20s} {:20s} {:20s} {:12f} {:4s} {:12f} {:12f} {:>3s}\n'
        label_format = '{:20s} {:20s} {:20s} {:>12s} {:4s} {:>12s} {:>12s}\n'
        f.write(label_format.format(';ID', 'Node1', 'Node2', 'Diameter', 'Type', 'Setting', 'Minor Loss'))
        for valve_name, valve in self.links(Valve):
            f.write(text_format.format(valve_name, valve.start_node(), valve.end_node(), valve.diameter*1000, valve.valve_type, valve._base_setting, valve.minor_loss, ';'))

        # Print status information
        f.write('[STATUS]\n')
        text_format = '{:10s} {:10s}\n'
        label_format = '{:10s} {:10s}\n'
        f.write( label_format.format(';ID', 'Setting'))
        for link_name, link in self.links(Pump):
            if link.get_base_status() == LinkStatus.closed:
                f.write(text_format.format(link_name, LinkStatus.status_to_str(link.get_base_status())))
        for link_name, link in self.links(Valve):
            if link.get_base_status() == LinkStatus.closed or link.get_base_status()==LinkStatus.opened:
                f.write(text_format.format(link_name, LinkStatus.status_to_str(link.get_base_status())))

        # Print pattern information
        num_columns = 8
        f.write('[PATTERNS]\n')
        label_format = '{:10s} {:10s}\n'
        f.write(label_format.format(';ID', 'Multipliers'))
        for pattern_name, pattern in self._patterns.iteritems():
            count = 0
            for i in pattern:
                if count%8 == 0:
                    f.write('\n%s %f'%(pattern_name, i,))
                else:
                    f.write(' %f'%(i,))
                count += 1
            f.write('\n')

        # Print curves
        f.write('[CURVES]\n')
        text_format = '{:10s} {:10f} {:10f} {:>3s}\n'
        label_format = '{:10s} {:10s} {:10s}\n'
        f.write(label_format.format(';ID', 'X-Value', 'Y-Value'))
        for curve_name, curve in self._curves.items():
            for i in curve.points:
                f.write( text_format.format(curve_name, 1000*i[0], i[1], ';'))
            f.write('\n')

        # Print Controls
        f.write( '[CONTROLS]\n')
        # Time controls and conditional controls only
        for text, all_control in self._control_dict.items():
            if isinstance(all_control,wntr.network.TimeControl):
                f.write('%s\n'%all_control.to_inp_string())
            elif isinstance(all_control,wntr.network.ConditionalControl):
                f.write('%s\n'%all_control.to_inp_string(flowunit))
        f.write('\n')

        # Report
        f.write('[REPORT]\n')
        f.write('Status Yes\n')
        f.write('Summary yes\n')

        # Options
        f.write('[OPTIONS]\n')
        text_format_string = '{:20s} {:20s}\n'
        text_format_float = '{:20s} {:<20.8f}\n'
        f.write(text_format_string.format('UNITS', 'LPS'))
        f.write(text_format_string.format('HEADLOSS', self.options.headloss))
        if self.options.hydraulics_option is not None:
            f.write('{:20s} {:20s} {:<30s}\n'.format('HYDRAULICS', self.options.hydraulics_option, self.options.hydraulics_filename))
        if self.options.quality_value is None:
            f.write(text_format_string.format('QUALITY', self.options.quality_option))
        else:
            f.write('{:20s} {:20s} {:20s}\n'.format('QUALITY', self.options.quality_option, self.options.quality_value))
        f.write(text_format_float.format('VISCOSITY', self.options.viscosity))
        f.write(text_format_float.format('DIFFUSIVITY', self.options.diffusivity))
        f.write(text_format_float.format('SPECIFIC GRAVITY', self.options.specific_gravity))
        f.write(text_format_float.format('TRIALS', self.options.trials))
        f.write(text_format_float.format('ACCURACY', self.options.accuracy))
        f.write(text_format_float.format('CHECKFREQ', self.options.checkfreq))
        if self.options.unbalanced_value is None:
            f.write(text_format_string.format('UNBALANCED', self.options.unbalanced_option))
        else:
            f.write('{:20s} {:20s} {:20d}\n'.format('UNBALANCED', self.options.unbalanced_option, self.options.unbalanced_value))
        if self.options.pattern is not None:
            f.write(text_format_string.format('PATTERN', self.options.pattern))
        f.write(text_format_float.format('DEMAND MULTIPLIER', self.options.demand_multiplier))
        f.write(text_format_float.format('EMITTER EXPONENT', self.options.emitter_exponent))
        f.write(text_format_float.format('TOLERANCE', self.options.tolerance))
        if self.options.map is not None:
            f.write(text_format_string.format('MAP', self.options.map))

        f.write('\n')

        # Reaction Options
        f.write( '[REACTIONS]\n')
        text_format_float = '{:15s}{:15s}{:<10.8f}\n'
        f.write(text_format_float.format('ORDER','BULK',self.options.bulk_rxn_order))
        f.write(text_format_float.format('ORDER','WALL',self.options.wall_rxn_order))
        f.write(text_format_float.format('ORDER','TANK',self.options.tank_rxn_order))
        f.write(text_format_float.format('GLOBAL','BULK',self.options.bulk_rxn_coeff))
        f.write(text_format_float.format('GLOBAL','WALL',self.options.wall_rxn_coeff))
        if self.options.limiting_potential is not None:
            f.write(text_format_float.format('LIMITING','POTENTIAL',self.options.limiting_potential))
        if self.options.roughness_correlation is not None:
            f.write(text_format_float.format('ROUGHNESS','CORRELATION',self.options.roughness_correlation))
        for tank_name, tank in self.nodes(Tank):
            if tank.bulk_rxn_coeff is not None:
                f.write(text_format_float.format('TANK',tank_name,tank.bulk_rxn_coeff))
        for pipe_name, pipe in self.links(Pipe):
            if pipe.bulk_rxn_coeff is not None:
                f.write(text_format_float.format('BULK',pipe_name,pipe.bulk_rxn_coeff))
            if pipe.wall_rxn_coeff is not None:
                f.write(text_format_float.format('WALL',pipe_name,pipe.wall_rxn_coeff))

        f.write('\n')

        # Time options
        f.write('[TIMES]\n')
        text_format = '{:20s} {:10s}\n'
        time_text_format = '{:20s} {:d}:{:d}:{:d}\n'
        hrs, mm, sec = self._sec_to_string(self.options.duration)
        f.write(time_text_format.format('DURATION', hrs, mm, sec))
        hrs, mm, sec = self._sec_to_string(self.options.hydraulic_timestep)
        f.write(time_text_format.format('HYDRAULIC TIMESTEP', hrs, mm, sec))
        hrs, mm, sec = self._sec_to_string(self.options.pattern_timestep)
        f.write(time_text_format.format('PATTERN TIMESTEP', hrs, mm, sec))
        hrs, mm, sec = self._sec_to_string(self.options.pattern_start)
        f.write(time_text_format.format('PATTERN START', hrs, mm, sec))
        hrs, mm, sec = self._sec_to_string(self.options.report_timestep)
        f.write(time_text_format.format('REPORT TIMESTEP', hrs, mm, sec))
        hrs, mm, sec = self._sec_to_string(self.options.report_start)
        f.write(time_text_format.format('REPORT START', hrs, mm, sec))

        hrs, mm, sec = self._sec_to_string(self.options.start_clocktime)
        if hrs < 12:
            time_format = ' AM'
        else:
            hrs -= 12
            time_format = ' PM'
        f.write('{:20s} {:d}:{:d}:{:d}{:s}\n'.format('START CLOCKTIME', hrs, mm, sec, time_format))

        hrs, mm, sec = self._sec_to_string(self.options.quality_timestep)
        f.write(time_text_format.format('QUALITY TIMESTEP', hrs, mm, sec))
        hrs, mm, sec = self._sec_to_string(self.options.rule_timestep)
        f.write(time_text_format.format('RULE TIMESTEP', hrs, mm, int(sec)))
        f.write(text_format.format('STATISTIC', self.options.statistic))

        f.write('\n')

        # Coordinates
        f.write('[COORDINATES]\n')
        text_format = '{:10s} {:<10.2f} {:<10.2f}\n'
        label_format = '{:10s} {:10s} {:10s}\n'
        f.write(label_format.format(';Node', 'X-Coord', 'Y-Coord'))
        coord = nx.get_node_attributes(self._graph, 'pos')
        for key, val in coord.iteritems():
            f.write(text_format.format(key, val[0], val[1]))

        f.close()

    def _sec_to_string(self, sec):
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        return (hours, mm, int(sec))
 
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
        self.checkfreq = 2

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

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        elif self._name == other._name:
            return True
        return False
        
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
        self._base_status = LinkStatus.opened
        self.status = LinkStatus.opened
        self.prev_flow = None
        self.flow = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        elif self._link_name       == other._link_name       and \
           self._start_node_name   == other._start_node_name and \
           self._end_node_name     == other._end_node_name:
            return True
        return False

    def get_base_status(self):
        """
        Returns the base status.
        """
        return self._base_status

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
        self._leak_start_control_name = 'junction'+self._name+'start_leak_control'
        self._leak_end_control_name = 'junction'+self._name+'end_leak_control'

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Junction, self).__eq__(other):
            return False
        if abs(self.elevation - other.elevation)<1e-10 and \
           abs(self.nominal_pressure - other.nominal_pressure)<1e-10 and \
           abs(self.minimum_pressure - other.minimum_pressure)<1e-10:
            return True
        return False

    def to_inp_string(self, flowunit):
        text_format = '{:20} {:12f} {:12f} {:24} {:>3s}'
        if self.base_demand == 0.0:
            return '{:20} {:12f} {:12s} {:24} {:>3s}'.format(self._name, convert('Elevation',flowunit,self.elevation,False), '0.0', '', ';')
        elif self.demand_pattern_name is not None:
            return text_format.format(self._name, convert('Elevation',flowunit,self.elevation,MKS=False), convert('Demand',flowunit,self.base_demand,False), self.demand_pattern_name, ';')
        else:
            return text_format.format(self._name, convert('Elevation',flowunit,self.elevation,False), convert('Demand',flowunit,self.base_demand,False), '', ';')
        

    def add_leak(self, wn, area, discharge_coeff = 0.75, start_time=None, end_time=None):
        """Method to add a leak to a junction. Leaks are modeled by:

        Q = discharge_coeff*area*sqrt(2*g*h)

        where:
           Q is the volumetric flow rate of water out of the leak
           g is the acceleration due to gravity
           h is the guage head at the junction, P_g/(rho*g); Note that this is not the hydraulic head (P_g + elevation)

        Parameters
        ----------
        wn: WaterNetworkModel object
           The WaterNetworkModel object containing the junction with
           the leak. This information is needed because the
           WaterNetworkModel object stores all controls, including
           when the leak starts and stops.
        area: float
           Area of the leak in m^2.
        discharge_coeff: float
           Leak discharge coefficient; Takes on values between 0 and 1.
        start_time: int
           Start time of the leak in seconds. If the start_time is
           None, it is assumed that an external control will be used
           to start the leak (otherwise, the leak will not start).
        end_time: int
           Time at which the leak is fixed in seconds. If the end_time
           is None, it is assumed that an external control will be
           used to end the leak (otherwise, the leak will not end).

        """

        self._leak = True
        self.leak_area = area
        self.leak_discharge_coeff = discharge_coeff

        if start_time is not None:
            start_control_action = wntr.network.ControlAction(self, 'leak_status', True)
            control = wntr.network.TimeControl(wn, start_time, 'SIM_TIME', False, start_control_action)
            wn.add_control(self._leak_start_control_name, control)

        if end_time is not None:
            end_control_action = wntr.network.ControlAction(self, 'leak_status', False)
            control = wntr.network.TimeControl(wn, end_time, 'SIM_TIME', False, end_control_action)
            wn.add_control(self._leak_end_control_name, control)

    def remove_leak(self,wn):
        """
        Method to remove a leak from a junction

        Parameters
        ----------
        wn: WaterNetworkModel object
        """
        self._leak = False
        wn.discard_control(self._leak_start_control_name)
        wn.discard_control(self._leak_end_control_name)

    def leak_present(self):
        """
        Method to check if the junction has a leak or not. Note that this
        does not check whether or not the leak is active (i.e., if the
        current time is between leak_start_time and leak_end_time).

        Returns
        -------
        bool: True if a leak is present, False if a leak is not present
        """
        return self._leak

    def set_leak_start_time(self, wn, t):
        """
        Method to set a start time for the leak. This internally creates a
        TimeControl object and adds it to the network for you. Please
        make sure all user-defined controls for starting the leak have
        been removed before using this method (see
        WaterNetworkModel.remove_leak() or
        WaterNetworkModel.discard_leak()).

        Parameters
        ----------
        wn: WaterNetworkModel object
        t: int
           end time in seconds
        """
        # remove old control
        wn.discard_control(self._leak_start_control_name)

        # add new control
        start_control_action = wntr.network.ControlAction(self, 'leak_status', True)
        control = wntr.network.TimeControl(wn, t, 'SIM_TIME', False, start_control_action)
        wn.add_control(self._leak_start_control_name, control)
    
    def set_leak_end_time(self, wn, t):
        """
        Method to set an end time for the leak. This internally creates a
        TimeControl object and adds it to the network for you. Please
        make sure all user-defined controls for ending the leak have
        been removed before using this method (see
        WaterNetworkModel.remove_leak() or
        WaterNetworkModel.discard_leak()).

        Parameters
        ----------
        wn: WaterNetworkModel object
        t: int
           end time in seconds
        """
        # remove old control
        wn.discard_control(self._leak_end_control_name)
    
        # add new control
        end_control_action = wntr.network.ControlAction(self, 'leak_status', False)
        control = wntr.network.TimeControl(wn, t, 'SIM_TIME', False, end_control_action)
        wn.add_control(self._leak_end_control_name, control)
    
    def discard_leak_controls(self, wn):
        """
        Method to specify that user-defined controls will be used to
        start and stop the leak. This will remove any controls set up
        through Junction.add_leak(), Junction.set_leak_start_time(),
        or Junction.set_leak_end_time().

        Parameters
        ----------
        wn: WaterNetworkModel object
        """
        wn.discard_control(self._leak_start_control_name)
        wn.discard_control(self._leak_end_control_name)

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
        self._leak_start_control_name = 'tank'+self._name+'start_leak_control'
        self._leak_end_control_name = 'tank'+self._name+'end_leak_control'
        self.bulk_rxn_coeff = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Tank, self).__eq__(other):
            return False
        if abs(self.elevation   - other.elevation)<1e-10 and \
           abs(self.min_vol     - other.min_vol)<1e-10   and \
           abs(self.diameter    - other.diameter)<1e-10  and \
           abs(self.min_level   - other.min_level)<1e-10 and \
           abs(self.max_level   - other.max_level)<1e-10 and \
           self.bulk_rxn_coeff == other.bulk_rxn_coeff   and \
           self.vol_curve      == other.vol_curve:
            return True
        return False    
        
    def add_leak(self, wn, area, discharge_coeff = 0.75, start_time=None, end_time=None):
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
        wn: WaterNetworkModel object
           The WaterNetworkModel object containing the tank with
           the leak. This information is needed because the
           WaterNetworkModel object stores all controls, including
           when the leak starts and stops.
        area: float
           Area of the leak in m^2.
        discharge_coeff: float
           Leak discharge coefficient; Takes on values between 0 and 1.
        start_time: int
           Start time of the leak in seconds. If the start_time is
           None, it is assumed that an external control will be used
           to start the leak (otherwise, the leak will not start).
        end_time: int
           Time at which the leak is fixed in seconds. If the end_time
           is None, it is assumed that an external control will be
           used to end the leak (otherwise, the leak will not end).

        """

        self._leak = True
        self.leak_area = area
        self.leak_discharge_coeff = discharge_coeff
        
        if start_time is not None:
            start_control_action = wntr.network.ControlAction(self, 'leak_status', True)
            control = wntr.network.TimeControl(wn, start_time, 'SIM_TIME', False, start_control_action)
            wn.add_control(self._leak_start_control_name, control)

        if end_time is not None:
            end_control_action = wntr.network.ControlAction(self, 'leak_status', False)
            control = wntr.network.TimeControl(wn, end_time, 'SIM_TIME', False, end_control_action)
            wn.add_control(self._leak_end_control_name, control)

    def remove_leak(self,wn):
        """
        Method to remove a leak from a tank.

        Parameters
        ----------
        wn: WaterNetworkModel object
        """
        self._leak = False
        wn.discard_control(self._leak_start_control_name)
        wn.discard_control(self._leak_end_control_name)

    def leak_present(self):
        """
        Method to check if the tank has a leak or not. Note that this
        does not check whether or not the leak is active (i.e., if the
        current time is between leak_start_time and leak_end_time).

        Returns
        -------
        bool: True if a leak is present, False if a leak is not present
        """
        return self._leak

    def set_leak_start_time(self, wn, t):
        """
        Method to set a start time for the leak. This internally creates a
        TimeControl object and adds it to the network for you. Please
        make sure all user-defined controls for starting the leak have
        been removed before using this method (see
        WaterNetworkModel.remove_leak() or
        WaterNetworkModel.discard_leak()).

        Parameters
        ----------
        wn: WaterNetworkModel object
        t: int
           start time in seconds
        """
        # remove old control
        wn.discard_control(self._leak_start_control_name)

        # add new control
        start_control_action = wntr.network.ControlAction(self, 'leak_status', True)
        control = wntr.network.TimeControl(wn, t, 'SIM_TIME', False, start_control_action)
        wn.add_control(self._leak_start_control_name, control)
    
    def set_leak_end_time(self, wn, t):
        """
        Method to set an end time for the leak. This internally creates a
        TimeControl object and adds it to the network for you. Please
        make sure all user-defined controls for ending the leak have
        been removed before using this method (see
        WaterNetworkModel.remove_leak() or
        WaterNetworkModel.discard_leak()).

        Parameters
        ----------
        wn: WaterNetworkModel object
        t: int
           end time in seconds
        """
        # remove old control
        wn.discard_control(self._leak_end_control_name)
    
        # add new control
        end_control_action = wntr.network.ControlAction(self, 'leak_status', False)
        control = wntr.network.TimeControl(wn, t, 'SIM_TIME', False, end_control_action)
        wn.add_control(self._leak_end_control_name, control)
    
    def use_external_leak_control(self, wn):
        """
        Method to specify that user-defined controls will be used to
        start and stop the leak. This will remove any controls set up
        through Tank.add_leak(), Tank.set_leak_start_time(),
        or Tank.set_leak_end_time().

        Parameters
        ----------
        wn: WaterNetworkModel object
        """
        wn.discard_control(self._leak_start_control_name)
        wn.discard_control(self._leak_end_control_name)

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

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Reservoir, self).__eq__(other):
            return False
        return True

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
            self._base_status = self.status
        self.bulk_rxn_coeff = None
        self.wall_rxn_coeff = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Pipe, self).__eq__(other):
            return False
        if abs(self.length        - other.length)<1e-10     and \
           abs(self.diameter      - other.diameter)<1e-10   and \
           abs(self.roughness     - other.roughness)<1e-10  and \
           abs(self.minor_loss    - other.minor_loss)<1e-10 and \
           self.cv               == other.cv                and \
           self.bulk_rxn_coeff   == other.bulk_rxn_coeff    and \
           self.wall_rxn_coeff   == other.wall_rxn_coeff:
            return True
        return False
    
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
        self._power_outage = False
        self._prev_power_outage = False
        self._base_power = None
        self.info_type = info_type.upper()
        if self.info_type == 'HEAD':
            self.curve = info_value
        elif self.info_type == 'POWER':
            self.power = info_value
            self._base_power = info_value
        else:
            raise RuntimeError('Pump info type not recognized. Options are HEAD or POWER.')

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Pump, self).__eq__(other):
            return False
        if self.info_type == other.info_type and \
           self.curve == other.curve:
            return True
        return False
        
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
            raise RuntimeError('Coefficient for Multipoint pump curves cannot be generated. ')

        if A<=0 or B<0 or C<=0:
            raise RuntimeError('Value of pump head curve coefficient is negative, which is not allowed. \nPump: {0} \nA: {1} \nB: {2} \nC:{3}'.format(self.name(),A,B,C))
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
        self._base_setting = setting
        self._base_status = LinkStatus.active
        self.status = LinkStatus.active
        self._status = LinkStatus.active

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Valve, self).__eq__(other):
            return False
        if abs(self.diameter   - other.diameter)<1e-10 and \
           self.valve_type    == other.valve_type      and \
           abs(self.minor_loss - other.minor_loss)<1e-10:
            return True
        return False

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

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self.name == other.name and \
           self.curve_type == other.curve_type and \
           self.num_points == other.num_points:
            for point1, point2 in zip(self.points, other.points):
                for value1, value2 in zip(point1, point2):
                    if not abs(value1 - value2)<1e-8:
                        return False
            return True
        return False
