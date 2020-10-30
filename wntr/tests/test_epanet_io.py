import unittest
import nose
from os.path import abspath, dirname, join
import sys

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, 'networks_for_testing')
ex_datadir = join(testdir,'..','..','examples','networks')

class TestWriter(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr

        inp_file = join(test_datadir, 'io.inp')
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.write_inpfile('temp.inp', 'GPM')
        self.wn2 = self.wntr.network.WaterNetworkModel('temp.inp')

    @classmethod
    def tearDownClass(self):
        pass

    def test_all(self):
        self.assertTrue(self.wn._compare(self.wn2))

    def test_pipe_minor_loss(self):
        p1 = self.wn2.get_link('p1')
        self.assertAlmostEqual(p1.minor_loss, 0.73, 6)

    def test_tcv_valve(self):
        v1 = self.wn2.get_link('v1')
        self.assertEqual(v1.start_node_name, 'j1')
        self.assertEqual(v1.end_node_name, 'j2')
        self.assertAlmostEqual(v1.diameter, 0.3048, 6)
        self.assertEqual(v1.valve_type, 'TCV')
        self.assertAlmostEqual(v1.setting, 3.52, 6)
        self.assertAlmostEqual(v1.minor_loss, 0.54, 6)

    def test_pump(self):
        p1 = self.wn2.get_link('pump1')
        p11 = self.wn.get_link('pump1')
        self.assertEqual(p1.start_node_name, 'j2')
        self.assertEqual(p1.end_node_name, 'j3')
        self.assertEqual(type(p1), self.wntr.network.elements.HeadPump)
        self.assertEqual(p1.pump_curve_name, 'curve1')
        self.assertAlmostEqual(p1.speed_timeseries.base_value, 1.2, 6)
        self.assertEqual(p1.speed_timeseries, p11.speed_timeseries)
        self.assertEqual(p1.speed_timeseries.pattern_name, 'pattern1')

        p2 = self.wn2.get_link('pump2')
        self.assertEqual(type(p2), self.wntr.network.elements.PowerPump)
        self.assertAlmostEqual(p2._base_power, 16629.107, 2)

    def test_valve_setting_control(self):
        control = self.wn2.get_control('control 1')
        run_time = control._condition._threshold
        self.assertAlmostEqual(run_time, 3600.0*3.4, 6)
        value = control.actions()[0]._value
        self.assertAlmostEqual(value, 0.82, 6)

        control = self.wn2.get_control('control 2')
        value = control.actions()[0]._value
        self.assertAlmostEqual(value, 1.8358, 3)

    def test_controls(self):
        for name, control in self.wn.controls():
            self.assertTrue(control._compare(self.wn2.get_control(name)))
        
    def test_demands(self):
        # In EPANET, the [DEMANDS] section overrides demands specified in [JUNCTIONS]
        expected_length = {'j1': 2, # DEMANDS duplicates demand in JUNCTIONS
                           'j2': 2, # DEMANDS does not duplicate demand in JUNCTIONS
                           'j3': 1, # Only in JUNCTIONS
                           'j4': 1} # Only in DEMANDS
        for j_name, j in self.wn.junctions():
            j2 = self.wn2.get_node(j_name)
            assert len(j.demand_timeseries_list) == len(j2.demand_timeseries_list)
            self.assertEqual(expected_length[j_name], len(j2.demand_timeseries_list))
            for d, d2 in zip(j.demand_timeseries_list, j2.demand_timeseries_list):
                self.assertEqual(d, d2)
                # DEMANDS use pattern2, JUNCTIONS demands use pattern1
                if j_name in ['j1', 'j2', 'j4']:    
                    self.assertEqual(d2.pattern_name, 'pattern2') 
                else:
                    self.assertEqual(d2.pattern_name, 'pattern1') 
                

class TestInpFileWriter(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr
        inp_file = join(test_datadir, 'Net6_plus.inp') # UNITS = GPM
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.write_inpfile('temp.inp', units='LPM')
        self.wn2 = self.wntr.network.WaterNetworkModel(inp_file)

    @classmethod
    def tearDownClass(self):
        pass

    def test_wn(self):
        self.assertTrue(self.wn._compare(self.wn2))

    def test_junctions(self):
        for name, node in self.wn.nodes(self.wntr.network.Junction):
            node2 = self.wn2.get_node(name)
            self.assertTrue(node._compare(node2))
            #self.assertAlmostEqual(node.base_demand, node2.base_demand, 5)

    def test_reservoirs(self):
        for name, node in self.wn.nodes(self.wntr.network.Reservoir):
            node2 = self.wn2.get_node(name)
            self.assertTrue(node._compare(node2))
            self.assertAlmostEqual(node.head_timeseries.base_value, node2.head_timeseries.base_value, 5)

    def test_tanks(self):
        for name, node in self.wn.nodes(self.wntr.network.Tank):
            node2 = self.wn2.get_node(name)
            self.assertTrue(node._compare(node2))
            self.assertAlmostEqual(node.init_level, node2.init_level, 5)

    def test_pipes(self):
        for name, link in self.wn.links(self.wntr.network.Pipe):
            link2 = self.wn2.get_link(name)
            self.assertTrue(link._compare(link2))
            self.assertEqual(link.initial_status, link2.initial_status)

    def test_pumps(self):
        for name, link in self.wn.links(self.wntr.network.Pump):
            link2 = self.wn2.get_link(name)
            self.assertTrue(link._compare(link2))

    def test_valves(self):
        for name, link in self.wn.links(self.wntr.network.Valve):
            link2 = self.wn2.get_link(name)
            self.assertTrue(link._compare(link2))
            self.assertAlmostEqual(link.setting, link2.setting, 5)

    def test_curves(self):
        pass

    def test_sources(self):
        for name, source in self.wn._sources.items():
            source2 = self.wn2._sources[name]
            self.assertEqual(source == source2, True)

    def test_demands(self):
        for j_name, j in self.wn.junctions():
            j2 = self.wn2.get_node(j_name)
            assert len(j.demand_timeseries_list) == len(j2.demand_timeseries_list)
            for d, d2 in zip(j.demand_timeseries_list, j2.demand_timeseries_list):
                self.assertEqual(d, d2)

    ### TODO
#    def test_controls(self):
#        for name1, control1 in self.wn.controls.items():
#            control2 = self.wn2._controls[name1]
#            self.assertEqual(control1 == control2, True)

    def test_options(self):
        options1 = self.wn.options
        options2 = self.wn2.options
        self.assertEqual(options1 == options2, True)

    def test_controls(self):
        for name, control in self.wn.controls():
            self.assertTrue(control._compare(self.wn2.get_control(name)))


class TestInp22FileWriter(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr
        inp_file = join(test_datadir, 'Net6_plus.inp') # UNITS = GPM
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.hydraulic.demand_model = 'PDA'
        self.wn.options.hydraulic.required_pressure = 1.0
        self.wn.write_inpfile('temp2.inp', units='LPM')
        self.wn2 = self.wntr.network.WaterNetworkModel('temp2.inp')

    @classmethod
    def tearDownClass(self):
        pass

    def test_pda(self):
        self.assertTrue(self.wn2.options.hydraulic.demand_model == 'PDA')
        self.assertTrue(self.wn.options.hydraulic.required_pressure == 1.0)


class TestNet3InpWriterResults(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr

        inp_file = join(ex_datadir, 'Net3.inp')
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)

        sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()

        self.wn.write_inpfile('temp.inp')
        self.wn2 = self.wntr.network.WaterNetworkModel('temp.inp')

        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.results2 = sim.run_sim()
        
        self.wn.write_inpfile('temp.inp')
        self.wn22 = self.wntr.network.WaterNetworkModel('temp.inp')
        self.wn22.options.hydraulic.demand_model = 'PDA'

        sim = self.wntr.sim.EpanetSimulator(self.wn22)
        self.results22 = sim.run_sim(version=2.2)
        

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.results2.link['flowrate'].index:
                self.assertLessEqual(abs(self.results2.link['flowrate'].loc[t,link_name] - self.results.link['flowrate'].loc[t,link_name]), 0.00001)
                self.assertLessEqual(abs(self.results22.link['flowrate'].loc[t,link_name] - self.results.link['flowrate'].loc[t,link_name]), 0.00001)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node['demand'].index:
                self.assertAlmostEqual(self.results2.node['demand'].loc[t,node_name], self.results.node['demand'].loc[t,node_name], 4)
                self.assertAlmostEqual(self.results22.node['demand'].loc[t,node_name], self.results.node['demand'].loc[t,node_name], 4)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node['head'].index:
                self.assertLessEqual(abs(self.results2.node['head'].loc[t,node_name] - self.results.node['head'].loc[t,node_name]), 0.01)
                self.assertLessEqual(abs(self.results22.node['head'].loc[t,node_name] - self.results.node['head'].loc[t,node_name]), 0.01)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node['pressure'].index:
                self.assertLessEqual(abs(self.results2.node['pressure'].loc[t,node_name] - self.results.node['pressure'].loc[t,node_name]), 0.05)
                self.assertLessEqual(abs(self.results22.node['pressure'].loc[t,node_name] - self.results.node['pressure'].loc[t,node_name]), 0.05)


class TestNet3InpUnitsResults(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr

        inp_file = join(ex_datadir, 'Net3.inp')
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)

        sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()

        self.wn.write_inpfile('temp.inp', units='CMH')
        self.wn2 = self.wntr.network.WaterNetworkModel('temp.inp')

        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.results2 = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate_units_convert(self):
        for link_name, link in self.wn.links():
            for t in self.results2.link['flowrate'].index:
                self.assertLessEqual(abs(self.results2.link['flowrate'].loc[t,link_name] - self.results.link['flowrate'].loc[t,link_name]), 0.00001)

if __name__ == '__main__':
    unittest.main()