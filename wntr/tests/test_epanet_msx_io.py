import unittest
import warnings
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr
import wntr.msx
import wntr.epanet.msx

testdir = dirname(abspath(str(__file__)))
test_network_dir = join(testdir, "networks_for_testing")
inp_filename = join(test_network_dir, "msx_example.inp")
msx_filename = join(test_network_dir, "msx_example.msx")


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
        wntr.epanet.InpFile().write("test.inp", wn_model)
        wntr.epanet.msx.MsxFile().write("test.msx", msx_model)
        msx_model2 = wntr.msx.MsxModel(msx_file_name="test.msx")
        true_vars = ["AS3", "AS5", "AS5s", "AStot", "NH2CL", "Ka", "Kb", "K1", "K2", "Smax", "Ks"]
        true_vars.sort()
        in_vars = msx_model.species_name_list + msx_model.constant_name_list + msx_model.parameter_name_list + msx_model.term_name_list
        in_vars.sort()
        io_vars = msx_model2.species_name_list + msx_model2.constant_name_list + msx_model2.parameter_name_list + msx_model2.term_name_list
        io_vars.sort()
        self.assertListEqual(true_vars, in_vars)
        self.assertListEqual(true_vars, io_vars)

if __name__ == "__main__":
    unittest.main(verbosity=2)
