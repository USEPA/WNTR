import unittest
import warnings
import os
from os.path import abspath, dirname, join, isfile
from pandas.testing import assert_frame_equal
import time

import wntr

import swmmio
import pyswmm
import subprocess

warnings.filterwarnings('ignore', module='swmmio')

import wntr.stormwater as swntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")

class TestStormwater(unittest.TestCase):

    def test_simulation(self):
        # Run swmm using
        # 1. swmmio cmd line
        # 2. stepwise simulation using pyswmm
        # 3. swmmio with read/write
        # 4. swntr with read/write
        inpfiles = [
                    #'Culvert.inp', # pyswmm and swmmio fail
                    'Detention_Pond_Model.inp',
                    #'Groundwater_Model.inp', # pyswmm fails (rpt file does not finish writing).  swmmio results in empty link results
                    'Inlet_Drains_Model.inp',
                    #'LID_Model.inp', # pyswmm fails (rpt file does not finish writing).  swmmio results in empty link results
                    'Pump_Control_Model.inp',
                    'Site_Drainage_Model.inp', 
                    ]
        
        for inpfile_name in inpfiles:
            print(inpfile_name)
            
            inpfile = join(test_datadir, "SWMM_examples", inpfile_name)
            rootname = inpfile.split('.inp')[0]
            outfile = join(test_datadir, rootname+'.out')
            
            temp_inpfile = 'temp.inp'
            temp_outfile = 'temp.out'
            
            # Direct swmmio
            print("   run direct swmmio")
            if isfile(outfile):
                os.remove(outfile)
            p = subprocess.run("python -m swmmio --run " + inpfile)
            results_swmmio_direct = swntr.io.read_outfile(outfile)
             
            # Direct pyswmm
            print("   run direct pyswmm")
            if isfile(outfile):
                os.remove(outfile)
            with pyswmm.Simulation(inpfile) as sim: 
                for step in sim:
                    pass
                sim.report()
                
            results_pyswmm_direct = swntr.io.read_outfile(outfile)

            # swmmio (with read/write)
            print("   run swmmio")
            if isfile(temp_inpfile):
                os.remove(temp_inpfile)
            if isfile(temp_outfile):
                os.remove(temp_outfile)
            swmmio_model = swmmio.Model(inpfile)
            swmmio_model.inp.save(temp_inpfile)
            p = subprocess.run("python -m swmmio --run " + temp_inpfile)
            results_swmmio = swntr.io.read_outfile(temp_outfile)
            
            # swntr
            print("   run swntr")
            if isfile(temp_inpfile):
                os.remove(temp_inpfile)
            if isfile(temp_outfile):
                os.remove(temp_outfile)
            swn = swntr.network.StormWaterNetworkModel(inpfile)
            sim = swntr.sim.SWMMSimulator(swn) 
            results_swntr = sim.run_sim()
            
            # Compare direct methods to swmmio and swntr, node total inflow
            assert_frame_equal(results_swmmio_direct.node['TOTAL_INFLOW'],
                               results_pyswmm_direct.node['TOTAL_INFLOW'])
            assert_frame_equal(results_swmmio_direct.node['TOTAL_INFLOW'],
                               results_swmmio.node['TOTAL_INFLOW'])
            assert_frame_equal(results_swmmio_direct.node['TOTAL_INFLOW'],
                               results_swntr.node['TOTAL_INFLOW'])
            
            # Compare direct methods to swmmio and swntr, link capacity
            assert_frame_equal(results_swmmio_direct.link['CAPACITY'],
                               results_pyswmm_direct.link['CAPACITY'])
            assert_frame_equal(results_swmmio_direct.link['CAPACITY'],
                               results_swmmio.link['CAPACITY'])
            assert_frame_equal(results_swmmio_direct.link['CAPACITY'],
                               results_swntr.link['CAPACITY'])

    def test_return_summary(self):
        inpfile = join(test_datadir, "SWMM_examples", "Site_Drainage_Model.inp")
        swn = swntr.network.StormWaterNetworkModel(inpfile)
        sim = swntr.sim.SWMMSimulator(swn) 
        summary = sim.run_sim(return_summary=True)
        assert 'Node Depth Summary' in summary.keys()
        assert 'MaxNodeDepth' in summary['Node Depth Summary'].columns
        assert set(summary['Node Depth Summary'].index) == set(swn.node_name_list)
        
    def test_conduit_reduced_flow(self):
        conduit_name = 'C1'
        max_flow1 = 0.001
        
        inpfile = join(test_datadir, "SWMM_examples", "Site_Drainage_Model.inp")
        swn1 = swntr.network.StormWaterNetworkModel(inpfile)
        swn1.conduits.loc[conduit_name, "MaxFlow"] = max_flow1
        
        # Test ability to modify INP file
        swntr.io.write_inpfile(swn1, "temp.inp")
        inpfile = join(testdir, "temp.inp")
        swn2 = swntr.network.StormWaterNetworkModel(inpfile)
        max_flow2 = swn2.conduits.loc[conduit_name, "MaxFlow"]
        assert max_flow1 == max_flow2
        
        # Test simulation results
        sim = swntr.sim.SWMMSimulator(swn1) 
        results_swntr = sim.run_sim()
        
        average_flow_rate = results_swntr.link['FLOW_RATE'].loc[:, conduit_name].mean()
        self.assertAlmostEqual(average_flow_rate, max_flow1, 4)

    def test_pump_outage(self):
        pass

            
if __name__ == "__main__":
    unittest.main()