import sys
import unittest
from os.path import abspath, dirname, join
import threading
import time

import pandas

pandas.set_option("display.max_rows", 10000)

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")
results_dir = join(testdir, "performance_results")


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
        sys.path.append(results_dir)
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

    def test_Net6_thread_performance(self):
        """
        Test thread-safe performance of simulators
        """
        def run_epanet(wn, name):
            sim = self.wntr.sim.EpanetSimulator(wn)
            sim.run_sim(name, version=2.2)

        def run_wntr(wn, name):
            sim = self.wntr.sim.WNTRSimulator(wn)
            sim.run_sim()

        inp_file = join(ex_datadir, "Net6.inp")
        wn1 = self.wntr.network.WaterNetworkModel(inp_file)
        wn1.options.time.duration = 24 * 3600
        wn1.options.time.hydraulic_timestep = 3600
        wn1.options.time.report_timestep = 3600
        wn1.remove_control(
            "control 72"
        )  # this control never gets activated in epanet because it uses a threshold equal to the tank max level
        wn2 = self.wntr.network.WaterNetworkModel(inp_file)
        wn2.options.time.duration = 24 * 3600
        wn2.options.time.hydraulic_timestep = 3600
        wn2.options.time.report_timestep = 3600
        wn2.remove_control(
            "control 72"
        )  # this control never gets activated in epanet because it uses a threshold equal to the tank max level

        start_time = time.time()
        run_epanet(wn1, 'temp1')
        run_epanet(wn2, 'temp2')
        seq_time = time.time()-start_time

        t1 = threading.Thread(target=run_epanet, args=(wn1, 'temp1'))
        t2 = threading.Thread(target=run_epanet, args=(wn2, 'temp2'))
        start_time = time.time()
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        thr_time = time.time()-start_time
        self.assertGreaterEqual(seq_time - thr_time, -1, 'EPANET threading took 1s longer than sequential')

        start_time = time.time()
        run_wntr(wn1, 'temp1')
        run_wntr(wn2, 'temp2')
        seq_time = time.time()-start_time

        t1 = threading.Thread(target=run_wntr, args=(wn1, 'temp1'))
        t2 = threading.Thread(target=run_wntr, args=(wn2, 'temp2'))
        start_time = time.time()
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        thr_time = time.time()-start_time
        self.assertGreaterEqual(seq_time - thr_time, -1, 'WNTR threading took 1s longer than sequential')

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
