"""
The wntr.network.elements module includes elements of a water network model, 
including junction, tank, reservoir, pipe, pump, valve, pattern, timeseries, 
demands, curves, and sources.
"""
import numpy as np
import sys
import logging
import math
import six
import copy
from scipy.optimize import curve_fit, OptimizeWarning
from warnings import warn
from collections.abc import MutableSequence

from .base import Node, Link, Registry, LinkStatus
from .options import TimeOptions
from wntr.epanet.util import MixType

import warnings
warnings.simplefilter("ignore", OptimizeWarning) # ignore scipy.optimize.OptimizeWarning

logger = logging.getLogger(__name__)


class Junction(Node):
    """
    Junction class, inherited from Node.
    
    Junctions are the nodes that contain demand, emitters, and 
    water quality sources.

    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_junction()` method. 
    Direct creation through the constructor is highly discouraged.

    Parameters
    ----------
    name : string
        Name of the junction.
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        WaterNetworkModel object the junction will belong to


    .. rubric:: Attributes

    .. autosummary:: 

        name
        node_type
        base_demand
        demand_timeseries_list
        elevation
        coordinates
        emitter_coefficient
        initial_quality
        minimum_pressure
        required_pressure
        pressure_exponent
        tag

    .. rubric:: Read-only simulation results

    .. autosummary::

        demand
        head
        pressure
        quality
        leak_demand
        leak_status
        leak_area
        leak_discharge_coeff
    
    """

    # base and optional attributes used to create a Junction in _from_dict
    # base attributes are used in add_junction
    _base_attributes = ["name", 
                        "base_demand",
                        "demand_pattern",
                        "elevation", 
                        "coordinates",
                        "demand_category"]
    _optional_attributes = ["emitter_coefficient",
                            "initial_quality", 
                            "minimum_pressure", 
                            "required_pressure", 
                            "pressure_exponent", 
                            "tag"]

    def __init__(self, name, wn):
        super(Junction, self).__init__(wn, name)
        self._demand_timeseries_list = Demands(self._pattern_reg)
        self._elevation = 0.0
        self._required_pressure = None
        self._minimum_pressure = None
        self._pressure_exponent = None
        self._emitter_coefficient = None
        self._leak = False
        self._leak_status = False
        self._leak_area = 0.0
        self._leak_discharge_coeff = 0.0
        self._leak_start_control_name = 'junction'+self._name+'start_leak_control'
        self._leak_end_control_name = 'junction'+self._name+'end_leak_control'
        
    def __repr__(self):
        return "<Junction '{}', elevation={}, demand_timeseries_list={}>".format(self._name, self.elevation, repr(self.demand_timeseries_list))

    def _compare(self, other):
        if not super(Junction, self)._compare(other):
            return False
        if abs(self.elevation - other.elevation)<1e-9 and \
           self.required_pressure == other.required_pressure and \
           self.minimum_pressure == other.minimum_pressure and \
           self.pressure_exponent == other.pressure_exponent and \
           self.emitter_coefficient == other.emitter_coefficient:
            return True
        return False
    
    @property
    def elevation(self):
        """float : elevation of the junction"""
        return self._elevation
    @elevation.setter
    def elevation(self, value):
        self._elevation = value

    @property
    def demand_timeseries_list(self):
        """Demands : list of demand patterns and base multipliers"""
        return self._demand_timeseries_list
    @demand_timeseries_list.setter
    def demand_timeseries_list(self, value):
        self._demand_timeseries_list = value

    @property
    def required_pressure(self):
        """float: The required pressure attribute is used for pressure-dependent demand
        simulations. This is the lowest pressure at which the junction receives 
        the full requested demand. If set to None, the global value in 
        wn.options.hydraulic.required_pressure is used."""
        return self._required_pressure
    @required_pressure.setter
    def required_pressure(self, value):
        self._required_pressure = value

    @property
    def minimum_pressure(self):
        """float: The minimum pressure attribute is used for pressure-dependent demand 
        simulations. Below this pressure, the junction will not receive any water.
        If set to None, the global value in wn.options.hydraulic.minimum_pressure is used."""
        return self._minimum_pressure
    @minimum_pressure.setter
    def minimum_pressure(self, value):
        self._minimum_pressure = value

    @property
    def pressure_exponent(self):
        """float: The pressure exponent attribute is used for pressure-dependent demand 
        simulations. 
        If set to None, the global value in wn.options.hydraulic.pressure_exponent is used."""
        return self._pressure_exponent
    @pressure_exponent.setter
    def pressure_exponent(self, value):
        self._pressure_exponent = value
        
    @property
    def emitter_coefficient(self):
        """float : if not None, then activate an emitter with the specified coefficient"""
        return self._emitter_coefficient
    @emitter_coefficient.setter
    def emitter_coefficient(self, value):
        self._emitter_coefficient = value

    @property
    def nominal_pressure(self):
        """deprecated - use required pressure"""
        raise DeprecationWarning('The nominal_pressure property has been renamed required_pressure. Please update your code')
    @nominal_pressure.setter
    def nominal_pressure(self, value):
        """deprecated - use required pressure"""
        raise DeprecationWarning('The nominal_pressure property has been renamed required_pressure. Please update your code')

    @property
    def node_type(self):
        """str : ``"Junction"`` (read only)"""
        return 'Junction'

    def add_demand(self, base, pattern_name, category=None):
        """Add a new demand entry to the Junction
        
        Parameters
        ----------
        base : float
            The base demand value for this new entry
        pattern_name : str or None
            The name of the pattern to use or ``None`` for a constant value
        category : str, optional
            A category name for this demand
        
        """
        if pattern_name is not None:
            self._pattern_reg.add_usage(pattern_name, (self.name, 'Junction'))
        self.demand_timeseries_list.append((base, pattern_name, category))

    @property
    def base_demand(self):
        """Get the base_value of the first demand in the demand_timeseries_list.

        This is a read-only property.
        """
        if len(self.demand_timeseries_list) > 0:
            return self.demand_timeseries_list[0].base_value
        return 0.0
    @base_demand.setter
    def base_demand(self, value):
        raise RuntimeWarning('The base_demand property is read-only. Please modify using demand_timeseries_list[0].base_value.')

    @property
    def demand_pattern(self):
        """Get the pattern_name of the first demand in the demand_timeseries_list.

        This is a read-only property.
        """
        if len(self.demand_timeseries_list) > 0:
            return self.demand_timeseries_list[0].pattern_name
        return None
    @demand_pattern.setter
    def demand_pattern(self, value):
        raise RuntimeWarning('The demand_pattern property is read-only. Please modify using demand_timeseries_list[0].pattern_name')
    
    @property
    def demand_category(self):
        """Get the category of the first demand in the demand_timeseries_list.

        This is a read-only property.
        """
        if len(self.demand_timeseries_list) > 0:
            return self.demand_timeseries_list[0].category
        return None
    @demand_category.setter
    def demand_category(self, value):
        raise RuntimeWarning('The demand_category property is read-only. Please modify using demand_timeseries_list[0].category.')
    
    def add_leak(self, wn, area, discharge_coeff=0.75, start_time=None, end_time=None):
        """
        Add a leak control to the water network model
        
        Leaks are modeled by:

        Q = discharge_coeff*area*sqrt(2*g*h)

        where:
           Q is the volumetric flow rate of water out of the leak
           g is the acceleration due to gravity
           h is the gauge head at the junction, P_g/(rho*g); Note that this is not the hydraulic head (P_g + elevation)

        Parameters
        ----------
        wn : :class:`~wntr.network.model.WaterNetworkModel`
           Water network model containing the junction with
           the leak. This information is needed because the
           WaterNetworkModel object stores all controls, including
           when the leak starts and stops.
        area : float
           Area of the leak in m^2.
        discharge_coeff : float
           Leak discharge coefficient; Takes on values between 0 and 1.
        start_time : int
           Start time of the leak in seconds. If the start_time is
           None, it is assumed that an external control will be used
           to start the leak (otherwise, the leak will not start).
        end_time : int
           Time at which the leak is fixed in seconds. If the end_time
           is None, it is assumed that an external control will be
           used to end the leak (otherwise, the leak will not end).

        """
        from wntr.network.controls import ControlAction, Control
        
        self._leak = True
        self._leak_area = area
        self._leak_discharge_coeff = discharge_coeff

        if start_time is not None:
            start_control_action = ControlAction(self, 'leak_status', True)
            control = Control._time_control(wn, start_time, 'SIM_TIME', False, start_control_action)
            wn.add_control(self._leak_start_control_name, control)

        if end_time is not None:
            end_control_action = ControlAction(self, 'leak_status', False)
            control = Control._time_control(wn, end_time, 'SIM_TIME', False, end_control_action)
            wn.add_control(self._leak_end_control_name, control)

    def remove_leak(self,wn):
        """
        Remove a leak control from the water network model

        Parameters
        ----------
        wn : :class:`~wntr.network.model.WaterNetworkModel`
           Water network model
        """
        self._leak = False
        wn._discard_control(self._leak_start_control_name)
        wn._discard_control(self._leak_end_control_name)
        
    def add_fire_fighting_demand(self, wn, fire_flow_demand, fire_start, fire_end, pattern_name=None):
        """Add a new fire flow demand entry to the Junction
        
        Parameters
        ----------
        wn : :class:`~wntr.network.model.WaterNetworkModel`
           Water network model
        fire_flow_demand : float
            Fire flow demand
        fire_start : int
            Start time of the fire flow in seconds. 
        fire_end : int
            End time of the fire flow in seconds. 
        pattern_name : str or None
            Pattern name.  If pattern name is None, the pattern name is assigned to junction name + '_fire'
        """
        if 'Fire_Flow' in self.demand_timeseries_list.category_list():
            raise ValueError('A single junction can not have multiple fire flow demands')

        if pattern_name is None:
            pattern_name = self._name+'_fire'
            
        fire_flow_pattern = Pattern(pattern_name).binary_pattern(pattern_name, 
                                          step_size=wn.options.time.pattern_timestep,
                                          start_time=fire_start,
                                          end_time=fire_end,
                                          duration=wn.options.time.duration)
        wn.add_pattern(pattern_name, fire_flow_pattern)
        self._pattern_reg.add_usage(pattern_name, (self.name, 'Junction'))
        self.demand_timeseries_list.append((fire_flow_demand, fire_flow_pattern, 'Fire_Flow'))

    def remove_fire_fighting_demand(self, wn):
        """Removes a fire flow demand entry to the Junction
        
        Parameters
        ----------
        wn : :class:`~wntr.network.model.WaterNetworkModel`
           Water network model
        """
        if 'Fire_Flow' in self.demand_timeseries_list.category_list():
            pattern_name = self.demand_timeseries_list.pattern_list('Fire_Flow')[0].name
            self._pattern_reg.remove_usage(pattern_name, (self.name, 'Junction'))
            self.demand_timeseries_list.remove_category('Fire_Flow')
            wn.remove_pattern(pattern_name)


class Tank(Node):
    """
    Tank class, inherited from Node.
    
    Tank volume can be defined using a constant diameter or a volume curve. 
    If the tank has a volume curve, the diameter has no effect on hydraulic 
    simulations. 
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_tank()` method. 
    Direct creation through the constructor is highly discouraged.

    Parameters
    ----------
    name : string
        Name of the tank.
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        WaterNetworkModel object the tank will belong to
    

    .. rubric:: Attributes

    .. autosummary::

        name
        node_type
        head
        demand
        elevation
        init_level
        min_level
        max_level
        diameter
        min_vol
        vol_curve_name
        vol_curve
        overflow
        mixing_model
        mixing_fraction
        bulk_coeff
        coordinates
        initial_quality
        tag

    .. rubric:: Read-only simulation results

    .. autosummary::

        head
        level
        pressure
        quality
        leak_demand
        leak_status
        leak_area
        leak_discharge_coeff

    """
    
    # base and optional attributes used to create a Tank in _from_dict
    # base attributes are used in add_tank
    _base_attributes = ["name", 
                        "elevation", 
                        "init_level",
                        "min_level",
                        "max_level", 
                        "diameter",
                        "min_vol",
                        "vol_curve_name",
                        "overflow", 
                        "coordinates"]
    _optional_attributes = ["initial_quality",
                            "mixing_fraction",
                            "mixing_model", 
                            "bulk_coeff", 
                            "tag"]
    
    def __init__(self, name, wn):
        super(Tank, self).__init__(wn, name)
        self._elevation=0.0
        self._init_level=3.048
        self._min_level=0.0
        self._max_level=6.096
        self._diameter=15.24
        self._head = self.elevation + self._init_level
        self._prev_head = self.head
        self._min_vol=0 
        self._vol_curve_name = None
        self._mixing_model = None
        self._mixing_fraction = None
        self._bulk_coeff = None
        self._overflow = False
        self._leak = False
        self._leak_status = False
        self._leak_area = 0.0
        self._leak_discharge_coeff = 0.0
        self._leak_start_control_name = 'tank'+self._name+'start_leak_control'
        self._leak_end_control_name = 'tank'+self._name+'end_leak_control'

    def __repr__(self):
        return "<Tank '{}', elevation={}, min_level={}, max_level={}, diameter={}, min_vol={}, vol_curve='{}'>".format(self._name, self.elevation, self.min_level, self.max_level, self.diameter, self.min_vol, (self.vol_curve.name if self.vol_curve else None))

    def _compare(self, other):
        if not super(Tank, self)._compare(other):
            return False
        if abs(self.elevation   - other.elevation)<1e-9 and \
           abs(self.min_level   - other.min_level)<1e-9 and \
           abs(self.max_level   - other.max_level)<1e-9 and \
           abs(self.diameter    - other.diameter)<1e-9  and \
           abs(self.min_vol     - other.min_vol)<1e-9   and \
           self.bulk_coeff == other.bulk_coeff   and \
           self.overflow == other.overflow  and \
           self.vol_curve      == other.vol_curve:
            return True
        return False
    
    @property
    def elevation(self):
        """float : elevation to the bottom of the tank. head = level + elevation"""
        return self._elevation
    @elevation.setter
    def elevation(self, value):
        self._elevation = value

    @property
    def min_level(self):
        """float : minimum level for the tank to be able to drain"""
        return self._min_level
    @min_level.setter
    def min_level(self, value):
        self._min_level = value

    @property 
    def max_level(self):
        """float : maximum level before tank begins to overflow (if permitted)"""
        return self._max_level
    @max_level.setter
    def max_level(self, value):
        self._max_level = value

    @property
    def diameter(self):
        """float : diameter of the tank as a cylinder""" 
        return self._diameter
    @diameter.setter
    def diameter(self, value):
        self._diameter = value

    @property
    def min_vol(self):
        """float : minimum volume to be able to drain (when using a tank curve)"""
        return self._min_vol
    @min_vol.setter
    def min_vol(self, value):
        self._min_vol = value

    @property
    def mixing_model(self):
        """
        The mixing model to be used by EPANET. This only affects water quality 
        simulations and has no impact on the WNTRSimulator. Uses the `MixType` 
        enum object, or it will convert string values from MIXED, 2COMP, FIFO and LIFO.
        By default, this is set to None, and will produce no output in the 
        EPANET INP file and EPANET will assume complete and instantaneous mixing (MIXED).
        """
        return self._mixing_model
    @mixing_model.setter
    def mixing_model(self, value):
        if isinstance(value, MixType):
            self._mixing_model = value
        elif isinstance(value, str):
            value = value.upper()
            if value == 'MIXED': self._mixing_model = MixType.Mixed
            elif value == '2COMP': self._mixing_model = MixType.TwoComp
            elif value == 'FIFO': self._mixing_model = MixType.FIFO
            elif value == 'LIFO': self._mixing_model = MixType.LIFO
            else:
                raise ValueError('Mixing model must be MIXED, 2COMP, FIFO or LIFO or a MixType object')
        else:
            raise ValueError('Mixing model must be MIXED, 2COMP, FIFO or LIFO or a MixType object')

    @property
    def mixing_fraction(self):
        """float : for water quality simulations only, the compartment size for 2-compartment mixing"""
        return self._mixing_fraction
    @mixing_fraction.setter
    def mixing_fraction(self, value):
        self._mixing_fraction = value    

    @property
    def bulk_coeff(self):
        """float : bulk reaction coefficient for this tank only; leave None to use global value"""
        return self._bulk_coeff
    @bulk_coeff.setter
    def bulk_coeff(self, value):
        self._bulk_coeff = value

    @property
    def init_level(self):
        """The initial tank level at the start of simulation"""
        return self._init_level
    @init_level.setter
    def init_level(self, value):
        self._init_level = value
        self._head = self.elevation+self._init_level

    @property
    def node_type(self):
        """returns ``"Tank"``"""
        return 'Tank'

    @property
    def vol_curve(self):
        """The volume curve, if defined (read only)
        
        Set this using the vol_curve_name.
        """
        return self._curve_reg[self._vol_curve_name]

    @property
    def vol_curve_name(self):
        """Name of the volume curve to use, or None"""
        return self._vol_curve_name
    @vol_curve_name.setter
    def vol_curve_name(self, name):
        self._curve_reg.remove_usage(self._vol_curve_name, (self._name, 'Tank'))
        self._curve_reg.add_usage(name, (self._name, 'Tank'))
        self._vol_curve_name = name

    @property
    def overflow(self):
        """bool : Is this tank allowed to overflow"""
        return self._overflow
    @overflow.setter
    def overflow(self, value):
        if isinstance(value, six.string_types):
            value = value.upper()
            if value in ["YES", "TRUE", "1"]:
                value = True
            elif value in ["NO", "FALSE", "0"]:
                value = False
            else:
                raise ValueError('The overflow entry must "YES" or "NO"')
        elif isinstance(value, int):
            value = bool(value)
        elif value is None:
            value = False
        elif not isinstance(value, bool):
            raise ValueError('The overflow entry must be blank, "YES"/"NO", 1/0, of True/False')
        self._overflow = value

    @property
    def level(self):
        """float : (read-only) the current simulation tank level (= head - elevation)"""
        return self.head - self.elevation
    
    @property
    def pressure(self):
        """float : (read-only) the current simulation pressure (head - elevation)"""
        return self._head - self.elevation

    def get_volume(self, level=None):
        """
        Returns tank volume at a given level
        
        Parameters
        ----------
        level: float or NoneType (optional)
            The level at which the volume is to be calculated. 
            If level=None, then the volume is calculated at the current 
            tank level (self.level)
            
        Returns
        -------
        vol: float 
            Tank volume at a given level
        """
        
        if self.vol_curve is None:
            A = (np.pi / 4.0 * self.diameter ** 2)
            if level is None:
                level = self.level 
            vol = A * level
        else:
            arr = np.array(self.vol_curve.points)
            if level is None:
                level = self.level
            vol = np.interp(level,arr[:,0],arr[:,1])
        return vol


    def add_leak(self, wn, area, discharge_coeff = 0.75, start_time=None, end_time=None):
        """
        Add a leak to a tank. 
        
        Leaks are modeled by:

        Q = discharge_coeff*area*sqrt(2*g*h)

        where:
           Q is the volumetric flow rate of water out of the leak
           g is the acceleration due to gravity
           h is the gauge head at the bottom of the tank, P_g/(rho*g); Note that this is not the hydraulic head (P_g + elevation)

        Note that WNTR assumes the leak is at the bottom of the tank.

        Parameters
        ----------
        wn: :class:`~wntr.network.model.WaterNetworkModel`
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
        from wntr.network.controls import ControlAction, Control
        
        self._leak = True
        self._leak_area = area
        self._leak_discharge_coeff = discharge_coeff

        if start_time is not None:
            start_control_action = ControlAction(self, 'leak_status', True)
            control = Control._time_control(wn, start_time, 'SIM_TIME', False, start_control_action)
            wn.add_control(self._leak_start_control_name, control)

        if end_time is not None:
            end_control_action = ControlAction(self, 'leak_status', False)
            control = Control._time_control(wn, end_time, 'SIM_TIME', False, end_control_action)
            wn.add_control(self._leak_end_control_name, control)

    def remove_leak(self,wn):
        """
        Remove a leak from a tank

        Parameters
        ----------
        wn: :class:`~wntr.network.model.WaterNetworkModel`
           Water network model
        """
        self._leak = False
        wn._discard_control(self._leak_start_control_name)
        wn._discard_control(self._leak_end_control_name)


class Reservoir(Node):
    """
    Reservoir class, inherited from Node
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_reservoir()` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the reservoir.
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this reservoir will belong to.
    base_head : float, optional
        Base head at the reservoir.
        Internal units must be meters (m).
    head_pattern : str, optional
        Head pattern **name**
    

    .. rubric:: Attributes

    .. autosummary::

        name
        node_type
        base_head
        head_pattern_name
        head_timeseries
        coordinates
        initial_quality
        tag

    .. rubric:: Read-only simulation results

    .. autosummary::

        demand
        head
        pressure
        quality

    """
    
    # base and optional attributes used to create a Reservoir in _from_dict
    # base attributes are used in add_reservoir
    _base_attributes = ["name", 
                        "base_head", 
                        "head_pattern_name",
                        "coordinates"]
    _optional_attributes = ["initial_quality", 
                            "tag"]
    
    def __init__(self, name, wn, base_head=0.0, head_pattern=None):
        super(Reservoir, self).__init__(wn, name)
        self._head_timeseries = TimeSeries(wn._pattern_reg, base_head)
        self.head_pattern_name = head_pattern
        """str : Name of the head pattern to use"""

    def __repr__(self):
        return "<Reservoir '{}', head={}>".format(self._name, self._head_timeseries)

    def _compare(self, other):
        if not super(Reservoir, self)._compare(other):
            return False
        if self._head_timeseries == other._head_timeseries:
            return True
        return False

    @property
    def node_type(self):
        """``"Reservoir"`` (read only)"""
        return 'Reservoir'

    @property
    def head_timeseries(self):
        """The head timeseries for the reservoir (read only)"""
        return self._head_timeseries

    @property
    def base_head(self):
        """The constant head (elevation) for the reservoir, or the base value for a head timeseries"""
        return self._head_timeseries.base_value
    @base_head.setter
    def base_head(self, value):
        self._head_timeseries.base_value = value

    @property
    def head_pattern_name(self):
        """The name of the multiplier pattern to use for the head timeseries"""
        return self._head_timeseries.pattern_name
    @head_pattern_name.setter
    def head_pattern_name(self, name):
        self._pattern_reg.remove_usage(self._head_timeseries.pattern_name, (self.name, 'Reservoir'))
        if name is not None:
            self._pattern_reg.add_usage(name, (self.name, 'Reservoir'))
        self._head_timeseries.pattern_name = name

    @property
    def pressure(self):
        """float : (read-only) the current simulation pressure (0.0 for reservoirs)"""
        return 0.0


class Pipe(Link):
    """
    Pipe class, inherited from Link.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pipe()` method. 
    Direct creation through the constructor is highly discouraged.

    Parameters
    ----------
    name : string
        Name of the pipe
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this pipe will belong to.
    

    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        length
        diameter
        roughness
        minor_loss
        initial_status
        check_valve
        bulk_coeff
        wall_coeff
        vertices
        tag

    .. rubric:: Read-only simulation results

    .. autosummary::

        flow
        velocity
        headloss
        friction_factor
        reaction_rate
        quality
        status

    """
    
    # base and optional attributes used to create a Pipe in _from_dict
    # base attributes are used in add_pipe
    _base_attributes = ["name",
                        "start_node_name",
                        "end_node_name",
                        "length",
                        "diameter",
                        "roughness",
                        "minor_loss",
                        "initial_status",
                        "check_valve"]
    _optional_attributes = ["initial_quality",
                            "bulk_coeff",
                            "wall_coeff",
                            "vertices",
                            "tag"]
    
    def __init__(self, name, start_node_name, end_node_name, wn):
        super(Pipe, self).__init__(wn, name, start_node_name, end_node_name)
        self._length = 304.8
        self._diameter = 0.3048
        self._roughness = 100
        self._minor_loss = 0.0
        self._check_valve = False
        self._bulk_coeff = None
        self._wall_coeff = None
        self._velocity = None
        self._friction_factor = None
        self._reaction_rate = None
        
    def __repr__(self):
        return "<Pipe '{}' from '{}' to '{}', length={}, diameter={}, roughness={}, minor_loss={}, check_valve={}, status={}>".format(self._link_name,
                       self.start_node, self.end_node, self.length, self.diameter, 
                       self.roughness, self.minor_loss, self.check_valve, str(self.status))
    
    def _compare(self, other):
        if not super(Pipe, self)._compare(other):
            return False
        if abs(self.length        - other.length)<1e-9     and \
           abs(self.diameter      - other.diameter)<1e-9   and \
           abs(self.roughness     - other.roughness)<1e-9  and \
           abs(self.minor_loss    - other.minor_loss)<1e-9 and \
           self.check_valve  == other.check_valve                and \
           self.bulk_coeff   == other.bulk_coeff    and \
           self.wall_coeff   == other.wall_coeff:
            return True
        return False

    @property
    def link_type(self):
        """returns ``"Pipe"``"""
        return 'Pipe'
    
    @property
    def length(self):
        """float : length of the pipe"""
        return self._length
    @length.setter
    def length(self, value):
        self._length = value

    @property
    def diameter(self):
        """float : diameter of the pipe"""
        return self._diameter
    @diameter.setter
    def diameter(self, value):
        self._diameter = value

    @property
    def roughness(self):
        """float : pipe roughness"""
        return self._roughness 
    @roughness.setter
    def roughness(self, value):
        self._roughness = value

    @property
    def minor_loss(self):
        """float : minor loss coefficient"""
        return self._minor_loss
    @minor_loss.setter
    def minor_loss(self, value):
        self._minor_loss = value

    @property
    def check_valve(self):
        """bool : does this pipe have a check valve"""
        return self._check_valve
    @check_valve.setter
    def check_valve(self, value): 
        self._check_valve = value

    @property
    def cv(self):
        """bool : alias of ``check_valve``
        
        Deprecated - use ``check_valve`` instead."""
        warn('cv is deprecated. Use check_valve instead', DeprecationWarning, stacklevel=2)
        return self._check_valve
    @cv.setter
    def cv(self, value): 
        warn('cv is deprecated. Use check_valve instead', DeprecationWarning, stacklevel=2)
        self._check_valve = value

    @property
    def bulk_coeff(self):
        """float or None : if not None, then a pipe specific bulk reaction coefficient"""
        return self._bulk_coeff
    @bulk_coeff.setter
    def bulk_coeff(self, value):
        self._bulk_coeff = value

    @property
    def wall_coeff(self):
        """float or None : if not None, then a pipe specific wall reaction coefficient"""
        return self._wall_coeff
    @wall_coeff.setter
    def wall_coeff(self, value):
        self._wall_coeff = value

    @property
    def status(self):
        """LinkStatus : the current status of the pipe"""
        if self._internal_status == LinkStatus.Closed:
            return LinkStatus.Closed
        else:
            return self._user_status

    @property
    def friction_factor(self):
        """float : (read-only) the current simulation friction factor in the pipe"""
        return self._friction_factor

    @property
    def reaction_rate(self):
        """float : (read-only) the current simulation reaction rate in the pipe"""
        return self._reaction_rate


class Pump(Link):
    """
    Pump class, inherited from Link.

    For details about the different subclasses, please see one of the following:
    :class:`~wntr.network.elements.HeadPump` and :class:`~wntr.network.elements.PowerPump`

    .. rubric:: Constructor
    
    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pump` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this pump will belong to.
    

    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        base_speed
        speed_pattern_name
        speed_timeseries
        initial_status
        initial_setting
        initial_quality
        efficiency
        energy_price
        energy_pattern
        vertices
        tag

    .. rubric:: Read-only simulation results

    .. autosummary::

        flow
        headloss
        velocity
        quality
        status
        setting

    """
    
    # base and optional attributes used to create a Pump in _from_dict
    # base attributes are used in add_pump
    _base_attributes = ["name",
                        "start_node_name",
                        "end_node_name",
                        "pump_type",
                        "pump_curve_name",
                        "power",
                        "base_speed",
                        "speed_pattern_name",
                        "initial_status"]
    _optional_attributes = ["initial_quality",
                            "initial_setting",
                            "efficiency",
                            "energy_pattern",
                            "energy_price",
                            "vertices",
                            "tag"]
    
    def __init__(self, name, start_node_name, end_node_name, wn):
        super(Pump, self).__init__(wn, name, start_node_name, end_node_name)
        self._speed_timeseries = TimeSeries(wn._pattern_reg, 1.0)
        self._base_power = None
        self._pump_curve_name = None
        self._efficiency = None
        self._energy_price = None 
        self._energy_pattern = None
        self._outage_rule_name = name+'_outage'
        self._after_outage_rule_name = name+'_after_outage'

    def _compare(self, other):
        if not super(Pump, self)._compare(other):
            return False
        return True

    @property
    def efficiency(self): 
        """Curve : pump efficiency"""
        return self._efficiency
    @efficiency.setter
    def efficiency(self, value):
        self._efficiency = value

    @property
    def energy_price(self):
        """float : energy price surcharge (only used by EPANET)"""
        return self._energy_price
    @energy_price.setter
    def energy_price(self, value):
        self._energy_price = value

    @property
    def energy_pattern(self):
        """str : energy pattern name"""
        return self._energy_pattern
    @energy_pattern.setter
    def energy_pattern(self, value):
        self._energy_pattern = value

    @property
    def status(self):
        """LinkStatus : the current status of the pump"""
        if self._internal_status == LinkStatus.Closed:
            return LinkStatus.Closed
        else:
            return self._user_status

    @property
    def link_type(self):
        """str : ``"Pump"`` (read only)"""
        return 'Pump'

    @property
    def speed_timeseries(self):
        """TimeSeries : timeseries of speed values (retrieve only)"""
        return self._speed_timeseries

    @property
    def base_speed(self):
        """float : base multiplier for a speed timeseries"""
        return self._speed_timeseries.base_value
    @base_speed.setter
    def base_speed(self, value):
        self._speed_timeseries.base_value = value
        
    @property
    def speed_pattern_name(self):
        """str : pattern name for the speed"""
        return self._speed_timeseries.pattern_name
    @speed_pattern_name.setter
    def speed_pattern_name(self, name):
        self._pattern_reg.remove_usage(self._speed_timeseries.pattern_name, (self.name, 'Pump'))
        self._pattern_reg.add_usage(name, (self.name, 'Pump'))
        self._speed_timeseries.pattern_name = name

    @property
    def setting(self):
        """Alias to speed for consistency with other link types"""
        return self._speed_timeseries
    
    def add_outage(self, wn, start_time, end_time=None, priority=6, add_after_outage_rule=False):
        """
        Add a pump outage rule to the water network model.

        Parameters
        ----------
        model : :class:`~wntr.network.model.WaterNetworkModel`
            The water network model this outage will belong to.
        start_time : int
           The time at which the outage starts.
        end_time : int
           The time at which the outage stops.
        priority : int
            The outage rule priority, default = 6 (very high)
        add_after_outage_rule : bool
            Flag indicating if a rule is added to open the pump after the outage. 
            Pump status after the outage is generally defined by existing controls/rules in the water network model. 
            For example, the pump opens based on the level of a specific tank.
        """
        from wntr.network.controls import ControlAction, SimTimeCondition, AndCondition, Rule

        # Outage
        act = ControlAction(self, 'status', LinkStatus.Closed)
        cond1 = SimTimeCondition(wn, 'Above' , start_time)
        if end_time is not None:
            cond2 = SimTimeCondition(wn, 'Below' , end_time)
            cond = AndCondition(cond1, cond2)
        else:
            cond = cond1
        rule = Rule(cond, act, priority=priority)
        wn.add_control(self._outage_rule_name, rule)
        
        # After outage
        if add_after_outage_rule and end_time is not None:
            act = ControlAction(self, 'status', LinkStatus.Open)
            cond = SimTimeCondition(wn, 'Above' , end_time)
            rule = Rule(cond, act, priority=priority)
            wn.add_control(self._after_outage_rule_name, rule)

    def remove_outage(self,wn):
        """
        Remove an outage control from the water network model

        Parameters
        ----------
        wn : :class:`~wntr.network.model.WaterNetworkModel`
           Water network model
        """
        
        wn._discard_control(self._outage_rule_name)
        wn._discard_control(self._after_outage_rule_name)
        

class HeadPump(Pump):    
    """
    Head pump class, inherited from Pump.
    
    This type of pump uses a pump curve (see curves). The curve is 
    set using the ``pump_curve_name`` attribute. The curve itself 
    can be accessed using the ``get_pump_curve()`` method.

    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pump` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this pump will belong to.


    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        base_speed
        speed_pattern_name
        speed_timeseries
        initial_status
        initial_setting
        initial_quality
        pump_type
        pump_curve_name
        efficiency
        energy_price
        energy_pattern
        vertices
        tag

    .. rubric:: Read-only simulation results

    .. autosummary::

        flow
        headloss
        velocity
        quality
        status
        setting

    """

#    def __init__(self, name, start_node_name, end_node_name, wn):
#        super(HeadPump,self).__init__(name, start_node_name, 
#                                      end_node_name, wn)
#        self._curve_coeffs = None
#        self._coeffs_curve_points = None # these are used to verify whether
#                                         # the pump curve was changed since
#                                         # the _curve_coeffs were calculated

    def __repr__(self):
        return "<Pump '{}' from '{}' to '{}', pump_type='{}', pump_curve={}, speed={}, status={}>".format(self._link_name,
                   self.start_node, self.end_node, 'HEAD', self.pump_curve_name, 
                   self.speed_timeseries, str(self.status))
    
    def _compare(self, other):
        if not super(HeadPump, self)._compare(other):
            return False
        if self.pump_type == other.pump_type and \
           self.pump_curve_name == other.pump_curve_name:
            return True
        return False
    
    @property
    def pump_type(self): 
        """str : ``"HEAD"`` (read only)"""
        return 'HEAD'
    
    @property
    def pump_curve_name(self):
        """str : the pump curve name"""
        return self._pump_curve_name
    @pump_curve_name.setter
    def pump_curve_name(self, name):
        self._curve_reg.remove_usage(self._pump_curve_name, (self._link_name, 'Pump'))
        self._curve_reg.add_usage(name, (self._link_name, 'Pump'))
        self._curve_reg.set_curve_type(name, 'HEAD')
        self._pump_curve_name = name
        # delete the pump curve coefficients because they have to be recaulcated 
        # if a new curve is associated with the pump
        self._curve_coeffs = None 

    def get_pump_curve(self):
        """
        Get the pump curve object

        Returns
        -------
        Curve
            the head curve for this pump
        """        
        curve = self._curve_reg[self.pump_curve_name]
        return curve
        
    def get_head_curve_coefficients(self):
        """
        Returns the A, B, C coefficients pump curves.

        * For a single point curve, the coefficients are generated according to the 
          following equation:

          :math:`A = 4/3 * H` 
          
          :math:`B = 1/3 * H/Q^2` 
          
          :math:`C = 2` 
        
        * For a two point curve, C is set to 1 and a straight line is fit between
          the points.
        
        * For three point and multi-point curves, the coefficients are generated 
          using ``scipy.optimize.curve_fit`` with the following equation:
            
          :math:`H = A - B*Q^C` 

        Returns
        -------
        Tuple of pump curve coefficient (A, B, C). All floats.
        
        The coefficients are only calculated the first time this function
        is called for a given HeadPump
        """
        def calculate_coefficients(curve):
            Q = []
            H = []
            for pt in curve.points:
                Q.append(pt[0])
                H.append(pt[1])
            
            # 1-Point curve - Replicate EPANET for a one point curve
            if curve.num_points == 1:
                A = (4.0/3.0)*H[0]
                B = (1.0/3.0)*(H[0]/(Q[0]**2))
                C = 2
            # 2-Point curve - Replicate EPANET - generate a straight line
            elif curve.num_points == 2:
                B = - (H[1] - H[0]) / (Q[1]**2 - Q[0]**2)
                A = H[0] + B * Q[0] ** 2
                C = 1
            # 3 - Multi-point curve (3 or more points) - Replicate EPANET for 
            #     3 point curves.  For multi-point curves, this is not a perfect 
            #     replication of EPANET. EPANET uses a mult-linear fit
            #     between points whereas this uses a regression fit of the same
            #     H = A - B * Q **C curve used for the three point fit.
            elif curve.num_points >= 3:
                A0 = H[0]
                C0 = math.log((H[0] - H[1])/(H[0] - H[-1]))/math.log(Q[1]/Q[-1])
                B0 = (H[0] - H[1])/(Q[1]**C0)
    
                def flow_vs_head_func(Q, a, b, c):
                    return a - b * Q ** c
                
                try:
                    coeff, cov = curve_fit(flow_vs_head_func, Q, H, [A0, B0, C0])
                except RuntimeError:
                    raise RuntimeError('Head pump ' + self.name + 
                                       ' results in a poor regression fit to H = A - B * Q^C')
    
                A = float(coeff[0])  # convert to native python floats
                B = float(coeff[1]) 
                C = float(coeff[2])  
            else:
                raise RuntimeError('Head pump ' + self.name + 
                                   ' has an empty pump curve.')
                    
            if A<=0 or B<0 or C<=0:
                raise RuntimeError('Head pump ' + self.name + 
                                   ' has a negative head curve coefficient.')
            # with using scipy curve_fit, I think this is a waranted check 
            elif np.isnan(A+B+C):
                raise RuntimeError('Head pump ' + self.name + 
                                   ' has a coefficient which is NaN!')
            
            self._coeffs_curve_points = curve.points                
            self._curve_coeffs = [A,B,C]
    
        # main procedure    
        curve = self.get_pump_curve()
        if self._curve_coeffs is None or curve.points != self._coeffs_curve_points:
            calculate_coefficients(curve)
        
        A = self._curve_coeffs[0]
        B = self._curve_coeffs[1]
        C = self._curve_coeffs[2]
        
        return A,B,C
    
    def get_design_flow(self):
        """
        Returns the design flow value for the pump.
        Equals to the first point on the pump curve.

        """
        curve = self._curve_reg[self.pump_curve_name]
        
        try:
            return curve.points[-1][0]
        except IndexError:
            raise IndexError("Curve point does not exist")


class PowerPump(Pump):
    """
    Power pump class, inherited from Pump.

    This is a constant power type of pump. The constant power is
    set and modified through the ``power`` attribute.

    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pump` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this pump will belong to.
        

    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        base_speed
        speed_pattern_name
        speed_timeseries
        initial_status
        initial_setting
        initial_quality
        pump_type
        power
        efficiency
        energy_price
        energy_pattern
        vertices
        tag

    .. rubric:: Read-only simulation results

    .. autosummary::

        flow
        headloss
        velocity
        quality
        status
        setting

    """

    def __repr__(self):
        return "<Pump '{}' from '{}' to '{}', pump_type='{}', power={}, speed={}, status={}>".format(self._link_name,
                   self.start_node, self.end_node, 'POWER', self._base_power, 
                   self.speed_timeseries, str(self.status))
    
    def _compare(self, other):
        if not super(PowerPump, self)._compare(other):
            return False
        if self.pump_type == other.pump_type and \
            abs(self.power - other.power)<1e-9:
            return True
        return False
    
    @property
    def pump_type(self): 
        """str : ``"POWER"`` (read only)"""
        return 'POWER'
    
    @property
    def power(self):
        """float : the fixed power value"""
        return self._base_power
    @power.setter
    def power(self, value):
        self._curve_reg.remove_usage(self._pump_curve_name, (self._link_name, 'Pump'))
        self._base_power = value


class Valve(Link):
    
    """
    Valve class, inherited from Link.
    
    For details about the  subclasses, please see one of the following:
    :class:`~wntr.network.elements.PRValve`, :class:`~wntr.network.elements.PSValve`,
    :class:`~wntr.network.elements.PBValve`, :class:`~wntr.network.elements.FCValve`,
    :class:`~wntr.network.elemedifferentnts.TCValve`, and :class:`~wntr.network.elements.GPValve`.

    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_valve` method. 
    Direct creation through the constructor is highly discouraged.

    Parameters
    ----------
    name : string
        Name of the valve
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this valve will belong to.
        
    
    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        valve_type
        initial_status
        initial_setting
        initial_quality
        vertices
        tag

    .. rubric:: Result attributes

    .. autosummary::

        flow
        velocity
        headloss
        quality
        status
        setting

    """

    # base and optional attributes used to create a Valve in _from_dict
    # base attributes are used in add_valve
    _base_attributes = ["name",
                        "start_node_name",
                        "end_node_name",
                        "diameter",
                        "valve_type",
                        "minor_loss",
                        "initial_setting",
                        "initial_status"]
    _optional_attributes = ["initial_quality",
                            "vertices",
                            "tag"]
        
    def __init__(self, name, start_node_name, end_node_name, wn):
        super(Valve, self).__init__(wn, name, start_node_name, end_node_name)
        self.diameter = 0.3048
        self.minor_loss = 0.0
        self._initial_status = LinkStatus.Active
        self._user_status = LinkStatus.Active
        self._initial_setting = 0.0
        self._velocity = None

    def __repr__(self):
        fmt = "<Valve '{}' from '{}' to '{}', valve_type='{}', diameter={}, minor_loss={}, setting={}, status={}>"
        return fmt.format(self._link_name,
                          self.start_node, self.end_node, self.__class__.__name__,
                          self.diameter, 
                          self.minor_loss, self.setting, str(self.status))
    
    def _compare(self, other):
        if not super(Valve, self)._compare(other):
            return False
        if abs(self.diameter   - other.diameter)<1e-9 and \
           self.valve_type    == other.valve_type      and \
           abs(self.minor_loss - other.minor_loss)<1e-9:
            return True
        return False
   
    @property
    def status(self):
        if self._user_status == LinkStatus.Closed:
            return LinkStatus.Closed
        elif self._user_status == LinkStatus.Open:
            return LinkStatus.Open
        else:
            return self._internal_status

    @property
    def link_type(self):
        """returns ``"Valve"``"""
        return 'Valve'

    @property
    def valve_type(self): 
        """returns ``None`` because this is an abstact class"""
        return None


class PRValve(Valve):
    """
    Pressure reducing valve class, inherited from Valve.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_valve` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this valve will belong to.
        
    
    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        initial_status
        initial_setting
        valve_type
        tag
        vertices


    .. rubric:: Result attributes

    .. autosummary::

        flow
        velocity
        headloss
        quality
        status
        setting

    """

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(PRValve, self).__init__(name, start_node_name, end_node_name, wn)

    @property
    def valve_type(self): 
        """returns ``"PRV"``"""
        return 'PRV'


class PSValve(Valve):
    """
    Pressure sustaining valve class, inherited from Valve.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_valve` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this valve will belong to.
        
    
    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        initial_status
        initial_setting
        valve_type
        tag
        vertices


    .. rubric:: Result attributes

    .. autosummary::

        flow
        velocity
        headloss
        quality
        status
        setting

    """

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(PSValve, self).__init__(name, start_node_name, end_node_name, wn)

    @property
    def valve_type(self): 
        """returns ``"PSV"``"""
        return 'PSV'


class PBValve(Valve):
    """
    Pressure breaker valve class, inherited from Valve.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_valve` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this valve will belong to.
        
    
    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        initial_status
        initial_setting
        valve_type
        tag
        vertices


    .. rubric:: Result attributes

    .. autosummary::

        flow
        velocity
        headloss
        quality
        status
        setting

    """

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(PBValve, self).__init__(name, start_node_name, end_node_name, wn)

    @property
    def valve_type(self): 
        """returns ``"PBV"``"""
        return 'PBV'


class FCValve(Valve):
    """
    Flow control valve class, inherited from Valve.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_valve` method. 
    Direct creation through the constructor is highly discouraged.
   
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this valve will belong to
        
    
    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        initial_status
        initial_setting
        valve_type
        tag
        vertices

    .. rubric:: Result attributes

    .. autosummary::

        flow
        velocity
        headloss
        quality
        status
        setting

    """

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(FCValve, self).__init__(name, start_node_name, end_node_name, wn)

    @property
    def valve_type(self): 
        """returns ``"FCV"``"""
        return 'FCV'


class TCValve(Valve):
    """
    Throttle control valve class, inherited from Valve.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_valve` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this valve will belong to
        
    
    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        initial_status
        initial_setting
        valve_type
        tag
        vertices


    .. rubric:: Result attributes

    .. autosummary::

        flow
        velocity
        headloss
        quality
        status
        setting

    """

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(TCValve, self).__init__(name, start_node_name, end_node_name, wn)

    @property
    def valve_type(self): 
        """returns ``"TCV"``"""
        return 'TCV'


class GPValve(Valve):
    """
    General purpose valve class, inherited from Valve.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_valve` method. 
    Direct creation through the constructor is highly discouraged.
    
    Parameters
    ----------
    name : string
        Name of the pump
    start_node_name : string
         Name of the start node
    end_node_name : string
         Name of the end node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this valve will belong to
        
    
    .. rubric:: Attributes

    .. autosummary::

        name
        link_type
        start_node
        start_node_name
        end_node
        end_node_name
        initial_status
        initial_setting
        valve_type
        headloss_curve
        headloss_curve_name
        tag
        vertices


    .. rubric:: Result attributes

    .. autosummary::

        flow
        velocity
        headloss
        quality
        status
        setting

    """

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(GPValve, self).__init__(name, start_node_name, end_node_name, wn)
        self._headloss_curve_name = None

    @property
    def valve_type(self): 
        """returns ``"GPV"``"""
        return 'GPV'

    @property
    def headloss_curve(self):
        """Curve : the headloss curve object (read only)"""
        return self._curve_reg[self._headloss_curve_name]

    @property
    def headloss_curve_name(self):
        """Returns the pump curve name if pump_type is 'HEAD', otherwise returns None"""
        return self._headloss_curve_name
    @headloss_curve_name.setter
    def headloss_curve_name(self, name):
        self._curve_reg.remove_usage(self._headloss_curve_name, (self._link_name, 'Valve'))
        self._curve_reg.add_usage(name, (self._link_name, 'Valve'))
        self._curve_reg.set_curve_type(name, 'HEADLOSS')
        self._headloss_curve_name = name
    

class Pattern(object):
    """
    Pattern class.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pattern` method. 
    
    Parameters
    ----------
    name : string
        Name of the pattern.
    multipliers : list
        A list of multipliers that makes up the pattern.
    time_options : wntr TimeOptions or tuple
        The water network model options.time object or a tuple of (pattern_start, 
        pattern_timestep) in seconds.
    wrap : bool, optional
        Boolean indicating if the pattern should be wrapped.
        If True (the default), then the pattern repeats itself forever; if 
        False, after the pattern has been exhausted, it will return 0.0.
        
    """
    
    def __init__(self, name, multipliers=[], time_options=None, wrap=True):
        self.name = name
        if isinstance(multipliers, (int, float)):
            multipliers = [multipliers]
        self._multipliers = np.array(multipliers, dtype=np.float64)
        if time_options:
            if isinstance(time_options, (tuple, list)) and len(time_options) >= 2:
                tmp = TimeOptions()
                tmp.pattern_start = time_options[0]
                tmp.pattern_timestep = time_options[1]
                time_options = tmp
            elif not isinstance(time_options, TimeOptions):
                raise ValueError('Pattern->time_options must be a TimeOptions class or null')
        self._time_options = time_options
        self.wrap = wrap
        
    def __eq__(self, other):
        if type(self) == type(other) and \
          self.name == other.name and \
          len(self._multipliers) == len(other._multipliers) and \
          self._time_options == other._time_options and \
          self.wrap == other.wrap and \
          np.all(np.abs(np.array(self._multipliers)-np.array(other._multipliers))<1.0e-10):
            return True
        return False

    def __hash__(self):
        return hash('Pattern/'+self.name)
        
    def __str__(self):
        return '%s'%self.name

    def __repr__(self):
        return "<Pattern '{}', multipliers={}>".format(self.name, repr(self.multipliers))
        
    def __len__(self):
        return len(self._multipliers)
    
    def __getitem__(self, index):
        """Returns the pattern value at a specific index (not time!)"""
        nmult = len(self._multipliers)
        if nmult == 0:                     return 1.0
        elif self.wrap:                    return self._multipliers[int(index%nmult)]
        elif index < 0 or index >= nmult:  return 0.0
        return self._multipliers[index]
    
    @classmethod
    def binary_pattern(cls, name, start_time, end_time, step_size, duration, wrap=False):
        """
        Creates a binary pattern (single instance of step up, step down).
        
        Parameters
        ----------
        name : string
            Name of the pattern.
        start_time : int
            The time at which the pattern turns "on" (1.0).
        end_time : int
            The time at which the pattern turns "off" (0.0).
        step_size : int
            Pattern step size.
        duration : int
            Total length of the pattern.
        wrap : bool, optional
            Boolean indicating if the pattern should be wrapped.
            If True, then the pattern repeats itself forever; if 
            False (the default), after the pattern has been exhausted, it will return 0.0.
        
        Returns
        -------
        A new pattern object with a list of 1's and 0's as multipliers. 
        """
        tmp = TimeOptions()
        tmp.pattern_start = 0
        tmp.pattern_timestep = step_size
        time_options = tmp
        patternstep = time_options.pattern_timestep
        patternstart = int(start_time/time_options.pattern_timestep)
        patternend = int(end_time/patternstep)
        patterndur = int(duration/patternstep)
        pattern_list = [0.0]*patterndur
        pattern_list[patternstart:patternend] = [1.0]*(patternend-patternstart)
        return cls(name, multipliers=pattern_list, time_options=None, wrap=wrap)
    
    @property
    def multipliers(self):
        """Returns the pattern multiplier values"""
        return self._multipliers
    @multipliers.setter
    def multipliers(self, values):
        if isinstance(values, (int, float, complex)):
            self._multipliers = np.array([values])
        else:
            self._multipliers = np.array(values)

    @property
    def time_options(self):
        """Returns the TimeOptions object"""
        return self._time_options
    @time_options.setter
    def time_options(self, object):
        if object and not isinstance(object, TimeOptions):
            raise ValueError('Pattern->time_options must be a TimeOptions or null')
        self._time_options = object

    def to_dict(self):
        """Dictionary representation of the pattern"""
        d = dict(name=self.name, 
                 multipliers=list(self._multipliers))
        if not self.wrap:
            d['wrap'] = False
        return d
    
    def at(self, time):
        """
        Returns the pattern value at a specific time
        
        Parameters
        ----------
        time : int
            Time in seconds        
        """
        nmult = len(self._multipliers)
        if nmult == 0:
            return 1.0
        if nmult == 1:
            return self._multipliers[0]
        if self._time_options is None:
            raise RuntimeError('Pattern->time_options cannot be None at runtime')
        step = int(time//self._time_options.pattern_timestep)
        if self.wrap:
            ndx = int(step%nmult)
            last_mult = self._multipliers[ndx]
            if self._time_options.pattern_interpolation:
                if ndx + 1 == nmult:
                    next_mult = self._multipliers[0]
                else:
                    next_mult = self._multipliers[ndx + 1]
                last_time = step * self._time_options.pattern_timestep
                next_time = (step + 1) * self._time_options.pattern_timestep
                slope = (next_mult - last_mult) / (next_time - last_time)
                intercept = next_mult - slope * next_time
                return slope * time + intercept
            else:
                return last_mult
        elif step < 0 or step >= nmult:
            return 0.0
        return self._multipliers[step]
    

class TimeSeries(object): 
    """
    Time series class.
    
    A TimeSeries object contains a base value, Pattern object, and category.  
    The object can be used to store changes in junction demand, source injection, 
    pricing, pump speed, and reservoir head. The class provides methods
    to calculate values using the base value and a multiplier pattern.

    .. rubric:: Constructor

    Parameters
    ----------
    base : number
        A number that represents the baseline value.
    pattern_registry : PatternRegistry
        The pattern registry for looking up patterns
    pattern : str, optional
        If None, then the value will be constant. Otherwise, the Pattern will be used.
        (default = None)
    category : string, optional
        A category, description, or other name that is useful to the user 
        (default = None).
        
    Raises
    ------
    ValueError
        If `base` or `pattern` are invalid types
    
    """
    def __init__(self, model, base, pattern_name=None, category=None):
        if not isinstance(base, (int, float, complex)):
            raise ValueError('TimeSeries->base must be a number')
        if isinstance(model, Registry):
            self._pattern_reg = model
        else:
            raise ValueError('Must pass in a pattern registry')
        self._pattern = pattern_name
        if base is None: base = 0.0
        self._base = base
        self._category = category
        
    def __nonzero__(self):
        return self._base
    __bool__ = __nonzero__

    def __str__(self):
        return repr(self)

    def __repr__(self):
        fmt = "<TimeSeries: base_value={}, pattern_name={}, category='{}'>"
        return fmt.format(self._base, 
                          (repr(self._pattern) if self.pattern else None),
                          str(self._category))
    
    def __eq__(self, other):
        if type(self) == type(other) and \
           self.pattern == other.pattern and \
           self.category == other.category and \
           abs(self._base - other._base)<1e-9 :
            return True
        return False
    
    def __getitem__(self, index):
        """Returns the value at a specific index (not time!)."""
        if not self._pattern:
            return self._base
        return self._base * self._pattern[index]
    
    @property
    def base_value(self):
        """Returns the baseline value."""
        return self._base
    @base_value.setter
    def base_value(self, value):
        if not isinstance(value, (int, float, complex)):
            raise ValueError('TimeSeries->base_value must be a number')
        self._base = value

    @property
    def pattern(self):
        """Returns the Pattern object."""
        return self._pattern_reg[self._pattern]

    @property
    def pattern_name(self):
        """Returns the name of the pattern."""
        if self._pattern:
            return str(self._pattern)
        return None
    @pattern_name.setter
    def pattern_name(self, pattern_name):
        self._pattern = pattern_name

    @property
    def category(self):
        """Returns the category."""
        return self._category
    @category.setter
    def category(self, category):
        self._category = category

    def at(self, time):
        """
        Returns the value at a specific time.
        
        Parameters
        ----------
        time : int
            Time in seconds
        """
        if not self.pattern:
            return self._base
        return self._base * self.pattern.at(time)
    
    def to_dict(self):
        """Dictionary representation of the time series"""
        d = dict(base_val=self._base)
        # if isinstance(self._pattern, six.string_types):
        d['pattern_name'] = self.pattern_name
        # if self._category:
        d['category'] = self.category
        return d
    
#    def tostring(self):
#        """String representation of the time series"""
#        fmt = ' {:12.6g}   {:20s}   {:14s}\n'
#        return fmt.format(self._base, self._pattern, self._category)
    

class Demands(MutableSequence):
    """
    Demands class.
    
    The Demands object is used to store multiple demands per 
    junction in a list. The class includes specialized demand-specific calls 
    and type checking.
    
    A demand list is a list of demands and can be used with all normal list-
    like commands.
    
    The demand list does not have any attributes, but can be created by passing 
    in demand objects or demand tuples as ``(base_demand, pattern, category_name)``
    """
    
    def __init__(self, patterns, *args):
        self._list = []
        self._pattern_reg = patterns
        for object in args:
            self.append(object)

    def __getitem__(self, index):
        """Get the demand at index <==> y = S[index]"""
        return self._list.__getitem__(index)
    
    def __setitem__(self, index, obj):
        """Set demand and index <==> S[index] = object"""
        return self._list.__setitem__(index, self.to_ts(obj))
    
    def __delitem__(self, index):
        """Remove demand at index <==> del S[index]"""
        return self._list.__delitem__(index)

    def __len__(self):
        """Number of demands in list <==> len(S)"""
        return len(self._list)
    
    def __nonzero__(self):
        """True if demands exist in list NOT if demand is non-zero"""
        return len(self._list) > 0
    __bool__ = __nonzero__
    
    def __repr__(self):
        return '<Demands: {}>'.format(repr(self._list))
    
    def to_ts(self, obj):
        """Time series representation of demands"""
        if isinstance(obj, (list, tuple)) and len(obj) >= 2:
            o1 = obj[0]
            o2 = self._pattern_reg.default_pattern if obj[1] is None else obj[1]
            o3 = obj[2] if len(obj) >= 3 else None
            obj = TimeSeries(self._pattern_reg, o1, o2, o3)
        elif isinstance(obj, TimeSeries):
            obj._pattern_reg = self._pattern_reg
        else:
            raise ValueError('object must be a TimeSeries or demand tuple')
        return obj
    
    def insert(self, index, obj):
        """S.insert(index, object) - insert object before index"""
        self._list.insert(index, self.to_ts(obj))
    
    def append(self, obj):
        """S.append(object) - append object to the end"""
        self._list.append(self.to_ts(obj))
    
    def extend(self, iterable):
        """S.extend(iterable) - extend list by appending elements from the iterable"""
        for obj in iterable:
            self._list.append(self.to_ts(obj))

    def clear(self):
        """S.clear() - remove all entries"""
        self._list = []

    def at(self, time, category=None, multiplier=1):
        """Return the total demand at a given time."""
        demand = 0.0
        if category:
            for dem in self._list:
                if dem.category == category:  
                    demand += dem.at(time)*multiplier
        else:
            for dem in self._list:
                demand += dem.at(time)*multiplier
        return demand
    
    def remove_category(self, category):
        """Remove all demands from a specific category"""
        def search():
            for ct, dem in enumerate(self._list):
                if dem.category == category:
                    return ct
            return None
        idx = search()
        while idx is not None:
            self.pop(idx)
            idx = search()
    
    def base_demand_list(self, category=None):
        """Returns a list of the base demands, optionally of a single category."""
        res = []
        for dem in self._list:
            if category is None or dem.category == category:
                res.append(dem.base_value)
        return res

    def pattern_list(self, category=None):
        """Returns a list of the patterns, optionally of a single category."""
        res = []
        for dem in self._list:
            if category is None or dem.category == category:
                res.append(dem.pattern)
        return res
    
    def category_list(self):
        """Returns a list of all the pattern categories."""
        res = []
        for dem in self._list:
                res.append(dem.category)
        return res

    def to_list(self):
        res = []
        for dem in self:
            res.append(dem.to_dict())
        return res
        

class Curve(object):
    """
    Curve base class.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_curve` method. 
    
    Parameters
    ----------
    name : str
        Name of the curve.
    curve_type : str
        The type of curve: None (unspecified), HEAD, HEADLOSS, VOLUME or EFFICIENCY
    points : list
        The points in the curve. List of 2-tuples (x,y) ordered by increasing x
    original_units : str
        The units the points were defined in
    current_units : str
        The units the points are currently defined in. This MUST be 'SI' by the time
        one of the simulators is run.
    options : Options, optional
        Water network options to lookup headloss function
        
    """
    
    def __init__(self, name, curve_type=None, points=[], 
                 original_units=None, current_units='SI', options=None):
        self._name = name
        self._curve_type = curve_type
        self._points = list(points)
        self._options = options
        self._original_units = None
        self._current_units = 'SI'
    
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
                if abs(value1 - value2) > 1e-9:
                    return False
        return True

    def __hash__(self):
        return hash('Curve/'+self._name)

    def __repr__(self):
        return "<Curve: '{}', curve_type='{}', points={}>".format(str(self.name), str(self.curve_type), repr(self.points))

    def __getitem__(self, index):
        return self.points.__getitem__(index)

    def __getslice__(self, i, j):
        return self.points.__getslice__(i, j)

    def __len__(self):
        return len(self.points)
    
    @property
    def original_units(self):
        """The original units the points were written in."""
        return self._original_units
    
    @property
    def current_units(self):
        """The current units that the points are in"""
        return self._current_units
    
    @property
    def name(self):
        """Curve names must be unique among curves"""
        return self._name
    
    @property
    def points(self):
        """The points in the curve. List of 2-tuples (x,y) ordered by increasing x"""
        return self._points
    @points.setter
    def points(self, points):
        self._points = copy.deepcopy(points)
        self._points.sort()
        
    @property
    def curve_type(self):
        """The type of curve: None (unspecified), HEAD, HEADLOSS, VOLUME or EFFICIENCY"""
        return self._curve_type
    @curve_type.setter
    def curve_type(self, curve_type):
        curve_type = str(curve_type)
        curve_type = curve_type.upper()
        if curve_type == 'HEAD':
            self._curve_type = 'HEAD'
        elif curve_type == 'VOLUME':
            self._curve_type = 'VOLUME'
        elif curve_type == 'EFFICIENCY':
            self._curve_type = 'EFFICIENCY'
        elif curve_type == 'HEADLOSS':
            self._curve_type = 'HEADLOSS'
        else:
            raise ValueError('curve_type must be HEAD, HEADLOSS, VOLUME, or EFFICIENCY')

    @property
    def num_points(self):
        """Returns the number of points in the curve."""
        return len(self.points)
    
    def to_dict(self):
        """Dictionary representation of the curve"""
        d = dict(name=self._name, 
                 curve_type=self._curve_type,
                 points=list(self._points))
        return d
    
    def set_units(self, original=None, current=None):
        """Set the units flags for the curve.
        
        Use this after converting the points, if necessary, to indicate that
        conversion to SI units is complete.
        """
        if original:
            self._original_units = original
        if current:
            self._current_units = current


class Source(object):
    """
    Water quality source class.
    
    .. rubric:: Constructor

    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_source` method. 
    
    Parameters
    ----------
    name : string
         Name of the source.
    node_name: string
        Injection node.
    source_type: string
        Source type, options = CONCEN, MASS, FLOWPACED, or SETPOINT.
    strength: float
        Source strength in Mass/Time for MASS and Mass/Volume for CONCEN, 
        FLOWPACED, or SETPOINT.
    pattern: Pattern, optional
        If None, then the value will be constant. Otherwise, the Pattern will be used
        (default = None).
    

    .. rubric:: Attributes

    .. autosummary::

        name
        node_name
        source_type
        strength_timeseries

    """

#    def __init__(self, name, node_registry, pattern_registry):
    def __init__(self, model, name, node_name, source_type, strength, pattern=None, species=None):
        self._strength_timeseries = TimeSeries(model._pattern_reg, strength, pattern, name)
        self._pattern_reg = model._pattern_reg
        self._pattern_reg.add_usage(pattern, (name, 'Source'))
        self._node_reg = model._node_reg
        self._node_reg.add_usage(node_name, (name, 'Source'))
        self._name = name
        self._node_name = node_name
        self._source_type = source_type
        self._species = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self.node_name == other.node_name and \
           self.source_type == other.source_type and \
           self.strength_timeseries == other.strength_timeseries:
            return True
        return False

    def __repr__(self):
        fmt = "<Source: '{}', '{}', '{}', {}, {}, {}>"
        return fmt.format(self.name, self.node_name, self.source_type, self._strength_timeseries.base_value, self._strength_timeseries.pattern_name, repr(self._species))

    @property
    def strength_timeseries(self): 
        """TimeSeries : timeseries of the source values (read only)"""
        return self._strength_timeseries

    @property
    def name(self):
        """str : the name for this source"""
        return self._name 
    @name.setter
    def name(self, value):
        self._name = value

    @property
    def node_name(self):
        """str : the node where this source is located"""
        return self._node_name 
    @node_name.setter
    def node_name(self, value):
        self._node_name = value

    @property
    def source_type(self):
        """str : the source type for this source"""
        return self._source_type 
    @source_type.setter
    def source_type(self, value):
        self._source_type = value

    @property
    def species(self):
        """str : species name for multispecies reactions, by default None"""
    @species.setter
    def species(self, value):
        self._species = str(value)

    def to_dict(self):
        ret = dict()
        ret['name'] = self.name
        ret['node_name'] = self.node_name
        ret['source_type'] = self.source_type
        ret['strength'] = self.strength_timeseries.base_value
        ret['pattern'] = self.strength_timeseries.pattern_name
        if self.species:
            ret['species'] = self.species
        return ret
