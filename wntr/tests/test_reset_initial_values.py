# These tests run a demand-driven simulation with both WNTR and Epanet and compare the results for the example networks
import pickle
import unittest
from os.path import abspath, dirname, join

import pandas as pd

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

tolerances = {
    "flowrate": 1.0e-5, # 10 mL/s
    "velocity": 1.0e-2, # 0.01 m/s
    "demand": 1.0e-5, # 10 mL/s
    "head": 1.0e-2,  # 0.01 m
    "pressure": 1.0e-2,  # 0.01 m H2O
    "headloss": 1.0e-2,  # 0.01 
    "status": 0.5,  #  i.e., 0 since this is integer
    "setting": 1.0e-2,  # 0.01
}

class TestResetInitialValues(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr
        self.tol = 1e-8

        inp_file = join(ex_datadir, "Net3.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 24 * 3600

        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res1 = sim.run_sim(solver_options={"TOL": 1e-8})

        self.wn.reset_initial_values()
        self.res2 = sim.run_sim(solver_options={"TOL": 1e-8})

        self.res4 = abs(self.res1 - self.res2).max()

    @classmethod
    def tearDownClass(self):
        pass
    
    def test_nodes(self):
        node_keys = ["demand", "head", "pressure"]
        for key in node_keys:
            max_res_diff = self.res4.node[key].max()
            self.assertLess(max_res_diff, tolerances[key])
            
    def test_links(self):
        link_keys = ["flowrate", "velocity", "status", "setting"]
        for key in link_keys:
            max_res_diff = self.res4.link[key].max()
            self.assertLess(max_res_diff, tolerances[key])
