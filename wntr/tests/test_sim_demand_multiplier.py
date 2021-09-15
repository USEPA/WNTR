import unittest
import warnings
from os.path import abspath, dirname, join

import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

class TestPatternStart(unittest.TestCase):

    def test_pattern_start(self):

        inp_file = join(ex_datadir, "Net1.inp")

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.pattern_start = 0

        sim = wntr.sim.EpanetSimulator(wn)
        epa_demand_0 = sim.run_sim().node['demand'].loc[:,wn.junction_name_list]

        sim = wntr.sim.WNTRSimulator(wn)
        wntr_demand_0 = sim.run_sim().node['demand'].loc[:,wn.junction_name_list]

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.pattern_start = 3*3600

        sim = wntr.sim.EpanetSimulator(wn)
        epa_demand_3 = sim.run_sim().node['demand'].loc[:,wn.junction_name_list]

        sim = wntr.sim.WNTRSimulator(wn)
        wntr_demand_3 = sim.run_sim().node['demand'].loc[:,wn.junction_name_list]

        diff_demand_0 = abs(epa_demand_0 - wntr_demand_0).sum().sum()
        self.assertLess(diff_demand_0, 1e-5)

        diff_demand_3 = abs(epa_demand_3 - wntr_demand_3).sum().sum()
        self.assertLess(diff_demand_3, 1e-5)

        epa_demand_3.index = epa_demand_3.index + 3*3600
        diff_epa_shifted = abs(epa_demand_0 - epa_demand_3).sum().sum()
        self.assertLess(diff_epa_shifted, 1e-5)

        wntr_demand_3.index = wntr_demand_3.index + 3*3600
        diff_wntr_shifted = abs(wntr_demand_0 - wntr_demand_3).sum().sum()
        self.assertLess(diff_wntr_shifted, 1e-5)

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
