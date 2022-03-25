"""
The wntr.gis.network module contains methods to convert between water network 
models and GIS formatted data
"""

import os.path
import warnings

import pandas as pd
import numpy as np

try:
    from shapely.geometry import LineString, Point, shape
    has_shapely = True
except ModuleNotFoundError:
    has_shapely = False

try:
    import geopandas as gpd
    has_geopandas = True
except ModuleNotFoundError:
    gpd = None
    has_geopandas = False


def wn_to_gis(wn, crs=None, pumps_as_points=False, valves_as_points=False):
    """
    Convert a WaterNetworkModel into GeoDataFrames
    
    Parameters
    ----------
    wn : WaterNetworkModel
        Water network model
    crs : str, optional
        Coordinate reference system, by default None
    pumps_as_points : bool, optional
        Create pumps as points (True) or lines (False), by default False
    valves_as_points : bool, optional
        Create valves as points (True) or lines (False), by default False
        
    Returns
    -------
    WaterNetworkGIS object that contains junctions, tanks, reservoirs, pipes, 
    pumps, and valves GeoDataFrames
        
    """
    gis_data = WaterNetworkGIS()
    gis_data.create_gis(wn, crs, pumps_as_points, valves_as_points)
    
    return gis_data

def gis_to_wn(gis_data):
    """
    Convert GeoDataFrames into a WaterNetworkModel
    
    Parameters
    ----------
    gis_data : WaterNetworkGIS or dictionary of GeoDataFrames
        GeoDataFrames containing water network attributes. If gis_data is a 
        dictionary, then the keys are junctions, tanks, reservoirs, pipes, 
        pumps, and valves. If the pumps or valves are Points, they will be 
        converted to Lines with the same start and end node location.
        
    Returns
    -------
    WaterNetworkModel
        
    """

    if isinstance(gis_data, dict):
        gis_data = WaterNetworkGIS()
        gis_data.junctions = gis_data['junctions']
        gis_data.tanks = gis_data['tanks']
        gis_data.reservoirs = gis_data['reservoirs']
        gis_data.pipes = gis_data['pipes']
        gis_data.pumps = gis_data['pumps']
        gis_data.valves = gis_data['valves']
        
    wn = gis_data.create_wn()
    
    return wn
        
class WaterNetworkGIS:
    """
    Water network GIS class 
    
    Contains methods to create GeoDataFrames from WaterNetworkModel and 
    create WaterNetworkModel from GeoDataFrames.

    Raises
    ------
    ModuleNotFoundError
        if missing either shapely or geopandas
    """
    
    def __init__(self) -> None:
        
        if not has_shapely or not has_geopandas:
            raise ModuleNotFoundError('shapley and geopandas are required')

        self.junctions = None
        self.tanks = None
        self.reservoirs = None
        self.pipes = None
        self.pumps = None
        self.valves = None

    def create_gis(self, wn, crs: str = None, pumps_as_points: bool = False, 
                   valves_as_points: bool = False,) -> None:
        """
        Create GIS data from a water network model.
        
        Note: patterns, curves, rules, controls, sources, and options are not 
        saved to the GIS data

        Parameters
        ----------
        wn : WaterNetworkModel
            Water network model
        crs : str, optional
            Coordinate reference system, by default None
        pumps_as_points : bool, optional
            Create pumps as points (True) or lines (False), by default False
        valves_as_points : bool, optional
            Create valves as points (True) or lines (False), by default False
        """
        ### Junctions
        data = list()
        geometry = list()
        for node_name in wn.junction_name_list:
            node = wn.get_node(node_name)
            g = Point(node.coordinates)
            dd = dict(
                name=node.name,
                type=node.node_type,
                elevation=node.elevation,
                tag=node.tag,
                initial_quality=node.initial_quality,
                base_demand=node.base_demand,
            )
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        if len(df) > 0:
            df.set_index("name", inplace=True)
            df.index.name = None
        self.junctions = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
        
        ### Tanks
        data = list()
        geometry = list()
        for node_name in wn.tank_name_list:
            node = wn.get_node(node_name)
            g = Point(node.coordinates)
            dd = dict(
                name=node.name,
                type=node.node_type,
                elevation=node.elevation,
                tag=node.tag,
                initial_quality=node.initial_quality,
                initial_level=node.init_level,
            )
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        if len(df) > 0:
            df.set_index("name", inplace=True)
            df.index.name = None
        self.tanks = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
        
        ### Reservoirs
        data = list()
        geometry = list()
        for node_name in wn.reservoir_name_list:
            node = wn.get_node(node_name)
            g = Point(node.coordinates)
            dd = dict(
                name=node.name,
                type=node.node_type,
                elevation=node.base_head,
                tag=node.tag,
                initial_quality=node.initial_quality,
                base_head=node.base_head,
            )
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        if len(df) > 0:
            df.set_index("name", inplace=True)
            df.index.name = None
        self.reservoirs = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
        
        ### Valves
        data = list()
        geometry = list()
        for link_name in wn.valve_name_list:
            ls = list()
            link = wn.get_link(link_name)
            ls.append(link.start_node.coordinates)
            for v in link.vertices:
                ls.append(v)
            ls.append(link.end_node.coordinates)
            g = LineString(ls)
            g2 = Point(link.start_node.coordinates)
            dd = dict(
                name=link.name,
                start_node_name=link.start_node_name,
                end_node_name=link.end_node_name,
                type=link.link_type,
                valve_type=link.valve_type,
                tag=link.tag,
                initial_status=link.initial_status,
                initial_setting=link.initial_setting,
            )
            data.append(dd)
            if valves_as_points:
                geometry.append(g2)
            else:
                geometry.append(g)
        df = pd.DataFrame(data)
        if len(df) > 0:
            df.set_index("name", inplace=True)
            df.index.name = None
        self.valves = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

        ### Pumps
        data = list()
        geometry = list()
        for link_name in wn.pump_name_list:
            ls = list()
            link = wn.get_link(link_name)
            ls.append(link.start_node.coordinates)
            for v in link.vertices:
                ls.append(v)
            ls.append(link.end_node.coordinates)
            g = LineString(ls)
            g2 = Point(link.start_node.coordinates)
            dd = dict(
                name=link.name,
                start_node_name=link.start_node_name,
                end_node_name=link.end_node_name,
                type=link.link_type,
                pump_type=link.pump_type,
                tag=link.tag,
                initial_status=link.initial_status,
                initial_setting=link.initial_setting,
            )
            data.append(dd)
            if pumps_as_points:
                geometry.append(g2)
            else:
                geometry.append(g)
        df = pd.DataFrame(data)
        if len(df) > 0:
            df.set_index("name", inplace=True)
            df.index.name = None
        self.pumps = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
        
        ### Pipes
        data = list()
        geometry = list()
        for link_name in wn.pipe_name_list:
            ls = list()
            link = wn.get_link(link_name)
            ls.append(link.start_node.coordinates)
            for v in link.vertices:
                ls.append(v)
            ls.append(link.end_node.coordinates)
            g = LineString(ls)
            dd = dict(
                name=link.name,
                start_node_name=link.start_node_name,
                end_node_name=link.end_node_name,
                type=link.link_type,
                tag=link.tag,
                initial_status=link.initial_status,
                length=link.length,
                diameter=link.diameter,
                roughness=link.roughness,
                cv=link.cv,
            )
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        if len(df) > 0:
            df.set_index("name", inplace=True)
            df.index.name = None
        self.pipes = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

        
    def create_wn(self):
        """
        Create a water network model from GIS data
        
        Note: The water network model will not include patterns, curves, rules, 
        controls, or sources.  Options will be set to default values.
        
        """
        from wntr.network import WaterNetworkModel
        
        wn = WaterNetworkModel()
        
        ### Junctions
        if self.junctions.shape[0] > 0:
            assert (self.junctions['geometry'].geom_type).isin(['Point']).all()
            attributes = list(wn.add_junction.__code__.co_varnames)
            valid_attributes = set(self.junctions.columns) & set(attributes)
            valid_attributes.update(['coordinates'])
            # TODO: we could also set additional attributes....
            # additional_attributes = set(self.junctions.columns) - set(attributes)
            
            for name, element in self.junctions.iterrows():
                element['coordinates'] = (element.geometry.xy[0][0],
                                         element.geometry.xy[1][0])
                wn.add_junction(name, **element[valid_attributes].to_dict())
        
        ### Tanks
        if self.tanks.shape[0] > 0:
            assert (self.tanks['geometry'].geom_type).isin(['Point']).all()
            attributes = list(wn.add_tank.__code__.co_varnames)
            valid_attributes = set(self.tanks.columns) & set(attributes)
            valid_attributes.update(['coordinates'])
            
            for name, element in self.tanks.iterrows():
                element['coordinates'] = (element.geometry.xy[0][0],
                                         element.geometry.xy[1][0])
                wn.add_tank(name, **element[valid_attributes].to_dict())
    
        ### Reservoirs
        if self.reservoirs.shape[0] > 0:
            assert (self.reservoirs['geometry'].geom_type).isin(['Point']).all()
            attributes = list(wn.add_reservoir.__code__.co_varnames)
            valid_attributes = set(self.reservoirs.columns) & set(attributes)
            valid_attributes.update(['coordinates'])
            
            for name, element in self.reservoirs.iterrows():
                element['coordinates'] = (element.geometry.xy[0][0],
                                         element.geometry.xy[1][0])
                wn.add_reservoir(name, **element[valid_attributes].to_dict())
                
        ### Pipes
        if self.pipes.shape[0] > 0:
            assert 'start_node_name' in self.pipes.columns
            assert 'end_node_name' in self.pipes.columns
            attributes = list(wn.add_pipe.__code__.co_varnames)
            valid_attributes = set(self.pipes.columns) & set(attributes)
    
            for name, element in self.pipes.iterrows():
                # TODO save vertices to the water network       
                wn.add_pipe(name, **element[valid_attributes].to_dict())

        ### Pumps
        if self.pumps.shape[0] > 0:
            assert 'start_node_name' in self.pumps.columns
            assert 'end_node_name' in self.pumps.columns
            attributes = list(wn.add_pump.__code__.co_varnames)
            valid_attributes = set(self.pumps.columns) & set(attributes)
            
            for name, element in self.pumps.iterrows():
                wn.add_pump(name, **element[valid_attributes].to_dict())
            
        ### Valves
        if self.valves.shape[0] > 0:
            assert 'start_node_name' in self.valves.columns
            assert 'end_node_name' in self.valves.columns
            attributes = list(wn.add_valve.__code__.co_varnames)
            valid_attributes = set(self.valves.columns) & set(attributes)
            
            for name, element in self.valves.iterrows():
                wn.add_valve(name, **element[valid_attributes].to_dict())
                
        return wn
                
    def add_node_attributes(self, values, name):
        """
        Add attribute to junctions, tanks, or reservoirs GeoDataFrames

        Parameters
        ----------
        values : dict or Series or row of a DataFrame
            Attribute values
        name : str
            Attribute name
        """
        for node_name, value in values.items():
            if node_name in self.junctions.index:
                if name not in self.junctions.columns:
                    self.junctions[name] = np.nan
                self.junctions.loc[node_name, name] = value
            elif node_name in self.tanks.index:
                if name not in self.tanks.columns:
                    self.tanks[name] = np.nan
                self.tanks.loc[node_name, name] = value
            elif node_name in self.reservoirs.index:
                if name not in self.reservoirs.columns:
                    self.reservoirs[name] = np.nan
                self.reservoirs.loc[node_name, name] = value
            
    def add_link_attributes(self, values, name):
        """
        Add attribute to pipes, pumps, or valves GeoDataFrames

        Parameters
        ----------
        values : dict or Series or row of a DataFrame
            Attribute values
        name : str
            Attribute name 
        """
        for link_name, value in values.items():
            if link_name in self.pipes.index:
                if name not in self.pipes.columns:
                    self.pipes[name] = np.nan
                self.pipes.loc[link_name, name] = value
            elif link_name in self.valves.index:
                if name not in self.valves.columns:
                    self.valves[name] = np.nan
                self.valves.loc[link_name, name] = value
            elif link_name in self.pumps.index:
                if name not in self.pumps.columns:
                    self.pumps[name] = np.nan
                self.pumps.loc[link_name, name] = value

    def write(self, prefix: str, crs: str = None, driver="GeoJSON") -> None:
        """
        Write the Geometry object to GIS file(s) with names constructed from parameters.

        One file will be created for each type of network element (junctions, 
        pipes, etc.) if those elements exists in the network
        

        Parameters
        ----------
        prefix : str
            Filename prefix, will have the element type (junctions, 
            pipes, etc.) appended
        crs : str, optional
            Coordinate reference system, by default None
        driver : str, optional
            Geopandas driver (use :code:`None` for ESRI shapefile folders), 
            by default "GeoJSON",
        """
        
        def write_gdf(gdf, crs, filename, driver):
            if crs is not None:
                gdf.to_crs(crs).to_file(filename, driver=driver)
            else:
                gdf.to_file(filename, driver=driver)
                
        if driver is None or driver == "":
            extension = ""
        else:
            extension = "." + driver.lower()
        
        if len(self.junctions) > 0:
            filename = prefix + "_junctions" + extension
            write_gdf(self.junctions, crs, filename, driver)
                
        if len(self.tanks) > 0:
            filename = prefix + "_tanks" + extension
            write_gdf(self.tanks, crs, filename, driver)
            
        if len(self.reservoirs) > 0:
            filename = prefix + "_reservoirs" + extension
            write_gdf(self.reservoirs, crs, filename, driver)
            
        if len(self.pipes) > 0:
            filename = prefix + "_pipes" + extension
            write_gdf(self.pipes, crs, filename, driver)
            
        if len(self.pumps) > 0:
            filename = prefix + "_pumps" + extension
            write_gdf(self.pumps, crs, filename, driver)
            
        if len(self.valves) > 0:
            filename = prefix + "_valves" + extension
            write_gdf(self.valves, crs, filename, driver)
    