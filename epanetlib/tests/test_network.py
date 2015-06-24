import unittest
import sys
sys.path.append('../../')
import epanetlib as en

class TestNetworkCreation(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        inp_file = 'networks_for_testing/Net6_mod.inp'
        self.wn = en.network.WaterNetworkModel()
        parser = en.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)

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

    def test_junction_attr(self):
        j = self.wn.get_node('JUNCTION-18')
        self.assertAlmostEqual(j.base_demand, 48.56/60.0*0.003785411784)
        self.assertEqual(j.demand_pattern_name, 'PATTERN-2')
        self.assertAlmostEqual(j.elevation, 80.0*0.3048)

    def test_reservoir_attr(self):
        j = self.wn.get_node('RESERVOIR-3323')
        self.assertAlmostEqual(j.base_head, 27.45*0.3048)
        self.assertEqual(j.head_pattern_name, None)

if __name__ == '__main__':
    unittest.main()
