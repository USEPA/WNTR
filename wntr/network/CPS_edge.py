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
from .base import AbstractModel, Link, LinkStatus, Registry

import abc

logger = logging.getLogger(__name__)

class CPS_Edge(six.with_metaclass(abc.ABCMeta, object)):
    """Base class for CPS_Edges.
    
    For details about the different subclasses, see one of the following:
    :class:`~wntr.network.elements.MODBUS`, 
    :class:`~wntr.network.elements.EIP`, and
    :class:`~wntr.network.elements.SER`

    .. rubric:: Constructor
    
    This is an abstract class and should not be instantiated directly.

    Parameters
    -----------
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        WaterNetworkModel object
    name : string
        Name of the CPS_Edge (must be unique among edges of all types)
    

    .. rubric:: Attributes

    .. autosummary::

        name
        edge_type
        coordinates
        tag
    


    """
    def __init__(self, wn, start_node_name, end_node_name, name):
        self._name = name
        self._start_node_name = start_node_name
        self._end_node_name = end_node_name
        self._options = wn._options
        self._node_reg = wn._node_reg
        self._link_reg = wn._link_reg
        self._controls = wn._controls
        self._cps_reg = wn._cps_reg
        self._cps_edges = wn._cps_edges
        self._coordinates = [0,0]


    def _compare(self, other):
        """
        Comparison function

        Parameters
        ----------
        other : Edge
            object to compare with

        Returns
        -------
        bool
            is these the same items
        """        
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
        return "<CPS edge '{}'>".format(self._name)

    @property
    def edge_type(self):
        """str: The edge type (read only)"""
        return 'CPS edge'
    
    @property
    def name(self):
        """str: The name of the edge (read only)"""
        return self._name
    
    @property
    def tag(self):
        """str: A tag or label for the edge"""
        return self._tag
    @tag.setter
    def tag(self, tag):
        self._tag = tag

    @property
    def coordinates(self):
        """tuple: The edge coordinates, (x,y)"""
        return self._coordinates
    @coordinates.setter
    def coordinates(self, coordinates):
        if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2:
            self._coordinates = tuple(coordinates)
        else:
            raise ValueError('coordinates must be a 2-tuple or len-2 list')

    def to_dict(self):
        """Dictionary representation of the edge"""
        d = {}
        d['name'] = self.name
        d['edge_type'] = self.edge_type
        for k in dir(self):
            if not k.startswith('_') and \
				k not in [ ]: #should be list of attributes and values associated with initial and ongoing operation-- see below
              #k not in ['demand', 'base_demand', 'head', 'leak_area', 'leak_demand',
                    #    'leak_discharge_coeff', 'leak_status', 'level', 'pressure', 'quality', 'vol_curve', 'head_timeseries']: 
                try:
                    val = getattr(self, k)
                    if not isinstance(val, types.MethodType):
                        if hasattr(val, "to_ref"):
                            d[k] = val.to_ref()
                        elif hasattr(val, "to_list"):
                            d[k] = val.to_list()
                        elif hasattr(val, "to_dict"):
                            d[k] = val.to_dict()
                        elif isinstance(val, (enum.IntEnum, enum.Enum)):
                            d[k] = str(val)
                        else:
                            d[k] = val
                except DeprecationWarning: pass
        return d

    def to_ref(self):
        return self._name


    

class MODBUS(CPS_Edge):
    """
    MODBUS class, inherited from CPS_Edge.

    CURRENT INSTANTIATION HAS NO SUBCLASSES

    .. rubric:: Constructor
    
    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pump` method. 
    Direct creation through the constructor is highly discouraged.
    
	This class is intended to be instantiated through a TODO:: constructor method
	in the TODO:: ~wntr.network.model.CyberNetworkModel class
	
	Control unit for entire network or subset of network. Can issue change_control commands to EIP class objects, and (if implemented) monitor and report on network latency and behaviors.
	
    Parameters
    ----------
    name : string
        Name of the MODBUS unit
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this CPS_Edge will belong to.
    

    .. rubric:: Attributes

    .. autosummary::

        name
        edge_type
        owned_list
        owner_list


    """

    def __init__(self, name, wn):
        super().__init__(wn, start_node_name, end_node_name, name)

    def _compare(self, other):
        if not super(MODBUS, self)._compare(other):
            return False
        return True
    
    @property
    def edge_type(self):
        """str : ``"MODBUS"`` (read only)"""
        return 'MODBUS'
    
            

        
class EIP(CPS_Edge):
    """
    EIP class, inherited from CPS_Edge.

    CURRENT INSTANTIATION HAS NO SUBCLASSES

    .. rubric:: Constructor
    
    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_EIP` method. 
    Direct creation through the constructor is highly discouraged.
    
	This class is intended to be instantiated through a TODO:: constructor method
	in the TODO:: ~wntr.network.model.CyberNetworkModel class
	
	Handles individual controls for wntr network.
	
    Parameters
    ----------
    name : string
        Name of the cps edge
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this cps edge will belong to.
    

    .. rubric:: Attributes

    .. autosummary::

        name
        edge_type
        coordinates
        tag

    """

    def __init__(self, name, wn):
        super(EIP, start_node_name, end_node_name, self).__init__(wn, name)
        
    def _compare(self, other):
        if not super(EIP, self)._compare(other):
            return False
        return True

    @property
    def edge_type(self):
        """str : ``"EIP"`` (read only)"""
        return 'EIP'
    
		
		
class SER(CPS_Edge):
    """
    SER class, inherited from CPS_Edge.

    CURRENT INSTANTIATION HAS NO SUBCLASSES

    .. rubric:: Constructor
    
    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pump` method. 
    Direct creation through the constructor is highly discouraged.
    
	This class is intended to be instantiated through a TODO:: constructor method
	in the TODO:: ~wntr.network.model.CyberNetworkModel class
	
	Differentiated from EIP by lack of change_control function, as SER are generally more rugged and individually programmed on-site
	
    Parameters
    ----------
    name : string
        Name of the pump
    start_edge_name : string
         Name of the start edge
    end_edge_name : string
         Name of the end edge
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
        initial_status
        initial_setting
        speed_timeseries
        efficiency
        energy_price
        energy_pattern
        tag
        vertices


    .. rubric:: Read-only simulation results

    .. autosummary::

        flow
        headloss
        velocity
        quality
        status
        setting

    """

    def __init__(self, name, wn):
        super(SER, start_node_name, end_node_name, self).__init__(wn, name)
        #self._speed_timeseries = TimeSeries(wn._pattern_reg, 1.0)

    def _compare(self, other):
        if not super(SER, self)._compare(other):
            return False
        return True

    @property
    def edge_type(self):
        """str : ``"SER"`` (read only)"""
        return 'SER'

        
        
        
class CPSEdgeRegistry(Registry):
    """A registry for edges."""
    
    __subsets = [
        "_MODBUS",
        "_EIP",
        "_SER",
    ]

    def __init__(self, model):
        super(CPSEdgeRegistry, self).__init__(model)
        self._listMODBUS = OrderedSet()
        self._listEIP = OrderedSet()
        self._listSER = OrderedSet()

    def _finalize_(self, model):
        super()._finalize_(model)

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise ValueError("Registry keys must be strings")
        self._data[key] = value
        if isinstance(value, MODBUS):
            self._listMODBUS.add(key)
        elif isinstance(value, EIP):
            self._listEIP.add(key)
        elif isinstance(value, SER):
            self._listSER.add(key)

    def __delitem__(self, key):
        try:
            if self._usage and key in self._usage and len(self._usage[key]) > 0:
                raise RuntimeError(
                    "cannot remove %s %s, still used by %s" % (self.__class__.__name__, key, str(self._usage[key]))
                )
            elif key in self._usage:
                self._usage.pop(key)
            edge = self._data.pop(key)
            self._listMODBUS.discard(key)
            self._listEIP.discard(key)
            self._listSER.discard(key)
            return edge
        except KeyError:
            return

    def __call__(self, edge_type=None):
        """
        Returns a generator to iterate over all edges of a specific edge type.
        If no edge type is specified, the generator iterates over all edges.

        Parameters
        ----------
        edge_type: edge type
            edge type, options include
            wntr.network.model.CPS_Edge,
            wntr.network.model.MODBUS,
            wntr.network.model.EIP,
            wntr.network.model.SER, or None. Default = None.
            Note None and wntr.network.model.CPS_Edge produce the same results.

        Returns
        -------
        A generator in the format (name, object).
        """
        if edge_type == None:
            for edge_name, edge in self._data.items():
                yield edge_name, edge
        elif edge_type == MODBUS:
            for edge_name in self._listMODBUS:
                yield edge_name, self._data[edge_name]
        elif edge_type == EIP:
            for edge_name in self._listEIP:
                yield edge_name, self._data[edge_name]
        elif edge_type == SER:
            for edge_name in self._listSER:
                yield edge_name, self._data[edge_name]
        else:
            raise RuntimeError("edge_type, " + str(edge_type) + ", not recognized.")

    def add_MODBUS(
        self,
        name,        
        start_node_name,
        end_node_name,
        coordinates=None,
    ):
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
            X-Y coordinates of the edge location.
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
        assert (
            isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(" ") == -1
        ), "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(" ") == -1
        ), "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(coordinates, (type(None), (tuple, list,))), "coordinates must be a tuple"

        MODBUS = MODBUS(name, self)
        self[name] = MODBUS
        if coordinates is not None:
            MODBUS.coordinates = coordinates
            

    def add_EIP(
        self,
        name,
        start_node_name,
        end_node_name,
        coordinates=None,
    ):
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
            X-Y coordinates of the edge location.
            
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
        assert isinstance(coordinates, (type(None), (tuple,list,))), "coordinates must be a tuple"

        EIP = EIP(name, self)
        self[name] = EIP
        if coordinates is not None:
            EIP.coordinates = coordinates

    def add_SER(
        self, 
        name,
        start_node_name,
        end_node_name,
        coordinates=None,
    ):
        """
        Adds a remote terminal unit to the water network model.

        Parameters
        ----------
        name : string
        coordinates : tuple of floats, optional
            X-Y coordinates of the edge location.
        
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
        assert isinstance(coordinates, (type(None), (tuple, list))), "coordinates must be a tuple"

        base_head = float(base_head)

        SER = SER(name, self)
        self[name] = SER
        if coordinates is not None:
            SER.coordinates = coordinates

    @property
    def MODBUS_names(self):
        """List of names of all MODBUS edges"""
        return self._listMODBUS

    @property
    def EIP_names(self):
        """List of names of all EIP edges"""
        return self._listEIP

    @property
    def SER_names(self):
        """List of names of all SER edges"""
        return self._listSER

    def MODBUS_edges(self):
        """Generator to get all MODBUS edges
        
        Yields
        ------
        name : str
            The name of the MODBUS edge
        edge : MODBUS
            The MODBUS object    
            
        """
        for edge_name in self._listMODBUS:
            yield edge_name, self._data[edge_name]

    def EIP_edges(self):
        """Generator to get all EIP
        
        Yields
        ------
        name : str
            The name of the tank
        edge : Tank
            The tank object    
            
        """
        for edge_name in self._listEIP:
            yield edge_name, self._data[edge_name]

    def SER_edges(self):
        """Generator to get all reservoirs
        
        Yields
        ------
        name : str
            The name of the reservoir
        edge : Reservoir
            The reservoir object    
            
        """
        for edge_name in self._listSER:
            yield edge_name, self._data[edge_name]

class CPSEdgeType(enum.IntEnum):
    """
    Enum class for edge types.

    .. rubric:: Enum Members

    .. autosummary::

        MODBUS
        EIP
        SER

    """
    MODBUS = 0  #: edge is a MODBUS unit
    EIP = 1  #: edge is a EIP
    SER = 2  #: edge is an SER

    def __init__(self, val):
        mmap = getattr(self, '_member_map_')
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return int(self) == int(other) and (isinstance(other, int) or \
               self.__class__.__name__ == other.__class__.__name__)
