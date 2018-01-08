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
        self.wn.options.time.report_timestep = 'all'
        self.wn.options.time.duration = 12*3600
        self.wn.options.energy.global_price = 3.61111111111e-8
        sim = self.wntr.sim.WNTRSimulator(self.wn, mode='DD')
        self.results = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_pump_cost(self):
        pump_res = self.wntr.metrics.pump_energy(self.wn, self.results)
        cost = pump_res.loc['cost',:,:]

        total_cost = 0
        for i in range(len(self.results.time) - 1):
            t = self.results.time[i]
            delta_t = self.results.time[i + 1] - t
            total_cost = total_cost + cost.loc[t, :] * delta_t

        avg_cost = total_cost / (self.results.time[-1] - self.results.time[0])

        avg_cost_sum = avg_cost.sum()

        self.assertAlmostEqual(avg_cost_sum, 0.070484, 5)
