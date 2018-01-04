"""
The wntr.network.elements module includes elements of a water network model, 
including junction, tank, reservoir, pipe, pump, valve, timeseries, sources, 
and demands.
"""
import numpy as np
import sys
import logging
import math
import six
from scipy.optimize import fsolve

if sys.version_info[0] == 2:
    from collections import MutableSequence
else:
    from collections.abc import MutableSequence

from .base import Node, Link, Registry, LinkStatus

logger = logging.getLogger(__name__)

class Junction(Node):
    """
    Junction class, inherited from Node.

    Parameters
    ----------
    name : string
        Name of the junction.
    base_demand : float, optional
        Base demand at the junction.
        Internal units must be cubic meters per second (m^3/s).
    demand_pattern : Pattern object, optional
        Demand pattern.
    elevation : float, optional
        Elevation of the junction.
        Internal units must be meters (m).
    """

    def __init__(self, name, model):
        super(Junction, self).__init__(model, name)
        self.demand_timeseries_list = Demands(model)
        self.elevation = 0.0

        self.nominal_pressure = 20.0
        """The nominal pressure attribute is used for pressure-dependent demand. This is the lowest pressure at
        which the customer receives the full requested demand."""

        self.minimum_pressure = 0.0
        """The minimum pressure attribute is used for pressure-dependent demand simulations. Below this pressure,
        the customer will not receive any water."""

        self._emitter_coefficient = None

    def __repr__(self):
        return "<Junction '{}', elevation={}, demand_timeseries_list={}>".format(self._name, self.elevation, repr(self.demand_timeseries_list))

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
    
    @property
    def node_type(self):
        """Returns the node type"""
        return 'Junction'

    def add_demand(self, base, pattern_name, category=None):
        if pattern_name is not None:
            self._pattern_reg.add_usage(pattern_name, (self.name, 'Junction'))
        self.demand_timeseries_list.append((base, pattern_name, category))

    def todict(self):
        d = super(Junction, self).todict()
        d['properties'] = dict(elevation=self.elevation,
                               demands=self.demand_timeseries_list.tolist())
        return d


class Tank(Node):
    """
    Tank class, inherited from Node.

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

    def __init__(self, name, model):
        super(Tank, self).__init__(model, name)
        self.elevation=0.0
        self._init_level=3.048
        self.min_level=0.0
        self.max_level=6.096
        self.diameter=15.24,
        self.head = self.elevation + self._init_level
        self.min_vol=0
        self._vol_curve_name = None
        self._mix_model = None
        self._mix_frac = None
        self.bulk_rxn_coeff = None
        
    def __repr__(self):
        return "<Tank '{}', elevation={}, min_level={}, max_level={}, diameter={}, min_vol={}, vol_curve='{}'>".format(self._name, self.elevation, self.min_level, self.max_level, self.diameter, self.min_vol, (self.vol_curve.name if self.vol_curve else None))

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
    
    @property
    def init_level(self):
        return self._init_level
    
    @init_level.setter
    def init_level(self, value):
        self._init_level = value
        self.head = self.elevation+self._init_level

    @property
    def node_type(self):
        return 'Tank'

    @property
    def vol_curve(self):
        return self._curve_reg[self._vol_curve_name]

    @property
    def vol_curve_name(self):
        """Name of the volume to use, or None"""
        return self._vol_curve_name
    
    @vol_curve_name.setter
    def vol_curve_name(self, name):
        self._curve_reg.remove_usage(self._vol_curve_name, (self._name, 'Tank'))
        self._curve_reg.add_usage(name, (self._name, 'Tank'))
        self._vol_curve_name = name

    @property
    def level(self):
        """Returns tank level (head - elevation)"""
        return self.head - self.elevation

    def todict(self):
        d = super(Tank, self).todict()
        d['properties'] = dict(elevation=self.elevation,
                              init_level=self.init_level,
                              min_level=self.min_level,
                              max_level=self.max_level,
                              min_vol=self.min_vol,
                              diameter=self.diameter)
        if self._vol_curve_name is not None:
            d['properties']['vol_curve'] = self._vol_curve_name
        if self.bulk_rxn_coeff is not None:
            d['properties']['bulk_rxn_coeff'] = self.bulk_rxn_coeff
        if self._mix_model is not None:
            d['properties']['mix_model'] = self._mix_model
        if self._mix_frac is not None:
            d['properties']['mix_frac'] = self._mix_frac
        return d

class Reservoir(Node):
    """
    Reservoir class, inherited from Node.

    Parameters
    ----------
    name : string
        Name of the reservoir.
    pattern_registry : PatternRegistry
        A registry for patterns must be provided
    base_head : float, optional
        Base head at the reservoir.
        Internal units must be meters (m).
    head_pattern : str, optional
        Head pattern.
    """
    def __init__(self, name, model, base_head=0.0, head_pattern=None):
        super(Reservoir, self).__init__(model, name)
        self._head_timeseries = TimeSeries(model, base_head)
        self.head_pattern_name = head_pattern

    def __repr__(self):
        return "<Reservoir '{}', head={}>".format(self._name, self._head_timeseries)

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Reservoir, self).__eq__(other):
            return False
        if self._head_timeseries == other._head_timeseries:
            return True
        return False

    @property
    def node_type(self):
        return 'Reservoir'

    @property
    def head_timeseries(self):
        return self._head_timeseries

    @property
    def base_head(self):
        return self._head_timeseries.base_value

    @base_head.setter
    def base_head(self, value):
        self._head_timeseries.base_value = value

    @property
    def head_pattern_name(self):
        return self._head_timeseries.pattern_name
    
    @head_pattern_name.setter
    def head_pattern_name(self, name):
        self._pattern_reg.remove_usage(self._head_timeseries.pattern_name, (self.name, 'Reservoir'))
        if name is not None:
            self._pattern_reg.add_usage(name, (self.name, 'Reservoir'))
        self._head_timeseries.pattern_name = name
    
    def todict(self):
        d = super(Reservoir, self).todict()
        d['properties'] = dict(head=self._head_timeseries.todict())
        return d


class Pipe(Link):
    """
    Pipe class, inherited from Link.

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

    def __init__(self, name, start_node_name, end_node_name, model):
        super(Pipe, self).__init__(model, name, start_node_name, end_node_name)
        self.length = 304.8
        self.diameter = 0.3048
        self.roughness = 100
        self.minor_loss = 0.0
        self.cv = False
        self.bulk_rxn_coeff = None
        self.wall_rxn_coeff = None
        
    def __repr__(self):
        return "<Pipe '{}' from '{}' to '{}', length={}, diameter={}, roughness={}, minor_loss={}, check_valve={}, status={}>".format(self._link_name,
                       self.start_node, self.end_node, self.length, self.diameter, 
                       self.roughness, self.minor_loss, self.cv, str(self.status))
    
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

    @property
    def link_type(self):
        return 'Pipe'
    
    @property
    def status(self):
        return self._user_status

    def todict(self):
        d = super(Pipe, self).todict()
        d['properties'] = dict(length=self.length,
                               diameter=self.diameter,
                               roughness=self.roughness,
                               minor_loss=self.minor_loss)
        if self.cv:
            d['properties']['cv'] = self.cv
        if self.wall_rxn_coeff:
            d['properties']['wall_rxn_coeff'] = self.wall_rxn_coeff
        if self.bulk_rxn_coeff:
            d['properties']['bulk_rxn_coeff'] = self.bulk_rxn_coeff
        return d

class Pump(Link):
    """
    Pump class, inherited from Link.

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
    base_speed: float
        Relative speed setting (1.0 is normal speed)
    speed_pattern: Pattern object, optional
        Speed pattern
    """

    def __init__(self, name, start_node_name, end_node_name, model):
        super(Pump, self).__init__(model, name, start_node_name, end_node_name)
        self._cv_status = LinkStatus.opened
        self._speed_timeseries = TimeSeries(model, 1.0)
        self._base_power = None
        self._pump_curve_name = None
        self.efficiency = None
        self.energy_price = None
        self.energy_pattern = None
        self._power_outage = False
        self._prev_power_outage = False

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if not super(Pump, self).__eq__(other):
            return False
        if self.info_type == other.info_type and \
           self.curve == other.curve:
            return True
        return False
   
    @property
    def status(self):
        if self._cv_status == LinkStatus.Closed:
            return LinkStatus.Closed
        elif self._power_outage is True:
            return LinkStatus.Closed
        else:
            return self._user_status

    @property
    def link_type(self):
        return 'Pump'

    @property
    def speed_timeseries(self):
        return self._speed_timeseries

    @property
    def base_speed(self):
        return self._speed_timeseries.base_value
    
    @base_speed.setter
    def base_speed(self, value):
        self._speed_timeseries.base_value = value
        
    @property
    def speed_pattern_name(self):
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

    def todict(self):
        d = super(Pump, self).todict()
        d['properties'] = dict(pump_type=self.pump_type,
                               speed=self._speed_timeseries.todict())
        return d


class HeadPump(Pump):
    """
    Head pump class, inherited from Pump.
    """
    def __repr__(self):
        return "<Pump '{}' from '{}' to '{}', pump_type='{}', pump_curve={}, speed={}, status={}>".format(self._link_name,
                   self.start_node, self.end_node, 'HEAD', self.pump_curve_name, 
                   self.speed_timeseries, str(self.status))
    
    @property
    def pump_type(self): return 'HEAD'
    
    @property
    def pump_curve_name(self):
        """Returns the pump curve name if info_type is 'HEAD', otherwise returns None"""
        return self._pump_curve_name
    
    @pump_curve_name.setter
    def pump_curve_name(self, name):
        self._curve_reg.remove_usage(self._pump_curve_name, (self._link_name, 'Pump'))
        self._curve_reg.add_usage(name, (self._link_name, 'Pump'))
        self._curve_reg.set_curve_type(name, 'HEAD')
        self._pump_curve_name = name

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

    def todict(self):
        d = super(HeadPump, self).todict()
        d['properties']['pump_curve'] = self._pump_curve_name
        return d

class PowerPump(Pump):
    """
    Power pump class, inherited from Pump.
    """
    def __repr__(self):
        return "<Pump '{}' from '{}' to '{}', pump_type='{}', power={}, speed={}, status={}>".format(self._link_name,
                   self.start_node, self.end_node, 'POWER', self._base_power, 
                   self.speed_timeseries, str(self.status))
        
    @property
    def pump_type(self): return 'POWER'
    
    @property
    def power(self):
        """Returns the fixed_power value if info_type is 'POWER', otherwise returns None"""
        return self._base_power
    @power.setter
    def power(self, kW):
        self._curve_reg.remove_usage(self._pump_curve_name, (self._link_name, 'Pump'))
        self._base_power = kW

    def todict(self):
        d = super(PowerPump, self).todict()
        d['properties']['base_power'] = self._base_power
        return d

class Valve(Link):
    """
    Valve class, inherited from Link.

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
    def __init__(self, name, start_node_name, end_node_name, model):
        super(Valve, self).__init__(model, name, start_node_name, end_node_name)
        self.diameter = 0.3048
        self.minor_loss = 0.0
        self._initial_status = LinkStatus.active
        self._initial_setting = 0.0

    def __repr__(self):
        fmt = "<Pump '{}' from '{}' to '{}', valve_type='{}', diameter={}, minor_loss={}, setting={}, status={}>"
        return fmt.format(self._link_name,
                          self.start_node, self.end_node, self.__class__.__name__,
                          self.diameter, 
                          self.minor_loss, self.setting, str(self.status))
    
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
        return 'Valve'

    def todict(self):
        d = super(Valve, self).todict()
        d['properties'] = dict(diameter=self.diameter,
                               valve_type=self.valve_type,
                               minor_loss=self.minor_loss)
        return d


class PRValve(Valve):
    """
    Pressure reducting valve class, inherited from Valve.
    """
    def __init__(self, name, start_node_name, end_node_name, model):
        super(PRValve, self).__init__(name, start_node_name, end_node_name, model)

    @property
    def valve_type(self): return 'PRV'


class PSValve(Valve):
    """
    Pressure sustaining valve class, inherited from Valve.
    """
    def __init__(self, name, start_node_name, end_node_name, model):
        super(PSValve, self).__init__(name, start_node_name, end_node_name, model)

    @property
    def valve_type(self): return 'PSV'


class PBValve(Valve):
    """
    Pressure breaker valve class, inherited from Valve.
    """
    def __init__(self, name, start_node_name, end_node_name, model):
        super(PBValve, self).__init__(name, start_node_name, end_node_name, model)

    @property
    def valve_type(self): return 'PBV'


class FCValve(Valve):
    """
    Flow control valve class, inherited from Valve.
    """
    def __init__(self, name, start_node_name, end_node_name, model):
        super(FCValve, self).__init__(name, start_node_name, end_node_name, model)

    @property
    def valve_type(self): return 'FCV'


class TCValve(Valve):
    """
    Throttle control valve class, inherited from Valve.
    """
    def __init__(self, name, start_node_name, end_node_name, model):
        super(TCValve, self).__init__(name, start_node_name, end_node_name, model)

    @property
    def valve_type(self): return 'TCV'


class GPValve(Valve):
    """
    General purpose valve class, inherited from Valve.
    """
    def __init__(self, name, start_node_name, end_node_name, model):
        super(GPValve, self).__init__(name, start_node_name, end_node_name, model)
        self._headloss_curve_name = None

    @property
    def valve_type(self): return 'GPV'

    @property
    def headloss_curve(self):
        return self._curve_reg[self._headloss_curve_name]

    @property
    def headloss_curve_name(self):
        """Returns the pump curve name if info_type is 'HEAD', otherwise returns None"""
        return self._headloss_curve_name
    @headloss_curve_name.setter
    def headloss_curve_name(self, name):
        self._curve_reg.remove_usage(self._headloss_curve_name, (self._link_name, 'Valve'))
        self._curve_reg.add_usage(name, (self._link_name, 'Valve'))
        self._curve_reg.set_curve_type(name, 'HEADLOSS')
        self._headloss_curve_name = name

    def todict(self):
        d = super(GPValve, self).todict()
        d['properties']['headloss_curve'] = self._headloss_curve_name        
        return d
    

class TimeSeries(object): 
    """
    Time series class.
    
    A TimeSeries object contains a base value, Pattern object, and category.  
    The object can be used to store changes in junction demand, source injection, 
    pricing, pump speed, and reservoir head. The class provides methods
    to calculate values using the base value and a multiplier pattern.
    
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
            self._pattern_reg = model.patterns
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
        fmt = "<TimeSeries: base={}, pattern='{}', category='{}'>"
        return fmt.format(self._base, 
                          (self._pattern if self.pattern else None),
                          str(self._category))
    
    def tostring(self):
        fmt = ' {:12.6g}   {:20s}   {:14s}\n'
        return fmt.format(self._base, self._pattern, self._category)
    
    def todict(self):
        d = dict(base_val=self._base)
        if isinstance(self._pattern, six.string_types):
            d['pattern_name'] = self._pattern
        if self._category:
            d['category'] = self._category
        return d
    
    def __eq__(self, other):
        if type(self) == type(other) and \
           self.pattern == other.pattern and \
           self.category == other.category and \
           abs(self._base - other._base)<1e-10 :
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
            return self._pattern
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
    __call__ = at
    
    def get_values(self, start_time, end_time, time_step):
        """
        Returns the values for a range of times.
        
        Parameters
        ----------
        start_time : int
            Start time in seconds.
        end_time : int
            End time in seconds.
        time_step : int
            Time step.
        """
        demand_times = range(start_time, end_time + time_step, time_step)
        demand_values = np.zeros((len(demand_times,)))
        for ct, t in enumerate(demand_times):
            demand_values[ct] = self.at(t)
        return demand_values


class Source(object):
    """
    Water quality source class.

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
    """

#    def __init__(self, name, node_registry, pattern_registry):
    def __init__(self, model, name, node_name, source_type, strength, pattern=None):
        self._strength_timeseries = TimeSeries(model, strength, pattern, name)
        self._pattern_reg = model.patterns
        self._pattern_reg.add_usage(pattern, (name, 'Source'))
        self._node_reg = model.nodes
        self._node_reg.add_usage(node_name, (name, 'Source'))
        self.name = name
        self.node_name = node_name
        self.source_type = source_type

    @property
    def strength_timeseries(self): return self._strength_timeseries

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self.node_name == other.node_name and \
           self.source_type == other.source_type and \
           self.strength_timeseries == other.strength_timeseries:
            return True
        return False

    def __repr__(self):
        fmt = "<Source: '{}', '{}', '{}', {}, {}>"
        return fmt.format(self.name, self.node_name, self.source_type, self._base, self._pattern_name)


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
    
    def __init__(self, model, *args):
        self._list = []
        self._pattern_reg = model.patterns
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
    
    def tostring(self):
        if len(self._list) == 0:
            s = ' Demand#__  Base_Value___  Pattern_Name_________  Category______\n'
            s += '    None\n'
            return s
#        elif len(self._list) == 1:
#            s  = '  ========   ============   ====================   ==============\n'
#            s += '  Demand:    {:12.6g}   {:20s}   {:14s}\n'.format(self._list[0].base_value,
#                                                                    self._list[0].pattern_name,
#                                                                    self._list[0].category)
#            s += '  ========   ============   ====================   ==============\n'
#            return s
#        s  = '  ========   ============   ====================   ==============\n'
#        s += '  Demand #   Base Value     Pattern Name           Category      \n'
#        s += '  --------   ------------   --------------------   --------------\n'
        s = ' Demand#__  Base_Value___  Pattern_Name_________  Category______\n'
        lf = '  [{:5d} ]  {}'
        for ct, dem in enumerate(self._list):
            s += lf.format(ct+1, dem.tostring())
#        s += '  ========   ============   ====================   ==============\n'
        return s
    
    def tolist(self):
        if len(self._list) == 0: return None
        d = []
        for demand in self._list:
            d.append(demand.todict())
        return d
    
    def to_ts(self, obj):
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

    def at(self, time, category=None):
        """Return the total demand at a given time."""
        demand = 0.0
        if category:
            for dem in self._list:
                if dem.category == category:  
                    demand += dem.at(time)
        else:
            for dem in self._list:
                demand += dem.at(time)
        return demand
    __call__ = at
    
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

    def get_values(self, start_time, end_time, time_step):
        """
        Returns the values for a range of times.
        
        Parameters
        ----------
        start_time : int
            Start time in seconds
        end_time : int
            End time in seconds
        time_step : int
            time_step
        """
        demand_times = range(start_time, end_time + time_step, time_step)
        demand_values = np.zeros((len(demand_times,)))
        for dem in self._list:
            for ct, t in enumerate(demand_times):
                demand_values[ct] += dem(t)
        return demand_values
        