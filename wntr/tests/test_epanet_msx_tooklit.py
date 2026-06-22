import unittest
import warnings
from os.path import join

import numpy as np
import pandas as pd
import wntr
import wntr.msx
import wntr.epanet.msx
import wntr.epanet.msx.toolkit

from wntr.tests.conftest import (
    NETWORKS_FOR_TESTING_DIR as test_network_dir,
)
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
