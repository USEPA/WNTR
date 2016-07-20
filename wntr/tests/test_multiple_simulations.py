# These tests run a demand driven simulation with both Pyomo and Epanet and compare the results for the example networks
import unittest
import sys
import os, inspect
import pandas as pd
import pickle
resilienceMainDir = os.path.abspath( 
    os.path.join( os.path.dirname( os.path.abspath( inspect.getfile( 
        inspect.currentframe() ) ) ), '..', '..' ))

class TestResetInitialValues(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/examples/networks/Net3.inp'
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.hydraulic_timestep = 3600
        self.wn.options.duration = 24*3600
        
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res1 = sim.run_sim(solver_options={'TOL':1e-8})

        self.wn.reset_initial_values()
        self.res2 = sim.run_sim(solver_options={'TOL':1e-8})

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link.major_axis:
                self.assertAlmostEqual(self.res1.link.at['flowrate',t,link_name], self.res2.link.at['flowrate',t,link_name], 7)

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link.major_axis:
                self.assertAlmostEqual(self.res1.link.at['velocity',t,link_name], self.res2.link.at['velocity',t,link_name], 7)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['demand',t,node_name], self.res2.node.at['demand',t,node_name], 7)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['expected_demand',t,node_name], self.res2.node.at['expected_demand',t,node_name], 7)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['head',t,node_name], self.res2.node.at['head',t,node_name], 7)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['pressure',t,node_name], self.res2.node.at['pressure',t,node_name], 7)

class TestStopStartSim(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/examples/networks/Net3.inp'

        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.hydraulic_timestep = 3600
        self.wn.options.duration = 24*3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res1 = sim.run_sim(solver_options={'TOL':1e-8})

        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.hydraulic_timestep = 3600
        self.wn.options.duration = 10*3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res2 = sim.run_sim(solver_options={'TOL':1e-8})
        self.wn.options.duration = 24*3600
        self.res3 = sim.run_sim(solver_options={'TOL':1e-8})

        node_res = pd.concat([self.res2.node,self.res3.node],axis=1)
        link_res = pd.concat([self.res2.link,self.res3.link],axis=1)
        self.res2.node = node_res
        self.res2.link = link_res

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link.major_axis:
                self.assertAlmostEqual(self.res1.link.at['flowrate',t,link_name], self.res2.link.at['flowrate',t,link_name], 7)

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link.major_axis:
                self.assertAlmostEqual(self.res1.link.at['velocity',t,link_name], self.res2.link.at['velocity',t,link_name], 7)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['demand',t,node_name], self.res2.node.at['demand',t,node_name], 7)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['expected_demand',t,node_name], self.res2.node.at['expected_demand',t,node_name], 7)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['head',t,node_name], self.res2.node.at['head',t,node_name], 7)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['pressure',t,node_name], self.res2.node.at['pressure',t,node_name], 7)

class TestPickle(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/examples/networks/Net3.inp'

        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.hydraulic_timestep = 3600
        self.wn.options.duration = 24*3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res1 = sim.run_sim(solver_options={'TOL':1e-8})

        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.hydraulic_timestep = 3600
        self.wn.options.duration = 10*3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res2 = sim.run_sim(solver_options={'TOL':1e-8})
        f=open('pickle_test.pickle','w')
        pickle.dump(self.wn,f)
        f.close()
        f=open('pickle_test.pickle','r')
        wn2 = pickle.load(f)
        f.close()
        wn2.options.duration = 24*3600
        sim = self.wntr.sim.WNTRSimulator(wn2)
        self.res3 = sim.run_sim(solver_options={'TOL':1e-8})

        node_res = pd.concat([self.res2.node,self.res3.node],axis=1)
        link_res = pd.concat([self.res2.link,self.res3.link],axis=1)
        self.res2.node = node_res
        self.res2.link = link_res

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link.major_axis:
                self.assertAlmostEqual(self.res1.link.at['flowrate',t,link_name], self.res2.link.at['flowrate',t,link_name], 7)

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link.major_axis:
                self.assertAlmostEqual(self.res1.link.at['velocity',t,link_name], self.res2.link.at['velocity',t,link_name], 7)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['demand',t,node_name], self.res2.node.at['demand',t,node_name], 7)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['expected_demand',t,node_name], self.res2.node.at['expected_demand',t,node_name], 7)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['head',t,node_name], self.res2.node.at['head',t,node_name], 7)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node.major_axis:
                self.assertAlmostEqual(self.res1.node.at['pressure',t,node_name], self.res2.node.at['pressure',t,node_name], 7)

if __name__ == '__main__':
    unittest.main()
