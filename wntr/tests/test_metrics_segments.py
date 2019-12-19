import unittest
import numpy as np
import pandas as pd
from os.path import abspath, dirname, join

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, 'networks_for_testing')
ex_datadir = join(testdir,'..','..','examples','networks')
np.random.seed(321)

class TestSegmentation(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        
        import wntr
        self.wntr = wntr
        
        inp_file1 = join(test_datadir, 'CCWI17-HermanMahmoud.inp')
        self.wn1 = self.wntr.network.WaterNetworkModel(inp_file1)

        inp_file2 = join(test_datadir, 'Net3.inp')
        self.wn2 = self.wntr.network.WaterNetworkModel(inp_file2)
        self.wn2 = wntr.morph.skeletonize(self.wn2,40*0.0254)

    @classmethod
    def tearDownClass(self):
        pass

        
    def test_segmentation(self):
        
        import wntr
        
        self.wntr = wntr
        
        # test a small network
        G1 = self.wn1.get_graph()
        
        valves_1 = [['p1', 'n1'] # valve 0 is on link p1 and protects node n1
                  ,['p3', 'n2']
                  ,['p7', 'n5']
                  ,['p7', 'n6']
                  ,['p8', 'n6']
                  ]
        valves_1 = pd.DataFrame(valves_1, columns=['link', 'node']) 
        
        node_segments_1, link_segments_1, n_segments_1, seg_size_1 = wntr.metrics.topographic.valve_segments(G1, valves_1, output_flag = True)
        
        self.assertEqual(seg_size_1, 11)
        self.assertEqual(n_segments_1, 4)
        
        # test a skeletonized version of Net3
        G2 = self.wn2.get_graph()
        
        valves_2 = []
        for pipe_name in np.random.choice(self.wn2.pipe_name_list, 300):
            pipe = self.wn2.get_link(pipe_name)
            valves_2.append([pipe_name, pipe.start_node_name])
        
        valves_2 = pd.DataFrame(valves_2, columns=['link', 'node']) 
        
        node_segments_2, link_segments_2, n_segments_2, seg_size_2 = wntr.metrics.topographic.valve_segments(G2, valves_2, output_flag = True)
        node_segments_2P, link_segments_2P, n_segments_2P, seg_size_2P = wntr.metrics.topographic.valve_segments(G2, valves_2, pandas_flag = True, output_flag = True)
        
        self.assertListEqual(node_segments_2.tolist(), node_segments_2P.tolist())
        self.assertListEqual(link_segments_2.tolist(), link_segments_2P.tolist())
        self.assertEqual(seg_size_2, 5)
        self.assertEqual(n_segments_2, 45)   
        self.assertEqual(node_segments_2[-1], 45)
        self.assertEqual(link_segments_2[-1], 41)
        
if __name__ == '__main__':
    unittest.main()