"""
The wntr.stormwater.network module includes methods to define
stormwater/wastewater network models.
"""
import logging
import random
import numpy as np
import pandas as pd
import swmmio

from wntr.stormwater.io import to_graph, to_gis

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

    def __init__(self, inp_file_name=None):
        
        if inp_file_name:
            self._swmmio_model = swmmio.Model(inp_file_name, include_rpt=False)
  
            # Attributes of StormWaterNetworkModel link to attributes 
            # in swmmio.Model.inp, which contains dataframes from an INP file.
            # The swmmio.Model.inp object also includes a .save method to 
            # write a new INP file.

            # Nodes = Junctions, outfall, and storage nodes
            # Links = Conduits, weirs, orifices, and pumps
            
            # A * by the section name indicates that we have an 
            # INP file for tests that include that section
            
            # [JUNCTIONS] *
            self.junctions = self._swmmio_model.inp.junctions
            # [OUTFALLS] *
            self.outfalls = self._swmmio_model.inp.outfalls
            # [STORAGE] *
            self.storage = self._swmmio_model.inp.storage

            # [CONDUITS] *
            self.conduits = self._swmmio_model.inp.conduits
            # [WEIRS] *
            self.weirs = self._swmmio_model.inp.weirs
            # [ORIFICES] *
            self.orifices = self._swmmio_model.inp.orifices
            # [PUMPS] *
            self.pumps = self._swmmio_model.inp.pumps
            
            # [SUBCATCHMENTS] *
            self.subcatchments = self._swmmio_model.inp.subcatchments
            # [SUBAREAS] *
            self.subareas = self._swmmio_model.inp.subareas
            # [INFILTRATION] *
            self.infiltration = self._swmmio_model.inp.infiltration
            # [LID_USAGE] *
            self.lid_usage = self._swmmio_model.inp.lid_usage
            
            # [INLETS] *
            self.inlets = self._swmmio_model.inp.inlets
            # [INLET_USAGE] *
            self.inlet_usage = self._swmmio_model.inp.inlet_usage
            
            # [RAINGAGES] *
            self.raingages = self._swmmio_model.inp.raingages
            # [EVAPORATION] *
            self.evaporation = self._swmmio_model.inp.evaporation
            
            # [POLLUTANTS] *
            self.pollutants = self._swmmio_model.inp.pollutants
            # [LANDUSES] *
            self.landuses = self._swmmio_model.inp.landuses
            # [COVERAGES] *
            self.coverages = self._swmmio_model.inp.coverages
            # [BUILDUP] *
            self.buildup = self._swmmio_model.inp.buildup
            # [WASHOFF]
            self.washoff = self._swmmio_model.inp.washoff
            
            # [OPTIONS] *
            self.options = self._swmmio_model.inp.options
            # [REPORT] *
            self.report = self._swmmio_model.inp.report
            
            # [COORDINATES] *
            self.coordinates = self._swmmio_model.inp.coordinates
            # [VERTICES] *
            self.vertices = self._swmmio_model.inp.vertices
            # [Polygons] *
            self.polygons = self._swmmio_model.inp.polygons
            # [STREETS] *
            self.streets = self._swmmio_model.inp.streets
            
            # [TAGS] *
            self.tags = self._swmmio_model.inp.tags
            
            # The following sections do not read/write correctly in swmmio
            # The use of create_dataframe_multi_index or the INP files have an unexpected format
            # As a results these sections are not supported for user modification in swntr
            # [CURVES] *
            #self.curves = self._swmmio_model.inp.curves
            # [TIMESERIES] *
            #self.timeseries = self._swmmio_model.inp.timeseries
            # [DWF] *
            # self.dwf = self._swmmio_model.inp.dwf
            # [XSECTIONS] *
            #self.xsections = self._swmmio_model.inp.xsections
            # [INFLOWS] *
            #self.inflows = self._swmmio_model.inp.inflows
            
            # The following sections are included in groundwatrer_model.inp 
            # but that model does not run based on sections above
            # [AQUIFERS] *
            #self.aquifers = self._swmmio_model.inp.aquifers
            # [GROUNDWATER] *
            #self.groundwater = self._swmmio_model.inp.groundwater
            
            # The following section is included in site_drainage_model.inp, 
            # but data is empty
            # [LOADINGS] *
            #self.loadings = self._swmmio_model.inp.loadings
            
            # The following sections are NOT included in an INP file we have for testing
            # [LOSSES]
            # [DIVIDERS]
            # [RDII]
            # [HYDROGRAPHS]
            # [FILES]
            
            # The following sections are NOT included in swmmio read/write
            # [TITLE] *
            # [LID_CONTROLS] *
            # [CONTROLS] *
            # [PATTERNS] *
            # [MAP] *
            # [SYMBOLS] *
            # [LABLES] *
            # [BACKDROP] *
            
        else:
            self._swmmio_model = None
            
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
