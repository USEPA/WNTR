"""
The wntr.network.base module includes base classes for network elements and 
the network model.

.. rubric:: Contents

.. autosummary::

    AbstractModel
    Subject
    Observer
    Node
    Link
    Registry
    NodeType
    LinkType
    LinkStatus

"""
import logging
import six
from six import string_types
import types
from wntr.utils.ordered_set import OrderedSet

import enum
import sys
from collections.abc import MutableSequence, MutableMapping
from collections import OrderedDict
from wntr.utils.ordered_set import OrderedSet

import abc

logger = logging.getLogger(__name__)


class AbstractModel(object):
    """
    Base class for water network models.
    """
    pass


class Subject(object):
    """
    Base class for the subject in an observer design pattern.
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
    Base class for the observer in an observer design pattern.
    """
    @abc.abstractmethod
    def update(self, subject):
        pass


class Node(six.with_metaclass(abc.ABCMeta, object)):
    """Base class for nodes.
    
    For details about the different subclasses, see one of the following:
    :class:`~wntr.network.elements.Junction`, 
    :class:`~wntr.network.elements.Tank`, and
    :class:`~wntr.network.elements.Reservoir`

    Parameters
    -----------
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        WaterNetworkModel object
    name : string
        Name of the node (must be unique among nodes of all types)


    """
    def __init__(self, wn, name):
        self._name = name
        self._head = None
        self._demand = None  
        self._leak_demand = None
        self._initial_quality = None
        self._tag = None
        self._leak = False
        self._leak_status = False
        self._leak_area = 0.0
        self._leak_discharge_coeff = 0.0
        self._options = wn._options
        self._node_reg = wn._node_reg
        self._link_reg = wn._link_reg
        self._controls = wn._controls
        self._pattern_reg = wn._pattern_reg
        self._curve_reg = wn._curve_reg
        self._coordinates = [0,0]
        self._source = None
        self._is_isolated = False

    def _compare(self, other):
        if not type(self) == type(other):
            return False
        if self.name == other.name and \
           self.initial_quality == other.initial_quality and \
           self.tag == other.tag:
               return True
        return False

    def __str__(self):
        return self._name

    def __repr__(self):
        return "<Node '{}'>".format(self._name)

    @property
    def head(self):
        """float: The current head at the node"""
        return self._head
    @head.setter
    def head(self, value):
        self._head = value

    @property
    def demand(self):
        """float: The current demand at the node"""
        return self._demand
    @demand.setter
    def demand(self, value):
        self._demand = value

    @property
    def leak_demand(self):
        """float: The current demand at the node"""
        return self._leak_demand
    @leak_demand.setter
    def leak_demand(self, value):
        self._leak_demand = value

    @property
    def leak_status(self):
        """bool: The current leak status at the node"""
        return self._leak_status
    @leak_status.setter
    def leak_status(self, value):
        self._leak_status = value

    @property
    def leak_area(self):
        """float: The leak area at the node"""
        return self._leak_area
    @leak_area.setter
    def leak_area(self, value):
        self._leak_area = value

    @property
    def leak_discharge_coeff(self):
        """float: The leak discharge coefficient"""
        return self._leak_discharge_coeff
    @leak_discharge_coeff.setter
    def leak_discharge_coeff(self, value):
        self._leak_discharge_coeff = value

    @property
    def node_type(self):
        """str: The node type"""
        return 'Node'
    
    @property
    def name(self):
        """str: The name of the node"""
        return self._name
    
    @property
    def tag(self):
        """str: A tag or label for the node"""
        return self._tag
    @tag.setter
    def tag(self, tag):
        self._tag = tag

    @property
    def initial_quality(self):
        """float: The initial quality (concentration) at the node"""
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
        """tuple: The node coordinates, (x,y)"""
        return self._coordinates
    @coordinates.setter
    def coordinates(self, coordinates):
        if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2:
            self._coordinates = tuple(coordinates)
        else:
            raise ValueError('coordinates must be a 2-tuple or len-2 list')

    def todict(self):
        """Dictionary representation of the node"""
        d = {}
        for k in dir(self):
            if not k.startswith('_'):
                val = getattr(self, k)
                if not isinstance(val, types.MethodType):
                    d[k] = val
        return d


class Link(six.with_metaclass(abc.ABCMeta, object)):
    """Base class for links.

    For details about the different subclasses, see one of the following:
    :class:`~wntr.network.elements.Pipe`, 
    :class:`~wntr.network.elements.Pump`, and
    :class:`~wntr.network.elements.Valve`

    Parameters
    ----------
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        WaterNetworkModel object
    link_name : string
        Name of the link
    start_node_name : string
        Name of the start node
    end_node_name : string
        Name of the end node
    
    """
    def __init__(self, wn, link_name, start_node_name, end_node_name):
        # Set the registries
        self._options = wn._options
        self._node_reg = wn._node_reg
        self._link_reg = wn._link_reg
        self._controls = wn._controls
        self._pattern_reg = wn._pattern_reg
        self._curve_reg = wn._curve_reg
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
        self._user_status = LinkStatus.opened
        self._internal_status = LinkStatus.active
        self._prev_setting = None
        self._setting = None
        self._flow = None
        self._is_isolated = False

    def _compare(self, other):
        """
        Parameters
        ----------
        other: Link

        Returns
        -------
        bool
        """
        if not type(self) == type(other):
            return False
        if self.name != other.name:
            return False
        if self.tag != other.tag:
            return False
        if self.initial_status != other.initial_status:
            return False
        if self.initial_setting != other.initial_setting:
            return False
        if self.start_node_name != other.start_node_name:
            return False
        if self.end_node_name != other.end_node_name:
            return False
        return True
    
    def __str__(self):
        return self._link_name

    def __repr__(self):
        return "<Link '{}'>".format(self._link_name)

    @property
    def link_type(self):
        """str: The link type"""
        return 'Link'

    @property
    def initial_status(self):
        """:class:`~wntr.network.base.LinkStatus`: The initial status (`Opened`, `Closed`, `Active`) of the Link"""
        return self._initial_status
    @initial_status.setter
    def initial_status(self, status):
        if not isinstance(status, LinkStatus):
            status = LinkStatus[status]
        self._initial_status = status
        
    @property
    def initial_setting(self):
        """float: The initial setting for the link (if `Active`)"""
        return self._initial_setting
    @initial_setting.setter
    def initial_setting(self, setting):
        # TODO: typechecking
        self._initial_setting = setting

    @property
    def start_node(self):
        """:class:`~wntr.network.base.Node`: The start node object."""
        return self._start_node
    @start_node.setter
    def start_node(self, node):
        self._node_reg.remove_usage(self.start_node_name, (self._link_name, self.link_type))
        self._node_reg.add_usage(node.name, (self._link_name, self.link_type))
        self._start_node = self._node_reg[node.name]

    @property
    def end_node(self):
        """:class:`~wntr.network.base.Node`: The end node object."""
        return self._end_node
    @end_node.setter
    def end_node(self, node):
        self._node_reg.remove_usage(self.end_node_name, (self._link_name, self.link_type))
        self._node_reg.add_usage(node.name, (self._link_name, self.link_type))
        self._end_node = self._node_reg[node.name]

    @property
    def start_node_name(self):
        """str: The name of the start node (read only)"""
        return self._start_node.name
    
    @property
    def end_node_name(self):
        """str: The name of the end node (read only)"""
        return self._end_node.name

    @property
    def name(self):
        """str: The link name (read-only)"""
        return self._link_name

    @property
    def flow(self):
        """float: Current flow through the link (read only)"""
        return self._flow
    
    @property
    @abc.abstractmethod
    def status(self):
        """:class:`~wntr.network.base.LinkStatus`: Current status of the link"""
        pass
    @status.setter
    @abc.abstractmethod
    def status(self, status):
        self._user_status = status
    
    @property
    def setting(self):
        """float: The current setting of the link"""
        return self._setting
    @setting.setter
    def setting(self, setting):
        self._setting = setting
    
    @property
    def tag(self):
        """str: A tag or label for this link"""
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
        """Dictionary representation of the link"""
        d = {}
        for k in dir(self):
            if not k.startswith('_'):
                val = getattr(self, k)
                if not isinstance(val, types.MethodType):
                    d[k] = val
        return d


class Registry(MutableMapping):
    """Base class for registries.
    
    Parameters
    ----------
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        WaterNetworkModel object
    """
    
    def __init__(self, wn):
        if not isinstance(wn, AbstractModel):
            raise ValueError('Registry must be initialized with a model')
#        self._m = model
        self._data = OrderedDict()
        self._usage = OrderedDict()

    def _finalize_(self, wn):
        self._options = wn._options
        self._pattern_reg = wn._pattern_reg
        self._curve_reg = wn._curve_reg
        self._node_reg = wn._node_reg
        self._link_reg = wn._link_reg
        self._controls = wn._controls
        self._sources = wn._sources
    
    def __getitem__(self, key):
        if not key:
            return None
        try:
            return self._data[key]
        except KeyError:
            try:
                return self._data[key.name]
            except:
                return self._data[str(key)]
            

    def __setitem__(self, key, value):
        if not isinstance(key, string_types):
            raise ValueError('Registry keys must be strings')
        self._data[key] = value
    
    def __delitem__(self, key):
        try:
            if self._usage and key in self._usage and len(self._usage[key]) > 0:
                raise RuntimeError('cannot remove %s %s, still used by %s', 
                                   self.__class__.__name__,
                                   key,
                                   self._usage[key])
            elif key in self._usage:
                self._usage.pop(key)
            return self._data.pop(key)
        except KeyError:
            # Do not raise an exception if there is no key of that name
            return
    
    def __iter__(self):
        return self._data.__iter__()
    
    def __len__(self):
        return len(self._data)

    def __call__(self):
        for key, value in self._data.items():
            yield key, value

    def usage(self):
        """Generator to get the usage for all objects in the registry
        
        Yields
        ------
        key : str
            The name of the object in the registry
        value : tuple of (str, str)
            Tuple of (name, typestr) of the external items using the object
        """
        for k, v in self._usage.items():
            yield k, v
        
    def get_usage(self, key):
        """Get a set of items using an object by key.
        
        Returns
        -------
        set of 2-tuples
            Set of (name, typestr) of the external object using the item
            
        """
        try:
            return self._usage[key]
        except KeyError:
            try:
                return self._usage[str(key)]
            except KeyError:
                return None
        return None

    def orphaned(self):
        """Get a list of orphaned usages.
        
        If removed without appropriate checks, it is possible that a some other 
        item will point to an object that has been deleted. (This is why the user
        should always use the "remove_*" methods). This method returns a list of 
        names for objects that are referenced, but no longer exist.
        
        Returns
        -------
        set
            The names of any orphaned items
        
        """
        defined = set(self._data.keys())
        assigned = set(self._usage.keys())
        return assigned.difference(defined)
    
    def unused(self):
        """Get a list of items which are unused by other objects in the model.
        
        In most cases, this method will give little information. For nodes, however,
        this method could be important to identify a node which has become completely 
        disconnected from the network. For patterns or curves, it may be used to find
        extra patterns or curves that are no longer necessary (or which the user 
        forgot ot assign). It is not terribly useful for links.
        
        Returns
        -------
        set
            The names of any unused objects in the registry
            
        """
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
        if not (key in self._usage):
            self._usage[key] = OrderedSet()
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

    def todict(self):
        """Dictionary representation of the registry"""
        d = dict()
        for k, v in self._data.items():
            d[k] = v.todict()
        return d
    
    def tolist(self):
        """List representation of the registry"""
        l = list()
        for k, v in self._data.items():
            l.append(v.todict())
        return l


class NodeType(enum.IntEnum):
    """
    Enum class for node types.

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
    Enum class for link types.

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
    Enum class for link statuses.

    .. warning::
        This is NOT the class for determining output status from an EPANET binary file.
        The class for output status is wntr.epanet.util.LinkTankStatus.

    .. rubric:: Enum Members

    =================  ==================================================================
    :attr:`~Closed`    Pipe/valve/pump is closed.
    :attr:`~Opened`    Pipe/valve/pump is open.
    :attr:`~Open`      Alias to "Opened"
    :attr:`~Active`    Valve is partially open.
    =================  ==================================================================

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
        return int(self) == int(other) and (isinstance(other, int) or
                                            self.__class__.__name__ == other.__class__.__name__)
