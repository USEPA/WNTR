"""
The wntr.network.elements module contains base classes for elements of a water network model.
"""

import enum
import numpy as np
import six

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
        self._headloss_function = None

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
    
    def __getitem__(self, index):
        return self.points[index]

    def _pump_curve(self, flow):
        pass
    
    def _single_point_pump_curve(self, flow):
        pass
    
    def _three_point_pump_curve(self, flow):
        pass
    
    def _multi_point_pump_curve(self, flow):
        pass
    
    def _variable_speed_pump_curve(self, flow):
        pass
    
    def _efficiency_curve(self, flow):
        pass
    
    def _volume_curve(self, level):
        pass
    
    def _headloss_curve(self, flow):
        pass


class Pattern(object):
    """Defines a multiplier pattern (series of multiplier factors)"""
    def __init__(self, name, multipliers=[], step_size=1, step_start=0, wrap=True):
        self.name = name
        """The name should be unique"""
        if isinstance(multipliers, (int, float)):
            multipliers = [multipliers]
        self._multipliers = np.array(multipliers)
        """The array of multipliers (list or numpy array)"""
        self.step_size = step_size
        self.step_start = step_start
        self.wrap = wrap
        """If wrap (default true) then repeat pattern forever, otherwise return 0 if exceeds length"""

    @classmethod
    def BinaryPattern(cls, name, step_size, start_time, end_time, duration):
        """Factory method to create a binary pattern (single instance of step up, step down)"""
        patternstep = step_size
        patternlen = int(end_time/patternstep)
        patternstart = int(start_time/patternstep)
        patternend = int(end_time/patternstep)
        patterndur = int(duration/patternstep)
        pattern_list = [0.0]*patterndur
        pattern_list[patternstart:patternend] = [1.0]*(patternend-patternstart)
        return cls(name, multipliers=pattern_list, step_size=patternstep, wrap=False)
    
    @classmethod
    def _SquareWave(cls, name, step_size, length_off, length_on, first_on):
        raise NotImplementedError('Square wave currently unimplemented')
    
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self.name != other.name or \
           len(self) != len(other) or \
           self.step_size != other.step_size or \
           self.step_start != other.step_start or \
           self.wrap != other.wrap:
            return False
        return np.all(np.abs(self._multipliers-other._multipliers)<1.0e-10)

    def __hash__(self):
        return hash(self.name)
        
    def __str__(self):
        return '<Pattern "%s">'%self.name
        
    def __len__(self):
        return len(self._multipliers)
    
    @property
    def multipliers(self):
        """The actual multiplier values in an array"""
        return self._multipliers
    
    @multipliers.setter
    def multipliers(self, values):
        if isinstance(values, (int, float, complex)):
            self._multipliers = np.array([values])
        elif not isinstance(values, list):
            self._multipliers = np.array(values)

    def at_step(self, step):
        """Get the multiplier appropriate for step"""
        nmult = len(self._multipliers)
#        if nmult == 0:                          return 1.0
#        elif nmult == 1:                        return self._multipliers[0]
        if self.wrap:                         return self._multipliers[step%nmult]
        elif step < 0 or step >= nmult:         return 0.0
        return self._multipliers[step]
    __getitem__ = at_step

    def at_time(self, time):
        """The pattern value at 'time', given in seconds since start of simulation"""
        step = ((time+self.step_start)//self.step_size)
        nmult = len(self._multipliers)
#        elif nmult == 1:                        return self._multipliers[0]
        if self.wrap:                         return self._multipliers[step%nmult]
        elif step < 0 or step >= nmult:         return 0.0
        return self._multipliers[step]
    __call__ = at_time


class TimeVaryingValue(object):
    def __init__(self, base=None, pattern=None, name=None):
        """A simple time varying value.
        Requires a base value, a pattern (optional) and a  name (optional)"""
        if base and not isinstance(base, (int, float, complex)):
            raise ValueError('TimeVaryingValue->base must be a number')
        if isinstance(pattern, Pattern):
            self._pattern = pattern
        elif pattern is None:
            self._pattern = None
        else:
            raise ValueError('TimeVaryingValue(pattern) must be a string, Pattern object, or None')
        if base is None: base = 0.0
        self._base = base
        self._name = name
        
    def __nonzero__(self):
        return self._base
    __bool__ = __nonzero__

    def __str__(self):
        return repr(self)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        fmt = "<TimeVaryingValue: {}, {}, category={}>"
        return fmt.format(self._base, self._pattern, repr(self._name))
    
    @property
    def base_value(self):
        return self._base
    
    @property
    def pattern_name(self):
        if self._pattern:
            return self._pattern.name
        return None
        
    @property
    def pattern(self):
        return self._pattern
    
    @property
    def name(self):
        return self._name
    
    def at_step(self, step):
        if not self._pattern:
            return self._base
        return self._base * self._pattern.at_step(step)
    __getitem__ = at_step
    
    def at_time(self, time):
        if not self._pattern:
            return self._base
        return self._base * self._pattern.at_time(time)
    __call__ = at_time


class Pricing(TimeVaryingValue):
    def __init__(self, base_price=None, pattern=None, category=None):
        super(Pricing, self).__init__(base=base_price, pattern=pattern, name=category)    

    def __str__(self):
        return repr(self)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        fmt = "<Pricing: {}, {}, category={}>"
        return fmt.format(self._base, self._pattern_name, repr(self._name))

    @property
    def category(self):
        return self._name

    @property
    def base_price(self):
        return self._base


class Speed(TimeVaryingValue):
    def __init__(self, base_speed=None, pattern=None, pump_name=None):
        super(Speed, self).__init__(base=base_speed, pattern=pattern, name=pump_name)    

    def __str__(self):
        return repr(self)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        fmt = "<VariableSpeed: {}, {}, pump_name={}>"
        return fmt.format(self._base, self._pattern_name, repr(self._name))

    @property
    def base_speed(self):
        return self._base
        
    @property
    def pump_name(self):
        return self._name


class Demand(TimeVaryingValue):
    def __init__(self, base_demand=None, pattern=None, category=None):
        super(Demand, self).__init__(base=base_demand, pattern=pattern, name=category)
    
    def __str__(self):
        return repr(self)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        fmt = "<Demand: {}, {}, category={}>"
        return fmt.format(self._base, self._pattern_name, repr(self._name))

    @property
    def category(self):
        return self._name

    @property
    def base_demand(self):
        return self._base


class ReservoirHead(TimeVaryingValue):
    def __init__(self, total_head=None, pattern=None, name=None):
        super(ReservoirHead, self).__init__(base=total_head, pattern=pattern, name=name)
    
    def __str__(self):
        return repr(self)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        fmt = "<ReservoirHead: {}, {}>"
        return fmt.format(self._base, self._pattern_name)

    @property
    def total_head(self):
        return self._base


class Source(TimeVaryingValue):
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

    def __init__(self, name, node_name, source_type, quality, pattern):
        super(Source, self).__init__(base=quality, pattern=pattern, name=name)
        self.node_name = node_name
        self.source_type = source_type

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self.node_name == other.node_name and \
           self.source_type == other.source_type and \
           abs(self._base - other._base)<1e-10 and \
           self._pattern == other._pattern:
            return True
        return False

    def __str__(self):
        return self.name

    def __hash__(self):
        return id(self)

    def __repr__(self):
        fmt = "<Source: '{}', '{}', '{}', {}, {}>"
        return fmt.format(self.name, self.node_name, self.source_type, self._base, self._pattern_name)

    @property
    def quality(self):
        return self._base
    

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


class DemandList(object):
    """Defines a demand or set of demands to be assigned to a node"""
    def __init__(self, base=None, pattern=None, name=None, category=None):
        self._non_zero = False
        self._demands = []
        self.add(base, pattern, category)
        self.name = name if name else id(self)
        """Optional name for debugging ease"""
        
    def __str__(self):
        return "<DemandList '{}'>".format(self.name)
        
    def __len__(self):
        return len(self._demands)
    
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if len(self._demands) != len(other._demands):
            return False
        l1 = [ v for v in self._demands ]
        l2 = [ v for v in other._demands ]
        l1.sort()
        l2.sort()
        for v1, v2 in zip(l1, l2):
            if v1[0] != v2[0] or v1[1] != v2[1] or v1[2] != v2[2]: 
                return False
        return True
    
    def __nonzero__(self):
        return self._non_zero

    def items(self):
        return self._demands.__iter__()

    def demand_values(self, start_time, end_time, time_step):
        demand_times = range(start_time, end_time + time_step, time_step)
        demand_values = np.zeros((len(demand_times,)))
        for dem in self._demands:
            for ct, t in enumerate(demand_times):
                demand_values[ct] += dem(t)
        return demand_values

    def base_demands(self):
        """generator yielding the base demands"""
        for v in self._demands:
            yield v.base_demand
    
    def clear(self):
        self._non_zero = False
        while self._demands: self._demands.pop()
    
    @property
    def total_base_demand(self):
        sum = 0.0
        for v in self._demands:
            sum += v.base_demand
            
    def patterns(self):
        """generator yielding the patterns"""
        for v in self._demands:
            yield v.pattern
            
    def categories(self):
        """generator yielding the categories"""
        for v in self._demands:
            yield v.cattegory
    
    def add(self, base, pattern, category=None):
        """add a base demand, pattern, and optional category name to the demands"""
        if base is None and pattern is None:
            return
        self._demands.append(Demand(float(base), pattern, category))
        self._non_zero = (self.total_base_demand != 0.0)

    def append(self, obj):
        """add a tuple of (base, pattern, category) to the demands"""
        demand = None
        if isinstance(obj, tuple) and len(obj) == 3:
            demand = Demand(*obj)
        elif isinstance(obj, Demand):
            demand = obj
        else:
            raise ValueError('remove requires a tuple or Demand')
        self._demands.append(demand)
        self._non_zero = (self.total_base_demand != 0.0)

    def extend(self, obj):
        """add all demands in obj to this Demand's demands"""
        if isinstance(obj, list):
            for i in list: self.append(i)
        elif isinstance(obj, DemandList):
            self._demands.extend(obj._demands)
        elif isinstance(obj, Demand):
            self.append(obj)
        else:
            raise ValueError('obj must be a list of 3-tuples or a Demand object')
        self._non_zero = (self.total_base_demand != 0.0)

    def remove(self, obj):
        """Remove an entry that exactly matches the (base, pattern, category) tuple"""
        if isinstance(obj, tuple) and len(obj) == 3:
            demand = Demand(*obj)
        elif isinstance(obj, Demand):
            demand = obj
        else:
            raise ValueError('remove requires a tuple or Demand')
        ret = self._demands.remove(demand)
        self._non_zero = (self.total_base_demand != 0.0)
        return ret

    def pop(self, index=None):
        """remove the demand at index, defaulting to the last one"""
        ret = self._demands.pop(index)
        self._non_zero = (self.total_base_demand != 0.0)        
        return ret
    
    def add_entry(self, entry):
        """add a Demand to the list of demands"""
        self.append(entry)
    
    def remove_entry(self, index):
        """remove a demand entry by index"""
        self.pop(index)

    def get_entry(self, index):
        """Returns a Demand from the given index"""
        return self._demands[index]
    
    def at_step(self, step):
        """Get the total demand at a given step index"""
        if not self._non_zero: return 0.0
        demand = 0.0
        for dem in self._demands:
            demand += dem.at_step(step)
        return demand
    __getitem__ = at_step

    def at_time(self, time):
        """Get the total demand at a given time - Demand objects must have been initialized with a step size"""
        if not self._non_zero: return 0.0
        demand = 0.0
        for dem in self._demands:
            demand += dem.at_time(time)
        return demand
    __call__ = at_time

    @property
    def _all_categories(self):
        """return a set of all category names within this Demand"""
        return set([cat for _, _, cat in self.demands])

    def _category_at_step(self, category, step):
        """Get the category demand at a given step index"""
        if not self._non_zero: return 0
        return sum([base * pat.at_step(step) for base, pat, cat in self.demands if cat == category])

    def _category_at_time(self, category, time):
        """Get the category demand at a given time - Demand objects must have been initialized with a step size"""
        if not self._non_zero: return 0
        return sum([base * pat.at_time(time) for base, pat, cat in self.demands if cat == category])

