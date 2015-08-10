import unittest
import sys
import os, inspect
resilienceMainDir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(
                    inspect.currentframe()))),'..','..'))

class TestCreationOfPyomoSimulatorObject(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_7.inp'
        self.wn = self.wntr.network.WaterNetworkModel()
        parser = self.wntr.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)

        self.wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        self.pyomo_sim = self.wntr.sim.PyomoSimulator(self.wn, 'PRESSURE DRIVEN')

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_time_options(self):
        self.assertEqual(self.pyomo_sim._sim_start_sec, 0.0*3600.0+0.0*60.0)
        self.assertEqual(self.pyomo_sim._sim_duration_sec, 27.0*3600.0+5.0*60.0)
        self.assertEqual(self.pyomo_sim._pattern_start_sec, 0.0*3600.0+0.0*60.0)
        self.assertEqual(self.pyomo_sim._hydraulic_step_sec, 1.0*3600.0+5.0*60.0)
        self.assertEqual(self.pyomo_sim._pattern_step_sec, 2.0*3600.0+10.0*60.0)
        self.assertEqual(self.pyomo_sim._report_step_sec, 1.0*3600.0+5.0*60.0)

