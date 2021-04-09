import math
import unittest
from os.path import abspath, dirname, join

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestLeakResults(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_leak_demand(self):
        inp_file = join(test_datadir, "leaks.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn = self.wntr.morph.split_pipe(wn, "pipe2", "pipe2__B", "leak1")
        leak1 = wn.get_node("leak1")
        leak1.add_leak(wn, area=math.pi / 4.0 * 0.01 ** 2, discharge_coeff=0.75)
        active_control_action = self.wntr.network.ControlAction(
            leak1, "leak_status", True
        )
        inactive_control_action = self.wntr.network.ControlAction(
            leak1, "leak_status", False
        )
        control = self.wntr.network.controls.Control._time_control(
            wn, 4 * 3600, "SIM_TIME", False, active_control_action
        )
        wn.add_control("control1", control)
        control = self.wntr.network.controls.Control._time_control(
            wn, 8 * 3600, "SIM_TIME", False, inactive_control_action
        )
        wn.add_control("control2", control)
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        for t in results.node["leak_demand"].index:
            if t < 4 * 3600 or t >= 8 * 3600:
                self.assertAlmostEqual(results.node["leak_demand"].at[t, "leak1"], 0.0)
            else:
                self.assertAlmostEqual(
                    results.node["leak_demand"].at[t, "leak1"],
                    0.75
                    * math.pi
                    / 4.0
                    * 0.01 ** 2.0
                    * math.sqrt(2 * 9.81 * results.node["pressure"].loc[t, "leak1"]),
                )

    def test_leak_against_epanet(self):
        inp_file = join(test_datadir, "leaks.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn = self.wntr.morph.split_pipe(wn, "pipe2", "pipe2__B", "leak1")
        leak1 = wn.get_node("leak1")
        leak1.add_leak(
            wn,
            area=math.pi / 4.0 * 0.08 ** 2,
            discharge_coeff=0.75,
            start_time=0,
            end_time=None,
        )
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        inp_file = join(test_datadir, "epanet_leaks.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.options.hydraulic.inpfile_units = self.wntr.epanet.util.FlowUnits.CMH
        sim = self.wntr.sim.EpanetSimulator(wn)
        epanet_results = sim.run_sim()

        for link_name, link in wn.links():
            for t in results.link["flowrate"].index:
                self.assertLessEqual(
                    abs(
                        results.link["flowrate"].at[t, link_name]
                        - epanet_results.link["flowrate"].at[t, link_name]
                    ),
                    0.00001,
                )

        for node_name, node in wn.nodes():
            if node_name != "leak1":
                for t in results.node["demand"].index:
                    self.assertLessEqual(
                        abs(
                            results.node["demand"].at[t, node_name]
                            - epanet_results.node["demand"].at[t, node_name]
                        ),
                        0.00001,
                    )
            else:
                for t in results.node["leak_demand"].index:
                    self.assertLessEqual(
                        abs(
                            results.node["leak_demand"].at[t, node_name]
                            - epanet_results.node["demand"].at[t, node_name]
                        ),
                        0.00001,
                    )

        for node_name, node in wn.nodes():
            for t in results.node["head"].index:
                self.assertLessEqual(
                    abs(
                        results.node["head"].at[t, node_name]
                        - epanet_results.node["head"].at[t, node_name]
                    ),
                    0.001,
                )

        for node_name, node in wn.nodes():
            for t in results.node["pressure"].index:
                self.assertLessEqual(
                    abs(
                        results.node["pressure"].at[t, node_name]
                        - epanet_results.node["pressure"].at[t, node_name]
                    ),
                    0.001,
                )

    # def test_remove_leak_results(self):
    #    inp_file = join(test_datadir. 'net_test_13.inp')
    #    wn = self.wntr.network.WaterNetworkModel(inp_file)
    #    sim = self.wntr.sim.PyomoSimulator(wn)
    #    results1 = sim.run_sim()
    #    j2 = wn.get_node('junction2')
    #    j2.add_leak(math.pi/4.0*0.08**2, 0.75, 4*3600, 12*3600)
    #    j2.remove_leak()
    #    sim = self.wntr.sim.PyomoSimulator(wn)
    #    results2 = sim.run_sim()
    #
    #    self.assertEqual(True, (results1.node == results2.node)['demand'].all().all())
    #    self.assertEqual(True, (results1.node == results2.node)['head'].all().all())
    #    self.assertEqual(True, (results1.node == results2.node)['pressure'].all().all())
    #    self.assertEqual(True, (results1.node == results2.node)['type'].all().all())
    #
    #    self.assertEqual(True, (results1.link == results2.link)['flowrate'].all().all())
    #    self.assertEqual(True, (results1.link == results2.link)['velocity'].all().all())
    #    self.assertEqual(True, (results1.link == results2.link)['type'].all().all())


if __name__ == "__main__":
    unittest.main()

