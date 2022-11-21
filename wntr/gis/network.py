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

import wntr.network.elements

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

    def _create_gis(self, wn, crs: str = None, pumps_as_points: bool = False, 
                   valves_as_points: bool = False,) -> None:
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
        
        # Tanks
        df = df_nodes[df_nodes['node_type'] == 'Tank']
        self.tanks = _extract_geodataframe(df, crs)
            
        # Reservoirs
        df = df_nodes[df_nodes['node_type'] == 'Reservoir']
        self.reservoirs = _extract_geodataframe(df, crs)
            
        # Pipes
        df = df_links[df_links['link_type'] == 'Pipe']
        self.pipes = _extract_geodataframe(df, crs, False)
            
        # Pumps
        df = df_links[df_links['link_type'] == 'Pump']
        self.pumps = _extract_geodataframe(df, crs, pumps_as_points)
            
        # Valves
        df = df_links[df_links['link_type'] == 'Valve']
        self.valves = _extract_geodataframe(df, crs, valves_as_points) 
        
    def _create_wn(self, append=None):
        """
        Create or append a WaterNetworkModel from GeoDataFrames
        
        This method is used by wntr.network.io.from_gis

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
        
        return wn

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
        for data in [self.junctions, self.tanks, self.reservoirs,
                     self.pipes, self.pumps, self.valves]:
            if 'geometry' in data.columns:
                data = data.to_crs(crs, inplace=True)

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

        for data in [self.junctions, self.tanks, self.reservoirs,
                     self.pipes, self.pumps, self.valves]:
            if 'geometry' in data.columns:
                data = data.set_crs(crs, inplace=True,
                                    allow_override=allow_override)

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
    
    def _read(self, files, index_col='index'):
        
        if 'junctions' in files.keys():
            data = gpd.read_file(files['junctions']).set_index(index_col)
            self.junctions = pd.concat([self.junctions, data])
        if 'tanks' in files.keys():
            data = gpd.read_file(files['tanks']).set_index(index_col)
            self.tanks = pd.concat([self.tanks, data])
        if 'reservoirs' in files.keys():
            data = gpd.read_file(files['reservoirs']).set_index(index_col)
            self.reservoirs = pd.concat([self.reservoirs, data])
        if 'pipes' in files.keys():
            data = gpd.read_file(files['pipes']).set_index(index_col)
            self.pipes = pd.concat([self.pipes, data])
        if 'pumps' in files.keys():
            data = gpd.read_file(files['pumps']).set_index(index_col)
            self.pumps = pd.concat([self.pumps, data])
        if 'valves' in files.keys():
            data = gpd.read_file(files['valves']).set_index(index_col)
            self.valves = pd.concat([self.valves, data])

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
        """
        Append information from ESRI Shapefiles to a WaterNetworkGIS object

        Parameters
        ----------
        files : dictionary
            Dictionary of Shapefile directory or filenames, where the keys are
            in the set ('junction', 'tanks', 'reservoirs', 'pipes', 'pumps',
            'valves') and values are the corresponding GeoJSON filename
        index_col : str, optional
            Column that contains the element name
        """
        self._read(files, index_col)

        # ESRI Shapefiles truncate field names to 10 characters. The field_name_map
        # maps truncated names to long names.  The following code assumes the 
        # first 10 characters are unique.
        element_attributes = {
            'junctions': dir(wntr.network.elements.Junction),
            'tanks': dir(wntr.network.elements.Tank),
            'reservoirs': dir(wntr.network.elements.Reservoir),
            'pipes': dir(wntr.network.elements.Pipe),
            'pumps': dir(wntr.network.elements.Pump) +
                     dir(wntr.network.elements.PowerPump) +
                     dir(wntr.network.elements.HeadPump),
            'valves': dir(wntr.network.elements.Valve) +
                      dir(wntr.network.elements.PRValve) +
                      dir(wntr.network.elements.PSValve) +
                      dir(wntr.network.elements.PBValve) +
                      dir(wntr.network.elements.FCValve) +
                      dir(wntr.network.elements.TCValve) +
                      dir(wntr.network.elements.GPValve)}

        field_name_map = {}
        for element, attribute in element_attributes.items():
            field_name_map[element] = {}
            for field_name in attribute:
                if (len(field_name) > 10) and (not field_name.startswith('_')):
                    field_name_map[element][field_name[0:10]] = field_name

        # TODO: pipe property is cv instead of check_valve, this should be updated
        field_name_map['pipes']['check_valv'] = 'check_valve'

        self.junctions.rename(columns=field_name_map['junctions'], inplace=True)
        self.tanks.rename(columns=field_name_map['tanks'], inplace=True)
        self.reservoirs.rename(columns=field_name_map['reservoirs'], inplace=True)
        self.pipes.rename(columns=field_name_map['pipes'], inplace=True)
        self.pumps.rename(columns=field_name_map['pumps'], inplace=True)
        self.valves.rename(columns=field_name_map['valves'], inplace=True)

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
        """
        Write the WaterNetworkGIS object to a set of ESRI Shapefiles, one
        directory for each network element.

        Parameters
        ----------
        prefix : str
            File and directory prefix
        """
        self._write(prefix=prefix, driver=None)
