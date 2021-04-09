import math
import unittest
from os.path import abspath, dirname, join

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestPDD(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_pdd_with_wntr(self):
        inp_file = join(test_datadir, "simulator.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        res1 = wn.get_node("reservoir1")
        res1.head_timeseries.base_value = 10.0
        p1 = wn.get_link("pipe1")
        p1.length = 0.0
        p2 = wn.get_link("pipe2")
        p2.length = 0.0

        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0

        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        for t in results.time:
            self.assertEqual(
                results.node["demand"].at[t, "junction2"],
                150.0 / 3600.0 * math.sqrt((10.0 - 0.0) / (15.0 - 0.0)),
            )


if __name__ == "__main__":
    unittest.main()
