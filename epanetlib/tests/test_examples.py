# These tests run a demand driven simulation with both Pyomo and Epanet and compare the results for the example networks
import unittest
import sys
sys.path.append('../../')
import epanetlib as en

class TestNet1(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        inp_file = 'networks_for_testing/net_test_1.inp'
        self.wn = en.network.WaterNetworkModel()
        parser = en.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)
        
        epanet_sim = en.sim.EpanetSimulator(self.wn)
        self.epanet_results = epanet_sim.run_sim()
        
        pyomo_sim = en.sim.PyomoSimulator(self.wn, 'DEMAND DRIVEN')
        self.pyomo_results = pyomo_sim.run_sim()

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.pyomo_results.link.loc[link_name].index:
                self.assertEqual(round(self.pyomo_results.link.at[(link_name,t),'flowrate'],5), round(self.epanet_results.link.at[(link_name,t),'flowrate'],5))

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.pyomo_results.link.loc[link_name].index:
                self.assertEqual(round(self.pyomo_results.link.at[(link_name,t),'velocity'],5), round(self.epanet_results.link.at[(link_name,t),'velocity'],5))

if __name__ == '__main__':
    unittest.main()
