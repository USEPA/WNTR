import unittest
from os.path import abspath, dirname, join
#import matplotlib.pylab as plt
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "..", "..", "examples", "networks")

class TestSimulationResults(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        inp_file = join(datadir, "Net2.inp")
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.EpanetSimulator(self.wn)
        sim.run_sim()
        
        binfile = wntr.epanet.io.BinFile()
        results_GPM = binfile.read('temp.bin', False, False, False)
        # time index needs to be converted to hours
        for key in results_GPM.node.keys():
            results_GPM.node[key].index = results_GPM.node[key].index/3600
        for key in results_GPM.link.keys():
            results_GPM.link[key].index = results_GPM.link[key].index/3600

        self.results_GPM = results_GPM
        
        self.tol = {}
        self.tol['node'] = {}
        self.tol['node']['demand'] = 1e-3
        self.tol['node']['head'] = 1e-3
        self.tol['node']['pressure'] = 1e-3
        self.tol['node']['quality'] = 1e-3
        self.tol['link'] = {}
        self.tol['link']['flowrate'] = 1e-2
        self.tol['link']['velocity'] = 1e-3
        self.tol['link']['headloss'] = 1e-3
        self.tol['link']['status'] = None # status is not checked.
        self.tol['link']['setting'] = 1e-5
        self.tol['link']['friction_factor'] = 1e-5
        self.tol['link']['quality'] = 1e-5
        self.tol['link']['reaction_rate'] = 1e-3

    @classmethod
    def tearDownClass(self):
        pass
 


if __name__ == "__main__":
    unittest.main()

