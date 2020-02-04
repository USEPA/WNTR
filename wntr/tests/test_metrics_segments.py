import unittest
import numpy as np
import pandas as pd
from os.path import abspath, dirname, join
from pandas.util.testing import assert_frame_equal, assert_series_equal
import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, 'networks_for_testing')
ex_datadir = join(testdir,'..','..','examples','networks')


class TestSegmentation(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        
        inp_file1 = join(test_datadir, 'CCWI17-HermanMahmoud.inp')
        self.wn1 = wntr.network.WaterNetworkModel(inp_file1)

        inp_file2 = join(ex_datadir, 'Net3.inp')
        self.wn2 = wntr.network.WaterNetworkModel(inp_file2)

    @classmethod
    def tearDownClass(self):
        pass

        
    def test_segmentation_1(self):
        # test a small network
        G = self.wn1.get_graph()
        
        valves = [['p1', 'n1'] # valve 0 is on link p1 and protects node n1
                  ,['p3', 'n2']
                  ,['p7', 'n5']
                  ,['p7', 'n6']
                  ,['p8', 'n6']
                  ]
        valves = pd.DataFrame(valves, columns=['link', 'node']) 
        
        node_segments, link_segments, seg_size = wntr.metrics.topographic.valve_segments(G, valves)
        
        max_seg_size = seg_size.sum(axis=1).max()
        self.assertEqual(max_seg_size, 11)
        self.assertEqual(seg_size.shape[0], 4)
        
    def test_segmentation_2(self):
        # test Net3
        G = self.wn2.get_graph()

        valves = wntr.network.generate_valve_layer(self.wn2, 'random', 50, 321)
        
        wntr.graphics.plot_network(self.wn2, node_size=4, valve_layer=valves)
        
        node_segments, link_segments, seg_size = wntr.metrics.topographic.valve_segments(G, valves)
        node_segments_P, link_segments_P, seg_size_P = wntr.metrics.topographic.valve_segments(G, valves, use_numpy=False)
        
        Net3_valves_answer = pd.read_excel("Net3_test_valves.xlsx", index_col=0, dtype=object)
        
        assert_frame_equal(valves, Net3_valves_answer)
        assert_series_equal(node_segments, node_segments_P)
        assert_series_equal(link_segments, link_segments_P)
        assert_frame_equal(seg_size, seg_size_P)
        self.assertEqual(seg_size.shape[0], 20)
        
if __name__ == '__main__':
    unittest.main()