"""
The wntr.network.model module includes methods to build a water network
model.
"""
import logging
from collections import OrderedDict
from typing import List, Union
from warnings import warn

import networkx as nx
import numpy as np
import pandas as pd
import six
import wntr.epanet
import wntr.network.io
from wntr.utils.ordered_set import OrderedSet

from .base import AbstractModel, Link, LinkStatus, Registry
from .controls import Control, Rule
from .elements import (
    Curve,
    Demands,
    FCValve,
    GPValve,
    HeadPump,
    Junction,
    Pattern,
    PBValve,
    Pipe,
    PowerPump,
    PRValve,
    PSValve,
    Pump,
    Reservoir,
    Source,
    Tank,
    TCValve,
    TimeSeries,
    Valve,
)

from .options import Options
from .io import read_inpfile

logger = logging.getLogger(__name__)


class WaterNetworkModel(AbstractModel):
    """
    Water network model class.

    Parameters
    -------------------
    inp_file_name: str (optional)
        Directory and filename of EPANET inp file to load into the
        :class:`~wntr.network.model.WaterNetworkModel` object.
    """

    def __init__(self, inp_file_name=None):

        # Network name
        self.name = None
        self._references: List[Union[str, dict]] = list()
        """A list of references that document the source of this model."""

        self._options = Options()
        self._node_reg = NodeRegistry(self)
        self._link_reg = LinkRegistry(self)
        self._pattern_reg = PatternRegistry(self)
        self._curve_reg = CurveRegistry(self)
        self._controls = OrderedDict()
        self._sources = SourceRegistry(self)
        self._msx = None

        self._node_reg._finalize_(self)
        self._link_reg._finalize_(self)
        self._pattern_reg._finalize_(self)
        self._curve_reg._finalize_(self)
        self._sources._finalize_(self)

        # NetworkX Graph to store the pipe connectivity and node coordinates

        self._labels = None

        self._inpfile = None
        if inp_file_name:
            read_inpfile(inp_file_name, append=self)

        # To be deleted and/or renamed and/or moved
        # Time parameters
        self.sim_time = 0.0
        self._prev_sim_time = None  # the last time at which results were accepted

    def _compare(self, other, level=1):
        """
        Parameters
        ----------
        other: WaterNetworkModel

        Returns
        -------
        bool
        """
        if (
            self.num_junctions != other.num_junctions
            or self.num_reservoirs != other.num_reservoirs
            or self.num_tanks != other.num_tanks
            or self.num_pipes != other.num_pipes
            or self.num_pumps != other.num_pumps
            or self.num_valves != other.num_valves
        ):
            return False
        for name, node in self.nodes():
            if not node._compare(other.get_node(name)):
                return False
        for name, link in self.links():
            if not link._compare(other.get_link(name)):
                return False
            
        if level > 0:
            for name, pat in self.patterns():
                if pat != other.get_pattern(name):
                    return False
            for name, curve in self.curves():
                if curve != other.get_curve(name):
                    return False
            for name, source in self.sources():
                if source != other.get_source(name):
                    return False
            if self.options != other.options:
                return False
            for name, control in self.controls():
                if not control._compare(other.get_control(name)):
                    return False
        return True

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
        AM on the first day to the time at the previous hydraulic
        timestep.
        """
        return self._prev_sim_time + self.options.time.start_clocktime

    @property
    def _clock_time(self):
        """
        Return the current time of day in seconds from 12 AM
        """
        return self._shifted_time % (24 * 3600)

    @property
    def _clock_day(self):
        """Return the clock-time day of the simulation"""
        return int(self._shifted_time / 86400)

    ### #
    ### Iteratable attributes
    @property
    def options(self):
        """The model's options object
        
        Returns
        -------
        Options
        
        """
        return self._options

    @property
    def nodes(self):
        """The node registry (as property) or a generator for iteration (as function call)
        
        Returns
        -------
        NodeRegistry
        
        """
        return self._node_reg

    @property
    def links(self):
        """The link registry (as property) or a generator for iteration (as function call)
        
        Returns
        -------
        LinkRegistry
        
        """
        return self._link_reg

    @property
    def patterns(self):
        """The pattern registry (as property) or a generator for iteration (as function call)

        Returns
        -------
        PatternRegistry

        """
        return self._pattern_reg

    @property
    def curves(self):
        """The curve registry (as property) or a generator for iteration (as function call)
        
        Returns
        -------
        CurveRegistry        
        
        """
        return self._curve_reg

    def sources(self):
        """Returns a generator to iterate over all sources

        Returns
        -------
        A generator in the format (name, object).
        """
        for source_name, source in self._sources.items():
            yield source_name, source

    def controls(self):
        """Returns a generator to iterate over all controls

        Returns
        -------
        A generator in the format (name, object).
        """
        for control_name, control in self._controls.items():
            yield control_name, control

    ### #
    ### Element iterators
    @property
    def junctions(self):
        """Iterator over all junctions"""
        return self._node_reg.junctions

    @property
    def tanks(self):
        """Iterator over all tanks"""
        return self._node_reg.tanks

    @property
    def reservoirs(self):
        """Iterator over all reservoirs"""
        return self._node_reg.reservoirs

    @property
    def pipes(self):
        """Iterator over all pipes"""
        return self._link_reg.pipes

    @property
    def pumps(self):
        """Iterator over all pumps"""
        return self._link_reg.pumps

    @property
    def valves(self):
        """Iterator over all valves"""
        return self._link_reg.valves

    @property
    def head_pumps(self):
        """Iterator over all head-based pumps"""
        return self._link_reg.head_pumps

    @property
    def power_pumps(self):
        """Iterator over all power pumps"""
        return self._link_reg.power_pumps

    @property
    def prvs(self):
        """Iterator over all pressure reducing valves (PRVs)"""
        return self._link_reg.prvs

    @property
    def psvs(self):
        """Iterator over all pressure sustaining valves (PSVs)"""
        return self._link_reg.psvs

    @property
    def pbvs(self):
        """Iterator over all pressure breaker valves (PBVs)"""
        return self._link_reg.pbvs

    @property
    def tcvs(self):
        """Iterator over all throttle control valves (TCVs)"""
        return self._link_reg.tcvs

    @property
    def fcvs(self):
        """Iterator over all flow control valves (FCVs)"""
        return self._link_reg.fcvs

    @property
    def gpvs(self):
        """Iterator over all general purpose valves (GPVs)"""
        return self._link_reg.gpvs

    @property
    def msx(self):
        """A multispecies water quality model, if defined"""
        return self._msx
    
    @msx.setter
    def msx(self, model):
        if model is None:
            self._msx = None
            return
        from wntr.msx.base import QualityModelBase
        if not isinstance(model, QualityModelBase):
            raise TypeError('Expected QualityModelBase (or derived), got {}'.format(type(model)))
        self._msx = model

    def add_msx_model(self, msx_filename=None):
        """Add an msx model from a MSX input file (.msx extension)"""
        from wntr.msx.model import MsxModel
        self._msx = MsxModel(msx_file_name=msx_filename)

    def remove_msx_model(self):
        """Remove an msx model from the network"""
        self._msx = None

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
    def add_junction(
        self, name, base_demand=0.0, demand_pattern=None, elevation=0.0, coordinates=None, demand_category=None
    ):
        """
        Adds a junction to the water network model

        Parameters
        -------------------
        name : str
            Name of the junction.
        base_demand : float
            Base demand at the junction.
        demand_pattern : str or Pattern
            Name of the demand pattern or the Pattern object
        elevation : float
            Elevation of the junction.
        coordinates : tuple of floats
            X-Y coordinates of the node location.
        demand_category  : str
            Name of the demand category
        """
        self._node_reg.add_junction(name, base_demand, demand_pattern, elevation, coordinates, demand_category)

    def add_tank(
        self,
        name,
        elevation=0.0,
        init_level=3.048,
        min_level=0.0,
        max_level=6.096,
        diameter=15.24,
        min_vol=0.0,
        vol_curve=None,
        overflow=False,
        coordinates=None,
    ):
        """
        Adds a tank to the water network model

        Parameters
        -------------------
        name : str
            Name of the tank.
        elevation : float
            Elevation at the tank.
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
        vol_curve : str, optional
            Name of a volume curve
        overflow : bool
           Overflow indicator (Always False for the WNTRSimulator)
        coordinates : tuple of float, optional
            X-Y coordinates of the node location.
            
        """
        self._node_reg.add_tank(
            name, elevation, init_level, min_level, max_level, diameter, min_vol, vol_curve, overflow, coordinates
        )

    def add_reservoir(self, name, base_head=0.0, head_pattern=None, coordinates=None):
        """
        Adds a reservoir to the water network model

        Parameters
        ----------
        name : str
            Name of the reservoir.
        base_head : float, optional
            Base head at the reservoir.
        head_pattern : str, optional
            Name of the head pattern.
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        
        """
        self._node_reg.add_reservoir(name, base_head, head_pattern, coordinates)

    def add_pipe(
        self,
        name,
        start_node_name,
        end_node_name,
        length=304.8,
        diameter=0.3048,
        roughness=100,
        minor_loss=0.0,
        initial_status="OPEN",
        check_valve=False,
    ):
        """
        Adds a pipe to the water network model

        Parameters
        ----------
        name : str
            Name of the pipe.
        start_node_name : str
             Name of the start node.
        end_node_name : str
             Name of the end node.
        length : float, optional
            Length of the pipe.
        diameter : float, optional
            Diameter of the pipe.
        roughness : float, optional
            Pipe roughness coefficient.
        minor_loss : float, optional
            Pipe minor loss coefficient.
        initial_status : str or LinkStatus, optional
            Pipe initial status. Options are 'OPEN' or 'CLOSED'.
        check_valve : bool, optional
            True if the pipe has a check valve.
            False if the pipe does not have a check valve.
        
        """
        self._link_reg.add_pipe(
            name, start_node_name, end_node_name, length, diameter, roughness, minor_loss, initial_status, check_valve
        )

    def add_pump(
        self,
        name,
        start_node_name,
        end_node_name,
        pump_type="POWER",
        pump_parameter=50.0,
        speed=1.0,
        pattern=None,
        initial_status="OPEN",
    ):
        """
        Adds a pump to the water network model

        Parameters
        ----------
        name : str
            Name of the pump.
        start_node_name : str
             Name of the start node.
        end_node_name : str
             Name of the end node.
        pump_type : str, optional
            Type of information provided for a pump. Options are 'POWER' or 'HEAD'.
        pump_parameter : float or str
            For a POWER pump, the pump power.
            For a HEAD pump, the head curve name.
        speed: float
            Relative speed setting (1.0 is normal speed)
        pattern: str
            Name of the speed pattern
        initial_status : str or LinkStatus
            Pump initial status. Options are 'OPEN' or 'CLOSED'.
        
        """
        self._link_reg.add_pump(
            name, start_node_name, end_node_name, pump_type, pump_parameter, speed, pattern, initial_status
        )

    def add_valve(
        self,
        name,
        start_node_name,
        end_node_name,
        diameter=0.3048,
        valve_type="PRV",
        minor_loss=0.0,
        initial_setting=0.0,
        initial_status="ACTIVE",
    ):
        """
        Adds a valve to the water network model

        Parameters
        ----------
        name : str
            Name of the valve.
        start_node_name : str
             Name of the start node.
        end_node_name : str
             Name of the end node.
        diameter : float, optional
            Diameter of the valve.
        valve_type : str, optional
            Type of valve. Options are 'PRV', 'PSV', 'PBV', 'FCV', 'TCV', and 'GPV'
        minor_loss : float, optional
            Pipe minor loss coefficient.
        initial_setting : float or str, optional
            Valve initial setting.
            Pressure setting for PRV, PSV, or PBV. 
            Flow setting for FCV. 
            Loss coefficient for TCV.
            Name of headloss curve for GPV.
        initial_status: str or LinkStatus
            Valve initial status. Options are 'OPEN',  'CLOSED', or 'ACTIVE'.
        """
        self._link_reg.add_valve(
            name, start_node_name, end_node_name, diameter, valve_type, minor_loss, initial_setting, initial_status
        )

    def add_pattern(self, name, pattern=None):
        """
        Adds a pattern to the water network model
        
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
        name : str
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
        Adds a curve to the water network model

        Parameters
        ----------
        name : str
            Name of the curve.
        curve_type : str
            Type of curve. Options are HEAD, EFFICIENCY, VOLUME, HEADLOSS.
        xy_tuples_list : list of (x, y) tuple
            List of X-Y coordinate tuples on the curve.
        """
        self._curve_reg.add_curve(name, curve_type, xy_tuples_list)

    def add_source(self, name, node_name, source_type, quality, pattern=None):
        """
        Adds a source to the water network model

        Parameters
        ----------
        name : str
            Name of the source

        node_name: str
            Injection node.

        source_type: str
            Source type, options = CONCEN, MASS, FLOWPACED, or SETPOINT

        quality: float
            Source strength in Mass/Time for MASS and Mass/Volume for CONCEN, 
            FLOWPACED, or SETPOINT

        pattern: str or Pattern
            Pattern name or object
        """
        if pattern and isinstance(pattern, six.string_types):
            pattern = self.get_pattern(pattern)
        source = Source(self, name, node_name, source_type, quality, pattern)
        self._sources[source.name] = source
        self._pattern_reg.add_usage(source.strength_timeseries.pattern_name, (source.name, "Source"))
        self._node_reg.add_usage(source.node_name, (source.name, "Source"))

    def add_control(self, name, control_object):
        """
        Adds a control or rule to the water network model

        Parameters
        ----------
        name : str
           control object name.
        control_object : Control or Rule
            Control or Rule object.
        """
        if name in self._controls:
            raise ValueError(
                "The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control."
            )
        self._controls[name] = control_object

    ### #
    ### Remove elements from the model
    def remove_node(self, name, with_control=False, force=False):
        """Removes a node from the water network model"""
        node = self.get_node(name)
        if not force:
            if with_control:
                x = []
                for control_name, control in self._controls.items():
                    if node in control.requires():
                        logger.warning(
                            control._control_type_str()
                            + " "
                            + control_name
                            + " is being removed along with node "
                            + name
                        )
                        x.append(control_name)
                for i in x:
                    self.remove_control(i)
            else:
                for control_name, control in self._controls.items():
                    if node in control.requires():
                        raise RuntimeError(
                            "Cannot remove node {0} without first removing control/rule {1}".format(name, control_name)
                        )
        self._node_reg.__delitem__(name)

    def remove_link(self, name, with_control=False, force=False):
        """Removes a link from the water network model"""
        link = self.get_link(name)
        if not force:
            if with_control:
                x = []
                for control_name, control in self._controls.items():
                    if link in control.requires():
                        logger.warning(
                            control._control_type_str()
                            + " "
                            + control_name
                            + " is being removed along with link "
                            + name
                        )
                        x.append(control_name)
                for i in x:
                    self.remove_control(i)
            else:
                for control_name, control in self._controls.items():
                    if link in control.requires():
                        raise RuntimeError(
                            "Cannot remove link {0} without first removing control/rule {1}".format(name, control_name)
                        )
        self._link_reg.__delitem__(name)

    def remove_pattern(self, name):
        """Removes a pattern from the water network model"""
        self._pattern_reg.__delitem__(name)

    def remove_curve(self, name):
        """Removes a curve from the water network model"""
        self._curve_reg.__delitem__(name)

    def remove_source(self, name):
        """Removes a source from the water network model

        Parameters
        ----------
        name : str
           The name of the source object to be removed
        """
        logger.warning(
            "You are deleting a source. This could have unintended \
            side effects. If you are replacing values, use get_source(name) \
            and modify it instead."
        )
        source = self._sources[name]
        self._pattern_reg.remove_usage(source.strength_timeseries.pattern_name, (source.name, "Source"))
        self._node_reg.remove_usage(source.node_name, (source.name, "Source"))
        del self._sources[name]

    def remove_control(self, name):
        """Removes a control from the water network model"""
        del self._controls[name]

    def _discard_control(self, name):
        """Removes a control from the water network model
        
        If the control is not present, an exception is not raised.

        Parameters
        ----------
        name : string
           The name of the control object to be removed.
        """
        try:
            del self._controls[name]
        except KeyError:
            pass

    ### #
    ### Get elements from the model
    def get_node(self, name):
        """Get a specific node
        
        Parameters
        ----------
        name : str
            The node name
            
        Returns
        -------
        Junction, Tank, or Reservoir
        
        """
        return self._node_reg[name]

    def get_link(self, name):
        """Get a specific link
        
        Parameters
        ----------
        name : str
            The link name
            
        Returns
        -------
        Pipe, Pump, or Valve
        
        """
        return self._link_reg[name]

    def get_pattern(self, name):
        """Get a specific pattern
        
        Parameters
        ----------
        name : str
            The pattern name
            
        Returns
        -------
        Pattern
        
        """
        return self._pattern_reg[name]

    def get_curve(self, name):
        """Get a specific curve
        
        Parameters
        ----------
        name : str
            The curve name
            
        Returns
        -------
        Curve
        
        """
        return self._curve_reg[name]

    def get_source(self, name):
        """Get a specific source
        
        Parameters
        ----------
        name : str
            The source name
            
        Returns
        -------
        Source
        
        """
        return self._sources[name]

    def get_control(self, name):
        """Get a specific control or rule
        
        Parameters
        ----------
        name : str
            The control name
            
        Returns
        -------
        ctrl: Control or Rule
        
        """
        return self._controls[name]

    ### #
    ### Name lists
    @property
    def node_name_list(self):
        """Get a list of node names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._node_reg.keys())

    @property
    def junction_name_list(self):
        """Get a list of junction names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._node_reg.junction_names)

    @property
    def tank_name_list(self):
        """Get a list of tanks names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._node_reg.tank_names)

    @property
    def reservoir_name_list(self):
        """Get a list of reservoir names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._node_reg.reservoir_names)

    @property
    def link_name_list(self):
        """Get a list of link names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._link_reg.keys())

    @property
    def pipe_name_list(self):
        """Get a list of pipe names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._link_reg.pipe_names)

    @property
    def pump_name_list(self):
        """Get a list of pump names (both types included)

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.pump_names)

    @property
    def head_pump_name_list(self):
        """Get a list of head pump names

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.head_pump_names)

    @property
    def power_pump_name_list(self):
        """Get a list of power pump names

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.power_pump_names)

    @property
    def valve_name_list(self):
        """Get a list of valve names (all types included)

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.valve_names)

    @property
    def prv_name_list(self):
        """Get a list of prv names

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.prv_names)

    @property
    def psv_name_list(self):
        """Get a list of psv names

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.psv_names)

    @property
    def pbv_name_list(self):
        """Get a list of pbv names

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.pbv_names)

    @property
    def tcv_name_list(self):
        """Get a list of tcv names

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.tcv_names)

    @property
    def fcv_name_list(self):
        """Get a list of fcv names

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.fcv_names)

    @property
    def gpv_name_list(self):
        """Get a list of gpv names

        Returns
        -------
        list of strings

        """
        return list(self._link_reg.gpv_names)

    @property
    def pattern_name_list(self):
        """Get a list of pattern names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._pattern_reg.keys())

    @property
    def curve_name_list(self):
        """Get a list of curve names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._curve_reg.keys())

    @property
    def source_name_list(self):
        """Get a list of source names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._sources.keys())

    @property
    def control_name_list(self):
        """Get a list of control/rule names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._controls.keys())

    ### #
    ### Counts
    @property
    def num_nodes(self):
        """The number of nodes"""
        return len(self._node_reg)

    @property
    def num_junctions(self):
        """The number of junctions"""
        return len(self._node_reg.junction_names)

    @property
    def num_tanks(self):
        """The number of tanks"""
        return len(self._node_reg.tank_names)

    @property
    def num_reservoirs(self):
        """The number of reservoirs"""
        return len(self._node_reg.reservoir_names)

    @property
    def num_links(self):
        """The number of links"""
        return len(self._link_reg)

    @property
    def num_pipes(self):
        """The number of pipes"""
        return len(self._link_reg.pipe_names)

    @property
    def num_pumps(self):
        """The number of pumps"""
        return len(self._link_reg.pump_names)

    @property
    def num_valves(self):
        """The number of valves"""
        return len(self._link_reg.valve_names)

    @property
    def num_patterns(self):
        """The number of patterns"""
        return len(self._pattern_reg)

    @property
    def num_curves(self):
        """The number of curves"""
        return len(self._curve_reg)

    @property
    def num_sources(self):
        """The number of sources"""
        return len(self._sources)

    @property
    def num_controls(self):
        """The number of controls"""
        return len(self._controls)

    ### #
    ### Helper functions
    def describe(self, level=0):
        """
        Describe number of components in the network model
        
        Parameters
        ----------
        level : int (0, 1, or 2)
            
           * Level 0 returns the number of Nodes, Links, Patterns, Curves, Sources, and Controls.
           * Level 1 includes information from Level 0 but 
             divides Nodes into Junctions, Tanks, and Reservoirs, 
             divides Links into Pipes, Pumps, and Valves, and 
             divides Curves into Pump, Efficiency, Headloss, and Volume.
           * Level 2 includes information from Level 1 but 
             divides Pumps into Head and Power, and 
             divides Valves into PRV, PSV, PBV, TCV, FCV, and GPV.
            
        Returns
        -------
        A dictionary with component counts
        """

        d = {
            "Nodes": self.num_nodes,
            "Links": self.num_links,
            "Patterns": self.num_patterns,
            "Curves": self.num_curves,
            "Sources": self.num_sources,
            "Controls": self.num_controls,
        }

        if level >= 1:
            d["Nodes"] = {"Junctions": self.num_junctions, "Tanks": self.num_tanks, "Reservoirs": self.num_reservoirs}
            d["Links"] = {"Pipes": self.num_pipes, "Pumps": self.num_pumps, "Valves": self.num_valves}
            d["Curves"] = {
                "Pump": len(self._curve_reg._pump_curves),
                "Efficiency": len(self._curve_reg._efficiency_curves),
                "Headloss": len(self._curve_reg._headloss_curves),
                "Volume": len(self._curve_reg._volume_curves),
            }

        if level >= 2:
            d["Links"]["Pumps"] = {"Head": len(list(self.head_pumps())), "Power": len(list(self.power_pumps()))}
            d["Links"]["Valves"] = {
                "PRV": len(list(self.prvs())),
                "PSV": len(list(self.psvs())),
                "PBV": len(list(self.pbvs())),
                "TCV": len(list(self.tcvs())),
                "FCV": len(list(self.fcvs())),
                "GPV": len(list(self.gpvs())),
            }

        return d

    def to_dict(self):
        """
        Dictionary representation of the WaterNetworkModel.
        
        Returns
        -------
        dict
        """
        return wntr.network.io.to_dict(self)

    def from_dict(self, d: dict):
        """
        Append the model with elements from a dictionary.

        Parameters
        ----------
        d : dict
            Dictionary representation of the WaterNetworkModel
        """
        wntr.network.io.from_dict(d, append=self)

    def to_gis(self, crs=None, pumps_as_points=False, valves_as_points=False):
        """
        Convert a WaterNetworkModel into GeoDataFrames
        
        Parameters
        ----------
        crs : str, optional
            Coordinate reference system, by default None
        pumps_as_points : bool, optional
            Represent pumps as points (True) or lines (False), by default False
        valves_as_points : bool, optional
            Represent valves as points (True) or lines (False), by default False
            
        Returns
        -------
        WaterNetworkGIS object that contains junctions, tanks, reservoirs, pipes, 
        pumps, and valves GeoDataFrames
        """
        return wntr.network.io.to_gis(self, crs, pumps_as_points, valves_as_points)
    
    def from_gis(self, gis_data):
        """
        Append the model with elements from GeoDataFrames
        
        Parameters
        ----------
        gis_data : WaterNetworkGIS or dict of geopandas.GeoDataFrame
            GeoDataFrames containing water network attributes. If gis_data is a 
            dictionary, then the keys are junctions, tanks, reservoirs, pipes, 
            pumps, and valves. If the pumps or valves are Points, they will be 
            converted to Lines with the same start and end node location.
            
        Returns
        -------
        WaterNetworkModel
        """
        return wntr.network.io.from_gis(gis_data, append=self)
    
    def to_graph(self, node_weight=None, link_weight=None, 
                 modify_direction=False):
        """
        Convert a WaterNetworkModel into a networkx MultiDiGraph
        
        Parameters
        ----------
        node_weight :  dict or pandas Series (optional)
            Node weights
        link_weight : dict or pandas Series (optional)
            Link weights.  
        modify_direction : bool (optional)
            If True, than if the link weight is negative, the link start and 
            end node are switched and the abs(weight) is assigned to the link
            (this is useful when weighting graphs by flowrate). If False, link 
            direction and weight are not changed.
            
        Returns
        --------
        networkx MultiDiGraph
        """
        return wntr.network.io.to_graph(self, node_weight, link_weight, 
                                        modify_direction)
                                        
                               
    def get_graph(self, node_weight=None, link_weight=None, modify_direction=False):
        """
        Convert a :class:`~wntr.network.model.WaterNetworkModel` into a networkx MultiDiGraph
        
        .. deprecated:: 0.5.0
        Use :meth:`~wntr.network.model.WaterNetworkModel.to_graph` instead
        
        Parameters
        ----------
        node_weight :  dict or pandas.Series (optional)
            Node weights
        link_weight : dict or pandas.Series (optional)
            Link weights.  
        modify_direction : bool (optional)
            If True, then if the link weight is negative, the link start and 
            end node are switched and the abs(weight) is assigned to the link
            (this is useful when weighting graphs by flowrate). If False, link 
            direction and weight are not changed.
            
        Returns
        --------
        networkx MultiDiGraph
        """
        warn("wntr.network.WaterNetworkModel.get_graph is deprecated, use wntr.network.WaterNetworkModel.to_graph instead", DeprecationWarning, stacklevel=2)
        
        return wntr.network.io.to_graph(self, node_weight, link_weight, 
                                        modify_direction)

    def assign_demand(self, demand, pattern_prefix="ResetDemand"):
        """
        Assign demands using values in a DataFrame. 
        
        New demands are specified in a pandas DataFrame indexed by
        time (in seconds). The method resets junction demands by creating a 
        new demand pattern and using a base demand of 1. 
        The demand pattern is resampled to match the water network model 
        pattern timestep. This method can be
        used to reset demands in a water network model to demands from a
        pressure dependent demand simulation.

        Parameters
        ----------
        demand : pandas.DataFrame
            A pandas DataFrame containing demands (index = time, columns = junction names)

        pattern_prefix: str
            Pattern name prefix, default = 'ResetDemand'.  The junction name is 
            appended to the prefix to create a new pattern name.  
            If the pattern name already exists, an error is thrown and the user 
            should use a different pattern prefix name.
        """
        for junc_name in demand.columns:

            # Extract the node demand pattern and resample to match the pattern timestep
            demand_pattern = demand.loc[:, junc_name]
            demand_pattern.index = pd.to_timedelta(demand_pattern.index, "s")
            resample_offset = str(int(self.options.time.pattern_timestep)) + "s"
            demand_pattern = demand_pattern.resample(resample_offset).mean() / self.options.hydraulic.demand_multiplier

            # Add the pattern
            # If the pattern name already exists, this fails
            pattern_name = pattern_prefix + junc_name
            self.add_pattern(pattern_name, demand_pattern.tolist())

            # Reset base demand
            junction = self.get_node(junc_name)
            junction.demand_timeseries_list.clear()
            junction.demand_timeseries_list.append((1.0, pattern_name))

    def get_links_for_node(self, node_name, flag="ALL"):
        """
        Returns a list of links connected to a node

        Parameters
        ----------
        node_name : str
            Name of the node.

        flag : str
            Options are 'ALL', 'INLET', 'OUTLET'.
            'ALL' returns all links connected to the node.
            'INLET' returns links that have the specified node as an end node.
            'OUTLET' returns links that have the specified node as a start node.

        Returns
        -------
        A list of link names connected to the node
        """
        link_types = {"Pipe", "Pump", "Valve"}
        link_data = self._node_reg.get_usage(node_name)
        if link_data is None:
            return []
        else:
            if flag.upper() == "ALL":
                return [
                    link_name
                    for link_name, link_type in link_data
                    if link_type in link_types
                    and node_name in {self.get_link(link_name).start_node_name, self.get_link(link_name).end_node_name}
                ]
            elif flag.upper() == "INLET":
                return [
                    link_name
                    for link_name, link_type in link_data
                    if link_type in link_types and node_name == self.get_link(link_name).end_node_name
                ]
            elif flag.upper() == "OUTLET":
                return [
                    link_name
                    for link_name, link_type in link_data
                    if link_type in link_types and node_name == self.get_link(link_name).start_node_name
                ]
            else:
                logger.error("Unrecognized flag: {0}".format(flag))
                raise ValueError("Unrecognized flag: {0}".format(flag))

    def query_node_attribute(self, attribute, operation=None, value=None, node_type=None):
        """
        Query node attributes, for example get all nodes with elevation <= threshold

        Parameters
        ----------
        attribute: str
            :class:`~wntr.network.base.Node` attribute.

        operation: numpy operator
            Numpy operator, options include
            :obj:`numpy.greater`,
            :obj:`numpy.greater_equal`,
            :obj:`numpy.less`,
            :obj:`numpy.less_equal`,
            :obj:`numpy.equal`,
            :obj:`numpy.not_equal`.

        value: float or int
            Threshold

        node_type: Node type
            :class:`~wntr.network.base.Node` type, options include
            :class:`~wntr.network.base.Node`,
            :class:`~wntr.network.elements.Junction`,
            :class:`~wntr.network.elements.Reservoir`,
            :class:`~wntr.network.elements.Tank`, or None. Default = None.
            Note None and :class:`~wntr.network.base.Node` produce the same results.

        Returns
        -------
        :class:`pandas.Series` that contains the attribute that satisfies the operation threshold for a given node_type.

        Notes
        -----
        If operation and value are both None, the :class:`pandas.Series` will contain the attributes
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
        return pd.Series(node_attribute_dict)

    def query_link_attribute(self, attribute, operation=None, value=None, link_type=None):
        """
        Query link attributes, for example get all pipe diameters > threshold

        Parameters
        ----------
        attribute: str
            :class:`~wntr.network.base.Link` attribute

        operation: numpy operator
            Numpy operator, options include the following: 
            :obj:`numpy.greater`,
            :obj:`numpy.greater_equal`,
            :obj:`numpy.less`,
            :obj:`numpy.less_equal`,
            :obj:`numpy.equal`,
            :obj:`numpy.not_equal`.

        value: float or int
            Threshold

        link_type: Link type
            :class:`~wntr.network.base.Link` type, options include
            :class:`~wntr.network.base.Link`,
            :class:`~wntr.network.elements.Pipe`,
            :class:`~wntr.network.elements.Pump`,
            :class:`~wntr.network.elements.Valve`, or None. Default = None.
            Note None and :class:`~wntr.network.base.Link` produce the same results.
    
        Returns
        -------
        :class:`pandas.Series` that contains the attribute that satisfies the operation threshold for a given link_type.

        Notes
        -----
        If operation and value are both None, the :class:`pandas.Series` will contain the attributes
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
        return pd.Series(link_attribute_dict)

    def convert_controls_to_rules(self, priority=3):
        """
        Convert all controls to rules.
        
        Note that for an exact match between controls and rules, the rule 
        timestep must be very small.

        Parameters
        ----------
        priority : int, optional
           Rule priority, default is 3.

        """
        for name in self.control_name_list:
            control = self.get_control(name)
            if isinstance(control, Control):
                act = control.actions()[0]
                cond = control.condition
                rule = Rule(cond, act, priority=priority)
                self.add_control(name.replace(" ", "_") + "_Rule", rule)
                self.remove_control(name)

    def reset_initial_values(self):
        """
        Resets all initial values in the network
        """
        #### TODO: move reset conditions to /sim
        self.sim_time = 0.0
        self._prev_sim_time = None

        for name, node in self.nodes(Junction):
            node._head = None
            node._demand = None
            node._pressure = None
            node._leak_demand = None
            node._leak_status = False
            node._is_isolated = False

        for name, node in self.nodes(Tank):
            node._head = node.init_level + node.elevation
            node._prev_head = node.head
            node._demand = None
            node._leak_demand = None
            node._leak_status = False
            node._is_isolated = False

        for name, node in self.nodes(Reservoir):
            node._head = None  # node.head_timeseries.base_value
            node._demand = None
            node._leak_demand = None
            node._is_isolated = False

        for name, link in self.links(Pipe):
            link._user_status = link.initial_status
            link._setting = link.initial_setting
            link._internal_status = LinkStatus.Active
            link._is_isolated = False
            link._flow = None
            link._prev_setting = None

        for name, link in self.links(Pump):
            link._user_status = link.initial_status
            link._setting = link.initial_setting
            link._internal_status = LinkStatus.Active
            link._is_isolated = False
            link._flow = None
            if isinstance(link, PowerPump):
                link.power = link._base_power
            link._prev_setting = None

        for name, link in self.links(Valve):
            link._user_status = link.initial_status
            link._setting = link.initial_setting
            link._internal_status = LinkStatus.Active
            link._is_isolated = False
            link._flow = None
            link._prev_setting = None

        for name, control in self.controls():
            control._reset()


class PatternRegistry(Registry):
    """A registry for patterns."""

    def _finalize_(self, model):
        super()._finalize_(model)
        self._pattern_reg = None

    class DefaultPattern(object):
        """An object that always points to the current default pattern for a model"""

        def __init__(self, options):
            self._options = options

        def __str__(self):
            return str(self._options.hydraulic.pattern) if self._options.hydraulic.pattern is not None else ""

        def __repr__(self):
            return "DefaultPattern()"

        @property
        def name(self):
            """The name of the default pattern, or ``None`` if no pattern is assigned"""
            return str(self._options.hydraulic.pattern) if self._options.hydraulic.pattern is not None else ""

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
        name : str
            Name of the pattern.
        pattern : list of float or Pattern
            A list of floats that make up the pattern, or a 
            :class:`~wntr.network.elements.Pattern` object.

        Raises
        ------
        ValueError
            If adding a pattern with `name` that already exists.
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(pattern, (list, np.ndarray, Pattern)), "pattern must be a list or Pattern"

        if not isinstance(pattern, Pattern):
            pattern = Pattern(name, multipliers=pattern, time_options=self._options.time)
        else:  # elif pattern.time_options is None:
            pattern.time_options = self._options.time
        if pattern.name in self._data.keys():
            raise ValueError("Pattern name already exists")
        self[name] = pattern

    @property
    def default_pattern(self):
        """A new default pattern object"""
        return self.DefaultPattern(self._options)


class CurveRegistry(Registry):
    """A registry for curves."""

    def __init__(self, model):
        super(CurveRegistry, self).__init__(model)
        self._pump_curves = OrderedSet()
        self._efficiency_curves = OrderedSet()
        self._headloss_curves = OrderedSet()
        self._volume_curves = OrderedSet()

    def _finalize_(self, model):
        super()._finalize_(model)
        self._curve_reg = None

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise ValueError("Registry keys must be strings")
        self._data[key] = value
        if value is not None:
            self.set_curve_type(key, value.curve_type)

    def set_curve_type(self, key, curve_type):
        """
        Sets curve type.
        
        WARNING -- this does not check to make sure key is typed before assigning it - 
        you could end up with a curve that is used for more than one type"""
        if curve_type is None:
            return
        curve_type = curve_type.upper()
        if curve_type == "HEAD":
            self._pump_curves.add(key)
        elif curve_type == "HEADLOSS":
            self._headloss_curves.add(key)
        elif curve_type == "VOLUME":
            self._volume_curves.add(key)
        elif curve_type == "EFFICIENCY":
            self._efficiency_curves.add(key)
        else:
            raise ValueError("curve_type must be HEAD, HEADLOSS, VOLUME, or EFFICIENCY")

    def add_curve(self, name, curve_type, xy_tuples_list):
        """
        Adds a curve to the water network model.

        Parameters
        ----------
        name : str
            Name of the curve.
        curve_type : str
            Type of curve. Options are HEAD, EFFICIENCY, VOLUME, HEADLOSS.
        xy_tuples_list : list of (x, y) tuples
            List of X-Y coordinate tuples on the curve.
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(curve_type, (type(None), str)), "curve_type must be a string"
        assert isinstance(xy_tuples_list, (list, np.ndarray)), "xy_tuples_list must be a list of (x,y) tuples"

        curve = Curve(name, curve_type, xy_tuples_list)
        self[name] = curve

    def untyped_curves(self):
        """Generator to get all curves without type
        
        Yields
        ------
        name : str
            The name of the curve
        curve : Curve
            The untyped curve object    
            
        """
        defined = set(self._data.keys())
        untyped = defined.difference(
            self._pump_curves, self._efficiency_curves, self._headloss_curves, self._volume_curves
        )
        for key in untyped:
            yield key, self._data[key]

    @property
    def untyped_curve_names(self):
        """List of names of all curves without types"""
        defined = set(self._data.keys())
        untyped = defined.difference(
            self._pump_curves, self._efficiency_curves, self._headloss_curves, self._volume_curves
        )
        return list(untyped)

    def pump_curves(self):
        """Generator to get all pump curves
        
        Yields
        ------
        name : str
            The name of the curve
        curve : Curve
            The pump curve object    
            
        """
        for key in self._pump_curves:
            yield key, self._data[key]

    @property
    def pump_curve_names(self):
        """List of names of all pump curves"""
        return list(self._pump_curves)

    def efficiency_curves(self):
        """Generator to get all efficiency curves
        
        Yields
        ------
        name : str
            The name of the curve
        curve : Curve
            The efficiency curve object    
            
        """
        for key in self._efficiency_curves:
            yield key, self._data[key]

    @property
    def efficiency_curve_names(self):
        """List of names of all efficiency curves"""
        return list(self._efficiency_curves)

    def headloss_curves(self):
        """Generator to get all headloss curves
        
        Yields
        ------
        name : str
            The name of the curve
        curve : Curve
            The headloss curve object    
            
        """
        for key in self._headloss_curves:
            yield key, self._data[key]

    @property
    def headloss_curve_names(self):
        """List of names of all headloss curves"""
        return list(self._headloss_curves)

    def volume_curves(self):
        """Generator to get all volume curves
        
        Yields
        ------
        name : str
            The name of the curve
        curve : Curve
            The volume curve object    
            
        """
        for key in self._volume_curves:
            yield key, self._data[key]

    @property
    def volume_curve_names(self):
        """List of names of all volume curves"""
        return list(self._volume_curves)


class SourceRegistry(Registry):
    """A registry for sources."""

    def _finalize_(self, model):
        super()._finalize_(model)
        self._sources = None

    def __delitem__(self, key):
        try:
            if self._usage and key in self._usage and len(self._usage[key]) > 0:
                raise RuntimeError(
                    "cannot remove %s %s, still used by %s" % (self.__class__.__name__, key, self._usage[key])
                )
            elif key in self._usage:
                self._usage.pop(key)
            source = self._data.pop(key)
            self._pattern_reg.remove_usage(source.strength_timeseries.pattern_name, (source.name, "Source"))
            self._node_reg.remove_usage(source.node_name, (source.name, "Source"))
            return source
        except KeyError:
            # Do not raise an exception if there is no key of that name
            return


class NodeRegistry(Registry):
    """A registry for nodes."""

    def __init__(self, model):
        super(NodeRegistry, self).__init__(model)
        self._junctions = OrderedSet()
        self._reservoirs = OrderedSet()
        self._tanks = OrderedSet()

    def _finalize_(self, model):
        super()._finalize_(model)
        self._node_reg = None

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise ValueError("Registry keys must be strings")
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
                raise RuntimeError(
                    "cannot remove %s %s, still used by %s" % (self.__class__.__name__, key, str(self._usage[key]))
                )
            elif key in self._usage:
                self._usage.pop(key)
            node = self._data.pop(key)
            self._junctions.discard(key)
            self._reservoirs.discard(key)
            self._tanks.discard(key)
            if isinstance(node, Junction):
                for pat_name in node.demand_timeseries_list.pattern_list():
                    if pat_name:
                        self._curve_reg.remove_usage(pat_name, (node.name, "Junction"))
            if isinstance(node, Reservoir) and node.head_pattern_name:
                self._curve_reg.remove_usage(node.head_pattern_name, (node.name, "Reservoir"))
            if isinstance(node, Tank) and node.vol_curve_name:
                self._curve_reg.remove_usage(node.vol_curve_name, (node.name, "Tank"))
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
        if node_type == None:
            for node_name, node in self._data.items():
                yield node_name, node
        elif node_type == Junction:
            for node_name in self._junctions:
                yield node_name, self._data[node_name]
        elif node_type == Tank:
            for node_name in self._tanks:
                yield node_name, self._data[node_name]
        elif node_type == Reservoir:
            for node_name in self._reservoirs:
                yield node_name, self._data[node_name]
        else:
            raise RuntimeError("node_type, " + str(node_type) + ", not recognized.")

    def add_junction(
        self,
        name,
        base_demand=0.0,
        demand_pattern=None,
        elevation=0.0,
        coordinates=None,
        demand_category=None,
        emitter_coeff=None,
        initial_quality=None,
    ):
        """
        Adds a junction to the water network model.

        Parameters
        -------------------
        name : str
            Name of the junction.
        base_demand : float
            Base demand at the junction.
        demand_pattern : str or Pattern
            Name of the demand pattern or the Pattern object
        elevation : float
            Elevation of the junction.
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        demand_category : str, optional
            Category to the **base** demand
        emitter_coeff : float, optional
            Emitter coefficient
        initial_quality : float, optional
            Initial quality at this junction
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(base_demand, (int, float)), "base_demand must be a float"
        assert isinstance(
            demand_pattern, (type(None), str, PatternRegistry.DefaultPattern, Pattern)
        ), "demand_pattern must be a string or Pattern"
        assert isinstance(elevation, (int, float)), "elevation must be a float"
        assert isinstance(coordinates, (type(None), (tuple, list,))), "coordinates must be a tuple"
        assert isinstance(demand_category, (type(None), str)), "demand_category must be a string"
        assert isinstance(emitter_coeff, (type(None), int, float)), "emitter_coeff must be a float"
        assert isinstance(initial_quality, (type(None), int, float)), "initial_quality must be a float"

        base_demand = float(base_demand)
        elevation = float(elevation)

        junction = Junction(name, self)
        junction.elevation = elevation
        junction.add_demand(base_demand, demand_pattern, demand_category)
        self[name] = junction
        if coordinates is not None:
            junction.coordinates = coordinates
        if emitter_coeff is not None:
            junction.emitter_coefficient = emitter_coeff
        if initial_quality is not None:
            junction.initial_quality = initial_quality

    def add_tank(
        self,
        name,
        elevation=0.0,
        init_level=3.048,
        min_level=0.0,
        max_level=6.096,
        diameter=15.24,
        min_vol=0.0,
        vol_curve=None,
        overflow=False,
        coordinates=None,
    ):
        """
        Adds a tank to the water network model.

        Parameters
        -------------------
        name : str
            Name of the tank.
        elevation : float
            Elevation at the tank.
        init_level : float
            Initial tank level.
        min_level : float
            Minimum tank level.
        max_level : float
            Maximum tank level.
        diameter : float
            Tank diameter of a cylindrical tank (only used when the volume 
            curve is None)
        min_vol : float
            Minimum tank volume (only used when the volume curve is None)
        vol_curve : str, optional
            Name of a volume curve. The volume curve overrides the tank diameter
            and minimum volume.
        overflow : bool, optional
            Overflow indicator (Always False for the WNTRSimulator)
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
            
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(elevation, (int, float)), "elevation must be a float"
        assert isinstance(init_level, (int, float)), "init_level must be a float"
        assert isinstance(min_level, (int, float)), "min_level must be a float"
        assert isinstance(max_level, (int, float)), "max_level must be a float"
        assert isinstance(diameter, (int, float)), "diameter must be a float"
        assert isinstance(min_vol, (int, float)), "min_vol must be a float"
        assert isinstance(vol_curve, (type(None), str)), "vol_curve must be a string"
        assert isinstance(overflow, (type(None), str, bool, int)), "overflow must be a bool, 'YES' or 'NO, or 0 or 1"
        assert isinstance(coordinates, (type(None), (tuple,list,))), "coordinates must be a tuple"
        
        elevation = float(elevation)
        init_level = float(init_level)
        min_level = float(min_level)
        max_level = float(max_level)
        diameter = float(diameter)
        min_vol = float(min_vol)
        if init_level < min_level:
            raise ValueError("Initial tank level must be greater than or equal to the tank minimum level.")
        if init_level > max_level:
            raise ValueError("Initial tank level must be less than or equal to the tank maximum level.")
        if vol_curve is not None and vol_curve != "*":
            if not isinstance(vol_curve, six.string_types):
                raise ValueError("Volume curve name must be a string")
            elif not vol_curve in self._curve_reg.volume_curve_names:
                raise ValueError(
                    "The volume curve "
                    + vol_curve
                    + " is not one of the curves in the "
                    + "list of volume curves. Valid volume curves are:"
                    + str(self._curve_reg.volume_curve_names)
                )
            vcurve = np.array(self._curve_reg[vol_curve].points)
            if min_level < vcurve[0, 0]:
                raise ValueError(
                    (
                        "The volume curve "
                        + vol_curve
                        + " has a minimum value ({0:5.2f}) \n"
                        + 'greater than the minimum level for tank "'
                        + name
                        + '" ({1:5.2f})\n'
                        + "please correct the user input."
                    ).format(vcurve[0, 0], min_level)
                )
            elif max_level > vcurve[-1, 0]:
                raise ValueError(
                    (
                        "The volume curve "
                        + vol_curve
                        + " has a maximum value ({0:5.2f}) \n"
                        + 'less than the maximum level for tank "'
                        + name
                        + '" ({1:5.2f})\n'
                        + "please correct the user input."
                    ).format(vcurve[-1, 0], max_level)
                )

        tank = Tank(name, self)
        tank.elevation = elevation
        tank.init_level = init_level
        tank.min_level = min_level
        tank.max_level = max_level
        tank.diameter = diameter
        tank.min_vol = min_vol
        tank.vol_curve_name = vol_curve
        tank.overflow = overflow
        self[name] = tank
        if coordinates is not None:
            tank.coordinates = coordinates

    def add_reservoir(self, name, base_head=0.0, head_pattern=None, coordinates=None):
        """
        Adds a reservoir to the water network model.

        Parameters
        ----------
        name : str
            Name of the reservoir.
        base_head : float, optional
            Base head at the reservoir.
        head_pattern : str, optional
            Name of the head pattern.
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(base_head, (int, float)), "base_head must be float"
        assert isinstance(head_pattern, (type(None), str)), "head_pattern must be a string"
        assert isinstance(coordinates, (type(None), (tuple, list))), "coordinates must be a tuple"

        base_head = float(base_head)

        reservoir = Reservoir(name, self)
        reservoir.base_head = base_head
        reservoir.head_pattern_name = head_pattern
        self[name] = reservoir
        if coordinates is not None:
            reservoir.coordinates = coordinates

    @property
    def junction_names(self):
        """List of names of all junctions"""
        return self._junctions

    @property
    def tank_names(self):
        """List of names of all junctions"""
        return self._tanks

    @property
    def reservoir_names(self):
        """List of names of all junctions"""
        return self._reservoirs

    def junctions(self):
        """Generator to get all junctions
        
        Yields
        ------
        name : str
            The name of the junction
        node : Junction
            The junction object    
            
        """
        for node_name in self._junctions:
            yield node_name, self._data[node_name]

    def tanks(self):
        """Generator to get all tanks
        
        Yields
        ------
        name : str
            The name of the tank
        node : Tank
            The tank object    
            
        """
        for node_name in self._tanks:
            yield node_name, self._data[node_name]

    def reservoirs(self):
        """Generator to get all reservoirs
        
        Yields
        ------
        name : str
            The name of the reservoir
        node : Reservoir
            The reservoir object    
            
        """
        for node_name in self._reservoirs:
            yield node_name, self._data[node_name]


class LinkRegistry(Registry):
    """A registry for links."""

    __subsets = [
        "_pipes",
        "_pumps",
        "_head_pumps",
        "_power_pumps",
        "_prvs",
        "_psvs",
        "_pbvs",
        "_tcvs",
        "_fcvs",
        "_gpvs",
        "_valves",
    ]

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

    def _finalize_(self, model):
        super()._finalize_(model)
        self._link_reg = None

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise ValueError("Registry keys must be strings")
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
                raise RuntimeError(
                    "cannot remove %s %s, still used by %s", self.__class__.__name__, key, self._usage[key]
                )
            elif key in self._usage:
                self._usage.pop(key)
            link = self._data.pop(key)
            self._node_reg.remove_usage(link.start_node_name, (link.name, link.link_type))
            self._node_reg.remove_usage(link.end_node_name, (link.name, link.link_type))
            if isinstance(link, GPValve):
                self._curve_reg.remove_usage(link.headloss_curve_name, (link.name, "Valve"))
            if isinstance(link, Pump):
                self._curve_reg.remove_usage(link.speed_pattern_name, (link.name, "Pump"))
            if isinstance(link, HeadPump):
                self._curve_reg.remove_usage(link.pump_curve_name, (link.name, "Pump"))
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
        if link_type == None:
            for name, node in self._data.items():
                yield name, node
        elif link_type == Pipe:
            for name in self._pipes:
                yield name, self._data[name]
        elif link_type == Pump:
            for name in self._pumps:
                yield name, self._data[name]
        elif link_type == Valve:
            for name in self._valves:
                yield name, self._data[name]
        else:
            raise RuntimeError("link_type, " + str(link_type) + ", not recognized.")

    def add_pipe(
        self,
        name,
        start_node_name,
        end_node_name,
        length=304.8,
        diameter=0.3048,
        roughness=100,
        minor_loss=0.0,
        initial_status="OPEN",
        check_valve=False,
    ):
        """
        Adds a pipe to the water network model.

        Parameters
        ----------
        name : str
            Name of the pipe.
        start_node_name : str
             Name of the start node.
        end_node_name : str
             Name of the end node.
        length : float, optional
            Length of the pipe.
        diameter : float, optional
            Diameter of the pipe.
        roughness : float, optional
            Pipe roughness coefficient.
        minor_loss : float, optional
            Pipe minor loss coefficient.
        initial_status : str, optional
            Pipe initial status. Options are 'OPEN' or 'CLOSED'.
        check_valve : bool, optional
            True if the pipe has a check valve.
            False if the pipe does not have a check valve.
        
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(" ") == -1
        ), "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(" ") == -1
        ), "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(length, (int, float)), "length must be a float"
        assert isinstance(diameter, (int, float)), "diameter must be a float"
        assert isinstance(roughness, (int, float)), "roughness must be a float"
        assert isinstance(minor_loss, (int, float)), "minor_loss must be a float"
        assert isinstance(initial_status, (int, str, LinkStatus)), "initial_status must be an int, string or LinkStatus"
        assert isinstance(check_valve, (str, int, bool)), "check_valve must be a Boolean"
        check_valve = bool(int(check_valve))
        
        length = float(length)
        diameter = float(diameter)
        roughness = float(roughness)
        minor_loss = float(minor_loss)
        if isinstance(initial_status, str):
            initial_status = LinkStatus[initial_status]

        pipe = Pipe(name, start_node_name, end_node_name, self)
        pipe.length = length
        pipe.diameter = diameter
        pipe.roughness = roughness
        pipe.minor_loss = minor_loss
        pipe.initial_status = initial_status
        pipe._user_status = initial_status
        pipe.check_valve = check_valve
        self[name] = pipe

    def add_pump(
        self,
        name,
        start_node_name,
        end_node_name,
        pump_type="POWER",
        pump_parameter=50.0,
        speed=1.0,
        pattern=None,
        initial_status="OPEN",
    ):
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
        pump_parameter : float or string
            For a POWER pump, the pump power (float).
            For a HEAD pump, the head curve name (string).
        speed: float
            Relative speed setting (1.0 is normal speed)
        pattern: string
            Name of the speed pattern
        initial_status: str or LinkStatus
            Pump initial status. Options are 'OPEN' or 'CLOSED'.
        
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(" ") == -1
        ), "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(" ") == -1
        ), "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(pump_type, str), "pump_type must be a string"
        assert isinstance(pump_parameter, (int, float, str)), "pump_parameter must be a float or string"
        assert isinstance(speed, (int, float)), "speed must be a float"
        assert isinstance(pattern, (type(None), str)), "pattern must be a string"
        assert isinstance(initial_status, (int, str, LinkStatus)), "initial_status must be an int, string or LinkStatus"

        if isinstance(initial_status, str):
            initial_status = LinkStatus[initial_status]
        if pump_type.upper() == "POWER":
            pump = PowerPump(name, start_node_name, end_node_name, self)
            pump.power = pump_parameter
        elif pump_type.upper() == "HEAD":
            pump = HeadPump(name, start_node_name, end_node_name, self)
            pump.pump_curve_name = pump_parameter
        else:
            raise ValueError('pump_type must be "POWER" or "HEAD"')
        pump.base_speed = speed
        pump.initial_status = initial_status
        pump.speed_pattern_name = pattern
        self[name] = pump

    def add_valve(
        self,
        name,
        start_node_name,
        end_node_name,
        diameter=0.3048,
        valve_type="PRV",
        minor_loss=0.0,
        initial_setting=0.0,
        initial_status="ACTIVE",
    ):
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
            Type of valve. Options are 'PRV', 'PSV', 'PBV', 'FCV', 'TCV', and 'GPV'
        minor_loss : float, optional
            Pipe minor loss coefficient.
        initial_setting : float or string, optional
            Valve initial setting.
            Pressure setting for PRV, PSV, or PBV. 
            Flow setting for FCV. 
            Loss coefficient for TCV.
            Name of headloss curve for GPV.
        initial_status: string or LinkStatus
            Valve initial status. Options are 'OPEN',  'CLOSED', or 'ACTIVE'
            
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(" ") == -1
        ), "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(" ") == -1
        ), "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(diameter, (int, float)), "diameter must be a float"
        assert isinstance(valve_type, str), "valve_type must be a string"
        assert isinstance(minor_loss, (int, float)), "minor_loss must be a float"
        assert isinstance(initial_setting, (int, float, str)), "initial_setting must be a float or string"
        assert isinstance(initial_status, (str, LinkStatus)), "initial_status must be a string or LinkStatus"

        if isinstance(initial_status, str):
            initial_status = LinkStatus[initial_status]
        start_node = self._node_reg[start_node_name]
        end_node = self._node_reg[end_node_name]

        valve_type = valve_type.upper()

        # A PRV, PSV or FCV cannot be directly connected to a reservoir or tank (use a length of pipe to separate the two)
        if valve_type in ["PRV", "PSV", "FCV"]:
            if type(start_node) == Tank or type(end_node) == Tank:
                msg = (
                    "%ss cannot be directly connected to a tank.  Add a pipe to separate the valve from the tank."
                    % valve_type
                )
                logger.error(msg)
                raise RuntimeError(msg)
            if type(start_node) == Reservoir or type(end_node) == Reservoir:
                msg = (
                    "%ss cannot be directly connected to a reservoir.  Add a pipe to separate the valve from the reservoir."
                    % valve_type
                )
                logger.error(msg)
                raise RuntimeError(msg)

        # TODO check the following: PRVs cannot share the same downstream node or be linked in series

        # TODO check the following: Two PSVs cannot share the same upstream node or be linked in series

        # TODO check the following: A PSV cannot be connected to the downstream node of a PRV

        if valve_type == "PRV":
            valve = PRValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == "PSV":
            valve = PSValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == "PBV":
            valve = PBValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == "FCV":
            valve = FCValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == "TCV":
            valve = TCValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == "GPV":
            valve = GPValve(name, start_node_name, end_node_name, self)
            valve.headloss_curve_name = initial_setting
        valve.initial_status = initial_status
        valve.diameter = diameter
        valve.minor_loss = minor_loss
        self[name] = valve

    def check_valves(self):
        """Generator to get all pipes with check valves
        
        Yields
        ------
        name : str
            The name of the pipe
        link : Pipe
            The pipe object    
            
        """
        for name in self._pipes:
            if self._data[name].check_valve:
                yield name

    @property
    def pipe_names(self):
        """A list of all pipe names"""
        return self._pipes

    @property
    def valve_names(self):
        """A list of all valve names"""
        return self._valves

    @property
    def pump_names(self):
        """A list of all pump names"""
        return self._pumps

    @property
    def head_pump_names(self):
        """A list of all head pump names"""
        return self._head_pumps

    @property
    def power_pump_names(self):
        """A list of all power pump names"""
        return self._power_pumps

    @property
    def prv_names(self):
        """A list of all prv names"""
        return self._prvs

    @property
    def psv_names(self):
        """A list of all psv names"""
        return self._psvs

    @property
    def pbv_names(self):
        """A list of all pbv names"""
        return self._pbvs

    @property
    def tcv_names(self):
        """A list of all tcv names"""
        return self._tcvs

    @property
    def fcv_names(self):
        """A list of all fcv names"""
        return self._fcvs

    @property
    def gpv_names(self):
        """A list of all gpv names"""
        return self._gpvs

    def pipes(self):
        """Generator to get all pipes
        
        Yields
        ------
        name : str
            The name of the pipe
        link : Pipe
            The pipe object    
            
        """
        for name in self._pipes:
            yield name, self._data[name]

    def pumps(self):
        """Generator to get all pumps
        
        Yields
        ------
        name : str
            The name of the pump
        link : Pump
            The pump object    
            
        """
        for name in self._pumps:
            yield name, self._data[name]

    def valves(self):
        """Generator to get all valves
        
        Yields
        ------
        name : str
            The name of the valve
        link : Valve
            The valve object    
            
        """
        for name in self._valves:
            yield name, self._data[name]

    def head_pumps(self):
        """Generator to get all head pumps
        
        Yields
        ------
        name : str
            The name of the pump
        link : HeadPump
            The pump object    
            
        """
        for name in self._head_pumps:
            yield name, self._data[name]

    def power_pumps(self):
        """Generator to get all power pumps
        
        Yields
        ------
        name : str
            The name of the pump
        link : PowerPump
            The pump object    
            
        """
        for name in self._power_pumps:
            yield name, self._data[name]

    def prvs(self):
        """Generator to get all PRVs
        
        Yields
        ------
        name : str
            The name of the valve
        link : PRValve
            The valve object
            
        """
        for name in self._prvs:
            yield name, self._data[name]

    def psvs(self):
        """Generator to get all PSVs
        
        Yields
        ------
        name : str
            The name of the valve
        link : PSValve
            The valve object
            
        """
        for name in self._psvs:
            yield name, self._data[name]

    def pbvs(self):
        """Generator to get all PBVs
        
        Yields
        ------
        name : str
            The name of the valve
        link : PBValve
            The valve object
            
        """
        for name in self._pbvs:
            yield name, self._data[name]

    def tcvs(self):
        """Generator to get all TCVs
        
        Yields
        ------
        name : str
            The name of the valve
        link : TCValve
            The valve object
            
        """
        for name in self._tcvs:
            yield name, self._data[name]

    def fcvs(self):
        """Generator to get all FCVs
        
        Yields
        ------
        name : str
            The name of the valve
        link : FCValve
            The valve object
            
        """
        for name in self._fcvs:
            yield name, self._data[name]

    def gpvs(self):
        """Generator to get all GPVs
        
        Yields
        ------
        name : str
            The name of the valve
        link : GPValve
            The valve object
            
        """
        for name in self._gpvs:
            yield name, self._data[name]

