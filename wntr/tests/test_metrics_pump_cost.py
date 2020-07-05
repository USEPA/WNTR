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
        self.wn.options.hydraulic.demand_model = 'DDA'
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.results = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_pump_cost(self):
        flowrate = self.results.link['flowrate'].loc[:,self.wn.pump_name_list]
        head = self.results.node['head'].loc[:,self.wn.node_name_list]
        
        cost = self.wntr.metrics.pump_cost(flowrate, head, self.wn)

        total_cost = 0
        times = self.results.link['flowrate'].index
        for i in range(len(times) - 1):
            t = times[i]
            delta_t = times[i + 1] - t
            total_cost = total_cost + cost.loc[t, :] * delta_t

        avg_cost = total_cost / (times[-1] - times[0])

        avg_cost_sum = avg_cost.sum()

        self.assertAlmostEqual(avg_cost_sum, 0.070484, 5)

if __name__ == '__main__':
    unittest.main()