"""
The wntr.network.model module includes methods to build a water network
model.
"""
import logging
import six

import sys
if sys.version_info[0] == 2:
    from collections import MutableSequence
else:
    from collections.abc import MutableSequence

import numpy as np
import networkx as nx

from .options import WaterNetworkOptions
from .base import Link, Registry, LinkStatus, AbstractModel
from .elements import Junction, Reservoir, Tank
from .elements import Pipe, Pump, HeadPump, PowerPump
from .elements import Valve, PRValve, PSValve, PBValve, TCValve, FCValve, GPValve
from .elements import Pattern, TimeSeries, Demands, Curve, Source
from .graph import WntrMultiDiGraph
from .controls import ControlPriority, _ControlType, TimeOfDayCondition, SimTimeCondition, ValueCondition, \
    TankLevelCondition, RelativeCondition, OrCondition, AndCondition, _CloseCVCondition, _OpenCVCondition, \
    _ClosePowerPumpCondition, _OpenPowerPumpCondition, _CloseHeadPumpCondition, _OpenHeadPumpCondition, \
    _ClosePRVCondition, _OpenPRVCondition, _ActivePRVCondition, _OpenFCVCondition, _ActiveFCVCondition, \
    _ValveNewSettingCondition, ControlAction, _InternalControlAction, Control, ControlManager, Comparison
from collections import OrderedDict
from wntr.utils.ordered_set import OrderedSet

import wntr.epanet

logger = logging.getLogger(__name__)


class WaterNetworkModel(AbstractModel):
    """
    Water network model class.

    Parameters
    -------------------
    inp_file_name: string (optional)
        Directory and filename of EPANET inp file to load into the
        WaterNetworkModel object.
    """

    def __init__(self, inp_file_name=None):

        # Network name
        self.name = None

        self._options = WaterNetworkOptions()
        self._node_reg = NodeRegistry(self)
        self._link_reg = LinkRegistry(self)
        self._pattern_reg = PatternRegistry(self)
        self._curve_reg = CurveRegistry(self)
        self._controls = OrderedDict()
        self._sources = {}

        # Name of pipes that are check valves
        self._check_valves = []

        # NetworkX Graph to store the pipe connectivity and node coordinates

        self._Htol = 0.00015  # Head tolerance in meters.
        self._Qtol = 2.8e-5  # Flow tolerance in m^3/s.

        self._labels = None

        self._inpfile = None
        if inp_file_name:
            self.read_inpfile(inp_file_name)
            
        # To be deleted and/or renamed and/or moved
        # Time parameters
        self.sim_time = 0.0
        self._prev_sim_time = None  # the last time at which results were accepted
    
    def _compare(self, other):
        if self.num_junctions  != other.num_junctions  or \
           self.num_reservoirs != other.num_reservoirs or \
           self.num_tanks      != other.num_tanks      or \
           self.num_pipes      != other.num_pipes      or \
           self.num_pumps      != other.num_pumps      or \
           self.num_valves     != other.num_valves:
            return False
        for name, node in self.nodes():
            if not node._compare(other.get_node(name)):
                return False
        for name, link in self.links():
            if not link._compare(other.get_link(name)):
                return False
        for name, pat in self.patterns():
            if pat != other.get_pattern(name):
                return False
        for name, curve in self.curves():
            if curve != other.get_curve(name):
                return False
        for name, source in self.sources():
            if source != other.get_source(name):
                return False
        return True
    
    def _sec_to_string(self, sec):
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        return (hours, mm, int(sec))
    
    @property
    def _shifted_time(self):
        """
        Return the time in seconds shifted by the
        simulation start time (e.g. as specified in the
        inp file). This is, this is the time since 12 AM
        on the first day.
        """
        return self.sim_time + self.options.time.start_clocktime

    @property
    def _prev_shifted_time(self):
        """
        Return the time in seconds of the previous solve shifted by
        the simulation start time. That is, this is the time from 12
        AM on the first day to the time at the prevous hydraulic
        timestep.
        """
        return self._prev_sim_time + self.options.time.start_clocktime

    @property
    def _clock_time(self):
        """
        Return the current time of day in seconds from 12 AM
        """
        return self.shifted_time % (24*3600)

    @property
    def _clock_day(self):
        return int(self.shifted_time / 86400)

    ### # 
    ### Iteratable attributes
    @property
    def options(self): return self._options
    
    @property
    def nodes(self): return self._node_reg
    
    @property
    def links(self): return self._link_reg
    
    @property
    def patterns(self): return self._pattern_reg
    
    @property
    def curves(self): return self._curve_reg
    
    def sources(self):
        """
        Returns a generator to iterate over all sources.

        Returns
        -------
        A generator in the format (name, object).
        """
        for source_name, source in self._sources.items():
            yield source_name, source
        
    def controls(self):
        """
        Returns a generator to iterate over all controls.

        Returns
        -------
        A generator in the format (name, object).
        """
        for control_name, control in self._controls.items():
            yield control_name, control
                
    ### # 
    ### Element iterators
    @property
    def junctions(self): return self._node_reg.junctions
    
    @property
    def tanks(self): return self._node_reg.tanks
    
    @property
    def reservoirs(self): return self._node_reg.reservoirs
    
    @property
    def pipes(self): return self._link_reg.pipes
    
    @property
    def pumps(self): return self._link_reg.pumps
    
    @property
    def valves(self): return self._link_reg.valves

    @property
    def head_pumps(self):
        return self._link_reg.head_pumps

    @property
    def power_pumps(self):
        return self._link_reg.power_pumps

    @property
    def prvs(self):
        return self._link_reg.prvs

    @property
    def psvs(self):
        return self._link_reg.psvs

    @property
    def pbvs(self):
        return self._link_reg.pbvs

    @property
    def tcvs(self):
        return self._link_reg.tcvs

    @property
    def fcvs(self):
        return self._link_reg.fcvs

    @property
    def gpvs(self):
        return self._link_reg.gpvs
    
    """
    ### # 
    ### Create blank, unregistered objects (for direct assignment)
    def new_demand_timeseries_list(self):
        return Demands(self) 
    
    def new_timeseries(self):
        return TimeSeries(self, 0.0)
    
    def new_pattern(self):
        return Pattern(None, time_options=self._options.time)
    """
    
    ### # 
    ### Add elements to the model
    def add_junction(self, name, base_demand=0.0, demand_pattern=None, 
                     elevation=0.0, coordinates=None, demand_category=None):
        """
        Adds a junction to the water network model.

        Parameters
        -------------------
        name : string
            Name of the junction.
        base_demand : float
            Base demand at the junction.
        demand_pattern : string or Pattern
            Name of the demand pattern or the actual Pattern object
        elevation : float
            Elevation of the junction.
        coordinates : tuple of floats
            X-Y coordinates of the node location.
        demand_category  : string
            Name of the demand category
        """
        self._node_reg.add_junction(name, base_demand, demand_pattern, 
                                    elevation, coordinates, demand_category)

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
        vol_curve : str
            Name of a volume curve (optional)
        coordinates : tuple of floats
            X-Y coordinates of the node location.
            
        Raises
        ------
        ValueError
            If `init_level` greater than `max_level` or less than `min_level`
            
        """
        self._node_reg.add_tank(name, elevation, init_level, min_level, 
                                max_level, diameter, min_vol, vol_curve, 
                                coordinates)

    def add_reservoir(self, name, base_head=0.0, head_pattern=None, coordinates=None):
        """
        Adds a reservoir to the water network model.

        Parameters
        ----------
        name : string
            Name of the reservoir.
        base_head : float, optional
            Base head at the reservoir.
        head_pattern : string
            Name of the head pattern (optional)
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        
        """
        self._node_reg.add_reservoir(name, base_head, head_pattern, coordinates)

    def add_pipe(self, name, start_node_name, end_node_name, length=304.8,
                 diameter=0.3048, roughness=100, minor_loss=0.0, status='OPEN', 
                 check_valve_flag=False):
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
        self._link_reg.add_pipe(name, start_node_name, end_node_name, length, 
                                diameter, roughness, minor_loss, status, 
                                check_valve_flag)
        if check_valve_flag:
            self._check_valves.append(name)


    def add_pump(self, name, start_node_name, end_node_name, pump_type='POWER',
                 pump_parameter=50.0, speed=1.0, pattern=None):
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
        pump_type : string, optional
            Type of information provided for a pump. Options are 'POWER' or 'HEAD'.
        pump_parameter : float or str object
            Float value of power in KW. Head curve name.
        speed: float
            Relative speed setting (1.0 is normal speed)
        pattern: str
            ID of pattern for speed setting
        
        """
        self._link_reg.add_pump(name, start_node_name, end_node_name, pump_type, 
                                pump_parameter, speed, pattern)
    
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
        self._link_reg.add_valve(name, start_node_name, end_node_name, diameter, 
                                 valve_type, minor_loss, setting)

    def add_pattern(self, name, pattern=None):
        """
        Adds a pattern to the water network model.
        
        The pattern can be either a list of values (list, numpy array, etc.) or a 
        :class:`~wntr.network.elements.Pattern` object. The Pattern class has options to automatically
        create certain types of patterns, such as a single, on/off pattern (previously created using
        the start_time and stop_time arguments to this function) -- see the class documentation for
        examples.

        
        .. warning::
            Patterns **must** be added to the model prior to adding any model element that uses the pattern,
            such as junction demands, sources, etc. Patterns are linked by reference, so changes to a 
            pattern affects all elements using that pattern. 

            
        .. warning::
            Patterns **always** use the global water network model options.time values.
            Patterns **will not** be resampled to match these values, it is assumed that 
            patterns created using Pattern(...) or Pattern.binary_pattern(...) object used the same 
            pattern timestep value as the global value, and they will be treated accordingly.


        Parameters
        ----------
        name : string
            Name of the pattern.
        pattern : list of floats or Pattern
            A list of floats that make up the pattern, or a :class:`~wntr.network.elements.Pattern` object.

        Raises
        ------
        ValueError
            If adding a pattern with `name` that already exists.

        
        """
        self._pattern_reg.add_pattern(name, pattern)
            
    def add_curve(self, name, curve_type, xy_tuples_list):
        """
        Adds a curve to the water network model.

        Parameters
        ----------
        name : string
            Name of the curve.
        curve_type : string
            Type of curve. Options are HEAD, EFFICIENCY, VOLUME, HEADLOSS.
        xy_tuples_list : list of (x, y) tuples
            List of X-Y coordinate tuples on the curve.
        """
        self._curve_reg.add_curve(name, curve_type, xy_tuples_list)
        
    def add_source(self, name, node_name, source_type, quality, pattern=None):
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
            Source strength in Mass/Time for MASS and Mass/Volume for CONCEN, 
            FLOWPACED, or SETPOINT

        pattern: string or Pattern object
            Pattern name or object
        """
        if pattern and isinstance(pattern, six.string_types):
            pattern = self.get_pattern(pattern)
        source = Source(self, name, node_name, source_type, quality, pattern)
        self._sources[source.name] = source

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
        if name in self._controls:
            raise ValueError('The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control.')
        self._controls[name] = control_object
    
    
    ### # 
    ### Remove elements from the model
    def remove_node(self, name, with_control=False):
        """"""
        node = self.get_node(name)
        if with_control:
            x=[]
            for control_name, control in self._controls.items():
                if node in control.requires():
                    logger.warning('Control '+control_name+' is being removed along with node '+name)
                    x.append(control_name)
            for i in x:
                self.remove_control(i)
        else:
            for control_name, control in self._controls.items():
                if node in control.requires():
                    raise RuntimeError('Cannot remove node {0} without first removing control {1}'.format(name, control_name))
        self._node_reg.__delitem__(name)

    def remove_link(self, name, with_control=False):
        """"""
        link = self.get_link(name)
        if with_control:
            x=[]
            for control_name, control in self._controls.items():
                if link in control.requires():
                    logger.warning('Control '+control_name+' is being removed along with link '+name)
                    x.append(control_name)
            for i in x:
                self.remove_control(i)
        else:
            for control_name, control in self._controls.items():
                if link in control.requires():
                    raise RuntimeError('Cannot remove link {0} without first removing control {1}'.format(name, control_name))
        self._link_reg.__delitem__(name)

    def remove_pattern(self, name): 
        """
        Removes a pattern from the water network model.
        """
        self._pattern_reg.__delitem__(name)
        
    def remove_curve(self, name): 
        """
        Removes a curve from the water network model.
        """
        self._curve_reg.__delitem__(name)
        
    def remove_source(self, name):
        """
        Removes a source from the water network model.

        Parameters
        ----------
        name : string
           The name of the source object to be removed.
        """
        logger.warning('You are deleting a source. This could have unintended \
            side effects. If you are replacing values, use get_source(name) \
            and modify it instead.')
        source = self._sources[name]
        self._pattern_reg.remove_usage(source.strength_timeseries.pattern_name, (source.name, 'Source'))
        self._node_reg.remove_usage(source.node_name, (source.name, 'Source'))            
        del self._sources[name]
        
    def remove_control(self, name): 
        """"""
        del self._controls[name]

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
            del self._controls[name]
            self._num_controls -= 1
        except KeyError:
            pass
    
    ### # 
    ### Get elements from the model
    def get_node(self, name): 
        """"""
        return self._node_reg[name]
    
    def get_link(self, name): 
        """"""
        return self._link_reg[name]
    
    def get_pattern(self, name): 
        """"""
        return self._pattern_reg[name]
    
    def get_curve(self, name): 
        """"""
        return self._curve_reg[name]
    
    def get_source(self, name):
        """"""
        return self._sources[name]
    
    def get_control(self, name): 
        """"""
        return self._controls[name]
    
    ### # 
    ### Get controls from the model (move?)
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
                elif isinstance(link, Pump):
                    if link.end_node == tank_name:
                        continue
                    else:
                        link_has_cv = True

                close_control_action = _InternalControlAction(link, '_internal_status', LinkStatus.Closed, 'status')
                open_control_action = _InternalControlAction(link, '_internal_status', LinkStatus.Open, 'status')

                close_condition = ValueCondition(tank, 'head', Comparison.le, min_head)
                close_control_1 = Control(close_condition, [close_control_action], [], ControlPriority.medium)
                close_control_1._control_type = _ControlType.pre_and_postsolve
                tank_controls.append(close_control_1)

                if not link_has_cv:
                    open_condition_1 = ValueCondition(tank, 'head', Comparison.ge, min_head+self._Htol)
                    open_control_1 = Control(open_condition_1, [open_control_action], [], ControlPriority.low)
                    open_control_1._control_type = _ControlType.postsolve
                    tank_controls.append(open_control_1)

                    if link.start_node is tank:
                        other_node = link.end_node
                    elif link.end_node is tank:
                        other_node = link.start_node
                    else:
                        raise RuntimeError('Tank is neither the start node nore the end node.')
                    open_condition_2a = RelativeCondition(tank, 'head', Comparison.le, other_node, 'head')
                    open_condition_2b = ValueCondition(tank, 'head', Comparison.le, min_head+self._Htol)
                    open_condition_2 = AndCondition(open_condition_2a, open_condition_2b)
                    open_control_2 = Control(open_condition_2, [open_control_action], [], ControlPriority.high)
                    open_control_2._control_type = _ControlType.postsolve
                    tank_controls.append(open_control_2)

            # Now take care of the max level
            max_head = tank.max_level+tank.elevation
            for link_name in all_links:
                link = self.get_link(link_name)
                link_has_cv = False
                if isinstance(link, Pipe):
                    if link.cv:
                        if link.start_node == tank_name:
                            continue
                        else:
                            link_has_cv = True
                if isinstance(link, Pump):
                    if link.start_node == tank_name:
                        continue
                    else:
                        link_has_cv = True

                close_control_action = _InternalControlAction(link, '_internal_status', LinkStatus.Closed, 'status')
                open_control_action = _InternalControlAction(link, '_internal_status', LinkStatus.Open, 'status')

                close_condition = ValueCondition(tank, 'head', Comparison.ge, max_head)
                close_control = Control(close_condition, [close_control_action], [], ControlPriority.medium)
                close_control._control_type = _ControlType.pre_and_postsolve
                tank_controls.append(close_control)

                if not link_has_cv:
                    open_condition_1 = ValueCondition(tank, 'head', Comparison.le, max_head - self._Htol)
                    open_control_1 = Control(open_condition_1, [open_control_action], [], ControlPriority.low)
                    open_control_1._control_type = _ControlType.postsolve
                    tank_controls.append(open_control_1)

                    if link.start_node is tank:
                        other_node = link.end_node
                    elif link.end_node is tank:
                        other_node = link.start_node
                    else:
                        raise RuntimeError('Tank is neither the start node nore the end node.')
                    open_condition_2a = RelativeCondition(tank, 'head', Comparison.ge, other_node, 'head')
                    open_condition_2b = ValueCondition(tank, 'head', Comparison.ge, max_head-self._Htol)
                    open_condition_2 = AndCondition(open_condition_2a, open_condition_2b)
                    open_control_2 = Control(open_condition_2, [open_control_action], [], ControlPriority.high)
                    open_control_2._control_type = _ControlType.postsolve
                    tank_controls.append(open_control_2)

        return tank_controls

    def _get_cv_controls(self):
        cv_controls = []
        for pipe_name in self._check_valves:
            pipe = self.get_link(pipe_name)
            open_condition = _OpenCVCondition(self, pipe)
            close_condition = _CloseCVCondition(self, pipe)
            open_action = _InternalControlAction(pipe, '_internal_status', LinkStatus.Open, 'status')
            close_action = _InternalControlAction(pipe, '_internal_status', LinkStatus.Closed, 'status')
            open_control = Control(open_condition, [open_action], [], ControlPriority.very_low)
            close_control = Control(close_condition, [close_action], [], ControlPriority.very_high)
            open_control._control_type = _ControlType.postsolve
            close_control._control_type = _ControlType.postsolve
            cv_controls.append(open_control)
            cv_controls.append(close_control)

        return cv_controls
    
    def _get_pump_controls(self):
        pump_controls = []
        for pump_name, pump in self.pumps():
            close_control_action = _InternalControlAction(pump, '_internal_status', LinkStatus.Closed, 'status')
            open_control_action = _InternalControlAction(pump, '_internal_status', LinkStatus.Open, 'status')

            if pump.pump_type == 'HEAD':
                close_condition = _CloseHeadPumpCondition(self, pump)
                open_condition = _OpenHeadPumpCondition(self, pump)
            elif pump.pump_type == 'POWER':
                close_condition = _ClosePowerPumpCondition(self, pump)
                open_condition = _OpenPowerPumpCondition(self, pump)
            else:
                raise ValueError('Unrecognized pump pump_type: {0}'.format(pump.pump_type))

            close_control = Control(close_condition, [close_control_action], [], ControlPriority.very_high)
            open_control = Control(open_condition, [open_control_action], [], ControlPriority.very_low)

            close_control._control_type = _ControlType.postsolve
            open_control._control_type = _ControlType.postsolve

            pump_controls.append(close_control)
            pump_controls.append(open_control)

        return pump_controls

    def _get_valve_controls(self):
        valve_controls = []
        for valve_name, valve in self.valves():

            new_setting_action = ControlAction(valve, 'status', LinkStatus.Active)
            new_setting_condition = _ValveNewSettingCondition(valve)
            new_setting_control = Control(new_setting_condition, [new_setting_action], [], ControlPriority.very_low)
            new_setting_control._control_type = _ControlType.postsolve
            valve_controls.append(new_setting_control)

            if valve.valve_type == 'PRV':
                close_condition = _ClosePRVCondition(valve)
                open_condition = _OpenPRVCondition(self, valve)
                active_condition = _ActivePRVCondition(self, valve)
                close_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Closed, 'status')
                open_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Open, 'status')
                active_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Active, 'status')
                close_control = Control(close_condition, [close_action], [], ControlPriority.very_high)
                open_control = Control(open_condition, [open_action], [], ControlPriority.very_low)
                active_control = Control(active_condition, [active_action], [], ControlPriority.very_low)
                close_control._control_type = _ControlType.postsolve
                open_control._control_type = _ControlType.postsolve
                active_control._control_type = _ControlType.postsolve
                valve_controls.append(close_control)
                valve_controls.append(open_control)
                valve_controls.append(active_control)
            elif valve.valve_type == 'FCV':
                open_condition = _OpenFCVCondition(self, valve)
                active_condition = _ActiveFCVCondition(self, valve)
                open_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Open, 'status')
                active_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Active, 'status')
                open_control = Control(open_condition, [open_action], [], ControlPriority.very_low)
                active_control = Control(active_condition, [active_action], [], ControlPriority.very_low)
                open_control._control_type = _ControlType.postsolve
                active_control._control_type = _ControlType.postsolve
                valve_controls.append(open_control)
                valve_controls.append(active_control)

        return valve_controls
    
    ### #
    ### Name lists
    @property
    def node_name_list(self): 
        """"""
        return list(self._node_reg.keys())

    @property
    def junction_name_list(self): 
        """"""
        return list(self._node_reg.junction_names)

    @property
    def tank_name_list(self): 
        """"""
        return list(self._node_reg.tank_names)

    @property
    def reservoir_name_list(self): 
        """"""
        return list(self._node_reg.reservoir_names)

    @property
    def link_name_list(self): 
        """"""
        return list(self._link_reg.keys())

    @property
    def pipe_name_list(self): 
        """"""
        return list(self._link_reg.pipe_names)

    @property
    def pump_name_list(self): 
        """"""
        return list(self._link_reg.pump_names)

    @property
    def valve_name_list(self): 
        """"""
        return list(self._link_reg.valve_names)

    @property
    def pattern_name_list(self): 
        """"""
        return list(self._pattern_reg.keys())

    @property
    def curve_name_list(self): 
        """"""
        return list(self._curve_reg.keys())

    @property
    def source_name_list(self): 
        """"""
        return list(self._sources.keys())

    @property
    def control_name_list(self): 
        """"""
        return list(self._controls.keys())
    
    ### # 
    ### Counts
    @property
    def num_nodes(self): 
        """"""
        return len(self._node_reg)
    
    @property
    def num_junctions(self): 
        """"""
        return len(self._node_reg.junction_names)
    
    @property
    def num_tanks(self): 
        """"""
        return len(self._node_reg.tank_names)
    
    @property
    def num_reservoirs(self): 
        """"""
        return len(self._node_reg.reservoir_names)
    
    @property
    def num_links(self): 
        """"""
        return len(self._link_reg)
    
    @property
    def num_pipes(self): 
        """"""
        return len(self._link_reg.pipe_names)
    
    @property
    def num_pumps(self): 
        """"""
        return len(self._link_reg.pump_names)
    
    @property
    def num_valves(self): 
        """"""
        return len(self._link_reg.valve_names)
    
    @property
    def num_patterns(self): 
        """"""
        return len(self._pattern_reg)
    
    @property
    def num_curves(self): 
        """"""
        return len(self._curve_reg)
    
    @property
    def num_sources(self): 
        """"""
        return len(self._sources)
    
    @property
    def num_controls(self): 
        """"""
        return len(self._control_reg)
    
    ### #
    ### Helper functions
    def todict(self):
        d = dict(options=self._options.todict(),
                 nodes=self._node_reg.tolist(),
                 links=self._link_reg.tolist(),
                 curves=self._curve_reg.tolist(),
                 controls=self._control_reg.todict(),
                 patterns=self._pattern_reg.tolist()
                 )
        return d
    
    def get_graph(self):
        """
        Returns a networkx graph of the water network model

        Returns
        --------
        WaterNetworkModel networkx graph.
        """
        graph = WntrMultiDiGraph()
        
        for name, node in self.nodes():
            graph.add_node(name)
            nx.set_node_attributes(graph, name='pos', values={name: node.coordinates})
            nx.set_node_attributes(graph, name='type', values={name:node.node_type})
        
        for name, link in self.links():
            start_node = link.start_node_name
            end_node = link.end_node_name
            graph.add_edge(start_node, end_node, key=name)
            nx.set_edge_attributes(graph, name='type', 
                        values={(start_node, end_node, name):link.link_type})
        
        return graph
    
    def assign_demand(self, demand, pattern_prefix='ResetDemand'):
        """
        Assign demands using values in a DataFrame. 
        
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
            A pandas DataFrame containing demands (index = time, columns = node names)

        pattern_prefix: string
            Pattern prefix, default = 'ResetDemand'
        """
        for node_name, node in self.nodes():
            
            # Extact the node demand pattern and resample to match the pattern timestep
            demand_pattern = demand.loc[:, node_name]
            demand_pattern.index = demand_pattern.index.astype('timedelta64[s]')
            resample_offset = str(int(self.options.time.pattern_timestep))+'S'
            demand_pattern = demand_pattern.resample(resample_offset).mean()

            # Add the pattern
            pattern_name = pattern_prefix + node_name
            self.add_pattern(pattern_name, demand_pattern.tolist())
            pattern = self.get_pattern(pattern_name)

            # Reset base demand
            if hasattr(node, 'demands'):
                node.demands.clear()
                node.demands.append((1.0, pattern, 'PDD'))

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
        link_types = {'Pipe', 'Pump', 'Valve'}
        if flag.upper() == 'ALL':
            return [link_name for link_name, link_type in self._node_reg.get_usage(node_name) if link_type in link_types and node_name in {self.get_link(link_name).start_node_name, self.get_link(link_name).end_node_name}]
        elif flag.upper() == 'INLET':
            return [link_name for link_name, link_type in self._node_reg.get_usage(node_name) if link_type in link_types and node_name == self.get_link(link_name).end_node_name]
        elif flag.upper() == 'OUTLET':
            return [link_name for link_name, link_type in self._node_reg.get_usage(node_name) if link_type in link_types and node_name == self.get_link(link_name).start_node_name]
        else:
            logger.error('Unrecognized flag: {0}'.format(flag))
            raise ValueError('Unrecognized flag: {0}'.format(flag))

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
        node_attribute_dict = OrderedDict()
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

    def reset_initial_values(self):
        """
        Resets all initial values in the network.
        """
        self.sim_time = 0.0
        self._prev_sim_time = None

        for name, node in self.nodes(Junction):
            node.head = None
            node.demand = None
            node.leak_demand = None
            node.leak_status = False

        for name, node in self.nodes(Tank):
            node.head = node.init_level+node.elevation
            node.demand = None
            node.leak_demand = None
            node.leak_status = False

        for name, node in self.nodes(Reservoir):
            node.head = node.head_timeseries.base_value
            node.demand = None
            node.leak_demand = None

        for name, link in self.links(Pipe):
            link.status = link.initial_status
            link._flow = None

        for name, link in self.links(Pump):
            link.status = link.initial_status
            link._flow = None
            link.power = link._base_power
            link._power_outage = LinkStatus.Open

        for name, link in self.links(Valve):
            link.status = link.initial_status
            link._flow = None
            link.setting = link.initial_setting
            link._prev_setting = None

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
    
    ### #
    ### Move to morph
    def scale_node_coordinates(self, scale):
        """
        Scales node coordinates, using 1:scale.  Scale should be in meters.
        Parameters
        -----------
        scale : float
            Coordinate scale multiplier.
        """
        for name, node in self.nodes():
            pos = node.coordinates
            node.coordinates = (pos[0]*scale, pos[1]*scale)
            
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
            
        Raises
        ------
        ValueError
            The link is not a pipe, `split_at_point` is out of bounds, `add_pipe_at_node` is invalid.
        RuntimeError
            The `new_junction_name` or `new_pipe_name` is already in use.
            
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
        start_node = pipe.start_node
        end_node = pipe.end_node
        
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
        x0 = pipe.start_node.coordinates[0]
        dx = pipe.end_node.coordinates[0] - x0
        y0 = pipe.start_node.coordinates[1]
        dy = pipe.end_node.coordinates[1] - y0
        junction_coordinates = (x0 + dx * split_at_point,
                                y0 + dy * split_at_point)

        # add the new junction
        self.add_junction(new_junction_name, base_demand=0.0, demand_pattern=None,
                          elevation=junction_elevation, coordinates=junction_coordinates)
        new_junction = self.get_node(new_junction_name)

        # remove the original pipe from the graph (to be added back below)
        #self._graph.remove_edge(pipe.start_node, pipe.end_node, key=pipe_name_to_split)
        original_length = pipe.length

        if add_pipe_at_node.lower() == 'start':
            # add original pipe back to graph between new junction and original end
            pipe.start_node = new_junction_name
            # add new pipe and change original length
            self.add_pipe(new_pipe_name, start_node.name, new_junction_name,
                          original_length*split_at_point, pipe.diameter, pipe.roughness,
                          pipe.minor_loss, pipe.status, pipe.cv)
            pipe.length = original_length * (1-split_at_point)

        elif add_pipe_at_node.lower() == 'end':
            # add original pipe back to graph between original start and new junction
            pipe.end_node = new_junction_name      
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
        x0 = pipe.start_node.coordinates[0]
        dx = pipe.end_node.coordinates[0] - x0
        y0 = pipe.start_node.coordinates[1]
        dy = pipe.end_node.coordinates[1] - y0
        junction_coordinates = (x0 + dx * split_at_point,
                                y0 + dy * split_at_point)

        # add the new junction
        self.add_junction(new_junction_name_old_pipe, base_demand=0.0, demand_pattern=None,
                          elevation=junction_elevation, coordinates=junction_coordinates)
        new_junction1 = self.get_node(new_junction_name_old_pipe)
        self.add_junction(new_junction_name_new_pipe, base_demand=0.0, demand_pattern=None,
                          elevation=junction_elevation, coordinates=junction_coordinates)
        new_junction2 = self.get_node(new_junction_name_new_pipe)

        # remove the original pipe from the graph (to be added back below)
        self._graph.remove_edge(pipe.start_node, pipe.end_node, key=pipe_name_to_split)
        original_length = pipe.length

        if add_pipe_at_node.lower() == 'start':
            # add original pipe back to graph between new junction and original end
            pipe.start_node_name = new_junction_name_old_pipe
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
            pipe.end_node_name = new_junction_name_old_pipe            
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


class PatternRegistry(Registry):

    @property
    def _patterns(self):
        raise UnboundLocalError('registries are not reentrant')

    class DefaultPattern(object):
        def __init__(self, options):
            self._options = options
        
        def __str__(self):
            return str(self._options.hydraulic.pattern) if self._options.hydraulic.pattern is not None else ''
        
        def __repr__(self):
            return 'DefaultPattern()'
        
        @property
        def name(self):
            return str(self._options.hydraulic.pattern) if self._options.hydraulic.pattern is not None else ''

    def __getitem__(self, key):
        try:
            return super(PatternRegistry, self).__getitem__(key)
        except KeyError:
            return None

    def add_pattern(self, name, pattern=None):
        """
        Adds a pattern to the water network model.
        
        The pattern can be either a list of values (list, numpy array, etc.) or 
        a :class:`~wntr.network.elements.Pattern` object. The Pattern class has 
        options to automatically create certain types of patterns, such as a 
        single, on/off pattern

        .. warning::
            Patterns **must** be added to the model prior to adding any model 
            element that uses the pattern, such as junction demands, sources, 
            etc. Patterns are linked by reference, so changes to a pattern 
            affects all elements using that pattern. 

        .. warning::
            Patterns **always** use the global water network model options.time 
            values. Patterns **will not** be resampled to match these values, 
            it is assumed that patterns created using Pattern(...) or 
            Pattern.binary_pattern(...) object used the same pattern timestep 
            value as the global value, and they will be treated accordingly.

        Parameters
        ----------
        name : string
            Name of the pattern.
        pattern : list of floats or Pattern
            A list of floats that make up the pattern, or a 
            :class:`~wntr.network.elements.Pattern` object.

        Raises
        ------
        ValueError
            If adding a pattern with `name` that already exists.
        """
        if not isinstance(pattern, Pattern):
            pattern = Pattern(name, multipliers=pattern, time_options=self._options.time)            
        else: #elif pattern.time_options is None:
            pattern.time_options = self._options.time
        if pattern.name in self._data.keys():
            raise ValueError('Pattern name already exists')
        self[name] = pattern
    
    @property
    def default_pattern(self):
        return self.DefaultPattern(self._m.options)
    
    def tostring(self):
        s  = 'Pattern Registry:\n'
        s += '  Total number of patterns defined:  {}\n'.format(len(self._data))
        s += '  Patterns used in the network:      {}\n'.format(len(self._usage))
        if len(self.orphaned()) > 0:
            s += '  Patterns used without definitions: {}\n'.format(len(self.orphaned()))
            for orphan in self.orphaned():
                s += '   - {}: {}\n'.format(orphan, self._usage[orphan])
        return s
        

class CurveRegistry(Registry):
    def __init__(self, model):
        super(CurveRegistry, self).__init__(model)
        self._pump_curves = OrderedSet()
        self._efficiency_curves = OrderedSet()
        self._headloss_curves = OrderedSet()
        self._volume_curves = OrderedSet()

    @property
    def _curves(self):
        raise UnboundLocalError('registries are not reentrant')

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise ValueError('Registry keys must be strings')
        self._data[key] = value
        self.set_curve_type(key, value.curve_type)
    
    def set_curve_type(self, key, curve_type):
        """WARNING -- does not check to make sure key is typed before assining it - you could end up
        with a curve that is used for more than one type, which would be really weird"""
        if curve_type is None:
            return
        curve_type = curve_type.upper()
        if curve_type == 'HEAD':
            self._pump_curves.add(key)
        elif curve_type == 'HEADLOSS':
            self._headloss_curves.add(key)
        elif curve_type == 'VOLUME':
            self._volume_curves.add(key)
        elif curve_type == 'EFFICIENCY':
            self._efficiency_curves.add(key)
        else:
            raise ValueError('curve_type must be HEAD, HEADLOSS, VOLUME, or EFFICIENCY')
        
    def add_curve(self, name, curve_type, xy_tuples_list):
        """
        Adds a curve to the water network model.

        Parameters
        ----------
        name : string
            Name of the curve.
        curve_type : string
            Type of curve. Options are HEAD, EFFICIENCY, VOLUME, HEADLOSS.
        xy_tuples_list : list of (x, y) tuples
            List of X-Y coordinate tuples on the curve.
        """
        curve = Curve(name, curve_type, xy_tuples_list)
        self[name] = curve
        
    def untyped_curves(self):
        defined = set(self._data.keys())
        untyped = defined.difference(self._pump_curves, self._efficiency_curves, 
                                     self._headloss_curves, self._volume_curves)
        for key in untyped:
            yield key, self._data[key]

    @property    
    def untyped_curve_names(self):
        defined = set(self._data.keys())
        untyped = defined.difference(self._pump_curves, self._efficiency_curves, 
                                     self._headloss_curves, self._volume_curves)
        return list(untyped)

    def pump_curves(self):
        for key in self._pump_curves:
            yield key, self._data[key]
    
    @property
    def pump_curve_names(self):
        return list(self._pump_curves)

    def efficiency_curves(self):
        for key in self._efficiency_curves:
            yield key, self._data[key]

    @property
    def efficiency_curve_names(self):
        return list(self._efficiency_curves)

    def headloss_curves(self):
        for key in self._headloss_curves:
            yield key, self._data[key]

    @property
    def headloss_curve_names(self):
        return list(self._headloss_curves)

    def volume_curves(self):
        for key in self._volume_curves:
            yield key, self._data[key]
    
    @property
    def volume_curve_names(self):
        return list(self._volume_curves)

    def tostring(self):
        s  = 'Curve Registry:\n'
        s += '  Total number of curves defined:    {}\n'.format(len(self._data))
        s += '    Pump Head curves:          {}\n'.format(len(self.pump_curve_names))
        s += '    Efficiency curves:         {}\n'.format(len(self.efficiency_curve_names))
        s += '    Headloss curves:           {}\n'.format(len(self.headloss_curve_names))
        s += '    Volume curves:             {}\n'.format(len(self.volume_curve_names))
        s += '  Curves used in the network:        {}\n'.format(len(self._usage))
        s += '  Curves provided without a type:    {}\n'.format(len(self.untyped_curve_names))
        if len(self.orphaned()) > 0:
            s += '  Curves used without definition:    {}\n'.format(len(self.orphaned()))
            for orphan in self.orphaned():
                s += '   - {}: {}\n'.format(orphan, self._usage[orphan])
        return s


class SourceRegistry(Registry):
    @property
    def _sources(self):
        raise UnboundLocalError('registries are not reentrant')

    def __delitem__(self, key):
        try:
            if self._usage and key in self._usage and len(self._usage[key]) > 0:
                raise RuntimeError('cannot remove %s %s, still used by %s'%( 
                                   self.__class__.__name__,
                                   key,
                                   self._usage[key]))
            elif key in self._usage:
                self._usage.pop(key)
            source = self._data.pop(key)
            self._patterns.remove_usage(source.strength_timeseries.pattern_name, (source.name, 'Source'))
            self._nodes.remove_usage(source.node_name, (source.name, 'Source'))            
            return source
        except KeyError:
            # Do not raise an exception if there is no key of that name
            return

class NodeRegistry(Registry):

    def __init__(self, model):
        super(NodeRegistry, self).__init__(model)
        self._junctions = OrderedSet()
        self._reservoirs = OrderedSet()
        self._tanks = OrderedSet()
    
    @property
    def _nodes(self):
        raise UnboundLocalError('registries are not reentrant')
    
    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise ValueError('Registry keys must be strings')
        self._data[key] = value
        if isinstance(value, Junction):
            self._junctions.add(key)
        elif isinstance(value, Tank):
            self._tanks.add(key)
        elif isinstance(value, Reservoir):
            self._reservoirs.add(key)
    
    def __delitem__(self, key):
        try:
            if self._usage and key in self._usage and len(self._usage[key]) > 0:
                raise RuntimeError('cannot remove %s %s, still used by %s'%(
                                   self.__class__.__name__,
                                   key,
                                   str(self._usage[key])))
            elif key in self._usage:
                self._usage.pop(key)
            node = self._data.pop(key)
            self._junctions.discard(key)
            self._reservoirs.discard(key)
            self._tanks.discard(key)
            if isinstance(node, Junction):
                for pat_name in node.demand_timeseries_list.pattern_list():
                    if pat_name:
                        self._curves.remove_usage(pat_name, (node.name, 'Junction'))
            if isinstance(node, Reservoir) and node.head_pattern_name:
                self._curves.remove_usage(node.head_pattern_name, (node.name, 'Reservoir'))
            if isinstance(node, Reservoir) and node.vol_curve_name:
                self._curves.remove_usage(node.vol_curve_name, (node.name, 'Tank'))
            return node
        except KeyError:
            return 
    
    def __call__(self, node_type=None):
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
            for node_name, node in self._data.items():
                yield node_name, node
        elif node_type==Junction:
            for node_name in self._junctions:
                yield node_name, self._data[node_name]
        elif node_type==Tank:
            for node_name in self._tanks:
                yield node_name, self._data[node_name]
        elif node_type==Reservoir:
            for node_name in self._reservoirs:
                yield node_name, self._data[node_name]
        else:
            raise RuntimeError('node_type, '+str(node_type)+', not recognized.')

    def add_junction(self, name, base_demand=0.0, demand_pattern=None, 
                     elevation=0.0, coordinates=None, demand_category=None):
        """
        Adds a junction to the water network model.

        Parameters
        -------------------
        name : string
            Name of the junction.
        base_demand : float
            Base demand at the junction.
        demand_pattern : string or Pattern
            Name of the demand pattern or the actual Pattern object
        elevation : float
            Elevation of the junction.
        coordinates : tuple of floats
            X-Y coordinates of the node location.
                
        """
        base_demand = float(base_demand)
        elevation = float(elevation)
        junction = Junction(name, self._m)
        junction.elevation = elevation
        if base_demand:
            junction.add_demand(base_demand, demand_pattern, demand_category)
        self[name] = junction
        if coordinates is not None:
            junction.coordinates = coordinates

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
        vol_curve : str
            Name of a volume curve (optional)
        coordinates : tuple of floats
            X-Y coordinates of the node location.
            
        Raises
        ------
        ValueError
            If `init_level` greater than `max_level` or less than `min_level`
            
        """
        elevation = float(elevation)
        init_level = float(init_level)
        min_level = float(min_level)
        max_level = float(max_level)
        diameter = float(diameter)
        if min_vol is not None:
            min_vol = float(min_vol)
        if init_level < min_level:
            raise ValueError("Initial tank level must be greater than or equal to the tank minimum level.")
        if init_level > max_level:
            raise ValueError("Initial tank level must be less than or equal to the tank maximum level.")
        if vol_curve and not isinstance(vol_curve, six.string_types):
            raise ValueError('Volume curve name must be a string')
        tank = Tank(name, self._m)
        tank.elevation = elevation
        tank.init_level = init_level
        tank.min_level = min_level
        tank.max_level = max_level
        tank.diameter = diameter
        tank.min_vol = min_vol
        tank.vol_curve_name = vol_curve
        self[name] = tank
        if coordinates is not None:
            tank.coordinates = coordinates

    def add_reservoir(self, name, base_head=0.0, head_pattern=None, coordinates=None):
        """
        Adds a reservoir to the water network model.

        Parameters
        ----------
        name : string
            Name of the reservoir.
        base_head : float, optional
            Base head at the reservoir.
        head_pattern : string
            Name of the head pattern (optional)
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        
        """
        base_head = float(base_head)
        if head_pattern and not isinstance(head_pattern, six.string_types):
            raise ValueError('Head pattern must be a string')
        reservoir = Reservoir(name, self._m)
        reservoir.base_head = base_head
        reservoir.head_pattern_name = head_pattern
        self[name] = reservoir
        if coordinates is not None:
            reservoir.coordinates = coordinates

    @property
    def junction_names(self):
        return self._junctions
    
    @property
    def tank_names(self):
        return self._tanks
    
    @property
    def reservoir_names(self):
        return self._reservoirs
    
    def junctions(self):
        for node_name in self._junctions:
            yield node_name, self._data[node_name]
    
    def tanks(self):
        for node_name in self._tanks:
            yield node_name, self._data[node_name]
    
    def reservoirs(self):
        for node_name in self._reservoirs:
            yield node_name, self._data[node_name]

    def tostring(self):
        s  = 'Node Registry:\n'
        s += '  Total number of nodes defined:     {}\n'.format(len(self._data))
        s += '    Junctions:      {}\n'.format(len(self.junction_names))
        s += '    Tanks:          {}\n'.format(len(self.tank_names))
        s += '    Reservoirs:     {}\n'.format(len(self.reservoir_names))
        if len(self.orphaned()) > 0:
            s += '  Nodes used without definition:     {}\n'.format(len(self.orphaned()))
            for orphan in self.orphaned():
                s += '   - {}: {}\n'.format(orphan, self._usage[orphan])
        return s


class LinkRegistry(Registry):
    __subsets = ['_pipes', '_pumps', '_head_pumps', '_power_pumps', '_prvs', '_psvs', '_pbvs', '_tcvs', '_fcvs', '_gpvs', '_valves']

    def __init__(self, model):
        super(LinkRegistry, self).__init__(model)
        self._pipes = OrderedSet()
        self._pumps = OrderedSet()
        self._head_pumps = OrderedSet()
        self._power_pumps = OrderedSet()
        self._prvs = OrderedSet()
        self._psvs = OrderedSet()
        self._pbvs = OrderedSet()
        self._tcvs = OrderedSet()
        self._fcvs = OrderedSet()
        self._gpvs = OrderedSet()
        self._valves = OrderedSet()
    
    @property
    def _links(self):
        raise UnboundLocalError('registries are not reentrant')

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise ValueError('Registry keys must be strings')
        self._data[key] = value
        if isinstance(value, Pipe):
            self._pipes.add(key)
        elif isinstance(value, Pump):
            self._pumps.add(key)
            if isinstance(value, HeadPump):
                self._head_pumps.add(key)
            elif isinstance(value, PowerPump):
                self._power_pumps.add(key)
        elif isinstance(value, Valve):
            self._valves.add(key)
            if isinstance(value, PRValve):
                self._prvs.add(key)
            elif isinstance(value, PSValve):
                self._psvs.add(key)
            elif isinstance(value, PBValve):
                self._pbvs.add(key)
            elif isinstance(value, TCValve):
                self._tcvs.add(key)
            elif isinstance(value, FCValve):
                self._fcvs.add(key)
            elif isinstance(value, GPValve):
                self._gpvs.add(key)
    
    def __delitem__(self, key):
        try:
            if self._usage and key in self._usage and len(self._usage[key]) > 0:
                raise RuntimeError('cannot remove %s %s, still used by %s', 
                                   self.__class__.__name__,
                                   key,
                                   self._usage[key])
            elif key in self._usage:
                self._usage.pop(key)
            link = self._data.pop(key)
            self._nodes.remove_usage(link.start_node_name, (link.name, link.link_type))
            self._nodes.remove_usage(link.end_node_name, (link.name, link.link_type))
            if isinstance(link, GPValve):
                self._curves.remove_usage(link.headloss_curve_name, (link.name, 'Valve'))
            if isinstance(link, Pump):
                self._curves.remove_usage(link.speed_pattern_name, (link.name, 'Pump'))
            if isinstance(link, HeadPump):
                self._curves.remove_usage(link.pump_curve_name, (link.name, 'Pump'))
            for ss in self.__subsets:
                # Go through the _pipes, _prvs, ..., and remove this link
                getattr(self, ss).discard(key)
            return link
        except KeyError:
            return
    
    def __call__(self, link_type=None):
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
        if link_type==None:
            for name, node in self._data.items():
                yield name, node
        elif link_type==Pipe:
            for name in self._pipes:
                yield name, self._data[name]
        elif link_type==Pump:
            for name in self._pumps:
                yield name, self._data[name]
        elif link_type==Valve:
            for name in self._valves:
                yield name, self._data[name]
        else:
            raise RuntimeError('link_type, '+str(link_type)+', not recognized.')

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
        pipe = Pipe(name, start_node_name, end_node_name, self._m)
        pipe.length = length
        pipe.diameter = diameter
        pipe.roughness = roughness
        pipe.minor_loss = minor_loss
        pipe.intial_status = status
        pipe.status = status
        pipe.cv = check_valve_flag
        self[name] = pipe

    def add_pump(self, name, start_node_name, end_node_name, pump_type='POWER',
                 pump_parameter=50.0, speed=1.0, pattern=None):
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
        pump_type : string, optional
            Type of information provided for a pump. Options are 'POWER' or 'HEAD'.
        pump_parameter : float or str object
            Float value of power in KW. Head curve name.
        speed: float
            Relative speed setting (1.0 is normal speed)
        pattern: str
            ID of pattern for speed setting
        
        """
        if pump_type.upper() == 'POWER':
            pump = PowerPump(name, start_node_name, end_node_name, self._m)
            pump.power = pump_parameter
        elif pump_type.upper() == 'HEAD':
            pump = HeadPump(name, start_node_name, end_node_name, self._m)
            if not isinstance(pump_parameter, six.string_types):
                pump.pump_curve_name = pump_parameter.name
            else:
                pump.pump_curve_name = pump_parameter
        else:
            raise ValueError('pump_type must be "POWER" or "HEAD"')
        pump.base_speed = speed
        if isinstance(pattern, Pattern):
            pump.speed_pattern = pattern.name
        else:
            pump.speed_pattern_name = pattern
        self[name] = pump
    
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
        start_node = self._nodes[start_node_name]
        end_node = self._nodes[end_node_name]
        if type(start_node)==Tank or type(end_node)==Tank:
            logger.warn('Valves should not be connected to tanks! Please add a pipe between the tank and valve. Note that this will be an error in the next release.')
        valve_type = valve_type.upper()
        if valve_type == 'PRV':
            valve = PRValve(name, start_node_name, end_node_name, self._m)
            valve.initial_setting = setting
            valve.setting = setting
        elif valve_type == 'PSV':
            valve = PSValve(name, start_node_name, end_node_name, self._m)
            valve.initial_setting = setting
            valve.setting = setting
        elif valve_type == 'PBV':
            valve = PBValve(name, start_node_name, end_node_name, self._m)
            valve.initial_setting = setting
            valve.setting = setting
        elif valve_type == 'FCV':
            valve = FCValve(name, start_node_name, end_node_name, self._m)
            valve.initial_setting = setting
            valve.setting = setting
        elif valve_type == 'TCV':
            valve = TCValve(name, start_node_name, end_node_name, self._m)
            valve.initial_setting = setting
            valve.setting = setting
        elif valve_type == 'GPV':
            valve = GPValve(name, start_node_name, end_node_name, self._m)
            valve.headloss_curve_name = setting
        valve.diameter = diameter
        valve.minor_loss = minor_loss
        self[name] = valve

    def check_valves(self):
        for name in self._pipes:
            if self._data[name].cv:
                yield name

    @property
    def pipe_names(self):
        return self._pipes
    
    @property
    def valve_names(self):
        return self._valves
    
    @property
    def pump_names(self):
        return self._pumps

    def pipes(self):
        for name in self._pipes:
            yield name, self._data[name]
    
    def pumps(self):
        for name in self._pumps:
            yield name, self._data[name]
    
    def valves(self):
        for name in self._valves:
            yield name, self._data[name]

    def head_pumps(self):
        for name in self._head_pumps:
            yield name, self._data[name]

    def power_pumps(self):
        for name in self._power_pumps:
            yield name, self._data[name]

    def prvs(self):
        for name in self._prvs:
            yield name, self._data[name]

    def psvs(self):
        for name in self._psvs:
            yield name, self._data[name]

    def pbvs(self):
        for name in self._pbvs:
            yield name, self._data[name]

    def tcvs(self):
        for name in self._tcvs:
            yield name, self._data[name]

    def fcvs(self):
        for name in self._fcvs:
            yield name, self._data[name]

    def gpvs(self):
        for name in self._gpvs:
            yield name, self._data[name]

    def tostring(self):
        s  = 'Link Registry:\n'
        s += '  Total number of links defined:     {}\n'.format(len(self._data))
        s += '    Pipes:                     {}\n'.format(len(self.pipe_names))
        ct_cv = sum([ 1 for n in self.check_valves()])
        if ct_cv:
            s += '      Check valves:     {}\n'.format(ct_cv)
        s += '    Pumps:                     {}\n'.format(len(self.pump_names))
        ct_cp = len(self._power_pumps)
        ct_hc = len(self._head_pumps)
        if ct_cp:
            s += '      Constant power:   {}\n'.format(ct_cp)
        if ct_hc:
            s += '      Head/pump curve:  {}\n'.format(ct_hc)
        s += '    Valves:                    {}\n'.format(len(self.valve_names))
        PRV = len(self._prvs)
        PSV = len(self._psvs)
        PBV = len(self._pbvs)
        FCV = len(self._fcvs)
        TCV = len(self._tcvs)
        GPV = len(self._gpvs)
        if PRV:
            s += '      Pres. reducing:   {}\n'.format(PRV)
        if PSV:
            s += '      Pres. sustaining: {}\n'.format(PSV)
        if PBV:
            s += '      Pres. breaker:    {}\n'.format(PBV)
        if FCV:
            s += '      Flow control:     {}\n'.format(FCV)
        if TCV:
            s += '      Throttle control: {}\n'.format(TCV)
        if GPV:
            s += '      General purpose:  {}\n'.format(GPV)
        if len(self.orphaned()) > 0:
            s += '  Links used without definition:     {}\n'.format(len(self.orphaned()))
            for orphan in self.orphaned():
                s += '   - {}: {}\n'.format(orphan, self._usage[orphan])
        return s

