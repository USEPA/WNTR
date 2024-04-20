import logging
import six
from six import string_types
import types
from wntr.utils.ordered_set import OrderedSet
# PLC-communication and emulation libraries
import pymodbus
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
    ModbusSparseDataBlock,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import (
    StartAsyncSerialServer,
    StartAsyncTcpServer,
    StartAsyncTlsServer,
    StartAsyncUdpServer,
)
from pycomm3 import LogixDriver
import awlsim

import enum
import sys
from collections.abc import MutableSequence, MutableMapping
from collections import OrderedDict
from wntr.utils.ordered_set import OrderedSet
from .base import AbstractModel, Link, LinkStatus, Registry
import wntr.epanet.io
from wntr.epanet.util import (EN, FlowUnits, HydParam, MassUnits, MixType, PressureUnits,
                   QualParam, QualType, ResultType, StatisticsType, from_si,
                   to_si)
import abc

logger = logging.getLogger(__name__)

class CPS_Node(six.with_metaclass(abc.ABCMeta, object)):
    """Base class for cps_nodes.
    
    For details about the different subclasses, see one of the following:
    :class:`~wntr.network.elements.SCADA`, 
    :class:`~wntr.network.elements.PLC`, and
    :class:`~wntr.network.elements.RTU`

    .. rubric:: Constructor
    
    This is an abstract class and should not be instantiated directly.

    Parameters
    -----------
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        WaterNetworkModel object
    name : string
        Name of the cps_node (must be unique among nodes of all types)
    

    .. rubric:: Attributes

    .. autosummary::

        name
        node_type
        coordinates
        tag
    


    """
    def __init__(self, wn, name, coordinates=[0,0]):
        self._wn = wn
        self._name = name
        self._options = wn._options
        self._node_reg = wn._node_reg
        self._link_reg = wn._link_reg
        self._controls = wn._controls
        self._cps_reg = wn._cps_reg
        self._cps_edges = wn._cps_edges
        self._coordinates = coordinates
        self._edges = OrderedSet()

    def _compare(self, other):
        """
        Comparison function

        Parameters
        ----------
        other : Node
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
        return "<CPS Node '{}'>".format(self._name)

    @property
    def node_type(self):
        """str: The node type (read only)"""
        return 'CPS Node'
    
    @property
    def name(self):
        """str: The name of the node (read only)"""
        return self._name
    
    @property
    def tag(self):
        """str: A tag or label for the node"""
        return self._tag
    @tag.setter
    def tag(self, tag):
        self._tag = tag

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

    def to_dict(self):
        """Dictionary representation of the node"""
        d = {}
        d['name'] = self.name
        d['node_type'] = self.node_type
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
        
    def add_edge(self, edge_name):
        """
        Add an edge to the internal list of connected edges
        Proper syntax is 'node1_edgeType_node2'
        """
        if edge_name not in self._edges:
            self._edges.add(edge_name)
        else: 
            raise ValueError(
                "The name provided for the edge is already present. Please ensure that the edge name is unique."
            )        
        
    def del_edge(self, edge_name):
        """Remove an edge from the internal list of connected edges"""
        if edge_name not in self._edges:
            raise ValueError(
                "The name provided for the edge to be removed is not recognized. Please check that the edge you intend to remove exists in the network."
            )
        else: 
            self._edges.remove(edge_name)
        
    def to_ref(self):
        return self._name
        
    def change_control(self, original, original_name, modified, modified_name):
        pass
    
    def disable_control(self, control):
        pass
        
    def disable_node(self):
        for control in list(self._controls):
            if self._controls[control]._cps_node == self._name:
                self._controls.pop(control)
    

class SCADA(CPS_Node):
    """
    SCADA class, inherited from CPS_Node.

    CURRENT INSTANTIATION HAS NO SUBCLASSES

    .. rubric:: Constructor
    
    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pump` method. 
    Direct creation through the constructor is highly discouraged.
    
	This class is intended to be instantiated through a TODO:: constructor method
	in the TODO:: ~wntr.network.model.CyberNetworkModel class
	
	Control unit for entire network or subset of network. Can issue change_control commands to PLC class objects, and (if implemented) monitor and report on network latency and behaviors.
	
    Parameters
    ----------
    name : string
        Name of the scada unit
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this CPS_Node will belong to.
    

    .. rubric:: Attributes

    .. autosummary::

        name
        node_type
        owned_list
        owner_list


    """

    def __init__(self, name, wn, coordinates=[0,0]):
        super().__init__(wn, name, coordinates=[0,0])
        self._owned_list = OrderedSet()
        self._owner_list = OrderedSet()

    def _compare(self, other):
        if not super(SCADA, self)._compare(other):
            return False
        return True
    
    @property
    def node_type(self):
        """str : ``"SCADA"`` (read only)"""
        return 'SCADA'
    
    def add_owned(self, cps_node):
        """Add node to list of nodes over which this SCADA unit has authority"""
        if cps_node not in self._owned_list:
            self._owned_list.add(cps_node)
            
    def add_owner(self, cps_node):
        """Add node to list of nodes which have authority over this SCADA"""
        if cps_node.node_type() != 'SCADA':
            raise ValueError(
                "SCADA units cannot be controlled by non-SCADA units."
            )
        else:
            self._owner_list.add(cps_node)

    def change_control(self, original, original_name, modified, modified_name):
        """Modify control assigned to model."""
        if original_name not in self._controls:
            raise ValueError(
                "The name provided for the original control is not recognized. Please check that the control you wish changed matches the input text."
            )
        else: 
            if (self._controls[original_name]._cps_node != self._name) and (self._controls[original_name]._cps_node not in self._owned_list):
                print(
                    "Control "+original_name+" saw attempted modification from "+ self._name +", which does not have authority to change the control. Attempt rejected."
                )
            else:    

                #TODO: Identify units from control text, automatically pull to use here
                cps_owner = self._controls[original_name]._cps_node
                del self._controls[original_name]
                control = wntr.epanet.io._read_control_line(modified, self._wn, FlowUnits.SI, modified_name)
                control.assign_cps(cps_owner)
                self._controls[modified_name] = control
                
    def assign_control_to_cps_node(self, control, cps_node):
        """Assign control an 'owner' cps_node by which it could be referenced."""
        if control not in self._controls:
            raise ValueError(
                "The name provided for the control is not recognized. Please check that the control you wish assigned matches the input text."
            )
        elif cps_node not in self._cps_reg:
            raise ValueError(
                "The name provided for the cps controller is not recognized. Please check that the cps_node you wish a control assigned to matches the input text."
            )
        elif cps_node not in self._owned_list:
            raise ValueError(
                "The cps node referenced is not one over which this unit has authority. Please check that this SCADA unit has been given authority over that cps_node via add_owned() function."
            )
        else:
            self._controls[name].assign_cps(cps_node)
            
    def disable_owned(self, cps_node):
        """Disable cps node over which this SCADA unit has authority"""
        if cps_node not in list(self._cps_reg):
            raise ValueError(
                "The name provided for the cps controller is not recognized. Please check that the cps_node you wish a control assigned to matches the input text."
            )
        elif cps_node not in list(self._owned_list):
            raise ValueError(
                "The cps node referenced is not one over which this unit has authority. Please check that this SCADA unit has been given authority over that cps_node via add_owned() function."
            )
        else:
            self._cps_reg[cps_node].disable_node()
            
    def disable_control(self, control_name):
        """Disable specific control assigned to model. TODO: Restrict control changes to assigned CPS_Node or SCADA unit if PLC, restrict entirely on RTU"""
        if control_name not in self._controls:
            raise ValueError(
                "The name provided for the original control is not recognized. Please check that the control you wish disabled matches the input text."
            )
        elif (self._controls[original_name]._cps_node != self._name) and (self._controls[control_name]._cps_node not in self._owned_list):
            raise ValueError(
                "The cps_node to which this control is assigned is not one over which this unit has authority. Please check that this SCADA unit has been given authority over that cps_node via add_owned() function."
            )
        else:
            del self._controls[control_name]
            

        
class PLC(CPS_Node):
    """
    PLC class, inherited from CPS_Node.

    CURRENT INSTANTIATION HAS NO SUBCLASSES

    .. rubric:: Constructor
    
    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_plc` method. 
    Direct creation through the constructor is highly discouraged.
    
	This class is intended to be instantiated through a TODO:: constructor method
	in the TODO:: ~wntr.network.model.CyberNetworkModel class
	
	Handles individual controls for wntr network.
	
    Parameters
    ----------
    name : string
        Name of the cps node
    wn : :class:`~wntr.network.model.WaterNetworkModel`
        The water network model this cps node will belong to.
    

    .. rubric:: Attributes

    .. autosummary::

        name
        node_type
        owned_list
        owner_list
        coordinates
        tag

    """

    def __init__(self, name, wn, coordinates=[0,0]):
        super(PLC, self).__init__(wn, name, coordinates=[0,0])
        self._owned_list = OrderedSet()
        self._owner_list = OrderedSet()
        #self._speed_timeseries = TimeSeries(wn._pattern_reg, 1.0)

    def _compare(self, other):
        if not super(PLC, self)._compare(other):
            return False
        return True

    @property
    def node_type(self):
        """str : ``"PLC"`` (read only)"""
        return 'PLC'
    
    def add_owned(self, cps_node):
        """Add node to list of nodes over which this PLC unit has authority"""
        if self._cps_reg[cps_node].node_type == 'SCADA':
            raise ValueError(
                "SCADA units cannot be controlled by non-SCADA units."
            )
        elif cps_node not in self._owned_list:
            self._owned_list.add(cps_node)
            
    def add_owner(self, cps_node):
        """Add node to list of nodes which have authority over this PLC"""
        self._owner_list.add(cps_node)            
        
    def disable_control(self, control_name):
        """Disable specific control assigned to model. TODO: Restrict control changes to assigned CPS_Node or SCADA unit if PLC, restrict entirely on RTU"""
        if control_name not in self._controls:
            raise ValueError(
                "The name provided for the original control is not recognized. Please check that the control you wish disabled matches the input text."
            )
        elif (self._controls[original_name]._cps_node != self._name):
            raise ValueError(
                "The cps_node to which this control is assigned is not one over which this unit has authority. Please check that this PLC unit has been given authority over that cps_node via add_owned() function."
            )
        else:
            del self._controls[control_name]
            
    def change_control(self, original, original_name, modified, modified_name):
        """Modify control assigned to model."""
        if original_name not in self._controls:
            raise ValueError(
                "The name provided for the original control is not recognized. Please check that the control you wish changed matches the input text."
            )
        else: 
            if (self._controls[original_name]._cps_node != self._name) and (self._controls[original_name]._cps_node not in self._owned_list):
                # No longer returns an error and ends the program, but does provide feedback indicating failures.
                print(
                    "Control "+original_name+" saw attempted modification from "+ self._name +", which does not have authority to change the control. Attempt rejected."
                )
            else:
                cps_owner = self._controls[original_name]._cps_node
                del self._controls[original_name]
                control = wntr.epanet.io._read_control_line(modified, self._wn, FlowUnits.SI, modified_name)
                control.assign_cps(cps_owner)
                self._controls[modified_name] = control
                

                
    def disable_owned(self, cps_node):
        """Disable cps node over which this SCADA unit has authority"""
        if cps_node not in list(self._cps_reg):
            raise ValueError(
                "The name provided for the cps controller is not recognized. Please check that the cps_node you wish a control assigned to matches the input text."
            )
        elif cps_node not in list(self._owned_list):
            raise ValueError(
                "The cps node referenced is not one over which this unit has authority. Please check that this PlC unit has been given authority over that cps_node via add_owned() function."
            )
        else:
            self._cps_reg[cps_node].disable_node()    
            
    def assign_control_to_cps_node(self, control, cps_node):
        """Assign control an 'owner' cps_node by which it could be referenced."""
        if control not in self._controls:
            raise ValueError(
                "The name provided for the control is not recognized. Please check that the control you wish assigned matches the input text."
            )
        elif cps_node not in self._cps_reg:
            raise ValueError(
                "The name provided for the cps controller is not recognized. Please check that the cps_node you wish a control assigned to matches the input text."
            )
        elif cps_node not in self._owned_list:
            raise ValueError(
                "The cps node referenced is not one over which this unit has authority. Please check that this SPLC unit has been given authority over that cps_node via add_owned() function."
            )
        else:
            self._controls[name].assign_cps(cps_node)
    
		
		
class RTU(CPS_Node):
    """
    RTU class, inherited from CPS_Node.

    CURRENT INSTANTIATION HAS NO SUBCLASSES

    .. rubric:: Constructor
    
    This class is intended to be instantiated through the 
    :class:`~wntr.network.model.WaterNetworkModel.add_pump` method. 
    Direct creation through the constructor is highly discouraged.
    
	This class is intended to be instantiated through a TODO:: constructor method
	in the TODO:: ~wntr.network.model.CyberNetworkModel class
	
	Differentiated from PLC by lack of change_control function, as RTU are generally more rugged and individually programmed on-site
	
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
        node_type
        owned_list
        owner_list

    """

    def __init__(self, name, wn, coordinates=[0,0]):
        super(RTU, self).__init__(wn, name, coordinates=[0,0])
        self._owned_list = OrderedSet()
        self._owner_list = OrderedSet()        
        #self._speed_timeseries = TimeSeries(wn._pattern_reg, 1.0)
        
    def _compare(self, other):
        if not super(RTU, self)._compare(other):
            return False
        return True

    def add_owned(self, cps_node):
        """Add node to list of nodes over which this PLC unit has authority"""
        if cps_node.node_type == 'SCADA':
            raise ValueError(
                "SCADA units cannot be controlled by non-SCADA units."
            )
        elif cps_node not in self._owned_list:
            self._owned_list.add(cps_node)
            
    def add_owner(self, cps_node):
        """Add node to list of nodes which have authority over this PLC"""
        self._owner_list.add(cps_node)

    @property
    def node_type(self):
        """str : ``"RTU"`` (read only)"""
        return 'RTU'

    def add_control():
        pass



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
        start_node
        end_node
        coordinates
        tag
    


    """
    def __init__(self, wn, name, start_node_name, end_node_name):
        self._name = name
        self._options = wn._options
        self._node_reg = wn._node_reg
        self._link_reg = wn._link_reg
        self._controls = wn._controls
        self._cps_reg = wn._cps_reg
        self._cps_edges = wn._cps_edges
        self._coordinates = [0,0]
        # Set and register the starting node
        self._start_node = self._cps_reg[start_node_name]
        self._start_node_name = start_node_name
        self._cps_reg.add_usage(start_node_name, (name, self.edge_type))
        # Set and register the ending node
        self._end_node = self._cps_reg[end_node_name]
        self._end_node_name = end_node_name
        self._cps_reg.add_usage(end_node_name, (name, self.edge_type))
        # Add information about new edge to corresponding nodes
        self._cps_reg[start_node_name].add_edge(name)
        self._cps_reg[end_node_name].add_edge(name)
        self._medium = 'wireless' #may split out to include specific wired/wireless classes
        self._loss_rate = 0.00 #rate of packet loss (separate from rates in communication modules)
        
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

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(MODBUS, self).__init__(wn, name, start_node_name, end_node_name)
        self._connection_limit = 255 #limits of modbus device count communication

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

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(EIP, self).__init__(wn, name, start_node_name, end_node_name)
        
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
	
	Differentiated from EIP by lack of remote access, as SER are generally only used for local systems transmitting digital data feeds directly between systems
	
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

    .. rubric:: Read-only simulation results

    .. autosummary::

        flow
        headloss
        velocity
        quality
        status
        setting

    """

    def __init__(self, name, start_node_name, end_node_name, wn):
        super(SER, self).__init__(wn, name, start_node_name, end_node_name)
        #self._speed_timeseries = TimeSeries(wn._pattern_reg, 1.0)

    def _compare(self, other):
        if not super(SER, self)._compare(other):
            return False
        return True

    @property
    def edge_type(self):
        """str : ``"SER"`` (read only)"""
        return 'SER'

       
        
class CPSNodeRegistry(Registry):
    """A registry for nodes."""

    def __init__(self, model):
        super(CPSNodeRegistry, self).__init__(model)
        self._listSCADA = OrderedSet()
        self._listPLC = OrderedSet()
        self._listRTU = OrderedSet()
        self._wn = model

    def _finalize_(self, model):
        super()._finalize_(model)

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise ValueError("Registry keys must be strings")
        self._data[key] = value
        if isinstance(value, SCADA):
            self._listSCADA.add(key)
        elif isinstance(value, PLC):
            self._listPLC.add(key)
        elif isinstance(value, RTU):
            self._listRTU.add(key)

    def __delitem__(self, key):
        try:
            if self._usage and key in self._usage and len(self._usage[key]) > 0:
                raise RuntimeError(
                    "cannot remove %s %s, still used by %s" % (self.__class__.__name__, key, str(self._usage[key]))
                )
            elif key in self._usage:
                self._usage.pop(key)
            node = self._data.pop(key)
            self._listSCADA.discard(key)
            self._listPLC.discard(key)
            self._listRTU.discard(key)
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
            wntr.network.model.CPS_node,
            wntr.network.model.SCADA,
            wntr.network.model.PLC,
            wntr.network.model.RTU, or None. Default = None.
            Note None and wntr.network.model.CPS_node produce the same results.

        Returns
        -------
        A generator in the format (name, object).
        """
        if node_type == None:
            for node_name, node in self._data.items():
                yield node_name, node
        elif node_type == SCADA:
            for node_name in self._listSCADA:
                yield node_name, self._data[node_name]
        elif node_type == PLC:
            for node_name in self._listPLC:
                yield node_name, self._data[node_name]
        elif node_type == RTU:
            for node_name in self._listRTU:
                yield node_name, self._data[node_name]
        else:
            raise RuntimeError("node_type, " + str(node_type) + ", not recognized.")

    def add_SCADA(
        self,
        name,
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
        assert isinstance(coordinates, (type(None), (tuple, list,))), "coordinates must be a tuple"

        scada = SCADA(name, self._wn)
        self[name] = scada
        if coordinates is not None:
            scada.coordinates = coordinates

    def add_PLC(
        self,
        name,
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
            X-Y coordinates of the node location.
            
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(coordinates, (type(None), (tuple,list,))), "coordinates must be a tuple"

        plc = PLC(name, self._wn)
        self[name] = plc
        if coordinates is not None:
            plc.coordinates = coordinates

    def add_RTU(self, 
        name,
        coordinates=None,
    ):
        """
        Adds a remote terminal unit to the water network model.

        Parameters
        ----------
        name : string
        coordinates : tuple of floats, optional
            X-Y coordinates of the node location.
        
        """
        assert (
            isinstance(name, str) and len(name) < 32 and name.find(" ") == -1
        ), "name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(coordinates, (type(None), (tuple, list))), "coordinates must be a tuple"

        rtu = RTU(name, self._wn)
        self[name] = rtu
        if coordinates is not None:
            rtu.coordinates = coordinates

    @property
    def SCADA_names(self):
        """List of names of all SCADA nodes"""
        return self._listSCADA

    @property
    def PLC_names(self):
        """List of names of all PLC nodes"""
        return self._listPLC

    @property
    def RTU_names(self):
        """List of names of all RTU nodes"""
        return self._listRTU

    def SCADA_nodes(self):
        """Generator to get all SCADA nodes
        
        Yields
        ------
        name : str
            The name of the SCADA node
        node : SCADA
            The SCADA object    
            
        """
        for node_name in self._listSCADA:
            yield node_name, self._data[node_name]

    def PLC_nodes(self):
        """Generator to get all PLC
        
        Yields
        ------
        name : str
            The name of the tank
        node : Tank
            The tank object    
            
        """
        for node_name in self._listPLC:
            yield node_name, self._data[node_name]

    def RTU_nodes(self):
        """Generator to get all reservoirs
        
        Yields
        ------
        name : str
            The name of the reservoir
        node : Reservoir
            The reservoir object    
            
        """
        for node_name in self._listRTU:
            yield node_name, self._data[node_name]   
            
    def remove_cps_node(self, name, with_control=False, force=False):
        """Removes a node from the water network model"""
        node = self._cps_reg[name]
        if not force:
            if with_control:
                for control_name, control in self._controls.items():
                    if name == control._cps_node._name:
                        logger.warning(
                            control._control_type_str()
                            + " "
                            + control_name
                            + " is being removed along with node "
                            + name
                        )
                        del self._controls[name]
            else:
                for control_name, control in self._controls.items():
                    if name == control._cps_node._name:
                        raise RuntimeError(
                            "Cannot remove node {0} without first removing control/rule {1}".format(name, control_name)
                        )
        self._cps_reg.__delitem__(name)


        
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
        self._wn = model

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
        Adds a MODBUS edge to the water network model.

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
            isinstance(name, str) and len(name) < 64 and name.find(" ") == -1
        ), "name must be a string with less than 64 characters and contain no spaces"
        assert (
            isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(" ") == -1
        ), "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(" ") == -1
        ), "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(coordinates, (type(None), (tuple, list,))), "coordinates must be a tuple"
        if start_node_name not in self._cps_reg:
            raise ValueError(
                "The name provided for the start node does not exist in the CPS node registry, please ensure nodes are added before edges and that the desired start node name matches the previously-declared name."
            )        
        if end_node_name not in self._cps_reg:
            raise ValueError(
                "The name provided for the end node does not exist in the CPS node registry, please ensure nodes are added before edges and that the desired end node name matches the previously-declared name."
            )      
        modbus = MODBUS(name, start_node_name, end_node_name, self)
        self[name] = modbus
        if coordinates is not None:
            modbus.coordinates = coordinates
            

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
            isinstance(name, str) and len(name) < 64 and name.find(" ") == -1
        ), "name must be a string with less than 64 characters and contain no spaces"
        assert (
            isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(" ") == -1
        ), "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(" ") == -1
        ), "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(coordinates, (type(None), (tuple,list,))), "coordinates must be a tuple"
        if start_node_name not in self._cps_reg:
            raise ValueError(
                "The name provided for the start node does not exist in the CPS node registry, please ensure nodes are added before edges and that the desired start node name matches the previously-declared name."
            )        
        if end_node_name not in self._cps_reg:
            raise ValueError(
                "The name provided for the end node does not exist in the CPS node registry, please ensure nodes are added before edges and that the desired end node name matches the previously-declared name."
            )   
        eip = EIP(name, start_node_name, end_node_name, self)
        self[name] = eip
        if coordinates is not None:
            eip.coordinates = coordinates

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
            isinstance(name, str) and len(name) < 64 and name.find(" ") == -1
        ), "name must be a string with less than 64 characters and contain no spaces"
        assert (
            isinstance(start_node_name, str) and len(start_node_name) < 32 and start_node_name.find(" ") == -1
        ), "start_node_name must be a string with less than 32 characters and contain no spaces"
        assert (
            isinstance(end_node_name, str) and len(end_node_name) < 32 and end_node_name.find(" ") == -1
        ), "end_node_name must be a string with less than 32 characters and contain no spaces"
        assert isinstance(coordinates, (type(None), (tuple, list))), "coordinates must be a tuple"

        if start_node_name not in self._cps_reg:
            raise ValueError(
                "The name provided for the start node does not exist in the CPS node registry, please ensure nodes are added before edges and that the desired start node name matches the previously-declared name."
            )        
        if end_node_name not in self._cps_reg:
            raise ValueError(
                "The name provided for the end node does not exist in the CPS node registry, please ensure nodes are added before edges and that the desired end node name matches the previously-declared name."
            )   
        ser = SER(name, start_node_name, end_node_name, self)
        self[name] = ser
        if coordinates is not None:
            ser.coordinates = coordinates

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
            The name of the edge
        edge : EIP
            The edge object    
            
        """
        for edge_name in self._listEIP:
            yield edge_name, self._data[edge_name]

    def SER_edges(self):
        """Generator to get all serial edges
        
        Yields
        ------
        name : str
            The name of the edge
        edge : SER
            The SER edge object    
            
        """
        for edge_name in self._listSER:
            yield edge_name, self._data[edge_name]
            
    def remove_edge(self, name, force=False):
        """Removes a cps edge from the water network model"""
        edge = self[name]
        if not force:
#            for data in self._wn._cps_reg.__call__():     
#                print(data)
            for cps_node_name, cps_node in self._wn._cps_reg.__call__():
                if name in cps_node._edges:
                    logger.warning(
                        edge.edge_type
                        + " "
                        + name
                        + " is being removed "
                    )
                    cps_node.del_edge(name)
        self.__delitem__(name)
#       print(name + " deleted")

class CPSNodeType(enum.IntEnum):
    """
    Enum class for node types.

    .. rubric:: Enum Members

    .. autosummary::

        SCADA
        PLC
        RTU

    """
    SCADA = 0  #: node is a SCADA unit
    PLC = 1  #: node is a PLC
    RTU = 2  #: node is an RTU

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
               


class CPSEdgeType(enum.IntEnum):
    """
    Enum class for edge types.

    .. rubric:: Enum Members

    .. autosummary::

        MODBUS
        EIP
        SER

    """
    MODBUS = 0  #: edge is a MODBUS link
    EIP = 1  #: edge is a EIP (ethernet/IP) link
    SER = 2  #: edge is a SER (serial) link

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
        
 