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
    
testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestGIS(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net1.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()
        self.wn_geojson = self.wntr.gis.wn_to_gis(self.wn)
        
        polygon_pts = [[(25,80), (80,80), (80,60), (25,60)],
                       [(25,60), (80,60), (80,30), (25,30)],
                       [(40,50), (60,60), (60,15), (40,15)]]
        polygon_data = []
        for i, pts in enumerate(polygon_pts):
            geometry = Polygon(pts)
            polygon_data.append({'name': str(i+1), 
                                 'value': (i+1)*10,
                                 'geometry': geometry.convex_hull})
            
        df = pd.DataFrame(polygon_data)
        df.set_index("name", inplace=True)
        self.polygons = gpd.GeoDataFrame(df, crs=None)

        points = [(52,72), (75,40), (27,37)]
        point_data = []
        for i, pts in enumerate(points):
            geometry = Point(pts)
            point_data.append({'geometry': geometry})
            
        df = pd.DataFrame(point_data)
        self.points = gpd.GeoDataFrame(df, crs=None)
        
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_wn_to_gis(self):
        self.wn_geojson
        
        self.assertEqual(1, 1)
        
    def test_gis_to_wn(self):
        
        wn2 = wntr.gis.gis_to_wn(self.wn_geojson)
        G1 = self.wn.get_graph()
        G2 = wn2.get_graph()
        
        assert nx.is_isomorphic(G1, G2)
                         
    def test_intersect_points_with_polygons(self):
        
        stats = wntr.gis.intersect(self.wn_geojson.junctions, self.polygons, 'value')
        print(stats)
        
        # Junction 22 intersects poly2 val=20, intersects poly3 val=30
        # weighted average = (1*20+0.5*30)/2 = 17.5
        expected = pd.Series({'intersections': ['2','3'], 'values': [20,30]})
        expected['n'] = len(expected['values'])
        expected['sum'] = float(sum(expected['values']))
        expected['min'] = float(min(expected['values']))
        expected['max'] = float(max(expected['values']))
        expected['average'] = expected['sum']/expected['n']
        expected = expected.reindex(stats.columns)
        
        assert_series_equal(stats.loc['22',:], expected, check_dtype=False, check_names=False)
        
        # Junction 31: no intersections
        expected = pd.Series({'n': 0, 'sum': np.nan, 'min': np.nan, 'max': np.nan,
                              'average': np.nan, 'intersections': [], 'values': []})
        
        assert_series_equal(stats.loc['31',:], expected, check_dtype=False, check_names=False)
        
    def test_intersect_lines_with_polygons(self):
        
        stats = wntr.gis.intersect(self.wn_geojson.pipes, self.polygons, 'value')
        
        #ax = self.polygons.plot(column='value', alpha=0.5)
        #ax = wntr.graphics.plot_network(self.wn, ax=ax)
        
        # Pipe 22 intersects poly2 100%, val=20, intersects poly3 50%, val=30
        # weighted average = (1*20+0.5*30)/2 = 17.5
        expected = pd.Series({'intersections': ['3','2'], 'values': [30,20], 'weighted_average': 17.5})
        expected['n'] = len(expected['values'])
        expected['sum'] = float(sum(expected['values']))
        expected['min'] = float(min(expected['values']))
        expected['max'] = float(max(expected['values']))
        expected['average'] = expected['sum']/expected['n']
        expected = expected.reindex(stats.columns)
        
        assert_series_equal(stats.loc['22',:], expected, check_dtype=False, check_names=False)
        
        # Pipe 31: no intersections
        expected = pd.Series({'n': 0, 'sum': np.nan, 'min': np.nan, 'max': np.nan,
                              'average': np.nan, 'intersections': [], 'values': [], 
                              'weighted_average': np.nan})
        
        assert_series_equal(stats.loc['31',:], expected, check_dtype=False, check_names=False)

    def test_add_attributes_and_write(self):
        self.wn_geojson.add_node_attributes(self.results.node['pressure'].loc[3600,:], 'Pressure_1hr')
        self.wn_geojson.add_link_attributes(self.results.link['flowrate'].loc[3600,:], 'Flowrate_1hr')
        assert 'Pressure_1hr' in self.wn_geojson.junctions.columns
        assert 'Pressure_1hr' in self.wn_geojson.tanks.columns
        assert 'Pressure_1hr' in self.wn_geojson.reservoirs.columns
        assert 'Flowrate_1hr' in self.wn_geojson.pipes.columns
        assert 'Flowrate_1hr' in self.wn_geojson.pumps.columns
        assert 'Flowrate_1hr' not in self.wn_geojson.valves.columns # Net1 has no valves
    
    def test_write(self):
        prefix = 'temp_Net1'
        components = ['junctions', 'tanks', 'reservoirs', 'pipes', 'pumps', 'valves']
        for component in components:
            filename = abspath(join(testdir, prefix+'_'+component+'.geojson'))
            if isfile(filename):
                os.remove(filename)
            
        self.wn_geojson.write(prefix)

        for component in components:
            if component == 'valves':
                continue # Net1 has no valves
            filename = abspath(join(testdir, prefix+'_'+component+'.geojson'))
            self.assertTrue(isfile(filename))

    def test_snap_points_to_points(self):
        
        snapped_points = wntr.gis.snap_points_to_points(self.points, self.wn_geojson.junctions, tolerance=5.0)
        
        # distance = np.sqrt(2)*2, 5, np.sqrt(2)*3
        expected = pd.DataFrame([{'node': '12', 'snap_distance': 2.828427, 'geometry': Point([50.0,70.0])},
                                 {'node': '23', 'snap_distance': 5.0,      'geometry': Point([70.0,40.0])},
                                 {'node': '21', 'snap_distance': 4.242641, 'geometry': Point([30.0,40.0])}])
        
        assert_frame_equal(pd.DataFrame(snapped_points), expected, check_dtype=False)
        

    def test_snap_points_to_lines(self):
        
        snapped_points = wntr.gis.snap_points_to_lines(self.points, self.wn_geojson.pipes, tolerance=5.0)
        
        # distance = 2,5,3
        expected = pd.DataFrame([{'link': '110', 'node': '12', 'snap_distance': 2.0, 'distance_along_line': 0.9, 'geometry': Point([50.0,72.0])},
                                 {'link':  '22', 'node': '23', 'snap_distance': 5.0, 'distance_along_line': 1.0, 'geometry': Point([70.0,40.0])},
                                 {'link': '121', 'node': '21', 'snap_distance': 3.0, 'distance_along_line': 0.1, 'geometry': Point([30.0,37.0])}])
        
        assert_frame_equal(pd.DataFrame(snapped_points), expected, check_dtype=False)

if __name__ == "__main__":
    unittest.main()