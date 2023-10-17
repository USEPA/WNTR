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
            self._swmmio_model = swmmio.Model(inp_file_name)
  
            # Attributes of StormWaterNetworkModel link to attributes 
            # in swmmio.Model.inp, which contains dataframes from an INP file.
            # The swmmio.Model.inp object also includes a .save method to 
            # write a new INP file.
 
            # Nodes = Junctions, outfall, and storage nodes
            self.junctions = self._swmmio_model.inp.junctions
            self.outfalls = self._swmmio_model.inp.outfalls
            self.storage = self._swmmio_model.inp.junctions

            # Links = Conduits, weirs, orifices, and pumps
            self.conduits = self._swmmio_model.inp.conduits
            self.weirs = self._swmmio_model.inp.weirs
            self.orifices = self._swmmio_model.inp.orifices
            self.pumps = self._swmmio_model.inp.pumps

            self.subcatchments = self._swmmio_model.inp.subcatchments
            self.subareas = self._swmmio_model.inp.subareas

            self.raingages = self._swmmio_model.inp.raingages
            self.infiltration = self._swmmio_model.inp.infiltration
            self.inflows = self._swmmio_model.inp.inflows
            #self.dwf = self._swmmio_model.inp.dwf

            self.curves = self._swmmio_model.inp.curves
            self.timeseries = self._swmmio_model.inp.timeseries

            self.options = self._swmmio_model.inp.options
            self.files = self._swmmio_model.inp.files

            self.coordinates = self._swmmio_model.inp.coordinates
            self.vertices = self._swmmio_model.inp.vertices
            self.polygons = self._swmmio_model.inp.polygons
            self.xsections = self._swmmio_model.inp.xsections

        else:
            self._swmmio_model = None
            
    @property
    # def junctions(self):
    #     """Generator to get all junctions
        
    #     Yields
    #     ------
    #     name : str
    #         The name of the junction
    #     node : Junction
    #         The junction object    
            
    #     """
    #     for name, junc in self.junctions.iterrows():
    #         yield name, junc
            
    @property
    def node_name_list(self):
        """Get a list of node names

        Returns
        -------
        list of strings

        """
        return self.junction_name_list + self.outfall_name_list + \
            self.storage_name_list

    @property
    def junction_name_list(self):
        """Get a list of junction names

        Returns
        -------
        list of strings

        """
        return list(self.junctions.index)

    @property
    def outfall_name_list(self):
        """Get a list of outfall names

        Returns
        -------
        list of strings

        """
        return list(self.outfalls.index)

    @property
    def storage_name_list(self):
        """Get a list of storage names

        Returns
        -------
        list of strings

        """
        return list(self.storage.index)

    @property
    def link_name_list(self):
        """Get a list of link names

        Returns
        -------
        list of strings

        """
        return self.conduit_name_list + self.weir_name_list + \
            self.orifice_name_list + self.pump_name_list

    @property
    def conduit_name_list(self):
        """Get a list of conduit names

        Returns
        -------
        list of strings

        """
        return list(self.conduits.index)

    @property
    def weir_name_list(self):
        """Get a list of weir names

        Returns
        -------
        list of strings

        """
        return list(self.weirs.index)

    @property
    def orifice_name_list(self):
        """Get a list of orifice names

        Returns
        -------
        list of strings

        """
        return list(self.orifices.index)

    @property
    def pump_name_list(self):
        """Get a list of pump names

        Returns
        -------
        list of strings

        """
        return list(self.pumps.index)

    @property
    def subcatchment_name_list(self):
        """Get a list of subcatchment names

        Returns
        -------
        list of strings

        """
        return list(self.subcatchments.index)

    @property
    def raingage_name_list(self):
        """Get a list of raingage names

        Returns
        -------
        list of strings

        """
        return list(self.raingages.index)

    @property
    def num_nodes(self):
        """The number of nodes"""
        return len(self.node_name_list)

    @property
    def num_junctions(self):
        """The number of junctions"""
        return len(self.junction_name_list)

    @property
    def num_outfalls(self):
        """The number of outfalls"""
        return len(self.outfall_name_list)

    @property
    def num_storages(self):
        """The number of storages"""
        return len(self.storage_name_list)

    @property
    def num_links(self):
        """The number of links"""
        return len(self.link_name_list)

    @property
    def num_conduits(self):
        """The number of conduits"""
        return len(self.conduit_name_list)

    @property
    def num_weirs(self):
        """The number of weirs"""
        return len(self.weir_name_list)

    @property
    def num_orifices(self):
        """The number of orifices"""
        return len(self.orifice_name_list)

    @property
    def num_pumps(self):
        """The number of pumps"""
        return len(self.pump_name_list)

    @property
    def num_subcatchments(self):
        """The number of subcatchments"""
        return len(self.subcatchment_name_list)

    @property
    def num_raingages(self):
        """The number of raingages"""
        return len(self.raingage_name_list)

    def get_node(self, name):
        """Get a specific node

        Parameters
        ----------
        name : str
            The node name

        Returns
        -------
        Junction, Outfall, or Storage

        """
        return Node(self, name)

    def get_link(self, name):
        """Get a specific link

        Parameters
        ----------
        name : str
            The link name

        Returns
        -------
        Pipe, Pump, or Valve

        """
        if name in self.conduit_name_list:
            data = self.conduits
        elif name in self.weir_name_list:
            data = self.weirs
        elif name in self.orifice_name_list:
            data = self.orifices
        elif name in self.pump_name_list:
            data = self.pumps
            
        start_node_name = data.loc[name, 'InletNode']
        end_node_name = data.loc[name, 'OutletNode']
        
        return Link(self, name, start_node_name, end_node_name)

    def to_gis(self, crs=None):
        """
        Convert a StormWaterNetworkModel into GeoDataFrames

        Parameters
        ----------
        crs : str, optional
            Coordinate reference system, by default None
        """
        return to_gis(self, crs)

    def to_graph(self):
        """
        Convert a StormWaterNetworkModel into a networkx MultiDiGraph

        Returns
        --------
        networkx MultiDiGraph
        """
        return to_graph(self)


class Node(object):
    """
    Base class for nodes.
    """

    def __init__(self, swn, name):

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

    def __init__(self, swn, link_name, start_node_name, end_node_name):

        self._link_name = link_name
        self._start_node_name = start_node_name
        self._end_node_name = end_node_name

    @property
    def name(self):
        """str: The link name (read-only)"""
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
