import math
import unittest
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr
from wntr.sim.models.utils import ModelUpdater

testdir = dirname(abspath(str(__file__)))
test_data_dir = join(testdir, "data_for_testing")


def compare_floats(a, b, tol=1e-5, rel_tol=1e-3):
    if abs(a) >= 1e-8:
        if abs(a - b) / abs(a) * 100 > rel_tol:
            return False
        return True
    if abs(a - b) > tol:
        return False
    return True


def approximate_derivative(con, var, h):
    orig_value = var.value
    var_vals = [orig_value - 2 * h, orig_value - h, orig_value + h, orig_value + 2 * h]
    f_vals = []
    for i in var_vals:
        var.value = i
        f_vals.append(con.evaluate())
    coeffs = [1, -8, 8, -1]
    var.value = orig_value
    return sum(coeffs[i] * f_vals[i] for i in range(len(f_vals))) / (12 * h)


def abs_hw(pipe, f, m):
    f = abs(f)
    if f >= m.hw_q2:
        r = (
            m.hw_k
            * pipe.roughness ** (-1.852)
            * pipe.diameter ** (-4.871)
            * pipe.length
            * (f ** 1.852)
        )
    elif f >= m.hw_q1:
        r = (
            m.hw_k
            * pipe.roughness ** (-1.852)
            * pipe.diameter ** (-4.871)
            * pipe.length
            * (m.hw_a * f ** 3 + m.hw_b * f ** 2 + m.hw_c * f + m.hw_d)
        )
    else:
        r = (
            m.hw_k
            * pipe.roughness ** (-1.852)
            * pipe.diameter ** (-4.871)
            * pipe.length
            * m.hw_m
            * f
        )
    return r


def abs_minor_loss(pipe, f):
    f = abs(f)
    return pipe.minor_loss / 2.0 / 9.81 * (f / (math.pi / 4 * pipe.diameter ** 2)) ** 2


class TestHeadloss(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wn = wn = wntr.network.WaterNetworkModel()
        wn.add_tank("t1", 0, 10, 0, 20, 15)
        wn.add_junction("j1", 0.01)
        wn.add_pipe("p1", "t1", "j1", minor_loss=10.0)
        wn.add_curve("curve1", "HEAD", [(0.0, 10.0), (0.05, 5.0), (0.1, 0.0)])
        wn.add_curve("curve2", "HEAD", [(0.0, 10.0), (0.03, 5.0), (0.1, 0.0)])
        wn.add_curve("curve3", "HEAD", [(0.0, 10.0), (0.07, 5.0), (0.1, 0.0)])

        # add a single point, 2-point, and a set of multi-point curves to test
        wn.add_curve("curve4", "HEAD", [(0.05, 5.0)])
        wn.add_curve("curve5", "HEAD", [(0.0, 10.0), (0.1, 0.0)])

        # multi_point_pump_curves = pump_curves_for_testing() # change to read in a csv file

        df = pd.read_csv(join(test_data_dir, "pump_practice_curves.csv"), skiprows=5)
        multi_point_pump_curves = []
        for i in range(11):
            multi_point_pump_curves.append(df[df["curve number"] == i].iloc[:, 1:3])

        for i, curve in enumerate(multi_point_pump_curves):
            curve_name = "curve{0:d}".format(i + 6)
            wn.add_curve(curve_name, "HEAD", curve.values)

        wn.add_pump("pump1", "t1", "j1", "HEAD", "curve1")
        wn.add_pump("pump2", "t1", "j1", "POWER", 50.0)
        cls.m = m = wntr.sim.aml.Model()
        cls.updater = updater = ModelUpdater()
        wntr.sim.models.constants.hazen_williams_constants(m)
        wntr.sim.models.param.hw_resistance_param.build(m, wn, updater)
        wntr.sim.models.param.minor_loss_param.build(m, wn, updater)
        wntr.sim.models.param.source_head_param(m, wn)
        wntr.sim.models.var.flow_var(m, wn)
        wntr.sim.models.var.head_var(m, wn)
        wntr.sim.models.constraint.piecewise_hazen_williams_headloss_constraint.build(
            m, wn, updater
        )
        wntr.sim.models.constants.head_pump_constants(m)
        wntr.sim.models.constraint.head_pump_headloss_constraint.build(m, wn, updater)
        wntr.sim.models.param.pump_power_param.build(m, wn, updater)
        wntr.sim.models.constraint.power_pump_headloss_constraint.build(m, wn, updater)

    def test_HW_headloss(self):
        wn = self.wn
        m = self.m
        pipe = wn.get_link("p1")

        flows_to_test = [
            0,
            m.hw_q1 / 2.0,
            m.hw_q1,
            (m.hw_q1 + m.hw_q2) / 2.0,
            m.hw_q2,
            m.hw_q2 + 0.1,
        ]
        _flows_to_test = [-i for i in flows_to_test]
        flows_to_test.extend(_flows_to_test)
        status_to_test = [1, 0]

        t1_head = 10
        j1_head = 0

        m.source_head["t1"].value = t1_head
        m.head["j1"].value = j1_head

        for status in status_to_test:
            pipe._user_status = status
            self.updater.update(m, wn, pipe, "status")
            for f in flows_to_test:
                m.flow["p1"].value = f
                r1 = m.piecewise_hazen_williams_headloss["p1"].evaluate()
                if status == 1:
                    if f <= 0:
                        r2 = (
                            abs_hw(pipe, f, m)
                            + abs_minor_loss(pipe, f)
                            + t1_head
                            - j1_head
                        )
                    else:
                        r2 = (
                            -abs_hw(pipe, f, m)
                            - abs_minor_loss(pipe, f)
                            + t1_head
                            - j1_head
                        )
                else:
                    r2 = f
                self.assertAlmostEqual(r1, r2, 12)
                d1 = m.piecewise_hazen_williams_headloss["p1"].reverse_ad()[
                    m.flow["p1"]
                ]
                d2 = m.piecewise_hazen_williams_headloss["p1"].reverse_ad()[
                    m.flow["p1"]
                ]
                d3 = approximate_derivative(
                    m.piecewise_hazen_williams_headloss["p1"], m.flow["p1"], 1e-6
                )
                rel_diff = abs(d1 - d2) / abs(d1) * 100
                self.assertLess(rel_diff, 0.1)
                rel_diff = abs(d1 - d3) / abs(d3) * 100
                self.assertLess(rel_diff, 0.1)
                self.assertAlmostEqual(d1, d2, 3)
                self.assertAlmostEqual(d1, d3, 3)

    def test_head_pump_headloss(self):
        wn = self.wn
        m = self.m
        pump = wn.get_link("pump1")
        curves_to_test = []
        for curve_name, curve in wn.curves.items():
            if curve.curve_type == "HEAD":
                curves_to_test.append(curve)

        flows_to_test = [
            m.pump_q1 - 0.1,
            m.pump_q1,
            (m.pump_q1 + m.pump_q2) / 2,
            m.pump_q2,
            m.pump_q2 + 0.1,
        ]
        status_to_test = [1, 0]

        t1_head = 5
        j1_head = 10

        m.source_head["t1"].value = t1_head
        m.head["j1"].value = j1_head

        for curve in curves_to_test:
            pump.pump_curve_name = curve.name
            self.updater.update(m, wn, pump, "pump_curve_name")
            A, B, C = pump.get_head_curve_coefficients()
            for status in status_to_test:
                pump._user_status = status
                self.updater.update(m, wn, pump, "status")
                for f in flows_to_test:
                    m.flow["pump1"].value = f
                    r1 = m.head_pump_headloss["pump1"].evaluate()
                    if status == 1:
                        if C <= 1:
                            (
                                a,
                                b,
                                c,
                                d,
                            ) = wntr.sim.models.constraint.get_pump_poly_coefficients(
                                A, B, C, m
                            )
                            if f <= m.pump_q1:
                                r2 = m.pump_slope * f + A - j1_head + t1_head
                            elif f <= m.pump_q2:
                                r2 = (
                                    a * f ** 3
                                    + b * f ** 2
                                    + c * f
                                    + d
                                    - j1_head
                                    + t1_head
                                )
                            else:
                                r2 = A - B * f ** C - j1_head + t1_head
                        else:
                            (
                                q_bar,
                                h_bar,
                            ) = wntr.sim.models.constraint.get_pump_line_params(
                                A, B, C, m
                            )
                            if f <= q_bar:
                                r2 = (
                                    m.pump_slope * (f - q_bar)
                                    + h_bar
                                    - j1_head
                                    + t1_head
                                )
                            else:
                                r2 = A - B * f ** C - j1_head + t1_head
                    else:
                        r2 = f
                    self.assertTrue(compare_floats(r1, r2, 1e-12, 1e-12))
                    if f < m.pump_q1 or f > m.pump_q2:
                        d1 = m.head_pump_headloss["pump1"].reverse_ad()[m.flow["pump1"]]
                        d2 = m.head_pump_headloss["pump1"].reverse_ad()[m.flow["pump1"]]
                        d3 = approximate_derivative(
                            m.head_pump_headloss["pump1"], m.flow["pump1"], 1e-6
                        )
                        self.assertTrue(compare_floats(d1, d2, 1e-12, 1e-12))
                        self.assertTrue(compare_floats(d1, d3, 1e-5, 1e-3))

    def test_power_pump_headloss(self):
        wn = self.wn
        m = self.m
        pump = wn.get_link("pump2")

        flows_to_test = np.linspace(-1.0, 1.0, 10, True)
        status_to_test = [1, 0]

        t1_head = 5
        j1_head = 10

        m.source_head["t1"].value = t1_head
        m.head["j1"].value = j1_head

        for status in status_to_test:
            pump._user_status = status
            self.updater.update(m, wn, pump, "status")
            for f in flows_to_test:
                ff = float(f)  # expr.m does not bind to
                # numpy.float64 correctly
                m.flow["pump2"].value = ff

                r1 = m.power_pump_headloss["pump2"].evaluate()
                if status == 1:
                    r2 = pump.power + (t1_head - j1_head) * ff * 9.81 * 1000.0
                else:
                    r2 = ff
                self.assertTrue(compare_floats(r1, r2, 1e-12, 1e-12))
                d1 = m.power_pump_headloss["pump2"].reverse_ad()[m.flow["pump2"]]
                d2 = m.power_pump_headloss["pump2"].reverse_ad()[m.flow["pump2"]]
                d3 = approximate_derivative(
                    m.power_pump_headloss["pump2"], m.flow["pump2"], 1e-6
                )
                self.assertTrue(compare_floats(d1, d2, 1e-12, 1e-12))
                self.assertTrue(compare_floats(d1, d3, 1e-8, 1e-6))


class TestPDD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wn = wn = wntr.network.WaterNetworkModel()
        wn.add_junction("j1", 0.01)

    def test_pdd(self):
        wn = self.wn
        # Changed to handle the specific heads_to_test range, which is bad
        node = wn.get_node("j1")
        node.required_pressure = 20.0
        node.minimum_pressure = 0.0

        m = wntr.sim.aml.Model()
        updater = ModelUpdater()
        wntr.sim.models.constants.pdd_constants(m)
        wntr.sim.models.param.expected_demand_param(m, wn)
        wntr.sim.models.param.elevation_param.build(m, wn, updater)
        wntr.sim.models.param.pdd_poly_coeffs_param.build(m, wn, updater)
        wntr.sim.models.param.pmin_param.build(m, wn, updater)
        wntr.sim.models.param.pnom_param.build(m, wn, updater)
        wntr.sim.models.var.head_var(m, wn)
        wntr.sim.models.var.demand_var(m, wn)
        wntr.sim.models.constraint.pdd_constraint.build(m, wn, updater)

        node = wn.get_node("j1")

        pmin = node.minimum_pressure
        pnom = node.required_pressure
        h0 = node.elevation + pmin
        h1 = node.elevation + pnom
        delta = m.pdd_smoothing_delta
        heads_to_test = [
            h0 - 1,
            h0,
            h0 + delta / 2,
            h0 + delta,
            h0 + (pmin + pnom) / 2,
            h1 - delta,
            h1 - delta / 2,
            h1,
            h1 + 1,
        ]
        d_expected = node.demand_timeseries_list.at(
            wn.sim_time, multiplier=wn.options.hydraulic.demand_multiplier
        )

        d = 0.01

        m.demand["j1"].value = d
        a1 = m.pdd_poly1_coeffs_a["j1"].value
        b1 = m.pdd_poly1_coeffs_b["j1"].value
        c1 = m.pdd_poly1_coeffs_c["j1"].value
        d1 = m.pdd_poly1_coeffs_d["j1"].value
        a2 = m.pdd_poly2_coeffs_a["j1"].value
        b2 = m.pdd_poly2_coeffs_b["j1"].value
        c2 = m.pdd_poly2_coeffs_c["j1"].value
        d2 = m.pdd_poly2_coeffs_d["j1"].value
        delta = m.pdd_smoothing_delta
        slope = m.pdd_slope

        for h in heads_to_test:
            m.head["j1"].value = h
            r1 = m.pdd["j1"].evaluate()
            p = h - node.elevation
            if p <= pmin:
                r2 = d - d_expected * slope * (p - pmin)
            elif p <= pmin + delta:
                r2 = d - d_expected * (a1 * p ** 3 + b1 * p ** 2 + c1 * p + d1)
            elif p <= pnom - delta:
                r2 = d - d_expected * ((p - pmin) / (pnom - pmin)) ** 0.5
            elif p <= pnom:
                r2 = d - d_expected * (a2 * p ** 3 + b2 * p ** 2 + c2 * p + d2)
            else:
                r2 = d - d_expected * (slope * (p - pnom) + 1.0)
            # print(p, r1, r2, abs(r1 - r2))
            self.assertAlmostEqual(r1, r2, 12)
            der1 = m.pdd["j1"].reverse_ad()[m.head["j1"]]
            der2 = m.pdd["j1"].reverse_ad()[m.head["j1"]]
            der3 = approximate_derivative(m.pdd["j1"], m.head["j1"], 1e-6)
            self.assertAlmostEqual(der1, der2, 7)
            self.assertAlmostEqual(der1, der3, 6)


if __name__ == "__main__":
    unittest.main()
