"""
The wntr.network.elements module includes elements of a water network model, 
such as curves, patterns, sources, and demands.
"""
import enum
import numpy as np
import sys
import copy
import logging

from .options import TimeOptions

logger = logging.getLogger(__name__)

if sys.version_info[0] == 2:
    from collections import MutableSequence
else:
    from collections.abc import MutableSequence

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
        self.points = copy.deepcopy(points)
        self.points.sort()
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
        return self.points.__getitem__(index)

    def __getslice__(self, i, j):
        return self.points.__getslice__(i, j)

    def __len__(self):
        return len(self.points)

    @property
    def num_points(self):
        return len(self.points)

class Pattern(object):
    """
    Pattern class.
    
    Parameters
    ----------
    name : string
        A unique name to describe the pattern (should be the same used when 
        adding the pattern to the model)
    multipliers : list-like
        A list of multipliers that makes up the pattern
    time_options : TimeOptions or tuple
        The global options.time object or a tuple of (pattern_start, pattern_timestep) in seconds
    wrap : bool
        If true (the default), then the pattern repeats itself forever; if 
        false, after the pattern has been exhausted, it will return 0.0
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

    @classmethod
    def BinaryPattern(cls, name, start_time, end_time, duration, time_options, wrap=False):
        """
        Creates a binary pattern (single instance of step up, step down)
        
        Parameters
        ----------
        name : str
            A unique name to describe the pattern (should be the same used when 
            adding the pattern to the model)
        time_options : TimeOptions or tuple
            Pattern and duration options set or as tuple (pattern_start, pattern_timestep)    
        start_time : int
            The time at which the pattern turns "on" (1.0)
        end_time : int
            The time at which the pattern turns "off" (0.0)
        """
        if isinstance(time_options, (tuple, list)) and len(time_options) >= 2:
            tmp = TimeOptions()
            tmp.pattern_start = time_options[0]
            tmp.pattern_timestep = time_options[1]
            time_options = tmp
        elif not isinstance(time_options, TimeOptions):
            raise ValueError('Pattern->time_options must be a TimeOptions, tuple or null')
        patternstep = time_options.pattern_timestep
        patternstart = int(start_time/time_options.pattern_timestep)
        patternend = int(end_time/patternstep)
        patterndur = int(duration/patternstep)
        pattern_list = [0.0]*patterndur
        pattern_list[patternstart:patternend] = [1.0]*(patternend-patternstart)
        return cls(name, multipliers=pattern_list, time_options=time_options, wrap=wrap)
    
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
        return hash(self.name)
        
    def __str__(self):
        return '<Pattern "%s">'%self.name
        
    def __len__(self):
        return len(self._multipliers)
    
    @property
    def multipliers(self):
        """The multiplier values"""
        return self._multipliers
    
    @multipliers.setter
    def multipliers(self, values):
        if isinstance(values, (int, float, complex)):
            self._multipliers = np.array([values])
        else:
            self._multipliers = np.array(values)

    @property
    def time_options(self):
        """The TimeOptions object for the model"""
        return self._time_options
    
    @time_options.setter
    def time_options(self, object):
        if object and not isinstance(object, TimeOptions):
            raise ValueError('Pattern->time_options must be a TimeOptions or null')
        self._time_options = object

    def __getitem__(self, index):
        """Returns the pattern value at a specific index (not time!)"""
        nmult = len(self._multipliers)
        if nmult == 0:                          return 1.0
        elif self.wrap:                         return self._multipliers[int(index%nmult)]
        elif index < 0 or index >= nmult:         return 0.0
        return self._multipliers[index]

    def at(self, time):
        """
        Returns the pattern value at a specific time
        
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
        step = ((time+self._time_options.pattern_start)//self._time_options.pattern_timestep)
        if self.wrap:                         return self._multipliers[int(step%nmult)]
        elif step < 0 or step >= nmult:         return 0.0
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
        A number that represents the baseline value
    pattern : Pattern, optional
        If None, then the value will be constant. Otherwise, the Pattern will be used.
    category : string, optional
        A category, description, or other name that is useful to the user
        
    Raises
    ------
    ValueError
        If `base` or `pattern` are invalid types
    
    """
    def __init__(self, base, pattern=None, category=None):
        if not isinstance(base, (int, float, complex)):
            raise ValueError('TimeSeries->base must be a number')
        if isinstance(pattern, Pattern):
            self._pattern = pattern
        elif pattern is None:
            self._pattern = None
        else:
            raise ValueError('TimeSeries->pattern must be a Pattern object or None')
        if base is None: base = 0.0
        self._base = base
        self._category = category
        
    def __nonzero__(self):
        return self._base
    __bool__ = __nonzero__

    def __str__(self):
        return repr(self)

    def __repr__(self):
        fmt = "<TimeSeries: base={}, pattern={}, category={}>"
        return fmt.format(self._base, self._pattern, repr(self._category))
    
    def __eq__(self, other):
        if type(self) == type(other) and \
           self.pattern == other.pattern and \
           self.category == other.category and \
           abs(self._base - other._base)<1e-10 :
            return True
        return False
    
    def __getitem__(self, index):
        """Returns the value at a specific index (not time!)"""
        if not self._pattern:
            return self._base
        return self._base * self._pattern[index]
    
    @property
    def base_value(self):
        """The baseline value for this variable"""
        return self._base
    
    @base_value.setter
    def base_value(self, value):
        if not isinstance(value, (int, float, complex)):
            raise ValueError('TimeSeries->base_value must be a number')
        self._base = value
        
    @property
    def pattern(self):
        """The pattern object"""
        return self._pattern
    
    @pattern.setter
    def pattern(self, pattern):
        if not isinstance(pattern, Pattern):
            raise ValueError('TimeSeries->pattern must be a Pattern object')
        self._pattern = pattern

    @property
    def pattern_name(self):
        """Get the name of the pattern used.
        
        This is a read-only property.
        """
        if self._pattern:
            return self._pattern.name
        return None
                    
    @property
    def category(self):
        """The category"""
        return self._category
    
    @category.setter
    def category(self, category):
        self._category = category

    def at(self, time):
        """
        Returns the value at a specific time
        
        Parameters
        ----------
        time : int
            Time in seconds
        """
        if not self._pattern:
            return self._base
        return self._base * self._pattern.at(time)
    __call__ = at
    
    def get_values(self, start_time, end_time, time_step):
        """
        Returns the values for a range of times
        
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
        for ct, t in enumerate(demand_times):
            demand_values[ct] = self.at(t)
        return demand_values

class Source(TimeSeries):
    """
    Water quality source class.

    Parameters
    ----------
    name : string
         Name of the source
    node_name: string
        Injection node
    source_type: string
        Source type, options = CONCEN, MASS, FLOWPACED, or SETPOINT
    quality: float
        Source strength in Mass/Time for MASS and Mass/Volume for CONCEN, 
        FLOWPACED, or SETPOINT
    pattern: Pattern, optional
        If None, then the value will be constant. Otherwise, the Pattern will be used.
    """

    def __init__(self, name, node_name, source_type, quality, pattern):
        super(Source, self).__init__(base=quality, pattern=pattern)
        self.name = name
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

    def __repr__(self):
        fmt = "<Source: '{}', '{}', '{}', {}, {}>"
        return fmt.format(self.name, self.node_name, self.source_type, self._base, self._pattern_name)

    @property
    def quality(self):
        return self._base
    

class Demands(MutableSequence):
    """
    Demands class.  
    
    The Demands object is used to store multiple demands per 
    junction in a list. The class includes specialized demand-specific calls 
    and type checking.
    
    A demand list is a list of demands and can be used with all normal list-
    like commands.
    For example,
    
    >>> from wntr.network.elements import Demands
    >>> dl = Demands()
    >>> len(dl)
    0
    >>> dl.append( (0.5, None, None) )
    >>> len(dl)
    1
    >>> dl[0]
    <TimeSeries: base=0.5, pattern=None, category=None>
    
    The demand list does not have any attributes, but can be created by passing 
    in demand objects or demand tuples as ``(base_demand, pattern, category_name)``
    """
    
    def __init__(self, *args):
        self._list = []
        for object in args:
            self.append(object)

    def __getitem__(self, index):
        """Get the demand at index <==> y = S[index]"""
        return self._list.__getitem__(index)
    
    def __setitem__(self, index, object):
        """Set demand and index <==> S[index] = object"""
        if isinstance(object, (list, tuple)) and len(object) in [2,3]:
            object = TimeSeries(*object)
        elif not isinstance(object, TimeSeries):
            raise ValueError('object must be a TimeSeries or demand tuple')
        return self._list.__setitem__(index, object)
    
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
    
    def insert(self, index, object):
        """S.insert(index, object) - insert object before index"""
        if isinstance(object, (list, tuple)) and len(object) in [2,3]:
            object = TimeSeries(*object)
        elif not isinstance(object, TimeSeries):
            raise ValueError('object must be a TimeSeries or demand tuple')
        self._list.insert(index, object)
    
    def append(self, object):
        """S.append(object) - append object to the end"""
        if isinstance(object, (list, tuple)) and len(object) in [2,3]:
            object = TimeSeries(*object)
        elif not isinstance(object, TimeSeries):
            raise ValueError('object must be a TimeSeries or demand tuple')
        self._list.append(object)
    
    def extend(self, iterable):
        """S.extend(iterable) - extend list by appending elements from the iterable"""
        for object in iterable:
            if isinstance(object, (list, tuple)) and len(object) in [2,3]:
                object = TimeSeries(*object)
            elif not isinstance(object, TimeSeries):
                raise ValueError('object must be a TimeSeries or demand tuple')
            self._list.append(object)

    def clear(self):
        """S.clear() - remove all entries"""
        self._list = []

    def at(self, time, category=None):
        """Get the total demand at a given time - Demand objects must have 
        been initialized with a step size"""
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
        """A list of the base demands, optionally of a single category"""
        res = []
        for dem in self._list:
            if category is None or dem.category == category:
                res.append(dem.base_value)
        return res

    def pattern_list(self, category=None):
        """A list of the patterns, optionally of a single category"""
        res = []
        for dem in self._list:
            if category is None or dem.category == category:
                res.append(dem.pattern)
        return res
    
    def category_list(self):
        """A list of all the pattern categories"""
        res = []
        for dem in self._list:
                res.append(dem.category)
        return res

    def get_values(self, start_time, end_time, time_step):
        """
        Returns the values for a range of times
        
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

