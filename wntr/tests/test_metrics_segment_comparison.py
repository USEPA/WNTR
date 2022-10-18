import unittest
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class CompareSegmentation(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        # wn_file = join(ex_datadir, "Net6.inp")
        wn_file = join(test_datadir, "CCWI17-HermanMahmoud.inp")
        self.wn = wntr.network.WaterNetworkModel(wn_file)
    
    @classmethod
    def tearDownClass(self):
        pass

    def test_compare_segmentations(self):
        #compare results from two segmentation algorithms
        G = self.wn.get_graph()
        #temporary valve layer, should pin a fixed layer at some point
        strategic_valve_layer = wntr.network.generate_valve_layer(
            self.wn, 'strategic', 2, seed = 123
            )

        (dev_node_segments, 
        dev_link_segments, 
        dev_segment_size) = wntr.metrics.valve_segments(
            G, strategic_valve_layer, alg = 'development'
            )

        (node_segments, 
        link_segments, 
        segment_size) = wntr.metrics.valve_segments(
            G, strategic_valve_layer, alg = 'original'
            )

        # basic length checks
        self.assertEqual(len(dev_node_segments), len(node_segments))
        self.assertEqual(len(dev_link_segments), len(link_segments))
        self.assertEqual(len(dev_segment_size), len(segment_size))

        # check node segments
        # WARNING this is not a proper test and is only
        # here for experimental purposes
        for link in link_segments.index:
            self.assertEqual(
                link_segments.loc[link],
                dev_link_segments.loc[link]
                )

        # check link segments
        # WARNING this is not a proper test and is only
        # here for experimental purposes
        for node in node_segments.index:
            self.assertEqual(
                node_segments.loc[link],
                dev_node_segments.loc[link]
                )

        # check segment sizes
        for k in range(len(segment_size)):
            self.assertTrue(
                (dev_segment_size.loc[k]==segment_size.loc[k]).all()
                )


if __name__ == "__main__":
    unittest.main()