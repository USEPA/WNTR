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


class TestEpanetMSXSim(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        pass

    @classmethod
    def tearDownClass(self):
        pass

    def test_msx_sim(self):
        wn = wntr.network.WaterNetworkModel(inp_file_name=inp_filename)
        wn.add_msx_model(msx_filename=msx_filename)
        sim = wntr.sim.EpanetSimulator(wn)
        msx_model = wntr.msx.MsxModel(msx_file_name=msx_filename)
        
        # run sim
        res = sim.run_sim()
        
        # check results object keys
        for species in wn.msx.species_name_list:
            assert species in res.node.keys()
            assert species in res.link.keys()
            
        
        # sanity check at test point
        expected = 10.032905  # Node 'C' at time 136800 for AStot
        error = abs(
            (res.node["AStot"].loc[136800, "C"] - expected) / expected
        )
        self.assertLess(error, 0.0001)  # 0.01% error


if __name__ == "__main__":
    unittest.main(verbosity=2)
