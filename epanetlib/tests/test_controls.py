# These tests test controls
import unittest
import sys
sys.path.append('../../')
import epanetlib as en

class TestTimeControls(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        inp_file = 'networks_for_testing/time_controls_test_network.inp'
        self.wn = en.network.WaterNetworkModel()
        parser = en.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)
        self.wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = en.sim.PyomoSimulator(self.wn, 'PRESSURE DRIVEN')
        self.pyomo_results = pyomo_sim.run_sim()

    def test_time_control_open_vs_closed(self):
        for t in self.pyomo_results.link.loc['pipe2'].index:
            if t.components.hours < 5 or t.components.hours >= 10:
                self.assertAlmostEqual(self.pyomo_results.link.at[('pipe2',t),'flowrate'], 150/3600.0)
            else:
                self.assertAlmostEqual(self.pyomo_results.link.at[('pipe2',t),'flowrate'], 0.0)

class TestConditionalControls(unittest.TestCase):

    def test_close_link_by_tank_level(self):
        inp_file = 'networks_for_testing/conditional_controls_test_network_1.inp'
        wn = en.network.WaterNetworkModel()
        parser = en.network.ParseWaterNetwork()
        parser.read_inp_file(wn, inp_file)
        wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = en.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')
        results = pyomo_sim.run_sim()

        activated_flag = False
        for t in results.link.loc['pump1'].index:
            if results.node.at[('tank1',t),'pressure'] >= 50.0:
                activated_flag = True
                continue
            if activated_flag:
                self.assertAlmostEqual(results.link.at[('pump1',t),'flowrate'], 0.0)
            else:
                self.assertGreaterEqual(results.link.at[('pump1',t),'flowrate'], 0.0001)

    def test_open_link_by_tank_level(self):
        inp_file = 'networks_for_testing/conditional_controls_test_network_2.inp'
        wn = en.network.WaterNetworkModel()
        parser = en.network.ParseWaterNetwork()
        parser.read_inp_file(wn, inp_file)
        wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
        
        pyomo_sim = en.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')
        results = pyomo_sim.run_sim()
        for t in results.link.loc['pump1'].index:
            self.assertGreaterEqual(results.node.at[('tank1',t),'pressure'], 30.0)

if __name__ == '__main__':
    unittest.main()
