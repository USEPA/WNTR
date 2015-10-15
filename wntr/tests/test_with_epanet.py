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
        
        pyomo_sim = self.wntr.sim.PyomoSimulator(self.wn)
        self.pyomo_results = pyomo_sim.run_sim(solver_options = {'tol':1e-10}, modified_hazen_williams=False)

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.pyomo_results.link.major_axis:
                self.assertAlmostEqual(self.pyomo_results.link.at['flowrate',t,link_name], self.epanet_results.link.at['flowrate',t,link_name], 5)

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.pyomo_results.link.major_axis:
                self.assertAlmostEqual(self.pyomo_results.link.at['velocity',t,link_name], self.epanet_results.link.at['velocity',t,link_name], 5)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.major_axis:
                self.assertAlmostEqual(self.pyomo_results.node.at['demand',t,node_name], self.epanet_results.node.at['demand',t,node_name], 5)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.major_axis:
                self.assertAlmostEqual(self.pyomo_results.node.at['expected_demand',t,node_name], self.epanet_results.node.at['expected_demand',t,node_name], 5)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.major_axis:
                self.assertAlmostEqual(self.pyomo_results.node.at['head',t,node_name], self.epanet_results.node.at['head',t,node_name], 3)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.major_axis:
                self.assertAlmostEqual(self.pyomo_results.node.at['pressure',t,node_name], self.epanet_results.node.at['pressure',t,node_name], 3)

class TestNet1(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_14.inp'
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        
        epanet_sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.epanet_results = epanet_sim.run_sim()
        
        pyomo_sim = self.wntr.sim.PyomoSimulator(self.wn)
        self.pyomo_results = pyomo_sim.run_sim(solver_options = {'hessian_approximation':'exact', 'halt_on_ampl_error':'yes'}, modified_hazen_williams=True)

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.pyomo_results.link.major_axis:
                self.assertLessEqual(abs(self.pyomo_results.link.at['flowrate',t,link_name] - self.epanet_results.link.at['flowrate',t,link_name]), 0.001)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.major_axis:
                self.assertAlmostEqual(self.pyomo_results.node.at['demand',t,node_name], self.epanet_results.node.at['demand',t,node_name], 5)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.major_axis:
                self.assertAlmostEqual(self.pyomo_results.node.at['expected_demand',t,node_name], self.epanet_results.node.at['expected_demand',t,node_name], 5)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.major_axis:
                self.assertLessEqual(abs(self.pyomo_results.node.at['head',t,node_name] - self.epanet_results.node.at['head',t,node_name]), 0.5)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.pyomo_results.node.major_axis:
                self.assertLessEqual(abs(self.pyomo_results.node.at['pressure',t,node_name] - self.epanet_results.node.at['pressure',t,node_name]), 0.5)

class TestNet3(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        #inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_15.inp'
        inp_file = resilienceMainDir+'/wntr/tests/timing/timing.inp'
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        
        epanet_sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.epanet_results = epanet_sim.run_sim()
        
        scipy_sim = self.wntr.sim.ScipySimulatorV2(self.wn)
        self.scipy_results = scipy_sim.run_sim()

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.scipy_results.link.major_axis:
                self.assertLessEqual(abs(self.scipy_results.link.at['flowrate',t,link_name] - self.epanet_results.link.at['flowrate',t,link_name]), 0.001)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.scipy_results.node.major_axis:
                self.assertAlmostEqual(self.scipy_results.node.at['demand',t,node_name], self.epanet_results.node.at['demand',t,node_name], 3)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.scipy_results.node.major_axis:
                self.assertAlmostEqual(self.scipy_results.node.at['expected_demand',t,node_name], self.epanet_results.node.at['expected_demand',t,node_name], 3)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.scipy_results.node.major_axis:
                self.assertLessEqual(abs(self.scipy_results.node.at['head',t,node_name] - self.epanet_results.node.at['head',t,node_name]), 0.1)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.scipy_results.node.major_axis:
                self.assertLessEqual(abs(self.scipy_results.node.at['pressure',t,node_name] - self.epanet_results.node.at['pressure',t,node_name]), 0.1)

#class TestNet6_mod(unittest.TestCase):
#
#    @classmethod
#    def setUpClass(self):
#        sys.path.append(resilienceMainDir)
#        import wntr
#        self.wntr = wntr
#
#        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_16.inp'
#        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
#        
#        epanet_sim = self.wntr.sim.EpanetSimulator(self.wn)
#        self.epanet_results = epanet_sim.run_sim()
#        
#        pyomo_sim = self.wntr.sim.PyomoSimulator(self.wn)
#        self.pyomo_results = pyomo_sim.run_sim(solver_options = {'hessian_approximation':'exact', 'halt_on_ampl_error':'yes'}, modified_hazen_williams=True)
#
#	for node_name in self.pyomo_results.node.index.levels[0]:
#	    print
#	    print 'node ',node_name
#	    print('{0:20s}{1:20s}{2:20s}{3:20s}'.format('time','pyomo head','epanet head','difference'))
#	    for t in self.pyomo_results.node.index.levels[1]:
#	        print('{0:20s}{1:<20.4f}{2:<20.4f}{3:<20.4f}'.format(t, self.pyomo_results.node.at[(node_name,t),'head'], self.epanet_results.node.at[(node_name,t),'head'], abs(self.pyomo_results.node.at[(node_name,t),'head'] - self.epanet_results.node.at[(node_name,t),'head'])))
#	
#	for node_name in self.pyomo_results.node.index.levels[0]:
#	    print
#	    print 'node ',node_name
#	    print('{0:20s}{1:20s}{2:20s}{3:20s}'.format('time','pyomo P','epanet P','difference'))
#	    for t in self.pyomo_results.node.index.levels[1]:
#	        print('{0:20s}{1:<20.4f}{2:<20.4f}{3:<20.4f}'.format(t, self.pyomo_results.node.at[(node_name,t),'pressure'], self.epanet_results.node.at[(node_name,t),'pressure'], abs(self.pyomo_results.node.at[(node_name,t),'pressure'] - self.epanet_results.node.at[(node_name,t),'pressure'])))
#	
#	for node_name in self.pyomo_results.node.index.levels[0]:
#	    print
#	    print 'node ',node_name
#	    print('{0:20s}{1:20s}{2:20s}{3:20s}'.format('time','pyomo Dact','epanet Dact','difference'))
#	    for t in self.pyomo_results.node.index.levels[1]:
#	        print('{0:20s}{1:<20.4f}{2:<20.4f}{3:<20.4f}'.format(t, self.pyomo_results.node.at[(node_name,t),'demand'], self.epanet_results.node.at[(node_name,t),'demand'], abs(self.pyomo_results.node.at[(node_name,t),'demand'] - self.epanet_results.node.at[(node_name,t),'demand'])))
#	
#	for node_name in self.pyomo_results.node.index.levels[0]:
#	    print
#	    print 'node ',node_name
#	    print('{0:20s}{1:20s}{2:20s}{3:20s}'.format('time','pyomo Dexp','epanet Dexp','difference'))
#	    for t in self.pyomo_results.node.index.levels[1]:
#	        print('{0:20s}{1:<20.4f}{2:<20.4f}{3:<20.4f}'.format(t, self.pyomo_results.node.at[(node_name,t),'expected_demand'], self.epanet_results.node.at[(node_name,t),'expected_demand'], abs(self.pyomo_results.node.at[(node_name,t),'expected_demand'] - self.epanet_results.node.at[(node_name,t),'expected_demand'])))
#	
#	for link_name in self.pyomo_results.link.index.levels[0]:
#	    print
#	    print 'link ',link_name
#	    print('{0:20s}{1:20s}{2:20s}{3:20s}'.format('time','pyomo velocity','epanet velocity','difference'))
#	    for t in self.pyomo_results.link.index.levels[1]:
#	        print('{0:20s}{1:<20.4f}{2:<20.4f}{3:<20.4f}'.format(t, self.pyomo_results.link.at[(link_name,t),'velocity'], self.epanet_results.link.at[(link_name,t),'velocity'], abs(self.pyomo_results.link.at[(link_name,t),'velocity'] - self.epanet_results.link.at[(link_name,t),'velocity'])))
#	
#	for link_name in self.pyomo_results.link.index.levels[0]:
#	    print
#	    print 'link ',link_name
#	    print('{0:20s}{1:20s}{2:20s}{3:20s}'.format('time','pyomo flowrate','epanet flowrate','difference'))
#	    for t in self.pyomo_results.link.index.levels[1]:
#	        print('{0:20s}{1:<20.4f}{2:<20.4f}{3:<20.4f}'.format(t, self.pyomo_results.link.at[(link_name,t),'flowrate'], self.epanet_results.link.at[(link_name,t),'flowrate'], abs(self.pyomo_results.link.at[(link_name,t),'flowrate'] - self.epanet_results.link.at[(link_name,t),'flowrate'])))
#
#
#    @classmethod
#    def tearDownClass(self):
#        sys.path.remove(resilienceMainDir)
#
#    def test_link_flowrate(self):
#        for link_name, link in self.wn.links():
#            for t in self.pyomo_results.link.loc[link_name].index:
#                self.assertLessEqual(abs(self.pyomo_results.link.at[(link_name,t),'flowrate'] - self.epanet_results.link.at[(link_name,t),'flowrate']), 0.001)
#
#    def test_node_demand(self):
#        for node_name, node in self.wn.nodes():
#            for t in self.pyomo_results.node.loc[node_name].index:
#                self.assertAlmostEqual(self.pyomo_results.node.at[(node_name,t),'demand'], self.epanet_results.node.at[(node_name,t),'demand'], 3)
#
#    def test_node_expected_demand(self):
#        for node_name, node in self.wn.nodes():
#            for t in self.pyomo_results.node.loc[node_name].index:
#                self.assertAlmostEqual(self.pyomo_results.node.at[(node_name,t),'expected_demand'], self.epanet_results.node.at[(node_name,t),'expected_demand'], 3)
#
#    def test_node_head(self):
#        for node_name, node in self.wn.nodes():
#            for t in self.pyomo_results.node.loc[node_name].index:
#                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'head'] - self.epanet_results.node.at[(node_name,t),'head']), 0.1)
#
#    def test_node_pressure(self):
#        for node_name, node in self.wn.nodes():
#            for t in self.pyomo_results.node.loc[node_name].index:
#                self.assertLessEqual(abs(self.pyomo_results.node.at[(node_name,t),'pressure'] - self.epanet_results.node.at[(node_name,t),'pressure']), 0.1)

if __name__ == '__main__':
    unittest.main()
