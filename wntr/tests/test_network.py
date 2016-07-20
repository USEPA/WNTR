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
import copy
import numpy as np
from scipy.optimize import fsolve

class TestNetworkCreation(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/examples/networks/Net6.inp'
        self.wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_num_junctions(self):
        self.assertEqual(self.wn._num_junctions, 3323)

    def test_num_reservoirs(self):
        self.assertEqual(self.wn._num_reservoirs, 1)

    def test_num_tanks(self):
        self.assertEqual(self.wn._num_tanks, 34)

    def test_num_pipes(self):
        self.assertEqual(self.wn._num_pipes, 3829)

    def test_num_pumps(self):
        self.assertEqual(self.wn._num_pumps, 61)

    def test_num_valves(self):
        self.assertEqual(self.wn._num_valves, 2)

    def test_num_nodes(self):
        self.assertEqual(self.wn.num_nodes(), 3323+1+34)

    def test_num_links(self):
        self.assertEqual(self.wn.num_links(), 3829+61+2)

    def test_junction_attr(self):
        j = self.wn.get_node('JUNCTION-18')
        self.assertAlmostEqual(j.base_demand, 48.56/60.0*0.003785411784)
        self.assertEqual(j.demand_pattern_name, 'PATTERN-2')
        self.assertAlmostEqual(j.elevation, 80.0*0.3048)

    def test_reservoir_attr(self):
        j = self.wn.get_node('RESERVOIR-3323')
        self.assertAlmostEqual(j.base_head, 27.45*0.3048)
        self.assertEqual(j.head_pattern_name, None)

class TestNetworkMethods(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        from wntr.network.WaterNetworkModel import Junction, Tank, Reservoir, Pipe, Pump, Valve
        from wntr.network.NetworkControls import ControlAction, TimeControl
        self.Junction = Junction
        self.Tank = Tank
        self.Reservoir = Reservoir
        self.Pipe = Pipe
        self.Pump = Pump
        self.Valve = Valve
        self.wntr = wntr
        self.ControlAction = ControlAction
        self.TimeControl = TimeControl

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_add_junction(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1', 150, 'pattern1', 15)
        j = wn.get_node('j1')
        self.assertEqual(j._name, 'j1')
        self.assertEqual(j.base_demand, 150.0)
        self.assertEqual(j.demand_pattern_name, 'pattern1')
        self.assertEqual(j.elevation, 15.0)
        self.assertEqual(wn._graph.nodes(),['j1'])
        self.assertEqual(type(j.base_demand), float)
        self.assertEqual(type(j.elevation), float)

    def test_add_tank(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_tank('t1', 15, 75, 0, 100, 10, 0)
        n = wn.get_node('t1')
        self.assertEqual(n._name, 't1')
        self.assertEqual(n.elevation, 15.0)
        self.assertEqual(n.init_level, 75.0)
        self.assertEqual(n.min_level, 0.0)
        self.assertEqual(n.max_level, 100.0)
        self.assertEqual(n.diameter, 10.0)
        self.assertEqual(n.min_vol, 0.0)
        self.assertEqual(wn._graph.nodes(),['t1'])
        self.assertEqual(type(n.elevation), float)
        self.assertEqual(type(n.init_level), float)
        self.assertEqual(type(n.min_level), float)
        self.assertEqual(type(n.max_level), float)
        self.assertEqual(type(n.diameter), float)
        self.assertEqual(type(n.min_vol), float)

    def test_add_reservoir(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_reservoir('r1', 30, 'pattern1')
        n = wn.get_node('r1')
        self.assertEqual(n._name, 'r1')
        self.assertEqual(n.base_head, 30.0)
        self.assertEqual(n.head_pattern_name, 'pattern1')
        self.assertEqual(wn._graph.nodes(),['r1'])
        self.assertEqual(type(n.base_head), float)

    def test_add_pipe(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_pipe('p1', 'j1', 'j2', 1000, 1, 100, 0, 'Open')
        l = wn.get_link('p1')
        self.assertEqual(l._link_name, 'p1')
        self.assertEqual(l.start_node(), 'j1')
        self.assertEqual(l.end_node(), 'j2')
        self.assertEqual(l.get_base_status(), self.wntr.network.LinkStatus.opened)
        self.assertEqual(l.length, 1000.0)
        self.assertEqual(l.diameter, 1.0)
        self.assertEqual(l.roughness, 100.0)
        self.assertEqual(l.minor_loss, 0.0)
        self.assertEqual(wn._graph.edges(), [('j1','j2')])
        self.assertEqual(type(l.length), float)
        self.assertEqual(type(l.diameter), float)
        self.assertEqual(type(l.roughness), float)
        self.assertEqual(type(l.minor_loss), float)

    def test_add_pipe_with_cv(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_pipe('p1', 'j1', 'j2', 1000, 1, 100, 0, 'OPEN', True)
        self.assertEqual(wn._check_valves, ['p1'])

    def test_remove_pipe(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_junction('j3')
        wn.add_pipe('p2','j1','j3')
        wn.add_pipe('p1','j1','j2', status = 'cv')
        wn.remove_link('p1')
        link_list = [link_name for link_name, link in wn.links()]
        self.assertEqual(link_list, ['p2'])
        self.assertEqual(wn._check_valves,[])
        self.assertEqual(wn._num_pipes, 1)
        self.assertEqual(wn._graph.edges(), [('j1','j3')])

    def test_remove_node(self):
        inp_file = resilienceMainDir+'/examples/networks/Net6.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)

        wn.remove_node('TANK-3326')
        
        self.assertNotIn('TANK-3326',wn._nodes.keys())
        self.assertNotIn('TANK-3326',wn._graph.nodes())

        
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/conditional_controls_1.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)

        tank1 = wn.get_node('tank1')
        action = self.ControlAction(tank1, 'elevation', 55)
        control = self.TimeControl(wn, 3652, 'SIM_TIME', False, action)
        wn.add_control('tank_control', control)

        controls_1 = copy.deepcopy(wn._control_dict)
        
        wn.remove_node('tank1')

        controls_2 = copy.deepcopy(wn._control_dict)

        self.assertEqual(True, 'tank_control' in controls_1.keys())
        self.assertEqual(False, 'tank_control' in controls_2.keys())
        
        self.assertNotIn('tank1',wn._nodes.keys())
        self.assertNotIn('tank1',wn._graph.nodes())
        node_list = ['junction1','res1']
        node_list.sort()
        node_list_2 = wn._nodes.keys()
        node_list_2.sort()
        self.assertEqual(node_list, node_list_2)

    def test_remove_controls_for_removing_link(self):
        inp_file = resilienceMainDir+'/examples/networks/Net1.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        
        control_action = self.wntr.network.ControlAction(wn.get_link('21'), 'status', self.wntr.network.LinkStatus.opened)
        control = self.wntr.network.ConditionalControl((wn.get_node('2'),'head'), np.greater, 10.0, control_action)
        wn.add_control('control_1',control)
        
        import copy
        controls_1 = copy.deepcopy(wn._control_dict)
        
        wn.remove_link('21')

        controls_2 = copy.deepcopy(wn._control_dict)
        self.assertEqual(True, 'control_1' in controls_1.keys())
        self.assertEqual(False, 'control_1' in controls_2.keys())

    def test_nodes(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_tank('t1')
        wn.add_reservoir('r1')
        wn.add_reservoir('r2')
        wn.add_junction('j3')
        node_list = [name for name,node in wn.nodes()]
        node_list.sort()
        junction_list = [name for name, junction in wn.nodes(self.Junction)]
        junction_list.sort()
        tank_list = [name for name, tank in wn.nodes(self.Tank)]
        tank_list.sort()
        reservoir_list = [name for name, reservoir in wn.nodes(self.Reservoir)]
        reservoir_list.sort()
        self.assertEqual(node_list,['j1','j2','j3','r1','r2','t1'])
        self.assertEqual(junction_list,['j1','j2','j3'])
        self.assertEqual(tank_list,['t1'])
        self.assertEqual(reservoir_list,['r1','r2'])
        for name,node in wn.nodes():
            self.assertEqual(name, node._name)

    def test_links(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_tank('t1')
        wn.add_reservoir('r1')
        wn.add_reservoir('r2')
        wn.add_junction('j3')
        wn.add_pipe('p1','j1','j2')
        wn.add_pipe('p2','j1','t1')
        wn.add_pipe('p3','r1','j1')
        wn.add_pump('pump1','r2','t2')
        wn.add_valve('v1','t1','j2')
        link_list = [name for name,link in wn.links()]
        link_list.sort()
        self.assertEqual(link_list,['p1','p2','p3','pump1','v1'])
        pipe_list = [name for name,pipe in wn.links(self.Pipe)]
        pipe_list.sort()
        self.assertEqual(pipe_list,['p1','p2','p3'])
        pump_list = [name for name,pump in wn.links(self.Pump)]
        pump_list.sort()
        self.assertEqual(pump_list,['pump1'])
        valve_list = [name for name,valve in wn.links(self.Valve)]
        valve_list.sort()
        self.assertEqual(valve_list,['v1'])
        for name,link in wn.links():
            self.assertEqual(name, link._link_name)

    def test_1_pt_head_curve(self):
        q2 = 10.0
        h2 = 20.0
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_curve('curve1','HEAD',[(q2, h2)])
        curve = wn.get_curve('curve1')
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_pump('p1', 'j1', 'j2', 'HEAD', curve)
        link = wn.get_link('p1')
        a,b,c = link.get_head_curve_coefficients()
        q1 = 0.0
        h1 = 4.0/3.0*h2
        q3 = 2.0*q2
        h3 = 0.0

        def curve_fun(x):
            f=[1.0,1.0,1.0]
            f[0] = h1 - x[0] + x[1]*q1**x[2]
            f[1] = h2 - x[0] + x[1]*q2**x[2]
            f[2] = h3 - x[0] + x[1]*q3**x[2]
            return f

        X = [a,b,c]
        Y = curve_fun(X)

        self.assertAlmostEqual(Y[0],0.0)
        self.assertAlmostEqual(Y[1],0.0)
        self.assertAlmostEqual(Y[2],0.0)

    def test_3_pt_head_curve(self):
        q1 = 0.0
        h1 = 35.0
        q2 = 10.0
        h2 = 20.0
        q3 = 18.0
        h3 = 2.0
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_curve('curve1','HEAD',[(q1, h1),(q2,h2),(q3,h3)])
        curve = wn.get_curve('curve1')
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_pump('p1', 'j1', 'j2', 'HEAD', curve)
        link = wn.get_link('p1')
        a,b,c = link.get_head_curve_coefficients()

        def curve_fun(x):
            f=[1.0,1.0,1.0]
            f[0] = h1 - x[0] + x[1]*q1**x[2]
            f[1] = h2 - x[0] + x[1]*q2**x[2]
            f[2] = h3 - x[0] + x[1]*q3**x[2]
            return f

        X = [a,b,c]
        Y = curve_fun(X)

        self.assertAlmostEqual(Y[0],0.0)
        self.assertAlmostEqual(Y[1],0.0)
        self.assertAlmostEqual(Y[2],0.0)

    def test_get_links_for_node_all(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_junction('j3')
        wn.add_junction('j4')
        wn.add_junction('j5')
        wn.add_pipe('p1','j1','j2')
        wn.add_pipe('p2','j1','j4')
        wn.add_pipe('p3','j1','j5')
        wn.add_pipe('p4','j3','j2')
        wn.add_pipe('p5','j4','j3')
        l1 = wn.get_links_for_node('j1')
        l2 = wn.get_links_for_node('j2','all')
        l3 = wn.get_links_for_node('j3','all')
        l4 = wn.get_links_for_node('j4')
        l5 = wn.get_links_for_node('j5')
        l1.sort()
        l2.sort()
        l3.sort()
        l4.sort()
        l5.sort()
        self.assertEqual(l1,['p1','p2','p3'])
        self.assertEqual(l2,['p1','p4'])
        self.assertEqual(l3,['p4','p5'])
        self.assertEqual(l4,['p2','p5'])
        self.assertEqual(l5,['p3'])

    def test_get_links_for_node_in(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_junction('j3')
        wn.add_junction('j4')
        wn.add_junction('j5')
        wn.add_pipe('p1','j1','j2')
        wn.add_pipe('p2','j1','j4')
        wn.add_pipe('p3','j1','j5')
        wn.add_pipe('p4','j3','j2')
        wn.add_pipe('p5','j4','j3')
        l1 = wn.get_links_for_node('j1','inlet')
        l2 = wn.get_links_for_node('j2','inlet')
        l3 = wn.get_links_for_node('j3','inlet')
        l4 = wn.get_links_for_node('j4','inlet')
        l5 = wn.get_links_for_node('j5','inlet')
        l1.sort()
        l2.sort()
        l3.sort()
        l4.sort()
        l5.sort()
        self.assertEqual(l1,[])
        self.assertEqual(l2,['p1','p4'])
        self.assertEqual(l3,['p5'])
        self.assertEqual(l4,['p2'])
        self.assertEqual(l5,['p3'])

    def test_get_links_for_node_out(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_junction('j3')
        wn.add_junction('j4')
        wn.add_junction('j5')
        wn.add_pipe('p1','j1','j2')
        wn.add_pipe('p2','j1','j4')
        wn.add_pipe('p3','j1','j5')
        wn.add_pipe('p4','j3','j2')
        wn.add_pipe('p5','j4','j3')
        l1 = wn.get_links_for_node('j1','outlet')
        l2 = wn.get_links_for_node('j2','outlet')
        l3 = wn.get_links_for_node('j3','outlet')
        l4 = wn.get_links_for_node('j4','outlet')
        l5 = wn.get_links_for_node('j5','outlet')
        l1.sort()
        l2.sort()
        l3.sort()
        l4.sort()
        l5.sort()
        self.assertEqual(l1,['p1','p2','p3'])
        self.assertEqual(l2,[])
        self.assertEqual(l3,['p4'])
        self.assertEqual(l4,['p5'])
        self.assertEqual(l5,[])

class TestInpFileWriter(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr
        inp_file = resilienceMainDir+'/examples/networks/Net6.inp'
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.write_inpfile('tmp.inp')
        self.wn2 = wntr.network.WaterNetworkModel('tmp.inp')

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_wn(self):
        self.assertEqual(self.wn == self.wn2, True)

    def test_junctions(self):
        for name, node in self.wn.nodes(self.wntr.network.Junction):
            node2 = self.wn2.get_node(name)
            self.assertEqual(node == node2, True)
            self.assertAlmostEqual(node.base_demand, node2.base_demand, 5)

    def test_reservoirs(self):
        for name, node in self.wn.nodes(self.wntr.network.Reservoir):
            node2 = self.wn2.get_node(name)
            self.assertEqual(node == node2, True)
            self.assertAlmostEqual(node.base_head, node2.base_head, 5)

    def test_tanks(self):
        for name, node in self.wn.nodes(self.wntr.network.Tank):
            node2 = self.wn2.get_node(name)
            self.assertEqual(node == node2, True)
            self.assertAlmostEqual(node.init_level, node2.init_level, 5)

    def test_pipes(self):
        for name, link in self.wn.links(self.wntr.network.Pipe):
            link2 = self.wn2.get_link(name)
            self.assertEqual(link == link2, True)
            self.assertEqual(link.get_base_status(), link2.get_base_status())

    def test_pumps(self):
        for name, link in self.wn.links(self.wntr.network.Pump):
            link2 = self.wn2.get_link(name)
            self.assertEqual(link == link2, True)
            if link.info_type=='POWER':
                self.assertAlmostEqual(link.power, link2.power, 5)
            elif link.info_type=='HEAD':
                A,B,C = link.get_head_curve_coefficients()
                A2,B2,C2 = link2.get_head_curve_coefficients()
                self.assertAlmostEqual(A,A2,5)
                self.assertLessEqual(abs(B-B2),6.0)
                self.assertLessEqual(abs(B-B2)/B,0.00001)
                self.assertAlmostEqual(C,C2,5)

    def test_valves(self):
        for name, link in self.wn.links(self.wntr.network.Valve):
            link2 = self.wn2.get_link(name)
            self.assertEqual(link == link2, True)
            self.assertAlmostEqual(link.setting, link2.setting, 5)

    def test_user_controls(self):
        for name1, control1 in self.wn._control_dict.iteritems():
            control2 = self.wn2._control_dict[name1]
            self.assertEqual(control1==control2, True)

class TestNet3InpWriterResults(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/examples/networks/Net3.inp'
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        
        sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()
        
        self.wn.write_inpfile('tmp.inp')
        self.wn2 = self.wntr.network.WaterNetworkModel('tmp.inp')

        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.results2 = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.results2.link.major_axis:
                self.assertLessEqual(abs(self.results2.link.at['flowrate',t,link_name] - self.results.link.at['flowrate',t,link_name]), 0.00001)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node.major_axis:
                self.assertAlmostEqual(self.results2.node.at['demand',t,node_name], self.results.node.at['demand',t,node_name], 4)

    def test_node_expected_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node.major_axis:
                self.assertAlmostEqual(self.results2.node.at['expected_demand',t,node_name], self.results.node.at['expected_demand',t,node_name], 4)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node.major_axis:
                self.assertLessEqual(abs(self.results2.node.at['head',t,node_name] - self.results.node.at['head',t,node_name]), 0.01)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node.major_axis:
                self.assertLessEqual(abs(self.results2.node.at['pressure',t,node_name] - self.results.node.at['pressure',t,node_name]), 0.05)


if __name__ == '__main__':
    unittest.main()
