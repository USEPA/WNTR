# These tests run a demand-driven simulation with both WNTR and Epanet and compare the results for the example networks
import copy
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

class TestResultsOperations(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr
        self.tol = 1e-8
        self.ts = 3600

        inp_file = join(ex_datadir, "Net3.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 4 * 3600

        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res = sim.run_sim(solver_options={"TOL": self.tol})

    @classmethod
    def tearDownClass(self):
        pass
    
    def test_adjust_time(self):
        res_copy = copy.deepcopy(self.res)
        res_copy._adjust_time(self.ts)
        
        for key in self.res.link.keys():
            assert self.res.link[key].index + self.ts == res_copy.node[key].index
        for key in self.res.node.keys():
            assert self.res.node[key].index + self.ts == res_copy.node[key].index

    def test_append(self):
        res_copy1 = copy.deepcopy(self.res)
        res_copy2 = copy.deepcopy(self.res)
        res_copy2._adjust_time(self.wn.options.time.duration)
        res_copy1.append(res_copy2)
        pass
    
    def test_arithmetic(self):
        added_res = self.res + self.res
        subtracted_res = self.res - self.res
        divided_res = self.res / self.res
        int_divided_res = self.res / 2
        pow_res = pow(self.res, 1/2)
        abs_res = abs(self.res)
        neg_res = -self.res
        pos_res = +self.res
        max_res = self.res.max()
        min_res = self.res.min()
        summed_res = self.res.sum()
        foo


if __name__ == "__main__":
    unittest.main()
