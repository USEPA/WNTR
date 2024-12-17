import unittest
from os.path import abspath, dirname, join
import sys, platform

import wntr

if 'darwin' in sys.platform.lower() and 'arm' in platform.platform().lower():
    skip_v2_tests_on_arm = True
else:
    skip_v2_tests_on_arm = False

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
netdir = join(testdir, "..", "..", "examples", "networks")


class TestHealthImpactsMetric(unittest.TestCase):
    """
    Compare the following results to WST impact files using TSG file
    121          SETPOINT      100000          0                86400
    """

    def test_mass_consumed(self):
        inp_file = join(netdir, "Net3.inp")
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60

        wn.options.quality.parameter = "CHEMICAL"
        newpat = wntr.network.elements.Pattern.binary_pattern(
            "NewPattern",
            0,
            24 * 3600,
            wn.options.time.pattern_timestep,
            wn.options.time.duration,
        )
        wn.add_pattern(newpat.name, newpat)
        wn.add_source("Source1", "121", "SETPOINT", 100, "NewPattern")

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)

        demand = results.node["demand"].loc[:, wn.junction_name_list]
        quality = results.node["quality"].loc[:, wn.junction_name_list]

        MC = wntr.metrics.mass_contaminant_consumed(demand, quality)
        MC_timeseries = MC.sum(axis=1)
        MC_cumsum = MC_timeseries.cumsum()
        # MC_timeseries.to_csv('MC.txt')

        expected = float(39069900000 / 1000000)  # hour 2
        error = abs((MC_cumsum[2 * 3600] - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error

        expected = float(1509440000000 / 1000000)  # hour 12
        error = abs((MC_cumsum[12 * 3600] - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error

    def test_volume_consumed(self):
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        inp_file = join(netdir, "Net3.inp")

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60
        
        wn.options.quality.parameter = "CHEMICAL"
        newpat = wntr.network.elements.Pattern.binary_pattern(
            "NewPattern",
            0,
            24 * 3600,
            wn.options.time.pattern_timestep,
            wn.options.time.duration,
        )
        wn.add_pattern(newpat.name, newpat)
        wn.add_source("Source1", "121", "SETPOINT", 100, "NewPattern")

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)

        demand = results.node["demand"].loc[:, wn.junction_name_list]
        quality = results.node["quality"].loc[:, wn.junction_name_list]

        VC = wntr.metrics.volume_contaminant_consumed(demand, quality, 0)
        VC_timeseries = VC.sum(axis=1)
        VC_cumsum = VC_timeseries.cumsum()
        # VC_timeseries.to_csv('VC.txt')

        expected = float(156760 / 264.172)  # hour 2, convert gallons to m3
        error = abs((VC_cumsum[2 * 3600] - expected) / expected)
        self.assertLess(error, 0.02)  # 2% error

        expected = float(4867920 / 264.172)  # hour 12, convert gallons to m3
        error = abs((VC_cumsum[12 * 3600] - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error

    def test_extent_contaminated(self):
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        inp_file = join(netdir, "Net3.inp")

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60
        
        wn.options.quality.parameter = "CHEMICAL"
        newpat = wntr.network.elements.Pattern.binary_pattern(
            "NewPattern",
            0,
            24 * 3600,
            wn.options.time.pattern_timestep,
            wn.options.time.duration,
        )
        wn.add_pattern(newpat.name, newpat)
        wn.add_source("Source1", "121", "SETPOINT", 100, "NewPattern")

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)

        quality = results.node["quality"]
        flowrate = results.link["flowrate"].loc[:, wn.pipe_name_list]

        EC = wntr.metrics.extent_contaminant(quality, flowrate, wn, 0)

        expected = float(80749.9 * 0.3048)  # hour 2
        error = abs((EC[2 * 3600] - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error

        expected = float(135554 * 0.3048)  # hour 12
        error = abs((EC[12 * 3600] - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error


if __name__ == "__main__":
    unittest.main()
