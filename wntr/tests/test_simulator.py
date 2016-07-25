import unittest
import sys
import os, inspect
resilienceMainDir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(
                    inspect.currentframe()))),'..','..'))
import math

class TestPDD(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_pdd_with_wntr(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/simulator.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        res1 = wn.get_node('reservoir1')
        res1.head = 10.0
        p1 = wn.get_link('pipe1')
        p1.length = 0.0
        p2 = wn.get_link('pipe2')
        p2.length = 0.0

        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0

        sim = self.wntr.sim.WNTRSimulator(wn, True)
        results = sim.run_sim()

        for t in results.time:
            self.assertEqual(results.node.at['demand',t,'junction2'], 150.0/3600.0*math.sqrt((10.0-0.0)/(15.0-0.0)))

