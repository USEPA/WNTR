import unittest
import sys
import os, inspect
resilienceMainDir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(
                    inspect.currentframe()))),'..','..'))
import math

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

        for jname, j in self.wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        self.pyomo_sim = self.wntr.sim.PyomoSimulator(self.wn, pressure_dependent = True)

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

class TestPDD(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_pdd_with_pyomo(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_1.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        res1 = wn.get_node('reservoir1')
        res1.base_head = 10.0
        p1 = wn.get_link('pipe1')
        p1.length = 0.0
        p2 = wn.get_link('pipe2')
        p2.length = 0.0

        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0

        sim = self.wntr.sim.PyomoSimulator(wn, True)
        results = sim.run_sim()

        for t in results.time:
            self.assertEqual(results.node.at[('junction2',t),'demand'], 150.0/3600.0*math.sqrt((10.0-0.0)/(15.0-0.0)))

    def test_pdd_with_scipy(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/net_test_1.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        res1 = wn.get_node('reservoir1')
        res1.base_head = 10.0
        p1 = wn.get_link('pipe1')
        p1.length = 0.0
        p2 = wn.get_link('pipe2')
        p2.length = 0.0

        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0

        sim = self.wntr.sim.ScipySimulator(wn, True)
        results = sim.run_sim()

        for t in results.time:
            self.assertEqual(results.node.at[('junction2',t),'demand'], 150.0/3600.0*math.sqrt((10.0-0.0)/(15.0-0.0)))
