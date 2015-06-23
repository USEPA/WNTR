# These tests run a demand driven simulation with both Pyomo and Epanet and compare the results for the example networks
import unittest
import sys
sys.path.append('../../')
import epanetlib as en

class TestNet1(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        inp_file = 'networks_for_testing/Net1.inp'
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
                self.assertLessEqual(abs(self.pyomo_results.link.at[(link_name,t),'flowrate'] - self.epanet_results.link.at[(link_name,t),'flowrate']), 0.1)

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.pyomo_results.link.loc[link_name].index:
                self.assertLessEqual(abs(self.pyomo_results.link.at[(link_name,t),'velocity'] - self.epanet_results.link.at[(link_name,t),'velocity']), 0.1)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'demand'] - self.epanet_results.node.at[(node_name,t),'demand']), 0.1)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'expected_demand'] - self.epanet_results.node.at[(node_name,t),'expected_demand']), 0.1)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'head'] - self.epanet_results.node.at[(node_name,t),'head']), 0.1)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'pressure'] - self.epanet_results.node.at[(node_name,t),'pressure']), 0.1)

if __name__ == '__main__':
    unittest.main()
