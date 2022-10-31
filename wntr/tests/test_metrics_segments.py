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
        G = self.wn1.get_graph()

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
        G = self.wn2.get_graph()
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
            join(test_datadir, "node_segments_random.csv"), index_col=0
        ).squeeze()
        expected_link_segments = pd.read_csv(
            join(test_datadir, "link_segments_random.csv"), index_col=0
        ).squeeze()
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
        G = self.wn2.get_graph()
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
            join(test_datadir, "node_segments_strategic.csv"), index_col=0
        ).squeeze()
        expected_link_segments = pd.read_csv(
            join(test_datadir, "link_segments_strategic.csv"), index_col=0
        ).squeeze()
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

    def test_compare_segmentations(self):
        #compare results from two segmentation algorithms
        G = self.wn2.get_graph()
        
        strategic_valve_layer = wntr.network.generate_valve_layer(
            self.wn2, 'strategic', 1, seed = 123
            )

        (node_segments, 
        link_segments, 
        segment_size) = wntr.metrics.valve_segments(
            G, strategic_valve_layer, algorithm = 'cc'
            )

        (old_node_segments, 
        old_link_segments, 
        old_segment_size) = wntr.metrics.valve_segments(
            G, strategic_valve_layer, algorithm = 'matrix'
            )

        # basic length checks
        self.assertEqual(len(old_node_segments), len(node_segments))
        self.assertEqual(len(old_link_segments), len(link_segments))
        self.assertEqual(len(old_segment_size), len(segment_size))

        """
        Warning: the following test assumes that algorithms output 
        same labels for segment classes, which may not always be the case.
        If this test fails, consider looking into a comparison
        that checks if segment groups are the same, rather
        than exact labelling.
        """
        for link in link_segments.index:
            self.assertEqual(
                link_segments.loc[link],
                old_link_segments.loc[link]
                )

        """
        Warning: the following test assumes that algorithms output 
        same labels for segment classes, which may not always be the case.
        If this test fails, consider looking into a comparison
        that checks if segment groups are the same, rather
        than exact labelling.
        """
        for node in node_segments.index:
            self.assertEqual(
                node_segments.loc[node],
                old_node_segments.loc[node]
                )

        # check segment sizes
        for k in segment_size.index:
            self.assertTrue(
                (old_segment_size.loc[k]==segment_size.loc[k]).all()
                )


if __name__ == "__main__":
    unittest.main()
