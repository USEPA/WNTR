# These tests test controls
import unittest
import warnings
from os.path import abspath, dirname, join

import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestValveSettingControls(unittest.TestCase):
    def test_status_open_when_setting_changes(self):
        wn = wntr.network.WaterNetworkModel()
        wn.add_reservoir("r1", base_head=10)
        wn.add_junction("j1", base_demand=0)
        wn.add_junction("j2", base_demand=0.05)
        wn.add_pipe("p1", "r1", "j1")
        wn.add_valve("v1", "j1", "j2", valve_type="PRV", initial_setting=2)
        wn.options.time.duration = 3600 * 5

        action = wntr.network.ControlAction(
            wn.get_link("v1"), "status", wntr.network.LinkStatus.Closed
        )
        condition = wntr.network.SimTimeCondition(wn, "==", 0)
        control = wntr.network.Control(condition=condition, then_action=action)
        wn.add_control("close_valve", control)

        action = wntr.network.ControlAction(wn.get_link("v1"), "setting", 2)
        condition = wntr.network.SimTimeCondition(wn, "==", 7200)
        control = wntr.network.Control(condition=condition, then_action=action)
        wn.add_control("valve_setting", control)

        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
        self.assertEqual(
            results.link["status"].at[7200, "v1"], wntr.network.LinkStatus.Active
        )


class TestPumpSettingControls(unittest.TestCase):
    def test_status_open_when_setting_changes(self):
        wn = wntr.network.WaterNetworkModel()
        wn.add_reservoir("r1", base_head=10)
        wn.add_junction("j1", base_demand=0)
        wn.add_junction("j2", base_demand=0.1)
        wn.add_junction("j3", base_demand=0.05)
        wn.add_pipe("p1", "r1", "j1")
        wn.add_pipe("p2", "j1", "j3")
        wn.add_curve("pump_curve", "HEAD", [(0.1, 3)])
        wn.add_pump("pump1", "j1", "j2", pump_type="HEAD", pump_parameter="pump_curve")
        wn.options.time.duration = 3600 * 5

        action = wntr.network.ControlAction(
            wn.get_link("pump1"), "status", wntr.network.LinkStatus.Closed
        )
        condition = wntr.network.SimTimeCondition(wn, "==", 0)
        control = wntr.network.Control(condition=condition, then_action=action)
        wn.add_control("close_pump", control)

        action = wntr.network.ControlAction(wn.get_link("pump1"), "base_speed", 1)
        condition = wntr.network.SimTimeCondition(wn, "==", 3600 * 2)
        control = wntr.network.Control(condition=condition, then_action=action)
        wn.add_control("pump_base_speed", control)

        sim = wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()
        self.assertEqual(
            results.link["status"].at[7200, "pump1"], wntr.network.LinkStatus.Open
        )


class TestTimeControls(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(test_datadir, "time_controls.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.time.report_timestep = "all"
        for jname, j in self.wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0

        self.wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(self.wn)
        self.results = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_time_control_open_vs_closed(self):
        res = self.results
        link_res = res.link
        for t in res.time:
            if t < 5 * 3600 or t >= 10 * 3600:
                self.assertAlmostEqual(
                    link_res["flowrate"].at[t, "pipe2"], 150 / 3600.0
                )
                self.assertEqual(
                    link_res["status"].at[t, "pipe2"], self.wntr.network.LinkStatus.Open
                )
            else:
                self.assertAlmostEqual(link_res["flowrate"].at[t, "pipe2"], 0.0)
                self.assertEqual(
                    link_res["status"].at[t, "pipe2"],
                    self.wntr.network.LinkStatus.Closed,
                )


class TestConditionalControls(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    
    def test_close_link_by_tank_level(self):
        inp_file = join(test_datadir, "conditional_controls_1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.report_timestep = "all"
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0

        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        activated_flag = False
        count = 0
        node_res = results.node
        link_res = results.link
        for t in results.time:
            if node_res["pressure"].at[t, "tank1"] >= 50.0 and not activated_flag:
                activated_flag = True
            if activated_flag:
                self.assertAlmostEqual(link_res["flowrate"].at[t, "pump1"], 0.0)
                self.assertEqual(
                    link_res["status"].at[t, "pump1"],
                    self.wntr.network.LinkStatus.Closed,
                )
                count += 1
            else:
                self.assertGreaterEqual(link_res["flowrate"].at[t, "pump1"], 0.0001)
                self.assertEqual(
                    link_res["status"].loc[t, "pump1"],
                    self.wntr.network.LinkStatus.Open,
                )
        self.assertEqual(activated_flag, True)
        self.assertGreaterEqual(count, 2)

    def test_update_priority(self):
        inp_file = join(test_datadir, "conditional_controls_1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        new_priority =1 
        idx = 0
        # check current priority is different to the new one
        self.assertNotEqual(wn.get_control(wn.control_name_list[idx]).priority, new_priority)
        # Update priority and check it has worked
        wn.get_control(wn.control_name_list[idx]).update_priority(new_priority)
        self.assertEqual(wn.get_control(wn.control_name_list[idx]).priority, new_priority)

    def test_update_conditions(self):
        inp_file = join(test_datadir, "conditional_controls_1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        idx = 0
        new_condition = self.wntr.network.controls.TimeOfDayCondition(wn, 'Is','01:00:00')

        self.assertNotEqual(wn.get_control(wn.control_name_list[idx]).condition, new_condition)
        wn.get_control(wn.control_name_list[idx]).update_condition(new_condition)
        self.assertEqual(wn.get_control(wn.control_name_list[idx]).condition, new_condition)


    def test_update_then_actions(self):
        inp_file = join(test_datadir, "conditional_controls_1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        link_num=0
        link = wn.get_link(wn.link_name_list[link_num])

        new_action = self.wntr.network.controls.ControlAction(link, 'status', 0)
        # When updating then_actions, the action will be made iterable, we need to make it iterable too.
        iterable_action = self.wntr.network.controls._ensure_iterable(new_action)

        self.assertNotEqual(wn.get_control(wn.control_name_list[0])._then_actions,iterable_action)
        wn.get_control(wn.control_name_list[0]).update_then_actions(new_action)
        self.assertEqual(wn.get_control(wn.control_name_list[0])._then_actions,iterable_action)

    def test_update_else_actions(self):
        inp_file = join(test_datadir, "conditional_controls_1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        link_num=0
        link = wn.get_link(wn.link_name_list[link_num])

        new_action = self.wntr.network.controls.ControlAction(link, 'status', 0)
        # When updating then_actions, the action will be made iterable, we need to make it iterable too.
        iterable_action = self.wntr.network.controls._ensure_iterable(new_action)

        self.assertNotEqual(wn.get_control(wn.control_name_list[0])._else_actions,iterable_action)
        wn.get_control(wn.control_name_list[0]).update_else_actions(new_action)
        self.assertEqual(wn.get_control(wn.control_name_list[0])._else_actions,iterable_action)

    def test_open_link_by_tank_level(self):
        inp_file = join(test_datadir, "conditional_controls_2.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.report_timestep = "all"
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0
        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        activated_flag = False
        count = 0  # Used to make sure the link is opened for at least 2 timesteps to make sure the link stays open
        for t in results.node["pressure"].index:
            if results.node["pressure"].at[t, "tank1"] >= 300.0 and not activated_flag:
                activated_flag = True
            if activated_flag:
                self.assertGreaterEqual(results.link["flowrate"].at[t, "pipe1"], 0.002)
                self.assertEqual(
                    results.link["status"].at[t, "pipe1"],
                    self.wntr.network.LinkStatus.Open,
                )
                count += 1
            else:
                self.assertAlmostEqual(results.link["flowrate"].at[t, "pipe1"], 0.0)
                self.assertEqual(
                    results.link["status"].at[t, "pipe1"],
                    self.wntr.network.LinkStatus.Closed,
                )
        self.assertEqual(activated_flag, True)
        self.assertGreaterEqual(count, 2)
        self.assertEqual(
            results.link["status"].at[results.link["status"].index[0], "pipe1"],
            self.wntr.network.LinkStatus.Closed,
        )  # make sure the pipe starts closed
        self.assertLessEqual(
            results.node["pressure"].at[results.node["pressure"].index[0], "tank1"],
            300.0,
        )  # make sure the pipe starts closed


class TestTankControls(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_pipe_closed_for_low_level(self):
        inp_file = join(test_datadir, "tank_controls_1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0
        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        tank_level_dropped_flag = False
        for t in results.node["pressure"].index:
            if results.node["pressure"].at[t, "tank1"] <= 10.0:
                self.assertLessEqual(results.link["flowrate"].at[t, "pipe1"], 0.0)
                self.assertEqual(
                    results.link["status"].at[t, "pipe1"],
                    self.wntr.network.LinkStatus.Closed,
                )
                tank_level_dropped_flag = True
        self.assertEqual(tank_level_dropped_flag, True)

    def test_reopen_pipe_after_tank_fills_back_up(self):
        """
        inp_file = join(test_datadir, 'tank_controls_2.inp')
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0
        wn.options.hydraulic.demand_model = 'PDA'
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        tank_level_dropped_flag = False
        tank_refilled_flag = False
        for t in results.time:
            if results.node.loc['pressure',t,'tank1'] <= 10.0:
                self.assertLessEqual(results.link.loc['flowrate',t,'pipe1'],0.0)
                tank_level_dropped_flag = True
            elif results.node.loc['pressure',t,'tank1'] > 10.0:
                self.assertGreaterEqual(results.link.loc['flowrate',t,'pipe1'],0.001)
                if tank_level_dropped_flag:
                    tank_refilled_flag = True
        self.assertEqual(tank_level_dropped_flag, True)
        self.assertEqual(tank_refilled_flag, True)
        """
        raise unittest.SkipTest
        self.assertEqual(True, False)


class TestValveControls(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_check_valve_closed(self):
        inp_file = join(test_datadir, "cv_controls.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0
        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        flowrate = results.link["flowrate"]
        for t in flowrate.index:
            self.assertAlmostEqual(flowrate.at[t, "pipe1"], 0.0)

    def test_check_valve_opened(self):
        inp_file = join(test_datadir, "cv_controls.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        tank1 = wn.get_node("tank1")
        tank2 = wn.get_node("tank2")
        tank1_init_level = tank1.init_level
        tank1.init_level = tank2.init_level
        tank2.init_level = tank1_init_level
        tank1._head = tank1.init_level + tank1.elevation
        tank2._head = tank2.init_level + tank2.elevation
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0
        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        flag1 = False
        flag2 = False
        for t in results.node["head"].index:
            if (
                results.node["head"].at[t, "tank1"]
                >= results.node["head"].at[t, "tank2"]
            ):
                self.assertGreaterEqual(results.link["flowrate"].at[t, "pipe1"], 0.001)
                flag1 = True
            else:
                self.assertAlmostEqual(results.link["flowrate"].at[t, "pipe1"], 0.0)
                flag2 = True

        self.assertEqual(flag1, True)
        self.assertEqual(flag2, True)


class TestControlCombinations(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_open_by_time_close_by_condition(self):
        inp_file = join(test_datadir, "control_comb.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        control_action = self.wntr.network.ControlAction(
            wn.get_link("pipe1"), "status", self.wntr.network.LinkStatus.Opened
        )
        control = self.wntr.network.controls.Control._time_control(
            wn, 6 * 3600, "SIM_TIME", False, control_action
        )
        wn.add_control("open_time_6", control)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0
        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        flag1 = False
        flag2 = False
        for t in results.node["head"].index:
            if t == 6 * 3600:
                flag1 = True
            if (
                t > 0
                and (
                    results.node["head"].at[t - 3600, "tank1"]
                    + (
                        results.node["demand"].at[t - 3600, "tank1"]
                        * 3600
                        * 4
                        / (3.14159 * wn.get_node("tank1").diameter ** 2)
                    )
                )
                <= 30
            ):
                flag1 = False
                flag2 = True
            if flag1 == False:
                self.assertAlmostEqual(results.link["flowrate"].at[t, "pipe1"], 0.0)
            elif flag1 == True:
                self.assertGreaterEqual(results.link["flowrate"].at[t, "pipe1"], 0.001)

        self.assertEqual(flag1, False)
        self.assertEqual(flag2, True)

    def test_close_by_condition_open_by_time_stay(self):
        inp_file = join(test_datadir, "control_comb.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        tank1 = wn.get_node("tank1")
        tank1.init_level = 40.0
        tank1._head = tank1.elevation + 40.0
        pipe1 = wn.get_link("pipe1")
        pipe1._user_status = self.wntr.network.LinkStatus.Opened
        control_action = self.wntr.network.ControlAction(
            wn.get_link("pipe1"), "status", self.wntr.network.LinkStatus.Opened
        )
        control = self.wntr.network.controls.Control._time_control(
            wn, 19 * 3600, "SIM_TIME", False, control_action
        )
        wn.add_control("open_time_19", control)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0
        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        flag1 = False
        flag2 = False
        for t in results.node["head"].index:
            if t == 19 * 3600:
                flag1 = False
            if (
                t > 0
                and (
                    results.node["head"].at[t - 3600, "tank1"]
                    + (
                        results.node["demand"].at[t - 3600, "tank1"]
                        * 3600
                        * 4
                        / (3.14159 * wn.get_node("tank1").diameter ** 2)
                    )
                )
                <= 30
            ):
                flag1 = True
                flag2 = True
            if flag1 == False:
                self.assertGreaterEqual(results.link["flowrate"].at[t, "pipe1"], 0.001)
            elif flag1 == True:
                self.assertAlmostEqual(results.link["flowrate"].at[t, "pipe1"], 0.0)

        self.assertEqual(flag1, False)
        self.assertEqual(flag2, True)

    def test_close_by_condition_open_by_time_reclose(self):
        inp_file = join(test_datadir, "control_comb.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        tank1 = wn.get_node("tank1")
        tank1.init_level = 40.0
        tank1._head = tank1.elevation + 40.0
        pipe1 = wn.get_link("pipe1")
        pipe1._user_status = self.wntr.network.LinkStatus.Opened
        control_action = self.wntr.network.ControlAction(
            wn.get_link("pipe1"), "status", self.wntr.network.LinkStatus.Opened
        )
        control = self.wntr.network.controls.Control._time_control(
            wn, 5 * 3600, "SIM_TIME", False, control_action
        )
        wn.add_control("open_time_5", control)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.required_pressure = 15.0
        wn.options.hydraulic.demand_model = "PDA"
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        flag1 = False
        for t in results.node["head"].index:
            if (
                t > 0
                and (
                    results.node["head"].at[t - 3600, "tank1"]
                    + (
                        results.node["demand"].at[t - 3600, "tank1"]
                        * 3600
                        * 4
                        / (3.14159 * wn.get_node("tank1").diameter ** 2)
                    )
                )
                <= 30.0
            ):
                flag1 = True
            if t == 5 * 3600:
                flag1 = False
            if flag1 == False:
                self.assertGreaterEqual(results.link["flowrate"].at[t, "pipe1"], 0.001)
            elif flag1 == True:
                self.assertAlmostEqual(results.link["flowrate"].at[t, "pipe1"], 0.0)

        self.assertEqual(flag1, True)


if __name__ == "__main__":
    unittest.main()
