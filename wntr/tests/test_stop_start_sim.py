import unittest
from os.path import abspath, dirname, join
import wntr


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

class TestStopStartSim(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        inp_file = join(ex_datadir, "Net3.inp")
        simulator = wntr.sim.WNTRSimulator
        
        # straight 24 hour simulation
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 24 * 3600
        sim = simulator(self.wn)
        self.res1 = sim.run_sim(solver_options={"TOL": 1e-8})
        
        # 24 hour simulation done in one 10 hour chunk and one 14 hour chunk
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 10 * 3600
        sim = simulator(self.wn)
        self.res2 = sim.run_sim(solver_options={'TOL':1e-8})
        self.wn.set_initial_conditions(self.res2)
        self.wn.options.time.pattern_start = self.wn.options.time.pattern_start + 10 * 3600
        self.wn.options.time.duration = 14 * 3600
        sim = simulator(self.wn)
        self.res3 = sim.run_sim(solver_options={'TOL':1e-8})
        self.res3._adjust_time(10*3600)
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
        inp_file = join(ex_datadir, "Net3.inp")
        
        # straight 24 hour simulation
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 24 * 3600
        sim = wntr.sim.EpanetSimulator(self.wn)
        self.res1 = sim.run_sim()
        
        # 24 hour simulation done in one 10 hour chunk and one 14 hour chunk
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.hydraulic_timestep = 3600
        self.wn.options.time.duration = 11 * 3600
        sim = wntr.sim.EpanetSimulator(self.wn)
        self.res2 = sim.run_sim()
        self.wn.set_initial_conditions(self.res2)
        self.wn.options.time.pattern_start = self.wn.options.time.pattern_start + 11 * 3600
        self.wn.options.time.duration = 13 * 3600
        sim = wntr.sim.EpanetSimulator(self.wn)
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


if __name__ == "__main__":
    unittest.main()