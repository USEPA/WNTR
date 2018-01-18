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
from scipy.optimize import fsolve

if sys.version_info[0] == 2:
    from collections import MutableSequence
else:
    from collections.abc import MutableSequence

from .base import Node, Link, Registry, LinkStatus
from .options import TimeOptions

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
        
        self._leak = False
        self.leak_status = False
        self.leak_area = 0.0
        self.leak_discharge_coeff = 0.0
        self._leak_start_control_name = 'junction'+self._name+'start_leak_control'
        self._leak_end_control_name = 'junction'+self._name+'end_leak_control'

        
    def __repr__(self):
        return "<Junction '{}', elevation={}, demand_timeseries_list={}>".format(self._name, self.elevation, repr(self.demand_timeseries_list))

    def _compare(self, other):
        if not super(Junction, self)._compare(other):
            return False
        if abs(self.elevation - other.elevation)<1e-10 and \
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

    def add_leak(self, wn, area, discharge_coeff=0.75, start_time=None, end_time=None):
        """
        Add a leak to a junction. Leaks are modeled by:

        Q = discharge_coeff*area*sqrt(2*g*h)

        where:
           Q is the volumetric flow rate of water out of the leak
           g is the acceleration due to gravity
           h is the guage head at the junction, P_g/(rho*g); Note that this is not the hydraulic head (P_g + elevation)

        Parameters
        ----------
        wn: wntr WaterNetworkModel
           Water network model containing the junction with
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
        self.leak_area = area
        self.leak_discharge_coeff = discharge_coeff

        if start_time is not None:
            start_control_action = ControlAction(self, 'leak_status', True)
            control = Control.time_control(wn, start_time, 'SIM_TIME', False, start_control_action)
            wn.add_control(self._leak_start_control_name, control)

        if end_time is not None:
            end_control_action = ControlAction(self, 'leak_status', False)
            control = Control.time_control(wn, end_time, 'SIM_TIME', False, end_control_action)
            wn.add_control(self._leak_end_control_name, control)

    def remove_leak(self,wn):
        """
        Remove a leak from a junction.

        Parameters
        ----------
        wn: wntr WaterNetworkModel
           Water network model
        """
        self._leak = False
        wn._discard_control(self._leak_start_control_name)
        wn._discard_control(self._leak_end_control_name)

    @property
    def base_demand(self):
        """Returns the first base demand (first entry in demands_timeseries_list)"""
        if len(self.demand_timeseries_list) > 0:
            dem0 = self.demand_timeseries_list[0]
            return dem0.base_value
        return 0


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
        self._prev_head = self.head
        self.min_vol=0
        self._vol_curve_name = None
        self._mix_model = None
        self._mix_frac = None
        self.bulk_rxn_coeff = None
        
        self._leak = False
        self.leak_status = False
        self.leak_area = 0.0
        self.leak_discharge_coeff = 0.0
        self._leak_start_control_name = 'tank'+self._name+'start_leak_control'
        self._leak_end_control_name = 'tank'+self._name+'end_leak_control'
        
    def __repr__(self):
        return "<Tank '{}', elevation={}, min_level={}, max_level={}, diameter={}, min_vol={}, vol_curve='{}'>".format(self._name, self.elevation, self.min_level, self.max_level, self.diameter, self.min_vol, (self.vol_curve.name if self.vol_curve else None))

    def _compare(self, other):
        if not super(Tank, self)._compare(other):
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
        from wntr.network.controls import ControlAction, Control
        
        self._leak = True
        self.leak_area = area
        self.leak_discharge_coeff = discharge_coeff

        if start_time is not None:
            start_control_action = ControlAction(self, 'leak_status', True)
            control = Control.time_control(wn, start_time, 'SIM_TIME', False, start_control_action)
            wn.add_control(self._leak_start_control_name, control)

        if end_time is not None:
            end_control_action = ControlAction(self, 'leak_status', False)
            control = Control.time_control(wn, end_time, 'SIM_TIME', False, end_control_action)
            wn.add_control(self._leak_end_control_name, control)

    def remove_leak(self,wn):
        """
        Remove a leak from a tank.

        Parameters
        ----------
        wn: wntr WaterNetworkModel
           Water network model
        """
        self._leak = False
        wn._discard_control(self._leak_start_control_name)
        wn._discard_control(self._leak_end_control_name)

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

    def _compare(self, other):
        if not super(Reservoir, self)._compare(other):
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
    
    def _compare(self, other):
        if not super(Pipe, self)._compare(other):
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
        if self._internal_status == LinkStatus.Closed:
            return LinkStatus.Closed
        else:
            return self._user_status

    @status.setter
    def status(self, status):
        self._user_status = status

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
    pump_type : string, optional
        Type of information provided about the pump. Options are 'POWER' or 'HEAD'.
    pump_parameter : float or curve type, optional
        Where power is a fixed value in KW, while a head curve is a Curve object.
    base_speed: float
        Relative speed setting (1.0 is normal speed)
    speed_pattern: Pattern object, optional
        Speed pattern
    """

    def __init__(self, name, start_node_name, end_node_name, model):
        super(Pump, self).__init__(model, name, start_node_name, end_node_name)
        self._speed_timeseries = TimeSeries(model, 1.0)
        self._base_power = None
        self._pump_curve_name = None
        self.efficiency = None
        self.energy_price = None
        self.energy_pattern = None
        self._power_outage = LinkStatus.Open

    def _compare(self, other):
        if not super(Pump, self)._compare(other):
            return False
        if self.pump_type == other.pump_type and \
           self.curve == other.curve:
            return True
        return False
   
    @property
    def status(self):
        if self._internal_status == LinkStatus.Closed:
            return LinkStatus.Closed
        elif self._power_outage == LinkStatus.Closed:
            return LinkStatus.Closed
        else:
            return self._user_status

    @status.setter
    def status(self, status):
        self._user_status = status

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
    
    def add_outage(self, wn, start_time, end_time):
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
        from wntr.network.controls import _InternalControlAction, Control

        start_power_outage_action = _InternalControlAction(self, '_power_outage', LinkStatus.Closed, 'status')
        end_power_outage_action = _InternalControlAction(self, '_power_outage', LinkStatus.Open, 'status')

        start_control = Control.time_control(wn, start_time, 'SIM_TIME', False, start_power_outage_action)
        end_control = Control.time_control(wn, end_time, 'SIM_TIME', False, end_power_outage_action)

        wn.add_control(self.name+'_power_off_'+str(start_time), start_control)
        wn.add_control(self.name+'_power_on_'+str(end_time), end_control)

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
    def pump_type(self): 
        return 'HEAD'
    
    @property
    def pump_curve_name(self):
        """Returns the pump curve name"""
        return self._pump_curve_name
    @pump_curve_name.setter
    def pump_curve_name(self, name):
        self._curve_reg.remove_usage(self._pump_curve_name, (self._link_name, 'Pump'))
        self._curve_reg.add_usage(name, (self._link_name, 'Pump'))
        self._curve_reg.set_curve_type(name, 'HEAD')
        self._pump_curve_name = name

    def get_pump_curve(self):
        curve = self._curve_reg[self.pump_curve_name]
        return curve
        
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
        
        curve = self._curve_reg[self.pump_curve_name]
        
        # 1-Point curve
        if curve.num_points == 1:
            H_1 = curve.points[0][1]
            Q_1 = curve.points[0][0]
            A = (4.0/3.0)*H_1
            B = (1.0/3.0)*(H_1/(Q_1**2))
            C = 2
        # 3-Point curve
        elif curve.num_points == 3:
            Q_1 = curve.points[0][0]
            H_1 = curve.points[0][1]
            Q_2 = curve.points[1][0]
            H_2 = curve.points[1][1]
            Q_3 = curve.points[2][0]
            H_3 = curve.points[2][1]

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
        curve = self._curve_reg[self.pump_curve_name]
        
        try:
            return curve.points[-1][0]
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
    def pump_type(self): 
        return 'POWER'
    
    @property
    def power(self):
        """Returns the fixed_power value"""
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
        self._initial_status = LinkStatus.Active
        self._user_status = LinkStatus.Active
        self._initial_setting = 0.0

    def __repr__(self):
        fmt = "<Pump '{}' from '{}' to '{}', valve_type='{}', diameter={}, minor_loss={}, setting={}, status={}>"
        return fmt.format(self._link_name,
                          self.start_node, self.end_node, self.__class__.__name__,
                          self.diameter, 
                          self.minor_loss, self.setting, str(self.status))
    
    def _compare(self, other):
        if not super(Valve, self)._compare(other):
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

    @status.setter
    def status(self, status):
        self._user_status = status

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
        """Returns the pump curve name if pump_type is 'HEAD', otherwise returns None"""
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
    

class Pattern(object):
    """
    Pattern class.
    
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
        self._multipliers = np.array(multipliers)
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
        """Returns the pattern multiplier values."""
        return self._multipliers
    @multipliers.setter
    def multipliers(self, values):
        if isinstance(values, (int, float, complex)):
            self._multipliers = np.array([values])
        else:
            self._multipliers = np.array(values)

    @property
    def time_options(self):
        """Returns the TimeOptions object."""
        return self._time_options
    @time_options.setter
    def time_options(self, object):
        if object and not isinstance(object, TimeOptions):
            raise ValueError('Pattern->time_options must be a TimeOptions or null')
        self._time_options = object

    def todict(self):
        d = dict(name=self.name, 
                 multipliers=list(self._multipliers))
        if not self.wrap:
            d['wrap'] = False
        return d
    
    def at(self, time):
        """
        Returns the pattern value at a specific time.
        
        Parameters
        ----------
        time : int
            Time in seconds        
        """
        nmult = len(self._multipliers)
        if nmult == 0: return 1.0
        if nmult == 1: return self._multipliers[0]
        if self._time_options is None:
            raise RuntimeError('Pattern->time_options cannot be None at runtime')
        step = int((time+self._time_options.pattern_start)//self._time_options.pattern_timestep)
        if self.wrap:                      return self._multipliers[int(step%nmult)]
        elif step < 0 or step >= nmult:    return 0.0
        return self._multipliers[step]
    __call__ = at
    

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
        

class Curve(object):
    """
    Curve base class.

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
    options : WaterNetworkOptions, optional
        Water network options to lookuup headloss function
    """
    def __init__(self, name, curve_type=None, points=[], 
                 original_units=None, current_units='SI', options=None):
        self._name = name
        self._curve_type = curve_type
        self._points = points
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
                if abs(value1 - value2) > 1e-8:
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
    
    def todict(self):
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
    def strength_timeseries(self): 
        return self._strength_timeseries

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

