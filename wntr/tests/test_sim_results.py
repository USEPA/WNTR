import unittest
from os.path import abspath, dirname, join
#import matplotlib.pylab as plt
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "..", "..", "examples", "networks")

def get_min_max(results):
    results_min = wntr.sim.SimulationResults()
    results_min.link = dict()
    results_min.node = dict()
    results_min.network_name = "-{}[{}]".format(
        results.network_name, results.timestamp)
    
    results_max = wntr.sim.SimulationResults()
    results_max.link = dict()
    results_max.node = dict()
    results_max.network_name = "-{}[{}]".format(
        results.network_name, results.timestamp)
    
    for key in results.link.keys():
        results_min.link[key] = results.link[key].min().min()
        results_max.link[key] = results.link[key].max().max()
    for key in results.node.keys():
        results_min.node[key] = results.node[key].min().min()
        results_max.node[key] = results.node[key].max().max()
        
    return results_min, results_max
    

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
        
        results_min, results_max = get_min_max(results_GPM)
        results_GPM_norm = (results_GPM - results_min)/results_max
        
        self.results_GPM_norm = results_GPM_norm
        
        self.tol = 0.0001 
        
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
        
        results_min, results_max = get_min_max(results_convert_GPM)
        results_convert_GPM_norm = (results_convert_GPM - results_min)/results_max
        
        results_diff = abs(results_convert_GPM_norm - self.results_GPM_norm)

        for key in results_diff.node.keys():
            #print(key, results_diff.node[key].max().max())
            #wntr.graphics.plot_network(self.wn, node_attribute=results_diff.node[key].max(), link_width=0.5, title=key+' diff, test_convert_units_epanet')
            self.assertLess(results_diff.node[key].max().max(), self.tol)
            
        for key in results_diff.link.keys():
            #wntr.graphics.plot_network(self.wn, link_attribute=results_diff.link[key].max(), link_width=2, node_size=0, title=key+' diff, test_convert_units_wntr')
            #print(key, results_diff.link[key].max().max())
            if key in ['status', 'reaction_rate']: # reaction rate is contant (normalized values are nan), status is different than epanet status
                continue
            self.assertLess(results_diff.link[key].max().max(), self.tol)
    
    
    
            
    def test_convert_units_wntr(self):
        sim = wntr.sim.WNTRSimulator(self.wn)
        results_SI = sim.run_sim()
        
        results_convert_GPM = results_SI.convert_units(self.wn, 
                                                       self.wn.options.hydraulic.inpfile_units, 
                                                       "mg", #self.wn.options.quality.inpfile_units,
                                                       None)
        
        results_min, results_max = get_min_max(results_convert_GPM)
        results_convert_GPM_norm = (results_convert_GPM - results_min)/results_max
        
        results_diff = abs(results_convert_GPM_norm - self.results_GPM_norm)

        for key in results_diff.node.keys():
            #wntr.graphics.plot_network(self.wn, node_attribute=results_diff.node[key].max(), link_width=0.5, title=key+' diff, test_convert_units_wntr')
            #print(key, results_diff.node[key].max().max())
            self.assertLess(results_diff.node[key].max().max(), self.tol)
            
        for key in results_diff.link.keys():
            #wntr.graphics.plot_network(self.wn, link_attribute=results_diff.link[key].max(), link_width=2, node_size=0, title=key+' diff, test_convert_units_wntr')
            #print(key, results_diff.link[key].loc[1::,:].max().max())
            if key in 'status': 
                continue
            # Some differences exist in the first hour
            self.assertLess(results_diff.link[key].loc[1::,:].max().max(), self.tol)


if __name__ == "__main__":
    unittest.main()

