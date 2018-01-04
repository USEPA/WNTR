"""
The wntr.network.base module includes base classes for network components.
"""
import copy
import logging
import six
from six import string_types
import warnings

import enum
import sys
if sys.version_info[0] == 2:
    from collections import MutableSequence, MutableMapping
else:
    from collections.abc import MutableSequence, MutableMapping
from collections import OrderedDict
from wntr.utils.ordered_set import OrderedSet

import abc

import numpy as np
import networkx as nx

from .options import TimeOptions, HydraulicOptions, WaterNetworkOptions

logger = logging.getLogger(__name__)


class AbstractModel(six.with_metaclass(abc.ABCMeta, object)):
    """
    Abstract water network model class.
    """
    @property
    @abc.abstractmethod
    def options(self): pass

    @property
    @abc.abstractmethod
    def nodes(self): pass

    @property
    @abc.abstractmethod
    def links(self): pass

    @property
    @abc.abstractmethod
    def sources(self): pass

    @property
    @abc.abstractmethod
    def patterns(self): pass

    @property
    @abc.abstractmethod
    def curves(self): pass

    @property
    @abc.abstractmethod
    def controls(self): pass


class Subject(object):
    """
    Subject base class for the observer design pattern.
    """
    def __init__(self):
        self._observers = OrderedSet()

    def subscribe(self, observer):
        self._observers.add(observer)

    def unsubscribe(self, observer):
        self._observers.remove(observer)

    def notify(self):
        for o in self._observers:
            o.update(self)


class Observer(six.with_metaclass(abc.ABCMeta, object)):
    """
    Observer base class for the observer design pattern.
    """
    @abc.abstractmethod
    def update(self, subject):
        pass


class Node(six.with_metaclass(abc.ABCMeta, object)):
    """
    Node base class.

    Parameters
    -----------
    name : string
        Name of the node
    """
    def __init__(self, model, name):
        if not isinstance(model, AbstractModel):
            raise ValueError('valid model must be passed as first argument')
        self._name = name
        self._prev_head = None
        self.head = None
        self._prev_demand = None
        self.demand = None
        self.leak_demand = None
        self._prev_leak_demand = None
        self._initial_quality = None
        self.tag = None
        self._leak = False
        self.leak_status = False
        self.leak_area = 0.0
        self.leak_discharge_coeff = 0.0
        self._options = model.options
        self._node_reg = model.nodes
        self._link_reg = model.links
        self._control_reg = model.controls
        self._pattern_reg = model.patterns
        self._curve_reg = model.curves
        self._coordinates = [0,0]
        self._source = None

    def __hash__(self):
        return hash('Node/'+self._name)

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self._name == other._name and \
           self.initial_quality == other.initial_quality and \
           self.tag == other.tag:
               return True
        return False

    def __str__(self):
        return self._name

    def __repr__(self):
        return "<Node '{}'>".format(self._name)

    @property
    def node_type(self):
        """Returns the node type"""
        return 'Node'
    
    @property
    def name(self):
        """Returns the name of the node"""
        return self._name
    
    @property
    def initial_quality(self):
        """Returns the initial quality (concentration) of the node. Can be a float or list of floats."""
        if not self._initial_quality:
            return 0.0
        return self._initial_quality

    @initial_quality.setter
    def initial_quality(self, value):
        if value and not isinstance(value, (list, float, int)):
            raise ValueError('Initial quality must be a float or a list')
        self._initial_quality = value

    @property
    def coordinates(self):
        """Returns the node coordinates"""
        return self._coordinates
    
    @coordinates.setter
    def coordinates(self, coordinates):
        if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2:
            self._coordinates = tuple(coordinates)
        else:
            raise ValueError('coordinates must be a 2-tuple or len-2 list')
    
    def todict(self):
        d = dict(name=self.name, 
                 node_type=self.node_type)
        if self.tag:
            d['tag'] = self.tags
        if self.initial_quality:
            d['init_quality'] = self.initial_quality
        d['coordinates'] = self.coordinates
        return d

class Link(six.with_metaclass(abc.ABCMeta, object)):
    """
    Link base class.

    Parameters
    ----------
    link_name : string
        Name of the link
    start_node_name : string
        Name of the start node
    end_node_name : string
        Name of the end node
    node_registry : NodeRegistry
        The registry object for tracking node usage
    graph : WntrNetworkDiGraph
        The network graph (for modifying start and end nodes)
    pattern_registry : PatternRegistry, optional
        An optional registry object for tracking pattern usage
    curve_registry : CurveRegistry, optional
        An optional registry object for tracking curve usage
    
    """
    def __init__(self, model, link_name, start_node_name, end_node_name):
        if not isinstance(model, AbstractModel):
            raise ValueError('valid model must be passed as first argument')

        # Set the registries
        self._options = model.options
        self._node_reg = model.nodes
        self._link_reg = model.links
        self._control_reg = model.controls
        self._pattern_reg = model.patterns
        self._curve_reg = model.curves
        # Set the link name
        self._link_name = link_name
        # Set and register the starting node
        self._start_node = self._node_reg[start_node_name]
        self._node_reg.add_usage(start_node_name, (link_name, self.link_type))
        # Set and register the ending node
        self._end_node = self._node_reg[end_node_name]
        self._node_reg.add_usage(end_node_name, (link_name, self.link_type))
        # Set up other metadata fields
        self._initial_status = LinkStatus.opened
        self._initial_setting = None
        self._vertices = []
        self._tag = None
        # Model state variables
        self._prev_status = None
        self._status = LinkStatus.opened
        self._base_status = LinkStatus.opened
        self._user_status = LinkStatus.opened
        self._internal_status = LinkStatus.active
        self._prev_setting = None
        self._setting = None
        self._prev_flow = None
        self._flow = None

    def __hash__(self):
        return hash('Link/'+self._name)
    
    def __str__(self):
        return self._link_name

    def __repr__(self):
        return "<Link '{}'>".format(self._link_name)

    @property
    def link_type(self):
        return 'Link'

    @property
    def initial_status(self):
        """The initial status (Opened, Closed, Active) of the Link"""
        return self._initial_status
    @initial_status.setter
    def initial_status(self, status):
        if not isinstance(status, LinkStatus):
            status = LinkStatus[status]
        self._initial_status = status
        
    @property
    def initial_setting(self):
        """The initial setting for the link (if Active)"""
        return self._initial_setting
    @initial_setting.setter
    def initial_setting(self, setting):
        # TODO: typechecking
        self._initial_setting = setting

    @property
    def start_node(self):
        """The name of the start node"""
        return self._start_node
    @start_node.setter
    def start_node(self, name):
        self._node_reg.remove_usage(self._start_node.name, (self._link_name, self.link_type))
        self._node_reg.add_usage(name, (self._link_name, self.link_type))
        self._start_node = self._node_reg[name]

    @property
    def end_node(self):
        """The name of the end node"""
        return self._end_node
    @end_node.setter
    def end_node(self, name):
        self._node_reg.remove_usage(self._end_node.name, (self._link_name, self.link_type))
        self._node_reg.add_usage(name, (self._link_name, self.link_type))
        self._end_node_name = self._node_reg[name]

    @property
    def start_node_name(self):
        return self._start_node.name
    
    @property
    def end_node_name(self):
        return self._end_node.name

    @property
    def name(self):
        """The link name (read-only)"""
        return self._link_name

    @property
    def flow(self):
        """Current flow through the link"""
        return self._flow
    
    @property
    def status(self):
        """Current status of the link"""
        return self._status
    @status.setter
    def status(self, status):
        self._status = status
    
    @property
    def setting(self):
        """The current setting of the link"""
        return self._setting
    @setting.setter
    def setting(self, setting):
        self._setting = setting
    
    @property
    def tag(self):
        """A tag or label for this link"""
        return self._tag
    @tag.setter
    def tag(self, tag):
        self._tag = tag
        
    @property
    def vertices(self):
        """A list of curve points, in the direction of start node to end node.
        
        The vertices should be listed as a list of (x,y) tuples when setting.
        """
        return self._vertices
    @vertices.setter
    def vertices(self, points):
        if not isinstance(points, list):
            raise ValueError('vertices must be a list of 2-tuples')
        for pt in points:
            if not isinstance(pt, tuple) or len(pt) != 2:
                raise ValueError('vertices must be a list of 2-tuples')
        self._vertices = points
    
    def todict(self):
        d = dict(name=self.name, 
                 start_node=self._start_node.name,
                 end_node=self._end_node.name,
                 link_type=self.link_type)
        if self._tag:
            d['tag'] = self._tag
        if self._initial_status is not LinkStatus.opened:
            d['init_status'] = str(self._initial_status)
        if self._initial_setting:
            d['init_setting'] = self._initial_setting
        if self._vertices:
            d['vertices'] = self._vertices
        return d


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

class Pattern(object):
    """
    Pattern base class.
    
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
        return hash('Pattern/'+self._name)
        
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
    def BinaryPattern(cls, name, start_time, end_time, step_size, duration, wrap=False):
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


class Registry(MutableMapping):
    """
    Registry base class.
    """
    def __init__(self, model):
        if not isinstance(model, AbstractModel):
            raise ValueError('Registry must be initialized with a model')
        self._m = model
        self._data = OrderedDict()
        self._usage = OrderedDict()

    @property
    def _options(self):
        return self._m.options
    
    @property
    def _patterns(self):
        return self._m.patterns
    
    @property
    def _curves(self):
        return self._m.curves

    @property
    def _nodes(self):
        return self._m.nodes
    
    @property
    def _links(self):
        return self._m.links

    @property
    def _controls(self):
        return self._m.controls
    
    @property
    def _sources(self):
        return self._m.sources

    def __getitem__(self, key):
        if not key:
            return None
        try:
            return self._data[key]
        except KeyError:
            return self._data[str(key)]

    def __setitem__(self, key, value):
        if not isinstance(key, string_types):
            raise ValueError('Registry keys must be strings')
        self._data[key] = value
    
    def __delitem__(self, key):
        try:
            if self._usage and len(self._usage[key]) > 0:
                raise RuntimeError('cannot remove %s %s, still used by %s', 
                                   self.__class__.__name__,
                                   key,
                                   self._usage[key])
            elif self._usage:
                self._usage.pop(key)
            return self._data.pop(key)
        except KeyError:
            return
    
    def __iter__(self):
        return self._data.__iter__()
    
    def __len__(self):
        return len(self._data)

    def __call__(self):
        for key, value in self._data.items():
            yield key, value
    
    def usage(self):
        return self._usage
        
    def get_usage(self, key):
        try:
            return self._usage[key]
        except KeyError:
            try:
                return self._usage[str(key)]
            except KeyError:
                return None
        return None

    def orphaned(self):
        defined = set(self._data.keys())
        assigned = set(self._usage.keys())
        return assigned.difference(defined)
    
    def unused(self):
        defined = set(self._data.keys())
        assigned = set(self._usage.keys())
        return defined.difference(assigned)

    def clear_usage(self, key):
        """if key in usage, clear usage[key]"""
        if not key:
            return
        self._usage[key].clear()
    
    def add_usage(self, key, *args):
        """add args to usage[key]"""
        if not key:
            return
        if not key in self._usage:
            self._usage[key] = set()
        for arg in args:
            self._usage[key].add(arg)
    
    def remove_usage(self, key, *args):
        """remove args from usage[key]"""
        if not key:
            return
        for arg in args:
            self._usage[key].discard(arg)
        if len(self._usage[key]) < 1:
            self._usage.pop(key)
            
    def tostring(self):
        s = 'Registry: {}\n'.format(self.__class__.__name__)
        s += '  Total entries defined: {}\n'.format(len(self._data))
        s += '  Total registered as used: {}\n'.format(len(self._usage))
        if len(self.orphaned()) > 0:
            s += '  Total used but undefined: {}\n'.format(len(self.orphaned()))
        return s
        
    def todict(self):
        d = dict()
        for k, v in self._data.items():
            d[k] = v.todict()
        return d
    
    def tolist(self):
        l = list()
        for k, v in self._data.items():
            l.append(v.todict())
        return l


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

