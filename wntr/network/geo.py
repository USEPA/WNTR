"""
Geographic and shape functionality
"""

import os.path
import warnings

import pandas as pd

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


class NetworkGeometry:
    """
    An object for holding the WaterNetworkModel geometry as a 
    set of GeoPandas and shapely objects.
    """

    def __init__(self, wn, crs: str = "") -> None:
        if not has_shapely or not has_geopandas:
            raise ModuleNotFoundError("Cannot do WNTR geometry without shapely and pandas")
        self.crs = crs
        self._wn = wn
        self.junctions = None
        self.tanks = None
        self.reservoirs = None
        self.pipes = None
        self.pumps = None
        self.valves = None
        self.set_data()

    def set_data(
        self,
        results = None,
        time: int = -1,
        node_data: pd.DataFrame = None,
        link_data: pd.DataFrame = None,
    ) -> None:
        """
        Set any extra data to be attached to the geometry objects ( **erases data previously set** )

        Parameters
        ----------
        results : SimulationResults, optional
            simulation results to add, by default None
        time : int, optional
            timestep of the results to add, by default the last timestep
        node_data : :class:`~pandas.DataFrame` or Dict[Dict or :class:`~pandas.Series`], optional
            data to add to nodes, by default None, see format note below 
        link_data : :class:`~pandas.DataFrame` or Dict[Dict or :class:`~pandas.Series`],, optional
            data to add to links, by default None, see format note below

        
        :attr:`node_data` and :attr:`link_data` must be a :class:`~pandas.DataFrame` or a :class:`dict`.
        If a :class:`~pandas.DataFrame`, it must be indexed by node/link name with columns
        as the names of the attributes.
        If a dictionary, it must have
        the attribute name as the outer key, and node/link names as the inner key. It can also
        handle a dictionary of :class:`pandas.Series` as long as the series are indexed by 
        node/link name.
        """
        crs = self.crs
        wn = self._wn
        from wntr.sim.results import SimulationResults
        if isinstance(results, SimulationResults) and time == -1:
            time = results.node["head"].index.iloc[-1]

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
            if isinstance(results, (SimulationResults,)):
                for key in results.node.keys():
                    dd[key] = results.node[key].loc[time, node_name]
            if isinstance(node_data, (pd.DataFrame, dict,)):
                for column in node_data.keys():
                    if node_name in node_data[column].keys():
                        dd[column] = node_data[column][node_name]
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        self.junctions = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

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
            if isinstance(results, (SimulationResults,)):
                for key in results.node.keys():
                    dd[key] = results.node[key].loc[time, node_name]
            if isinstance(node_data, (pd.DataFrame, dict,)):
                for column in node_data.keys():
                    if node_name in node_data[column].keys():
                        dd[column] = node_data[column][node_name]
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        self.tanks = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

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
            if isinstance(results, (SimulationResults,)):
                for key in results.node.keys():
                    dd[key] = results.node[key].loc[time, node_name]
            if isinstance(node_data, (pd.DataFrame, dict,)):
                for column in node_data.keys():
                    if node_name in node_data[column].keys():
                        dd[column] = node_data[column][node_name]
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        self.reservoirs = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

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
                type=link.link_type,
                valve_type=link.valve_type,
                tag=link.tag,
                initial_status=link.initial_status,
                initial_setting=link.initial_setting,
            )
            if isinstance(results, (SimulationResults,)):
                for key in results.link.keys():
                    dd[key] = results.link[key].loc[time, link_name]
            if isinstance(link_data, (pd.DataFrame, dict,)):
                for column in link_data.keys():
                    if link_name in link_data[column].keys():
                        dd[column] = link_data[column][link_name]
            data.append(dd)
            geometry.append([g, g2])
        df = pd.DataFrame(data)
        self.valves = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

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
            dd = dict(
                name=link.name,
                type=link.link_type,
                pump_type=link.pump_type,
                tag=link.tag,
                initial_status=link.initial_status,
                initial_setting=link.initial_setting,
            )
            if isinstance(results, (SimulationResults,)):
                for key in results.link.keys():
                    dd[key] = results.link[key].loc[time, link_name]
            if isinstance(link_data, (pd.DataFrame, dict,)):
                for column in link_data.keys():
                    if link_name in link_data[column].keys():
                        dd[column] = link_data[column][link_name]
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        self.pumps = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

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
                type=link.link_type,
                tag=link.tag,
                initial_status=link.initial_status,
                length=link.length,
                diameter=link.diameter,
                roughness=link.roughness,
                cv=link.cv,
            )
            if isinstance(results, (SimulationResults,)):
                for key in results.link.keys():
                    dd[key] = results.link[key].loc[time, link_name]
            if isinstance(link_data, (pd.DataFrame, dict,)):
                for column in link_data.keys():
                    if link_name in link_data[column].keys():
                        dd[column] = link_data[column][link_name]
            data.append(dd)
            geometry.append(g)
        df = pd.DataFrame(data)
        self.pipes = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

    def write_geojson(self, prefix: str, path: str = ".", suffix: str = "") -> None:
        """
        Write the Geometry object to a GeoJSON file

        Parameters
        ----------
        prefix : str
            the filename prefix, will have the element type (junctions, valves) appended
        path : str, optional
            the path to write the file, by default '.' (current directory)
        suffix : str, optional
            if desired, an indicator such as the timestep or other string; by default blank
        """
        prefix = os.path.join(path, prefix)
        try:
            self.junctions.to_file(
                prefix + "_junctions" + suffix + ".geojson", driver="GeoJSON",
            )
        except ValueError:
            warnings.warn('No junctions in water network, no file created for them')
        try:
            self.tanks.to_file(
                prefix + "_tanks" + suffix + ".geojson", driver="GeoJSON",
            )
        except ValueError:
            warnings.warn('No tanks in water network, no file created for them')
        try:
            self.reservoirs.to_file(
                prefix + "_reservoirs" + suffix + ".geojson", driver="GeoJSON",
            )
        except ValueError:
            warnings.warn('No reservoirs in water network, no file created for them')
        try:
            self.pipes.to_file(
                prefix + "_pipes" + suffix + ".geojson", driver="GeoJSON",
            )
        except ValueError:
            warnings.warn('No pipes in water network, no file created for them')
        try:
            self.pumps.to_file(
                prefix + "_pumps" + suffix + ".geojson", driver="GeoJSON",
            )
        except ValueError:
            warnings.warn('No pumps in water network, no file created for them')
        try:
            self.valves.to_file(
                prefix + "_valves" + suffix + ".geojson", driver="GeoJSON",
            )
        except ValueError:
            warnings.warn('No valves in water network, no file created for them')
