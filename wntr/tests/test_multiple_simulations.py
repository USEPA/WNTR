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

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["flowrate"].at[link_name],
                tolerances["flowrate"],
            )

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["velocity"].at[link_name],
                tolerances["velocity"]
            )

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["demand"].at[node_name],
                tolerances["demand"]
            )

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["head"].at[node_name],
                tolerances["head"]
            )

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["pressure"].at[node_name],
                tolerances["pressure"]
            )


class TestStopStartSim(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net3.inp")

        parser = self.wntr.epanet.InpFile()
        self.wn = parser.read(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 24 * 3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res1 = sim.run_sim(solver_options={"TOL": 1e-8})

        parser = self.wntr.epanet.InpFile()
        self.wn = parser.read(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 10 * 3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res2 = sim.run_sim(solver_options={'TOL':1e-8})
        self.wn.set_initial_conditions(self.res2)
        self.wn.options.time.pattern_start = self.wn.options.time.pattern_start + 10 * 3600
        self.wn.options.time.duration = 14 * 3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res3 = sim.run_sim(solver_options={'TOL':1e-8})
        self.res3._adjust_time(10*3600)
        # node_res = {}
        # link_res = {}
        # for key in self.res2.node.keys(): 
        #     node_res[key] = pd.concat([self.res2.node[key],self.res3.node[key]],axis=0)
        # for key in self.res2.link.keys():
        #     link_res[key] = pd.concat([self.res2.link[key],self.res3.link[key]],axis=0)
        # self.res2.node = node_res
        # self.res2.link = link_res
        self.res2.append(self.res3)
        self.res4 = abs(self.res1 - self.res2).max()

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            print(link_name, self.res1.link["flowrate"].loc[:,link_name].describe(), abs(self.res1 - self.res2).link["flowrate"].loc[:,link_name].describe())
            self.assertLess(
                self.res4.link["flowrate"].at[link_name],
                tolerances["flowrate"],
            )

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["velocity"].at[link_name],
                tolerances["velocity"]
            )

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["demand"].at[node_name],
                tolerances["demand"]
            )

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["head"].at[node_name],
                tolerances["head"]
            )

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["pressure"].at[node_name],
                tolerances["pressure"]
            )



class TestStopStartEpanetSim(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net3.inp")

        parser = self.wntr.epanet.InpFile()
        self.wn = parser.read(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 24 * 3600
        sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.res1 = sim.run_sim()

        parser = self.wntr.epanet.InpFile()
        self.wn2 = parser.read(inp_file)
        self.wn2.options.time.hydraulic_timestep = 3600
        self.wn2.options.time.duration = 11 * 3600
        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.res2 = sim.run_sim()
        self.wn2.set_initial_conditions(self.res2)
        self.wn2.options.time.pattern_start = self.wn2.options.time.pattern_start + 11 * 3600
        self.wn2.options.time.duration = 13 * 3600
        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.res3 = sim.run_sim()
        self.res3._adjust_time(11*3600)
        
        self.res2.append(self.res3)
        self.res4 = abs(self.res1 - self.res2).max()

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["flowrate"].at[link_name],
                tolerances["flowrate"],
            )

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["velocity"].at[link_name],
                tolerances["velocity"]
            )

    def test_link_headloss(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["headloss"].at[link_name],
                tolerances["headloss"]
            )

    def test_link_status(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["status"].at[link_name],
                tolerances["status"]
            )

    def test_link_setting(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["setting"].at[link_name],
                tolerances["setting"]
            )

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["demand"].at[node_name],
                tolerances["demand"]
            )

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["head"].at[node_name],
                tolerances["head"]
            )

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["pressure"].at[node_name],
                tolerances["pressure"]
            )


class TestPickle(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net3.inp")

        parser = self.wntr.epanet.InpFile()
        self.wn = parser.read(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 24 * 3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res1 = sim.run_sim(solver_options={"TOL": 1e-8})

        parser = self.wntr.epanet.InpFile()
        self.wn2 = parser.read(inp_file)
        self.wn2.options.time.hydraulic_timestep = 3600
        self.wn2.options.time.duration = 10 * 3600
        sim = self.wntr.sim.WNTRSimulator(self.wn2)
        self.res2 = sim.run_sim(solver_options={"TOL": 1e-8})
        self.wn2.set_initial_conditions(self.res2, 36000)
        self.wn2.options.time.pattern_start = self.wn2.options.time.pattern_start + 10 * 3600
        f = open("temp.pickle", "wb")
        pickle.dump(self.wn2, f)
        f.close()
        f = open("temp.pickle", "rb")
        self.wn2 = pickle.load(f)
        f.close()
        self.wn2.options.time.duration = 14*3600
        sim = self.wntr.sim.WNTRSimulator(self.wn2)
        self.res3 = sim.run_sim(solver_options={'TOL':1e-8})
        self.res3._adjust_time(10*3600)
        
        self.res2.append(self.res3)
        self.res4 = abs(self.res1 - self.res2).max()

    @classmethod
    def tearDownClass(self):
        pass


    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["flowrate"].at[link_name],
                tolerances["flowrate"],
            )

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            self.assertLess(
                self.res4.link["velocity"].at[link_name],
                tolerances["velocity"]
            )

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["demand"].at[node_name],
                tolerances["demand"]
            )

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["head"].at[node_name],
                tolerances["head"]
            )

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            self.assertLess(
                self.res4.node["pressure"].at[node_name],
                tolerances["pressure"]
            )


if __name__ == "__main__":
    unittest.main()
