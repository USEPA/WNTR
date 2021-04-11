import unittest
from os.path import abspath, dirname, join

import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "..", "..", "examples", "networks")


class TestSimulationResults(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        inp_file = join(datadir, "Net3.inp")
        self.wn = wntr.network.WaterNetworkModel(inp_file)
    
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_convert_units_epanet(self):
        sim = wntr.sim.EpanetSimulator(self.wn)
        results = sim.run_sim()
        
        results_GPM = results.convert_units(self.wn, 'GPM')
        results_LPS = results.convert_units(self.wn, 'LPS')
    
    def test_convert_units_wntr(self):
        sim = wntr.sim.WNTRSimulator(self.wn)
        results = sim.run_sim()
        raise unittest.SkipTest('headloss not yet implemented in WNTR results')
        results_GPM = results.convert_units(self.wn, 'GPM')
        results_LPS = results.convert_units(self.wn, 'LPS')

if __name__ == "__main__":
    unittest.main()

