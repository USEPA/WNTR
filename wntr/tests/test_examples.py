# These tests run a demand driven simulation with both Pyomo and Epanet and compare the results for the example networks
import unittest
import sys
import os, inspect
resilienceMainDir = os.path.abspath( 
    os.path.join( os.path.dirname( os.path.abspath( inspect.getfile( 
        inspect.currentframe() ) ) ), '..', '..' ))

class TestWithEpanet(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_2.inp'
        self.wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)
        
        epanet_sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.epanet_results = epanet_sim.run_sim()
        
        pyomo_sim = self.wntr.sim.PyomoSimulator(self.wn, 'DEMAND DRIVEN')
        self.pyomo_results = pyomo_sim.run_sim(solver_options = {'tol':1e-10}, modified_hazen_williams=False)

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.pyomo_results.link.loc[link_name].index:
                self.assertLessEqual(abs(self.pyomo_results.link.at[(link_name,t),'flowrate'] - self.epanet_results.link.at[(link_name,t),'flowrate']), 0.00001)

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.pyomo_results.link.loc[link_name].index:
                self.assertLessEqual(abs(self.pyomo_results.link.at[(link_name,t),'velocity'] - self.epanet_results.link.at[(link_name,t),'velocity']), 0.00001)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'demand'] - self.epanet_results.node.at[(node_name,t),'demand']), 0.00001)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'expected_demand'] - self.epanet_results.node.at[(node_name,t),'expected_demand']), 0.00001)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'head'] - self.epanet_results.node.at[(node_name,t),'head']), 0.0001)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'pressure'] - self.epanet_results.node.at[(node_name,t),'pressure']), 0.0001)

#class TestNet1(unittest.TestCase):
#
#    @classmethod
#    def setUpClass(self):
#        sys.path.append(resilienceMainDir)
#        import wntr
#        self.wntr = wntr
#
#        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_13.inp'
#        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
#        
#        epanet_sim = self.wntr.sim.EpanetSimulator(self.wn)
#        self.epanet_results = epanet_sim.run_sim()
#        
#        pyomo_sim = self.wntr.sim.PyomoSimulator(self.wn, 'DEMAND DRIVEN')
#        self.pyomo_results = pyomo_sim.run_sim(solver_options = {'tol':1e-10}, modified_hazen_williams=True)
#
#    @classmethod
#    def tearDownClass(self):
#        sys.path.remove(resilienceMainDir)
#
#    def test_link_flowrate(self):
#        for link_name, link in self.wn.links():
#            self.assertLessEqual(abs(self.pyomo_results.link.loc[link_name]['flowrate'].mean() - self.epanet_results.link.loc[link_name]['flowrate'].mean()), 0.0002)
#
#    def test_node_demand(self):
#        for node_name, node in self.wn.nodes():
#                self.assertLessEqual(abs(self.pyomo_results.node.loc[node_name]['demand'].mean() - self.epanet_results.node.loc[node_name]['demand'].mean()), 0.0001)
#
#    def test_node_expected_demand(self):
#        for node_name, node in self.wn.nodes():
#                self.assertLessEqual(abs(self.pyomo_results.node.loc[node_name]['expected_demand'].mean() - self.epanet_results.node.loc[node_name]['expected_demand'].mean()), 0.0001)
#
#    def test_node_head(self):
#        for node_name, node in self.wn.nodes():
#                self.assertLessEqual(abs(self.pyomo_results.node.loc[node_name]['head'].mean() - self.epanet_results.node.loc[node_name]['head'].mean()), 0.1)
#
#    def test_node_pressure(self):
#        for node_name, node in self.wn.nodes():
#                self.assertLessEqual(abs(self.pyomo_results.node.loc[node_name]['pressure'].mean() - self.epanet_results.node.loc[node_name]['pressure'].mean()), 0.1)

if __name__ == '__main__':
    unittest.main()
