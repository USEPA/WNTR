import unittest
from os.path import abspath, dirname, join

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, 'networks_for_testing')


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
        self.assertEqual(v1.start_node, 'j1')
        self.assertEqual(v1.end_node, 'j2')
        self.assertAlmostEqual(v1.diameter, 0.3048, 6)
        self.assertEqual(v1.valve_type, 'TCV')
        self.assertAlmostEqual(v1.setting, 3.52, 6)
        self.assertAlmostEqual(v1.minor_loss, 0.54, 6)

    def test_pump(self):
        p1 = self.wn2.get_link('pump1')
        p11 = self.wn.get_link('pump1')
        self.assertEqual(p1.start_node, 'j2')
        self.assertEqual(p1.end_node, 'j3')
        self.assertEqual(p1.info_type, 'HEAD')
        self.assertEqual(p1.curve, p11.curve)
        self.assertEqual(p1.curve_name, 'curve1')
        self.assertAlmostEqual(p1.base_speed, 1.2, 6)
        self.assertEqual(p1.expected_speed, p11.expected_speed)
        self.assertEqual(p1.expected_speed.pattern_name, 'pattern1')

        p2 = self.wn2.get_link('pump2')
        self.assertEqual(p2.info_type, 'POWER')
        self.assertAlmostEqual(p2._base_power, 16629.107, 2)

    def test_valve_setting_control(self):
        control = self.wn2.get_control('LINKv10.82ATTIME12240')
        run_time = control._run_at_time
        self.assertAlmostEqual(run_time, 3600.0*3.4, 6)
        value = control._control_action._value
        self.assertAlmostEqual(value, 0.82, 6)

        control = self.wn2.get_control('LINKv22.61IFNODET1BELOW1.53')
        value = control._control_action._value
        self.assertAlmostEqual(value, 1.83548, 4)
