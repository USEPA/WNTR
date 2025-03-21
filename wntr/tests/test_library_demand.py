import unittest
from pandas.testing import assert_series_equal
import os
from os.path import abspath, dirname, join, isfile
import numpy as np
import pandas as pd
import matplotlib.pylab as plt

import wntr
from wntr.library import DemandPatternLibrary

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

plt.close('all')

class TestDemandPatternLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        DPL = DemandPatternLibrary()
        DPL.add_gaussian_pattern('Gaussian', 12*3600, 5*3600, normalize=True)

        self.DPL = DPL
        
    @classmethod
    def tearDownClass(self):
        pass

    def test_pattern_name_list(self):
        pattern_names = self.DPL.pattern_name_list
        assert set(["Net1_1", "Net2_1", "Net3_1"]).issubset(set(pattern_names))
    
    def test_add_pattern(self):
        pattern_name = "New_Pattern"
        entry = {"name": "New_Name",
                 "category": "New_Category",
                 "description": "New_Desription",
                 "citation": "New_Citation",
                 "start_clocktime": 0,
                 "pattern_timestep": 3600,
                 "wrap": True,
                 "multipliers": [int(i) for i in range(25)], #np.linspace(0, 24, 1), #list(np.arange(0,25,1))
                 }

        self.DPL.add_pattern(pattern_name, entry)
        pat = self.DPL.get_pattern("New_Pattern")
        series = self.DPL.to_Series("New_Pattern")
        
        expected = pd.Series(data=np.arange(0,25,1), index=np.arange(0,86401,3600))
        assert_series_equal(series, expected, check_dtype=False)

    def test_add_pulse_pattern(self):
        self.DPL.add_pulse_pattern('Pulse', [3*3600,6*3600,14*3600,20*3600], 
                                   normalize=True)
        self.DPL.add_pulse_pattern('Pulse_invert', [3*3600,6*3600,14*3600,20*3600], 
                                   invert=True, normalize=True)
        pass
    
    def test_add_gaussian_pattern(self):
        self.DPL.add_gaussian_pattern('Gaussian2', 24*3600, 12*3600)
        pass
    
    def test_add_triangular_pattern(self):
        self.DPL.add_triangular_pattern('Triangular', 2*3600, 12*3600, 18*3600, 
                                        normalize=True)
        pass
    
    def test_add_combined_pattern_overlap(self):
        self.DPL.add_combined_pattern('Combined_overlap', 
                                      ['Net1_1', 'Net2_1', 'Net3_1'], 
                                      combine='Overlap', 
                                      weights=None, 
                                      durations=[9*3600*24], 
                                      pattern_timestep=3600, 
                                      start_clocktime=0,
                                      wrap=True, normalize=False)
        self.DPL.plot_patterns(names=['Net1_1', 'Net2_1', 'Net3_1', 'Combined_overlap'])
    
    def test_add_combined_pattern_sequential(self):
        self.DPL.add_combined_pattern('Combined_sequential', 
                                      ['Net1_1', 'Net2_1', 'Net3_1'], 
                                      combine='Sequential', 
                                      weights=None, 
                                      durations=[2*3600*24, 3*3600*24, 4*3600*24], 
                                      pattern_timestep=3600, 
                                      start_clocktime=0,
                                      wrap=True, normalize=False)
        self.DPL.plot_patterns(names=['Net1_1', 'Net2_1', 'Net3_1', 'Combined_sequential'])
    
    def test_remove_pattern(self):
        pattern_name = "Constant"
        
        pattern_names = self.DPL.pattern_name_list
        assert pattern_name in set(pattern_names)
        
        self.DPL.remove_pattern(pattern_name)
        
        pattern_names = self.DPL.pattern_name_list
        assert pattern_name not in set(pattern_names)
    
    def test_copy_pattern(self):
        # Copy pattern
        self.DPL.copy_pattern('Net1_1', 'Net1_2')
        
        pat1 = self.DPL.to_Series('Net1_1')
        pat2 = self.DPL.to_Series('Net1_2')
        
        assert_series_equal(pat1, pat2)
        
    def test_read_write(self):
        num_patterns = len(self.DPL.pattern_name_list)
        self.DPL.write_json('New_demand_pattern_library.json')
        DPL2 = DemandPatternLibrary('New_demand_pattern_library.json')
        assert len(DPL2.pattern_name_list) == num_patterns
        
    def test_filter_by_category(self):
        # Filter patterns by category
        reidential_patterns = self.DPL.filter_by_category('Residential')
        commercial_patterns = self.DPL.filter_by_category('Commercial')
        indistrial_patterns = self.DPL.filter_by_category('Industrial')
        none_patterns = self.DPL.filter_by_category(None)
        
        assert 'Micropolis_2' in list(pd.DataFrame(reidential_patterns)['name'])
        assert 'Micropolis_1' in list(pd.DataFrame(commercial_patterns)['name'])
        assert 'Micropolis_3' in list(pd.DataFrame(indistrial_patterns)['name'])
        assert 'Null' in list(pd.DataFrame(none_patterns)['name'])
        
    def test_normalize(self):
        pattern_name = 'Net3_1'
        self.DPL.plot_patterns(names=[pattern_name])
        multipliers = self.DPL.get_pattern(pattern_name)['multipliers']
        mean_val = np.mean(multipliers)
        std_val = np.std(multipliers)
        
        # check that the original mean was not equal to 1
        self.assertNotAlmostEqual(mean_val, 1, 3) 
        
        self.DPL.normalize_pattern(pattern_name)
        multipliers = self.DPL.get_pattern(pattern_name)['multipliers']
        mean_val_norm = np.mean(multipliers)
        std_val_norm = np.std(multipliers)

        self.assertAlmostEquals(mean_val_norm, 1, 3)
        
    def test_resample_add_noise(self):
        val = 0.25
        
        pat = self.DPL.get_pattern('Gaussian')
        length = len(pat['multipliers'])
        duration = len(pat['multipliers'])*pat['pattern_timestep']
        assert length == 24
        assert duration == 24*3600
        
        # Create a longer timeseries
        self.DPL.resample_multipliers('Gaussian', duration=7*24*3600, pattern_timestep=60, start_clocktime=0)
        
        pat = self.DPL.get_pattern('Gaussian')
        duration = len(pat['multipliers'])*pat['pattern_timestep']
        assert duration == 7*24*3600
        
        # Copy pattern and apply noise
        self.DPL.copy_pattern('Gaussian', 'Gaussian_with_noise')
        self.DPL.apply_noise('Gaussian_with_noise', val, seed=123)
        
        mult1 = self.DPL.get_pattern('Gaussian')['multipliers']
        mult2 = self.DPL.get_pattern('Gaussian_with_noise')['multipliers']
        diff = np.array(mult1) - np.array(mult2)
        mean_diff = np.mean(diff)
        std_diff = np.std(diff)
        
        self.assertAlmostEquals(mean_diff, 0, 2)
        self.assertAlmostEquals(std_diff, val, 2)
        
    def test_to_Pattern(self):
        pattern_name = 'Net3_1'
        mult = self.DPL.get_pattern(pattern_name)['multipliers']
        
        # Convert to a WNTR Pattern object
        pattern = self.DPL.to_Pattern(pattern_name)
        
        MEA = np.mean(np.abs(pattern.multipliers -  np.array(mult)))
        
        assert pattern.name == pattern_name
        self.assertAlmostEquals(MEA, 0, 6)
        
    def test_to_Series(self):
        pattern_name = 'Net3_1'
        mult = self.DPL.get_pattern(pattern_name)['multipliers']
        
        # Convert to a Pandas Series and change time parameters, this could be used to 
        # update the pattern or create a new pattern
        series1 = self.DPL.to_Series('Net3_1')
        series2 = self.DPL.to_Series('Net3_1', duration=4*24*3600)
        
        MEA = np.mean(np.abs(series1.values -  np.array(mult)))
        
        self.assertAlmostEquals(MEA, 0, 6)
        assert series2.shape[0] == 4*24
        
    def test_add_to_wn(self):
        # Create a water network model
        wn = wntr.network.WaterNetworkModel(ex_datadir+'/Net1.inp')

        # Get demands associated with a junction
        junction = wn.get_node('11')
        print(junction.demand_timeseries_list)

        # Modify the base value and pattern of the original demand
        junction.demand_timeseries_list[0].base_value = 6e-5
        junction.demand_timeseries_list[0].pattern_name = '1'
        junction.demand_timeseries_list[0].category = 'A'
        
        # Resample Net2_1 pattern to pattern timestep from Net1
        wn_pattern_timestep = wn.options.time.pattern_timestep
        pattern_timestep = self.DPL.get_pattern('Net2_1')['pattern_timestep']
        assert wn_pattern_timestep != pattern_timestep
        self.DPL.copy_pattern('Net2_1', 'Net2_1_resampled')
        multipliers = self.DPL.resample_multipliers('Net2_1_resampled', duration=3*24*3600,
                                               pattern_timestep=wn_pattern_timestep, start_clocktime=0)
        #self.DPL.plot_patterns(names=['Net2_1_resampled', 'Net2_1'])
    
        # Add a new pattern from the pattern library, then add a demand
        print(wn.options.time.pattern_timestep, wn.options.time.start_clocktime)
        pattern = self.DPL.to_Pattern('Net2_1_resampled', wn.options.time)
        wn.add_pattern('Net2_1_resample', pattern)
        junction.add_demand(base=5e-5, pattern_name='Net2_1_resample', category='B')
        print(junction.demand_timeseries_list)

        # Add another pattern from a list, then add a demand
        wn.add_pattern('New', [1,1,1,0,0,0,1,0,0.5,0.5,0.5,1])
        junction.add_demand(base=2e-5, pattern_name='New', category='C')
        print(junction.demand_timeseries_list)

        # Simulate hydraulics
        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim()

        # Plot results on the network
        pressure_at_5hr = results.node['pressure'].loc[5*3600, :]
        wntr.graphics.plot_network(wn, node_attribute=pressure_at_5hr, node_size=30, 
                                title='Pressure at 5 hours')

        print(wn.pattern_name_list)
        
    def test_plot_pattern(self):
        filename = abspath(join(testdir, "plot_pattern.png"))
        if isfile(filename):
            os.remove(filename)
        
        # Plot patterns
        ax1 = self.DPL.plot_patterns(names=['Net1_1', 'Net2_1', 'Net3_1'])
        
        plt.savefig(filename, format="png")
        plt.close()


if __name__ == "__main__":
    unittest.main()
