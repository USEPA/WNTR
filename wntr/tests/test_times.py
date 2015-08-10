import unittest
import sys
# HACK until resilience is a proper module
# __file__ fails if script is called in different ways on Windows
# __file__ fails if someone does os.chdir() before
# sys.argv[0] also fails because it doesn't not always contains the path
import os, inspect
resilienceMainDir = os.path.abspath( 
    os.path.join( os.path.dirname( os.path.abspath( inspect.getfile( 
        inspect.currentframe() ) ) ), '..', '..' ))
import copy
import numpy as np

class TestNetworkTimeErrors(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_pattern_start_time(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_8.inp'
        wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        
        with self.assertRaises(ValueError):
            parser.read_inp_file(wn, inp_file)

    def test_report_time_step(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_9.inp'
        wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        
        with self.assertRaises(ValueError):
            parser.read_inp_file(wn, inp_file)

    def test_report_start_time(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_10.inp'
        wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        
        with self.assertRaises(ValueError):
            parser.read_inp_file(wn, inp_file)

    def test_start_clocktime(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_11.inp'
        wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        
        with self.assertRaises(ValueError):
            parser.read_inp_file(wn, inp_file)

class TestNetworkTimeBehavior(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_12.inp'
        wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        parser.read_inp_file(wn, inp_file)
        sim = self.wntr.sim.PyomoSimulator(wn, 'DEMAND DRIVEN')
        self.results = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_duration(self):
        results = self.results
        self.assertEqual(len(results.node.loc['junction1'].index), 26)
        self.assertEqual(results.node.loc['junction1'].index[25].components.days, 1)
        self.assertEqual(results.node.loc['junction1'].index[25].components.hours, 3)
        self.assertEqual(results.node.loc['junction1'].index[25].components.minutes, 5)
        self.assertEqual(results.node.loc['junction1'].index[25].components.seconds, 0)

    def test_hydraulic_timestep(self):
        results = self.results
        self.assertEqual((results.node.loc['junction1'].index[1] - results.node.loc['junction1'].index[0]).components.days, 0) 
        self.assertEqual((results.node.loc['junction1'].index[1] - results.node.loc['junction1'].index[0]).components.hours, 1) 
        self.assertEqual((results.node.loc['junction1'].index[1] - results.node.loc['junction1'].index[0]).components.minutes, 5) 
        self.assertEqual((results.node.loc['junction1'].index[1] - results.node.loc['junction1'].index[0]).components.seconds, 0) 

    def test_pattern_timestep(self):
        results = self.results
        for t in results.node.loc['junction1'].index:
            self.assertEqual(results.node.at[('junction1',t),'demand'], 1.0)
            total_seconds = t.components.days*3600.0*24.0 + t.components.hours*3600.0 + t.components.minutes*60.0 + t.components.seconds
            if (total_seconds/3900.0)%8 == 0.0 or ((total_seconds/3900.0)-1)%8 == 0.0:
                self.assertEqual(results.node.at[('junction2',t),'demand'], 0.5)
            elif (total_seconds/3900.0)%8 == 2.0 or ((total_seconds/3900.0)-1)%8 == 2.0:
                self.assertEqual(results.node.at[('junction2',t),'demand'], 1.0)
            elif (total_seconds/3900.0)%8 == 4.0 or ((total_seconds/3900.0)-1)%8 == 4.0:
                self.assertEqual(results.node.at[('junction2',t),'demand'], 1.5)
            elif (total_seconds/3900.0)%8 == 6.0 or ((total_seconds/3900.0)-1)%8 == 6.0:
                self.assertEqual(results.node.at[('junction2',t),'demand'], 1.0)

if __name__ == '__main__':
    unittest.main()
