from wntr.gis import snap, intersect

import swmmio

import pandas as pd
import numpy as np

try:
    from shapely.geometry import LineString, Point
    has_shapely = True
except ModuleNotFoundError:
    has_shapely = False

try:
    import geopandas as gpd
    has_geopandas = True
except ModuleNotFoundError:
    has_geopandas = False

import wntr.network.elements

class StormWaterNetworkGIS:
    """
    Storm Water network GIS class 
    
    Contains methods to create GeoDataFrames from StormWaterNetworkModel.
    The ability to a create StormWaterNetworkModel from GeoDataFrames is 
    not implemented.
    
    Parameters
    ----------
    gis_data : dict, optional
        Dictionary of GeoDataFrames containing data to populate an instance 
        of StormWaterNetworkGIS.  Valid dictionary keys are 
        'junctions', 'outfalls','storage', 
        'conduits', 'weirs', 'orifices', and 'pumps'
    
    Raises
    ------
    ModuleNotFoundError
        if missing either shapely or geopandas
    """
    
    def __init__(self, gis_data=None) -> None:
        
        if not has_shapely or not has_geopandas:
            raise ModuleNotFoundError('shapley and geopandas are required')
        
        self.junctions = gpd.GeoDataFrame()
        self.outfalls = gpd.GeoDataFrame()
        self.storage = gpd.GeoDataFrame()
        self.conduits = gpd.GeoDataFrame()
        self.weirs = gpd.GeoDataFrame()
        self.orifices = gpd.GeoDataFrame()
        self.pumps = gpd.GeoDataFrame()
        
        if isinstance(gis_data, dict):
            for name in ["junctions", "outfalls", "storage", 
                         "conduits", "weirs", "orifices", "pumps"]:
                gdf = getattr(self, name)
                if name in gis_data.keys():
                    assert isinstance(gis_data[name], gpd.GeoDataFrame)
                    gdf = gis_data[name]

    def _create_gis(self, swn, crs: str = None) -> None:
        """
        Create GIS data from a water network model.
        
        This method is used by wntr.network.io.to_gis
        
        Note: patterns, curves, rules, controls, sources, and options are not 
        saved to the GIS data

        Parameters
        ----------
        wn : WaterNetworkModel
            Water network model
        crs : str, optional
            Coordinate reference system, by default None
        """
  
        # create an updated swmmio model from inp file
        filename = 'temp.inp'
        swn._swmmio_model.inp.save(filename)
        m = swmmio.Model(filename)
        
        self.junctions = m.nodes.geodataframe.loc[swn.junction_name_list,:]
        self.outfalls = m.nodes.geodataframe.loc[swn.outfall_name_list,:]
        self.storage = m.nodes.geodataframe.loc[swn.storage_name_list,:]
        
        self.conduits = m.links.geodataframe.loc[swn.conduit_name_list,:]
        self.weirs = m.links.geodataframe.loc[swn.weir_name_list,:]
        self.orifices = m.links.geodataframe.loc[swn.orifice_name_list,:]
        self.pumps = m.links.geodataframe.loc[swn.pump_name_list,:]
        
        self.set_crs(crs, allow_override=True)
        
    def _create_swn(self, append=None):
        raise NotImplementedError
    
    def to_crs(self, crs):
        """
        Transform CRS of the junctions, tanks, reservoirs, pipes, pumps,
        and valves GeoDataFrames.

        Calls geopandas.GeoDataFrame.to_crs on each GeoDataFrame.

        Parameters
        ----------
        crs : str
            Coordinate reference system
        """
        for name in ["junctions", "outfalls", "storage", 
                     "conduits", "weirs", "orifices", "pumps"]:
            gdf = getattr(self, name)
            if 'geometry' in gdf.columns:
                gdf = gdf.to_crs(crs, inplace=True)

    def set_crs(self, crs, allow_override=False):
        """
        Set CRS of the junctions, tanks, reservoirs, pipes, pumps,
        and valves GeoDataFrames.

        Calls geopandas.GeoDataFrame.set_crs on each GeoDataFrame.

        Parameters
        ----------
        crs : str
            Coordinate reference system
        allow_override : bool (optional)
            Allow override of existing coordinate reference system
        """
        
        for name in ["junctions", "outfalls", "storage", 
                     "conduits", "weirs", "orifices", "pumps"]:
            gdf = getattr(self, name)
            if 'geometry' in gdf.columns:
                gdf = gdf.set_crs(crs, inplace=True,
                                   allow_override=allow_override)

    def add_node_attributes(self, values, name):
        raise NotImplementedError

    def add_link_attributes(self, values, name):
        raise NotImplementedError
    
    def _read(self, files, index_col='index'):
        
        for name in ["junctions", "outfalls", "storage", 
                     "conduits", "weirs", "orifices", "pumps"]:
            gdf = getattr(self, name)
            if name in files.keys():
                data = gpd.read_file(files[name]).set_index(index_col)
                gdf = pd.concat([gdf, data])

    def read_geojson(self, files, index_col='index'):
        """
        Append information from GeoJSON files to a WaterNetworkGIS object

        Parameters
        ----------
        files : dictionary
            Dictionary of GeoJSON filenames, where the keys are in the set 
            ('junction', 'tanks', 'reservoirs', 'pipes', 'pumps', 'valves') and 
            values are the corresponding GeoJSON filename
        index_col : str, optional
            Column that contains the element name
        """
        self._read(files, index_col)

    def read_shapefile(self, files, index_col='index'):
        raise NotImplementedError

    def _write(self, prefix: str, driver="GeoJSON") -> None:
        """
        Write the WaterNetworkGIS object to GIS files

        One file will be created for each type of network element (junctions, 
        pipes, etc.) if those elements exists in the network
        
        Parameters
        ----------
        prefix : str
            Filename prefix, will have the element type (junctions, 
            pipes, etc.) appended
        driver : str, optional
            GeoPandas driver. Use "GeoJSON" for GeoJSON files, use :code:`None` 
            for Esri Shapefile folders, by default "GeoJSON"

        """
        
        if driver is None or driver == "":
            extension = ""
        else:
            extension = "." + driver.lower()
        
        for name in ["junctions", "outfalls", "storage", 
                     "conduits", "weirs", "orifices", "pumps"]:
            gdf = getattr(self, name)
            if len(gdf) > 0:
                filename = prefix + "_" + name + extension
                gdf.to_file(filename, driver=driver)
 
    def write_geojson(self, prefix: str):
        """
        Write the WaterNetworkGIS object to a set of GeoJSON files, one file
        for each network element.

        Parameters
        ----------
        prefix : str
            File prefix
        """
        self._write(prefix=prefix, driver="GeoJSON")

    def write_shapefile(self, prefix: str):
        raise NotImplementedError

    def _valid_names(self, complete_list=True, truncate_names=None):
        raise NotImplementedError
    
    def _shapefile_field_name_map(self):
        raise NotImplementedError
