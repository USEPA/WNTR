import logging
import pandas as pd
import swmmio

from wntr.stormwater.io import to_graph, to_gis, write_inpfile

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
        
        """
        swmmio.Model.links.geodataframe returns a geodataframe containing 
        PUMPS, CONDUITS, WEIRS, and ORIFICES joined with XSECTIONS and 
        COORDINATES
        """
        
        if inp_file_name:
            self._swmmio_model = swmmio.Model(inp_file_name)
            
            # These dataframes can be used to modify the network model
            # prior to running pyswmm, the updates are saved to a new INP file
            # before running the simulation
            self.nodes = self._swmmio_model.nodes.geodataframe.copy()
            self.links = self._swmmio_model.links.geodataframe.copy()
            self.subcatchments = self._swmmio_model.subcatchments.geodataframe.copy()
            self.raingages = self._swmmio_model.inp.raingages.copy()
            self.options = self._swmmio_model.inp.options.copy()

        else:
            self._swmmio_model = None
            
            self.nodes = None
            self.links  = None
            self.subcatchments = None
            self.raingages = None
            self.options = None
            

    @property
    def node_name_list(self):
        """Get a list of node names
        
        Returns
        -------
        list of strings
        
        """
        return self.junction_name_list + self.outfall_name_list + self.storage_name_list
    
    @property
    def junction_name_list(self):
        """Get a list of junction names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._swmmio_model.inp.junctions.index)


    @property
    def outfall_name_list(self):
        """Get a list of outfall names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._swmmio_model.inp.outfalls.index)
    
    
    @property
    def storage_name_list(self):
        """Get a list of storage names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._swmmio_model.inp.storage.index)
    
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
        return list(self._swmmio_model.inp.conduits.index)
    
    @property
    def weir_name_list(self):
        """Get a list of weir names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._swmmio_model.inp.weirs.index)
    
    @property
    def orifice_name_list(self):
        """Get a list of orifice names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._swmmio_model.inp.orifices.index)
    
    @property
    def pump_name_list(self):
        """Get a list of pump names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._swmmio_model.inp.pumps.index)
    
    @property
    def subcatchment_name_list(self):
        """Get a list of subcatchment names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._swmmio_model.inp.subcatchments.index)
    
    @property
    def raingage_name_list(self):
        """Get a list of raingage names
        
        Returns
        -------
        list of strings
        
        """
        return list(self._swmmio_model.inp.raingages.index)
    
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
    
    
    def to_gis(self, crs=None):
        
        return to_gis(self)
    
    
    def to_graph(self, node_weight=None, link_weight=None, 
                 modify_direction=False):
        """
        Convert a StormWaterNetworkModel into a networkx MultiDiGraph
        
        Parameters
        ----------
        node_weight :  dict or pandas Series (optional)
            Node weights
        link_weight : dict or pandas Series (optional)
            Link weights.  
        modify_direction : bool (optional)
            If True, than if the link weight is negative, the link start and 
            end node are switched and the abs(weight) is assigned to the link
            (this is useful when weighting graphs by flowrate). If False, link 
            direction and weight are not changed.
            
        Returns
        --------
        networkx MultiDiGraph
        """
        return to_graph(self)
    
    
    def udpate_model_inp(self, filename=None):
        """
        Update self._swmmio_model.inp based udpates to self.nodes, self.links, 
        self.subcatchments, and self.raingages
        """
        model_inp = self._swmmio_model.inp
        
        # nodes
        for df in [model_inp.junctions, model_inp.outfalls, model_inp.storage]:
            df = self.nodes.loc[df.index, df.columns]
        # links
        for df in [model_inp.conduits, model_inp.weirs, model_inp.orifices, model_inp.pumps]:
            df = self.links.loc[df.index, df.columns]
        # subcatchments
        for df in [model_inp.subcatchments]:
            df = self.subcatchments.loc[df.index, df.columns]
        # raingages
        for df in [model_inp.raingages]:
            df = self.raingages.loc[df.index, df.columns]
        # options
        for df in [model_inp.options]:
            df = self.options.loc[df.index, df.columns]

        if filename:
            write_inpfile(self, filename)