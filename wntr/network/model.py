"""
The wntr.network.model module includes methods to define a water network
model.
"""
import copy
import networkx as nx
import math
from scipy.optimize import fsolve
import wntr.network
import wntr.network.controls
import wntr.epanet
import numpy as np
import sys
import logging
import enum

logger = logging.getLogger(__name__)

class WaterNetworkModel(object):
    """
    Base water network model class.

    Parameters
    -------------------
    inp_file_name: string (optional)
        Directory and filename of EPANET inp file to load into the
        WaterNetworkModel object.
    """

    def __init__(self, inp_file_name=None):

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
        self._num_sources = 0
        self._num_demands = 0

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
        self._sources = {}
        self._demands = {}

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

        self._backdrop = _Backdrop()
        self.energy = Energy()
        self._reportopts = _Report()
        self._labels = None

        self._inpfile = None
        if inp_file_name:
            self.read_inpfile(inp_file_name)

    def __eq__(self, other):
        #self._control_dict   == other._control_dict   and \
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
           self._sources        == other._sources        and \
           self._check_valves   == other._check_valves:
            return True
        return False

    def __hash__(self):
        return id(self)

    def add_junction(self, name, base_demand=0.0, demand_pattern_name=None, elevation=0.0, coordinates=None):
        """
        Adds a junction to the water network model.

        Parameters
        -------------------
        name : string
            Name of the junction.
        base_demand : float
            Base demand at the junction.
        demand_pattern_name : string
            Name of the demand pattern.
        elevation : float
            Elevation of the junction.
        coordinates : tuple of floats
            X-Y coordinates of the node location.
        """
        base_demand = float(base_demand)
        elevation = float(elevation)
        junction = Junction(name, base_demand, demand_pattern_name, elevation)
        self._nodes[name] = junction
        self._junctions[name] = junction
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        nx.set_node_attributes(self._graph, name='type', values={name:'junction'})
        self._num_junctions += 1

    def add_tank(self, name, elevation=0.0, init_level=3.048,
                 min_level=0.0, max_level=6.096, diameter=15.24,
                 min_vol=None, vol_curve=None, coordinates=None):
        """
        Adds a tank to the water network model.

        Parameters
        -------------------
        name : string
            Name of the tank.
        elevation : float
            Elevation at the Tank.
        init_level : float
            Initial tank level.
        min_level : float
            Minimum tank level.
        max_level : float
            Maximum tank level.
        diameter : float
            Tank diameter.
        min_vol : float
            Minimum tank volume.
        vol_curve : Curve object
            Curve object
        coordinates : tuple of floats
            X-Y coordinates of the node location.
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
        nx.set_node_attributes(self._graph, name='type', values={name: 'tank'})
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
                        if link.end_node == tank_name:
                            continue
                        else:
                            link_has_cv = True
                if isinstance(link, Pump):
                    if link.end_node == tank_name:
                        continue
                    else:
                        link_has_cv = True

                close_control_action = wntr.network.ControlAction(link, 'status', LinkStatus.closed)
                open_control_action = wntr.network.ControlAction(link, 'status', LinkStatus.opened)

                control = wntr.network.ConditionalControl((tank,'head'), np.less_equal, min_head,close_control_action)
                control._priority = 1
                control.name = link_name+' closed because tank '+tank.name+' head is less than min head'
                tank_controls.append(control)

                if not link_has_cv:
                    control = wntr.network._MultiConditionalControl([(tank,'head'), (tank, 'prev_head'),
                                                                    (self, 'sim_time')],
                                                                   [np.greater, np.less_equal,np.greater],
                                                                   [min_head+self._Htol, min_head+self._Htol, 0.0],
                                                                   open_control_action)
                    control._partial_step_for_tanks = False
                    control._priority = 0
                    control.name = link_name+' opened because tank '+tank.name+' head is greater than min head'
                    tank_controls.append(control)

                    if link.start_node == tank_name:
                        other_node_name = link.end_node
                    else:
                        other_node_name = link.start_node
                    other_node = self.get_node(other_node_name)
                    control = wntr.network._MultiConditionalControl([(tank,'head'),(tank,'head')],
                                                                   [np.less_equal,np.less_equal],
                                                                   [min_head+self._Htol,(other_node,'head')],
                                                                   open_control_action)
                    control._priority = 2
                    control.name = (link_name+' opened because tank '+tank.name+
                                    ' head is below min head but flow should be in')
                    tank_controls.append(control)

            # Now take care of the max level
            max_head = tank.max_level+tank.elevation
            for link_name in all_links:
                link = self.get_link(link_name)
                link_has_cv = False
                if isinstance(link, Pipe):
                    if link.cv:
                        if link.start_node==tank_name:
                            continue
                        else:
                            link_has_cv = True
                if isinstance(link, Pump):
                    if link.start_node==tank_name:
                        continue
                    else:
                        link_has_cv = True

                close_control_action = wntr.network.ControlAction(link, 'status', LinkStatus.closed)
                open_control_action = wntr.network.ControlAction(link, 'status', LinkStatus.opened)

                control = wntr.network.ConditionalControl((tank,'head'),np.greater_equal,max_head,close_control_action)
                control._priority = 1
                control.name = link_name+' closed because tank '+tank.name+' head is greater than max head'
                tank_controls.append(control)

                if not link_has_cv:
                    control = wntr.network._MultiConditionalControl([(tank,'head'),(tank,'prev_head'),(self,'sim_time')],[np.less,np.greater_equal,np.greater],[max_head-self._Htol,max_head-self._Htol,0.0],open_control_action)
                    control._partial_step_for_tanks = False
                    control._priority = 0
                    control.name = link_name+'opened because tank '+tank.name+' head is less than max head'
                    tank_controls.append(control)

                    if link.start_node == tank_name:
                        other_node_name = link.end_node
                    else:
                        other_node_name = link.start_node
                    other_node = self.get_node(other_node_name)
                    control = wntr.network._MultiConditionalControl([(tank,'head'),(tank,'head')],[np.greater_equal,np.greater_equal],[max_head-self._Htol,(other_node,'head')],open_control_action)
                    control._priority = 2
                    control.name = link_name+' opened because tank '+tank.name+' head above max head but flow should be out'
                    tank_controls.append(control)

                #control = wntr.network._MultiConditionalControl([(tank,'head'),(other_node,'head')],[np.greater,np.greater],[max_head-self._Htol,max_head-self._Htol], close_control_action)
                #control._priority = 2
                #self.add_control(control)

        return tank_controls

    def add_reservoir(self, name, base_head=0.0, head_pattern_name=None, coordinates=None):
        """
        Adds a reservoir to the water network model.

        Parameters
        ----------
        name : string
            Name of the reservoir.
        base_head : float, optional
            Base head at the reservoir.
        head_pattern_name : string, optional
            Name of the head pattern.
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        """
        base_head = float(base_head)
        reservoir = Reservoir(name, base_head, head_pattern_name)
        self._nodes[name] = reservoir
        self._reservoirs[name] = reservoir
        self._graph.add_node(name)
        if coordinates is not None:
            self.set_node_coordinates(name, coordinates)
        nx.set_node_attributes(self._graph, name='type', values={name:'reservoir'})
        self._num_reservoirs += 1

    def add_pipe(self, name, start_node_name, end_node_name, length=304.8,
                 diameter=0.3048, roughness=100, minor_loss=0.0, status='OPEN', check_valve_flag=False):
        """
        Adds a pipe to the water network model.

        Parameters
        ----------
        name : string
            Name of the pipe.
        start_node_name : string
             Name of the start node.
        end_node_name : string
             Name of the end node.
        length : float, optional
            Length of the pipe.
        diameter : float, optional
            Diameter of the pipe.
        roughness : float, optional
            Pipe roughness coefficient.
        minor_loss : float, optional
            Pipe minor loss coefficient.
        status : string, optional
            Pipe status. Options are 'Open' or 'Closed'.
        check_valve_flag : bool, optional
            True if the pipe has a check valve.
            False if the pipe does not have a check valve.
        """
        length = float(length)
        diameter = float(diameter)
        roughness = float(roughness)
        minor_loss = float(minor_loss)
        if isinstance(status, str):
            status = LinkStatus[status]
        pipe = Pipe(name, start_node_name, end_node_name, length,
                    diameter, roughness, minor_loss, status, check_valve_flag)
        # Add to list of cv
        if check_valve_flag:
            self._check_valves.append(name)

        self._links[name] = pipe
        self._pipes[name] = pipe
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        nx.set_edge_attributes(self._graph, name='type', values={(start_node_name, end_node_name, name):'pipe'})
        self._num_pipes += 1

    def _get_cv_controls(self):
        cv_controls = []
        for pipe_name in self._check_valves:
            pipe = self.get_link(pipe_name)

            close_control_action = wntr.network.ControlAction(pipe, 'status', LinkStatus.closed)
            open_control_action = wntr.network.ControlAction(pipe, 'status', LinkStatus.opened)

            control = wntr.network._CheckValveHeadControl(self, pipe, np.greater, self._Htol, open_control_action)
            control._priority = 0
            control.name = pipe.name+'opened because of cv head control'
            cv_controls.append(control)

            control = wntr.network._CheckValveHeadControl(self, pipe, np.less, -self._Htol, close_control_action)
            control._priority = 3
            control.name = pipe.name+' closed because of cv head control'
            cv_controls.append(control)

            control = wntr.network.ConditionalControl((pipe,'flow'),np.less, -self._Qtol, close_control_action)
            control._priority = 3
            control.name = pipe.name+' closed because negative flow in cv'
            cv_controls.append(control)

        return cv_controls

    def add_pump(self, name, start_node_name, end_node_name, info_type='POWER', info_value=50.0,
                 speed=1.0, pattern=None):
        """
        Adds a pump to the water network model.

        Parameters
        ----------
        name : string
            Name of the pump.
        start_node_name : string
             Name of the start node.
        end_node_name : string
             Name of the end node.
        info_type : string, optional
            Type of information provided for a pump. Options are 'POWER' or 'HEAD'.
        info_value : float or Curve object, optional
            Float value of power in KW. Head curve object.
        speed: float
            Relative speed setting (1.0 is normal speed)
        pattern: str
            ID of pattern for speed setting
        """
        pump = Pump(name, start_node_name, end_node_name, info_type, info_value, speed, pattern)
        self._links[name] = pump
        self._pumps[name] = pump
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        nx.set_edge_attributes(self._graph, name='type', values={(start_node_name, end_node_name, name):'pump'})
        self._num_pumps += 1

    def _get_pump_controls(self):
        pump_controls = []
        for pump_name, pump in self.links(Pump):

            close_control_action = wntr.network.ControlAction(pump, '_cv_status', LinkStatus.closed)
            open_control_action = wntr.network.ControlAction(pump, '_cv_status', LinkStatus.opened)

            control = wntr.network._CheckValveHeadControl(self, pump, np.greater, self._Htol, open_control_action)
            control._priority = 0
            control.name = pump.name+' opened because of cv head control'
            pump_controls.append(control)

            control = wntr.network._CheckValveHeadControl(self, pump, np.less, -self._Htol, close_control_action)
            control._priority = 3
            control.name = pump.name+' closed because of cv head control'
            pump_controls.append(control)

            control = wntr.network.ConditionalControl((pump,'flow'),np.less, -self._Qtol, close_control_action)
            control._priority = 3
            control.name = pump.name+' closed because negative flow in pump'
            pump_controls.append(control)

        return pump_controls

    def add_valve(self, name, start_node_name, end_node_name,
                 diameter=0.3048, valve_type='PRV', minor_loss=0.0, setting=0.0):
        """
        Adds a valve to the water network model.

        Parameters
        ----------
        name : string
            Name of the valve.
        start_node_name : string
             Name of the start node.
        end_node_name : string
             Name of the end node.
        diameter : float, optional
            Diameter of the valve.
        valve_type : string, optional
            Type of valve. Options are 'PRV', etc.
        minor_loss : float, optional
            Pipe minor loss coefficient.
        setting : float or string, optional
            pressure setting for PRV, PSV, or PBV,
            flow setting for FCV,
            loss coefficient for TCV,
            name of headloss curve for GPV.
        """
        start_node = self.get_node(start_node_name)
        end_node = self.get_node(end_node_name)
        if type(start_node)==Tank or type(end_node)==Tank:
            logger.warn('Valves should not be connected to tanks! Please add a pipe between the tank and valve. Note that this will be an error in the next release.')

        valve = Valve(name, start_node_name, end_node_name,
                      diameter, valve_type, minor_loss, setting)
        self._links[name] = valve
        self._valves[name] = valve
        self._graph.add_edge(start_node_name, end_node_name, key=name)
        nx.set_edge_attributes(self._graph, name='type', values={(start_node_name, end_node_name, name):'valve'})
        self._num_valves += 1

    def _get_valve_controls(self):
        valve_controls = []
        for valve_name, valve in self.links(Valve):

            if valve.valve_type == 'PRV':
                close_control_action = wntr.network.ControlAction(valve, '_status', LinkStatus.Closed)
                open_control_action = wntr.network.ControlAction(valve, '_status', LinkStatus.Opened)
                active_control_action = wntr.network.ControlAction(valve, '_status', LinkStatus.Active)

                control = wntr.network._PRVControl(self, valve, self._Htol, self._Qtol, close_control_action, open_control_action, active_control_action)
                control.name = valve.name+' prv control'
                valve_controls.append(control)
            elif valve.valve_type == 'FCV':
                open_control_action = wntr.network.ControlAction(valve, '_status', LinkStatus.Opened)
                active_control_action = wntr.network.ControlAction(valve, '_status', LinkStatus.Active)
                control = wntr.network.controls._FCVControl(self, valve, self._Htol, open_control_action,
                                                            active_control_action)
                control.name = valve.name + ' FCV control'
                valve_controls.append(control)

        return valve_controls

    def add_pattern(self, name, pattern_list=None, start_time=None, end_time=None):
        """
        Adds a pattern to the water network model.
        If pattern_list is None, a new binary pattern will be created using
        the pattern timestep and duration stored in wn.options.
        The pattern will have 1s between the start time and end time.

        Parameters
        ----------
        name : string
            Name of the pattern.
        pattern_list : list of floats
            A list of floats that make up the pattern.
        start_time: float
            If pattern_list is None, a new binary pattern will be created using start_time.
        end_time: float
            If pattern_list is None, a new binary pattern will be created using end_time.
        """
        if pattern_list is None:
            patternstep = self.options.pattern_timestep
            duration = self.options.duration
            patternlen = int(duration/patternstep)
            patternstart = int(start_time/patternstep)
            patternend = int(end_time/patternstep)
            pattern_list = [0.0]*patternlen
            pattern_list[patternstart:patternend] = [1.0]*(patternend-patternstart)

        self._patterns[name] = pattern_list

    def add_curve(self, name, curve_type, xy_tuples_list):
        """
        Adds a curve to the water network model.

        Parameters
        ----------
        name : string
            Name of the curve.
        curve_type : string
            Type of curve. Options are HEAD, EFFICIENCY, VOLUME, HEADLOSS.
        xy_tuples_list : list of tuples
            List of X-Y coordinate tuples on the curve.
        """
        curve = Curve(name, curve_type, xy_tuples_list)
        self._curves[name] = curve

    def add_source(self, name, node_name, source_type, quality, pattern_name):
        """
        Adds a source to the water network model.

        Parameters
        ----------
        name : string
            Name of the source

        node_name: string
            Injection node.

        source_type: string
            Source type, options = CONCEN, MASS, FLOWPACED, or SETPOINT

        quality: float
            Source strength in Mass/Time for MASS and Mass/Volume for CONCEN, FLOWPACED, or SETPOINT

        pattern_name: string
            Pattern name
        """
        source = Source(name, node_name, source_type, quality, pattern_name)
        self._sources[name] = source
        self._num_sources += 1

    def _add_demand(self, name, junction_name, base_demand=0.0, demand_pattern_name=None):

        demands = _Demands(name, junction_name, base_demand, demand_pattern_name)
        self._demands[name] = demands
        self._num_demands += 1

    def add_control(self, name, control_object):
        """
        Adds a control to the water network model.

        Parameters
        ----------
        name : string
           control object name.
        control_object : Control object
            Control object.
        """
        if name in self._control_dict:
            raise ValueError('The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control.')

        if not isinstance(control_object, wntr.network.controls.IfThenElseControl):
            target = control_object._control_action._target_obj_ref
            if isinstance(target, Link):
                start_node_name = target.start_node
                end_node_name = target.end_node
                start_node = self.get_node(start_node_name)
                end_node = self.get_node(end_node_name)
                if type(start_node)==Tank or type(end_node)==Tank:
                    logger.warning('Controls should not be added to links that are connected to tanks. Consider adding an additional link and using the control on it. Note that this will become an error in the next release.')
            control_object.name = name
        self._control_dict[name] = control_object

    def add_pump_outage(self, pump_name, start_time, end_time):
        """
        Adds a pump outage to the water network model.

        Parameters
        ----------
        pump_name : string
           The name of the pump to be affected by an outage.
        start_time : int
           The time at which the outage starts.
        end_time : int
           The time at which the outage stops.
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

        control = wntr.network._MultiConditionalControl([(pump,'_power_outage')],[np.equal],[True], closed_action_obj)
        control._priority = 3
        self.add_control(pump_name+'PowerOffStatus'+str(end_time),control)

        control = wntr.network._MultiConditionalControl([(pump,'_prev_power_outage'),(pump,'_power_outage')],[np.equal,np.equal],[True,False],opened_action_obj)
        control._priority = 0
        self.add_control(pump_name+'PowerOnStatus'+str(start_time),control)

#    def all_pump_outage(self, start_time, end_time):
#        """
#        Add a pump outage to the water network model that affects all pumps.
#
#        Parameters
#        ----------
#        start_time : int
#           The time at which the outage starts
#        end_time : int
#           The time at which the outage stops.
#        """
#        for pump_name, pump in self.links(Pump):
#            self.add_pump_outage(pump_name, start_time, end_time)

    def remove_link(self, name, with_control=True):
        """
        Removes a link from the water network model.

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
            logger.warn('You are removing a pipe with a check valve.')
        self._graph.remove_edge(link.start_node, link.end_node, key=name)
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
            for control_name, control in self._control_dict.items():
                if type(control)==wntr.network._PRVControl:
                    if link==control._close_control_action._target_obj_ref:
                        logger.warn('Control '+control_name+' is being removed along with link '+name)
                        x.append(control_name)
                else:
                    if link == control._control_action._target_obj_ref:
                        logger.warn('Control '+control_name+' is being removed along with link '+name)
                        x.append(control_name)
            for i in x:
                self.remove_control(i)
        else:
            for control_name, control in self._control_dict.items():
                if type(control)==wntr.network._PRVControl:
                    if link==control._close_control_action._target_obj_ref:
                        logger.warn('A link is being removed that is the target object of a control. However, the control is not being removed.')
                else:
                    if link == control._control_action._target_obj_ref:
                        logger.warn('A link is being removed that is the target object of a control. However, the control is not being removed.')

    def remove_node(self, name, with_control=True):
        """
        Removes a node from the water network model.

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
            for control_name, control in self._control_dict.items():
                if type(control)==wntr.network._PRVControl:
                    if node==control._close_control_action._target_obj_ref:
                        logger.warn('Control '+control_name+' is being removed along with node '+name)
                        x.append(control_name)
                else:
                    if node == control._control_action._target_obj_ref:
                        logger.warn('Control '+control_name+' is being removed along with node '+name)
                        x.append(control_name)
            for i in x:
                self.remove_control(i)
        else:
            for control_name, control in self._control_dict.items():
                if type(control)==wntr.network._PRVControl:
                    if node==control._close_control_action._target_obj_ref:
                        logger.warn('A node is being removed that is the target object of a control. However, the control is not being removed.')
                else:
                    if node == control._control_action._target_obj_ref:
                        logger.warn('A node is being removed that is the target object of a control. However, the control is not being removed.')

    def remove_source(self, name):
        """
        Removes a source from the water network model.

        Parameters
        ----------
        name : string
           The name of the source object to be removed.
        """
        del self._sources[name]
        self._num_sources -= 1

    def remove_control(self, name):
        """
        Removes a control from the water network model.
        If the control is not present, an exception is raised.

        Parameters
        ----------
        name : string
           The name of the control object to be removed.
        """
        del self._control_dict[name]

    def _discard_control(self, name):
        """
        Removes a control from the water network model.
        If the control is not present, an exception is not raised.

        Parameters
        ----------
        name : string
           The name of the control object to be removed.
        """
        try:
            del self._control_dict[name]
        except KeyError:
            pass

    def split_pipe(self, pipe_name_to_split, new_pipe_name, new_junction_name,
                   add_pipe_at_node='end', split_at_point=0.5):
        """Splits a pipe by adding a junction and one new pipe segment.
        
        This method is convenient when adding leaks to a pipe. It provides 
        an initially zero-demand node at some point along the pipe and then
        reconnects the original pipe to this node and adds a new pipe to the
        other side. Hydraulic paths are maintained. The new junction can 
        then have a leak added to it.
        
        It is important to note that check valves are not added to the new
        pipe. By allowing the new pipe to be connected at either the start
        or the end of the old pipe, this allows the split to occur before
        or after the check valve. Additionally, no controls will be added
        to the new pipe; the old pipe will keep any controls. Again, this
        allows the split to occur before or after a "valve" that is controled
        by opening or closing a pipe.
        
        This method keeps 'pipe_name_to_split', resizes it, and adds
        a new pipe to keep total length equal. The pipe will be split at 
        a new junction placed at a point 'split_at_point' of the way 
        between the start and end (in that direction). The new pipe can be
        added to 'add_pipe_at_node' of either ``start`` or ``end``. For
        example, if ``add_pipe_at_node='start'``, then the original pipe
        will go from the new junction to the original end node, and the
        new pipe will go from the original start node to the new junction.
        
        The new pipe will have the same diameter,
        roughness, minor loss, and base status of the original
        pipe. The new junction will have a base demand of 0,
        an elevation equal to the 'split_at_point' x 100% of the 
        elevation between the
        original start and end nodes, coordinates at 'split_at_point'
        between the original start and end nodes, and will use the
        default demand pattern.
        
        Parameters
        ----------
        pipe_name_to_split: string
            The name of the pipe to split.

        new_pipe_name: string
            The name of the new pipe to be added as the split part of the pipe.

        new_junction_name: string
            The name of the new junction to be added.

        add_pipe_at_node: string
            Either 'start' or 'end', 'end' is default. The new pipe goes between this
            original node and the new junction.
            
        split_at_point: float
            Between 0 and 1, the position along the original pipe where the new 
            junction will be located.
                
            
        Returns
        -------
        tuple
            returns (original_pipe, new_junction, new_pipe) objects
            
        """
        
        # Do sanity checks
        pipe = self.get_link(pipe_name_to_split)
        if not isinstance(pipe, Pipe):
            raise ValueError('You can only split pipes.')
        if split_at_point < 0 or split_at_point > 1:
            raise ValueError('split_at_point must be between 0 and 1')
        if add_pipe_at_node.lower() not in ['end', 'start']:
            raise ValueError('add_pipe_at_node must be "end" or "start"')
        node_list = [node_name for node_name, node in self.nodes()]
        link_list = [link_name for link_name, link in self.links()]
        if new_junction_name in node_list:
            raise RuntimeError('The junction name you provided is already being used for another node.')
        if new_pipe_name in link_list:
            raise RuntimeError('The new link name you provided is already being used for another link.')

        # Get start and end node info
        start_node = self.get_node(pipe.start_node)
        end_node = self.get_node(pipe.end_node)
        
        # calculate the new elevation
        if isinstance(start_node, Reservoir):
            junction_elevation = end_node.elevation
        elif isinstance(end_node, Reservoir):
            junction_elevation = start_node.elevation
        else:
            e0 = start_node.elevation
            de = end_node.elevation - e0
            junction_elevation = e0 + de * split_at_point

        # calculate the new coordinates
        x0 = self._graph.node[pipe.start_node]['pos'][0]
        dx = self._graph.node[pipe.end_node]['pos'][0] - x0
        y0 = self._graph.node[pipe.start_node]['pos'][1]
        dy = self._graph.node[pipe.end_node]['pos'][1] - y0
        junction_coordinates = (x0 + dx * split_at_point,
                                y0 + dy * split_at_point)

        # add the new junction
        self.add_junction(new_junction_name, base_demand=0.0, demand_pattern_name=None,
                          elevation=junction_elevation, coordinates=junction_coordinates)
        new_junction = self.get_node(new_junction_name)

        # remove the original pipe from the graph (to be added back below)
        self._graph.remove_edge(pipe.start_node, pipe.end_node, key=pipe_name_to_split)
        original_length = pipe.length

        if add_pipe_at_node.lower() == 'start':
            # add original pipe back to graph between new junction and original end
            pipe._start_node_name = new_junction_name
            self._graph.add_edge(new_junction_name, end_node.name, key=pipe_name_to_split)
            nx.set_edge_attributes(self._graph, name='type', values={(new_junction_name, 
                                                          pipe.end_node,
                                                          pipe_name_to_split):'pipe'})
            # add new pipe and change original length
            self.add_pipe(new_pipe_name, start_node.name, new_junction_name,
                          original_length*split_at_point, pipe.diameter, pipe.roughness,
                          pipe.minor_loss, pipe.status, pipe.cv)
            pipe.length = original_length * (1-split_at_point)

        elif add_pipe_at_node.lower() == 'end':
            # add original pipe back to graph between original start and new junction
            pipe._end_node_name = new_junction_name            
            self._graph.add_edge(start_node.name, new_junction_name, key=pipe_name_to_split)
            nx.set_edge_attributes(self._graph, name='type', values={(pipe.start_node,
                                                          new_junction_name,
                                                          pipe_name_to_split):'pipe'})
            # add new pipe and change original length
            self.add_pipe(new_pipe_name, new_junction_name, end_node.name,
                          original_length*(1-split_at_point), pipe.diameter, pipe.roughness,
                          pipe.minor_loss, pipe.status, pipe.cv)
            pipe.length = original_length * split_at_point
        new_pipe = self.get_link(new_pipe_name)
        if pipe.cv:
            logger.warn('You are splitting a pipe with a check valve. The new pipe will not have a check valve.')
        return (pipe, new_junction, new_pipe)

    def _break_pipe(self, pipe_name_to_split, new_pipe_name, new_junction_name_old_pipe,
                   new_junction_name_new_pipe,
                   add_pipe_at_node='end', split_at_point=0.5):
        """BETA Breaks a pipe by adding a two unconnected junctions and one new pipe segment.
        
        This method provides a true broken pipe -- i.e., there is no longer flow possible 
        from one side of the break to the other. This is more likely to break the model
        through non-convergable hydraulics than a simple split_pipe with a leak added.

        It is important to note that check valves are not added to the new
        pipe. By allowing the new pipe to be connected at either the start
        or the end of the old pipe, this allows the break to occur before
        or after the check valve. This may mean that one of the junctions will
        not have demand, as it would be inaccessible. No error checking is 
        performed to stop such a condition, it is left to the user.
        Additionally, no controls will be added
        to the new pipe; the old pipe will keep any controls. Again, this
        allows the break to occur before or after a "valve" that is controled
        by opening or closing a pipe.
        
        This method keeps 'pipe_name_to_split', resizes it, and adds
        a new pipe to keep total length equal. Two junctions are added at the same position,
        but are not connected. The pipe will be split at 
        a point 'split_at_point' of the way 
        between the start and end (in that direction). The new pipe can be
        added to 'add_pipe_at_node' of either ``start`` or ``end``. For
        example, if ``add_pipe_at_node='start'``, then the original pipe
        will go from the first new junction to the original end node, and the
        new pipe will go from the original start node to the second new junction.
        
        The new pipe will have the same diameter,
        roughness, minor loss, and base status of the original
        pipe. The new junctions will have a base demand of 0,
        an elevation equal to the 'split_at_point' x 100% of the 
        elevation between the
        original start and end nodes, coordinates at 'split_at_point'
        between the original start and end nodes, and will use the
        default demand pattern. These junctions will be returned so that 
        a new demand (usually a leak) can be added to them.
        
        The original pipe will keep its controls.  
        The new pipe _will not_ have any controls automatically added;
        this includes not adding a check valve.
        
        Parameters
        ----------
        pipe_name_to_split: string
            The name of the pipe to split.

        new_pipe_name: string
            The name of the new pipe to be added as the split part of the pipe.

        new_junction_name_old_pipe: string
            The name of the new junction to be added to the original pipe

        new_junction_name_old_pipe: string
            The name of the new junction to be added to the new pipe

        add_pipe_at_node: string
            Either 'start' or 'end', 'end' is default. The new pipe goes between this
            original node and the new junction.
            
        split_at_point: float
            Between 0 and 1, the position along the original pipe where the new 
            junction will be located.
                
            
        Returns
        -------
        tuple
            Returns the new junctions that have been created, with the junction attached to the 
            original pipe as the first element of the tuple
            
        """
        
        # Do sanity checks
        pipe = self.get_link(pipe_name_to_split)
        if not isinstance(pipe, Pipe):
            raise ValueError('You can only split pipes.')
        if split_at_point < 0 or split_at_point > 1:
            raise ValueError('split_at_point must be between 0 and 1')
        if add_pipe_at_node.lower() not in ['end', 'start']:
            raise ValueError('add_pipe_at_node must be "end" or "start"')
        node_list = [node_name for node_name, node in self.nodes()]
        link_list = [link_name for link_name, link in self.links()]
        if new_junction_name_old_pipe in node_list or new_junction_name_new_pipe in node_list:
            raise RuntimeError('The junction name you provided is already being used for another node.')
        if new_pipe_name in link_list:
            raise RuntimeError('The new link name you provided is already being used for another link.')

        # Get start and end node info
        start_node = self.get_node(pipe.start_node)
        end_node = self.get_node(pipe.end_node)
        
        # calculate the new elevation
        if isinstance(start_node, Reservoir):
            junction_elevation = end_node.elevation
        elif isinstance(end_node, Reservoir):
            junction_elevation = start_node.elevation
        else:
            e0 = start_node.elevation
            de = end_node.elevation - e0
            junction_elevation = e0 + de * split_at_point

        # calculate the new coordinates
        x0 = self._graph.node[pipe.start_node]['pos'][0]
        dx = self._graph.node[pipe.end_node]['pos'][0] - x0
        y0 = self._graph.node[pipe.start_node]['pos'][1]
        dy = self._graph.node[pipe.end_node]['pos'][1] - y0
        junction_coordinates = (x0 + dx * split_at_point,
                                y0 + dy * split_at_point)

        # add the new junction
        self.add_junction(new_junction_name_old_pipe, base_demand=0.0, demand_pattern_name=None,
                          elevation=junction_elevation, coordinates=junction_coordinates)
        new_junction1 = self.get_node(new_junction_name_old_pipe)
        self.add_junction(new_junction_name_new_pipe, base_demand=0.0, demand_pattern_name=None,
                          elevation=junction_elevation, coordinates=junction_coordinates)
        new_junction2 = self.get_node(new_junction_name_new_pipe)

        # remove the original pipe from the graph (to be added back below)
        self._graph.remove_edge(pipe.start_node, pipe.end_node, key=pipe_name_to_split)
        original_length = pipe.length

        if add_pipe_at_node.lower() == 'start':
            # add original pipe back to graph between new junction and original end
            pipe._start_node_name = new_junction_name_old_pipe
            self._graph.add_edge(new_junction_name_old_pipe, end_node.name, key=pipe_name_to_split)
            nx.set_edge_attributes(self._graph, name='type', values={(new_junction_name_old_pipe, 
                                                          end_node.name,
                                                          pipe_name_to_split):'pipe'})
            # add new pipe and change original length
            self.add_pipe(new_pipe_name, start_node.name, new_junction_name_new_pipe,
                          original_length*split_at_point, pipe.diameter, pipe.roughness,
                          pipe.minor_loss, pipe.status, pipe.cv)
            pipe.length = original_length * (1-split_at_point)

        elif add_pipe_at_node.lower() == 'end':
            # add original pipe back to graph between original start and new junction
            pipe._end_node_name = new_junction_name_old_pipe            
            self._graph.add_edge(start_node.name, new_junction_name_old_pipe, key=pipe_name_to_split)
            nx.set_edge_attributes(self._graph, name='type', values={(start_node.name,
                                                          new_junction_name_old_pipe,
                                                          pipe_name_to_split):'pipe'})
            # add new pipe and change original length
            self.add_pipe(new_pipe_name, new_junction_name_new_pipe, end_node.name,
                          original_length*(1-split_at_point), pipe.diameter, pipe.roughness,
                          pipe.minor_loss, pipe.status, pipe.cv)
            pipe.length = original_length * split_at_point
        new_pipe = self.get_link(new_pipe_name)
        if pipe.cv:
            logger.warn('You are splitting a pipe with a check valve. The new pipe will not have a check valve.')
        return (pipe, new_junction1, new_junction2, new_pipe)

    def reset_demand(self, demand, pattern_prefix='ResetDemand'):
        """
        Resets demands.
        New demands are specified in a pandas DataFrame indexed by simulation
        time (in seconds) and one column for each node. The method resets
        node demands by creating a new demand pattern for each node and
        resetting the base demand to 1. The demand pattern is resampled to
        match the water network model pattern timestep. This method can be
        used to reset demands in a water network model to demands from a
        pressure dependent demand simualtion.

        Parameters
        ----------
        demand : pandas DataFrame
            Name of the node.

        pattern_prefix: str
            Pattern prefix, default = 'ResetDemand'
        """
        for node_name, node in self.nodes():

            # Extact the node demand pattern and resample to match the pattern timestep
            demand_pattern = demand.loc[:, node_name]
            demand_pattern.index = demand_pattern.index.astype('timedelta64[s]')
            resample_offset = str(int(self.options.pattern_timestep))+'S'
            demand_pattern = demand_pattern.resample(resample_offset).mean()

            # Add the pattern
            pattern_name = pattern_prefix + node_name
            self.add_pattern(pattern_name, demand_pattern.tolist())

            # Reset base demand
            node.base_demand = 1
            node.demand_pattern_name = pattern_name

    def get_node(self, name):
        """
        Returns the node object of a specific node.

        Parameters
        ----------
        name : string
            Name of the node.

        Returns
        --------
        Node object.
        """
        return self._nodes[name]

    def get_link(self, name):
        """
        Returns the link object of a specific link.

        Parameters
        ----------
        name : string
            Name of the link.

        Returns
        --------
        Link object.
        """
        return self._links[name]

    def get_control(self, name):
        """
        Returns the control object of a specific control.

        Parameters
        ----------
        name: string
           Name of the control

        Returns
        --------
        Control object.
        """
        return self._control_dict[name]

    def get_source(self, name):
        """
        Returns the source object of a specific source.

        Parameters
        ----------
        name: string
           Name of the source

        Returns
        --------
        Source object.
        """
        return self._sources[name]

    def get_links_for_node(self, node_name, flag='ALL'):
        """
        Returns a list of links connected to a node.

        Parameters
        ----------
        node_name : string
            Name of the node.

        flag : string
            Options are 'ALL', 'INLET', 'OUTLET'.
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
            edges = list(in_edges) + list(out_edges)
        if flag.upper() == 'INLET':
            in_edges = self._graph.in_edges(node_name, data=False, keys=True)
            edges = list(in_edges)
        if flag.upper() == 'OUTLET':
            out_edges = self._graph.out_edges(node_name, data=False, keys=True)
            edges = list(out_edges)
        list_of_links = []
        for edge_tuple in edges:
            list_of_links.append(edge_tuple[2])

        return list_of_links

    def get_node_coordinates(self, name=None):
        """
        Returns node coordinates.

        Parameters
        ----------
        name: string
            Name of the node.

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
        Returns the curve object of a specific curve.

        Parameters
        ----------
        name : string
            Name of the curve.

        Returns
        --------
        Curve object.
        """
        return self._curves[name]

    def get_pattern(self, name):
        """
        Returns the pattern object of a specific pattern.

        Parameters
        ----------
        name : string
            Name of the pattern.

        Returns
        --------
        Pattern object.
        """
        return self._patterns[name]

    def get_graph_deep_copy(self):
        """
        Returns a deep copy of the WaterNetworkModel networkx graph.

        Returns
        --------
        WaterNetworkModel networkx graph.
        """
        return copy.deepcopy(self._graph)

    def query_node_attribute(self, attribute, operation=None, value=None, node_type=None):
        """
        Query node attributes, for example get all nodes with elevation <= threshold.

        Parameters
        ----------
        attribute: string
            Node attribute.

        operation: numpy operator
            Numpy operator, options include
            np.greater,
            np.greater_equal,
            np.less,
            np.less_equal,
            np.equal,
            np.not_equal.

        value: float or int
            Threshold

        node_type: Node type
            Node type, options include
            wntr.network.model.Node,
            wntr.network.model.Junction,
            wntr.network.model.Reservoir,
            wntr.network.model.Tank, or None. Default = None.
            Note None and wntr.network.model.Node produce the same results.

        Returns
        -------
        A dictionary of node names to attribute where node_type satisfies the
        operation threshold.

        Notes
        -----
        If operation and value are both None, the dictionary will contain the attributes
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
        """
        Query link attributes, for example get all pipe diameters > threshold.

        Parameters
        ----------
        attribute: string
            Link attribute

        operation: numpy operator
            Numpy operator, options include
            np.greater,
            np.greater_equal,
            np.less,
            np.less_equal,
            np.equal,
            np.not_equal.

        value: float or int
            Threshold

        link_type: Link type
            Link type, options include
            wntr.network.model.Link,
            wntr.network.model.Pipe,
            wntr.network.model.Pump,
            wntr.network.model.Valve, or None. Default = None.
            Note None and wntr.network.model.Link produce the same results.

        Returns
        -------
        A dictionary of link names to attributes where link_type satisfies the
        operation threshold.

        Notes
        -----
        If operation and value are both None, the dictionary will contain the attributes
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

    @property
    def num_nodes(self):
        """
        Returns the number of nodes in the water network model.
        """
        return len(self._nodes)

    @property
    def num_junctions(self):
        """
        Returns the number of junctions in the water network model.
        """
        return self._num_junctions

    @property
    def num_tanks(self):
        """
        Returns the number of tanks in the water network model.
        """
        return self._num_tanks

    @property
    def num_reservoirs(self):
        """
        Returns the number of reservoirs in the water network model.
        """
        return self._num_reservoirs

    @property
    def num_links(self):
        """
        Returns the number of links in the water network model.
        """
        return len(self._links)

    @property
    def num_pipes(self):
        """
        Returns the number of pipes in the water network model.
        """
        return self._num_pipes

    @property
    def num_pumps(self):
        """
        Returns the number of pumps in the water network model.
        """
        return self._num_pumps

    @property
    def num_valves(self):
        """
        Returns the number of valves in the water network model.
        """
        return self._num_valves

    def nodes(self, node_type=None):
        """
        Returns a generator to iterate over all nodes of a specific node type.
        If no node type is specified, the generator iterates over all nodes.

        Parameters
        ----------
        node_type: Node type
            Node type, options include
            wntr.network.model.Node,
            wntr.network.model.Junction,
            wntr.network.model.Reservoir,
            wntr.network.model.Tank, or None. Default = None.
            Note None and wntr.network.model.Node produce the same results.

        Returns
        -------
        A generator in the format (name, object).
        """
        if node_type==None:
            for node_name, node in self._nodes.items():
                yield node_name, node
        elif node_type==Junction:
            for node_name, node in self._junctions.items():
                yield node_name, node
        elif node_type==Tank:
            for node_name, node in self._tanks.items():
                yield node_name, node
        elif node_type==Reservoir:
            for node_name, node in self._reservoirs.items():
                yield node_name, node
        else:
            raise RuntimeError('node_type, '+str(node_type)+', not recognized.')

    def junctions(self):
        """
        Returns a generator to iterate over all junctions.

        Returns
        -------
        A generator in the format (name, object).
        """
        for name, node in self._junctions.items():
            yield name, node

    def tanks(self):
        """
        Returns a generator to iterate over all tanks.

        Returns
        -------
        A generator in the format (name, object).
        """
        for name, node in self._tanks.items():
            yield name, node

    def reservoirs(self):
        """
        Returns a generator to iterate over all reservoirs.

        Returns
        -------
        A generator in the format (name, object).
        """
        for name, node in self._reservoirs.items():
            yield name, node

    def links(self, link_type=None):
        """
        Returns a generator to iterate over all links of link_type.
        If no link_type is passed, this method iterates over all links.

        Return a generator to iterate over all links of a specific link type.
        If no link type is specified, the generator iterates over all links.

        Parameters
        ----------
        link_type: Link type
            Link type, options include
            wntr.network.model.Link,
            wntr.network.model.Pipe,
            wntr.network.model.Pump,
            wntr.network.model.Valve, or None. Default = None.
            Note None and wntr.network.model.Link produce the same results.

        Returns
        -------
        A generator in the format (name, object).
        """
        if link_type==None:
            for link_name, link in self._links.items():
                yield link_name, link
        elif link_type==Pipe:
            for link_name, link in self._pipes.items():
                yield link_name, link
        elif link_type==Pump:
            for link_name, link in self._pumps.items():
                yield link_name, link
        elif link_type==Valve:
            for link_name, link in self._valves.items():
                yield link_name, link
        else:
            raise RuntimeError('link_type, '+str(link_type)+', not recognized.')

    def pipes(self):
        """
        Returns a generator to iterate over all pipes.

        Returns
        -------
        A generator in the format (name, object).
        """
        for name, link in self._pipes.items():
            yield name, link

    def pumps(self):
        """
        Returns a generator to iterate over all pumps.

        Returns
        -------
        A generator in the format (name, object).
        """
        for name, link in self._pumps.items():
            yield name, link

    def valves(self):
        """
        Returns a generator to iterate over all valves.

        Returns
        -------
        A generator in the format (name, object).
        """
        for name, link in self._valves.items():
            yield name, link

    def curves(self):
        """
        Returns a generator to iterate over all curves.

        Returns
        -------
        A generator in the format (name, object).
        """
        for curve_name, curve in self._curves.items():
            yield curve_name, curve

    def sources(self):
        """
        Returns a generator to iterate over all sources.

        Returns
        -------
        A generator in the format (name, object).
        """
        for source_name, source in self._sources.items():
            yield source_name, source

    @property
    def node_name_list(self):
        """
        Returns a list of the names of all nodes.
        """
        return list(self._nodes.keys())

    @property
    def junction_name_list(self):
        """
        Returns a list of the names of all junctions.
        """
        return list(self._junctions.keys())

    @property
    def tank_name_list(self):
        """
        Returns a list of the names of all tanks.
        """
        return list(self._tanks.keys())

    @property
    def reservoir_name_list(self):
        """
        Returns a list of the names of all reservoirs.
        """
        return list(self._reservoirs.keys())

    @property
    def link_name_list(self):
        """
        Returns a list of the names of all links.
        """
        return list(self._links.keys())

    @property
    def pipe_name_list(self):
        """
        Returns a list of the names of all pipes.
        """
        return list(self._pipes.keys())

    @property
    def pump_name_list(self):
        """
        Returns a list of the names of all pumps.
        """
        return list(self._pumps.keys())

    @property
    def valve_name_list(self):
        """
        Returns a list of the names of all valves.
        """
        return list(self._valves.keys())

    def set_node_coordinates(self, name, coordinates):
        """
        Sets the node coordinates in the networkx graph.

        Parameters
        ----------
        name : string
            Name of the node.
        coordinates : tuple
            X-Y coordinates.
        """
        nx.set_node_attributes(self._graph, name='pos', values={name: coordinates})

    def scale_node_coordinates(self, scale):
        """
        Scales node coordinates, using 1:scale.  Scale should be in meters.

        Parameters
        -----------
        scale : float
            Coordinate scale multiplier.
        """
        pos = nx.get_node_attributes(self._graph, 'pos')

        for name, node in self._nodes.items():
            self.set_node_coordinates(name, (pos[name][0]*scale, pos[name][1]*scale))

    @property
    def _shifted_time(self):
        """
        Return the time in seconds shifted by the
        simulation start time (e.g. as specified in the
        inp file). This is, this is the time since 12 AM
        on the first day.
        """
        return self.sim_time + self.options.start_clocktime

    @property
    def _prev_shifted_time(self):
        """
        Return the time in seconds of the previous solve shifted by
        the simulation start time. That is, this is the time from 12
        AM on the first day to the time at the prevous hydraulic
        timestep.
        """
        return self.prev_sim_time + self.options.start_clocktime

    @property
    def _clock_time(self):
        """
        Return the current time of day in seconds from 12 AM
        """
        return self.shifted_time % (24*3600)

    @property
    def _clock_day(self):
        return int(self.shifted_time / 86400)

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

    def read_inpfile(self, filename):
        """
        Defines water network model components from an EPANET INP file.

        Parameters
        ----------
        filename : string
            Name of the INP file.

        """
        inpfile = wntr.epanet.InpFile()
        inpfile.read(filename, wn=self)
        self._inpfile = inpfile

    def write_inpfile(self, filename, units=None):
        """
        Writes the current water network model to an EPANET INP file.

        Parameters
        ----------
        filename : string
            Name of the inp file.
        units : str, int or FlowUnits
            Name of the units being written to the inp file.

        """
        if self._inpfile is None:
            logger.warning('Writing a minimal INP file without saved non-WNTR options (energy, etc.)')
            self._inpfile = wntr.epanet.InpFile()
        self._inpfile.write(filename, self, units=units)

    def _sec_to_string(self, sec):
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        return (hours, mm, int(sec))

class WaterNetworkOptions(object):
    """
    A class to manage options.  These options mimic options in the EPANET User Manual.
    """

    def __init__(self):
        # Time related options
        self.duration = 0
        "Simulation duration in seconds"

        self.hydraulic_timestep = 3600
        "Hydraulic timestep in seconds."

        self.quality_timestep = 360.0
        "Water quality timestep in seconds"

        self.rule_timestep = 360.0
        "Rule timestep in seconds"

        self.pattern_timestep = 3600.0
        "Pattern timestep in seconds"

        self.pattern_start = 0.0
        "Time offset in seconds at which all patterns will start. E.g., a value of 7200 would start the simulation with each pattern in the time period that corresponds to hour 2."

        self.report_timestep = 3600.0
        "Reporting timestep in seconds"

        self.report_start = 0.0
        "Start time of the report in seconds from the start of the simulation."

        self.start_clocktime = 0.0
        "Time of day in seconds from 12 am at which the simulation begins."

        self.statistic = 'NONE'
        "Post processing statistic.  Options are AVERAGED, MINIMUM, MAXIUM, RANGE, and NONE (as defined in the EPANET User Manual)."

        # General options
        self.units = 'GPM'
        "EPANET INP File units of measurement.  Options are CFS, GPM, MGD, IMGD, AFD, LPS, LPM, MLD, CMH, and CMD (as defined in the EPANET User Manual)."

        self.headloss = 'H-W'
        "Formula to use for computing head loss through a pipe. Options are H-W, D-W, and C-M (as defined in the EPANET User Manual)."

        self.hydraulics = None #string
        "Indicates if a hydraulics file should be used or saved.  Options are USE and SAVE (as defined in the EPANET User Manual)."

        self.hydraulics_filename = None #string
        "Filename to use if hydraulics = SAVE"

        self.quality = 'NONE'
        "Type of water quality analysis.  Options are NONE, CHEMICAL, AGE, and TRACE (as defined in the EPANET User Manual)."

        self.quality_value = None #string
        "Trace node name if quality = TRACE, Chemical units if quality = CHEMICAL"

        self.viscosity = 1.0
        "Kinematic viscosity of the fluid"

        self.diffusivity = 1.0
        "Molecular diffusivity of the chemical"

        self.specific_gravity = 1.0
        "Specific gravity of the fluid"

        self.trials = 40
        "Maximum number of trials used to solve network hydraulics"

        self.accuracy = 0.001
        "Convergence criteria for hydraulic solutions"

        self.unbalanced = 'STOP'
        "Indicate what happens if a hydraulic solution cannot be reached.  Options are STOP and CONTINUE  (as defined in the EPANET User Manual)."

        self.unbalanced_value = None #int
        "Number of additional trials if unbalanced = CONTINUE"

        self.pattern = None
        "Name of the default pattern for junction demands. If None, the junctions without patterns will be held constant."

        self.demand_multiplier = 1.0
        "The demand multiplier adjusts the values of baseline demands for all junctions"

        self.emitter_exponent = 0.5
        "The exponent used when computing flow from an emitter"

        self.tolerance = 0.01
        "Convergence criteria for water quality solutions"

        self.map = None
        "Filename used to store node coordinates"

        self.checkfreq = 2
        "Number of solution trials that pass between status check"

        self.maxcheck = 10
        "Number of solution trials that pass between status check"

        self.damplimit = 0
        "Accuracy value at which solution damping begins"

        # Reaction options
        self.bulk_rxn_order = 1.0
        "Order of reaction occurring in the bulk fluid"

        self.wall_rxn_order = 1.0
        "Order of reaction occurring at the pipe wall"

        self.tank_rxn_order = 1.0
        "Order of reaction occurring in the tanks"

        self.bulk_rxn_coeff = 0.0
        "Reaction coefficient for bulk fluid and tanks"

        self.wall_rxn_coeff = 0.0
        "Reaction coefficient for pipe walls"

        self.limiting_potential = None
        "Specifies that reaction rates are proportional to the difference between the current concentration and some limiting potential value"

        self.roughness_correlation = None
        "Makes all default pipe wall reaction coefficients related to pipe roughness"


    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if abs(self.duration - other.duration)<1e-10 and \
           abs(self.hydraulic_timestep - other.hydraulic_timestep)<1e-10 and \
           abs(self.quality_timestep - other.quality_timestep)<1e-10 and \
           abs(self.rule_timestep - other.rule_timestep)<1e-10 and \
           abs(self.pattern_timestep - other.pattern_timestep)<1e-10 and \
           abs(self.pattern_start - other.pattern_start)<1e-10 and \
           abs(self.report_timestep - other.report_timestep)<1e-10 and \
           abs(self.report_start - other.report_start)<1e-10 and \
           abs(self.start_clocktime - other.start_clocktime)<1e-10 and \
           self.statistic == other.statistic and \
           self.headloss == other.headloss and \
           self.hydraulics == other.hydraulics and \
           self.hydraulics_filename == other.hydraulics_filename and \
           self.quality == other.quality and \
           self.quality_value == other.quality_value and \
           abs(self.viscosity - other.viscosity)<1e-10 and \
           abs(self.diffusivity - other.diffusivity)<1e-10 and \
           abs(self.specific_gravity - other.specific_gravity)<1e-10 and \
           abs(self.trials - other.trials)<1e-10 and \
           abs(self.accuracy - other.accuracy)<1e-10 and \
           self.unbalanced == other.unbalanced and \
           self.pattern == other.pattern and \
           abs(self.demand_multiplier - other.demand_multiplier)<1e-10 and \
           abs(self.emitter_exponent - other.emitter_exponent)<1e-10 and \
           abs(self.tolerance - other.tolerance)<1e-10 and \
           self.map == other.map and \
           abs(self.checkfreq - other.checkfreq)<1e-10 and \
           abs(self.maxcheck - other.maxcheck)<1e-10 and \
           abs(self.damplimit - other.damplimit)<1e-10 and \
           abs(self.bulk_rxn_order - other.bulk_rxn_order)<1e-10 and \
           abs(self.wall_rxn_order - other.wall_rxn_order)<1e-10 and \
           abs(self.tank_rxn_order - other.tank_rxn_order)<1e-10 and \
           abs(self.bulk_rxn_coeff - other.bulk_rxn_coeff)<1e-10 and \
           abs(self.wall_rxn_coeff - other.wall_rxn_coeff)<1e-10 and \
           abs(self.limiting_potential - other.limiting_potential)<1e-10 and \
           abs(self.roughness_correlation - other.roughness_correlation)<1e-10:
               return True
        return False

class NodeType(enum.IntEnum):
    """
    An enum class for types of nodes.

    .. rubric:: Enum Members

    ==================  ==================================================================
    :attr:`~Junction`   Node is a :class:`~wntr.network.model.Junction`
    :attr:`~Reservoir`  Node is a :class:`~wntr.network.model.Reservoir`
    :attr:`~Tank`       Node is a :class:`~wntr.network.model.Tank`
    ==================  ==================================================================

    """
    Junction = 0
    Reservoir = 1
    Tank = 2

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return int(self) == int(other) and (isinstance(other, int) or \
               self.__class__.__name__ == other.__class__.__name__)


class LinkType(enum.IntEnum):
    """
    An enum class for types of links.

    .. rubric:: Enum Members

    ===============  ==================================================================
    :attr:`~CV`      Pipe with check valve
    :attr:`~Pipe`    Regular pipe
    :attr:`~Pump`    Pump
    :attr:`~Valve`   Any valve type (see following)
    :attr:`~PRV`     Pressure reducing valve
    :attr:`~PSV`     Pressure sustaining valve
    :attr:`~PBV`     Pressure breaker valve
    :attr:`~FCV`     Flow control valve
    :attr:`~TCV`     Throttle control valve
    :attr:`~GPV`     General purpose valve
    ===============  ==================================================================

    """
    CV = 0
    Pipe = 1
    Pump = 2
    PRV = 3
    PSV = 4
    PBV = 5
    FCV = 6
    TCV = 7
    GPV = 8
    Valve = 9

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return int(self) == int(other) and (isinstance(other, int) or \
               self.__class__.__name__ == other.__class__.__name__)


class LinkStatus(enum.IntEnum):
    """
    An enum class for link statuses.
    
    .. warning:: 
        This is NOT the class for determining output status from an EPANET binary file.
        The class for output status is wntr.epanet.util.LinkTankStatus.

    .. rubric:: Enum Members

    ===============  ==================================================================
    :attr:`~Closed`  Pipe/valve/pump is closed.
    :attr:`~Opened`  Pipe/valve/pump is open.
    :attr:`~Open`    Alias to "Opened"
    :attr:`~Active`  Valve is partially open.
    ===============  ==================================================================

    """
    Closed = 0
    Open = 1
    Opened = 1
    Active = 2
    CV = 3

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return int(self) == int(other) and (isinstance(other, int) or \
               self.__class__.__name__ == other.__class__.__name__)


class Node(object):
    """
    The base node class.

    Parameters
    -----------
    name : string
        Name of the node
    node_type : string
        Type of the node. Options are 'Junction', 'Tank', or 'Reservoir'


    """
    def __init__(self, name):

        self._name = name
        self.prev_head = None
        self.head = None
        self.prev_demand = None
        self.demand = None
        self.leak_demand = None
        self.prev_leak_demand = None
        self.initial_quality = None
        self.tag = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self._name == other._name and \
           self.initial_quality == other.initial_quality and \
           self.tag == other.tag:
               return True
        return False

    def __str__(self):
        """
        Returns the name of the node when printing to a stream.
        """
        return self._name

    def __repr__(self):
        return "<Node '{}'>".format(self._name)

    def __hash__(self):
        return id(self)

    @property
    def name(self):
        """
        Returns the name of the node.
        """
        return self._name


class Link(object):
    """
    The base link class.

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

    """

    def __init__(self, link_name, start_node_name, end_node_name):

        self._link_name = link_name
        self._start_node_name = start_node_name
        self._end_node_name = end_node_name
        self.prev_status = None
        self._base_status = LinkStatus.opened
        self.status = LinkStatus.opened
        self.prev_flow = None
        self.flow = None
        self.tag = None
        self._vertices = []

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        elif self._link_name       == other._link_name       and \
           self._start_node_name   == other._start_node_name and \
           self._end_node_name     == other._end_node_name and \
           self.tag               == other.tag:
            return True
        return False

    def __hash__(self):
        return id(self)

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

    def __repr__(self):
        return "<Link '{}'>".format(self._link_name)

    @property
    def start_node(self):
        """
        Returns name of start node
        """
        return self._start_node_name

    @property
    def end_node(self):
        """
        Returns name of end node
        """
        return self._end_node_name

    @property
    def name(self):
        """
        Returns the name of the link
        """
        return self._link_name

class Junction(Node):
    """
    Junction class that is inherited from Node

    Parameters
    ----------
    name : string
        Name of the junction.
    base_demand : float, optional
        Base demand at the junction.
        Internal units must be cubic meters per second (m^3/s).
    demand_pattern_name : string, optional
        Name of the demand pattern.
    elevation : float, optional
        Elevation of the junction.
        Internal units must be meters (m).


    """

    def __init__(self, name, base_demand=0.0, demand_pattern_name=None, elevation=0.0):

        super(Junction, self).__init__(name)
        self.base_demand = base_demand
        self.prev_expected_demand = None
        self.expected_demand = base_demand
        self.demand_pattern_name = demand_pattern_name
        self._categorized_demands = {}  # _categorized_demands[category] = (base_demand, pattern_name)
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
        self._emitter_coefficient = None

    def __repr__(self):
        return "<Junction '{}'>".format(self._name)

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Junction, self).__eq__(other):
            return False
        if abs(self.base_demand - other.base_demand)<1e-10 and \
           self.demand_pattern_name == other.demand_pattern_name and \
           abs(self.elevation - other.elevation)<1e-10 and \
           abs(self.nominal_pressure - other.nominal_pressure)<1e-10 and \
           abs(self.minimum_pressure - other.minimum_pressure)<1e-10 and \
           self._emitter_coefficient == other._emitter_coefficient:
            return True
        return False

    def __hash__(self):
        return id(self)

    def add_leak(self, wn, area, discharge_coeff = 0.75, start_time=None, end_time=None):
        """
        Add a leak to a junction. Leaks are modeled by:

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
        Remove a leak from a junction.

        Parameters
        ----------
        wn: WaterNetworkModel object
        """
        self._leak = False
        wn._discard_control(self._leak_start_control_name)
        wn._discard_control(self._leak_end_control_name)

    def leak_present(self):
        """
        Check if the junction has a leak or not. Note that this
        does not check whether or not the leak is active (i.e., if the
        current time is between leak_start_time and leak_end_time).

        Returns
        -------
        bool: True if a leak is present, False if a leak is not present
        """
        return self._leak

    def set_leak_start_time(self, wn, t):
        """
        Set a start time for the leak. This internally creates a
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
        wn._discard_control(self._leak_start_control_name)

        # add new control
        start_control_action = wntr.network.ControlAction(self, 'leak_status', True)
        control = wntr.network.TimeControl(wn, t, 'SIM_TIME', False, start_control_action)
        wn.add_control(self._leak_start_control_name, control)

    def set_leak_end_time(self, wn, t):
        """
        Set an end time for the leak. This internally creates a
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
        wn._discard_control(self._leak_end_control_name)

        # add new control
        end_control_action = wntr.network.ControlAction(self, 'leak_status', False)
        control = wntr.network.TimeControl(wn, t, 'SIM_TIME', False, end_control_action)
        wn.add_control(self._leak_end_control_name, control)

    def discard_leak_controls(self, wn):
        """
        Specify that user-defined controls will be used to
        start and stop the leak. This will remove any controls set up
        through Junction.add_leak(), Junction.set_leak_start_time(),
        or Junction.set_leak_end_time().

        Parameters
        ----------
        wn: WaterNetworkModel object
        """
        wn._discard_control(self._leak_start_control_name)
        wn._discard_control(self._leak_end_control_name)

    def set_demand(self, base_demand, pattern_name=None):
        pass

    def add_categorized_demand(self, category, base_demand, pattern_name=None):
        pass

    def remove_categorized_demand(self, category):
        pass


class Tank(Node):
    """
    Tank class that is inherited from Node

    Parameters
    ----------
    name : string
        Name of the tank.
    elevation : float, optional
        Elevation at the Tank.
        Internal units must be meters (m).
    init_level : float, optional
        Initial tank level.
        Internal units must be meters (m).
    min_level : float, optional
        Minimum tank level.
        Internal units must be meters (m)
    max_level : float, optional
        Maximum tank level.
        Internal units must be meters (m)
    diameter : float, optional
        Tank diameter.
        Internal units must be meters (m)
    min_vol : float, optional
        Minimum tank volume.
        Internal units must be cubic meters (m^3)
    vol_curve : Curve object, optional
        Curve object
    """

    def __init__(self, name, elevation=0.0, init_level=3.048,
                 min_level=0.0, max_level=6.096, diameter=15.24,
                 min_vol=None, vol_curve=None):

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
        self._mix_model = None
        self._mix_frac = None
        self.leak_status = False
        self.leak_area = 0.0
        self.leak_discharge_coeff = 0.0
        self._leak_start_control_name = 'tank'+self._name+'start_leak_control'
        self._leak_end_control_name = 'tank'+self._name+'end_leak_control'
        self.bulk_rxn_coeff = None

    @property
    def level(self):
        return self.head - self.elevation

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Tank, self).__eq__(other):
            return False
        if abs(self.elevation   - other.elevation)<1e-10 and \
           abs(self.min_level   - other.min_level)<1e-10 and \
           abs(self.max_level   - other.max_level)<1e-10 and \
           abs(self.diameter    - other.diameter)<1e-10  and \
           abs(self.min_vol     - other.min_vol)<1e-10   and \
           self.bulk_rxn_coeff == other.bulk_rxn_coeff   and \
           self.vol_curve      == other.vol_curve:
            return True
        return False

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return "<Tank '{}'>".format(self._name)

    def add_leak(self, wn, area, discharge_coeff = 0.75, start_time=None, end_time=None):
        """
        Add a leak to a tank. Leaks are modeled by:

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
        Remove a leak from a tank.

        Parameters
        ----------
        wn: WaterNetworkModel object
        """
        self._leak = False
        wn._discard_control(self._leak_start_control_name)
        wn._discard_control(self._leak_end_control_name)

    def leak_present(self):
        """
        Check if the tank has a leak or not. Note that this
        does not check whether or not the leak is active (i.e., if the
        current time is between leak_start_time and leak_end_time).

        Returns
        -------
        bool: True if a leak is present, False if a leak is not present
        """
        return self._leak

    def set_leak_start_time(self, wn, t):
        """
        Set a start time for the leak. This internally creates a
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
        wn._discard_control(self._leak_start_control_name)

        # add new control
        start_control_action = wntr.network.ControlAction(self, 'leak_status', True)
        control = wntr.network.TimeControl(wn, t, 'SIM_TIME', False, start_control_action)
        wn.add_control(self._leak_start_control_name, control)

    def set_leak_end_time(self, wn, t):
        """
        Set an end time for the leak. This internally creates a
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
        wn._discard_control(self._leak_end_control_name)

        # add new control
        end_control_action = wntr.network.ControlAction(self, 'leak_status', False)
        control = wntr.network.TimeControl(wn, t, 'SIM_TIME', False, end_control_action)
        wn.add_control(self._leak_end_control_name, control)

    def use_external_leak_control(self, wn):
        """
        Specify that user-defined controls will be used to
        start and stop the leak. This will remove any controls set up
        through Tank.add_leak(), Tank.set_leak_start_time(),
        or Tank.set_leak_end_time().

        Parameters
        ----------
        wn: WaterNetworkModel object
        """
        wn._discard_control(self._leak_start_control_name)
        wn._discard_control(self._leak_end_control_name)

class Reservoir(Node):
    """
    Reservoir class that is inherited from Node

    Parameters
    ----------
    name : string
        Name of the reservoir.
    base_head : float, optional
        Base head at the reservoir.
        Internal units must be meters (m).
    head_pattern_name : string, optional
        Name of the head pattern.
    """
    def __init__(self, name, base_head=0.0, head_pattern_name=None):

        super(Reservoir, self).__init__(name)
        self.base_head = base_head
        self.head = base_head
        self.head_pattern_name = head_pattern_name

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Reservoir, self).__eq__(other):
            return False
        if abs(self.base_head - other.base_head)<1e-10 and \
           self.head_pattern_name == other.head_pattern_name:
            return True
        return True

    def __repr__(self):
        return "<Reservoir '{}'>".format(self._name)

    def __hash__(self):
        return id(self)

class Pipe(Link):
    """
    Pipe class that is inherited from Link

    Parameters
    ----------
    name : string
        Name of the pipe
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    length : float, optional
        Length of the pipe.
        Internal units must be meters (m)
    diameter : float, optional
        Diameter of the pipe.
        Internal units must be meters (m)
    roughness : float, optional
        Pipe roughness coefficient
    minor_loss : float, optional
        Pipe minor loss coefficient
    status : string, optional
        Pipe status. Options are 'Open' or 'Closed'
    check_valve_flag : bool, optional
        True if the pipe has a check valve
        False if the pipe does not have a check valve
    """

    def __init__(self, name, start_node_name, end_node_name, length=304.8,
                 diameter=0.3048, roughness=100, minor_loss=0.00, status='OPEN', check_valve_flag=False):

        super(Pipe, self).__init__(name, start_node_name, end_node_name)
        self.length = length
        self.diameter = diameter
        self.roughness = roughness
        self.minor_loss = minor_loss
        self.cv = check_valve_flag
        if status is not None:
            if isinstance(status, str):
                self.status = LinkStatus[status]
            else:
                self.status = status
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

    def __repr__(self):
        return "<Pipe '{}'>".format(self._link_name)

    def __hash__(self):
        return id(self)


class Pump(Link):
    """
    Pump class that is inherited from Link

    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    info_type : string, optional
        Type of information provided about the pump. Options are 'POWER' or 'HEAD'.
    info_value : float or curve type, optional
        Where power is a fixed value in KW, while a head curve is a Curve object.
    speed: float
        Relative speed setting (1.0 is normal speed)
    pattern: str
        ID of pattern for speed setting
    """

    def __init__(self, name, start_node_name, end_node_name, info_type='POWER',info_value=50.0,
                 speed=1.0, pattern=None):

        super(Pump, self).__init__(name, start_node_name, end_node_name)
        self._cv_status = LinkStatus.opened
        self.prev_speed = None
        self.speed = speed
        self.pattern = pattern
        self.curve = None
        self.efficiency = None
        self.energy_price = None
        self.energy_pattern = None
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

    def __repr__(self):
        return "<Pump '{}'>".format(self._link_name)

    @property
    def setting(self):
        """Alias to speed for consistency with other link types"""
        return self.speed

    @setting.setter
    def setting(self, value):
        self.speed = value

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Pump, self).__eq__(other):
            return False
        if self.info_type == other.info_type and \
           self.curve == other.curve:
            return True
        return False

    def __hash__(self):
        return id(self)

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
            raise RuntimeError('Value of pump head curve coefficient is negative, which is not allowed. \nPump: {0} \nA: {1} \nB: {2} \nC:{3}'.format(self.name,A,B,C))
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

    Parameters
    ----------
    name : string
        Name of the valve
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    diameter : float, optional
        Diameter of the valve.
        Internal units must be meters (m)
    valve_type : string, optional
        Type of valve. Options are 'PRV', etc
    minor_loss : float, optional
        Pipe minor loss coefficient
    setting : float or string, optional
        Valve setting or name of headloss curve for GPV
    """
    def __init__(self, name, start_node_name, end_node_name,
                 diameter=0.3048, valve_type='PRV', minor_loss=0.0, setting=0.0):

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

    def __repr__(self):
        return "<Valve: '{}', '{}'>".format(self._link_name, self.valve_type)

    def __hash__(self):
        return id(self)

class Curve(object):
    """
    Curve class.

    Parameters
    ----------
    name : string
         Name of the curve
    curve_type :
         Type of curve. Options are Volume, Pump, Efficiency, Headloss.
    points :
         List of tuples with X-Y points.
    """

    def __init__(self, name, curve_type, points):

        self.name = name
        self.curve_type = curve_type
        self.points = points
        self.points.sort()
        self.num_points = len(points)

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if self.name != other.name:
            return False
        if self.curve_type != other.curve_type:
            return False
        if self.num_points != other.num_points:
            return False
        for point1, point2 in zip(self.points, other.points):
            for value1, value2 in zip(point1, point2):
                if abs(value1 - value2) > 1e-8:
                    return False
        return True

    def __repr__(self):
        return '<Curve: {}, curve_type={}, points={}>'.format(repr(self.name), repr(self.curve_type), repr(self.points))

    def __hash__(self):
        return id(self)

class Source(object):
    """
    Source class.

    Parameters
    ----------
    name : string
         Name of the source

    node_name: string
        Injection node

    source_type: string
        Source type, options = CONCEN, MASS, FLOWPACED, or SETPOINT

    quality: float
        Source strength in Mass/Time for MASS and Mass/Volume for CONCEN, FLOWPACED, or SETPOINT

    pattern_name: string
        Pattern name

    """

    def __init__(self, name, node_name, source_type, quality, pattern_name):

        self.name = name
        self.node_name = node_name
        self.source_type = source_type
        self.quality = quality
        self.pattern_name = pattern_name

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self.node_name == other.node_name and \
           self.source_type == other.source_type and \
           abs(self.quality - other.quality)<1e-10 and \
           self.pattern_name == other.pattern_name:
            return True
        return False

    def __hash__(self):
        return id(self)

    def __repr__(self):
        fmt = "<Source: '{}', '{}', '{}', {}, {}>"
        return fmt.format(self.name, self.node_name, self.source_type, self.quality, repr(self.pattern_name))

class _Backdrop(object):
    """An epanet backdrop object."""
    def __init__(self, filename=None, dim=None, units=None, offset=None):
        self.dimensions = dim
        self.units = units
        self.filename = filename
        self.offset = offset

    def __str__(self):
        text = ""
        if self.dimensions is not None:
            text += "DIMENSIONS {} {} {} {}\n".format(self.dimensions[0],
                                                      self.dimensions[1],
                                                      self.dimensions[2],
                                                      self.dimensions[3])
        if self.units is not None:
            text += "UNITS {}\n".format(self.units)
        if self.filename is not None:
            text += "FILE {}\n".format(self.filename)
        if self.offset is not None:
            text += "OFFSET {} {}\n".format(self.offset[0], self.offset[1])
        return text


class Energy(object):
    """An epanet energy definitions object."""
    def __init__(self):
        self.global_price = 0
        """Global average cost per Joule (default 0)"""
        self.global_pattern = None
        """ID label of time pattern describing how energy price varies with time"""
        self.global_efficiency = 75.0
        """Global pump efficiency as percent; i.e., 75.0 means 75% (default 75%)"""
        self.demand_charge = None
        """Added cost per maximum kW usage during the simulation period"""

class _Demands(object):
    def __init__(self, name, junction_name=None, base_demand=None, demand_pattern_name=None):
        self.name = name
        self.junction_name = junction_name
        self.base_demand = base_demand
        self.demand_pattern_name = demand_pattern_name

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self.junction_name == other.junction_name and \
           abs(self.base_demand - other.base_demand)<1e-10 and \
           self.demand_pattern_name == other.demand_pattern_name:
            return True
        return False

class _Report(object):
    def __init__(self):
        self.pagesize = 0
        self.file = None
        self.status = 'NO'
        self.summary = 'YES'
        self.energy = 'NO'
        self.nodes = False
        self.links = False
        self.rpt_params = { # param name: [Default, Setting]
                           'elevation': [False, False],
                           'demand': [True, True],
                           'head': [True, True],
                           'pressure': [True, True],
                           'quality': [True, True],
                           'length': [False, False],
                           'diameter': [False, False],
                           'flow': [True, True],
                           'velocity': [True, True],
                           'headloss': [True, True],
                           'position': [False, False],
                           'setting': [False, False],
                           'reaction': [False, False],
                           'f-factor': [False, False],
                           }
        self.param_opts = { # param name: [Default, Setting]
                           'elevation': {},
                           'demand': {},
                           'head': {},
                           'pressure': {},
                           'quality': {},
                           'length': {},
                           'diameter': {},
                           'flow': {},
                           'velocity': {},
                           'headloss': {},
                           'position': {},
                           'setting': {},
                           'reaction': {},
                           'f-factor': {},
                           }