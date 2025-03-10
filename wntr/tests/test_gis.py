import sys
import unittest
import warnings
import os
from os.path import abspath, dirname, isfile, join

import numpy as np
import pandas as pd
import networkx as nx
import wntr
from pandas.testing import assert_frame_equal, assert_series_equal

try:
    from shapely.geometry import LineString, Point, Polygon, shape
    has_shapely = True
except ModuleNotFoundError:
    has_shapely = False

try:
    import geopandas as gpd
    has_geopandas = True
except ModuleNotFoundError:
    gpd = None
    has_geopandas = False
    
try:
    import rasterio
    has_rasterio = True
except ModuleNotFoundError:
    rasterio = None
    has_rasterio = False
    
testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


@unittest.skipIf(not has_geopandas,
                 "Cannot test GIS capabilities: geopandas is missing")
class TestGIS(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net1.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()
        self.gis_data = self.wn.to_gis()
        
        vertex_inp_file = join(datadir, "io.inp")
        self.vertex_wn = self.wntr.network.WaterNetworkModel(vertex_inp_file)
        self.vertex_gis_data = self.vertex_wn.to_gis()
        
        polygon_pts = [[(25,80), (65,80), (65,60), (25,60)],
                       [(25,60), (80,60), (80,30), (25,30)],
                       [(40,50), (60,65), (60,15), (40,15)]]
        polygon_data = []
        for i, pts in enumerate(polygon_pts):
            geometry = Polygon(pts)
            polygon_data.append({'name': str(i+1), 
                                 'value': (i+1)*10,
                                 'geometry': geometry.convex_hull})
            
        df = pd.DataFrame(polygon_data)
        df.set_index("name", inplace=True)
        self.polygons = gpd.GeoDataFrame(df, crs=None)

        points = [(52,71), (75,40), (27,37)]
        point_data = []
        for i, pts in enumerate(points):
            geometry = Point(pts)
            point_data.append({'geometry': geometry})
            
        df = pd.DataFrame(point_data)
        self.points = gpd.GeoDataFrame(df, crs=None)

    @classmethod
    def tearDownClass(self):
        pass
    
    def test_gis_index(self):
        # Tests that WN can be made using dataframes with customized index names
        wn_gis = self.wn.to_gis()
        
        # check that index name of geodataframes is "name"
        assert wn_gis.junctions.index.name == "name"
        assert wn_gis.tanks.index.name == "name"
        assert wn_gis.reservoirs.index.name == "name"
        assert wn_gis.pipes.index.name == "name"
        assert wn_gis.pumps.index.name == "name"
        
        # check that index names can be changed and still be read back into a wn
        wn_gis.junctions.index.name = "my_index"
        wn_gis.pipes.index.name = "my_index"
        wn2 = wntr.network.from_gis(wn_gis)
        
        assert self.wn.pipe_name_list == wn2.pipe_name_list
        assert self.wn.junction_name_list == wn2.junction_name_list
        
        # test snap and intersect functionality with alternate index names
        result = wntr.gis.snap(self.points, wn_gis.junctions, tolerance=5.0)
        assert len(result) > 0
        result = wntr.gis.snap(wn_gis.junctions, self.points, tolerance=5.0)
        assert len(result) > 0
        result = wntr.gis.intersect(wn_gis.junctions, self.polygons)
        assert len(result) > 0
        result = wntr.gis.intersect(self.polygons, wn_gis.pipes)
        assert len(result) > 0
        
        # check that custom index name persists after running snap/intersect
        assert wn_gis.junctions.index.name == "my_index"
        assert wn_gis.pipes.index.name == "my_index"

    def test_wn_to_gis(self):
        # Check type
        isinstance(self.gis_data.junctions, gpd.GeoDataFrame)
        isinstance(self.gis_data.tanks, gpd.GeoDataFrame)
        isinstance(self.gis_data.reservoirs, gpd.GeoDataFrame)
        isinstance(self.gis_data.pipes, gpd.GeoDataFrame)
        isinstance(self.gis_data.pumps, gpd.GeoDataFrame)
        isinstance(self.gis_data.valves, gpd.GeoDataFrame)
        
        # Check size
        assert self.gis_data.junctions.shape[0] == self.wn.num_junctions
        assert self.gis_data.tanks.shape[0] == self.wn.num_tanks
        assert self.gis_data.reservoirs.shape[0] == self.wn.num_reservoirs
        assert self.gis_data.pipes.shape[0] == self.wn.num_pipes
        assert self.gis_data.pumps.shape[0] == self.wn.num_pumps
        #assert self.gis_data.valves.shape[0] == self.wn.num_valves
        
        # Check minimal set of attributes
        assert set(['elevation', 'geometry']).issubset(self.gis_data.junctions.columns)
        assert set(['elevation', 'geometry']).issubset(self.gis_data.tanks.columns)
        assert set(['geometry']).issubset(self.gis_data.reservoirs.columns)
        assert set(['start_node_name', 'end_node_name', 'geometry']).issubset(self.gis_data.pipes.columns)
        assert set(['start_node_name', 'end_node_name', 'geometry']).issubset(self.gis_data.pumps.columns)
        #assert set(['start_node_name', 'end_node_name', 'geometry']).issubset(self.gis_data.valves.columns) # Net1 has no valves

        #check base_demand and demand_pattern attrivutes
        assert set(['base_demand','demand_pattern']).issubset(self.gis_data.junctions.columns)
        
    def test_gis_to_wn(self):
        
        wn2 = wntr.network.io.from_gis(self.gis_data)
        G1 = self.wn.to_graph()
        G2 = wn2.to_graph()
        
        assert nx.is_isomorphic(G1, G2)
        
        # test vertices
        vertex_wn2 = wntr.network.io.from_gis(self.vertex_gis_data)
        for name, link in vertex_wn2.links():
            assert link.vertices == self.vertex_wn.get_link(name).vertices
                         
    def test_intersect_points_with_polygons(self):
        
        stats = wntr.gis.intersect(self.gis_data.junctions, self.polygons, 'value')
        
        # Junction 22 intersects poly2 val=20, intersects poly3 val=30
        # weighted mean = (1*20+0.5*30)/2 = 17.5
        expected = pd.Series({'intersections': ['2','3'], 'values': [20,30]})
        expected['n'] = len(expected['values'])
        expected['sum'] = float(sum(expected['values']))
        expected['min'] = float(min(expected['values']))
        expected['max'] = float(max(expected['values']))
        expected['mean'] = expected['sum']/expected['n']
        expected = expected.reindex(stats.columns)
        
        assert_series_equal(stats.loc['22',:], expected, check_dtype=False, check_names=False)
        
        # Junction 31: no intersections
        expected = pd.Series({'intersections': [], 'values': [], 'n': 0, 
                              'sum': np.nan, 'min': np.nan, 'max': np.nan,
                              'mean': np.nan, })
        
        assert_series_equal(stats.loc['31',:], expected, check_dtype=False, check_names=False)
        
    def test_intersect_lines_with_polygons(self):
        
        bv = 0
        stats = wntr.gis.intersect(self.gis_data.pipes, self.polygons, 'value', True, bv)

        ax = self.polygons.plot(column='value', alpha=0.5)
        ax = wntr.graphics.plot_network(self.wn, ax=ax)
        
        # Pipe 22 intersects poly2 100%, val=20, intersects poly3 50%, val=30
        expected_weighted_mean = (20*1+30*0.5)/1.5
        expected = pd.Series({'intersections': ['2','3'], 'values': [20,30], 'weighted_mean': expected_weighted_mean})
        expected['n'] = len(expected['values'])
        expected['sum'] = float(sum(expected['values']))
        expected['min'] = float(min(expected['values']))
        expected['max'] = float(max(expected['values']))
        expected['mean'] = expected['sum']/expected['n']
        expected = expected.reindex(stats.columns)
        
        assert_series_equal(stats.loc['22',:], expected, check_dtype=False, check_names=False)
        
        # Pipe 31: no intersections
        expected = pd.Series({'intersections': ['BACKGROUND'], 'values': [bv],
                              'n': 1, 'sum': bv, 'min': bv, 'max': bv,
                              'mean': bv, 'weighted_mean': bv})
        
        assert_series_equal(stats.loc['31',:], expected, check_dtype=False, check_names=False)
        
        # Pipe 122
        self.assertEqual(stats.loc['122','intersections'], ['BACKGROUND', '2', '3'])
        # total length = 30
        expected_weighted_mean = (bv*(5/30) + 30*(25/30) + 20*(10/30))/(40/30)
        self.assertAlmostEqual(stats.loc['122','weighted_mean'], expected_weighted_mean, 2)
        
    
    def test_intersect_polygons_with_lines(self):
        
        stats = wntr.gis.intersect(self.polygons, self.gis_data.pipes)
        
        expected = pd.DataFrame([{'intersections': ['10', '11', '110', '111', '112', '12'], 'n': 6},
                                 {'intersections': ['111', '112', '113', '121', '122', '21', '22'], 'n': 7},
                                 {'intersections': ['112', '122', '21', '22'], 'n': 4}])
        expected.index=['1', '2', '3']
    
        assert_frame_equal(stats, expected, check_dtype=False)
        
    def test_intersect_polygons_with_lines_zero_length(self):
        
        wn = wntr.morph.break_pipe(self.wn, '22', '22_A', '22_A','22_B', split_at_point=0.5)
        wn.add_pipe('22_0', '22_A', '22_B', length=0)
        
        gis_data = wn.to_gis()
        assert gis_data.pipes.length['22_0'] == 0
        
        # No value
        stats = wntr.gis.intersect(gis_data.pipes, self.polygons)
        assert stats.shape == (14,2)
        
        # With value
        stats = wntr.gis.intersect(gis_data.pipes, self.polygons, 'value')
        assert stats.shape == (14,8)
        
        assert stats.loc['22_0', 'weighted_mean'] == stats.loc['22_0', 'mean'] # zero length pipe
        assert stats.loc['22_A', 'weighted_mean'] == 20 # overlaps with 20 and 30, but zero length with 30
        assert stats.loc['22', 'weighted_mean'] == 25 # overlaps with 20 and 30 across the entire pipe
        
        assert (stats.loc[stats['n']>0, 'weighted_mean'] >= stats.loc[stats['n']>0, 'min']).all()
        assert (stats.loc[stats['n']>0, 'weighted_mean'] <= stats.loc[stats['n']>0, 'max']).all()
        
    def test_set_crs_to_crs(self):
        # Test uses transformation from https://epsg.io/
        # https://epsg.io/transform#s_srs=4326&t_srs=3857&x=20.0000000&y=70.0000000
        
        gis_data = self.wn.to_gis()
        
        gis_data.set_crs('EPSG:4326')  # EPSG:4326 WGS 84
        x0 = gis_data.junctions.loc['10','geometry'].x
        y0 = gis_data.junctions.loc['10','geometry'].y
        self.assertEqual(gis_data.junctions.crs, 'EPSG:4326')
        self.assertEqual(x0, 20)
        self.assertEqual(y0, 70)
        
        gis_data.to_crs('EPSG:3857')  # EPSG:3857 WGS 84 / Pseudo-Mercator
        x1 = gis_data.junctions.loc['10','geometry'].x
        y1 = gis_data.junctions.loc['10','geometry'].y
        self.assertEqual(gis_data.junctions.crs, 'EPSG:3857')
        self.assertAlmostEqual(x1, 2226389.8158654715, 6)
        self.assertAlmostEqual(y1, 11068715.659379493, 6)
        
    def test_add_attributes_and_write(self):
        
        gis_data = self.wn.to_gis()
        
        gis_data.add_node_attributes(self.results.node['pressure'].loc[3600,:], 'Pressure_1hr')
        gis_data.add_link_attributes(self.results.link['flowrate'].loc[3600,:], 'Flowrate_1hr')
       
        assert 'Pressure_1hr' in gis_data.junctions.columns
        assert 'Pressure_1hr' in gis_data.tanks.columns
        assert 'Pressure_1hr' in gis_data.reservoirs.columns
        assert 'Flowrate_1hr' in gis_data.pipes.columns
        assert 'Flowrate_1hr' in gis_data.pumps.columns
        assert 'Flowrate_1hr' not in gis_data.valves.columns # Net1 has no valves
    
    def test_write_geojson(self):
        prefix = 'temp_Net1'
        components = ['junctions', 'tanks', 'reservoirs', 'pipes', 'pumps', 'valves']
        for component in components:
            filename = abspath(join(testdir, prefix+'_'+component+'.geojson'))
            if isfile(filename):
                os.remove(filename)
            
        self.gis_data.write_geojson(abspath(join(testdir, prefix)))

        for component in components:
            if component == 'valves':
                continue # Net1 has no valves
            # check file exists
            filename = abspath(join(testdir, prefix+'_'+component+'.geojson'))
            self.assertTrue(isfile(filename))
            
            # check for "name" column
            gdf = gpd.read_file(filename)
            assert "name" in gdf.columns

    def test_snap_points_to_points(self):
        
        snapped_points = wntr.gis.snap(self.points, self.gis_data.junctions, tolerance=5.0)        
        # distance = np.sqrt(2)*2, 5, np.sqrt(2)*3
        expected = pd.DataFrame([{'node': '12', 'snap_distance': 2.23607, 'geometry': Point([50.0,70.0])},
                                 {'node': '23', 'snap_distance': 5.0,      'geometry': Point([70.0,40.0])},
                                 {'node': '21', 'snap_distance': 4.242641, 'geometry': Point([30.0,40.0])}])
        
        assert_frame_equal(pd.DataFrame(snapped_points), expected, check_dtype=False)
        

    def test_snap_points_to_lines(self):
        
        snapped_points = wntr.gis.snap(self.points, self.gis_data.pipes, tolerance=5.0)
        
        # distance = 1,5,3
        expected = pd.DataFrame([{'link': '12', 'node': '12', 'snap_distance': 1, 'line_position': 0.1, 'geometry': Point([52.0,70.0])},
                                 {'link': '113', 'node': '23', 'snap_distance': 5.0, 'line_position': 1.0, 'geometry': Point([70.0,40.0])},
                                 {'link': '121', 'node': '21', 'snap_distance': 3.0, 'line_position': 0.1, 'geometry': Point([30.0,37.0])}])
        
        assert_frame_equal(pd.DataFrame(snapped_points), expected, check_dtype=False)

@unittest.skipIf(not has_rasterio,
                 "Cannot test raster capabilities: rasterio is missing")
class TestRaster(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # use net1 junctions as example points
        inp_file = join(ex_datadir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        wn_gis = wn.to_gis(crs="EPSG:4326")
        points = pd.concat((wn_gis.junctions, wn_gis.tanks))
        self.points = points
        
        min_lon, min_lat, max_lon, max_lat = self.points.total_bounds

        resolution = 1.0
        
        # adjust to include boundary
        max_lon += resolution
        min_lat -= resolution
                
        lon_values = np.arange(min_lon, max_lon, resolution)
        lat_values = np.arange(max_lat, min_lat, -resolution)  # Decreasing order for latitudes
        raster_data = np.outer(lat_values,lon_values) # value is product of coordinate

        transform = rasterio.transform.from_origin(min_lon, max_lat, resolution, resolution)
        with rasterio.open(
            "test_raster.tif", "w", driver="GTiff", height=raster_data.shape[0], width=raster_data.shape[1], 
            count=1, dtype=raster_data.dtype, crs="EPSG:4326", transform=transform) as file:
            file.write(raster_data, 1) 
        
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_sample_raster(self):
        raster_values = wntr.gis.sample_raster(self.points, "test_raster.tif")
        assert (raster_values.index == self.points.index).all()
        
        # values should be product of coordinates
        expected_values = self.points.apply(lambda row: row.geometry.x * row.geometry.y, axis=1)
        assert np.isclose(raster_values.values, expected_values, atol=1e-5).all()


if __name__ == "__main__":
    unittest.main()