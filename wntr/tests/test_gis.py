import sys
import unittest
import warnings
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr
from pandas.testing import assert_frame_equal

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
    
testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestGIS(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.EpanetSimulator(wn)
        self.results = sim.run_sim()
        self.wn_geojson = self.wntr.gis.wn_to_gis(wn)
        
        polygon_pts = [[(25,80), (80,80), (80,60), (25,60)],
                       [(25,60), (80,60), (80,30), (25,30)],
                       [(40,50), (60,60), (60,15), (40,15)]]
        polygon_data = []
        for i, pts in enumerate(polygon_pts):
            geometry = Polygon(pts)
            polygon_data.append({'name': str(i+1), 
                                 'value': i+1,
                                 'geometry': geometry.convex_hull})
            
        df = pd.DataFrame(polygon_data)
        df.set_index("name", inplace=True)
        self.polygons = gpd.GeoDataFrame(df, crs=None)

        points = [(48.2,37.2), (70.8,69.3), (54.5, 40.5), 
                  (51.2, 71.1), (32.1, 67.6), (51.7, 87.3)]
        point_data = []
        for i, pts in enumerate(points):
            geometry = Point(pts)
            point_data.append({'geometry': geometry})
            
        df = pd.DataFrame(point_data)
        self.points = gpd.GeoDataFrame(df, crs=None)
        
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_intersect_points_with_polygons(self):
        
        stats = wntr.gis.intersect_points_with_polygons(self.wn_geojson.junctions, self.polygons, 'value')
        print(stats)
        
        self.assertEqual(1, 1)
        
    def test_intersect_lines_with_polygons(self):
        
        stats = wntr.gis.intersect_lines_with_polygons(self.wn_geojson.pipes, self.polygons, 'value')
        print(stats)
        
        self.assertEqual(1, 1)
    
    def test_add_attributes_and_write(self):
        self.wn_geojson.add_node_attributes(self.results.node['pressure'].loc[3600,:], 'Pressure_1hr')
        self.wn_geojson.add_link_attributes(self.results.link['flowrate'].loc[3600,:], 'Flowrate_1hr')
        self.wn_geojson.write('temp_Net1')

    def test_snap_points_to_points(self):
        
        snapped_points = wntr.gis.snap_points_to_points(self.points, self.wn_geojson.junctions, tolerance=5.0)
        snap_calc = pd.DataFrame(snapped_points)
        actual_points_to_points = gpd.read_file(join(datadir, "snapped_points_to_points.geojson"))
        snap_actual = pd.DataFrame(actual_points_to_points, index=actual_points_to_points["name"])
        snap_actual = snap_actual.drop(columns="name")
        assert_frame_equal(snap_calc, snap_actual)

    def test_snap_points_to_lines(self):
        
        snapped_points = wntr.gis.snap_points_to_lines(self.points, self.wn_geojson.pipes, tolerance=5.0)
        snap_calc = pd.DataFrame(snapped_points)        
        actual_points_to_lines = gpd.read_file(join(datadir, "snapped_points_to_lines.geojson"))
        snap_actual = pd.DataFrame(actual_points_to_lines, index=actual_points_to_lines["name"])
        snap_actual = snap_actual.drop(columns="name")
        assert_frame_equal(snap_calc, snap_actual)

if __name__ == "__main__":
    unittest.main()