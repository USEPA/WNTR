# These tests run a demand-driven simulation with both WNTR and Epanet and compare the results for the example networks
import pickle
import unittest
from os.path import abspath, dirname, join

import pandas as pd

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestResetInitialValues(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net3.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 24 * 3600

        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res1 = sim.run_sim(solver_options={"TOL": 1e-8})

        self.wn.reset_initial_values()
        self.res2 = sim.run_sim(solver_options={"TOL": 1e-8})

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.res1.time:
                self.assertAlmostEqual(
                    self.res1.link["flowrate"].at[t, link_name],
                    self.res2.link["flowrate"].at[t, link_name],
                    7,
                )

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link["velocity"].index:
                self.assertAlmostEqual(
                    self.res1.link["velocity"].at[t, link_name],
                    self.res2.link["velocity"].at[t, link_name],
                    7,
                )

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["demand"].index:
                self.assertAlmostEqual(
                    self.res1.node["demand"].at[t, node_name],
                    self.res2.node["demand"].at[t, node_name],
                    7,
                )

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["head"].index:
                self.assertAlmostEqual(
                    self.res1.node["head"].at[t, node_name],
                    self.res2.node["head"].at[t, node_name],
                    7,
                )

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["pressure"].index:
                self.assertAlmostEqual(
                    self.res1.node["pressure"].at[t, node_name],
                    self.res2.node["pressure"].at[t, node_name],
                    7,
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
        self.wn.options.time.duration = 24*3600
        self.res3 = sim.run_sim(solver_options={'TOL':1e-8})

        node_res = {}
        link_res = {}
        for key in self.res2.node.keys(): 
            node_res[key] = pd.concat([self.res2.node[key],self.res3.node[key]],axis=0)
        for key in self.res2.link.keys():
            link_res[key] = pd.concat([self.res2.link[key],self.res3.link[key]],axis=0)
        self.res2.node = node_res
        self.res2.link = link_res

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link["flowrate"].index:
                self.assertAlmostEqual(
                    self.res1.link["flowrate"].at[t, link_name],
                    self.res2.link["flowrate"].at[t, link_name],
                    7,
                )

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link["velocity"].index:
                self.assertAlmostEqual(
                    self.res1.link["velocity"].at[t, link_name],
                    self.res2.link["velocity"].at[t, link_name],
                    7,
                )

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["demand"].index:
                self.assertAlmostEqual(
                    self.res1.node["demand"].at[t, node_name],
                    self.res2.node["demand"].at[t, node_name],
                    7,
                )

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["head"].index:
                self.assertAlmostEqual(
                    self.res1.node["head"].at[t, node_name],
                    self.res2.node["head"].at[t, node_name],
                    7,
                )

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["pressure"].index:
                self.assertAlmostEqual(
                    self.res1.node["pressure"].at[t, node_name],
                    self.res2.node["pressure"].at[t, node_name],
                    7,
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
        self.wn = parser.read(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 10 * 3600
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.res2 = sim.run_sim(solver_options={"TOL": 1e-8})
        f = open("temp.pickle", "wb")
        pickle.dump(self.wn, f)
        f.close()
        f = open("temp.pickle", "rb")
        wn2 = pickle.load(f)
        f.close()
        #wn2.set_initial_conditions(self.res2)
        wn2.options.time.duration = 24*3600
        sim = self.wntr.sim.WNTRSimulator(wn2)
        self.res3 = sim.run_sim(solver_options={'TOL':1e-8})

        node_res = {}
        link_res = {}
        for key in self.res2.node.keys():
            node_res[key] = pd.concat([self.res2.node[key],self.res3.node[key]],axis=0)
        for key in self.res2.link.keys():
            link_res[key] = pd.concat([self.res2.link[key],self.res3.link[key]],axis=0)
    
        self.res2.node = node_res
        self.res2.link = link_res

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link["flowrate"].index:
                self.assertAlmostEqual(
                    self.res1.link["flowrate"].at[t, link_name],
                    self.res2.link["flowrate"].at[t, link_name],
                    7,
                )

    def test_link_velocity(self):
        for link_name, link in self.wn.links():
            for t in self.res1.link["velocity"].index:
                self.assertAlmostEqual(
                    self.res1.link["velocity"].at[t, link_name],
                    self.res2.link["velocity"].at[t, link_name],
                    7,
                )

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["demand"].index:
                self.assertAlmostEqual(
                    self.res1.node["demand"].at[t, node_name],
                    self.res2.node["demand"].at[t, node_name],
                    7,
                )

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["head"].index:
                self.assertAlmostEqual(
                    self.res1.node["head"].at[t, node_name],
                    self.res2.node["head"].at[t, node_name],
                    7,
                )

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.res1.node["pressure"].index:
                self.assertAlmostEqual(
                    self.res1.node["pressure"].at[t, node_name],
                    self.res2.node["pressure"].at[t, node_name],
                    7,
                )


if __name__ == "__main__":
    unittest.main()
