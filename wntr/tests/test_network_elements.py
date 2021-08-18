"""
Test the wntr.network.elements classes
"""
import unittest
from os.path import abspath, dirname, join
from unittest import SkipTest

import numpy as np
import wntr
import wntr.network.elements as elements
from wntr.network.options import TimeOptions

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
net1dir = join(testdir, "..", "..", "examples", "networks")


class TestElements(unittest.TestCase):
    def test_Curve(self):
        pts1 = [[3, 5]]
        pts2 = [[3, 6], [7, 2], [10, 0]]
        pts3 = [[3, 6], [7, 2], [10, 1]]
        expected_str = (
            "<Curve: 'curve2', curve_type='HEAD', points=[[3, 6], [7, 2], [10, 0]]>"
        )
        # Create the curves
        curve1 = elements.Curve("curve1", "PUMP", pts1)
        curve2a = elements.Curve("curve2", "HEAD", pts2)
        curve2b = elements.Curve("curve2", "HEAD", pts3)
        curve2c = elements.Curve("curve2", "HEAD", pts3)
        # Test that the assignments are working
        self.assertListEqual(curve2b.points, pts3)
        self.assertEqual(curve1.num_points, 1)
        self.assertEqual(len(curve2c), 3)
        # Testing __eq__
        self.assertNotEqual(curve1, curve2a)
        self.assertNotEqual(curve2a, curve2b)
        self.assertEqual(curve2b, curve2c)
        # testing __getitem__ and __getslice__
        self.assertListEqual(curve2a[0], [3, 6])
        self.assertListEqual(curve2a[:2], [[3, 6], [7, 2]])
        # verify that the points are being deep copied
        self.assertNotEqual(id(curve2b.points), id(curve2c.points))

    def test_Pattern(self):
        pattern_points1 = [1, 2, 3, 4, 3, 2, 1]
        pattern_points2 = [1.0, 1.2, 1.0]
        pattern_points3 = 3.2

        # test constant pattern creation
        timing1 = TimeOptions()
        timing1.pattern_start = 0
        timing1.pattern_timestep = 1

        timing2 = TimeOptions()
        timing2.pattern_start = 0
        timing2.pattern_timestep = 5
        pattern1a = elements.Pattern(
            "constant", multipliers=pattern_points3, time_options=timing1
        )
        pattern1b = elements.Pattern(
            "constant", multipliers=[pattern_points3], time_options=(0, 1)
        )
        self.assertListEqual(pattern1a.multipliers.tolist(), [pattern_points3])
        self.assertTrue(np.all(pattern1a.multipliers == pattern1b.multipliers))
        self.assertFalse(id(pattern1a.multipliers) == id(pattern1b.multipliers))
        self.assertEqual(pattern1a.time_options, pattern1b.time_options)

        # def multipliers setter
        pattern2a = elements.Pattern(
            "oops", multipliers=pattern_points3, time_options=(0, 5)
        )
        pattern2b = elements.Pattern(
            "oops", multipliers=pattern_points1, time_options=timing2
        )
        pattern2a.multipliers = pattern_points1
        self.assertEqual(pattern2a.time_options, pattern2b.time_options)

        # test pattern evaluations
        expected_value = pattern_points1[2]
        self.assertEqual(pattern2a[2], expected_value)
        self.assertEqual(pattern2b.at(10), expected_value)
        self.assertEqual(pattern2b.at(12.5), expected_value)
        self.assertEqual(pattern2b.at(14), expected_value)
        self.assertEqual(pattern2b.at(9 * 5), expected_value)
        self.assertNotEqual(pattern2b.at(15), expected_value)

        pattern3 = elements.Pattern(
            "nowrap", multipliers=pattern_points2, time_options=(0, 100), wrap=False
        )
        self.assertEqual(pattern3[5], 0.0)
        self.assertEqual(pattern3[-39], 0.0)
        self.assertEqual(pattern3.at(-39), 0.0)
        self.assertEqual(pattern3.at(50), 1.0)

        pattern4 = elements.Pattern("constant")
        self.assertEqual(len(pattern4), 0)
        self.assertEqual(pattern4.at(492), 1.0)

        pattern5a = elements.Pattern(
            "binary",
            [0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
            time_options=(0, 1),
            wrap=False,
        )
        pattern5b = elements.Pattern.binary_pattern(
            "binary", step_size=1, start_time=2, end_time=6, duration=9
        )
        self.assertFalse(pattern5a.__eq__(pattern5b))
        self.assertTrue(
            np.all(np.abs(pattern5a.multipliers - pattern5b.multipliers) < 1.0e-10)
        )

    def test_pattern_interpolation(self):
        timing = TimeOptions()
        timing.pattern_interpolation = True
        p = elements.Pattern('p1', multipliers=[1, 1.2, 1.6], time_options=timing)
        self.assertAlmostEqual(p.at(0), 1)
        self.assertAlmostEqual(p.at(3600), 1.2)
        self.assertAlmostEqual(p.at(7200), 1.6)
        self.assertAlmostEqual(p.at(1800), 1.1)
        self.assertAlmostEqual(p.at(5400), 1.4)
        self.assertAlmostEqual(p.at(2250), 0.2/3600*2250 + 1)
        self.assertAlmostEqual(p.at(9000), 1.3)
        self.assertAlmostEqual(p.at(12600), 1.1)

    def test_TimeSeries(self):
        wn = wntr.network.WaterNetworkModel()

        pattern_points2 = [1.0, 1.2, 1.0]
        wn.add_pattern("oops", pattern_points2)
        pattern2 = wn.get_pattern("oops")
        pattern5 = elements.Pattern.binary_pattern(
            "binary", step_size=1, start_time=2, end_time=6, duration=9
        )
        wn.add_pattern("binary", pattern5)
        base1 = 2.0

        # test constructor and setters, getters
        tvv1 = elements.TimeSeries(wn.patterns, base1, None, None)
        tvv2 = elements.TimeSeries(wn.patterns, base1, "oops", "tvv2")
        self.assertRaises(ValueError, elements.TimeSeries, *("A", None, None))
        self.assertRaises(ValueError, elements.TimeSeries, *(1.0, "A", None))
        self.assertEqual(tvv1._base, base1)
        self.assertEqual(tvv1.base_value, tvv1._base)
        self.assertEqual(tvv1.pattern_name, None)
        self.assertEqual(tvv1.pattern, None)
        self.assertEqual(tvv1.category, None)
        tvv1.base_value = 3.0
        self.assertEqual(tvv1.base_value, 3.0)
        tvv1.pattern_name = "binary"
        self.assertEqual(tvv1.pattern_name, "binary")
        tvv1.category = "binary"
        self.assertEqual(tvv1.category, "binary")

        # Test getitem
        # print(tvv1)
        # print(tvv2, pattern2)
        self.assertEqual(tvv1.at(1), 0.0)
        self.assertEqual(tvv1.at(7202), 3.0)
        self.assertEqual(tvv2.at(1), 2.0)
        # print(tvv2, pattern2.time_options)
        self.assertEqual(tvv2.at(3602), 2.4)

        price1 = elements.TimeSeries(wn.patterns, 35.0, None)
        price2 = elements.TimeSeries(wn.patterns, 35.0, None)
        self.assertEqual(price1, price2)
        self.assertEqual(price1.base_value, 35.0)

        speed1 = elements.TimeSeries(wn.patterns, 35.0, pattern5)
        speed2 = elements.TimeSeries(wn.patterns, 35.0, pattern5)
        self.assertEqual(speed1, speed2)
        self.assertEqual(speed1.base_value, 35.0)

        head1 = elements.TimeSeries(wn.patterns, 35.0, pattern2)
        head2 = elements.TimeSeries(wn.patterns, 35.0, pattern2)
        self.assertEqual(head1, head2)
        self.assertEqual(head1.base_value, 35.0)

        demand1 = elements.TimeSeries(wn.patterns, 1.35, pattern2)
        demand2 = elements.TimeSeries(wn.patterns, 1.35, pattern2)
        self.assertEqual(demand1, demand2)
        self.assertEqual(demand1.base_value, 1.35)

    #    expected_values1 = np.array([1.35, 1.62, 1.35, 1.35, 1.62])
    #    demand_values1 = demand2.get_values(0, 40, 10)
    #    self.assertTrue(np.all(np.abs(expected_values1-demand_values1)<1.0e-10))
    #    expected_values1 = np.array([1.35, 1.35, 1.62, 1.62, 1.35, 1.35, 1.35, 1.35, 1.62])
    #    demand_values1 = demand2.get_values(0, 40, 5)
    #    self.assertTrue(np.all(np.abs(expected_values1-demand_values1)<1.0e-10))
    #
    #    source1 = elements.Source('source1', 'NODE-1131', 'CONCEN', 1000.0, pattern5)
    #    source2 = elements.Source('source1', 'NODE-1131', 'CONCEN', 1000.0, pattern5)
    #    self.assertEqual(source1, source2)
    #    self.assertEqual(source1.strength_timeseries.base_value, 1000.0)

    def test_Demands(self):
        wn = wntr.network.WaterNetworkModel()

        pattern_points1 = [0.5, 1.0, 0.4, 0.2]
        pattern1 = elements.Pattern(
            "1", multipliers=pattern_points1, time_options=(0, 10)
        )
        pattern_points2 = [1.0, 1.2, 1.0]
        pattern2 = elements.Pattern(
            "2", multipliers=pattern_points2, time_options=(0, 10)
        )
        demand1 = elements.TimeSeries(wn.patterns, 2.5, pattern1, "_base_demand")
        demand2 = elements.TimeSeries(wn.patterns, 1.0, pattern2, "residential")
        demand3 = elements.TimeSeries(wn.patterns, 0.8, pattern2, "residential")

        expected1 = 2.5 * np.array(pattern_points1 * 3)
        expected2 = 1.0 * np.array(pattern_points2 * 4)
        expected3 = 0.8 * np.array(pattern_points2 * 4)
        expectedtotal = expected1 + expected2 + expected3
        expectedresidential = expected2 + expected3
        demandlist1 = elements.Demands(wn.patterns, demand1, demand2, demand3)
        demandlist2 = elements.Demands(wn.patterns)
        demandlist2.append(demand1)
        demandlist2.append(demand1)
        demandlist2[1] = demand2
        demandlist2.append((0.8, pattern2, "residential"))
        self.assertListEqual(list(demandlist1), list(demandlist2))

        demandlist2.extend(demandlist1)
        self.assertEqual(len(demandlist1), 3)
        self.assertEqual(len(demandlist2), 6)
        del demandlist2[3]
        del demandlist2[3]
        del demandlist2[3]
        del demandlist2[0]
        demandlist2.insert(0, demand1)
        self.assertListEqual(list(demandlist1), list(demandlist2))
        demandlist2.clear()
        self.assertEqual(len(demandlist2), 0)
        self.assertFalse(demandlist2)

        raise SkipTest

        self.assertEqual(demandlist1.at(5), expectedtotal[0])
        self.assertEqual(demandlist1.at(13), expectedtotal[1])
        self.assertEqual(demandlist1.at(13, "residential"), expectedresidential[1])
        self.assertTrue(
            np.all(np.abs(demandlist1.get_values(0, 110, 10) - expectedtotal) < 1.0e-10)
        )
        self.assertListEqual(demandlist1.base_demand_list(), [2.5, 1.0, 0.8])
        self.assertListEqual(demandlist1.base_demand_list("_base_demand"), [2.5])
        self.assertListEqual(demandlist1.pattern_list(), [pattern1, pattern2, pattern2])
        self.assertListEqual(
            demandlist1.pattern_list(category="residential"), [pattern2, pattern2]
        )
        self.assertListEqual(
            demandlist1.category_list(), ["_base_demand", "residential", "residential"]
        )

    def test_fire_fighting_demand(self):
        # Setup network
        wn = wntr.network.WaterNetworkModel()
        wn.add_junction(
            "new_junction", base_demand=1, elevation=10, coordinates=(6, 25)
        )
        duration = 1 * 5 * 60 * 60
        wn.options.time.duration = duration

        # Add fire demand
        node = wn.get_node("new_junction")
        fire_flow_demand = 0.252
        fire_start = 2 * 60 * 60
        fire_end = 4 * 60 * 60
        node.add_fire_fighting_demand(wn, fire_flow_demand, fire_start, fire_end)
        ff_demand = list(
            wntr.metrics.hydraulic.expected_demand(wn)["new_junction"].values
        )
        expected_ff_demand = [1, 1, 1.252, 1.252, 1, 1]
        self.assertListEqual(ff_demand, expected_ff_demand)

        # Remove fire demand
        node.remove_fire_fighting_demand(wn)
        self.assertTrue(
            not ("Fire_Flow" in node.demand_timeseries_list.category_list())
        )


if __name__ == "__main__":
    unittest.main()
