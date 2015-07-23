"""
TODO
1. Modify conditional controls tests to match epanet (resolve timestep is control is activated)
"""

# These tests test controls
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

class TestTimeControls(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import epanetlib as en
        self.en = en

        inp_file = resilienceMainDir+'/epanetlib/tests/networks_for_testing/time_controls_test_network.inp'
        self.wn = self.en.network.WaterNetworkModel()
        parser = self.en.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)
        self.wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = self.en.sim.PyomoSimulator(self.wn, 'PRESSURE DRIVEN')
        self.pyomo_results = pyomo_sim.run_sim()

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_time_control_open_vs_closed(self):
        for t in self.pyomo_results.link.loc['pipe2'].index:
            if t.components.hours < 5 or t.components.hours >= 10:
                self.assertAlmostEqual(self.pyomo_results.link.at[('pipe2',t),'flowrate'], 150/3600.0)
            else:
                self.assertAlmostEqual(self.pyomo_results.link.at[('pipe2',t),'flowrate'], 0.0)

class TestConditionalControls(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import epanetlib as en
        self.en = en

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)


    def test_close_link_by_tank_level(self):
        inp_file = resilienceMainDir+'/epanetlib/tests/networks_for_testing/conditional_controls_test_network_1.inp'
        wn = self.en.network.WaterNetworkModel()
        parser = self.en.network.ParseWaterNetwork()
        parser.read_inp_file(wn, inp_file)
        wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = self.en.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')
        results = pyomo_sim.run_sim()

        activated_flag = False
        for t in results.link.loc['pump1'].index:
            if activated_flag:
                self.assertAlmostEqual(results.link.at[('pump1',t),'flowrate'], 0.0)
            else:
                self.assertGreaterEqual(results.link.at[('pump1',t),'flowrate'], 0.0001)
            if results.node.at[('tank1',t),'pressure'] >= 50.0 and not activated_flag:
                activated_flag = True
        self.assertEqual(activated_flag, True)

    def test_open_link_by_tank_level(self):
        inp_file = resilienceMainDir+'/epanetlib/tests/networks_for_testing/conditional_controls_test_network_2.inp'
        wn = self.en.network.WaterNetworkModel()
        parser = self.en.network.ParseWaterNetwork()
        parser.read_inp_file(wn, inp_file)
        wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = self.en.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')
        results = pyomo_sim.run_sim()

        activated_flag = False
        for t in results.link.loc['pump1'].index:
            if activated_flag:
                self.assertGreaterEqual(results.link.at[('pipe1',t),'flowrate'], 0.002)
            else:
                self.assertAlmostEqual(results.link.at[('pipe1',t),'flowrate'], 0.0)
            if results.node.at[('tank1',t),'pressure'] >= 300.0 and not activated_flag:
                activated_flag = True
        self.assertEqual(activated_flag, True)

if __name__ == '__main__':
    unittest.main()
