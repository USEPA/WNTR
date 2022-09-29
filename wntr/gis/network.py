"""
The wntr.gis.network module contains methods to convert between water network 
models and GIS formatted data
"""

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


class WaterNetworkGIS:
    """
    Water network GIS class 
    
    Contains methods to create GeoDataFrames from WaterNetworkModel and 
    create WaterNetworkModel from GeoDataFrames.
    
    Parameters
    ----------
    gis_data : dict, optional
        Dictionary of GeoDataFrames containing data to populate an instance 
        of WaterNetworkGIS.  Valid dictionary keys are 'junction', 'tanks',
        'reservoirs', 'pipes', 'pumps', and 'valves'
    
    Raises
    ------
    ModuleNotFoundError
        if missing either shapely or geopandas
    """
    
    def __init__(self, gis_data=None) -> None:
        
        if not has_shapely or not has_geopandas:
            raise ModuleNotFoundError('shapley and geopandas are required')
        
        self.junctions = gpd.GeoDataFrame()
        self.tanks = gpd.GeoDataFrame()
        self.reservoirs = gpd.GeoDataFrame()
        self.pipes = gpd.GeoDataFrame()
        self.pumps = gpd.GeoDataFrame()
        self.valves = gpd.GeoDataFrame()
        
        if isinstance(gis_data, dict):
            if 'junctions' in gis_data.keys():
                assert isinstance(gis_data['junctions'], gpd.GeoDataFrame)
                self.junctions = gis_data['junctions']
                    
            if 'tanks' in gis_data.keys():
                assert isinstance(gis_data['tanks'], gpd.GeoDataFrame)
                self.tanks = gis_data['tanks']
                    
            if 'reservoirs' in gis_data.keys():
                assert isinstance(gis_data['reservoirs'], gpd.GeoDataFrame)
                self.reservoirs = gis_data['reservoirs']
                    
            if 'pipes' in gis_data.keys():
                assert isinstance(gis_data['pipes'], gpd.GeoDataFrame)
                self.pipes = gis_data['pipes']
                    
            if 'pumps' in gis_data.keys():
                assert isinstance(gis_data['pumps'], gpd.GeoDataFrame)
                self.pumps = gis_data['pumps']
                    
            if 'valves' in gis_data.keys():
                assert isinstance(gis_data['valves'], gpd.GeoDataFrame)
                self.valves = gis_data['valves']

        
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
            Represent pumps as points (True) or lines (False), by default False
        valves_as_points : bool, optional
            Represent valves as points (True) or lines (False), by default False
        """
        
        def _extract_geodataframe(df, crs=None, links_as_points=False):
            # Drop any column with all NaN
            df = df.loc[:, ~df.isna().all()]
            
            if df.shape[0] > 0:
                # Define geom
                if 'node_type' in df.columns:
                    geom = [Point((x,y)) for x,y in df['coordinates']]
                elif 'link_type' in df.columns:
                    geom = []
                    for link_name in df['name']:
                        link = wn.get_link(link_name)
                        if links_as_points: #Point
                            geom.append(Point(link.start_node.coordinates))
                        else: # LineString
                            ls = list()
                            ls.append(link.start_node.coordinates)
                            for v in link.vertices:
                                ls.append(v)
                            ls.append(link.end_node.coordinates)
                            geom.append(LineString(ls))
                    
                # Drop column if not a str, float, int, or bool
                # This could be extended to keep additional data type (list, 
                # tuple, network elements like Patterns, Curves)
                drop_cols = []
                for col in df.columns:
                    if not isinstance(df.iloc[0][col], (str, float, int, bool)):
                        drop_cols.append(col) 
                df = df.drop(columns=drop_cols)
                
                # Set index
                if len(df) > 0:
                    df.set_index('name', inplace=True)
                    df.index.name = None
                
                df = gpd.GeoDataFrame(df, crs=crs, geometry=geom)
            else:
                df = gpd.GeoDataFrame()
                
            return df
        
        # Convert the WaterNetworkModel to a dictionary
        wn_dict = wn.to_dict()
        # Create dataframes for node and link attributes
        df_nodes = pd.DataFrame(wn_dict['nodes'])
        df_links = pd.DataFrame(wn_dict['links'])
        
        # Junctions
        df = df_nodes[df_nodes['node_type'] == 'Junction']
        self.junctions = _extract_geodataframe(df, crs)
            
        df = df_nodes[df_nodes['node_type'] == 'Tank']
        self.tanks = _extract_geodataframe(df, crs)
            
        df = df_nodes[df_nodes['node_type'] == 'Reservoir']
        self.reservoirs = _extract_geodataframe(df, crs)
            
        df = df_links[df_links['link_type'] == 'Pipe']
        self.pipes = _extract_geodataframe(df, crs, False)
            
        df = df_links[df_links['link_type'] == 'Pump']
        self.pumps = _extract_geodataframe(df, crs, pumps_as_points)
            
        df = df_links[df_links['link_type'] == 'Valve']
        self.valves = _extract_geodataframe(df, crs, valves_as_points)
            
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
        """
        
    def create_wn(self, append=None):
        """
        Create or append a WaterNetworkModel from GeoDataFrames
        
       Parameters
       ----------
        append : WaterNetworkModel or None, optional
            Existing WaterNetworkModel to append.  If None, a new WaterNetworkModel 
            is created.
        """
        # Convert the WaterNetworkGIS to a dictionary
        wn_dict = {}
        wn_dict['nodes'] = []
        wn_dict['links'] = []

        for element in [self.junctions, self.tanks, self.reservoirs]:
            if element.shape[0] > 0:
                assert (element['geometry'].geom_type).isin(['Point']).all()
                df = element.reset_index()
                df.rename(columns={'index':'name', 'geometry':'coordinates'}, inplace=True)
                df['coordinates'] = [[x,y] for x,y in zip(df['coordinates'].x, 
                                                          df['coordinates'].y)]
                wn_dict['nodes'].extend(df.to_dict('records'))

        for element in [self.pipes, self.pumps, self.valves]:
            if element.shape[0] > 0:
                assert 'start_node_name' in element.columns
                assert 'end_node_name' in element.columns
                df = element.reset_index()
                df.rename(columns={'index':'name'}, inplace=True)
                # TODO: create vertices from LineString geometry
                df.drop(columns=['geometry'], inplace=True)
                wn_dict['links'].extend(df.to_dict('records'))
        
        # Create WaterNetworkModel from dictionary
        from wntr.network import from_dict
        wn = from_dict(wn_dict, append)
        """
        from wntr.network import WaterNetworkModel
        
        if append is None:
            wn = WaterNetworkModel()
        else:
            wn = append
            
        ### Junctions
        if self.junctions.shape[0] > 0:
            assert (self.junctions['geometry'].geom_type).isin(['Point']).all()
            attributes = list(wn.add_junction.__code__.co_varnames)
            valid_attributes = set(self.junctions.columns) & set(attributes)
            valid_attributes.update(['coordinates'])
            valid_attributes = list(valid_attributes)
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
            valid_attributes = list(valid_attributes)
            
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
            valid_attributes = list(valid_attributes)
            
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
            valid_attributes = list(valid_attributes)
    
            for name, element in self.pipes.iterrows():
                # TODO save vertices to the water network       
                wn.add_pipe(name, **element[valid_attributes].to_dict())

        ### Pumps
        if self.pumps.shape[0] > 0:
            assert 'start_node_name' in self.pumps.columns
            assert 'end_node_name' in self.pumps.columns
            attributes = list(wn.add_pump.__code__.co_varnames)
            valid_attributes = set(self.pumps.columns) & set(attributes)
            valid_attributes = list(valid_attributes)
            
            for name, element in self.pumps.iterrows():
                wn.add_pump(name, **element[valid_attributes].to_dict())
            
        ### Valves
        if self.valves.shape[0] > 0:
            assert 'start_node_name' in self.valves.columns
            assert 'end_node_name' in self.valves.columns
            attributes = list(wn.add_valve.__code__.co_varnames)
            valid_attributes = set(self.valves.columns) & set(attributes)
            valid_attributes = list(valid_attributes)
            
            for name, element in self.valves.iterrows():
                wn.add_valve(name, **element[valid_attributes].to_dict())
        """
        
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

    def write(self, prefix: str, driver="GeoJSON") -> None:
        """
        Write the WaterNetworkGIS object to GIS file(s) with names 
        constructed from parameters.

        One file will be created for each type of network element (junctions, 
        pipes, etc.) if those elements exists in the network
        
        Parameters
        ----------
        prefix : str
            Filename prefix, will have the element type (junctions, 
            pipes, etc.) appended
        driver : str, optional
            GeoPandas driver. Use "GeoJSON" for GeoJSON files, use :code:`None` 
            for ESRI shapefile folders, by default "GeoJSON"

        """
        
        if driver is None or driver == "":
            extension = ""
        else:
            extension = "." + driver.lower()
        
        if len(self.junctions) > 0:
            filename = prefix + "_junctions" + extension
            self.junctions.to_file(filename, driver=driver)
                
        if len(self.tanks) > 0:
            filename = prefix + "_tanks" + extension
            self.tanks.to_file(filename, driver=driver)
            
        if len(self.reservoirs) > 0:
            filename = prefix + "_reservoirs" + extension
            self.reservoirs.to_file(filename, driver=driver)
            
        if len(self.pipes) > 0:
            filename = prefix + "_pipes" + extension
            self.pipes.to_file(filename, driver=driver)
            
        if len(self.pumps) > 0:
            filename = prefix + "_pumps" + extension
            self.pumps.to_file(filename, driver=driver)
            
        if len(self.valves) > 0:
            filename = prefix + "_valves" + extension
            self.valves.to_file(filename, driver=driver)
    