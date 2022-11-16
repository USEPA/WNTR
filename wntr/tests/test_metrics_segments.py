import unittest
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestSegmentation(unittest.TestCase):
    @classmethod
    def setUpClass(self):

        inp_file1 = join(test_datadir, "CCWI17-HermanMahmoud.inp")
        self.wn1 = wntr.network.WaterNetworkModel(inp_file1)

        inp_file2 = join(ex_datadir, "Net3.inp")
        self.wn2 = wntr.network.WaterNetworkModel(inp_file2)

    @classmethod
    def tearDownClass(self):
        pass

    def test_segmentation_small(self):
        # test a small network
        G = self.wn1.to_graph()

        valves = [
            ["p1", "n1"],  # valve 0 is on link p1 and protects node n1
            ["p3", "n2"],
            ["p7", "n5"],
            ["p7", "n6"],
            ["p8", "n6"],
        ]
        valves = pd.DataFrame(valves, columns=["link", "node"])

        (
            node_segments,
            link_segments,
            seg_size,
        ) = wntr.metrics.topographic.valve_segments(G, valves)

        max_seg_size = seg_size.sum(axis=1).max()
        self.assertEqual(max_seg_size, 11)
        self.assertEqual(seg_size.shape[0], 4)

    def test_segmentation_random(self):
        # test Net3
        G = self.wn2.to_graph()
        valves = pd.read_csv(
            join(test_datadir, "valve_layer_random.csv"), index_col=0, dtype="object"
        )

        (
            node_segments,
            link_segments,
            seg_size,
        ) = wntr.metrics.topographic.valve_segments(G, valves)
        max_seg_size = seg_size.sum(axis=1).max()
        num_segments = seg_size.shape[0]

        #        node_segments.to_csv('node_segments_random.csv')
        #        link_segments.to_csv('link_segments_random.csv')

        expected_node_segments = pd.read_csv(
            join(test_datadir, "node_segments_random.csv"), index_col=0, squeeze=True
        )
        expected_link_segments = pd.read_csv(
            join(test_datadir, "link_segments_random.csv"), index_col=0, squeeze=True
        )
        expected_node_segments.astype("int32")
        expected_link_segments.astype("int32")

        #        import matplotlib
        #        cmap = matplotlib.colors.ListedColormap(np.random.rand(num_segments,3))
        #        wntr.graphics.plot_network(self.wn2, node_segments, link_segments, valve_layer=valves,
        #                                   node_cmap=cmap, link_cmap=cmap,
        #                                   node_range=[0.5,num_segments+0.5],
        #                                   link_range=[0.5,num_segments+0.5])

        self.assertListEqual(list(node_segments), list(expected_node_segments))
        self.assertListEqual(list(link_segments), list(expected_link_segments))

        self.assertEqual(max_seg_size, 112)
        self.assertEqual(num_segments, 15)

    def test_segmentation_strategic(self):
        # test Net3
        G = self.wn2.to_graph()
        valves = pd.read_csv(
            join(test_datadir, "valve_layer_stategic_1.csv"),
            index_col=0,
            dtype="object",
        )

        (
            node_segments,
            link_segments,
            seg_size,
        ) = wntr.metrics.topographic.valve_segments(G, valves)
        max_seg_size = seg_size.sum(axis=1).max()
        num_segments = seg_size.shape[0]

        #        node_segments.to_csv('node_segments_strategic.csv')
        #        link_segments.to_csv('link_segments_strategic.csv')

        expected_node_segments = pd.read_csv(
            join(test_datadir, "node_segments_strategic.csv"), index_col=0, squeeze=True
        )
        expected_link_segments = pd.read_csv(
            join(test_datadir, "link_segments_strategic.csv"), index_col=0, squeeze=True
        )
        expected_node_segments.astype("int32")
        expected_link_segments.astype("int32")

        #        import matplotlib
        #        cmap = matplotlib.colors.ListedColormap(np.random.rand(num_segments,3))
        #        wntr.graphics.plot_network(self.wn2, node_segments, link_segments, valve_layer=valves,
        #                                   node_cmap=cmap, link_cmap=cmap,
        #                                   node_range=[0.5,num_segments+0.5],
        #                                   link_range=[0.5,num_segments+0.5])

        self.assertListEqual(list(node_segments), list(expected_node_segments))
        self.assertListEqual(list(link_segments), list(expected_link_segments))

        self.assertEqual(max_seg_size, 3)
        self.assertEqual(num_segments, 119)


if __name__ == "__main__":
    unittest.main()
