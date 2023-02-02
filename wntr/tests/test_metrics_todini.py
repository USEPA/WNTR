import unittest
from os.path import abspath, dirname, join
from pandas.testing import assert_frame_equal, assert_series_equal

import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

class TestTodiniMetrics(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        import wntr

        # Network models from Todini, 2000 (based on Abebe and Solomatine, 
        # 1988 - defined h_star)
        self.h_star = 30 # m
        
    def test_Todini_Fig2_optCost_GPM(self):
        inp_file = join(datadir, "Todini_Fig2_optCost_GPM.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        # Compute todini index
        head = results.node["head"]
        pressure = results.node["pressure"]
        demand = results.node["demand"]
        flowrate = results.link["flowrate"]
        todini = wntr.metrics.todini_index(
            head, pressure, demand, flowrate, wn, self.h_star
        )  

        expected = 0.22
        error = abs(todini[0] - expected)
        # print(todini[0], expected, error)
        self.assertLess(error, 0.01)

    def test_Todini_Fig2_optCost_CMH(self):
        inp_file = join(datadir, "Todini_Fig2_optCost_CMH.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        # Compute todini index
        head = results.node["head"]
        pressure = results.node["pressure"]
        demand = results.node["demand"]
        flowrate = results.link["flowrate"]
        todini = wntr.metrics.todini_index(
            head, pressure, demand, flowrate, wn, self.h_star
        )  

        expected = 0.22
        error = abs(todini[0] - expected)
        # print(todini[0], expected, error)
        self.assertLess(error, 0.01)

    def test_Todini_Fig2_solA_GPM(self):
        inp_file = join(datadir, "Todini_Fig2_solA_GPM.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        # Compute todini index
        head = results.node["head"]
        pressure = results.node["pressure"]
        demand = results.node["demand"]
        flowrate = results.link["flowrate"]
        todini = wntr.metrics.todini_index(
            head, pressure, demand, flowrate, wn, self.h_star
        )  

        expected = 0.41
        error = abs(todini[0] - expected)
        # print(todini[0], expected, error)
        self.assertLess(error, 0.03)

    def test_Todini_Fig2_solA_CMH(self):
        inp_file = join(datadir, "Todini_Fig2_solA_CMH.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        # Compute todini index
        head = results.node["head"]
        pressure = results.node["pressure"]
        demand = results.node["demand"]
        flowrate = results.link["flowrate"]
        todini = wntr.metrics.todini_index(
            head, pressure, demand, flowrate, wn, self.h_star
        ) 

        expected = 0.41
        error = abs(todini[0] - expected)
        # print(todini[0], expected, error)
        self.assertLess(error, 0.03)

class TestMRIMetric(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        inp_file = join(ex_datadir, "Net3.inp")
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.duration = 2*24*3600 # 2 days
        sim = wntr.sim.WNTRSimulator(self.wn)
        self.results = sim.run_sim()
    
    @classmethod
    def tearDownClass(self):
        pass
    
    def test_MRI(self):
        
        elevation = self.wn.query_node_attribute('elevation').loc[self.wn.junction_name_list]
        pressure = self.results.node["pressure"].loc[:,self.wn.junction_name_list]
        demand = self.results.node["demand"].loc[:,self.wn.junction_name_list]
        
        temp = demand.sum()
        nzd_nodes = temp[temp>0].index
        
        average_system_pressure = pressure.loc[:,nzd_nodes].mean().mean()
        Pstar = pressure.loc[:,nzd_nodes].min().min()
        #print(Pstar)
        
        mri_per_junction = wntr.metrics.modified_resilience_index(pressure, elevation, Pstar)
        mri_per_junction_nzd = wntr.metrics.modified_resilience_index(pressure.loc[:,nzd_nodes], elevation[nzd_nodes], Pstar)
        
        mri = wntr.metrics.modified_resilience_index(pressure, elevation, Pstar, demand, False)
        mri_nzd = wntr.metrics.modified_resilience_index(pressure.loc[:,nzd_nodes], elevation[nzd_nodes], Pstar, demand.loc[:,nzd_nodes], False)

        # import matplotlib.pylab as plt
        
        # fig, axes = plt.subplots(2,1, figsize=(5,10))
        # pressure.plot(title='Pressure at junctions', legend=False, ax=axes[0])
        # pressure.loc[:,nzd_nodes].plot(title='Pressure at NZD junctions', legend=False, ax=axes[1])
        
        # fig, axes = plt.subplots(2,1, figsize=(5,10))
        # mri_per_junction.plot(title='MRI at junctions', legend=False, ax=axes[0])
        # mri_per_junction_nzd.plot(title='MRI at NZD junctions', legend=False, ax=axes[1])
        
        # fig, axes = plt.subplots(2,1, figsize=(5,10))
        # mri.plot(title='MRI system average', legend=False, ax=axes[0])
        # mri_nzd.plot(title='MRI system average at NZD junctions', legend=False, ax=axes[1])
        
        assert_series_equal(mri, mri_nzd, check_dtype=False) # system mri over all junctions = system average over demand junctions
        assert_frame_equal(mri_per_junction.loc[:,nzd_nodes], mri_per_junction_nzd, check_dtype=False) 
        
        self.assertEqual(mri_per_junction_nzd.min().min(), 0) # the min is 0 because Pstar is the min required pressure
        self.assertLess(mri_per_junction_nzd.max().max(), 1) # for this example, mri per junction is < 1
        
if __name__ == "__main__":
    unittest.main()
