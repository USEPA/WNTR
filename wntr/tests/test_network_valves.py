import unittest
from unittest import SkipTest
import wntr
from os.path import abspath, dirname, join


testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")


class TestTCVs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_pipe_minor_loss(self):

        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 4
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.1)
        wn.add_pipe(
            name="p1",
            start_node_name="r1",
            end_node_name="j1",
            length=10.0,
            diameter=0.3048,
            roughness=100,
            minor_loss=0.0,
        )
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3048,
            valve_type="TCV",
            minor_loss=30.0,
            initial_setting=60.0,
        )

        valve = wn.get_link("v1")
        open_action = wntr.network.ControlAction(
            valve, "status", wntr.network.LinkStatus.Opened
        )
        control = wntr.network.controls.Control._time_control(
            wn, 7200, time_flag="SIM_TIME", daily_flag=False, control_action=open_action
        )
        wn.add_control("c1", control)

        wn.options.hydraulic.demand_model = "DDA"
        sim = wntr.sim.WNTRSimulator(wn)
        results1 = sim.run_sim()

        sim = wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()

        for t in results2.node["head"].index:
            head1 = results1.node["head"].loc[t, "j2"]
            head2 = results2.node["head"].loc[t, "j2"]
            head_diff = abs(head1 - head2)
            self.assertLess(head_diff, 0.01)


class TestPSVs(unittest.TestCase):
    def test_active(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 4
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t1", init_level=10.0, max_level=25, min_vol=0.0)
        wn.add_pipe(name="p1", start_node_name="r1", end_node_name="j1", diameter=0.2)
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3,
            valve_type="PSV",
            minor_loss=100.0,
            initial_setting=18,
        )
        wn.add_pipe(name="p3", start_node_name="t1", end_node_name="j2")

        sim = wntr.sim.WNTRSimulator(wn)
        res = sim.run_sim()

        for t in res.time:
            self.assertEqual(res.link["status"].loc[t, "v1"], 2)
            self.assertAlmostEqual(res.node["head"].loc[t, "j1"], 18)

    def test_open(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 4
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t1", init_level=10.0, max_level=25, min_vol=0.0)
        wn.add_pipe(name="p1", start_node_name="r1", end_node_name="j1", diameter=0.2)
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3,
            valve_type="PSV",
            minor_loss=100.0,
            initial_setting=10,
        )
        wn.add_pipe(name="p3", start_node_name="t1", end_node_name="j2")

        sim = wntr.sim.WNTRSimulator(wn)
        res = sim.run_sim()

        for t in res.time:
            self.assertEqual(res.link["status"].loc[t, "v1"], 1)

    def test_active_to_open_to_close(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 4
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t1", init_level=10.0, max_level=25, min_vol=0.0)
        wn.add_reservoir(name="r2", base_head=30)
        wn.add_pipe(name="p1", start_node_name="r1", end_node_name="j1", diameter=0.2)
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3,
            valve_type="PSV",
            minor_loss=100.0,
            initial_setting=15,
        )
        wn.add_pipe(name="p3", start_node_name="t1", end_node_name="j2")
        wn.add_pipe(name="p4", start_node_name="r2", end_node_name="t1")

        sim = wntr.sim.WNTRSimulator(wn)
        res = sim.run_sim()

        self.assertEqual(res.link["status"].loc[0, "v1"], 2)
        self.assertEqual(res.link["status"].loc[3600, "v1"], 1)
        self.assertEqual(res.link["status"].loc[7200, "v1"], 0)
        self.assertEqual(res.link["status"].loc[10800, "v1"], 0)
        self.assertEqual(res.link["status"].loc[14400, "v1"], 0)

    def test_active_to_open(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 4
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t1", init_level=10.0, max_level=25, min_vol=0.0)
        wn.add_pipe(name="p1", start_node_name="r1", end_node_name="j1", diameter=0.2)
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3,
            valve_type="PSV",
            minor_loss=100.0,
            initial_setting=15,
        )
        wn.add_pipe(name="p3", start_node_name="t1", end_node_name="j2")

        sim = wntr.sim.WNTRSimulator(wn)
        res = sim.run_sim()

        self.assertEqual(res.link["status"].loc[0, "v1"], 2)
        self.assertEqual(res.link["status"].loc[3600, "v1"], 2)
        self.assertEqual(res.link["status"].loc[7200, "v1"], 2)
        self.assertEqual(res.link["status"].loc[10800, "v1"], 1)
        self.assertEqual(res.link["status"].loc[14400, "v1"], 1)

    def test_close(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 4
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t1", init_level=10.0, max_level=25, min_vol=0.0)
        wn.add_pipe(name="p1", start_node_name="r1", end_node_name="j1", diameter=0.2)
        wn.add_valve(
            name="v1",
            start_node_name="j2",
            end_node_name="j1",
            diameter=0.3,
            valve_type="PSV",
            minor_loss=100.0,
            initial_setting=15,
        )
        wn.add_pipe(name="p3", start_node_name="t1", end_node_name="j2")

        sim = wntr.sim.WNTRSimulator(wn)
        res = sim.run_sim()

        self.assertEqual(res.link["status"].loc[0, "v1"], 0)
        self.assertEqual(res.link["status"].loc[3600, "v1"], 0)
        self.assertEqual(res.link["status"].loc[7200, "v1"], 0)
        self.assertEqual(res.link["status"].loc[10800, "v1"], 0)
        self.assertEqual(res.link["status"].loc[14400, "v1"], 0)

    def test_close_to_open_to_active(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 12
        wn.add_reservoir(name="t0", base_head=30)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t1", init_level=40.0, max_level=100, min_vol=0.0)
        wn.add_tank(name="t2", init_level=0, max_level=100)
        wn.add_pipe(name="p1", start_node_name="t0", end_node_name="j1", diameter=0.2)
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3,
            valve_type="PSV",
            minor_loss=100.0,
            initial_setting=25,
        )
        wn.add_pipe(name="p3", start_node_name="j2", end_node_name="t1")
        wn.add_pipe(name="p4", start_node_name="t1", end_node_name="t2")

        sim = wntr.sim.WNTRSimulator(wn)
        res = sim.run_sim()
        # print(res.node['head'])
        # print(res.link['flowrate'])
        # print(res.link['status'])

        self.assertEqual(res.link["status"].loc[0, "v1"], 0)
        self.assertEqual(res.link["status"].loc[3600, "v1"], 0)
        self.assertEqual(res.link["status"].loc[7200, "v1"], 1)
        self.assertEqual(res.link["status"].loc[10800, "v1"], 2)
        self.assertEqual(res.link["status"].loc[14400, "v1"], 2)


class TestFCVs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_active_FCV(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 4
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t1", init_level=10.0, max_level=25.0, min_vol=0.0)
        wn.add_pipe(
            name="p1",
            start_node_name="r1",
            end_node_name="j1",
            length=1000.0,
            diameter=0.3048,
            roughness=100,
            minor_loss=0.0,
        )
        wn.add_pipe(
            name="p2",
            start_node_name="j2",
            end_node_name="t1",
            length=1000.0,
            diameter=0.3048,
            roughness=100,
            minor_loss=0.0,
        )
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3048,
            valve_type="FCV",
            minor_loss=100.0,
            initial_setting=0.01,
        )

        sim = wntr.sim.WNTRSimulator(wn)
        results1 = sim.run_sim()

        sim = wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()

        for t in results2.link["flowrate"].index:
            self.assertAlmostEqual(results1.link["flowrate"].loc[t, "v1"], 0.01, 7)
            self.assertAlmostEqual(results2.link["flowrate"].loc[t, "v1"], 0.01, 7)

    def test_open_FCV(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 4
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t1", init_level=10.0, max_level=25.0, min_vol=0.0)
        wn.add_pipe(
            name="p1",
            start_node_name="r1",
            end_node_name="j1",
            length=1000.0,
            diameter=0.3048,
            roughness=100,
            minor_loss=0.0,
        )
        wn.add_pipe(
            name="p2",
            start_node_name="j2",
            end_node_name="t1",
            length=1000.0,
            diameter=0.3048,
            roughness=100,
            minor_loss=0.0,
        )
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3048,
            valve_type="FCV",
            minor_loss=100.0,
            initial_setting=0.1,
        )

        sim = wntr.sim.WNTRSimulator(wn)
        results1 = sim.run_sim()

        sim = wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()

        for t in results2.link["flowrate"].index:
            self.assertLess(
                abs(
                    results1.link["flowrate"].loc[t, "v1"]
                    - results2.link["flowrate"].loc[t, "v1"]
                ),
                1e-5,
            )
            self.assertLess(results1.link["flowrate"].loc[t, "v1"], 0.09)

    def test_open_to_active_FCV(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 10
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_tank(name="t1", init_level=10.0, max_level=25.0, min_vol=0.0)
        wn.add_junction(name="j1", base_demand=0.0)
        wn.add_junction(name="j2", base_demand=0.0)
        wn.add_tank(name="t2", init_level=10.0, max_level=25.0, min_vol=0.0)
        wn.add_pipe(
            name="p0",
            start_node_name="r1",
            end_node_name="t1",
            length=1000.0,
            diameter=0.3048,
            roughness=100,
            minor_loss=0.0,
        )
        wn.add_pipe(
            name="p1",
            start_node_name="t1",
            end_node_name="j1",
            length=1000.0,
            diameter=0.3048,
            roughness=100,
            minor_loss=0.0,
        )
        wn.add_pipe(
            name="p2",
            start_node_name="j2",
            end_node_name="t2",
            length=1000.0,
            diameter=0.3048,
            roughness=100,
            minor_loss=0.0,
        )
        wn.add_valve(
            name="v1",
            start_node_name="j1",
            end_node_name="j2",
            diameter=0.3048,
            valve_type="FCV",
            minor_loss=100.0,
            initial_setting=0.03,
        )

        sim = wntr.sim.WNTRSimulator(wn)
        results1 = sim.run_sim()

        sim = wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()

        for t in results2.link["flowrate"].index:
            self.assertLess(
                abs(
                    results1.link["flowrate"].loc[t, "v1"]
                    - results2.link["flowrate"].loc[t, "v1"]
                ),
                1e-4,
            )
            if t > 7200:
                self.assertLess(
                    abs(results1.link["flowrate"].loc[t, "v1"] - 0.03), 1e-8
                )

        self.assertLess(abs(results1.link["flowrate"].loc[0, "v1"] - 0.0), 1e-4)
        self.assertLess(
            abs(results1.link["flowrate"].loc[3600, "v1"] - 0.0245344210416), 1e-5
        )
        self.assertLess(
            abs(results1.link["flowrate"].loc[7200, "v1"] - 0.0293480847031), 1e-5
        )


class TestValveIsolation(unittest.TestCase):
    def test_psv_open(self):
        wn = wntr.network.WaterNetworkModel(inp_file_name=join(test_datadir, 'psv_open_no_downstream_sources.inp'))
        
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
        self.assertTrue(results.error_code != 0)
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == wntr.network.LinkStatus.Opened).all())
        
        sim = wntr.sim.EpanetSimulator(wn)
        results_epanet = sim.run_sim()
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == results_epanet.link['status'].loc[:, 'VALVE']).all())

    def test_prv_open(self):
        wn = wntr.network.WaterNetworkModel(inp_file_name=join(test_datadir, 'prv_open_no_upstream_sources.inp'))
        
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
        self.assertTrue(results.error_code != 0)
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == wntr.network.LinkStatus.Opened).all())
        
        sim = wntr.sim.EpanetSimulator(wn)
        results_epanet = sim.run_sim()
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == results_epanet.link['status'].loc[:, 'VALVE']).all())

    def test_prv_closed(self):
        wn = wntr.network.WaterNetworkModel(inp_file_name=join(test_datadir, 'prv_closed_no_upstream_sources.inp'))
        
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
        self.assertTrue(results.error_code != 0)
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == wntr.network.LinkStatus.Closed).all())
        
        sim = wntr.sim.EpanetSimulator(wn)
        results_epanet = sim.run_sim()
        raise SkipTest # EPANET valve should be closed, but is open and has flow at a few timesteps
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == results_epanet.link['status'].loc[:, 'VALVE']).all())

    def test_fcv_open_no_downstream_sources(self):
        wn = wntr.network.WaterNetworkModel(inp_file_name=join(test_datadir, 'fcv_open_no_downstream_sources.inp'))

        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
        self.assertTrue(results.error_code != 0)
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == wntr.network.LinkStatus.Opened).all())
        
        sim = wntr.sim.EpanetSimulator(wn)
        results_epanet = sim.run_sim()
        raise SkipTest  # EPANET valve should be open, but is active; pressures at some junctions are very negative
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == results_epanet.link['status'].loc[:, 'VALVE']).all())

    def test_fcv_open_no_upstream_sources(self):
        wn = wntr.network.WaterNetworkModel(inp_file_name=join(test_datadir, 'fcv_open_no_upstream_sources.inp'))
        
        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
        self.assertTrue(results.error_code != 0)
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == wntr.network.LinkStatus.Opened).all())
        
        sim = wntr.sim.EpanetSimulator(wn)
        results_epanet = sim.run_sim()
        self.assertTrue((results.link['status'].loc[:, 'VALVE'] == results_epanet.link['status'].loc[:, 'VALVE']).all())

if __name__ == "__main__":
    unittest.main()
