import unittest
from os.path import abspath, dirname, join

import pandas as pd
import wntr
from pandas.testing import assert_frame_equal, assert_series_equal

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestSegmentation(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        inp_file = join(ex_datadir, "Net3.inp")
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        G = self.wn.to_graph()
        self.valves = pd.read_csv(
            join(test_datadir, "valve_layer_stategic_1.csv"),
            index_col=0,
            dtype="object",
        )
        (
            self.node_segments,
            self.link_segments,
            self.seg_size,
        ) = wntr.metrics.topographic.valve_segments(G, self.valves)

        # import matplotlib
        # cmap = matplotlib.colors.ListedColormap(np.random.rand(num_segments,3))
        # wntr.graphics.plot_network(self.wn2, node_segments, link_segments, valve_layer=valves,
        #                            node_cmap=cmap, link_cmap=cmap,
        #                            node_range=[0.5,num_segments+0.5],
        #                            link_range=[0.5,num_segments+0.5])

    @classmethod
    def tearDownClass(self):
        pass

    def test_valve_criticality_length(self):

        # Gather the link lengths for the length-based criticality calculation
        link_lengths = self.wn.query_link_attribute("length")

        # Calculate the length-based valve criticality for each valve
        valve_crit = wntr.metrics.topographic._valve_criticality_length(
            link_lengths, self.valves, self.node_segments, self.link_segments
        )

        # valve_crit.to_csv('valve_crit_length.csv')
        # filename = 'valve_crit_length.jpg'
        # wntr.graphics.plot_network(self.wn, valve_layer=self.valves,
        #                            valve_criticality=valve_crit,
        #                            node_size=10, filename=filename)

        expected_valve_crit = pd.read_csv(
            join(test_datadir, "valve_crit_length.csv"), index_col=[0], squeeze=True
        )

        assert_series_equal(
            valve_crit, expected_valve_crit, check_dtype=False, check_names=False
        )

    def test_valve_criticality_demand(self):

        # Gather the node demands for the demand-based criticality calculation
        node_demands = wntr.metrics.average_expected_demand(self.wn)

        # Calculate the demand-based valve criticality for each valve
        valve_crit = wntr.metrics.topographic._valve_criticality_demand(
            node_demands, self.valves, self.node_segments, self.link_segments
        )

        # valve_crit.to_csv('valve_crit_demand.csv')
        # filename = 'valve_crit_demand.jpg'
        # wntr.graphics.plot_network(self.wn, valve_layer=self.valves,
        #                            valve_criticality=valve_crit,
        #                            node_size=10, filename=filename)

        expected_valve_crit = pd.read_csv(
            join(test_datadir, "valve_crit_demand.csv"), index_col=[0], squeeze=True
        )

        assert_series_equal(
            valve_crit, expected_valve_crit, check_dtype=False, check_names=False
        )

    def test_valve_criticality(self):

        # Calculate the valve-based valve criticality for each valve
        valve_crit = wntr.metrics.topographic._valve_criticality(
            self.valves, self.node_segments, self.link_segments
        )

        # valve_crit.to_csv('valve_crit_valve.csv')
        # filename = 'valve_crit_valve.jpg'
        # wntr.graphics.plot_network(self.wn, valve_layer=self.valves,
        #                            valve_criticality=valve_crit,
        #                            node_size=10, filename=filename)

        expected_valve_crit = pd.read_csv(
            join(test_datadir, "valve_crit_valve.csv"), index_col=[0], squeeze=True
        )

        assert_series_equal(
            valve_crit, expected_valve_crit, check_dtype=False, check_names=False
        )


if __name__ == "__main__":
    unittest.main()

