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
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/time_controls_test_network.inp'
        self.wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)
        self.wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = self.wntr.sim.PyomoSimulator(self.wn, 'PRESSURE DRIVEN')
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
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)


    def test_close_link_by_tank_level(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/conditional_controls_test_network_1.inp'
        wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        parser.read_inp_file(wn, inp_file)
        wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = self.wntr.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')
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
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/conditional_controls_test_network_2.inp'
        wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        parser.read_inp_file(wn, inp_file)
        wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = self.wntr.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')
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

class TestTankControls(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_pipe_closed_for_low_level(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/tank_controls_test_network1.inp'
        wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        parser.read_inp_file(wn, inp_file)
        wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        sim = self.wntr.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')
        results = sim.run_sim()

        tank_level_dropped_flag = False
        for t in results.link.loc['pipe1'].index:
            if results.node.at[('tank1',t),'pressure'] <= 0.0:
                self.assertLessEqual(results.link.at[('pipe1',t),'flowrate'],0.0)
                tank_level_dropped_flag = True
        self.assertEqual(tank_level_dropped_flag, True)

    def test_reopen_pipe_after_tank_fills_back_up(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/tank_controls_test_network2.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        sim = self.wntr.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')
        results = sim.run_sim()

        tank_level_dropped_flag = False
        tank_refilled_flag = False
        for t in results.link.loc['pipe1'].index:
            if results.node.at[('tank1',t),'pressure'] <= 0.0:
                self.assertLessEqual(results.link.at[('pipe1',t),'flowrate'],0.0)
                tank_level_dropped_flag = True
            elif results.node.at[('tank1',t),'pressure'] > 0.0:
                self.assertGreaterEqual(results.link.at[('pipe1',t),'flowrate'],0.001)
                if tank_level_dropped_flag:
                    tank_refilled_flag = True
        self.assertEqual(tank_level_dropped_flag, True)
        self.assertEqual(tank_refilled_flag, True)


if __name__ == '__main__':
    unittest.main()
