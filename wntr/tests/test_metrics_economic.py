import unittest
from os.path import abspath, dirname, join

import pandas as pd
import wntr
from pandas.testing import assert_frame_equal, assert_series_equal

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
netdir = join(testdir, "..", "..", "examples", "networks")


class TestEconomicMetrics(unittest.TestCase):
    def test_annual_network_cost1(self):
        inp_file = join(netdir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        cost = wntr.metrics.annual_network_cost(wn)
        self.assertAlmostEqual(cost, 460147, 0)

    def test_annual_network_cost2(self):
        # Network cost using a tank volume curve
        inp_file = join(datadir, "Anytown_multipointcurves.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        cost = wntr.metrics.annual_network_cost(wn)
        self.assertAlmostEqual(cost, 1201467.78, 0)

    def test_annual_ghg_emissions(self):
        inp_file = join(netdir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        cost = wntr.metrics.annual_ghg_emissions(wn)
        self.assertAlmostEqual(cost, 410278, 0)


if __name__ == "__main__":
    unittest.main()
