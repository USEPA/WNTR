import unittest
import sys
# HACK until resilience is a proper module
# __file__ fails if script is called in different ways on Windows
# __file__ fails if someone does os.chdir() before
# sys.argv[0] also fails because it doesn't not always contains the path
import os, inspect
resilienceMainDir = os.path.abspath( 
    os.path.join( os.path.dirname( os.path.abspath( inspect.getfile( 
        inspect.currentframe() ) ) ), '..', '..' ))
import math
import pandas as pd

class TestLeakAdditionaAndRemoval(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_add_leak(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_1.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        pipe = wn.get_link('pipe1')
        wn.add_leak('leak1','pipe1', 0.1)
        pipeA = wn.get_link('pipe1__A')
        pipeB = wn.get_link('pipe1__B')
        self.assertEqual(True, 'leak1' in [name for name,n in wn.nodes()])
        self.assertEqual(True, 'leak1' in [name for name,n in wn.nodes(self.wntr.network.Leak)])
        self.assertEqual(True, 'pipe1__A' in [name for name,l in wn.links()])
        self.assertEqual(True, 'pipe1__A' in [name for name,l in wn.links(self.wntr.network.Pipe)])
        self.assertEqual(True, 'pipe1__B' in [name for name,l in wn.links()])
        self.assertEqual(True, 'pipe1__B' in [name for name,l in wn.links(self.wntr.network.Pipe)])
        self.assertEqual(pipe.start_node(), pipeA.start_node())
        self.assertEqual(pipe.end_node(), pipeB.end_node())
        self.assertEqual(pipeA.end_node(), 'leak1')
        self.assertEqual(pipeB.start_node(), 'leak1')
        self.assertEqual(pipe.length, pipeA.length+pipeB.length)
        self.assertEqual(pipe.diameter, pipeA.diameter)
        self.assertEqual(pipe.diameter, pipeB.diameter)
        self.assertEqual(pipe.roughness, pipeA.roughness)
        self.assertEqual(pipe.roughness, pipeB.roughness)
        self.assertEqual(pipe.minor_loss, pipeA.minor_loss)
        self.assertEqual(pipe.minor_loss, pipeB.minor_loss)
        self.assertEqual(pipe.get_base_status(), pipeA.get_base_status())
        self.assertEqual(pipe.get_base_status(), pipeB.get_base_status())

    def test_update_controls_for_leak(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/leak_test_network.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        import copy
        time_controls_1 = copy.deepcopy(wn.time_controls)
        conditional_controls_1 = copy.deepcopy(wn.conditional_controls)
        wn.add_leak('leak21','21',0.02)
        time_controls_2 = copy.deepcopy(wn.time_controls)
        conditional_controls_2 = copy.deepcopy(wn.conditional_controls)
        self.assertEqual(time_controls_1['21'], time_controls_2['21__A'])
        self.assertEqual(time_controls_1['21'], time_controls_2['21__B'])
        self.assertEqual(conditional_controls_1['21'], conditional_controls_2['21__A'])
        self.assertEqual(conditional_controls_1['21'], conditional_controls_2['21__B'])
        self.assertEqual(True, '21' in time_controls_1.keys())
        self.assertEqual(False, '21' in time_controls_2.keys())
        self.assertEqual(True, '21' in conditional_controls_1.keys())
        self.assertEqual(False, '21' in conditional_controls_2.keys())

    def test_update_controls_for_leak2(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/leak_test_network.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        import copy
        time_controls_1 = copy.deepcopy(wn.time_controls)
        conditional_controls_1 = copy.deepcopy(wn.conditional_controls)
        wn.add_leak('leak21','21',0.02, control_dest = 'START_NODE')
        time_controls_2 = copy.deepcopy(wn.time_controls)
        conditional_controls_2 = copy.deepcopy(wn.conditional_controls)
        self.assertEqual(time_controls_1['21'], time_controls_2['21__A'])
        self.assertEqual(False, '21__B' in time_controls_2.keys())
        self.assertEqual(conditional_controls_1['21'], conditional_controls_2['21__A'])
        self.assertEqual(False, '21__B' in conditional_controls_2.keys())
        self.assertEqual(True, '21' in time_controls_1.keys())
        self.assertEqual(False, '21' in time_controls_2.keys())
        self.assertEqual(True, '21' in conditional_controls_1.keys())
        self.assertEqual(False, '21' in conditional_controls_2.keys())

    def test_update_controls_for_leak3(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/leak_test_network.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        import copy
        time_controls_1 = copy.deepcopy(wn.time_controls)
        conditional_controls_1 = copy.deepcopy(wn.conditional_controls)
        wn.add_leak('leak21','21',0.02, control_dest = 'END_NODE')
        time_controls_2 = copy.deepcopy(wn.time_controls)
        conditional_controls_2 = copy.deepcopy(wn.conditional_controls)
        self.assertEqual(time_controls_1['21'], time_controls_2['21__B'])
        self.assertEqual(False, '21__A' in time_controls_2.keys())
        self.assertEqual(conditional_controls_1['21'], conditional_controls_2['21__B'])
        self.assertEqual(False, '21__A' in conditional_controls_2.keys())
        self.assertEqual(True, '21' in time_controls_1.keys())
        self.assertEqual(False, '21' in time_controls_2.keys())
        self.assertEqual(True, '21' in conditional_controls_1.keys())
        self.assertEqual(False, '21' in conditional_controls_2.keys())

    def test_update_controls_for_leak4(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/leak_test_network.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        import copy
        time_controls_1 = copy.deepcopy(wn.time_controls)
        conditional_controls_1 = copy.deepcopy(wn.conditional_controls)
        wn.add_leak('leak21', '21', 0.02, control_dest = 'REMOVE')
        time_controls_2 = copy.deepcopy(wn.time_controls)
        conditional_controls_2 = copy.deepcopy(wn.conditional_controls)
        self.assertEqual(False, '21__A' in time_controls_2.keys())
        self.assertEqual(False, '21__B' in time_controls_2.keys())
        self.assertEqual(False, '21__A' in conditional_controls_2.keys())
        self.assertEqual(False, '21__B' in conditional_controls_2.keys())
        self.assertEqual(True, '21' in time_controls_1.keys())
        self.assertEqual(False, '21' in time_controls_2.keys())
        self.assertEqual(True, '21' in conditional_controls_1.keys())
        self.assertEqual(False, '21' in conditional_controls_2.keys())

class TestLeakResults(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_leak_demand(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_2.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.add_leak('leak1','pipe2',leak_diameter = 0.01, leak_discharge_coeff = 0.75, start_time = '0 days 04:00:00', fix_time = '0 days 08:00:00')
        sim = self.wntr.sim.PyomoSimulator(wn, 'DEMAND DRIVEN')
        results = sim.run_sim()

        for t in results.node.loc['leak1'].index:
            if t.components.hours < 4 or t.components.hours >= 8:
                self.assertAlmostEqual(results.node.at[('leak1',t),'demand'], 0.0)
            else:
                self.assertAlmostEqual(results.node.at[('leak1',t),'demand'], 0.75*math.pi/4.0*0.01**2.0*math.sqrt(2*9.81*results.node.at[('leak1',t),'pressure']))

    def test_leak_against_epanet(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_13.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.add_leak('leak1','pipe2', leak_diameter = 0.08, leak_discharge_coeff = 0.75, start_time = '0 days 04:00:00', fix_time = '0 days 12:00:00')
        sim = self.wntr.sim.PyomoSimulator(wn, 'DEMAND DRIVEN')
        pyomo_results = sim.run_sim()

        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_13B.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        sim = self.wntr.sim.EpanetSimulator(wn)
        epanet_results = sim.run_sim()

        for link_name, link in wn.links():
            for t in pyomo_results.link.loc[link_name].index:
                self.assertLessEqual(abs(pyomo_results.link.at[(link_name,t),'flowrate'] - epanet_results.link.at[(link_name,t),'flowrate']), 0.00001)

        for link_name, link in wn.links():
            for t in pyomo_results.link.loc[link_name].index:
                self.assertLessEqual(abs(pyomo_results.link.at[(link_name,t),'velocity'] - epanet_results.link.at[(link_name,t),'velocity']), 0.0001)

        for node_name, node in wn.nodes():
            for t in pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(pyomo_results.node.at[(node_name,t),'demand'] - epanet_results.node.at[(node_name,t),'demand']), 0.00001)

        for node_name, node in wn.nodes():
            for t in pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(pyomo_results.node.at[(node_name,t),'expected_demand'] - epanet_results.node.at[(node_name,t),'expected_demand']), 0.00001)

        for node_name, node in wn.nodes():
            for t in pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(pyomo_results.node.at[(node_name,t),'head'] - epanet_results.node.at[(node_name,t),'head']), 0.001)

        for node_name, node in wn.nodes():
            for t in pyomo_results.node.loc[node_name].index:
                self.assertLessEqual(abs(pyomo_results.node.at[(node_name,t),'pressure'] - epanet_results.node.at[(node_name,t),'pressure']), 0.001)

    def test_remove_leak_results(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_13.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        sim = self.wntr.sim.PyomoSimulator(wn, 'DEMAND DRIVEN')
        results1 = sim.run_sim()
        wn.add_leak('leak1','pipe2', leak_diameter = 0.08, leak_discharge_coeff = 0.75, start_time = '0 days 04:00:00', fix_time = '0 days 12:00:00')
        wn.remove_leak('leak1')
        sim = self.wntr.sim.PyomoSimulator(wn, 'DEMAND DRIVEN')
        results2 = sim.run_sim()

        self.assertEqual(True, (results1.node == results2.node)['demand'].all())
        self.assertEqual(True, (results1.node == results2.node)['expected_demand'].all())
        self.assertEqual(True, (results1.node == results2.node)['head'].all())
        self.assertEqual(True, (results1.node == results2.node)['pressure'].all())
        self.assertEqual(True, (results1.node == results2.node)['type'].all())

        self.assertEqual(True, (results1.link == results2.link)['flowrate'].all())
        self.assertEqual(True, (results1.link == results2.link)['velocity'].all())
        self.assertEqual(True, (results1.link == results2.link)['type'].all())

