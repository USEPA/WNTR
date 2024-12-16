import unittest
from os.path import abspath, dirname, join
import sys, platform
import wntr

if 'darwin' in sys.platform.lower() and 'arm' in platform.platform().lower():
    skip_v2_tests_on_arm = True
else:
    skip_v2_tests_on_arm = False

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "..", "..", "examples", "networks")

"""
Compare results to EPANET GUI using Net3 and Source Quality at
121          SETPOINT      100000  mg/L
121          FLOWPACED     100000  mg/L
121          MASS          6000000000  mg/min
River        CONCEN        100000   mg/L
"""


class TestWaterQualitySimulations(unittest.TestCase):
    def test_setpoint_waterquality_simulation(self):
        inp_file = join(datadir, "Net3.inp")
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60
        
        wn.options.quality.parameter = "CHEMICAL"
        wn.add_pattern(
            "NewPattern", [1]
        )  # start_time=0, end_time=wn.options.time.duration)
        wn.add_source("Source1", "121", "SETPOINT", 100, "NewPattern")
        # WQ = wntr.scenario.Waterquality('CHEM', ['121'], 'SETPOINT', 100, 0, -1)

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)

        expected = 91661.72 * (1e-6 / 0.001)  # Node '159' at hour 6
        # print(results.node)
        error = abs(
            (results.node["quality"].loc[6 * 3600, "159"] - expected) / expected
        )
        self.assertLess(error, 0.0001)  # 0.01% error

    def test_flowpaced_waterquality_simulation(self):
        inp_file = join(datadir, "Net3.inp")
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60
        
        wn.options.quality.parameter = "CHEMICAL"
        wn.add_pattern(
            "NewPattern", [1]
        )  # start_time=0, end_time=wn.options.time.duration)
        wn.add_source("Source1", "121", "FLOWPACED", 100, "NewPattern")
        # WQ = wntr.scenario.Waterquality('CHEM', ['121'], 'FLOWPACED', 100, 0, -1)

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)

        expected = 92246.55 * (1e-6 / 0.001)  # Node '159' at hour 6
        error = abs(
            (results.node["quality"].loc[6 * 3600, "159"] - expected) / expected
        )
        self.assertLess(error, 0.0001)  # 0.01% error

    def test_mass_waterquality_simulation(self):
        inp_file = join(datadir, "Net3.inp")
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60
        
        wn.options.quality.parameter = "CHEMICAL"
        wn.add_pattern(
            "NewPattern", [1.0]
        )  # start_time=0, end_time=wn.options.time.duration)
        wn.add_source("Source1", "121", "MASS", 100, "NewPattern")
        # WQ = wntr.scenario.Waterquality('CHEM', ['121'], 'MASS', 100, 0, -1)

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)

        expected = 217903.60 * (1e-6 / 0.001)  # Node '159' at hour 6
        error = abs(
            (results.node["quality"].loc[6 * 3600, "159"] - expected) / expected
        )
        self.assertLess(error, 0.0001)  # 0.01% error

    def test_conc_waterquality_simulation(self):
        inp_file = join(datadir, "Net3.inp")
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60
        
        wn.options.quality.parameter = "CHEMICAL"
        wn.add_pattern(
            "NewPattern", [1.0]
        )  # start_time=0, end_time=wn.options.time.duration)
        wn.add_source("Source1", "River", "CONCEN", 100, "NewPattern")
        # WQ = wntr.scenario.Waterquality('CHEM', ['River'], 'CONCEN', 100, 0, -1)

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)

        expected = 91661.72 * (1e-6 / 0.001)  # Node '159' at hour 6
        error = abs(
            (results.node["quality"].loc[6 * 3600, "159"] - expected) / expected
        )
        self.assertLess(error, 0.0001)  # 0.01% error

    def test_age_waterquality_simulation(self):

        inp_file = join(datadir, "Net3.inp")
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60
        
        wn.options.quality.parameter = "AGE"
        # WQ = wntr.scenario.Waterquality('AGE')

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)

        # WARNING: This does NOT match the EPANET Windows results - it does match
        # the epanet linux binary
        expected = 3.652 * 3600  # Node '159' at hour 6
        error = abs(
            (results.node["quality"].loc[6 * 3600, "159"] - expected) / expected
        )
        # print([expected, results.node['quality'].loc[6*3600, '159']])
        self.assertLess(error, 0.001)  # 0.01% error

    def test_trace_waterquality_simulation(self):
        inp_file = join(datadir, "Net3.inp")
        if skip_v2_tests_on_arm: self.skipTest('skipped test due to skip_tests_flag')

        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 15*60
        wn.options.time.quality_timestep = 15*60
        wn.options.time.report_timestep = 15*60
        
        wn.options.quality.parameter = "TRACE"
        wn.options.quality.trace_node = "121"
        # WQ = wntr.scenario.Waterquality('TRACE', ['121'])

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim(version=2.0)
        # print(results.node.keys())
        expected = 91.66  # Node '159' at hour 6
        error = abs(
            float(results.node["quality"].loc[6 * 3600, "159"] - expected)
            / float(expected)
        )
        self.assertLess(error, 0.0001)  # 0.01% error


if __name__ == "__main__":
    unittest.main()

