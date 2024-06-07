import unittest
from os.path import abspath, dirname, join
import wntr
import pandas as pd

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

tolerances = {
    "flowrate": 1.0e-5, # 10 mL/s
    "velocity": 1.0e-2, # 0.01 m/s
    "demand": 1.0e-4, # 10 mL/s
    "head": 1.0e-2,  # 0.01 m
    "pressure": 1.0e-2,  # 0.01 m H2O
    "headloss": 1.0e-2,  # 0.01 
    "status": 0.5,  #  i.e., 0 since this is integer
    "setting": 1.0e-2,  # 0.01
}


class TestStepwiseSim(unittest.TestCase):
    @classmethod
    def setUpClass(self):

        inp_file = join(ex_datadir, "Net3.inp")

        # straight 24 hour simulation
        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 3600
        wn.options.time.duration = 24 * 3600
        sim = wntr.sim.EpanetSimulator(wn)
        continuous_res = sim.run_sim()

        # 24 hour simulation done in 24 1-hour chunks
        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 3600
        wn.options.time.duration = 1 * 3600

        for i in range(0,24):
            # run simulation for ith step
            sim = wntr.sim.EpanetSimulator(wn)
            i_res = sim.run_sim()
            
            # update wn with ith results
            wn.set_initial_conditions(i_res)
            wn.options.time.pattern_start = wn.options.time.pattern_start + (1 * 3600)
            
            
            # adjust time of ith results
            start_time = i * 3600
            i_res._adjust_time(start_time)
            
            # concatenate step results
            if i == 0:
                stepwise_res = i_res
            else:
                stepwise_res.append(i_res, overwrite=True)
                
        self.diff_res = abs(continuous_res - stepwise_res).max()

    def test_nodes(self):
        node_keys = ["demand", "head", "pressure"]
        for key in node_keys:
            max_res_diff = self.diff_res.node[key].max()
            self.assertLess(max_res_diff, tolerances[key])
            
    def test_links(self):
        link_keys = ["flowrate", "velocity", "status", "setting", "headloss"]
        for key in link_keys:
            max_res_diff = self.diff_res.link[key].max()
            self.assertLess(max_res_diff, tolerances[key])
            
            

# self.diff_res.node["pressure"].plot()

# self.diff_res.link["status"].plot()


if __name__ == "__main__":
    unittest.main()