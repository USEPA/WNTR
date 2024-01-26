"""
The wntr.stormwater.network module includes methods to define
stormwater/wastewater network models.
"""
import logging
import random
import numpy as np
import pandas as pd
import swmmio

from wntr.stormwater.io import to_graph, to_gis, _read_controls

logger = logging.getLogger(__name__)


class StormWaterNetworkModel(object):
    """
    Storm water network model class.

    Unlike the WaterNetworkModel, this class has no iterator methods,
    add/remove methods, and no component registries.

    Parameters
    -------------------
    inp_file_name: string 
        Directory and filename of SWMM inp file to load into the
        StormWaterNetworkModel object.
    """

    def __init__(self, inp_file_name):
        
        self._swmmio_model = swmmio.Model(inp_file_name, include_rpt=False)
  
        # See https://github.com/pyswmm/swmmio/issues/57 for a list of supported INP file sections
        
        # Attributes of StormWaterNetworkModel link to attributes 
        # in swmmio.Model.inp, which contains dataframes from an INP file.
        # The swmmio.Model.inp object also includes a .save method to 
        # write a new INP file.

        # Nodes = Junctions, outfall, and storage nodes
        # Links = Conduits, weirs, orifices, and pumps
        
        # Sections that are commented out are not currently supported by swntr
        
        self.section_names = [
            'junctions',
            'outfalls',
            'storage',
            'conduits',
            'weirs',
            'orifices',
            'pumps',
            'subcatchments', 
            'subareas',
            'infiltration',
            'lid_usage', 
            'inlets', 
            'inlet_usage', 
            'raingages',
            'evaporation',
            'pollutants',
            'landuses',
            'coverages',
            'buildup',
            'options',
            'report',
            'coordinates',
            'vertices',
            'polygons',
            'streets',
            'tags',
            
            # Insufficient test (not included or empty in INP test files)
            #'loading',
            #'washoff',
            #'losses',
            #'dividers',
            #'drii',
            #'hydrographs',
            #'files',
            
            # I/O failure in swmmio
            #'curves',
            #'timeseries',
            #'dwf',
            #'xsections',
            #'inflows',
            #'aquifers',
            #'groundwater', 
            
            # Not supported by swmmio
            'controls', # requires an additional read of the INP file
            #'title',
            #'lid_controls',
            #'patterns',
            #'map',
            #'symbols',
            #'labels',
            #'backdrop',
            ]
        for sec in self.section_names:
            if sec == 'controls':
                controls = _read_controls(inp_file_name)
                setattr(self, sec, controls)
            else:
                df = getattr(self._swmmio_model.inp, sec)
                setattr(self, sec, df)
        
    def describe(self, level=0):
        """
        Describe number of components in the network model
        
        Parameters
        ----------
        level : int (0, 1, or 2)
            
           * Level 0 returns the number of Junctions, Outfalls, Storage, Conduits, Weirs, Orifices, Pumps, Subcatchments, and Raingages
           * Level 1 includes information on additional network components
           
        Returns
        -------
        A pandas Series with component counts
        """

        d = {
            "Junctions": self.num_junctions,
            "Outfalls": self.num_outfalls,
            "Storage": self.num_storages,
            "Conduits": self.num_conduits,
            "Weirs": self.num_weirs,
            "Orifices": self.num_orifices,
            "Pumps": self.num_pumps,
            "Subcatchments": self.num_subcatchments,
            "Raingages": self.num_raingages,
            #"Controls": self.num_controls,
        }
        
        if level == 1:
            raise NotImplementedError

        return pd.Series(d)
    
    @property
    def nodes(self):
        """Nodes database (read only)"""
        return pd.concat([self.junctions, 
                          self.outfalls,
                          self.storage])
    
    @property
    def links(self):
        """Links database (read only)"""
        return pd.concat([self.conduits, 
                          self.weirs,
                          self.orifices,
                          self.pumps])

    @property
    def node_name_list(self):
        """List of node names"""
        return list(self.nodes.index)

    @property
    def junction_name_list(self):
        """List of junction names"""
        return list(self.junctions.index)

    @property
    def outfall_name_list(self):
        """List of outfall names"""
        return list(self.outfalls.index)

    @property
    def storage_name_list(self):
        """List of storage names"""
        return list(self.storage.index)

    @property
    def link_name_list(self):
        """List of link names"""
        return list(self.links.index)

    @property
    def conduit_name_list(self):
        """List of conduit names"""
        return list(self.conduits.index)

    @property
    def weir_name_list(self):
        """List of weir names"""
        return list(self.weirs.index)

    @property
    def orifice_name_list(self):
        """List of orifice names"""
        return list(self.orifices.index)

    @property
    def pump_name_list(self):
        """List of pump names"""
        return list(self.pumps.index)

    @property
    def subcatchment_name_list(self):
        """List of subcatchment names"""
        return list(self.subcatchments.index)

    @property
    def raingage_name_list(self):
        """List of raingage names"""
        return list(self.raingages.index)

    @property
    def num_nodes(self):
        """Number of nodes"""
        return len(self.node_name_list)

    @property
    def num_junctions(self):
        """Number of junctions"""
        return len(self.junction_name_list)

    @property
    def num_outfalls(self):
        """Number of outfalls"""
        return len(self.outfall_name_list)

    @property
    def num_storages(self):
        """Number of storages"""
        return len(self.storage_name_list)

    @property
    def num_links(self):
        """Number of links"""
        return len(self.link_name_list)

    @property
    def num_conduits(self):
        """Number of conduits"""
        return len(self.conduit_name_list)

    @property
    def num_weirs(self):
        """Number of weirs"""
        return len(self.weir_name_list)

    @property
    def num_orifices(self):
        """Number of orifices"""
        return len(self.orifice_name_list)

    @property
    def num_pumps(self):
        """Number of pumps"""
        return len(self.pump_name_list)

    @property
    def num_subcatchments(self):
        """Number of subcatchments"""
        return len(self.subcatchment_name_list)

    @property
    def num_raingages(self):
        """Number of raingages"""
        return len(self.raingage_name_list)

    def get_node(self, name):
        """Get a specific node

        Parameters
        ----------
        name : str
            The node name

        Returns
        -------
        Node

        """
        return Node(name, self.nodes.loc[name,:])

    def get_link(self, name):
        """Get a specific link

        Parameters
        ----------
        name : str
            The link name

        Returns
        -------
        Link

        """
        return Link(name, self.links.loc[name,:])

    def to_gis(self, crs=None):
        """
        Convert a StormWaterNetworkModel into GeoDataFrames

        Parameters
        ----------
        crs : str, optional
            Coordinate reference system, by default None
        """
        return to_gis(self, crs)

    def to_graph(self, node_weight=None, link_weight=None, modify_direction=False):
        """
        Convert a StormWaterNetworkModel into a networkx MultiDiGraph

        Returns
        --------
        networkx MultiDiGraph
        """
        return to_graph(self, node_weight, link_weight, modify_direction)

    def add_pump_outage_control(self, pump_name, start_time, end_time=None, priority=4):
        """
        Add a pump outage rule to the stormwater network model.
    
        Parameters
        ----------
        start_time : int
           The time at which the outage starts in decimal hours
        end_time : int
           The time at which the outage stops in decimal hours
        priority : int
            The outage rule priority, default = 4 (highest priority)
        """
        rule_name = pump_name + '_power_outage'
        rule = ["IF SIMULATION TIME > "+str(start_time)]
        if end_time is not None:
            rule.append("AND SIMULATION TIME < "+str(end_time))
        rule.extend(["THEN PUMP "+pump_name+" status = OFF",
                     "ELSE PUMP "+pump_name+" status = ON",
                     "PRIORITY "+str(priority)])
        self.controls[rule_name] = rule

class Node(object):
    """
    Base class for nodes.
    """

    def __init__(self, name, data):

        # Set the node name
        self._name = name

    @property
    def name(self):
        """str: The name of the node (read only)"""
        return self._name


class Link(object):
    """
    Base class for links.
    """

    def __init__(self, name, data):

        self._link_name = name
        self._start_node_name = data['InletNode']
        self._end_node_name = data['OutletNode']

    @property
    def name(self):
        """str: The link name (read only)"""
        return self._link_name

    @property
    def start_node_name(self):
        """str: The name of the start node (read only)"""
        return self._start_node_name

    @property
    def end_node_name(self):
        """str: The name of the end node (read only)"""
        return self._end_node_name


def generate_valve_layer(swn, placement_type='strategic', n=1, seed=None):
    """
    Generate valve layer data, which can be used in valve segmentation analysis.

    Parameters
    -----------
    swn : wntr StrormWaterNetworkModel
        A StormWaterNetworkModel object
        
    placement_type : string
        Options include 'strategic' and 'random'.  
        
        - If 'strategic', n is the number of pipes from each node that do not 
          contain a valve. In this case, n is generally 0, 1 or 2 
          (i.e. N, N-1, N-2 valve placement).
        - If 'random', then n randomly placed valves are used to define the 
          valve layer.
        
    n : int
        
        - If 'strategic', n is the number of pipes from each node that do not 
          contain a valve.
        - If 'random', n is the number of number of randomly placed valves.
        
    seed : int or None
        Random seed
       
    Returns
    ---------
    valve_layer : pandas DataFrame
        Valve layer, defined by node and link pairs (for example, valve 0 is 
        on link A and protects node B). The valve_layer DataFrame is indexed by
        valve number, with columns named 'node' and 'link'.
    """
    
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    valve_layer = []
    if placement_type=='random':
        s = swn.conduits['InletNode']
        all_valves = list(tuple(zip(s.index,s)))
        s = swn.conduits['OutletNode']
        all_valves.extend(tuple(zip(s.index,s)))
        for valve_tuple in random.sample(all_valves, n):
            pipe_name, node_name = valve_tuple
            valve_layer.append([pipe_name, node_name])
            
    elif placement_type == 'strategic':
        s = pd.concat([swn.conduits['InletNode'], swn.conduits['OutletNode']])
        s = s.to_frame('Node')
        for node_name, group in s.groupby('Node'):
            links = list(group.index)
            for l in np.random.choice(links, max(len(links)-n,0), replace=False):
                valve_layer.append([l, node_name])
            
    valve_layer = pd.DataFrame(valve_layer, columns=['link', 'node'])  
    
    return valve_layer
