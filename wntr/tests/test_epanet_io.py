import sys
import unittest
from os.path import abspath, dirname, join

from numpy.testing._private.utils import assert_string_equal

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestWriter(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(test_datadir, "io.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wntr.network.write_inpfile(self.wn, "temp.inp", "GPM")
        self.wn2 = self.wntr.network.WaterNetworkModel("temp.inp")

    @classmethod
    def tearDownClass(self):
        pass

    def test_all(self):
        self.assertTrue(self.wn._compare(self.wn2))

    def test_pipe_minor_loss(self):
        p1 = self.wn2.get_link("p1")
        self.assertAlmostEqual(p1.minor_loss, 0.73, 6)

    def test_tcv_valve(self):
        v1 = self.wn2.get_link("v1")
        self.assertEqual(v1.start_node_name, "j1")
        self.assertEqual(v1.end_node_name, "j2")
        self.assertAlmostEqual(v1.diameter, 0.3048, 6)
        self.assertEqual(v1.valve_type, "TCV")
        self.assertAlmostEqual(v1.setting, 3.52, 6)
        self.assertAlmostEqual(v1.minor_loss, 0.54, 6)

    def test_pump(self):
        p1 = self.wn2.get_link("pump1")
        p11 = self.wn.get_link("pump1")
        self.assertEqual(p1.start_node_name, "j2")
        self.assertEqual(p1.end_node_name, "j3")
        self.assertEqual(type(p1), self.wntr.network.elements.HeadPump)
        self.assertEqual(p1.pump_curve_name, "curve1")
        self.assertAlmostEqual(p1.speed_timeseries.base_value, 1.2, 6)
        self.assertEqual(p1.speed_timeseries, p11.speed_timeseries)
        self.assertEqual(p1.speed_timeseries.pattern_name, "pattern1")

        p2 = self.wn2.get_link("pump2")
        self.assertEqual(type(p2), self.wntr.network.elements.PowerPump)
        self.assertAlmostEqual(p2._base_power, 16629.107, 2)

    def test_valve_setting_control(self):
        control = self.wn2.get_control("control 1")
        run_time = control._condition._threshold
        self.assertAlmostEqual(run_time, 3600.0 * 3.4, 6)
        value = control.actions()[0]._value
        self.assertAlmostEqual(value, 0.82, 6)

        control = self.wn2.get_control("control 2")
        value = control.actions()[0]._value
        self.assertAlmostEqual(value, 1.8358, 3)

    def test_controls(self):
        for name, control in self.wn.controls():
            self.assertTrue(control._compare(self.wn2.get_control(name)))

    def test_demands(self):
        # In EPANET, the [DEMANDS] section overrides demands specified in [JUNCTIONS]
        expected_length = {
            "j1": 2,  # DEMANDS duplicates demand in JUNCTIONS
            "j2": 2,  # DEMANDS does not duplicate demand in JUNCTIONS
            "j3": 1,  # Only in JUNCTIONS
            "j4": 1,
        }  # Only in DEMANDS
        for j_name, j in self.wn.junctions():
            j2 = self.wn2.get_node(j_name)
            assert len(j.demand_timeseries_list) == len(j2.demand_timeseries_list)
            self.assertEqual(expected_length[j_name], len(j2.demand_timeseries_list))
            for d, d2 in zip(j.demand_timeseries_list, j2.demand_timeseries_list):
                self.assertEqual(d, d2)
                # DEMANDS use pattern2, JUNCTIONS demands use pattern1
                if j_name in ["j1", "j2", "j4"]:
                    self.assertEqual(d2.pattern_name, "pattern2")
                else:
                    self.assertEqual(d2.pattern_name, "pattern1")


class TestInpFileWriter(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr
        inp_file = join(test_datadir, "Net6_plus.inp")  # UNITS = GPM
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wntr.network.write_inpfile(self.wn, "temp.inp", units="LPM")
        self.wn2 = self.wntr.network.WaterNetworkModel(inp_file)

    @classmethod
    def tearDownClass(self):
        pass

    def test_wn(self):
        self.assertTrue(self.wn._compare(self.wn2))

    def test_junctions(self):
        for name, node in self.wn.nodes(self.wntr.network.Junction):
            node2 = self.wn2.get_node(name)
            self.assertTrue(node._compare(node2))
            # self.assertAlmostEqual(node.base_demand, node2.base_demand, 5)

    def test_reservoirs(self):
        for name, node in self.wn.nodes(self.wntr.network.Reservoir):
            node2 = self.wn2.get_node(name)
            self.assertTrue(node._compare(node2))
            self.assertAlmostEqual(
                node.head_timeseries.base_value, node2.head_timeseries.base_value, 5
            )

    def test_tanks(self):
        for name, node in self.wn.nodes(self.wntr.network.Tank):
            node2 = self.wn2.get_node(name)
            self.assertTrue(node._compare(node2))
            self.assertAlmostEqual(node.init_level, node2.init_level, 5)

    def test_pipes(self):
        for name, link in self.wn.links(self.wntr.network.Pipe):
            link2 = self.wn2.get_link(name)
            self.assertTrue(link._compare(link2))
            self.assertEqual(link.initial_status, link2.initial_status)

    def test_pumps(self):
        for name, link in self.wn.links(self.wntr.network.Pump):
            link2 = self.wn2.get_link(name)
            self.assertTrue(link._compare(link2))

    def test_valves(self):
        for name, link in self.wn.links(self.wntr.network.Valve):
            link2 = self.wn2.get_link(name)
            self.assertTrue(link._compare(link2))
            self.assertAlmostEqual(link.setting, link2.setting, 5)

    def test_curves(self):
        pass

    def test_sources(self):
        for name, source in self.wn._sources.items():
            source2 = self.wn2._sources[name]
            self.assertEqual(source == source2, True)

    def test_demands(self):
        for j_name, j in self.wn.junctions():
            j2 = self.wn2.get_node(j_name)
            assert len(j.demand_timeseries_list) == len(j2.demand_timeseries_list)
            for d, d2 in zip(j.demand_timeseries_list, j2.demand_timeseries_list):
                self.assertEqual(d, d2)

    ### TODO
    #    def test_controls(self):
    #        for name1, control1 in self.wn.controls.items():
    #            control2 = self.wn2._controls[name1]
    #            self.assertEqual(control1 == control2, True)

    def test_options(self):
        options1 = self.wn.options
        options2 = self.wn2.options
        self.assertEqual(options1 == options2, True)

    def test_controls(self):
        for name, control in self.wn.controls():
            self.assertTrue(control._compare(self.wn2.get_control(name)))


class TestInpRules(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr
        self._rules = """
RULE NEW_VALVE1_DRAINING IF Tank TANK-3326 level >= 29.5 THEN Valve NEW_VALVE1 status = Open  AND Valve NEW_VALVE1 setting = 100 PRIORITY 1 ; end of rule

RULE NEW_VALVE1_FILLING IF Tank TANK-3326 level <= 18 THEN Valve NEW_VALVE1 status = Closed PRIORITY 1 ; end of rule

RULE NEW_VALVE2 IF Pipe LINK-1107 status = Open  AND SYSTEM CLOCKTIME >= 7:00:00 AM  AND SYSTEM CLOCKTIME <= 7:00:00 PM THEN Valve NEW_VALVE2 status = Open  AND Valve NEW_VALVE2 setting = 100 ELSE Valve NEW_VALVE2 status = Closed PRIORITY 2 ; end of rule

RULE NEW_VALVE3 IF SYSTEM CLOCKTIME >= 7:00:00 AM  AND SYSTEM CLOCKTIME <= 7:00:00 PM THEN Valve NEW_VALVE3 status = Open  AND Valve NEW_VALVE3 setting = 100 ELSE Valve NEW_VALVE3 status = Closed PRIORITY 2 ; end of rule

RULE control_1_Rule IF SYSTEM TIME Is 00:00:00 THEN Valve NEW_VALVE1 setting = 1e+09 PRIORITY 3 ; end of rule

RULE control_2_Rule IF SYSTEM TIME Is 00:00:00 THEN Valve NEW_VALVE2 setting = 100 PRIORITY 3 ; end of rule

RULE control_3_Rule IF Tank TANK-3326 level > 29.5 THEN Pump PUMP-3829 status = Closed PRIORITY 3 ; end of rule

RULE control_4_Rule IF Tank TANK-3326 level < 18 THEN Pump PUMP-3829 status = Open PRIORITY 3 ; end of rule

RULE control_5_Rule IF Tank TANK-3325 level < 21.3 THEN Pump PUMP-3830 status = Open PRIORITY 3 ; end of rule

RULE control_6_Rule IF Tank TANK-3325 level > 22.8 THEN Pump PUMP-3830 status = Closed PRIORITY 3 ; end of rule

RULE control_7_Rule IF Tank TANK-3325 level < 19.3 THEN Pump PUMP-3831 status = Open PRIORITY 3 ; end of rule

RULE control_8_Rule IF Tank TANK-3325 level > 21.8 THEN Pump PUMP-3831 status = Closed PRIORITY 3 ; end of rule

RULE control_9_Rule IF Tank TANK-3325 level < 18.8 THEN Pump PUMP-3832 status = Open PRIORITY 3 ; end of rule

RULE control_10_Rule IF Tank TANK-3325 level > 20.8 THEN Pump PUMP-3832 status = Closed PRIORITY 3 ; end of rule

RULE control_11_Rule IF Tank TANK-3325 level < 17.8 THEN Pump PUMP-3833 status = Open PRIORITY 3 ; end of rule

RULE control_12_Rule IF Tank TANK-3325 level > 19.8 THEN Pump PUMP-3833 status = Closed PRIORITY 3 ; end of rule

RULE control_13_Rule IF Tank TANK-3325 level < 17.6 THEN Pump PUMP-3834 status = Open PRIORITY 3 ; end of rule

RULE control_14_Rule IF Tank TANK-3325 level > 18.8 THEN Pump PUMP-3834 status = Closed PRIORITY 3 ; end of rule

RULE control_15_Rule IF Tank TANK-3333 level < 18.5 THEN Pump PUMP-3835 status = Open PRIORITY 3 ; end of rule

RULE control_16_Rule IF Tank TANK-3333 level > 20 THEN Pump PUMP-3835 status = Closed PRIORITY 3 ; end of rule

RULE control_17_Rule IF Tank TANK-3333 level < 16.5 THEN Pump PUMP-3836 status = Open PRIORITY 3 ; end of rule

RULE control_18_Rule IF Tank TANK-3333 level > 19 THEN Pump PUMP-3836 status = Closed PRIORITY 3 ; end of rule

RULE control_19_Rule IF Tank TANK-3333 level < 16 THEN Pump PUMP-3837 status = Open PRIORITY 3 ; end of rule

RULE control_20_Rule IF Tank TANK-3333 level > 17.5 THEN Pump PUMP-3837 status = Closed PRIORITY 3 ; end of rule

RULE control_21_Rule IF Tank TANK-3333 level < 15 THEN Pump PUMP-3838 status = Open PRIORITY 3 ; end of rule

RULE control_22_Rule IF Tank TANK-3333 level > 16.5 THEN Pump PUMP-3838 status = Closed PRIORITY 3 ; end of rule

RULE control_23_Rule IF Tank TANK-3333 level < 18 THEN Pump PUMP-3839 status = Open PRIORITY 3 ; end of rule

RULE control_24_Rule IF Tank TANK-3333 level > 19.5 THEN Pump PUMP-3839 status = Closed PRIORITY 3 ; end of rule

RULE control_25_Rule IF Tank TANK-3333 level < 16 THEN Pump PUMP-3840 status = Open PRIORITY 3 ; end of rule

RULE control_26_Rule IF Tank TANK-3333 level > 18.5 THEN Pump PUMP-3840 status = Closed PRIORITY 3 ; end of rule

RULE control_27_Rule IF Tank TANK-3333 level < 15.5 THEN Pump PUMP-3841 status = Open PRIORITY 3 ; end of rule

RULE control_28_Rule IF Tank TANK-3333 level > 17 THEN Pump PUMP-3841 status = Closed PRIORITY 3 ; end of rule

RULE control_29_Rule IF Tank TANK-3336 level < 17 THEN Pump PUMP-3845 status = Open PRIORITY 3 ; end of rule

RULE control_30_Rule IF Tank TANK-3336 level > 19 THEN Pump PUMP-3845 status = Closed PRIORITY 3 ; end of rule

RULE control_31_Rule IF Tank TANK-3336 level < 16 THEN Pump PUMP-3846 status = Open PRIORITY 3 ; end of rule

RULE control_32_Rule IF Tank TANK-3336 level > 18 THEN Pump PUMP-3846 status = Closed PRIORITY 3 ; end of rule

RULE control_33_Rule IF Tank TANK-3335 level < 18 THEN Pump PUMP-3842 status = Open PRIORITY 3 ; end of rule

RULE control_34_Rule IF Tank TANK-3335 level > 19 THEN Pump PUMP-3842 status = Closed PRIORITY 3 ; end of rule

RULE control_35_Rule IF Tank TANK-3335 level < 17 THEN Pump PUMP-3843 status = Open PRIORITY 3 ; end of rule

RULE control_36_Rule IF Tank TANK-3335 level > 18 THEN Pump PUMP-3843 status = Closed PRIORITY 3 ; end of rule

RULE control_37_Rule IF Tank TANK-3335 level < 16 THEN Pump PUMP-3844 status = Open PRIORITY 3 ; end of rule

RULE control_38_Rule IF Tank TANK-3335 level > 17 THEN Pump PUMP-3844 status = Closed PRIORITY 3 ; end of rule

RULE control_39_Rule IF Tank TANK-3337 level < 22 THEN Pump PUMP-3849 status = Open PRIORITY 3 ; end of rule

RULE control_40_Rule IF Tank TANK-3337 level > 24 THEN Pump PUMP-3849 status = Closed PRIORITY 3 ; end of rule

RULE control_41_Rule IF Tank TANK-3337 level < 20.5 THEN Pump PUMP-3850 status = Open PRIORITY 3 ; end of rule

RULE control_42_Rule IF Tank TANK-3337 level > 23 THEN Pump PUMP-3850 status = Closed PRIORITY 3 ; end of rule

RULE control_43_Rule IF Tank TANK-3337 level < 18.5 THEN Pump PUMP-3851 status = Open PRIORITY 3 ; end of rule

RULE control_44_Rule IF Tank TANK-3337 level > 22 THEN Pump PUMP-3851 status = Closed PRIORITY 3 ; end of rule

RULE control_45_Rule IF Tank TANK-3337 level < 17 THEN Pump PUMP-3852 status = Open PRIORITY 3 ; end of rule

RULE control_46_Rule IF Tank TANK-3337 level > 21 THEN Pump PUMP-3852 status = Closed PRIORITY 3 ; end of rule

RULE control_47_Rule IF Tank TANK-3337 level < 15 THEN Pump PUMP-3853 status = Open PRIORITY 3 ; end of rule

RULE control_48_Rule IF Tank TANK-3337 level > 20.5 THEN Pump PUMP-3853 status = Closed PRIORITY 3 ; end of rule

RULE control_49_Rule IF Tank TANK-3337 level < 21.5 THEN Pump PUMP-3847 status = Open PRIORITY 3 ; end of rule

RULE control_50_Rule IF Tank TANK-3337 level > 23 THEN Pump PUMP-3847 status = Closed PRIORITY 3 ; end of rule

RULE control_51_Rule IF Tank TANK-3337 level < 20 THEN Pump PUMP-3848 status = Open PRIORITY 3 ; end of rule

RULE control_52_Rule IF Tank TANK-3337 level > 22 THEN Pump PUMP-3848 status = Closed PRIORITY 3 ; end of rule

RULE control_53_Rule IF Tank TANK-3340 level < 35 THEN Pump PUMP-3854 status = Open PRIORITY 3 ; end of rule

RULE control_54_Rule IF Tank TANK-3340 level > 36.5 THEN Pump PUMP-3854 status = Closed PRIORITY 3 ; end of rule

RULE control_55_Rule IF Tank TANK-3340 level < 34 THEN Pump PUMP-3855 status = Open PRIORITY 3 ; end of rule

RULE control_56_Rule IF Tank TANK-3340 level > 36 THEN Pump PUMP-3855 status = Closed PRIORITY 3 ; end of rule

RULE control_57_Rule IF Tank TANK-3340 level < 33 THEN Pump PUMP-3856 status = Open PRIORITY 3 ; end of rule

RULE control_58_Rule IF Tank TANK-3340 level > 35 THEN Pump PUMP-3856 status = Closed PRIORITY 3 ; end of rule

RULE control_59_Rule IF Tank TANK-3341 level < 22 THEN Pump PUMP-3857 status = Open PRIORITY 3 ; end of rule

RULE control_60_Rule IF Tank TANK-3341 level > 24 THEN Pump PUMP-3857 status = Closed PRIORITY 3 ; end of rule

RULE control_61_Rule IF Tank TANK-3341 level < 21 THEN Pump PUMP-3858 status = Open PRIORITY 3 ; end of rule

RULE control_62_Rule IF Tank TANK-3341 level > 23 THEN Pump PUMP-3858 status = Closed PRIORITY 3 ; end of rule

RULE control_63_Rule IF Tank TANK-3341 level < 20 THEN Pump PUMP-3859 status = Open PRIORITY 3 ; end of rule

RULE control_64_Rule IF Tank TANK-3341 level > 22 THEN Pump PUMP-3859 status = Closed PRIORITY 3 ; end of rule

RULE control_65_Rule IF Tank TANK-3342 level < 21.4 THEN Pump PUMP-3860 status = Open PRIORITY 3 ; end of rule

RULE control_66_Rule IF Tank TANK-3342 level > 23 THEN Pump PUMP-3860 status = Closed PRIORITY 3 ; end of rule

RULE control_67_Rule IF Tank TANK-3342 level < 20.3 THEN Pump PUMP-3861 status = Open PRIORITY 3 ; end of rule

RULE control_68_Rule IF Tank TANK-3342 level > 21.9 THEN Pump PUMP-3861 status = Closed PRIORITY 3 ; end of rule

RULE control_69_Rule IF Tank TANK-3342 level < 18.2 THEN Pump PUMP-3862 status = Open PRIORITY 3 ; end of rule

RULE control_70_Rule IF Tank TANK-3342 level > 19.8 THEN Pump PUMP-3862 status = Closed PRIORITY 3 ; end of rule

RULE control_71_Rule IF Tank TANK-3343 level < 28.4 THEN Pump PUMP-3863 status = Open PRIORITY 3 ; end of rule

RULE control_72_Rule IF Tank TANK-3343 level > 29.5 THEN Pump PUMP-3863 status = Closed PRIORITY 3 ; end of rule

RULE control_73_Rule IF Tank TANK-3343 level < 27.8 THEN Pump PUMP-3864 status = Open PRIORITY 3 ; end of rule

RULE control_74_Rule IF Tank TANK-3343 level > 29 THEN Pump PUMP-3864 status = Closed PRIORITY 3 ; end of rule

RULE control_75_Rule IF Tank TANK-3343 level < 27.3 THEN Pump PUMP-3865 status = Open PRIORITY 3 ; end of rule

RULE control_76_Rule IF Tank TANK-3343 level > 28.4 THEN Pump PUMP-3865 status = Closed PRIORITY 3 ; end of rule

RULE control_77_Rule IF Tank TANK-3343 level < 25.9 THEN Pump PUMP-3866 status = Open PRIORITY 3 ; end of rule

RULE control_78_Rule IF Tank TANK-3343 level > 27.1 THEN Pump PUMP-3866 status = Closed PRIORITY 3 ; end of rule

RULE control_79_Rule IF Tank TANK-3347 level < 22 THEN Pump PUMP-3870 status = Open PRIORITY 3 ; end of rule

RULE control_80_Rule IF Tank TANK-3347 level > 24 THEN Pump PUMP-3870 status = Closed PRIORITY 3 ; end of rule

RULE control_81_Rule IF Tank TANK-3347 level < 20 THEN Pump PUMP-3871 status = Open PRIORITY 3 ; end of rule

RULE control_82_Rule IF Tank TANK-3347 level > 23 THEN Pump PUMP-3871 status = Closed PRIORITY 3 ; end of rule

RULE control_83_Rule IF Tank TANK-3346 level < 16.5 THEN Pump PUMP-3867 status = Open PRIORITY 3 ; end of rule

RULE control_84_Rule IF Tank TANK-3346 level > 17 THEN Pump PUMP-3867 status = Closed PRIORITY 3 ; end of rule

RULE control_85_Rule IF Tank TANK-3346 level < 16.4 THEN Pump PUMP-3868 status = Open PRIORITY 3 ; end of rule

RULE control_86_Rule IF Tank TANK-3346 level > 16.8 THEN Pump PUMP-3868 status = Closed PRIORITY 3 ; end of rule

RULE control_87_Rule IF Tank TANK-3346 level < 16.2 THEN Pump PUMP-3869 status = Open PRIORITY 3 ; end of rule

RULE control_88_Rule IF Tank TANK-3346 level > 16.6 THEN Pump PUMP-3869 status = Closed PRIORITY 3 ; end of rule

RULE control_89_Rule IF Tank TANK-3349 level < 17.5 THEN Pump PUMP-3872 status = Open PRIORITY 3 ; end of rule

RULE control_90_Rule IF Tank TANK-3349 level > 19 THEN Pump PUMP-3872 status = Closed PRIORITY 3 ; end of rule

RULE control_91_Rule IF Tank TANK-3349 level < 16 THEN Pump PUMP-3873 status = Open PRIORITY 3 ; end of rule

RULE control_92_Rule IF Tank TANK-3349 level > 17.5 THEN Pump PUMP-3873 status = Closed PRIORITY 3 ; end of rule

RULE control_93_Rule IF Tank TANK-3349 level < 14.4 THEN Pump PUMP-3874 status = Open PRIORITY 3 ; end of rule

RULE control_94_Rule IF Tank TANK-3349 level > 16 THEN Pump PUMP-3874 status = Closed PRIORITY 3 ; end of rule

RULE control_95_Rule IF Tank TANK-3348 level < 18 THEN Pump PUMP-3875 status = Open PRIORITY 3 ; end of rule

RULE control_96_Rule IF Tank TANK-3348 level > 19.5 THEN Pump PUMP-3875 status = Closed PRIORITY 3 ; end of rule

RULE control_97_Rule IF Tank TANK-3348 level < 16.5 THEN Pump PUMP-3876 status = Open PRIORITY 3 ; end of rule

RULE control_98_Rule IF Tank TANK-3348 level > 18 THEN Pump PUMP-3876 status = Closed PRIORITY 3 ; end of rule

RULE control_99_Rule IF Tank TANK-3348 level < 14.9 THEN Pump PUMP-3877 status = Open PRIORITY 3 ; end of rule

RULE control_100_Rule IF Tank TANK-3348 level > 16.5 THEN Pump PUMP-3877 status = Closed PRIORITY 3 ; end of rule

RULE control_101_Rule IF Tank TANK-3353 level < 24.5 THEN Pump PUMP-3879 status = Open PRIORITY 3 ; end of rule

RULE control_102_Rule IF Tank TANK-3353 level > 26 THEN Pump PUMP-3879 status = Closed PRIORITY 3 ; end of rule

RULE control_103_Rule IF Tank TANK-3353 level < 24 THEN Pump PUMP-3880 status = Open PRIORITY 3 ; end of rule

RULE control_104_Rule IF Tank TANK-3353 level > 25.5 THEN Pump PUMP-3880 status = Closed PRIORITY 3 ; end of rule

RULE control_105_Rule IF Tank TANK-3353 level < 23.5 THEN Pump PUMP-3881 status = Open PRIORITY 3 ; end of rule

RULE control_106_Rule IF Tank TANK-3353 level > 25 THEN Pump PUMP-3881 status = Closed PRIORITY 3 ; end of rule

RULE control_107_Rule IF Tank TANK-3352 level < 24 THEN Pump PUMP-3878 status = Open PRIORITY 3 ; end of rule

RULE control_108_Rule IF Tank TANK-3352 level > 29.5 THEN Pump PUMP-3878 status = Closed PRIORITY 3 ; end of rule

RULE control_109_Rule IF Tank TANK-3354 level < 27.4 THEN Pump PUMP-3885 status = Open PRIORITY 3 ; end of rule

RULE control_110_Rule IF Tank TANK-3354 level > 29.5 THEN Pump PUMP-3885 status = Closed PRIORITY 3 ; end of rule

RULE control_111_Rule IF Tank TANK-3356 level < 20 THEN Pump PUMP-3886 status = Open PRIORITY 3 ; end of rule

RULE control_112_Rule IF Tank TANK-3356 level > 22.4 THEN Pump PUMP-3886 status = Closed PRIORITY 3 ; end of rule

RULE control_113_Rule IF Tank TANK-3356 level < 19.8 THEN Pump PUMP-3887 status = Open PRIORITY 3 ; end of rule

RULE control_114_Rule IF Tank TANK-3356 level > 21.7 THEN Pump PUMP-3887 status = Closed PRIORITY 3 ; end of rule

RULE control_115_Rule IF Tank TANK-3356 level < 19.5 THEN Pump PUMP-3888 status = Open PRIORITY 3 ; end of rule

RULE control_116_Rule IF Tank TANK-3356 level > 21.5 THEN Pump PUMP-3888 status = Closed PRIORITY 3 ; end of rule

RULE control_117_Rule IF Tank TANK-3355 level < 12 THEN Pump PUMP-3882 status = Open PRIORITY 3 ; end of rule

RULE control_118_Rule IF Tank TANK-3355 level > 13 THEN Pump PUMP-3882 status = Closed PRIORITY 3 ; end of rule

RULE control_119_Rule IF Tank TANK-3355 level < 11 THEN Pump PUMP-3883 status = Open PRIORITY 3 ; end of rule

RULE control_120_Rule IF Tank TANK-3355 level > 12 THEN Pump PUMP-3883 status = Closed PRIORITY 3 ; end of rule

RULE control_121_Rule IF Tank TANK-3355 level < 10 THEN Pump PUMP-3884 status = Open PRIORITY 3 ; end of rule

RULE control_122_Rule IF Tank TANK-3355 level > 11 THEN Pump PUMP-3884 status = Closed PRIORITY 3 ; end of rule

RULE control_123_Rule IF Tank TANK-3324 level > 27 THEN Pipe LINK-1827 status = Closed PRIORITY 3 ; end of rule

RULE control_124_Rule IF Tank TANK-3324 level < 26.5 THEN Pipe LINK-1827 status = Open PRIORITY 3 ; end of rule
"""

    @classmethod
    def tearDownClass(self):
        pass

    def test_convert_controls_to_rules(self):
        inp_file = join(test_datadir, "Net6_plus.inp")  # UNITS = GPM
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.convert_controls_to_rules()
        self.wntr.network.write_inpfile(self.wn, 'temp2.inp')
        self.wn2 = self.wntr.network.WaterNetworkModel('temp2.inp')
        for control_name in self.wn.control_name_list:
            ctrl1 = self.wn.get_control(control_name)
            ctrl2 = self.wn2.get_control(control_name)
            self.assertTrue(ctrl1._compare(ctrl2))        

    def test_convert_single_line_rules(self):
        inp_file = join(test_datadir, "Net6_plus.inp")  # UNITS = GPM
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.convert_controls_to_rules()
        self.wntr.network.write_inpfile(self.wn, 'temp2.inp')
        self.wn2 = self.wntr.network.WaterNetworkModel('temp2.inp')
        for control_name in [n for n in self.wn2.control_name_list]:
            self.wn2.remove_control(control_name)
        self.wntr.network.write_inpfile(self.wn2, 'temp3.inp')
        self.wn3 = self.wntr.network.WaterNetworkModel('temp3.inp')
        rules = self._rules.splitlines()
        new_rules = self.wntr.epanet.io._EpanetRule.parse_rules_lines(rules, self.wntr.epanet.util.FlowUnits.GPM)
        for rule in new_rules:
            ctrl = rule.generate_control(self.wn3)
            self.wn3.add_control(ctrl.name, ctrl)
        for control_name in self.wn.control_name_list:
            ctrl1 = self.wn.get_control(control_name)
            ctrl2 = self.wn3.get_control(control_name)
            self.assertTrue(ctrl1._compare(ctrl2))        



class TestInp22FileWriter(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr
        inp_file = join(test_datadir, "Net6_plus.inp")  # UNITS = GPM
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.hydraulic.demand_model = "PDA"
        self.wn.options.hydraulic.required_pressure = 1.0
        self.wntr.network.write_inpfile(self.wn, "temp2.inp", units="LPM")
        self.wn2 = self.wntr.network.WaterNetworkModel("temp2.inp")

    @classmethod
    def tearDownClass(self):
        pass

    def test_pda(self):
        self.assertTrue(self.wn2.options.hydraulic.demand_model == "PDA")
        self.assertTrue(self.wn.options.hydraulic.required_pressure == 1.0)


class TestNet3InpWriterResults(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net3.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)

        sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()

        self.wntr.network.write_inpfile(self.wn, "temp.inp")
        self.wn2 = self.wntr.network.WaterNetworkModel("temp.inp")

        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.results2 = sim.run_sim()

        self.wntr.network.write_inpfile(self.wn, "temp.inp")
        self.wn22 = self.wntr.network.WaterNetworkModel("temp.inp")
        self.wn22.options.hydraulic.demand_model = "PDA"

        sim = self.wntr.sim.EpanetSimulator(self.wn22)
        self.results22 = sim.run_sim(version=2.2)

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate(self):
        for link_name, link in self.wn.links():
            for t in self.results2.link["flowrate"].index:
                self.assertLessEqual(
                    abs(
                        self.results2.link["flowrate"].loc[t, link_name]
                        - self.results.link["flowrate"].loc[t, link_name]
                    ),
                    0.00001,
                )
                self.assertLessEqual(
                    abs(
                        self.results22.link["flowrate"].loc[t, link_name]
                        - self.results.link["flowrate"].loc[t, link_name]
                    ),
                    0.00001,
                )

    def test_node_demand(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node["demand"].index:
                self.assertAlmostEqual(
                    self.results2.node["demand"].loc[t, node_name],
                    self.results.node["demand"].loc[t, node_name],
                    4,
                )
                self.assertAlmostEqual(
                    self.results22.node["demand"].loc[t, node_name],
                    self.results.node["demand"].loc[t, node_name],
                    4,
                )

    def test_node_head(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node["head"].index:
                self.assertLessEqual(
                    abs(
                        self.results2.node["head"].loc[t, node_name]
                        - self.results.node["head"].loc[t, node_name]
                    ),
                    0.01,
                )
                self.assertLessEqual(
                    abs(
                        self.results22.node["head"].loc[t, node_name]
                        - self.results.node["head"].loc[t, node_name]
                    ),
                    0.01,
                )

    def test_node_pressure(self):
        for node_name, node in self.wn.nodes():
            for t in self.results2.node["pressure"].index:
                self.assertLessEqual(
                    abs(
                        self.results2.node["pressure"].loc[t, node_name]
                        - self.results.node["pressure"].loc[t, node_name]
                    ),
                    0.05,
                )
                self.assertLessEqual(
                    abs(
                        self.results22.node["pressure"].loc[t, node_name]
                        - self.results.node["pressure"].loc[t, node_name]
                    ),
                    0.05,
                )


class TestNet3InpUnitsResults(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net3.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)

        sim = self.wntr.sim.EpanetSimulator(self.wn)
        self.results = sim.run_sim()

        self.wntr.network.write_inpfile(self.wn, "temp.inp", units="CMH")
        self.wn2 = self.wntr.network.WaterNetworkModel("temp.inp")

        sim = self.wntr.sim.EpanetSimulator(self.wn2)
        self.results2 = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_link_flowrate_units_convert(self):
        for link_name, link in self.wn.links():
            for t in self.results2.link["flowrate"].index:
                self.assertLessEqual(
                    abs(
                        self.results2.link["flowrate"].loc[t, link_name]
                        - self.results.link["flowrate"].loc[t, link_name]
                    ),
                    0.00001,
                )
    
    def test_link_headloss_units_convert(self):
        
        # headloss = per unit length for pipes and CVs
        pipe_name = '123'
        pipe = self.wn.get_link(pipe_name)
        delta_h = abs(self.results.node["head"].loc[0,pipe.end_node_name] - 
                      self.results.node["head"].loc[0,pipe.start_node_name])
        delta_l = pipe.length
        pipe_headloss = delta_h/delta_l
        
        self.assertLessEqual(
            abs(pipe_headloss - self.results.link["headloss"].loc[0, pipe_name]
            ),
            0.00001,
        )
        
        # headloss = Negative of head gain
        pump_name = '335'
        pump = self.wn.get_link(pump_name)
        delta_h = self.results.node["head"].loc[0,pump.end_node_name] - \
                self.results.node["head"].loc[0,pump.start_node_name]
            
        pump_headloss = - delta_h

        self.assertLessEqual(
            abs(pump_headloss - self.results.link["headloss"].loc[0, pump_name]
            ),
            0.00001,
        )
        

if __name__ == "__main__":
    unittest.main()
