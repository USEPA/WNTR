import logging
import pandas as pd

import swmmio

from wntr.stormwater.io import to_graph, write_inpfile

logger = logging.getLogger(__name__)


class StormWaterNetworkModel(object):
    """
    Storm water network model class.

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
            
            # These dataframes can be modified to create scenarios
            # prior to running pyswmm, the updates are saved to a new INP file
            self.nodes = self._swmmio_model.nodes.geodataframe
            self.links = self._swmmio_model.links.geodataframe
            self.subcatchments = self._swmmio_model.subcatchments.geodataframe
            self.raingages = self._swmmio_model.inp.raingages
            
            # nodes
            self.junction_name_list = list(self._swmmio_model.inp.junctions.index)
            self.outfall_name_list = list(self._swmmio_model.inp.outfalls.index)
            self.storage_name_list = list(self._swmmio_model.inp.storage.index)
            
            # links
            self.conduit_name_list = list(self._swmmio_model.inp.conduits.index)
            self.weir_name_list = list(self._swmmio_model.inp.weirs.index)
            self.orifice_name_list = list(self._swmmio_model.inp.orifices.index)
            self.pump_name_list = list(self._swmmio_model.inp.pumps.index)
            
            # subcatchments
            self.subcatchment_name_list = list(self._swmmio_model.inp.subcatchments.index)
            
            # raingages
            self.raingage_name_list = list(self._swmmio_model.inp.raingages.index)
            
        else:
            self._swmmio_model = None
            
    def udpate_inp_model(self, filename=None):
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

        if filename:
            write_inpfile(self, filename)


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
                                        

 