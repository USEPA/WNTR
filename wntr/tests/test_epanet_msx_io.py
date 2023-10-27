import unittest
import warnings
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr
import wntr.msx
import wntr.epanet.msx
import sympy

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
        true_vars = ["AS3", "AS5", "AS5s", "AStot", "Av", "D", "Ff", "K1", "K2", "Ka", "Kb", "Kc", "Ks", "Len", "NH2CL", "Q", "Re", "Smax", "U", "Us"]
        in_vars = msx_model.variable_name_list
        in_vars.sort()
        io_vars = msx_model2.variable_name_list
        io_vars.sort()
        self.assertListEqual(true_vars, in_vars)
        self.assertListEqual(true_vars, io_vars)

if __name__ == "__main__":
    unittest.main(verbosity=2)
