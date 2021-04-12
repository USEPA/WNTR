import unittest
import warnings
from os.path import abspath, dirname, join

import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")



class TestDemandMultiplier(unittest.TestCase):
    def test_demand_multiplier(self):

        node_name = "147"
        time = 3600

        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        node = wn.get_node(node_name)

        # Demand multiplier = 1
        wn.options.hydraulic.demand_multiplier = 1
        sim = wntr.sim.EpanetSimulator(wn)
        epanet_results1 = sim.run_sim()
        sim = wntr.sim.WNTRSimulator(wn)
        wntr_results1 = sim.run_sim()

        expected_demand1 = node.demand_timeseries_list.at(time)
        epanet_actual_demand1 = epanet_results1.node["demand"].loc[time, node_name]
        wntr_actual_demand1 = wntr_results1.node["demand"].loc[time, node_name]

        self.assertGreater(
            expected_demand1, 0
        )  # make sure expected demand is greater than 0

        self.assertAlmostEqual(expected_demand1, epanet_actual_demand1, 8)
        self.assertAlmostEqual(expected_demand1, wntr_actual_demand1, 8)
        self.assertAlmostEqual(epanet_actual_demand1, wntr_actual_demand1, 8)

        # Increase demand multiplier to 1.5
        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.hydraulic.demand_multiplier = 1.5
        sim = wntr.sim.EpanetSimulator(wn)
        epanet_results2 = sim.run_sim()
        sim = wntr.sim.WNTRSimulator(wn)
        wntr_results2 = sim.run_sim()

        expected_demand2 = node.demand_timeseries_list.at(time, multiplier=1.5)
        epanet_actual_demand2 = epanet_results2.node["demand"].loc[time, node_name]
        wntr_actual_demand2 = wntr_results2.node["demand"].loc[time, node_name]

        self.assertAlmostEqual(expected_demand1 * 1.5, epanet_actual_demand2, 8)

        self.assertAlmostEqual(expected_demand2, epanet_actual_demand2, 8)
        self.assertAlmostEqual(expected_demand2, wntr_actual_demand2, 8)
        self.assertAlmostEqual(epanet_actual_demand2, wntr_actual_demand2, 8)

        # Decrease demand multiplier to 0.5
        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.hydraulic.demand_multiplier = 0.5
        sim = wntr.sim.EpanetSimulator(wn)
        epanet_results2 = sim.run_sim()
        sim = wntr.sim.WNTRSimulator(wn)
        wntr_results2 = sim.run_sim()

        expected_demand2 = node.demand_timeseries_list.at(time, multiplier=0.5)
        epanet_actual_demand2 = epanet_results2.node["demand"].loc[time, node_name]
        wntr_actual_demand2 = wntr_results2.node["demand"].loc[time, node_name]

        self.assertAlmostEqual(expected_demand1 * 0.5, epanet_actual_demand2, 8)

        self.assertAlmostEqual(expected_demand2, epanet_actual_demand2, 8)
        self.assertAlmostEqual(expected_demand2, wntr_actual_demand2, 8)
        self.assertAlmostEqual(epanet_actual_demand2, wntr_actual_demand2, 8)


if __name__ == "__main__":
    unittest.main()
