import unittest
from os.path import abspath, dirname, join

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, 'networks_for_testing')
ex_datadir = join(testdir,'..','..','examples','networks')


class TestPumpCost(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr

        inp_file = join(ex_datadir, 'Net6.inp')
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.report_timestep = 'all'
        self.wn.options.duration = 12*3600
        self.wn.energy.global_price = 0.13
        sim = self.wntr.sim.WNTRSimulator(self.wn, pressure_driven=False)
        self.results = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_pump_cost(self):
        pump_res = self.wntr.metrics.pump_energy(self.wn, self.results, 'average')
        cost = pump_res.sum().loc['cost']
        self.assertAlmostEqual(cost, 0.070484, 5)
