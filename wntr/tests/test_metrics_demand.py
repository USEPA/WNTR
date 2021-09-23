from __future__ import division

import unittest
from os.path import abspath, dirname, join

import pandas as pd
import wntr
from pandas.testing import assert_frame_equal, assert_series_equal

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
net3dir = join(testdir, "..", "..", "examples", "networks")


class TestMetricsDemand(unittest.TestCase):
    def test_expected_demand_net3_node101(self):
        inp_file = join(net3dir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        expected_demand = wntr.metrics.hydraulic.expected_demand(wn)
        ave_expected_demand = wntr.metrics.hydraulic.average_expected_demand(wn)

        ex_demand_101 = expected_demand["101"]
        ave_ex_demand_101 = ave_expected_demand["101"]

        expected = 0.012813608
        error = abs((ex_demand_101.mean() - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error

        error = abs((ave_ex_demand_101 - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error

    def test_expected_demand_category(self):
        inp_file = join(net3dir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        node = wn.get_node("123")
        node.demand_timeseries_list[0].category = "A"

        ave_expected_demand = wntr.metrics.hydraulic.average_expected_demand(wn)
        ave_expected_demand_A = wntr.metrics.hydraulic.average_expected_demand(
            wn, category="A"
        )

        error = abs(ave_expected_demand["123"] - ave_expected_demand_A["123"])
        self.assertLess(error, 1e-7)

        error = abs(
            ave_expected_demand_A.sum() - ave_expected_demand_A["123"]
        )  # all other entries are 0
        self.assertLess(error, 1e-7)

    def test_wsa(self):

        expected_demand = pd.DataFrame(
            data=[[12, 2], [3, 4], [5, 10]], columns=["A", "B"], index=[0, 1, 2]
        )
        demand = pd.DataFrame(
            data=[[5, 2], [3, 2], [3, 4]], columns=["A", "B"], index=[0, 1, 2]
        )

        # WSA at each junction and time
        wsa = wntr.metrics.hydraulic.water_service_availability(expected_demand, demand)
        expected = pd.DataFrame(
            data=[[5 / 12, 2 / 2], [3 / 3, 2 / 4], [3 / 5, 4 / 10]],
            columns=["A", "B"],
            index=[0, 1, 2],
        )
        assert_frame_equal(wsa, expected, check_dtype=False)

        # WSA at each junction
        wsa = wntr.metrics.hydraulic.water_service_availability(
            expected_demand.sum(axis=0), demand.sum(axis=0)
        )
        expected = pd.Series(
            data=[(5 + 3 + 3) / (12 + 3 + 5), (2 + 2 + 4) / (2 + 4 + 10)],
            index=["A", "B"],
        )
        assert_series_equal(wsa, expected, check_dtype=False)

        # WSA at each time
        wsa = wntr.metrics.hydraulic.water_service_availability(
            expected_demand.sum(axis=1), demand.sum(axis=1)
        )
        expected = pd.Series(
            data=[(5 + 2) / (12 + 2), (3 + 2) / (3 + 4), (3 + 4) / (5 + 10)],
            index=[0, 1, 2],
        )
        assert_series_equal(wsa, expected, check_dtype=False)

class TestTankCapacity(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        inp_file = join(net3dir, "Net3.inp")
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.duration = 2*24*3600 # 2 days
        sim = wntr.sim.WNTRSimulator(self.wn)
        self.results = sim.run_sim()
    
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_tank_capacity(self):
        
        pressure = self.results.node["pressure"].loc[:,self.wn.tank_name_list]
        tank_capacity = wntr.metrics.tank_capacity(pressure, self.wn)

        self.assertLess(tank_capacity.max().max(), 1)
        self.assertGreater(tank_capacity.min().min(), 0.4) # for this example, tanks capcity is > 0.4
    
    
if __name__ == "__main__":
    unittest.main()
