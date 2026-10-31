import sys
import unittest
import pytest
from os.path import join
from concurrent.futures import ThreadPoolExecutor
import numpy as np

import pandas

pandas.set_option("display.max_rows", 10000)

from _test_paths import (
    NETWORKS_FOR_TESTING_DIR as test_datadir,
    EXAMPLES_NETWORKS_DIR as ex_datadir,
)


def compare_results(wntr_res, epa_res, abs_threshold, rel_threshold):
    abs_diff = abs(wntr_res - epa_res)
    rel_diff = abs_diff / abs(epa_res)
    abs_diffa = abs_diff.mean()
    rel_diffa = rel_diff.mean()
    abs_diffb = abs_diff.mean(axis=1)
    rel_diffb = rel_diff.mean(axis=1)
    diffa = (abs_diffa < abs_threshold) | (rel_diffa < rel_threshold)
    diffb = (abs_diffb < abs_threshold) | (rel_diffb < rel_threshold)
    return diffa.all() and diffb.all()


class TestPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_Anytown_multipointcurves_performance(self):
        head_diff_abs_threshold = 1e-3
        demand_diff_abs_threshold = 1e-5
        flow_diff_abs_threshold = 1e-5
        rel_threshold = 1e-3

        inp_file = join(test_datadir, "Anytown_multipointcurves.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn2 = self.wntr.network.WaterNetworkModel(inp_file)

        # Apply a curve that is very fine along H = a - b * Q ** c and
        # verify the answers are nearly identical under these conditions.
        A = 1.313e3
        B = 8.705e-6
        C = 1.796e0
        new_curve_name = "perfect_curve"
        cdata = [(10 * q, A - B * (10 * q) ** C) for q in range(1200)]
        wn.add_curve(new_curve_name, "HEAD", cdata)
        wn2.add_curve(new_curve_name, "HEAD", cdata)
        for pump_name, pump in wn.pumps():
            pump.pump_curve_name = new_curve_name
        for pump_name, pump in wn2.pumps():
            pump.pump_curve_name = new_curve_name
        
        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        sim = self.wntr.sim.WNTRSimulator(wn2)
        results = sim.run_sim()

        self.assertTrue(
            compare_results(
                results.node["head"],
                epa_res.node["head"],
                head_diff_abs_threshold,
                rel_threshold,
            )
        )
        self.assertTrue(
            compare_results(
                results.node["demand"].loc[:, wn.tank_name_list],
                epa_res.node["demand"].loc[:, wn.tank_name_list],
                demand_diff_abs_threshold,
                rel_threshold,
            )
        )
        self.assertTrue(
            compare_results(
                results.link["flowrate"],
                epa_res.link["flowrate"],
                flow_diff_abs_threshold,
                rel_threshold,
            )
        )

    def test_Net1_float64(self):
        """Only needs to test that runs successfully with float64 time options"""
        inp_file = join(ex_datadir, "Net1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        
        wn.options.time.duration = np.float64(wn.options.time.duration)
        wn.options.time.hydraulic_timestep = np.float64(wn.options.time.hydraulic_timestep)
        wn.options.time.quality_timestep = np.float64(wn.options.time.quality_timestep)
        wn.options.time.rule_timestep = np.float64(wn.options.time.rule_timestep)
        wn.options.time.pattern_timestep = np.float64(wn.options.time.pattern_timestep)
        wn.options.time.pattern_start = np.float64(wn.options.time.pattern_start)
        wn.options.time.report_timestep = np.float64(wn.options.time.report_timestep)
        wn.options.time.report_start = np.float64(wn.options.time.report_start)
        wn.options.time.start_clocktime = np.float64(wn.options.time.start_clocktime)
        
        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
    
    def test_Net1_charset(self):
        """Only needs to test that runs successfully with latin-1 character set."""
        inp_file = join(test_datadir, "latin1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)

        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

    def test_Net1_performance(self):
        head_diff_abs_threshold = 1e-3
        demand_diff_abs_threshold = 1e-5
        flow_diff_abs_threshold = 1e-5
        rel_threshold = 1e-3

        inp_file = join(ex_datadir, "Net1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)

        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        self.assertTrue(
            compare_results(
                results.node["head"],
                epa_res.node["head"],
                head_diff_abs_threshold,
                rel_threshold,
            )
        )
        self.assertTrue(
            compare_results(
                results.node["demand"].loc[:, wn.tank_name_list],
                epa_res.node["demand"].loc[:, wn.tank_name_list],
                demand_diff_abs_threshold,
                rel_threshold,
            )
        )
        self.assertTrue(
            compare_results(
                results.link["flowrate"],
                epa_res.link["flowrate"],
                flow_diff_abs_threshold,
                rel_threshold,
            )
        )

    def test_Net3_performance(self):
        head_diff_abs_threshold = 1e-3
        demand_diff_abs_threshold = 1e-5
        flow_diff_abs_threshold = 1e-5
        rel_threshold = 1e-3

        inp_file = join(ex_datadir, "Net3.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)

        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        self.assertTrue(
            compare_results(
                results.node["head"],
                epa_res.node["head"],
                head_diff_abs_threshold,
                rel_threshold,
            )
        )
        self.assertTrue(
            compare_results(
                results.node["demand"].loc[:, wn.tank_name_list],
                epa_res.node["demand"].loc[:, wn.tank_name_list],
                demand_diff_abs_threshold,
                rel_threshold,
            )
        )
        self.assertTrue(
            compare_results(
                results.link["flowrate"],
                epa_res.link["flowrate"],
                flow_diff_abs_threshold,
                rel_threshold,
            )
        )

    def test_Net3_performance_PDA(self):
        head_diff_abs_threshold = 1e-3
        demand_diff_abs_threshold = 1e-5
        flow_diff_abs_threshold = 1e-5
        rel_threshold = 1e-3

        inp_file = join(ex_datadir, "Net3.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.options.hydraulic.demand_model = "PDA"

        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim(version=2.2)

        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        self.assertTrue(
            compare_results(
                results.node["head"],
                epa_res.node["head"],
                head_diff_abs_threshold,
                rel_threshold,
            )
        )
        self.assertTrue(
            compare_results(
                results.node["demand"].loc[:, wn.tank_name_list],
                epa_res.node["demand"].loc[:, wn.tank_name_list],
                demand_diff_abs_threshold,
                rel_threshold,
            )
        )
        self.assertTrue(
            compare_results(
                results.link["flowrate"],
                epa_res.link["flowrate"],
                flow_diff_abs_threshold,
                rel_threshold,
            )
        )
    
    @pytest.mark.time_consuming
    def test_Net6_thread_results(self):
        """Compare threaded and sequential results for both simulators."""
        inp_file = join(ex_datadir, "Net6.inp")

        def run_sim(simulator_type, name):
            # Each run needs a fresh model because WNTR stores simulation state.
            wn = self.wntr.network.WaterNetworkModel(inp_file)
            wn.options.time.duration = 24 * 3600
            wn.options.time.hydraulic_timestep = 3600
            wn.options.time.report_timestep = 3600
            # EPANET does not activate this control at the tank's maximum level.
            wn.remove_control("control 72")
            sim = simulator_type(wn)
            if simulator_type is self.wntr.sim.EpanetSimulator:
                return sim.run_sim(name, version=2.2)
            return sim.run_sim()

        for simulator_type in (self.wntr.sim.EpanetSimulator, self.wntr.sim.WNTRSimulator):
            with self.subTest(simulator=simulator_type.__name__):
                sequential = [run_sim(simulator_type, f"seq{i}") for i in range(2)]
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [
                        executor.submit(run_sim, simulator_type, f"thr{i}")
                        for i in range(2)
                    ]
                    threaded = [future.result() for future in futures]

                for expected, actual in zip(sequential, threaded, strict=True):
                    for expected_data, actual_data in (
                        (expected.node, actual.node), (expected.link, actual.link)
                    ):
                        assert expected_data
                        assert actual_data
                        self.assertEqual(expected_data.keys(), actual_data.keys())
                        for variable in expected_data:
                            pandas.testing.assert_frame_equal(
                                expected_data[variable],
                                actual_data[variable],
                                check_exact=False, rtol=1e-6, atol=1e-8,
                            )
        
    @pytest.mark.time_consuming
    def test_Net6_mod_performance(self):
        head_diff_abs_threshold = 1e-3
        demand_diff_abs_threshold = 1e-5
        flow_diff_abs_threshold = 1e-5
        rel_threshold = 1e-3

        inp_file = join(ex_datadir, "Net6.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.duration = 24 * 3600
        wn.options.time.hydraulic_timestep = 3600
        wn.options.time.report_timestep = 3600
        wn.remove_control(
            "control 72"
        )  # this control never gets activated in epanet because it uses a threshold equal to the tank max level

        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        self.assertTrue(
            compare_results(
                results.node["head"],
                epa_res.node["head"],
                head_diff_abs_threshold,
                rel_threshold,
            )
        )
        # self.assertTrue(compare_results(results.node['demand'].loc[:, wn.tank_name_list], epa_res.node['demand'].loc[:, wn.tank_name_list], demand_diff_abs_threshold, rel_threshold))
        # self.assertTrue(compare_results(results.link['flowrate'], epa_res.link['flowrate'], flow_diff_abs_threshold, rel_threshold))


if __name__ == "__main__":
    unittest.main()
