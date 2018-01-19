import unittest
from os.path import abspath, dirname, join

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
        self.wn.write_inpfile('_io_copy.inp', 'GPM')
        self.wn2 = self.wntr.network.WaterNetworkModel('_io_copy.inp')

    @classmethod
    def tearDownClass(self):
        pass

    def test_all(self):
        self.assertEqual(self.wn, self.wn2)

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
        run_time = control._run_at_time
        self.assertAlmostEqual(run_time, 3600.0*3.4, 6)
        value = control._control_action._value
        self.assertAlmostEqual(value, 0.82, 6)

        control = self.wn2.get_control('control 2')
        value = control._control_action._value
        self.assertAlmostEqual(value, 1.83548, 4)

class TestInpFileWriter(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr
        inp_file = join(test_datadir, 'Net6_plus.inp') # UNITS = GPM
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.write_inpfile('tmp.inp', units='LPM')
        self.wn2 = self.wntr.network.WaterNetworkModel(inp_file)

    @classmethod
    def tearDownClass(self):
        pass

    def test_wn(self):
        self.assertEqual(self.wn == self.wn2, True)

    def test_junctions(self):
        for name, node in self.wn.nodes(self.wntr.network.Junction):
            node2 = self.wn2.get_node(name)
            self.assertEqual(node == node2, True)
            #self.assertAlmostEqual(node.base_demand, node2.base_demand, 5)

    def test_reservoirs(self):
        for name, node in self.wn.nodes(self.wntr.network.Reservoir):
            node2 = self.wn2.get_node(name)
            self.assertEqual(node == node2, True)
            self.assertAlmostEqual(node.head_timeseries.base_value, node2.head_timeseries.base_value, 5)

    def test_tanks(self):
        for name, node in self.wn.nodes(self.wntr.network.Tank):
            node2 = self.wn2.get_node(name)
            self.assertEqual(node == node2, True)
            self.assertAlmostEqual(node.init_level, node2.init_level, 5)

    def test_pipes(self):
        for name, link in self.wn.links(self.wntr.network.Pipe):
            link2 = self.wn2.get_link(name)
            self.assertEqual(link == link2, True)
            self.assertEqual(link.initial_status, link2.initial_status)

    def test_pumps(self):
        for name, link in self.wn.links(self.wntr.network.Pump):
            link2 = self.wn2.get_link(name)
            self.assertEqual(link == link2, True)

    def test_valves(self):
        for name, link in self.wn.links(self.wntr.network.Valve):
            link2 = self.wn2.get_link(name)
            self.assertEqual(link == link2, True)
            self.assertAlmostEqual(link.setting, link2.setting, 5)

    def test_curves(self):
        pass

    def test_sources(self):
        for name, source in self.wn._sources.items():
            source2 = self.wn2._sources[name]
            self.assertEqual(source == source2, True)

    def test_demands(self):
        for name, demand in self.wn._demands.items():
            demand2 = self.wn2._demands[name]
            self.assertEqual(demand == demand2, True)

    ### TODO
#    def test_controls(self):
#        for name1, control1 in self.wn.controls.items():
#            control2 = self.wn2._controls[name1]
#            self.assertEqual(control1 == control2, True)

    def test_options(self):
        options1 = self.wn.options
        options2 = self.wn2.options
        self.assertEqual(options1 == options2, True)

class TestNet3InpWriterResults(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr

        inp_file = join(ex_datadir, 'Net3.inp')
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)

        sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()

        self.wn.write_inpfile('tmp.inp')
        self.wn2 = self.wntr.network.WaterNetworkModel('tmp.inp')

        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.results2 = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.results2.time:
                self.assertLessEqual(abs(self.results2.link['flowrate'].loc[t,link_name] - self.results.link['flowrate'].loc[t,link_name]), 0.00001)

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.time:
                self.assertAlmostEqual(self.results2.node['demand'].loc[t,node_name], self.results.node['demand'].loc[t,node_name], 4)

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.time:
                self.assertLessEqual(abs(self.results2.node['head'].loc[t,node_name] - self.results.node['head'].loc[t,node_name]), 0.01)

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.time:
                self.assertLessEqual(abs(self.results2.node['pressure'].loc[t,node_name] - self.results.node['pressure'].loc[t,node_name]), 0.05)


class TestNet3InpUnitsResults(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr

        inp_file = join(ex_datadir, 'Net3.inp')
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)

        sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()

        self.wn.write_inpfile('tmp_units.inp', units='CMH')
        self.wn2 = self.wntr.network.WaterNetworkModel('tmp_units.inp')

        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.results2 = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate_units_convert(self):
        for link_name, link in self.wn.links():
            for t in self.results2.time:
                self.assertLessEqual(abs(self.results2.link['flowrate'].loc[t,link_name] - self.results.link['flowrate'].loc[t,link_name]), 0.00001)
