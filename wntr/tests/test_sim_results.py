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
 
    def test_convert_units_epanet(self):
        sim = wntr.sim.EpanetSimulator(self.wn)
        results_SI = sim.run_sim()
        
        results_convert_GPM = results_SI.convert_units(self.wn, 
                                                       self.wn.options.hydraulic.inpfile_units, 
                                                       "mg", #self.wn.options.quality.inpfile_units,
                                                       self.wn.options.quality.parameter)
        
        results_diff = abs(results_convert_GPM - self.results_GPM)

        for key in results_diff.node.keys():
            #wntr.graphics.plot_network(self.wn, node_attribute=results_diff.node[key].max(), link_width=0.5, title=key+' diff, test_convert_units_epanet')
            #print(key, results_diff.node[key].max().max())
            self.assertLess(results_diff.node[key].max().max(), self.tol['node'][key])
            
        for key in results_diff.link.keys():
            #wntr.graphics.plot_network(self.wn, link_attribute=results_diff.link[key].max(), link_width=2, node_size=0, title=key+' diff, test_convert_units_wntr')
            #print(key, results_diff.link[key].max().max())
            if key in ['status']: # status in WNTR is different than EPANET status
                continue
            self.assertLess(results_diff.link[key].max().max(), self.tol['link'][key])
    
    def test_convert_units_wntr(self):
        sim = wntr.sim.WNTRSimulator(self.wn)
        results_SI = sim.run_sim()
        
        results_convert_GPM = results_SI.convert_units(self.wn, 
                                                       self.wn.options.hydraulic.inpfile_units, 
                                                       "mg", #self.wn.options.quality.inpfile_units,
                                                       None)
        
        results_diff = abs(results_convert_GPM - self.results_GPM)

        for key in results_diff.node.keys():
            #wntr.graphics.plot_network(self.wn, node_attribute=results_diff.node[key].max(), link_width=0.5, title=key+' diff, test_convert_units_wntr')
            #print(key, results_diff.node[key].max().max())
            self.assertLess(results_diff.node[key].max().max(), self.tol['node'][key])
            
        for key in results_diff.link.keys():
            #wntr.graphics.plot_network(self.wn, link_attribute=results_diff.link[key].max(), link_width=2, node_size=0, title=key+' diff, test_convert_units_wntr')
            print(key, results_diff.link[key].loc[1::,:].max().max())
            if key in 'status': # status in WNTR is different than EPANET status
                continue
            # Some differences exist in the first hour
            self.assertLess(results_diff.link[key].loc[1::,:].max().max(), self.tol['link'][key])


if __name__ == "__main__":
    unittest.main()

