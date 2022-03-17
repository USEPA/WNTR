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


def wn_to_gis(wn, crs: str = "", pump_as_point_geometry=True, valve_as_point_geometry=True):
    """
    Convert a WaterNetworkModel into GeoDataFrames
    
    Parameters
    ----------
    wn : WaterNetworkModel
        Water network model
    crs : str, optional
        Coordinate reference string, by default ""
    pump_as_point_geometry : bool, optional
        Create pumps as points (True) or lines (False), by default True
    valve_as_point_geometry : bool, optional
        Create valves as points (True) or lines (False), by default True
        
    Returns
    -------
    WaterNetworkGIS object that contains junctions, tanks, reservoirs, pipes, 
    pumps, and valves GeoDataFrames
        
    """
    gis_data = WaterNetworkGIS()
    gis_data.create_gis(wn, crs, pump_as_point_geometry, valve_as_point_geometry)
    
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

    def create_gis(
        self, wn, crs: str = None, pump_as_point_geometry: bool = None, valve_as_point_geometry: bool = None,
    ) -> None:
        """
        Create GIS data from a water network model.
        
        Note: patterns, curves, rules, controls, sources, and options are not 
        saved to the GIS data

        Parameters
        ----------
        wn : WaterNetworkModel
            Water network model
        crs : str, optional
            the coordinate reference system, such as by default None (use internal object attribute value).
            If set, this will update the object's internal attribute
        pump_as_point_geometry : bool, optional
            create pumps as points (True) or lines (False), by default None (use internal object attribute value).
            If set, this will update the object's internal attribute
        valve_as_point_geometry : bool, optional
            create valves as points (True) or lines (False), by default None (use internal object attribute value).
            If set, this will update the object's internal attribute
        """
        pumps_as_points = pump_as_point_geometry
        valves_as_points = valve_as_point_geometry
        
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
        assert (self.junctions['geometry'].geom_type).isin(['Point']).all()
        attributes = ['base_demand', 'demand_pattern', 'elevation', 'demand_category']
        
        for name, element in self.junctions.iterrows():
            kwargs = {}
            for attribute in attributes:
                if attribute in element.index:
                    kwargs[attribute] = element[attribute] 

            x = element.geometry.xy[0][0]
            y = element.geometry.xy[1][0]
            kwargs['coordinates'] = (x,y)

            wn.add_junction(name, **kwargs)
        
        ### Tanks
        assert (self.tanks['geometry'].geom_type).isin(['Point']).all()
        attributes = ['elevation', 'init_level', 'min_level', 'max_level',
                      'diameter', 'min_vol', 'vol_curve', 'overflow']
        
        for name, element in self.tanks.iterrows():
            kwargs = {}
            for attribute in attributes:
                if attribute in element.index:
                    kwargs[attribute] = element[attribute] 

            x = element.geometry.xy[0][0]
            y = element.geometry.xy[1][0]
            kwargs['coordinates'] = (x,y)
            
            wn.add_tank(name, **kwargs)
    
        ### Reservoirs
        assert (self.reservoirs['geometry'].geom_type).isin(['Point']).all()
        attributes = ['base_head', 'head_pattern']
        
        for name, element in self.reservoirs.iterrows():
            kwargs = {}
            for attribute in attributes:
                if attribute in element.index:
                    kwargs[attribute] = element[attribute] 

            x = element.geometry.xy[0][0]
            y = element.geometry.xy[1][0]
            kwargs['coordinates'] = (x,y)
                
            wn.add_reservoir(name, **kwargs)
            
        ### Pipes
        assert (self.pipes['geometry'].geom_type).isin(['LineString', 'MultiLineString']).all()
        assert 'start_node_name' in self.pipes.columns
        assert 'end_node_name' in self.pipes.columns
        attributes = ['start_node_name', 'end_node_name', 'length', 'diameter', 
                      'roughness', 'minor_loss', 'initial_status', 'check_valve']

        for name, element in self.pipes.iterrows():
            kwargs = {}
            for attribute in attributes:
                if attribute in element.index:
                    kwargs[attribute] = element[attribute] 

            # TODO save vertices to the water network       

            wn.add_pipe(name, **kwargs)

        ### Pumps
        # TODO if geometry is a Point, the dataframe might not include a start or end node name 
        # and a new node might need to be added and connected to the out link.
        assert (self.pipes['geometry'].geom_type).isin(['Point', 'LineString', 'MultiLineString']).all()
        assert 'start_node_name' in self.pipes.columns
        assert 'end_node_name' in self.pipes.columns
        attributes = ['start_node_name', 'end_node_name', 'pump_type', 
                      'pump_parameter', 'speed', 'pattern', 'initial_status']
        
        for name, element in self.pumps.iterrows():
            kwargs = {}
            for attribute in attributes:
                if attribute in element.index:
                    kwargs[attribute] = element[attribute] 

            wn.add_pump(name, **kwargs)
            
        ### Valves
        # TODO if geometry is a Point, the dataframe might not include a start or end node name 
        # and a new node might need to be added and connected to the out link.
        assert (self.pipes['geometry'].geom_type).isin(['Point', 'LineString', 'MultiLineString']).all()
        assert 'start_node_name' in self.pipes.columns
        assert 'end_node_name' in self.pipes.columns
        attributes = ['start_node_name', 'end_node_name', 'diameter', 
                      'valve_type', 'minor_loss', 'initial_setting', 'initial_status']
        
        for name, element in self.valves.iterrows():
            kwargs = {}
            for attribute in attributes:
                if attribute in element.index:
                    kwargs[attribute] = element[attribute] 

            wn.add_valve(name, **kwargs)
            
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

    def write(self, prefix: str, path: str = None, suffix: str = None, driver="GeoJSON") -> None:
        """
        Write the Geometry object to GIS file(s) with names constructed from parameters.

        The file name is of the format

            [ ``{path}/`` ] ``{prefix}_$elementType`` [ ``_{suffix}`` ] ``.$extensionByDriver``

        where parameters surrounded by brackets "[]" are optional parameters and the ``$`` indicates
        parts of the filename determined by the function. One file will be created for each type of
        network element (junctions, pipes, etc.) assuming that the element exists in the network;
        i.e., blank files will not be created. Drivers available are any of the geopandas valid
        drivers.


        Parameters
        ----------
        prefix : str
            the filename prefix, will have the element type (junctions, valves) appended
        path : str, optional
            the path to write the file, by default None (current directory)
        suffix : str, optional
            if desired, an indicator such as the timestep or other string, by default None
        driver : str, optional
            one of the geopandas drivers (use :code:`None` for ESRI shapefile folders), by default "GeoJSON",
        """
        if path is None:
            path = "."
        if suffix is None:
            suffix = ""
        prefix = os.path.join(path, prefix)
        if driver is None or driver == "":
            extension = ""
        else:
            extension = "." + driver.lower()
        if len(self.junctions) > 0:
            self.junctions.to_file(
                prefix + "_junctions" + suffix + extension, driver=driver,
            )
        if len(self.tanks) > 0:
            self.tanks.to_file(
                prefix + "_tanks" + suffix + extension, driver=driver,
            )
        if len(self.reservoirs) > 0:
            self.reservoirs.to_file(
                prefix + "_reservoirs" + suffix + extension, driver=driver,
            )
        if len(self.pipes) > 0:
            self.pipes.to_file(
                prefix + "_pipes" + suffix + extension, driver=driver,
            )
        if len(self.pumps) > 0:
            self.pumps.to_file(
                prefix + "_pumps" + suffix + extension, driver=driver,
            )
        if len(self.valves) > 0:
            self.valves.to_file(
                prefix + "_valves" + suffix + extension, driver=driver,
            )
    


