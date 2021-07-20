import math
import unittest
from os.path import abspath, dirname, join

from wntr.network.controls import Control, Rule

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestOutageResults(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_outage(self):
        inp_file = join(ex_datadir, "Net3.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.convert_controls_to_rules(priority=3)

        # Original simulation
        sim = self.wntr.sim.EpanetSimulator(wn)
        results1 = sim.run_sim()

        pump_flowrate = results1.link["flowrate"].loc[13 * 3600 : 36 * 3600, "10"]
        assert pump_flowrate.sum() > 0

        # Add power outage
        pump = wn.get_link("10")
        pump.add_outage(wn, 12 * 3600, 36 * 3600)

        sim = self.wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()

        assert "10_outage" in wn.control_name_list
        num_controls = wn.num_controls

        pump_flowrate = results2.link["flowrate"].loc[13 * 3600 : 36 * 3600, "10"]
        assert pump_flowrate.sum() == 0

        # Remove power outage
        pump.remove_outage(wn)

        assert wn.num_controls == num_controls - 1

        sim = self.wntr.sim.EpanetSimulator(wn)
        results3 = sim.run_sim()

        pump_flowrate = results3.link["flowrate"].loc[13 * 3600 : 36 * 3600, "10"]
        assert pump_flowrate.sum() > 0

        # (results1.node['pressure'] - results2.node['pressure']).plot()
        # (results1.node['pressure'] - results3.node['pressure']).plot()

        max_diff = (
            abs(results1.node["pressure"] - results3.node["pressure"]).max().max()
        )

        assert max_diff < 0.0001


if __name__ == "__main__":
    unittest.main()

