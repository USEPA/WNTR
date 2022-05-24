"""
The wntr.network.model module includes methods to build a water network
model.

.. rubric:: Contents

.. autosummary::

    WaterNetworkModel
    PatternRegistry
    CurveRegistry
    SourceRegistry
    NodeRegistry
    LinkRegistry

"""
from ctypes import ArgumentError
from functools import partial
from itertools import combinations
from lib2to3.pytree import BasePattern
import logging
from collections import OrderedDict
from copy import deepcopy
import os
from tkinter import E
from typing import Iterable, Type
import warnings
import pyproj
import requests
import urllib

from wntr.utils.constants import *

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from shapely.geometry.linestring import LineString
import six
from tqdm.contrib.concurrent import process_map
# from tqdm import tqdm
from tqdm.auto import tqdm
import wntr.epanet
import wntr.network.io
from wntr.utils.ordered_set import OrderedSet

from .base import AbstractModel, Link, LinkStatus, Node, Registry
from .controls import Control, Rule
from .elements import (Curve, Demands, FCValve, GPValve, HeadPump, Junction,
                       Pattern, PBValve, Pipe, PowerPump, PRValve, PSValve,
                       Pump, Reservoir, Source, Tank, TCValve, TimeSeries,
                       Valve)
from .options import Options


logger = logging.getLogger(__name__)
 
def get_pipe_hyd(links, g):
    dists = links.distance(g)
    if dists.min() < 100:
        return dists.argmin()
    else:
        return None

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

        self._options = Options()
        self._node_reg = NodeRegistry(self)
        self._link_reg = LinkRegistry(self)
        self._pattern_reg = PatternRegistry(self)
        self._curve_reg = CurveRegistry(self)
        self._controls = OrderedDict()
        self._sources = SourceRegistry(self)

        self._node_reg._finalize_(self)
        self._link_reg._finalize_(self)
        self._pattern_reg._finalize_(self)
        self._curve_reg._finalize_(self)
        self._sources._finalize_(self)

        # NetworkX Graph to store the pipe connectivity and node coordinates

        self._labels = None
        self._nodes_gis = None
        self._links_gis = None
        self._junctions_pressure_zone = {}

        self._inpfile = None
        if inp_file_name:
            self.read_inpfile(inp_file_name)
            
        # To be deleted and/or renamed and/or moved
        # Time parameters
        self.sim_time = 0.0
        self._prev_sim_time = None  # the last time at which results were accepted
    
    def _compare(self, other):
        """
        Parameters
        ----------
        other: WaterNetworkModel

        Returns
        -------
        bool
        """
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
        return self._shifted_time % (24*3600)

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
    def nodes_gis(self) -> gpd.GeoDataFrame:
        return self._nodes_gis
    @nodes_gis.setter
    def nodes_gis(self, value):
        self._nodes_gis = value

    @property
    def links_gis(self) -> gpd.GeoDataFrame:
        return self._links_gis
    @links_gis.setter
    def links_gis(self, value):
        self._links_gis = value

    @property
    def hydrants_gis(self) -> gpd.GeoDataFrame:
        return self._hydrants_gis
    
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
        Adds a junction to the water network model

        Parameters
        -------------------
        name : string
            Name of the junction.
        base_demand : float
            Base demand at the junction.
        demand_pattern : string or Pattern
            Name of the demand pattern or the Pattern object
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
                 min_vol=0.0, vol_curve=None, overflow=False, coordinates=None):
        """
        Adds a tank to the water network model

        Parameters
        -------------------
        name : string
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
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
            
        """
        self._node_reg.add_tank(name, elevation, init_level, min_level, 
                                max_level, diameter, min_vol, vol_curve, 
                                overflow, coordinates)

    def add_reservoir(self, name, base_head=0.0, head_pattern=None, coordinates=None):
        """
        Adds a reservoir to the water network model

        Parameters
        ----------
        name : string
            Name of the reservoir.
        base_head : float, optional
            Base head at the reservoir.
        head_pattern : string, optional
            Name of the head pattern.
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        
        """
        self._node_reg.add_reservoir(name, base_head, head_pattern, coordinates)

    def add_pipe(self, name, start_node_name, end_node_name, length=304.8,
                 diameter=0.3048, roughness=100, minor_loss=0.0, initial_status='OPEN', 
                 check_valve=False, vertices=None):
        """
        Adds a pipe to the water network model

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
        initial_status : string or LinkStatus, optional
            Pipe initial status. Options are 'OPEN' or 'CLOSED'.
        check_valve : bool, optional
            True if the pipe has a check valve.
            False if the pipe does not have a check valve.
        
        """
        self._link_reg.add_pipe(name, start_node_name, end_node_name, length, 
                                diameter, roughness, minor_loss, initial_status, 
                                check_valve)

        if vertices is not None:
            self.get_link(name).vertices = vertices

        if self._links_gis is not None:
            pipe_gis = self._epanet_links_to_gis([name])
            self._links_gis.loc[name] = pipe_gis.loc[name]
            if self._gis_pzone is not None:
                try:
                    in_pz = self._gis_pzone.contains(self._links_gis.loc[name].geometry)
                    pz = self._gis_pzone.loc[in_pz].NAME.values[0]
                    self._links_gis.loc[name, 'pzone'] = pz
                except IndexError:
                    pass

    def add_pump(self, name, start_node_name, end_node_name, pump_type='POWER',
                 pump_parameter=50.0, speed=1.0, pattern=None, initial_status='OPEN'):
        """
        Adds a pump to the water network model

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
            For a POWER pump, the pump power.
            For a HEAD pump, the head curve name.
        speed: float
            Relative speed setting (1.0 is normal speed)
        pattern: string
            Name of the speed pattern
        initial_status : string or LinkStatus
            Pump initial status. Options are 'OPEN' or 'CLOSED'.
        
        """
        self._link_reg.add_pump(name, start_node_name, end_node_name, pump_type, 
                                pump_parameter, speed, pattern, initial_status)
    
    def add_valve(self, name, start_node_name, end_node_name,
                 diameter=0.3048, valve_type='PRV', minor_loss=0.0, 
                 initial_setting=0.0, initial_status='ACTIVE'):
        """
        Adds a valve to the water network model

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
            Valve initial status. Options are 'OPEN',  'CLOSED', or 'ACTIVE'.
        """
        self._link_reg.add_valve(name, start_node_name, end_node_name, diameter, 
                                 valve_type, minor_loss, initial_setting, initial_status)

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
        Adds a curve to the water network model

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
        Adds a source to the water network model

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
        self._pattern_reg.add_usage(source.strength_timeseries.pattern_name, (source.name, 'Source'))
        self._node_reg.add_usage(source.node_name, (source.name, 'Source'))

    def add_control(self, name, control_object):
        """
        Adds a control or rule to the water network model

        Parameters
        ----------
        name : string
           control object name.
        control_object : Control or Rule
            Control or Rule object.
        """
        if name in self._controls:
            raise ValueError('The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control.')
        self._controls[name] = control_object
    
    ### # 
    ### Remove elements from the model
    def remove_node(self, name, with_control=False, force=False):
        """Removes a node from the water network model"""
        node = self.get_node(name)
        if not force:
            if with_control:
                x=[]
                for control_name, control in self._controls.items():
                    if node in control.requires():
                        logger.warning(control._control_type_str()+' '+control_name+' is being removed along with node '+name)
                        x.append(control_name)
                for i in x:
                    self.remove_control(i)
                if self._nodes_gis is not None:
                    self._nodes_gis = self._nodes_gis.drop(index=name)
            else:
                used_controls = []
                for control_name, control in self._controls.items():
                    if node in control.requires():
                        used_controls.append(control_name)
                if len(used_controls) > 0:
                    raise RuntimeError('Cannot remove node {0} without first removing controls/rules {1}'.format(name, used_controls))
                if self._nodes_gis is not None:
                    self._nodes_gis = self._nodes_gis.drop(index=name)
        self._node_reg.__delitem__(name)

    def remove_link(self, name, with_control=False, force=False):
        """Removes a link from the water network model"""
        link = self.get_link(name)
        if not force:
            if with_control:
                x=[]
                for control_name, control in self._controls.items():
                    if link in control.requires():
                        logger.warning(control._control_type_str()+' '+control_name+' is being removed along with link '+name)
                        x.append(control_name)
                for i in x:
                    self.remove_control(i)
                if self._links_gis is not None:
                    self._links_gis = self._links_gis.drop(index=name)
            else:
                used_controls = []
                for control_name, control in self._controls.items():
                    if link in control.requires():
                        used_controls.append(control_name)
                if len(used_controls) > 0:
                    raise RuntimeError('Cannot remove link {0} without first removing controls/rules {1}'.format(name, used_controls))
                if self._links_gis is not None:
                    self._links_gis = self._links_gis.drop(index=name)
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
        name : string
           The name of the source object to be removed
        """
        logger.warning('You are deleting a source. This could have unintended \
            side effects. If you are replacing values, use get_source(name) \
            and modify it instead.')
        source = self._sources[name]
        self._pattern_reg.remove_usage(source.strength_timeseries.pattern_name, (source.name, 'Source'))
        self._node_reg.remove_usage(source.node_name, (source.name, 'Source'))            
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
    def get_node(self, name) -> Node: 
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
    def potential_hydrant_name_list(self):
        """Get a list of names of hydrants in GIS
        
        Returns
        -------
        list of strings
        
        """
        return list(self._hydrants_gis.index)

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
        
        d = {'Nodes': self.num_nodes,
             'Links': self.num_links,
             'Patterns': self.num_patterns,
             'Curves': self.num_curves,
             'Sources': self.num_sources,
             'Controls': self.num_controls}
        
        if level >= 1:
            d['Nodes'] = {
                    'Junctions': self.num_junctions,
                    'Tanks': self.num_tanks,
                    'Reservoirs': self.num_reservoirs}
            d['Links'] = {
                    'Pipes': self.num_pipes,
                    'Pumps': self.num_pumps,
                    'Valves': self.num_valves}
            d['Curves'] = {
                    'Pump': len(self._curve_reg._pump_curves), 
                    'Efficiency': len(self._curve_reg._efficiency_curves),  
                    'Headloss': len(self._curve_reg._headloss_curves), 
                    'Volume': len(self._curve_reg._volume_curves)}
            
        if level >= 2:
            d['Links']['Pumps'] = {
                    'Head': len(list(self.head_pumps())),
                    'Power': len(list(self.power_pumps()))}
            d['Links']['Valves'] = {
                    'PRV': len(list(self.prvs())),
                    'PSV': len(list(self.psvs())),
                    'PBV': len(list(self.pbvs())),
                    'TCV': len(list(self.tcvs())),
                    'FCV': len(list(self.fcvs())),
                    'GPV': len(list(self.gpvs()))}
                
        return d
    
    def to_dict(self):
        """Dictionary representation of the WaterNetworkModel.
        
        Returns
        -------
        dict
            Dictionary representation of the WaterNetworkModel
        """
        return wntr.network.io.to_dict(self)

    def from_dict(self, d: dict):
        """
        Append the model with elements from a water network model dictionary.

        Parameters
        ----------
        d : dict
            dictionary representation of the water network model to append to existing model
        """
        wntr.network.io.from_dict(d, append=self)

    def write_json(self, f, **kw_json):
        """
        Write the WaterNetworkModel to a JSON file

        Parameters
        ----------
        f : str
            Name of the file or file pointer
        kw_json : keyword arguments
            arguments to pass directly to `json.dump`
        """
        wntr.network.io.write_json(self, f, **kw_json)
    
    def read_json(self, f, **kw_json):
        """
        Create a WaterNetworkModel from a JSON file.

        Parameters
        ----------
        f : str
            Name of the file or file pointer
        kw_json : keyword arguments
            keyword arguments to pass to `json.load`

        Returns
        -------
        WaterNetworkModel
        """
        return wntr.network.io.read_json(f, append=self, **kw_json)

    def get_graph(self, node_weight=None, link_weight=None, modify_direction=False):
        """
        Returns a networkx MultiDiGraph of the water network model
        
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
        G = nx.MultiDiGraph()
        
        for name, node in self.nodes():
            G.add_node(name)
            nx.set_node_attributes(G, name='pos', values={name: node.coordinates})
            nx.set_node_attributes(G, name='type', values={name: node.node_type})
            
            if node_weight is not None:
                try: # weight nodes
                    value = node_weight[name]
                    nx.set_node_attributes(G, name='weight', values={name: value})
                except:
                    pass
            
        for name, link in self.links():
            start_node = link.start_node_name
            end_node = link.end_node_name
            G.add_edge(start_node, end_node, key=name)
            nx.set_edge_attributes(G, name='type', 
                        values={(start_node, end_node, name): link.link_type})
                
            if link_weight is not None:
                try: # weight links
                    value = link_weight[name]
                    if modify_direction and value < 0: # change the direction of the link and value
                        G.remove_edge(start_node, end_node, name)
                        G.add_edge(end_node, start_node, name)
                        nx.set_edge_attributes(G, name='type', 
                                values={(end_node, start_node, name): link.link_type})
                        nx.set_edge_attributes(G, name='weight', 
                                values={(end_node, start_node, name): -value})
                    else:
                        nx.set_edge_attributes(G, name='weight', 
                            values={(start_node, end_node, name): value})
                except:
                    pass
            
        return G
    
    def assign_demand(self, demand, pattern_prefix='ResetDemand'):
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
        demand : pandas DataFrame
            A pandas DataFrame containing demands (index = time, columns = junction names)

        pattern_prefix: string
            Pattern name prefix, default = 'ResetDemand'.  The junction name is 
            appended to the prefix to create a new pattern name.  
            If the pattern name already exists, an error is thrown and the user 
            should use a different pattern prefix name.
        """
        for junc_name in demand.columns:
            
            # Extract the node demand pattern and resample to match the pattern timestep
            demand_pattern = demand.loc[:, junc_name]
            demand_pattern.index = pd.TimedeltaIndex(demand_pattern.index, 's')
            resample_offset = str(int(self.options.time.pattern_timestep))+'S'
            demand_pattern = demand_pattern.resample(resample_offset).mean() / self.options.hydraulic.demand_multiplier

            # Add the pattern
            # If the pattern name already exists, this fails 
            pattern_name = pattern_prefix + junc_name
            self.add_pattern(pattern_name, demand_pattern.tolist())
            
            # Reset base demand
            junction = self.get_node(junc_name)
            junction.demand_timeseries_list.clear()
            junction.demand_timeseries_list.append((1.0, pattern_name))

    def get_links_for_node(self, node_name, flag='ALL'):
        """
        Returns a list of links connected to a node

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
        link_data = self._node_reg.get_usage(node_name)
        if link_data is None:
            return []
        else:
            if flag.upper() == 'ALL':
                return [link_name for link_name, link_type in link_data if link_type in link_types and node_name in {self.get_link(link_name).start_node_name, self.get_link(link_name).end_node_name}]
            elif flag.upper() == 'INLET':
                return [link_name for link_name, link_type in link_data if link_type in link_types and node_name == self.get_link(link_name).end_node_name]
            elif flag.upper() == 'OUTLET':
                return [link_name for link_name, link_type in link_data if link_type in link_types and node_name == self.get_link(link_name).start_node_name]
            else:
                logger.error('Unrecognized flag: {0}'.format(flag))
                raise ValueError('Unrecognized flag: {0}'.format(flag))

    def query_node_attribute(self, attribute, operation=None, value=None, node_type=None):
        """
        Query node attributes, for example get all nodes with elevation <= threshold

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
        A pandas Series that contains the attribute that satisfies the
        operation threshold for a given node_type.

        Notes
        -----
        If operation and value are both None, the Series will contain the attributes
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
        A pandas Series that contains the attribute that satisfies the
        operation threshold for a given link_type.

        Notes
        -----
        If operation and value are both None, the Series will contain the attributes
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
                self.add_control(name.replace(' ', '_')+'_Rule', rule)
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
            node._head = node.init_level+node.elevation
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
    
    def read_inpfile(self, filename):
        """
        Defines water network model components from an EPANET INP file

        Parameters
        ----------
        filename : string
            Name of the INP file.

        """
        return wntr.network.io.read_inpfile(filename, append=self)

    def write_inpfile(self, filename, units=None, version=2.2, force_coordinates=False):
        """
        Writes the current water network model to an EPANET INP file

        .. note::

            By default, WNTR now uses EPANET version 2.2 for the EPANET simulator engine. Thus,
            The WaterNetworkModel will also write an EPANET 2.2 formatted INP file by default as well.
            Because the PDD analysis options will break EPANET 2.0, the ``version`` option will allow
            the user to force EPANET 2.0 compatibility at the expense of pressured-dependent analysis 
            options being turned off.


        Parameters
        ----------
        filename : string
            Name of the inp file.

        units : str, int or FlowUnits
            Name of the units being written to the inp file.

        version : float, {2.0, **2.2**}
            Optionally specify forcing EPANET 2.0 compatibility.

        force_coordinates : bool
            This only applies if `self.options.graphics.map_filename` is not `None`,
            and will force the COORDINATES section to be written even if a MAP file is
            provided. False by default, but coordinates **are** written by default since
            the MAP file is `None` by default.

        """
        wntr.network.io.write_inpfile(self, filename, units=units, version=version, force_coordinates=force_coordinates)

    def parse_hydrants_from_gis(self, hydrants_layer: gpd.GeoDataFrame=None, 
            hyd_branch_line_layer: gpd.GeoDataFrame=None, add_all_to_network=False, 
            hyd_juncs_gis: str=None, parallel=True) -> None:
        """Create GIS layers with hydrants and junctions where hydrant branch lines are connected to and keep them ready to be added to model one by one or in batch.

        Parameters
        ----------
        hydrants_layer : gpd.GeoDataFrame, optional
            GIS hydrant layer, by default None
        hyd_branch_line_layer : gpd.GeoDataFrame, optional
            GIS branch line layer (linestrings), by default None
        add_all_to_network : bool, optional
            Wether to add all hydrants to model, by default False
        hyd_juncs_gis : str, optional
            Location of model hydrants and model hydrant branch line junction shapefiles, by default None
        parallel : bool, optional
            Whether to match branch lines to pipes in parallel or in serial, by default True

        Returns
        -------
        None
            None

        Raises
        ------
        RuntimeError
            GIS has not been initialized
        """

        if self.links_gis is None:
            raise RuntimeError('GIS not initialized. Call wn.create_model_gis(<crs>) where "crs" is a coordinate reference system.')

        # Reproject hydrants and branch lines if needed.
        if self.links_gis.crs != hyd_branch_line_layer.crs:
            hyd_branch_line_layer.to_crs(self.links_gis.crs, inplace=True)
            hydrants_layer.to_crs(self.links_gis.crs, inplace=True)

        self._hyd_branch_line = hyd_branch_line_layer.set_index('EAMID')

        if hyd_juncs_gis is not None and os.path.isfile(hyd_juncs_gis + '_hyds.shp'):
            # If model GIS layer for hydrants and hydrant junctions exist, load them.
            self._hydrants_gis = gpd.read_file(hyd_juncs_gis + '_hyds.shp')
            self._hydrants_gis = self._hydrants_gis.set_index('EAMID')
            self._hyd_juncs_gis = gpd.read_file(hyd_juncs_gis + '_hyd_juncs.shp')
            self._hyd_juncs_gis = self._hyd_juncs_gis.set_index('EAMID_hyd')
        else:
            # Pair hydrants with branch lines
            hyds_to_branch = hyd_branch_line_layer.sjoin(hydrants_layer, lsuffix='bran', rsuffix='hyd')
            hyds_to_branch = hyds_to_branch.drop(columns=['index_hyd'])

            # Add "_dup" to the end of duplicated hydrants' EAMIDs
            dup_hyds = hydrants_layer.EAMID.duplicated(keep='first')
            if dup_hyds.sum() > 0:
                hydrants_layer.loc[dup_hyds, 'EAMID'] = hydrants_layer[dup_hyds].EAMID.apply(lambda x: x + '_dup').values
            self._hydrants_gis = hydrants_layer.set_index('EAMID')

            def get_branch_end(b):
                """Get coordinates of branch line connection to main.

                Args:
                    b (shapely.geometry.LineString): Branch line geometry

                Returns:
                    tuple: coordinates.
                """
                try:
                    start = b.geometry[0].coords[0]
                    end = b.geometry[-1].coords[-1]
                except TypeError as e:
                    start = b.geometry.coords[0]
                    end = b.geometry.coords[-1]

                choose_start = b.geometry.project(self._hydrants_gis.loc[b.EAMID_hyd].geometry) > 0.1

                return start if choose_start else end

            # Create hydrant junction layer based on branch line connection to main.
            new_hydrants_coords = np.array(
                [np.array(get_branch_end(l)) for _, l in hyds_to_branch.iterrows()]
            ).T
            hyd_coords = gpd.points_from_xy(
                new_hydrants_coords[0],
                new_hydrants_coords[1],
                crs=hyd_branch_line_layer.crs
            )
            new_hydrants = gpd.GeoDataFrame(
                data=hyds_to_branch[['EAMID_hyd', 'EAMID_bran']],
                geometry=hyd_coords, crs=hyd_branch_line_layer.crs
            )
            self._hyd_juncs_gis = new_hydrants.set_index('EAMID_hyd')

            # Add to hydrant layer the ID of pipe the branch line is connected to.
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                if parallel:
                    get_pipe_hyd_partial = partial(get_pipe_hyd, self.links_gis)
                    pipes_to_hyds = process_map(get_pipe_hyd_partial, self._hyd_juncs_gis.geometry, chunksize=50)
                else:
                    pipes_to_hyds = [get_pipe_hyd(self.links_gis, g) for g in self._hyd_juncs_gis.geometry]
            
            self._hyd_juncs_gis['pipe_id'] = [self._links_gis.index[p] if p else None for p in pipes_to_hyds]
            
            # Save new hydrant and branch line GIS.
            if hyd_juncs_gis is not None:
                self._hydrants_gis.to_file(hyd_juncs_gis + '_hyds.shp')
                self._hyd_juncs_gis.to_file(hyd_juncs_gis + '_hyd_juncs.shp')

        # Create dictionary of hydrants connected to pipes
        self._pipe_basis_dict = {pid: [pid] for pid in self._hyd_juncs_gis.pipe_id.values if pid is not None}

        if add_all_to_network:
            # Add all hydrants to model, if user so desires.
            print('Adding all hydrants to model')
            for ix, hyd in tqdm(self._hyd_juncs_gis.iterrows(), total=len(self._hyd_juncs_gis)):
                if hyd.pipe_id is not None:
                    self.add_hydrant_to_pipe(ix)

        return 

    def add_hydrant_to_pipe(self, hydrant_id: str, branch_id: str=None, pipe_id: str=None, hydrant_height=0.6) -> None:
        """Adds one hydrant from the model's GIS to the network. Model's GIS needs to be initialized first and hydrants parsed.

        Parameters
        ----------
        hydrant_id : str
            Hydrant id in the original shapefile
        branch_id : str, optional
            Hydrant id branch line in the original shapefile, by default None
        pipe_id : _type_, optional
            ID of pipe to which the hydrant is connected in the original shapefile, by default None
        hydrant_height : float, optional
            Height of the hydrant, by default 0.6

        Raises
        ------
        RuntimeError
            There is no column named "DIAMETER" in the branch line shapefile
        """

        if 'DIAMETER' not in self._hyd_branch_line.columns:
            raise RuntimeError('Hydrant branch lines must have a field called "DIAMETER."')

        hyd = self._hyd_juncs_gis.loc[hydrant_id]
        if pipe_id is None:
            pipe_id = hyd.pipe_id
        if branch_id is None:
            branch_id = hyd.EAMID_bran
        hydrant_intersect_point = hyd.geometry

        potential_pipes_hyd = self._links_gis.loc[self._pipe_basis_dict[pipe_id]]
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            pipe_ix = potential_pipes_hyd.distance(hydrant_intersect_point).argmin()
        updated_pipe_id = potential_pipes_hyd.iloc[pipe_ix].name
            
        # Figure out how far into the main the lateral is placed
        pipe_line = self._links_gis.loc[updated_pipe_id].geometry
        dist_to_split = self._links_gis.loc[updated_pipe_id].geometry.project(hydrant_intersect_point)
        split_at_point = dist_to_split / pipe_line.length

        lateral_junc = None
        if split_at_point == 0.:
            # If hydrant at upstream junction
            lateral_junc = self.get_link(pipe_id).start_node.name
        elif split_at_point == 1.:
            # If hydrant at downstream junction
            lateral_junc = self.get_link(pipe_id).end_node.name
        else:
            # Create new pipe ID that does not yet exist in model
            pipe_id_new = pipe_id + '_2'
            count = 1
            while pipe_id_new in self.pipe_name_list:
                count += 1
                pipe_id_new = f'{pipe_id}_{count}'

            self._pipe_basis_dict[pipe_id].append(pipe_id_new)

            # Create junction for hydrant lateral
            lateral_junc = hydrant_id + '_junc'
            wntr.morph.link.split_pipe(self, updated_pipe_id, pipe_id_new, lateral_junc, 
                split_at_point=split_at_point, return_copy=False)

            new_links_gis = self._epanet_links_to_gis([updated_pipe_id, pipe_id_new])
            self._links_gis.drop(index=updated_pipe_id, inplace=True)
            self._links_gis = gpd.GeoDataFrame(pd.concat((self._links_gis, new_links_gis)))

        # Add hydrant
        x, y = self._hydrants_gis.loc[hydrant_id].geometry.coords.xy
        self.add_junction(hydrant_id, coordinates=(x[0], y[0]), 
            elevation=self.get_node(lateral_junc).elevation + hydrant_height)

        # Add lateral
        bline = self._hyd_branch_line.loc[branch_id]
        self.add_pipe(branch_id, lateral_junc, hydrant_id, length=bline.geometry.length, 
            diameter=bline.DIAMETER * IN_TO_FT * FT_TO_M)

        return

    def create_model_gis(self, crs: pyproj.crs.crs.CRS=None, pressure_zone_layer: gpd.GeoDataFrame=None, assign_missing_elevation: bool=True) -> None:
        """Initializes the model's GIS with the coordinates specified in the EPANET file and either a specified coordinate system or the same coordinate system of the pressure zones shapefile, if the latter is passed to the function.

        Parameters
        ----------
        crs : pyproj.crs.crs.CRS, optional
            Projection of the coordinates in the EPANET file, by default None
        pressure_zone_layer : gpd.GeoDataFrame, optional
            Shapefile with the pressure zones as polygons, by default None

        Returns
        -------
        None
            None

        Raises
        ------
        Exception
            Either "crs" or "pressure_zone_layer" must be provided.
        Exception
            If "pressure_zone_layer" is provided its crs will be used, so do not pass a "crs.
        """

        self._results = None
        self._demands_pzone = None
        self._date = None
        self._gis_pzone = None
        self._crs = crs

        if (crs is None) and (pressure_zone_layer is not None):
            self._gis_pzone = pressure_zone_layer
            self._crs = self._gis_pzone.crs
        elif (crs is None) and (pressure_zone_layer is None):
            raise Exception('Either "crs" or "pressure_zone_layer" must be provided.')
        elif (crs is not None) and (pressure_zone_layer is not None):
            raise Exception('If "pressure_zone_layer" is provided its crs will be used, so do not pass a "crs."')

        # Create gis of nodes from EPANET
        coords_raw = np.array(
            [self.nodes[n].coordinates for n in self.nodes]
        ).T
        nodes_points = gpd.points_from_xy(
            coords_raw[0],
            coords_raw[1]
        )

        self._nodes_gis = gpd.GeoDataFrame(
            data=[n for n in self.nodes],
            geometry=nodes_points, crs=self._crs.srs
        ).set_index(0)
        self._nodes_gis.index.name = 'name'

        # Add pattern names to nodes
        def get_pattern(node):
            junc = self.get_node(node.name)
            if junc.node_type == 'Junction':
                pattern = self.get_node(
                    node.name).demand_timeseries_list[0].pattern_name
            else:
                pattern = ''
            return pattern  # colors[pattern]
        self._nodes_gis['pattern'] = self._nodes_gis.apply(get_pattern, axis=1)
        self._nodes_gis['elevation'] = 0
        self._nodes_gis['elevation'] = self.query_node_attribute('elevation', np.greater, 0)
        if assign_missing_elevation:
            self.assign_elevation()

        # Create gis of pipes from EPANET
        link_names = self.link_name_list
        self._links_gis = self._epanet_links_to_gis(link_names)

        # Set pressure zones
        if pressure_zone_layer is not None:
            self._assign_pressure_zones()

            self._all_dmas = self._nodes_gis.pzone.unique()
            self._all_dmas = np.delete(self._all_dmas, self._all_dmas==None) # Remove None DMA

            # Set original demand multiplier for each DMA
            self._dma_demand_multipliers = {dma: 1. for dma in self._all_dmas}

    def _epanet_links_to_gis(self, link_names: Iterable[str]) -> gpd.GeoDataFrame:
        """Convert the vertex coordinates of links in the EPANET file model to GeoPandas GIS. 

        Parameters
        ----------
        link_names : Iterable[str]
            IDs of links to be added to the model's GIS

        Returns
        -------
        GeoPandas.GeoDataFrame
            GeoDataFrame of links
        """
        link_geometry = []
        for link_name in link_names:
            # Transform link vertices in the EPANET model into LineStrings
            link = self.get_link(link_name)
            coords = [self.nodes[link.start_node].coordinates]
            coords += link.vertices
            coords += [self.nodes[link.end_node].coordinates]
            link_geometry.append(LineString(coords))

        # Create final GeoDataFrame
        links_gis = gpd.GeoDataFrame(
            data=link_names,
            geometry=link_geometry, crs=self._crs.srs).set_index(0)
        links_gis.index.name = 'name'

        # Add to the GeoDataFrame start and end nodes of each link
        for link in link_names:
            l = self.get_link(link)
            links_gis.loc[link, 'start_node'] = l.start_node_name
            links_gis.loc[link, 'end_node'] = l.end_node_name

        return links_gis

    def assign_highest_diameter_link(self) -> None:
        """Registers in each node the diameter of the largest pipe connected to it.
        """
        for link_name in self.link_name_list:
            link = self.get_link(link_name)
            if link.link_type == 'Pipe':
                start_node_name = link.start_node_name
                end_node_name = link.end_node_name
                start_diameter = self.get_node(start_node_name).highest_link_diameter 
                end_diameter = self.get_node(end_node_name).highest_link_diameter 

                self.get_node(start_node_name).highest_link_diameter = link.diameter if start_diameter is None else max(start_diameter, link.diameter)
                self.get_node(end_node_name).highest_link_diameter = link.diameter if end_diameter is None else max(end_diameter, link.diameter)

    def _assign_pressure_zones(self) -> None:
        """Assign pressure zone to nodes in EPANET GIS.
        """
        self._nodes_gis['pzone'] = None
        for ix, pz in self._gis_pzone.iterrows():
            # Assign pressure zone to nodes
            in_pz = self._nodes_gis.geometry.within(pz.geometry)
            self._nodes_gis.loc[in_pz, 'pzone'] = pz.NAME
            for n in self._nodes_gis.loc[in_pz].index:
                self.get_node(n).pressure_zone = pz.NAME

            self._junctions_pressure_zone[pz.NAME] = list(in_pz[in_pz].index)

            # Assign pressure zone to links
            in_pz = self._links_gis.geometry.within(pz.geometry)
            self._links_gis.loc[in_pz, 'pzone'] = pz.NAME
            for n in self._links_gis.loc[in_pz].index:
                self.get_link(n).pressure_zone = pz.NAME

        return

    def update_base_demands_dict(self, new_demands_junctions: dict=None, 
            all_junctions_demand_mult: float=None, 
            dma_demand_mult: dict=None, units='GPM') -> None:
        """Apply either new demands or a DMA-based multiplier to all nodes in
        the network.

        Parameters
        ----------
        new_demands_junctions : dict, optional
            Keys as nodes and values as demands, by default None
        all_junctions_demand_mult : float, optional
            Demand multiplier for all nodes and values as demand multipliers, by default None
        dma_demand_mult : dict, optional
            Demand multiplier for all nodes within DMAs, by default None
        units : str, optional
            Flow units, by default 'GPM'

        Raises
        ------
        ArgumentError
            No input is passed.
        """

        assert (units == 'GPM') or (units == 'CMS')

        # If DMA demands are passed and junction demand dictionary is not 
        # provided, create with multiplied demands for all nodes within each DMA.
        unit_mult = 1. if units == 'CMS' else CMS_TO_GPM
        if new_demands_junctions is not None:
            for k, v in new_demands_junctions.items():
                try:
                    self.get_node(k).demand_timeseries_list[0].base_value = v / unit_mult
                except AttributeError as e:
                    print(
                        f'Could not attribute demand of {v} to node {k} of ' +
                        'type {self.get_node(k).node_type}')
        elif all_junctions_demand_mult is not None:
            for k in self.junction_name_list:
                self.get_node(k).demand_timeseries_list[0].base_value *= \
                    all_junctions_demand_mult
        elif dma_demand_mult is not None:
            for k in self.junction_name_list:
                self.get_node(k).demand_timeseries_list[0].base_value *= dma_demand_mult[self._nodes_gis[k]]
        else:
            raise ArgumentError('Either new_demands_junctions, new_demands_dmas, all_junctions_demand_mult, or dma_demand_mult must be provided.')

        return

    def _elevation_function(self, df, url, lat_column, lon_column) -> None:
        """Query service using lat, lon and add the elevation values to nodes DataFrame as a new column.

        Parameters
        ----------
        df : _type_
            _description_
        url : _type_
            _description_
        lat_column : _type_
            _description_
        lon_column : _type_
            _description_
        """

        elevations = []
        for lat, lon in zip(df[lat_column], df[lon_column]):

            # define rest query params
            params = {
                'output': 'json',
                'x': lon,
                'y': lat,
                'units': 'Meters'
            }

            # format query string and return query value
            result = requests.get((url + urllib.parse.urlencode(params)))
            elevations.append(result.json()['USGS_Elevation_Point_Query_Service']['Elevation_Query']['Elevation'])

        df['elev_meters'] = elevations

        return

    def assign_elevation(self):  
        """Assigns an elevation to nodes with zero elevation.
        """

        # USGS Elevation Point Query Service
        url = r'https://nationalmap.gov/epqs/pqs.php?'

        nodes_nad83 = self.nodes_gis.to_crs('epsg:4269')

        nodes_no_elev = [j for j in self.junction_name_list if self.get_node(j).elevation < 1e-6]
        for junc in nodes_no_elev:
            lat, lon = nodes_nad83.loc[junc].geometry.coords.xy
            # define rest query params
            params = {
                'output': 'json',
                'y': lon[0],
                'x': lat[0],
                'units': 'Meters'
            }

            # format query string and return query value
            result = requests.get((url + urllib.parse.urlencode(params)))
            # elevations.append(result.json()['USGS_Elevation_Point_Query_Service']['Elevation_Query']['Elevation'])
            elev = result.json()['USGS_Elevation_Point_Query_Service']['Elevation_Query']['Elevation']
            if elev > 0:
                self.get_node(junc).elevation = elev
                print(f'Assigned elevation of {elev:.2f} ({elev / 0.3048:.2f} ft) to junction {junc}.')
                self._nodes_gis.loc[junc, 'elevation'] = elev
            else:
                print(f'Unable to assign elevation to junction {junc}.')

    def paths_through_open_links(self, source: str, target: str, links_to_remove: Iterable[str], 
            flow_for_direction: pd.Series=None, max_paths_to_return=200):
        """Find paths from source node to target node through links with flow. To check if there 
            are open paths between pressure zones, remove PRVs, pumps, and pipes with zero flows.

        Parameters
        ----------
        source : str
            Source node
        target : str
            Target node
        links_to_remove : Iterable[str]
            Links to consider closed.
        flow_for_direction : pd.Series, optional
            Use flow for directed graph to speed things up, by default None
        max_paths_to_return : int, optional
            Number of shortest paths to report, by default 200

        Returns
        -------
        Tuple with list and generator
            List with first *max_paths_to_return* paths and generator for others
        """

        if flow_for_direction is None:
            g_raw = self.get_graph()
        else:
            g_raw = self.get_graph(link_weight=flow_for_direction, modify_direction=True)

        for link in links_to_remove:
            try:
                g_raw.remove_edge(self.get_link(link).start_node_name, self.get_link(link).end_node_name)
            except nx.exception.NetworkXError:
                pass
        
        # TODO: ADD POSSIBILITY OF PATHS BEING DEPENDENT ON FLOW DIRECTION SO THAT USER CAN MORE EASILY FIND OUT WHERE WATER IS GOING.
        g = nx.Graph(g_raw)

        paths = []
        paths_gen = nx.shortest_simple_paths(g, source, target)
        
        for i in range(max_paths_to_return):
            try:
                nodes = next(paths_gen)
                paths.append(self.nodes_to_links(nodes))
            except StopIteration as e:
                print(F'Maximum number of shortest paths reached at {i}.')
                break

        return paths, paths_gen

    def nodes_to_links(self, nodes):
        """Converts path of nodes into path of links.

        Parameters
        ----------
        nodes : list of str
            List with nodes in the path

        Returns
        -------
        list of str
            List with links in the path
        """

        links = []
        for i in range(len(nodes) - 1):
            link = self.links_gis.loc[(self.links_gis.start_node == nodes[i]) & (self.links_gis.end_node == nodes[i + 1])]
            if len(link) > 0:
                links += list(link.index)
            else:
                link = self.links_gis.loc[(self.links_gis.start_node == nodes[i + 1]) & (self.links_gis.end_node == nodes[i])]
                links += list(link.index)
        
        return links

    def estimate_losses(self, service_lines_shp: gpd.GeoDataFrame, results: pd.DataFrame):
        """Estimate unnavoidable annual real losses (URAL) using IWA's formula.

        Parameters
        ----------
        service_lines_shp : gpd.GeoDataFrame
            Shapefile with service lines
        results : pd.DataFrame
            WNTR simulation

        Returns
        -------
        dictionary
            Leaks by pressure zone and system-wide in gallons.

        Raises
        ------
        RuntimeError
            GIS not initialized.
        """

        #TODO: MOVE TO METRICS

        if self._links_gis is None:
            raise RuntimeError('GIS not initialized.')

        self._service_lines = service_lines_shp

        losses_pressure_zones = {'pressure_zone': [], 'leak_est': []}
        if self._gis_pzone is not None:
            for pz in self._nodes_gis.pzone.unique():
                if pz is not None:
                    links = self._links_gis.loc[self._links_gis.pzone == pz]
                    service_lines = gpd.sjoin(
                        self._service_lines, 
                        self._gis_pzone.loc[self._gis_pzone.NAME == pz], 
                        op='intersects'
                    )

                    losses = self._loss_estimate(results, links, service_lines)
                    losses_pressure_zones['pressure_zone'].append(pz) 
                    losses_pressure_zones['leak_est'].append(losses)

            return pd.DataFrame.from_dict(losses_pressure_zones).set_index('pressure_zone')
        else:
            return pd.DataFrame(
                data=[self._loss_estimate(
                    results, 
                    self._links_gis, 
                    self._service_lines
                )], 
                columns=('system-wide',)
            )

    def _loss_estimate(self, results: pd.DataFrame, links: gpd.GeoDataFrame, 
            service_lines: gpd.GeoDataFrame) -> float:
        """Used the IWA's formula to calculate the unnavoidable annual real water losses.

        Parameters
        ----------
        results : pd.DataFrame
            WNTR simulation results
        links : gpd.GeoDataFrame
            Links GIS
        service_lines : gpd.GeoDataFrame
            Service lines GIS

        Returns
        -------
        float
            Losses in gallons.
        """

        #TODO: REMOVE MAGIC NUMBERS
        length_mains = links.geometry.apply(lambda x: x.length).sum() / 1000
        n_connections = len(service_lines)
        length_serv_line = service_lines.geometry.apply(lambda x: x.length).sum() / 1000
        ave_press = results.node['pressure'].mean()
        ave_press = ave_press.loc[ave_press > 0].mean()
        losses = (6.57 * length_mains + 0.256 * n_connections + 9.13 * length_serv_line) * ave_press / 3.79

        return losses

    def fix_overlapping_links_and_nodes(self, with_control=False) -> None:
        #TODO: DOCUMENT THIS FUNCTION
        self.fix_overlapping_junctions(with_control=with_control)
        self.fix_overlapping_pipes(with_control=with_control)

    def fix_overlapping_pipes(self, with_control=False) -> None:
        #TODO: DOCUMENT THIS FUNCTION
        if self._links_gis is None:
            raise RuntimeError('GIS must be initialized for overlapping lines to be removed. Run wn.create_model_gis(<crs>).')

        links_gis_buff = deepcopy(self._links_gis)
        links_gis_buff['geometry'] = links_gis_buff.geometry.buffer(JUNC_PIPE_OVERLAY_THRESHOLD)
        def get_overlap(x): 
            return [ix for ix, v in gpd.clip(self._links_gis, x.geometry).length.items() if v > 1]
        tqdm.pandas(desc="Progress")
        links_in_buffer = links_gis_buff.progress_apply(get_overlap, axis=1)
        potentially_dupplicated = links_in_buffer.apply(lambda x: len(x) > 1)
        potentially_dupplicated = potentially_dupplicated.loc[potentially_dupplicated].index

        graph = self.get_graph().to_undirected()
        dead_ends = [k for k, v in graph.degree() if (v == 1) and (k in self.junction_name_list)]

        print('Potentially duplicated pipes as dead ends')
        dup_dead_ends = []
        for pipe_id in potentially_dupplicated:
            pipe = self.get_link(pipe_id)
            if (pipe.start_node_name in dead_ends) or (pipe.end_node_name in dead_ends):
                dup_dead_ends.append(pipe_id)

        merged_pipes = self._merge_overlapping_dead_ends(links_gis_buff, dead_ends, dup_dead_ends)

        artificial_dead_ends = set(dup_dead_ends) - set(merged_pipes)
        
        self.remove_orphan_nodes(with_control=with_control)

    def remove_orphan_nodes(self, with_control=False) -> None:
        """Remove orphan nodes

        Parameters
        ----------
        with_control : bool, optional
            Remove controls associated with orphan nodes, by default False
        """
        graph = self.get_graph().to_undirected()
        for on in nx.isolates(graph):
            self.remove_node(on, with_control=with_control)

        return

    def _merge_overlapping_dead_ends(self, links_gis_buff, dead_ends, dup_dead_ends) -> list:
        #TODO: DOCUMENT THIS FUNCTION
        merged_pipes = []
        for pipe1, pipe2 in combinations(dup_dead_ends, 2):
            if len(links_gis_buff.loc[[pipe1]].overlay(links_gis_buff.loc[[pipe2]], how='intersection')) > 0:
                p1 = self.get_link(pipe1)
                p2 = self.get_link(pipe2)

                base_pipe = p1 if p1.length > p2.length else p2

                p1_start_node_name = p1.start_node_name
                p2_start_node_name = p2.start_node_name

                new_start_node_name = p1_start_node_name if p1_start_node_name not in dead_ends else p1.end_node_name
                new_end_node_name = p2_start_node_name if p2_start_node_name not in dead_ends else p2.end_node_name

                vertices = [] 
                vertices += p1.vertices if new_start_node_name == p1_start_node_name else p1.vertices[::-1] 
                vertices += p2.vertices[::-1] if new_end_node_name == p2_start_node_name else p2.vertices  #TODO: REVERSE AND MERGE VERTICES AS DEPENDING ON START AND END NODES.

                new_pipe_name=base_pipe.name
                new_pipe_start_node_name=new_start_node_name
                new_pipe_end_node_name=new_end_node_name
                new_pipe_diameter=base_pipe.diameter
                new_pipe_roughness=base_pipe.roughness
                new_pipe_initial_status=base_pipe.initial_status
                new_pipe_check_valve=base_pipe.check_valve

                self.remove_link(p1.name)
                self.remove_link(p2.name)

                self.add_pipe(
                    name=new_pipe_name, 
                    start_node_name=new_pipe_start_node_name, 
                    end_node_name=new_pipe_end_node_name, 
                    diameter=new_pipe_diameter, 
                    roughness=new_pipe_roughness, 
                    initial_status=new_pipe_initial_status, 
                    check_valve=new_pipe_check_valve,
                    vertices=vertices
                )

                self.get_link(base_pipe.name).length = self._links_gis.loc[[base_pipe.name]].length.values[0] * FT_TO_M

                print(f'Pipes {pipe1} and {pipe2} were merged for being overlapping dead ends.')

                merged_pipes += [pipe1, pipe2]

        return merged_pipes

    def fix_overlapping_junctions(self, with_control=False) -> None:
        #TODO: DOCUMENT THIS FUNCTION
        juncs_buff = self._nodes_gis.buffer(JUNC_PIPE_OVERLAY_THRESHOLD)
        juncs_buff = gpd.GeoDataFrame(geometry=juncs_buff)
        
        juncs_sjoin = gpd.sjoin(self._nodes_gis, juncs_buff)
        unique, count = np.unique(juncs_sjoin.index, return_counts=True)
        overlapping_juncs = [j for j in unique[count > 1] if '-' not in j]

        for junc in overlapping_juncs:
            keep = []
            remove = []
            for j in juncs_sjoin.loc[junc].index_right:
                if j in self.junction_name_list:
                    if self.get_node(j).base_demand > 0:
                        keep.append(j)
                    else:
                        remove.append(j)
            if len(keep) > 1:
                raise RuntimeError('Overlapping junctions with demands found. Solution to dealing with those not yet implemented.')
            elif len(keep) == 1:
                for j in remove:
                    links_dup_start = self.query_link_attribute('start_node_name', lambda x, y: x == y, j)
                    for l in links_dup_start.index:
                        if self.get_link(l).link_type == 'Pipe':
                            self._fix_duplicate_junction(l, start_node_name=keep[0])
                        else:
                            print(f'Link {l} is connected to nodes with overlaps but since it is not a pipe it cannot be fixed.')

                    links_dup_end = self.query_link_attribute('end_node_name', lambda x, y: x == y, j)
                    for l in links_dup_end.index:
                        if self.get_link(l).link_type == 'Pipe':
                            self._fix_duplicate_junction(l, end_node_name=keep[0])
                        else:
                            print(f'Link {l} is connected to nodes with overlaps but since it is not a pipe it cannot be fixed.')
                for j in remove:
                    self.remove_node(j, with_control=with_control)
                    print(f'None {j} removed as duplicate.')
            else:
                pass

    def _fix_duplicate_junction(self, l: str, start_node_name: str=None, 
            end_node_name: str=None) -> None:
        """Fixes a duplicate junction by deleting a pipe connecting to the
        duplicate junction and recreating it connecting to the correct junction.

        Parameters
        ----------
        l : str
            Link ID
        start_node_name : str, optional
            Junction to be kept, if at the start of the link, by default None
        end_node_name : str, optional
            Junction to be kept, if at the end of the link, by default None
        """
        
        name=self.get_link(l).name
        start_node_name=start_node_name if start_node_name is not None else self.get_link(l).start_node_name
        end_node_name=end_node_name if end_node_name is not None else self.get_link(l).end_node_name
        length=self.get_link(l).length
        diameter=self.get_link(l).diameter
        roughness=self.get_link(l).roughness
        minor_loss=self.get_link(l).minor_loss
        initial_status=self.get_link(l).initial_status
        check_valve=self.get_link(l).check_valve
        vertices=self.get_link(l).vertices

        if start_node_name == end_node_name:
            junc = self.get_node(end_node_name)
            end_node_name  += '_2'
            self.add_junction(
                end_node_name, 
                elevation=junc.elevation, 
                coordinates=junc.coordinates
            )
            self.add_pipe(start_node_name + '_ghost', start_node_name, 
                end_node_name, length=0.1, diameter=4, roughness=200)
                            
        self.remove_link(l)
        self.add_pipe(
            name=name,
            start_node_name=start_node_name,
            end_node_name=end_node_name,
            length=length,
            diameter=diameter,
            roughness=roughness,
            minor_loss=minor_loss,
            initial_status=initial_status,
            check_valve=check_valve,
        )
        self.get_link(l).vertices = vertices

    def find_disconnected_subnetworks(self, delete_small_subnetworks=False, n_nodes_del_threshold=10):
        graph = self.get_graph().to_undirected()
        sub_networks = [{'graph': graph.subgraph(c), 'nodes': None} for c in nx.connected_components(graph)]
        for sub_graph in sub_networks:
            sub_graph['nodes'] = sub_graph['graph'].nodes

            if delete_small_subnetworks and sub_graph['graph'].number_of_nodes() < n_nodes_del_threshold:
                for n in sub_graph['nodes']:
                    links_with_node = list(self.query_link_attribute('start_node_name', lambda x, y: x == y, n).index)
                    links_with_node += list(self.query_link_attribute('end_node_name', lambda x, y: x == y, n).index)

                    for link in links_with_node:
                        self.remove_link(link)
                    self.remove_node(n)

        return sub_networks

    @property
    def junctions_pressure_zone(self):
        return self._junctions_pressure_zone


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
            return str(self._options.hydraulic.pattern) if self._options.hydraulic.pattern is not None else ''
        
        def __repr__(self):
            return 'DefaultPattern()'
        
        @property
        def name(self):
            """The name of the default pattern, or ``None`` if no pattern is assigned"""
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
        assert isinstance(name, str) and len(name) < 32 and name.find(' ') == -1, "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(pattern, (list, np.ndarray, Pattern)), "pattern must be a list or Pattern"
                          
        if not isinstance(pattern, Pattern):
            pattern = Pattern(name, multipliers=pattern, time_options=self._options.time)            
        else: #elif pattern.time_options is None:
            pattern.time_options = self._options.time
        if pattern.name in self._data.keys():
            raise ValueError('Pattern name already exists')
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
            raise ValueError('Registry keys must be strings')
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
        assert isinstance(name, str) and len(name) < 32 and name.find(' ') == -1, "name must be a string with less than 32 characters and contain no spaces"
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
        untyped = defined.difference(self._pump_curves, self._efficiency_curves, 
                                     self._headloss_curves, self._volume_curves)
        for key in untyped:
            yield key, self._data[key]

    @property    
    def untyped_curve_names(self):
        """List of names of all curves without types"""
        defined = set(self._data.keys())
        untyped = defined.difference(self._pump_curves, self._efficiency_curves, 
                                     self._headloss_curves, self._volume_curves)
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
                raise RuntimeError('cannot remove %s %s, still used by %s'%( 
                                   self.__class__.__name__,
                                   key,
                                   self._usage[key]))
            elif key in self._usage:
                self._usage.pop(key)
            source = self._data.pop(key)
            self._pattern_reg.remove_usage(source.strength_timeseries.pattern_name, (source.name, 'Source'))
            self._node_reg.remove_usage(source.node_name, (source.name, 'Source'))            
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
                        self._curve_reg.remove_usage(pat_name, (node.name, 'Junction'))
            if isinstance(node, Reservoir) and node.head_pattern_name:
                self._curve_reg.remove_usage(node.head_pattern_name, (node.name, 'Reservoir'))
            if isinstance(node, Tank) and node.vol_curve_name:
                self._curve_reg.remove_usage(node.vol_curve_name, (node.name, 'Tank'))
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
                     elevation=0.0, coordinates=None, demand_category=None,
                     emitter_coeff=None, initial_quality=None):
        """
        Adds a junction to the water network model.

        Parameters
        -------------------
        name : string
            Name of the junction.
        base_demand : float
            Base demand at the junction.
        demand_pattern : string or Pattern
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
        assert isinstance(name, str) and len(name) < 32 and name.find(' ') == -1, "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(base_demand, (int, float)), "base_demand must be a float"
        assert isinstance(demand_pattern, (type(None), str, PatternRegistry.DefaultPattern, Pattern)), "demand_pattern must be a string or Pattern"
        assert isinstance(elevation, (int, float)), "elevation must be a float"
        assert isinstance(coordinates, (type(None), (tuple,list,))), "coordinates must be a tuple"
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

    def add_tank(self, name, elevation=0.0, init_level=3.048,
                 min_level=0.0, max_level=6.096, diameter=15.24,
                 min_vol=0.0, vol_curve=None, overflow=False, 
                 coordinates=None):
        """
        Adds a tank to the water network model.

        Parameters
        -------------------
        name : string
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
        vol_curve : string, optional
            Name of a volume curve. The volume curve overrides the tank diameter
            and minimum volume.
        overflow : bool, optional
            Overflow indicator (Always False for the WNTRSimulator)
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
            
        """
        assert isinstance(name, str) and len(name) < 32 and name.find(' ') == -1, "name must be a string with less than 32 characters and contain no spaces"
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
        if vol_curve is not None and vol_curve != '*':
            if not isinstance(vol_curve, six.string_types):
                raise ValueError('Volume curve name must be a string')
            elif not vol_curve in self._curve_reg.volume_curve_names:
                raise ValueError('The volume curve ' + vol_curve + ' is not one of the curves in the ' +
                                 'list of volume curves. Valid volume curves are:' + 
                                 str(self._curve_reg.volume_curve_names))
            vcurve = np.array(self._curve_reg[vol_curve].points)
            if min_level < vcurve[0,0]:
                raise ValueError(('The volume curve ' + vol_curve + ' has a minimum value ({0:5.2f}) \n' +
                                 'greater than the minimum level for tank "' + name + '" ({1:5.2f})\n' +
                                 'please correct the user input.').format(vcurve[0,0],min_level))
            elif max_level > vcurve[-1,0]:
                raise ValueError(('The volume curve ' + vol_curve + ' has a maximum value ({0:5.2f}) \n' +
                                 'less than the maximum level for tank "' + name + '" ({1:5.2f})\n' +
                                 'please correct the user input.').format(vcurve[-1,0],max_level))

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
        name : string
            Name of the reservoir.
        base_head : float, optional
            Base head at the reservoir.
        head_pattern : string, optional
            Name of the head pattern.
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        
        """
        assert isinstance(name, str) and len(name) < 32 and name.find(' ') == -1, "name must be a string with less than 32 characters and contain no spaces"
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
    
    def _finalize_(self, model):
        super()._finalize_(model)
        self._link_reg = None

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
            self._node_reg.remove_usage(link.start_node_name, (link.name, link.link_type))
            self._node_reg.remove_usage(link.end_node_name, (link.name, link.link_type))
            if isinstance(link, GPValve):
                self._curve_reg.remove_usage(link.headloss_curve_name, (link.name, 'Valve'))
            if isinstance(link, Pump):
                self._curve_reg.remove_usage(link.speed_pattern_name, (link.name, 'Pump'))
            if isinstance(link, HeadPump):
                self._curve_reg.remove_usage(link.pump_curve_name, (link.name, 'Pump'))
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
                 diameter=0.3048, roughness=100, minor_loss=0.0, initial_status='OPEN', check_valve=False):
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
        initial_status : string, optional
            Pipe initial status. Options are 'OPEN' or 'CLOSED'.
        check_valve : bool, optional
            True if the pipe has a check valve.
            False if the pipe does not have a check valve.
        
        """
        assert isinstance(name, str) and len(name) < 32 and name.find(' ') == -1, "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(' ') == -1, "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(' ') == -1, "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(length, (int, float)), "length must be a float"
        assert isinstance(diameter, (int, float)), "diameter must be a float"
        assert isinstance(roughness, (int, float)), "roughness must be a float"
        assert isinstance(minor_loss, (int, float)), "minor_loss must be a float"
        assert isinstance(initial_status, (str, LinkStatus)), "initial_status must be a string or LinkStatus"
        assert isinstance(check_valve, bool), "check_valve must be a Boolean"
        
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

    def add_pump(self, name, start_node_name, end_node_name, pump_type='POWER',
                 pump_parameter=50.0, speed=1.0, pattern=None, initial_status='OPEN'):
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
        assert isinstance(name, str) and len(name) < 32 and name.find(' ') == -1, "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(' ') == -1, "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(' ') == -1, "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(pump_type, str), "pump_type must be a string"
        assert isinstance(pump_parameter, (int, float, str)), "pump_parameter must be a float or string"
        assert isinstance(speed, (int, float)), "speed must be a float"
        assert isinstance(pattern, (type(None), str)), "pattern must be a string"
        assert isinstance(initial_status, (str, LinkStatus)), "initial_status must be a string or LinkStatus"
        
        if isinstance(initial_status, str):
            initial_status = LinkStatus[initial_status]
        if pump_type.upper() == 'POWER':
            pump = PowerPump(name, start_node_name, end_node_name, self)
            pump.power = pump_parameter
        elif pump_type.upper() == 'HEAD':
            pump = HeadPump(name, start_node_name, end_node_name, self)
            pump.pump_curve_name = pump_parameter
        else:
            raise ValueError('pump_type must be "POWER" or "HEAD"')
        pump.base_speed = speed
        pump.initial_status = initial_status
        pump.speed_pattern_name = pattern
        self[name] = pump
    
    def add_valve(self, name, start_node_name, end_node_name,
                 diameter=0.3048, valve_type='PRV', minor_loss=0.0, 
                 initial_setting=0.0, initial_status='ACTIVE'):
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
        assert isinstance(name, str) and len(name) < 32 and name.find(' ') == -1, "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(' ') == -1, "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(' ') == -1, "end_node_name must be a string with less than 32 characters and contain no spaces"
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
        if valve_type in ['PRV', 'PSV', 'FCV']:
            if type(start_node)==Tank or type(end_node)==Tank or type(start_node)==Reservoir or type(end_node)==Reservoir:
                msg = '%ss cannot be directly connected to a tank.  Add a pipe to separate the valve from the tank.' % valve_type
                logger.error(msg)   
                raise RuntimeError(msg)
            if type(start_node)==Reservoir or type(end_node)==Reservoir:
                msg = '%ss cannot be directly connected to a reservoir.  Add a pipe to separate the valve from the reservoir.' % valve_type
                logger.error(msg)   
                raise RuntimeError(msg)
        
        # TODO check the following: PRVs cannot share the same downstream node or be linked in series
            
        # TODO check the following: Two PSVs cannot share the same upstream node or be linked in series
        
        # TODO check the following: A PSV cannot be connected to the downstream node of a PRV
        
        if valve_type == 'PRV':
            valve = PRValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == 'PSV':
            valve = PSValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == 'PBV':
            valve = PBValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == 'FCV':
            valve = FCValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == 'TCV':
            valve = TCValve(name, start_node_name, end_node_name, self)
            valve.initial_setting = initial_setting
            valve._setting = initial_setting
        elif valve_type == 'GPV':
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

