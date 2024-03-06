import unittest
import warnings
import os
from os.path import abspath, dirname, join, isfile
from pandas.testing import assert_frame_equal
import networkx as nx
import pandas as pd
import matplotlib.pylab as plt
import subprocess

try:
    import swmmio
    warnings.filterwarnings('ignore', module='swmmio')
    has_swmmio = True
except ModuleNotFoundError:
    swmmio = None
    has_swmmio = False
try:
    import pyswmm
except ModuleNotFoundError:
    pyswmm = None

import wntr.stormwater as swntr


testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


@unittest.skipIf(not has_swmmio,
                 "Cannot test SWNTR capabilities: swmmio is missing")
class TestStormWaterSim(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        inpfile = join(ex_datadir, "Site_Drainage_Model.inp")
        swn = swntr.network.StormWaterNetworkModel(inpfile)
        self.supported_sections = set(swn.section_names)
        self.tested_sections = set()
    
    @classmethod
    def tearDownClass(self):
        untested = self.supported_sections - self.tested_sections
        print('untested sections', untested)
    
    def test_simulation(self):
        # Run swmm using
        # 1. direct use of pyswmm, stepwise simulation
        # 2. direct use of swmmio cmd
        # 3. swmmio cmd with INP file read/write
        # 4. swntr with INP file read/write
        inpfiles = [ 
                    # SWMMIO INP test files
                    swmmio.tests.data.MODEL_FULL_FEATURES_PATH, 
                    #swmmio.tests.data.MODEL_CURVE_NUMBER, # pyswmm fails
                    #swmmio.tests.data.MODEL_MOD_HORTON, # pyswmm fails
                    swmmio.tests.data.MODEL_GREEN_AMPT,
                    
                    # SWMM INP example files
                    #'Culvert.inp', # pyswmm fails
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

            # Direct use of INP file with pyswmm
            print("   run pyswmm")
            if isfile(outfile):
                os.remove(outfile)
            with pyswmm.Simulation(inpfile) as sim: 
                for step in sim:
                    pass
                sim.report()
                
            results_pyswmm = swntr.io.read_outfile(outfile)
            
            # swmmio with saved INP file
            # No model sections are flagged for rewrite
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
            # All model sections are flagged for rewrite
            print("   run swntr")
            if isfile(temp_inpfile):
                os.remove(temp_inpfile)
            if isfile(temp_outfile):
                os.remove(temp_outfile)
            swn = swntr.network.StormWaterNetworkModel(inpfile)
            sim = swntr.sim.SWMMSimulator(swn) 
            results_swntr = sim.run_sim()
            
            for sec in swn.section_names:
                df = getattr(swn, sec)
                if df.shape[0] > 0:
                    self.tested_sections.add(sec)
                
            # Compare direct methods to swmmio and swntr, node total inflow
            assert_frame_equal(results_pyswmm.node['TOTAL_INFLOW'],
                               results_swmmio.node['TOTAL_INFLOW'])
            assert_frame_equal(results_pyswmm.node['TOTAL_INFLOW'],
                               results_swntr.node['TOTAL_INFLOW'])
            
            # Compare direct methods to swmmio and swntr, link capacity
            assert_frame_equal(results_pyswmm.link['CAPACITY'],
                               results_swmmio.link['CAPACITY'])
            assert_frame_equal(results_pyswmm.link['CAPACITY'],
                               results_swntr.link['CAPACITY'])

    def test_return_summary(self):
        inpfile = join(test_datadir, "SWMM_examples", "Site_Drainage_Model.inp")
        swn = swntr.network.StormWaterNetworkModel(inpfile)
        sim = swntr.sim.SWMMSimulator(swn) 
        summary = sim.run_sim(return_summary=True)
        assert 'Node Depth Summary' in summary.keys()
        assert 'MaxNodeDepth' in summary['Node Depth Summary'].columns
        assert set(summary['Node Depth Summary'].index) == set(swn.node_name_list)

@unittest.skipIf(not has_swmmio,
                 "Cannot test GIS capabilities: geopandas is missing")
class TestStormWaterScenarios(unittest.TestCase):

    def test_conduit_reduced_flow(self):
        conduit_name = 'C1'
        max_flow1 = 0.001
        
        inpfile = join(ex_datadir, "Site_Drainage_Model.inp")
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
        pump_name = 'PUMP1'
        start_time = 4.5
        end_time = 12

        inpfile = join(test_datadir, "SWMM_examples", "Pump_Control_Model.inp")
        swn1 = swntr.network.StormWaterNetworkModel(inpfile)
        assert swn1.controls.shape[0] == 2
        swn1.add_pump_outage_control(pump_name, start_time, end_time) # Outage times in decimal hours
        assert swn1.controls.shape[0] == 3
        
        # Test ability to modify INP file
        swntr.io.write_inpfile(swn1, "temp.inp")
        inpfile = join(testdir, "temp.inp")
        swn2 = swntr.network.StormWaterNetworkModel(inpfile)
        assert swn2.controls.shape[0] == 3
        control_name = 'RULE ' + pump_name + '_power_outage'
        assert control_name in swn2.controls.index
        
        # Test simulation results
        sim = swntr.sim.SWMMSimulator(swn1) 
        results_swntr = sim.run_sim()
        
        # Pump flowrate over the entire simulation is not 0
        flow_rate = results_swntr.link['FLOW_RATE'].loc[:, pump_name]
        assert flow_rate.mean() != 0
        
        # Pump flowrate during the outage is 0
        start_datetime = flow_rate.index[0] + + pd.Timedelta(str(start_time) + " hours")
        end_datetime = flow_rate.index[0] + + pd.Timedelta(str(end_time-0.001) + " hours")
        flow_rate_outage = results_swntr.link['FLOW_RATE'].loc[start_datetime:end_datetime, pump_name]
        self.assertAlmostEqual(flow_rate_outage.mean(), 0, 4)


@unittest.skipIf(not has_swmmio,
                 "Cannot test GIS capabilities: geopandas is missing")
class TestStormWaterMetrics(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        pass
    
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_pump_power(self):
        inpfile = join(test_datadir, "SWMM_examples", "Pump_Control_Model.inp")
        swn = swntr.network.StormWaterNetworkModel(inpfile)
        
        sim = swntr.sim.SWMMSimulator(swn) 
        results = sim.run_sim()
        summary = swntr.io.read_rptfile('temp.rpt')
        
        pump_flowrate = results.link['FLOW_RATE'].loc[:, swn.pump_name_list]
        head = results.node['HYDRAULIC_HEAD']

        pump_headloss = swntr.metrics.headloss(head, swn.pump_name_list, swn)
        pump_power = swntr.metrics.pump_power(pump_flowrate, pump_headloss, swn)
        pump_energy = swntr.metrics.pump_energy(pump_flowrate, pump_headloss, swn)
        
        pump_name = swn.pump_name_list[0]
        from_metrics = pump_energy[pump_name].sum()
        from_rpt = summary['Pumping Summary'].loc[pump_name,'PowerUsage(kW-hr)']
        
        self.assertAlmostEqual(from_metrics, from_rpt, 1)


@unittest.skipIf(not has_swmmio,
                 "Cannot test GIS capabilities: geopandas is missing")
class TestStormWaterGIS(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        inpfile = join(ex_datadir, "Site_Drainage_Model.inp")
        self.swn = swntr.network.StormWaterNetworkModel(inpfile)
    
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_create_gis_object(self):
        swn_gis = self.swn.to_gis()
        
        fig, ax = plt.subplots()
        swn_gis.subcatchments.boundary.plot(ax=ax)
        swn_gis.junctions.plot(column="InvertElev", ax=ax)
        swn_gis.conduits.plot(column="MaxFlow", ax=ax)
    
        assert swn_gis.subcatchments.shape == (7,8)
        assert 'geometry' in swn_gis.subcatchments.columns
        assert swn_gis.junctions.shape == (11,6)
        assert 'geometry' in swn_gis.junctions.columns
        assert swn_gis.conduits.shape == (11,9)
        assert 'geometry' in swn_gis.conduits.columns
        
    def test_write_geojson(self):
        valid_components = ["junctions", "outfalls", "conduits", "subcatchments"]
        for name in valid_components:
            filename = abspath(join(testdir, "temp_"+name+".geojson"))
            if isfile(filename):
                os.remove(filename)
            
        swntr.io.write_geojson(self.swn, 'temp')
            
        for name in valid_components:
            filename = abspath(join(testdir, "temp_"+name+".geojson"))
            self.assertTrue(isfile(filename))


@unittest.skipIf(not has_swmmio,
                 "Cannot test GIS capabilities: geopandas is missing")
class TestStormWaterGraphics(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        inpfile = join(ex_datadir, "Site_Drainage_Model.inp")
        self.swn = swntr.network.StormWaterNetworkModel(inpfile)
    
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_plot_network1(self):
        # Basic network plot
        filename = abspath(join(testdir, "plot_network1_swmm.png"))
        if isfile(filename):
            os.remove(filename)

        plt.figure()
        swntr.graphics.plot_network(self.swn)
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

    def test_plot_network2(self):
        # Node and link attributes
        filename = abspath(join(testdir, "plot_network2_swmm.png"))
        if isfile(filename):
            os.remove(filename)

        plt.figure()
        swntr.graphics.plot_network(self.swn, 
                                    node_attribute="InvertElev", 
                                    link_attribute="Length",
                                    subcatchment_attribute='PercImperv')
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))
    
    def test_plot_network3(self):
        # List of node and link names
        filename = abspath(join(testdir, "plot_network3_swmm.png"))
        if isfile(filename):
            os.remove(filename)

        plt.figure()
        swntr.graphics.plot_network(self.swn, 
                                    node_attribute=["J1", "J4"],
                                    link_attribute=["C3", "C5"],
                                    link_labels=True)
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))
    
    def test_plot_network4(self):
        # Dictionary of attributes
        filename = abspath(join(testdir, "plot_network4_swmm.png"))
        if isfile(filename):
            os.remove(filename)
        
        plt.figure()
        swntr.graphics.plot_network(self.swn,
                                    node_attribute={"J1": 5, "J4": 10},
                                    link_attribute={"C3": 3, "C5": 9},
                                    node_labels=True)
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))
    
    def test_plot_network5(self):
        # Series, range and title
        filename = abspath(join(testdir, "plot_network5_swmm.png"))
        if isfile(filename):
            os.remove(filename)
        
        G = self.swn.to_graph()
        node_degree = pd.Series(dict(nx.degree(G)))
        
        plt.figure()
        swntr.graphics.plot_network(self.swn, 
                                    node_attribute=node_degree, 
                                    node_range=[1, 4], 
                                    title="Node degree")
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))


if __name__ == "__main__":
    unittest.main()
