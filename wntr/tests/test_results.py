# These tests run a demand-driven simulation with both WNTR and Epanet and compare the results for the example networks
import copy
import unittest
from os.path import abspath, dirname, join
from pandas.testing import assert_frame_equal, assert_series_equal, assert_index_equal

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
        
        for attr in self.res._data_attributes:
            for key in getattr(self.res, attr).keys():
                assert_index_equal(getattr(self.res, attr)[key].index + self.ts, getattr(res_copy, attr)[key].index)

    def test_append(self):
        res_copy1 = copy.deepcopy(self.res)
        res_copy2 = copy.deepcopy(self.res)
        res_copy2._adjust_time(self.wn.options.time.duration)
        res_copy1.append(res_copy2)
        assert res_copy1.node["head"].shape == (9,97)
        assert (res_copy1.node["head"].loc[0] == res_copy1.node["head"].loc[14400]).all()
    
    def test_arithmetic(self):
        df = self.res.node["head"]
        
        # addition
        temp_res = self.res + self.res
        temp_df = temp_res.node["head"]
        test_df = df + df
        assert_frame_equal(temp_df, test_df)
        
        # subtraction
        temp_res = self.res - self.res
        temp_df = temp_res.node["head"]
        test_df = df - df
        assert_frame_equal(temp_df, test_df)
        
        # division
        temp_res = self.res / self.res
        temp_df = temp_res.node["head"]
        test_df = df / df
        assert_frame_equal(temp_df, test_df)
        
        # int division
        temp_res = self.res / 2
        temp_df = temp_res.node["head"]
        test_df = df / 2
        assert_frame_equal(temp_df, test_df)
        
        # power
        temp_res = pow(self.res, 1/2)
        temp_df = temp_res.node["head"]
        test_df = pow(df, 1/2)
        assert_frame_equal(temp_df, test_df)
        
        # abs
        temp_res = abs(self.res)
        temp_df = temp_res.node["head"]
        test_df = abs(df)
        assert_frame_equal(temp_df, test_df)
        
        # neg
        temp_res = -self.res
        temp_df = temp_res.node["head"]
        test_df = -df
        assert_frame_equal(temp_df, test_df)
        
        # pos
        temp_res = +self.res
        temp_df = temp_res.node["head"]
        test_df = +df
        assert_frame_equal(temp_df, test_df)
        
        # max
        temp_res = self.res.max()
        temp_df = temp_res.node["head"]
        test_df = df.max(axis=0)
        assert_series_equal(temp_df, test_df)
        
        # min
        temp_res = self.res.min()
        temp_df = temp_res.node["head"]
        test_df = df.min(axis=0)
        assert_series_equal(temp_df, test_df)
        
        # sum
        temp_res = self.res.sum()
        temp_df = temp_res.node["head"]
        test_df = df.sum(axis=0)
        assert_series_equal(temp_df, test_df)



if __name__ == "__main__":
    unittest.main()
