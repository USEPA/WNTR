import unittest
import warnings
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr
import wntr.msx
import wntr.epanet.msx
import wntr.epanet.msx.toolkit

testdir = dirname(abspath(str(__file__)))
test_network_dir = join(testdir, "networks_for_testing")
inp_filename = join(test_network_dir, 'msx_example.inp')
msx_filename = join(test_network_dir, 'msx_example.msx')

class Test(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        pass

    @classmethod
    def tearDownClass(self):
        pass

    def test_msx_io(self):
        wn_model = wntr.network.WaterNetworkModel(inp_file_name=inp_filename)
        msx_model = wntr.msx.MsxModel(msx_file_name=msx_filename)
        wntr.epanet.msx.toolkit.MSXepanet(inp_filename, msxfile=msx_filename)
        


if __name__ == "__main__":
    unittest.main(verbosity=2)
