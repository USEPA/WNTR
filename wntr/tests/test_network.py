import unittest
import warnings
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr
from wntr.network.controls import Control, Rule

testdir = dirname(abspath(str(__file__)))
test_network_dir = join(testdir, "networks_for_testing")
test_data_dir = join(testdir, "data_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestNetworkCreation(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net6.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)

    @classmethod
    def tearDownClass(self):
        pass

    def test_num_junctions(self):
        self.assertEqual(self.wn.num_junctions, 3323)

    def test_num_reservoirs(self):
        self.assertEqual(self.wn.num_reservoirs, 1)

    def test_num_tanks(self):
        self.assertEqual(self.wn.num_tanks, 32)

    def test_num_pipes(self):
        self.assertEqual(self.wn.num_pipes, 3829)

    def test_num_pumps(self):
        self.assertEqual(self.wn.num_pumps, 61)

    def test_num_valves(self):
        self.assertEqual(self.wn.num_valves, 2)

    def test_num_nodes(self):
        self.assertEqual(self.wn.num_nodes, 3323 + 1 + 32)

    def test_num_links(self):
        self.assertEqual(self.wn.num_links, 3829 + 61 + 2)

    def test_junction_attr(self):
        j = self.wn.get_node("JUNCTION-18")
        # self.assertAlmostEqual(j.base_demand, 48.56/60.0*0.003785411784)
        self.assertEqual(j.demand_timeseries_list[0].pattern_name, "PATTERN-2")
        self.assertAlmostEqual(j.elevation, 80.0 * 0.3048)

    def test_reservoir_attr(self):
        j = self.wn.get_node("RESERVOIR-3323")
        self.assertAlmostEqual(j.head_timeseries.base_value, 27.45 * 0.3048)
        self.assertEqual(j.head_timeseries.pattern_name, None)


class TestNetworkMethods(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr
        from wntr.network.controls import Control, ControlAction
        from wntr.network.model import Junction, Pipe, Pump, Reservoir, Tank, Valve

        self.Junction = Junction
        self.Tank = Tank
        self.Reservoir = Reservoir
        self.Pipe = Pipe
        self.Pump = Pump
        self.Valve = Valve
        self.wntr = wntr
        self.ControlAction = ControlAction
        self.TimeControl = Control._time_control

    @classmethod
    def tearDownClass(self):
        pass

    def test_add_junction(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_pattern("pattern1", [1])
        wn.add_junction("j1", 150, "pattern1", 15)
        j = wn.get_node("j1")
        self.assertEqual(j._name, "j1")
        # self.assertEqual(j.base_demand, 150.0)
        self.assertEqual(j.demand_timeseries_list[0].pattern_name, "pattern1")
        self.assertEqual(j.elevation, 15.0)
        self.assertEqual(list(wn.node_name_list), ["j1"])
        # self.assertEqual(type(j.base_demand), float)
        self.assertEqual(type(j.elevation), float)

    def test_add_tank(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_tank("t1", 15, 75, 0, 100, 10, 0)
        n = wn.get_node("t1")
        self.assertEqual(n._name, "t1")
        self.assertEqual(n.elevation, 15.0)
        self.assertEqual(n.init_level, 75.0)
        self.assertEqual(n.min_level, 0.0)
        self.assertEqual(n.max_level, 100.0)
        self.assertEqual(n.diameter, 10.0)
        self.assertEqual(n.min_vol, 0.0)
        self.assertEqual(list(wn.node_name_list), ["t1"])
        self.assertEqual(type(n.elevation), float)
        self.assertEqual(type(n.init_level), float)
        self.assertEqual(type(n.min_level), float)
        self.assertEqual(type(n.max_level), float)
        self.assertEqual(type(n.diameter), float)
        self.assertEqual(type(n.min_vol), float)

    def test_add_reservoir(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_pattern("pattern1", [1])
        wn.add_reservoir("r1", 30, "pattern1")
        n = wn.get_node("r1")
        self.assertEqual(n._name, "r1")
        self.assertEqual(n.head_timeseries.base_value, 30.0)
        self.assertEqual(n.head_timeseries.pattern_name, "pattern1")
        self.assertEqual(list(wn.node_name_list), ["r1"])

    def test_add_pipe(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_pipe("p1", "j1", "j2", 1000, 1, 100, 0, "Open")
        l = wn.get_link("p1")
        self.assertEqual(l.name, "p1")
        self.assertEqual(l.start_node_name, "j1")
        self.assertEqual(l.end_node_name, "j2")
        self.assertEqual(l.initial_status, self.wntr.network.LinkStatus.opened)
        self.assertEqual(l.length, 1000.0)
        self.assertEqual(l.diameter, 1.0)
        self.assertEqual(l.roughness, 100.0)
        self.assertEqual(l.minor_loss, 0.0)
        self.assertEqual(type(l.length), float)
        self.assertEqual(type(l.diameter), float)
        self.assertEqual(type(l.roughness), float)
        self.assertEqual(type(l.minor_loss), float)

    def test_add_pattern(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.options.time.duration = 10
        wn.options.time.pattern_timestep = 1
        #        wn.add_pattern('pat1', start_time=2, end_time=4)
        pat1 = self.wntr.network.elements.Pattern.binary_pattern(
            "pat1", start_time=2, end_time=4, duration=10, step_size=1
        )
        wn.add_pattern("pat1", pat1)
        wn.add_pattern("pat2", [1, 2, 3, 4])

        pat1 = wn.get_pattern("pat1")
        pat2 = wn.get_pattern("pat2")

        self.assertEqual(
            pat1.multipliers.tolist(),
            [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        )
        self.assertEqual(pat2.multipliers.tolist(), [1, 2, 3, 4])

    def test_add_source(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.options.time.duration = 10
        wn.options.time.pattern_timestep = 1
        pat1 = self.wntr.network.elements.Pattern.binary_pattern(
            "pat1",
            start_time=2,
            end_time=4,
            duration=10,
            step_size=wn.options.time.pattern_timestep,
        )
        wn.add_pattern("pat1", pat1)
        wn.add_source("s1", "j1", "SETPOINT", 100, "pat1")
        s = wn.get_source("s1")
        self.assertEqual(s.name, "s1")
        self.assertEqual(s.node_name, "j1")
        self.assertEqual(s.source_type, "SETPOINT")
        self.assertEqual(s.strength_timeseries.base_value, 100)
        self.assertEqual(s.strength_timeseries.pattern_name, "pat1")

    def test_add_pipe_with_cv(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_pipe("p1", "j1", "j2", 1000, 1, 100, 0, "OPEN", True)
        self.assertTrue(wn.get_link('p1').check_valve)

    def test_remove_pipe(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_junction("j3")
        wn.add_pipe("p2", "j1", "j3")
        wn.add_pipe("p1", "j1", "j2", initial_status=self.wntr.network.LinkStatus.CV)
        wn.remove_link("p1")
        link_list = [link_name for link_name, link in wn.links()]
        self.assertEqual(link_list, ["p2"])
        self.assertEqual(wn.num_pipes, 1)

    def test_remove_node(self):
        inp_file = join(ex_datadir, "Net6.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)

        links_to_remove = wn.get_links_for_node("TANK-3326")
        for l in links_to_remove:
            wn.remove_link(l, with_control=True)
        wn.remove_node("TANK-3326", with_control=True)

        self.assertNotIn("TANK-3326", {name for name, node in wn.nodes()})
        self.assertNotIn("TANK-3326", wn.node_name_list)

        inp_file = join(test_network_dir, "conditional_controls_1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)

        tank1 = wn.get_node("tank1")
        action = self.ControlAction(tank1, "elevation", 55)
        control = self.TimeControl(wn, 3652, "SIM_TIME", False, action)
        wn.add_control("tank_control", control)

        controls_1 = {c_name for c_name, c in wn.controls()}

        links_to_remove = wn.get_links_for_node("tank1")
        for l in links_to_remove:
            wn.remove_link(l, with_control=True)
        wn.remove_node("tank1", with_control=True)

        controls_2 = {c_name for c_name, c in wn.controls()}

        self.assertTrue("tank_control" in controls_1)
        self.assertFalse("tank_control" in controls_2)

        self.assertNotIn("tank1", {name for name, node in wn.nodes()})
        self.assertNotIn("tank1", wn.node_name_list)
        expected_nodes = {"junction1", "res1"}
        self.assertSetEqual({name for name, node in wn.nodes()}, expected_nodes)

    def test_remove_controls_for_removing_link(self):
        inp_file = join(ex_datadir, "Net1.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)

        control_action = self.wntr.network.ControlAction(
            wn.get_link("21"), "status", self.wntr.network.LinkStatus.opened
        )
        control = self.wntr.network.controls.Control._conditional_control(
            wn.get_node("2"), "head", np.greater_equal, 10.0, control_action
        )
        wn.add_control("control_1", control)

        controls_1 = {c_name for c_name, c in wn.controls()}

        wn.remove_link("21", with_control=True)

        controls_2 = {c_name for c_name, c in wn.controls()}
        self.assertTrue("control_1" in controls_1)
        self.assertFalse("control_1" in controls_2)

    def test_nodes(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_tank("t1")
        wn.add_reservoir("r1")
        wn.add_reservoir("r2")
        wn.add_junction("j3")
        node_list = [name for name, node in wn.nodes()]
        node_list.sort()
        junction_list = [name for name, junction in wn.nodes(self.Junction)]
        junction_list.sort()
        tank_list = [name for name, tank in wn.nodes(self.Tank)]
        tank_list.sort()
        reservoir_list = [name for name, reservoir in wn.nodes(self.Reservoir)]
        reservoir_list.sort()
        self.assertEqual(node_list, ["j1", "j2", "j3", "r1", "r2", "t1"])
        self.assertEqual(junction_list, ["j1", "j2", "j3"])
        self.assertEqual(tank_list, ["t1"])
        self.assertEqual(reservoir_list, ["r1", "r2"])
        for name, node in wn.nodes():
            self.assertEqual(name, node._name)

    def test_links(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_tank("t1")
        wn.add_tank("t2")
        wn.add_reservoir("r1")
        wn.add_reservoir("r2")
        wn.add_junction("j3")
        wn.add_pipe("p1", "j1", "j2")
        wn.add_pipe("p2", "j1", "t1")
        wn.add_pipe("p3", "r1", "j1")
        wn.add_pump("pump1", "r2", "t2")
        wn.add_valve("v1", "j3", "j2")
        link_list = [name for name, link in wn.links()]
        link_list.sort()
        self.assertEqual(link_list, ["p1", "p2", "p3", "pump1", "v1"])
        pipe_list = [name for name, pipe in wn.links(self.Pipe)]
        pipe_list.sort()
        self.assertEqual(pipe_list, ["p1", "p2", "p3"])
        pump_list = [name for name, pump in wn.links(self.Pump)]
        pump_list.sort()
        self.assertEqual(pump_list, ["pump1"])
        valve_list = [name for name, valve in wn.links(self.Valve)]
        valve_list.sort()
        self.assertEqual(valve_list, ["v1"])
        for name, link in wn.links():
            self.assertEqual(name, link._link_name)

    def test_1_pt_head_curve(self):
        q2 = 10.0
        h2 = 20.0
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_curve("curve1", "HEAD", [(q2, h2)])
        curve = wn.get_curve("curve1")
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_pump("p1", "j1", "j2", "HEAD", curve.name)
        link = wn.get_link("p1")
        a, b, c = link.get_head_curve_coefficients()
        q1 = 0.0
        h1 = 4.0 / 3.0 * h2
        q3 = 2.0 * q2
        h3 = 0.0

        def curve_fun(x):
            f = [1.0, 1.0, 1.0]
            f[0] = h1 - x[0] + x[1] * q1 ** x[2]
            f[1] = h2 - x[0] + x[1] * q2 ** x[2]
            f[2] = h3 - x[0] + x[1] * q3 ** x[2]
            return f

        X = [a, b, c]
        Y = curve_fun(X)

        self.assertAlmostEqual(Y[0], 0.0)
        self.assertAlmostEqual(Y[1], 0.0)
        self.assertAlmostEqual(Y[2], 0.0)

    def test_2_pt_head_curve(self):
        q1 = 0.0
        h1 = 1.0
        q2 = 1.0
        h2 = 0.0
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_curve("curve1", "HEAD", [(q1, h1), (q2, h2)])
        curve = wn.get_curve("curve1")
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_pump("p1", "j1", "j2", "HEAD", curve.name)
        link = wn.get_link("p1")
        a, b, c = link.get_head_curve_coefficients()

        Y = [a - b, 0.5 - (a - b * (0.5) ** c), 1.0 - a]

        self.assertAlmostEqual(Y[0], 0.0)
        self.assertAlmostEqual(Y[1], 0.0)
        self.assertAlmostEqual(Y[2], 0.0)

    
    def test_3_pt_head_curve(self):
        q1 = 0.0
        h1 = 35.0
        q2 = 10.0
        h2 = 20.0
        q3 = 18.0
        h3 = 2.0
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_curve("curve1", "HEAD", [(q1, h1), (q2, h2), (q3, h3)])
        curve = wn.get_curve("curve1")
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_pump("p1", "j1", "j2", "HEAD", curve.name)
        link = wn.get_link("p1")
        a, b, c = link.get_head_curve_coefficients()

        def curve_fun(x):
            f = [1.0, 1.0, 1.0]
            f[0] = h1 - x[0] + x[1] * q1 ** x[2]
            f[1] = h2 - x[0] + x[1] * q2 ** x[2]
            f[2] = h3 - x[0] + x[1] * q3 ** x[2]
            return f

        X = [a, b, c]
        Y = curve_fun(X)

        self.assertAlmostEqual(Y[0], 0.0)
        self.assertAlmostEqual(Y[1], 0.0)
        self.assertAlmostEqual(Y[2], 0.0)

    def test_multi_pt_head_curve(self):
        # pump_curves = pump_curves_for_testing() # change this to read in a csv file

        df = pd.read_csv(join(test_data_dir, "pump_practice_curves.csv"), skiprows=5)
        pump_curves = []
        for i in range(11):
            pump_curves.append(df[df["curve number"] == i].iloc[:, 1:3])

        # these are the least squares optimal curve coefficients for
        # pump_curves!
        expected_coef = [
            (95.2793750017631, 92.93210451708887, 1.7962733026912),
            (65.73126364420834, 754.0506268456613, 3.4783989343179305),
            (21.278376275311476, 4077.4535673165924, 2.358360722834581),
            (80.75954376866605, 7027.4864048631935, 4.082009299805731),
            (136.17943689581463, 829.0733504294045, 4.489091828720322),
            (127.24246902634025, 180.0189467345297, 3.932735276445609),
            (26.851737190843544, 546.1599637089113, 2.200609181978668),
            (49.44241876166496, 933337.4378918532, 2.7686910719067157),
            (34.29268375712387, 110108.09777459255, 3.522011383917406),
            (34.11693364265361, 170.07427285446153, 1.6314432418473557),
            (14.886248327061447, 3667.672645345962, 2.1488882176053345),
        ]

        # start an empty WNTR model and add dummy junctions so that
        # head pumps can be added
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")

        # check all of the pump_curves
        for idx, curve in enumerate(pump_curves):
            pump_name = "p" + str(idx + 1)
            curve_name = "c" + str(idx + 1)

            wn.add_curve(curve_name, "HEAD", curve.values)
            wn.add_pump(
                pump_name, "j1", "j2", pump_type="HEAD", pump_parameter=curve_name
            )
            pump = wn.get_link(pump_name)
            coef = pump.get_head_curve_coefficients()

            for i in range(2):
                error = abs(coef[i] - expected_coef[idx][i]) / expected_coef[idx][i]
                self.assertLess(error, 1e-6)
            # self.wntr.graphics.curve.plot_pump_curve(pump)
            # savefig(pump_name + "_" + cname + ".png")

    
    def test_multi_pt_head_curve_expected_error(self):
        # now test two error conditions using bad datasets.
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")

        # Negative coefficients
        data_points1 = [(x, x ** 2 + 2 * x + 3) for x in range(10)]
        wn.add_curve("curve1", "HEAD", data_points1)
        wn.add_pump("pump1", "j1", "j2", pump_type="HEAD", pump_parameter="curve1")
        pump = wn.get_link("pump1")
        with self.assertRaises(RuntimeError):
            pump.get_head_curve_coefficients()

        # Bad fit
        data_points2 = [(x, (-1) ** x * np.exp(-0.001 * x) * 100) for x in range(10)]
        wn.add_curve("curve2", "HEAD", data_points2)
        wn.add_pump("pump2", "j1", "j2", pump_type="HEAD", pump_parameter="curve2")
        pump = wn.get_link("pump2")
        with self.assertRaises(RuntimeError):
            pump.get_head_curve_coefficients()

    def test_get_links_for_node_all(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_junction("j3")
        wn.add_junction("j4")
        wn.add_junction("j5")
        wn.add_pipe("p1", "j1", "j2")
        wn.add_pipe("p2", "j1", "j4")
        wn.add_pipe("p3", "j1", "j5")
        wn.add_pipe("p4", "j3", "j2")
        wn.add_pipe("p5", "j4", "j3")
        l1 = wn.get_links_for_node("j1")
        l2 = wn.get_links_for_node("j2", "all")
        l3 = wn.get_links_for_node("j3", "all")
        l4 = wn.get_links_for_node("j4")
        l5 = wn.get_links_for_node("j5")
        l1.sort()
        l2.sort()
        l3.sort()
        l4.sort()
        l5.sort()
        self.assertEqual(l1, ["p1", "p2", "p3"])
        self.assertEqual(l2, ["p1", "p4"])
        self.assertEqual(l3, ["p4", "p5"])
        self.assertEqual(l4, ["p2", "p5"])
        self.assertEqual(l5, ["p3"])

    def test_get_links_for_node_in(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_junction("j3")
        wn.add_junction("j4")
        wn.add_junction("j5")
        wn.add_pipe("p1", "j1", "j2")
        wn.add_pipe("p2", "j1", "j4")
        wn.add_pipe("p3", "j1", "j5")
        wn.add_pipe("p4", "j3", "j2")
        wn.add_pipe("p5", "j4", "j3")
        l1 = wn.get_links_for_node("j1", "inlet")
        l2 = wn.get_links_for_node("j2", "inlet")
        l3 = wn.get_links_for_node("j3", "inlet")
        l4 = wn.get_links_for_node("j4", "inlet")
        l5 = wn.get_links_for_node("j5", "inlet")
        l1.sort()
        l2.sort()
        l3.sort()
        l4.sort()
        l5.sort()
        self.assertEqual(l1, [])
        self.assertEqual(l2, ["p1", "p4"])
        self.assertEqual(l3, ["p5"])
        self.assertEqual(l4, ["p2"])
        self.assertEqual(l5, ["p3"])

    def test_get_links_for_node_out(self):
        wn = self.wntr.network.WaterNetworkModel()
        wn.add_junction("j1")
        wn.add_junction("j2")
        wn.add_junction("j3")
        wn.add_junction("j4")
        wn.add_junction("j5")
        wn.add_pipe("p1", "j1", "j2")
        wn.add_pipe("p2", "j1", "j4")
        wn.add_pipe("p3", "j1", "j5")
        wn.add_pipe("p4", "j3", "j2")
        wn.add_pipe("p5", "j4", "j3")
        l1 = wn.get_links_for_node("j1", "outlet")
        l2 = wn.get_links_for_node("j2", "outlet")
        l3 = wn.get_links_for_node("j3", "outlet")
        l4 = wn.get_links_for_node("j4", "outlet")
        l5 = wn.get_links_for_node("j5", "outlet")
        l1.sort()
        l2.sort()
        l3.sort()
        l4.sort()
        l5.sort()
        self.assertEqual(l1, ["p1", "p2", "p3"])
        self.assertEqual(l2, [])
        self.assertEqual(l3, ["p4"])
        self.assertEqual(l4, ["p5"])
        self.assertEqual(l5, [])


epanet_unit_id = {
    "CFS": 0,
    "GPM": 1,
    "MGD": 2,
    "IMGD": 3,
    "AFD": 4,
    "LPS": 5,
    "LPM": 6,
    "MLD": 7,
    "CMH": 8,
    "CMD": 9,
}


class TestCase(unittest.TestCase):
    def test_Net1(self):
        inp_file = join(ex_datadir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        G = wn.to_graph()

        node = G.nodes
        elevation = wn.query_node_attribute("elevation")
        # base_demand = wn.query_node_attribute('base_demand')
        edge = G.adj
        diameter = wn.query_link_attribute("diameter")
        length = wn.query_link_attribute("length")

        # Data from the INP file, converted using flowunits
        expected_node = {
            "11": {"type": "Junction", "pos": (30.0, 70.0)},
            "10": {"type": "Junction", "pos": (20.0, 70.0)},
            "13": {"type": "Junction", "pos": (70.0, 70.0)},
            "12": {"type": "Junction", "pos": (50.0, 70.0)},
            "21": {"type": "Junction", "pos": (30.0, 40.0)},
            "22": {"type": "Junction", "pos": (50.0, 40.0)},
            "23": {"type": "Junction", "pos": (70.0, 40.0)},
            "32": {"type": "Junction", "pos": (50.0, 10.0)},
            "31": {"type": "Junction", "pos": (30.0, 10.0)},
            "2": {"type": "Tank", "pos": (50.0, 90.0)},
            "9": {"type": "Reservoir", "pos": (10.0, 70.0)},
        }

        expected_elevation = {
            "11": 710.0,
            "10": 710.0,
            "13": 695.0,
            "12": 700.0,
            "21": 700.0,
            "22": 695.0,
            "23": 690.0,
            "32": 710.0,
            "31": 700.0,
            "2": 850.0,
        }
        expected_elevation = wntr.epanet.util.HydParam.Elevation._to_si(
            wn._inpfile.flow_units, expected_elevation
        )

        expected_base_demand = {
            "11": 150,
            "10": 0,
            "13": 100,
            "12": 150,
            "21": 150,
            "22": 200,
            "23": 150,
            "32": 100,
            "31": 100,
        }
        expected_base_demand = wntr.epanet.util.HydParam.Demand._to_si(
            wn._inpfile.flow_units, expected_base_demand
        )

        expected_edge = {
            "11": {"12": {"11": {"type": "Pipe"}}, "21": {"111": {"type": "Pipe"}}},
            "10": {"11": {"10": {"type": "Pipe"}}},
            "13": {"23": {"113": {"type": "Pipe"}}},
            "12": {"13": {"12": {"type": "Pipe"}}, "22": {"112": {"type": "Pipe"}}},
            "21": {"31": {"121": {"type": "Pipe"}}, "22": {"21": {"type": "Pipe"}}},
            "22": {"32": {"122": {"type": "Pipe"}}, "23": {"22": {"type": "Pipe"}}},
            "23": {},
            "32": {},
            "31": {"32": {"31": {"type": "Pipe"}}},
            "2": {"12": {"110": {"type": "Pipe"}}},
            "9": {"10": {"9": {"type": "Pump"}}},
        }

        expected_diameter = {
            "11": 14.0,
            "111": 10.0,
            "10": 18.0,
            "113": 8.0,
            "12": 10.0,
            "112": 12.0,
            "121": 8.0,
            "21": 10.0,
            "122": 6.0,
            "22": 12.0,
            "31": 6.0,
            "110": 18.0,
        }
        expected_diameter = wntr.epanet.util.HydParam.PipeDiameter._to_si(
            wn._inpfile.flow_units, expected_diameter
        )

        expected_length = {
            "11": 5280.0,
            "111": 5280.0,
            "10": 10530.0,
            "113": 5280.0,
            "12": 5280.0,
            "112": 5280.0,
            "121": 5280.0,
            "21": 5280.0,
            "122": 5280.0,
            "22": 5280.0,
            "31": 5280.0,
            "110": 200.0,
        }
        expected_length = wntr.epanet.util.HydParam.Length._to_si(
            wn._inpfile.flow_units, expected_length
        )

        self.assertDictEqual(dict(node), expected_node)
        self.assertDictEqual(dict(elevation), expected_elevation)
        # self.assertDictEqual(base_demand, expected_base_demand)

        self.assertDictEqual(dict(edge), expected_edge)
        self.assertDictEqual(dict(diameter), expected_diameter)
        self.assertDictEqual(dict(length), expected_length)

    def test_query_node_attribute(self):
        inp_file = join(ex_datadir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        elevation = 213.36  # 700*float(units.ft/units.m) # ft to m
        nodes = wn.query_node_attribute("elevation", np.less, elevation)

        expected_nodes = set(["13", "22", "23"])

        self.assertSetEqual(set(nodes.keys()), expected_nodes)

    def test_query_pipe_attribute(self):
        inp_file = join(ex_datadir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        length = 1609.344  # 5280*float(units.ft/units.m) # ft to m
        pipes = wn.query_link_attribute("length", np.greater, length)

        expected_pipes = set(["10"])

        self.assertSetEqual(set(pipes.keys()), expected_pipes)

    def test_nzd_nodes(self):
        inp_file = join(ex_datadir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        nzd_nodes = []
        for name, node in wn.junctions():
            demand = 0
            for ts in np.arange(
                0, wn.options.time.duration, wn.options.time.report_timestep
            ):
                demand += node.demand_timeseries_list.at(ts)
            if demand > 0:
                nzd_nodes.append(name)

        expected_nodes = set(["11", "13", "12", "21", "22", "23", "32", "31"])

        self.assertSetEqual(set(nzd_nodes), expected_nodes)

    def test_name_list(self):
        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        self.assertIn("10", wn.junction_name_list)
        self.assertIn("1", wn.tank_name_list)
        self.assertIn("River", wn.reservoir_name_list)
        self.assertIn("20", wn.pipe_name_list)
        self.assertIn("10", wn.pump_name_list)
        self.assertEqual(0, len(wn.valve_name_list))
        self.assertIn("1", wn.pattern_name_list)
        self.assertIn("1", wn.curve_name_list)
        self.assertEqual(0, len(wn.source_name_list))
        #    self.assertEqual(0, len(wn._demand_name_list))
        self.assertIn("control 1", wn.control_name_list)

    def test_add_get_remove_num(self):
        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        wn.add_junction("new_junc")
        wn.get_node("new_junc")

        wn.add_tank("new_tank")
        wn.get_node("new_tank")

        wn.add_reservoir("new_reservoir")
        wn.get_node("new_reservoir")

        wn.add_pipe("new_pipe", "139", "131")
        wn.get_link("new_pipe")

        wn.add_pump("new_pump", "139", "131")
        wn.get_link("new_pump")

        wn.add_valve("new_valve", "139", "131")
        wn.get_link("new_valve")

        wn.add_pattern("new_pattern", [])
        wn.get_pattern("new_pattern")

        wn.add_curve("new_curve", "HEAD", [])
        wn.get_curve("new_curve")

        wn.add_source("new_source", "new_junc", "CONCEN", 1, "new_pattern")
        wn.get_source("new_source")

        nums = [
            wn.num_junctions,
            wn.num_tanks,
            wn.num_reservoirs,
            wn.num_pipes,
            wn.num_pumps,
            wn.num_valves,
            wn.num_patterns,
            wn.num_curves,
            wn.num_sources,
        ]
        expected = [93, 4, 3, 118, 3, 1, 6, 3, 1]
        self.assertListEqual(nums, expected)

        # Verify that runtime errors occur when there is a node/pattern still in use
        self.assertRaises(RuntimeError, wn.remove_node, "new_junc")
        self.assertRaises(RuntimeError, wn.remove_pattern, "1")

        wn.remove_source("new_source")
        wn.remove_curve("new_curve")
        wn.remove_pattern("new_pattern")
        wn.remove_link("new_pipe")
        wn.remove_link("new_pump")
        wn.remove_link("new_valve")
        wn.remove_node("new_junc")
        wn.remove_node("new_tank")
        wn.remove_node("new_reservoir")

        nums = [
            wn.num_junctions,
            wn.num_tanks,
            wn.num_reservoirs,
            wn.num_pipes,
            wn.num_pumps,
            wn.num_valves,
            wn.num_patterns,
            wn.num_curves,
            wn.num_sources,
        ]
        expected = [92, 3, 2, 117, 2, 0, 5, 2, 0]
        self.assertListEqual(nums, expected)

    def test_describe(self):
        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        d0 = wn.describe(0)
        self.assertDictEqual(
            d0,
            {
                "Nodes": 97,
                "Links": 119,
                "Patterns": 5,
                "Curves": 2,
                "Sources": 0,
                "Controls": 18,
            },
        )

        d1 = wn.describe(1)
        self.assertDictEqual(
            d1,
            {
                "Nodes": {"Junctions": 92, "Tanks": 3, "Reservoirs": 2},
                "Links": {"Pipes": 117, "Pumps": 2, "Valves": 0},
                "Patterns": 5,
                "Curves": {"Pump": 2, "Efficiency": 0, "Headloss": 0, "Volume": 0},
                "Sources": 0,
                "Controls": 18,
            },
        )

    def test_assign_demand(self):

        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        demands0 = wntr.metrics.expected_demand(wn)
        pattern_name0 = wn.get_node("10").demand_timeseries_list[0].pattern_name

        wn.options.hydraulic.demand_multiplier = 1.5
        demands1 = wntr.metrics.expected_demand(wn)

        self.assertEqual(pattern_name0, "1")
        self.assertEqual(len(wn.pattern_name_list), 5)  # number of original patterns
        self.assertLess(abs((demands1 / demands0).max().max() - 1.5), 0.000001)

        sim1 = wntr.sim.EpanetSimulator(wn)
        results1 = sim1.run_sim()
        demands_sim1 = results1.node["demand"].loc[:, wn.junction_name_list]

        ### re-assign demands to be 2 times the original demands
        wn.assign_demand(demands1 * 2, pattern_prefix="ResetDemand1_")

        demands2 = wntr.metrics.expected_demand(wn)
        pattern_name = wn.get_node("10").demand_timeseries_list[0].pattern_name

        sim = wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()
        demands_sim2 = results2.node["demand"].loc[:, wn.junction_name_list]

        self.assertEqual(pattern_name, "ResetDemand1_10")
        self.assertEqual(len(wn.pattern_name_list), wn.num_junctions + 5)
        self.assertLess(abs((demands2 / demands1).max().max() - 2), 0.000001)
        self.assertLess(abs((demands_sim2 / demands_sim1).max().max() - 2), 0.01)

        ### re-assign demands using results from the simulation
        wn.assign_demand(demands_sim2, pattern_prefix="ResetDemand2_")

        demands2 = wntr.metrics.expected_demand(wn)
        pattern_name = wn.get_node("10").demand_timeseries_list[0].pattern_name

        sim = wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()
        demands_sim2 = results2.node["demand"].loc[:, wn.junction_name_list]

        self.assertEqual(pattern_name, "ResetDemand2_10")
        self.assertEqual(len(wn.pattern_name_list), 2 * wn.num_junctions + 5)
        self.assertLess(abs((demands2 / demands1).max().max() - 2), 0.01)
        self.assertLess(abs((demands_sim2 / demands_sim1).max().max() - 2), 0.01)

    def test_convert_controls_to_rules(self):

        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.rule_timestep = (
            1  # For an exact match, the rule timestep must be very small
        )

        nControls = 0
        nRules = 0
        for name, control in wn.controls():
            if isinstance(control, Control):
                nControls = nControls + 1
            elif isinstance(control, Rule):
                nRules = nRules + 1
        assert nControls == 18
        assert nRules == 0

        sim = wntr.sim.EpanetSimulator(wn)
        results1 = sim.run_sim()

        wn.convert_controls_to_rules(priority=3)

        nControls = 0
        nRules = 0
        for name, control in wn.controls():
            if isinstance(control, Control):
                nControls = nControls + 1
            elif isinstance(control, Rule):
                nRules = nRules + 1
        assert nControls == 0
        assert nRules == 18

        sim = wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()

        # (results1.node['pressure'] - results2.node['pressure']).plot()

        for node_name, node in wn.nodes():
            for t in results1.node["pressure"].index:
                self.assertLess(
                    abs(
                        results1.node["pressure"].at[t, node_name]
                        - results2.node["pressure"].at[t, node_name]
                    ),
                    0.001,
                )


class TestNetworkIO_Dict(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net6.inp")
        self.inp_files = [join(ex_datadir, f) for f in ["Net1.inp", "Net2.inp", "Net3.inp", "Net6.inp"]]

    @classmethod
    def tearDownClass(self):
        pass

    def test_dict_roundtrip(self):
        for inp_file in self.inp_files:
            wn = self.wntr.network.WaterNetworkModel(inp_file)
            A = wn.to_dict()
            B = self.wntr.network.from_dict(A)
            assert(wn._compare(B))

    def test_json_roundtrip(self):
        for inp_file in self.inp_files:
            wn = self.wntr.network.WaterNetworkModel(inp_file)
            wn.convert_controls_to_rules()
            self.wntr.network.write_json(wn, 'temp.json')
            B = self.wntr.network.read_json('temp.json')
            assert(wn._compare(B))

    def test_json_pattern_dump(self):
        wn = wntr.network.WaterNetworkModel()
        wn.add_pattern('pat0', [0,1,0,1,0,1,0])
        self.wntr.network.write_json(wn, f'temp.json')
        
class TestNetworkIO_GIS(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net6.inp")
        self.inp_files = [join(ex_datadir, f) for f in ["Net1.inp", "Net2.inp", "Net3.inp", "Net6.inp"]]

    @classmethod
    def tearDownClass(self):
        pass
    
    def test_gis_additional_attributes(self):
        wn = self.wntr.network.WaterNetworkModel(self.inp_files[0])
        A = wn.to_gis(pumps_as_points=True, valves_as_points=True)
        A.junctions['new'] = range(wn.num_junctions)
        A.junctions['pressure_exponent'] = 0.45
        A.tanks['new'] = 4
        A.reservoirs['new'] = 5
        A.pipes['new'] = 6
        A.pumps['new'] = 7
        A.valves['new'] = 8
        B = self.wntr.network.from_gis(A)

        node_attr = B.query_node_attribute('new')
        assert((node_attr[wn.junction_name_list] == range(wn.num_junctions)).all())
        assert((node_attr[wn.tank_name_list] == 4).all())
        assert((node_attr[wn.reservoir_name_list] == 5).all())
        
        link_attr = B.query_link_attribute('new')
        assert((link_attr[wn.pipe_name_list] == 6).all())
        assert((link_attr[wn.pump_name_list] == 7).all())
        assert((link_attr[wn.valve_name_list] == 8).all())
        
        pressure_exponent = B.query_node_attribute('pressure_exponent')
        assert((pressure_exponent[wn.junction_name_list] == 0.45).all())
        
    def test_gis_roundtrip(self):
        for inp_file in self.inp_files:
            wn = self.wntr.network.WaterNetworkModel(inp_file)
            A = wn.to_gis()
            B = self.wntr.network.from_gis(A)
            assert(wn._compare(B, level=0))
    
    def test_gis_point_roundtrip(self):
        for inp_file in self.inp_files:
            wn = self.wntr.network.WaterNetworkModel(inp_file)
            A = wn.to_gis(pumps_as_points=True, valves_as_points=True)
            B = self.wntr.network.from_gis(A)
            assert(wn._compare(B, level=0))
    
    def test_gis_append_roundtrip(self):
        for inp_file in self.inp_files:
            wn = self.wntr.network.WaterNetworkModel(inp_file)
            A = wn.to_gis(pumps_as_points=True, valves_as_points=True)
            B = self.wntr.network.from_gis({'junctions': A.junctions})
            B = self.wntr.network.from_gis({'tanks': A.tanks,
                                            'reservoirs': A.reservoirs}, B)
            B = self.wntr.network.from_gis({'pipes': A.pipes}, B)
            B = self.wntr.network.from_gis({'pumps': A.pumps,
                                            'valves': A.valves}, B)
            assert(wn._compare(B, level=0))
    
    def test_geojson_roundtrip(self):
        for inp_file in self.inp_files:
            wn = self.wntr.network.WaterNetworkModel(inp_file)
            wntr.network.write_geojson(wn, 'temp', pumps_as_points=True, valves_as_points=False)
            files = {}
            if wn.num_junctions > 0:
                files['junctions'] = 'temp_junctions.geojson'
            if wn.num_tanks > 0:
                files['tanks'] = 'temp_tanks.geojson'
            if wn.num_reservoirs > 0:
                files['reservoirs'] = 'temp_reservoirs.geojson'
            if wn.num_pipes > 0:
                files['pipes'] = 'temp_pipes.geojson'
            if wn.num_pumps > 0:
                files['pumps'] = 'temp_pumps.geojson'
            if wn.num_valves > 0:
                files['valves'] = 'temp_valves.geojson'
            B = self.wntr.network.read_geojson(files)
            assert(wn._compare(B, level=0))

    def test_shapefile_roundtrip(self):
        for inp_file in self.inp_files:
            wn = self.wntr.network.WaterNetworkModel(inp_file)
            wntr.network.write_shapefile(wn, 'temp')
            files = {}
            if wn.num_junctions > 0:
                files['junctions'] = 'temp_junctions'
            if wn.num_tanks > 0:
                files['tanks'] = 'temp_tanks'
            if wn.num_reservoirs > 0:
                files['reservoirs'] = 'temp_reservoirs'
            if wn.num_tanks > 0:
                files['pipes'] = 'temp_pipes'
            if wn.num_pumps > 0:
                files['pumps'] = 'temp_pumps'
            if wn.num_valves > 0:
                files['valves'] = 'temp_valves'
            B = self.wntr.network.read_shapefile(files)
            assert(wn._compare(B, level=0))

if __name__ == "__main__":
    unittest.main()
