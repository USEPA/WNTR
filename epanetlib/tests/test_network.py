import unittest
import sys
sys.path.append('../../')
import epanetlib as en

class TestNetworkCreation(unittest.TestCase):

    def setUp(self):
        inp_file = 'networks_for_testing/net_test_1.inp'
        self.wn = en.network.WaterNetworkModel()
        parser = en.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)

    def test_num_junctions(self):
        self.assertEqual(self.wn._num_junctions, 2)

    def test_num_reservoirs(self):
        self.assertEqual(self.wn._num_reservoirs, 1)

if __name__ == '__main__':
    unittest.main()
