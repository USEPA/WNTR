import wntr
import unittest
import math
import numpy as np
import matplotlib.pyplot as plt


def approximate_derivative(con, var, h):
    orig_value = var.value
    var_vals = [orig_value - 2*h, orig_value - h, orig_value + h, orig_value + 2*h]
    f_vals = []
    for i in var_vals:
        var.value = i
        f_vals.append(con.evaluate())
    coeffs = [1, -8, 8, -1]
    var.value = orig_value
    return sum(coeffs[i]*f_vals[i] for i in range(len(f_vals))) / (12*h)


def abs_hw(pipe, f, m):
    f = abs(f)
    if f >= m.hw_q2:
        r = m.hw_k*pipe.roughness**(-1.852)*pipe.diameter**(-4.871)*pipe.length*(f**1.852)
    elif f >= m.hw_q1:
        r = m.hw_k*pipe.roughness**(-1.852)*pipe.diameter**(-4.871)*pipe.length*(m.hw_a*f**3 + m.hw_b*f**2 + m.hw_c*f + m.hw_d)
    else:
        r = m.hw_k*pipe.roughness**(-1.852)*pipe.diameter**(-4.871)*pipe.length*m.hw_m*f
    return r


def abs_minor_loss(pipe, f):
    f = abs(f)
    return pipe.minor_loss/2.0/9.81*(f/(math.pi/4*pipe.diameter**2))**2


class TestHeadloss(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.wn = wn = wntr.network.WaterNetworkModel()
        wn.add_tank('t1', 0, 10, 0, 20, 15)
        wn.add_junction('j1', 0.01)
        wn.add_pipe('p1', 't1', 'j1', minor_loss=10.0)

    def test_HW_headloss(self):
        wn = self.wn
        m = wntr.aml.Model()
        wntr.models.constants.hazen_williams_params(m)
        wntr.models.param.hw_resistance_param(m, wn)
        wntr.models.param.minor_loss_param(m, wn)
        wntr.models.param.status_param(m, wn)
        wntr.models.param.source_head_param(m, wn)
        wntr.models.var.flow_var(m, wn)
        wntr.models.var.head_var(m, wn)
        wntr.models.constraint.hazen_williams_headloss_constraint(m, wn)

        pipe = wn.get_link('p1')

        flows_to_test = [0, m.hw_q1/2.0, m.hw_q1, (m.hw_q1+m.hw_q2)/2.0, m.hw_q2, m.hw_q2+0.1]
        _flows_to_test = [-i for i in flows_to_test]
        flows_to_test.extend(_flows_to_test)
        status_to_test = [1, 0]

        t1_head = 10
        j1_head = 0

        m.source_head['t1'].value = t1_head
        m.head['j1'].value = j1_head

        for status in status_to_test:
            m.status['p1'].value = status
            for f in flows_to_test:
                m.flow['p1'].value = f
                r1 = m.hazen_williams_headloss['p1'].evaluate()
                if status == 1:
                    if f <= 0:
                        r2 = abs_hw(pipe, f, m) + abs_minor_loss(pipe, f) + t1_head - j1_head
                    else:
                        r2 = -abs_hw(pipe, f, m) - abs_minor_loss(pipe, f) + t1_head - j1_head
                else:
                    r2 = f
                self.assertAlmostEqual(r1, r2, 12)
                d1 = m.hazen_williams_headloss['p1'].ad(m.flow['p1'], False)
                d2 = m.hazen_williams_headloss['p1'].ad(m.flow['p1'], True)
                d3 = approximate_derivative(m.hazen_williams_headloss['p1'], m.flow['p1'], 1e-6)
                rel_diff = abs(d1-d2)/abs(d1) * 100
                self.assertLess(rel_diff, 0.1)
                rel_diff = abs(d1-d3)/abs(d3) * 100
                self.assertLess(rel_diff, 0.1)
                self.assertAlmostEqual(d1, d2, 3)
                self.assertAlmostEqual(d1, d3, 3)


class TestPDD(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.wn = wn = wntr.network.WaterNetworkModel()
        wn.add_junction('j1', 0.01)

    def test_pdd(self):
        wn = self.wn
        m = wntr.aml.Model()
        wntr.models.constants.pdd_constants(m)
        wntr.models.param.expected_demand_param(m, wn)
        wntr.models.param.elevation_param(m, wn)
        wntr.models.param.pdd_poly_coeffs_param(m, wn)
        wntr.models.param.pmin_param(m, wn)
        wntr.models.param.pnom_param(m, wn)
        wntr.models.var.head_var(m, wn)
        wntr.models.var.demand_var(m, wn)
        wntr.models.constraint.pdd_constraint(m, wn)

        node = wn.get_node('j1')

        pmin = node.minimum_pressure
        pnom = node.nominal_pressure
        h0 = node.elevation + pmin
        h1 = node.elevation + pnom
        delta = m.pdd_smoothing_delta
        heads_to_test = [h0 - 1, h0, h0 + delta/2, h0 + delta, h0 + (pmin + pnom)/2, h1 - delta, h1 - delta/2, h1, h1 + 1]
        d_expected = node.demand_timeseries_list(wn.sim_time)

        d = 0.01

        m.demand['j1'].value = d
        a1 = m.pdd_poly1_coeffs_a['j1'].value
        b1 = m.pdd_poly1_coeffs_b['j1'].value
        c1 = m.pdd_poly1_coeffs_c['j1'].value
        d1 = m.pdd_poly1_coeffs_d['j1'].value
        a2 = m.pdd_poly2_coeffs_a['j1'].value
        b2 = m.pdd_poly2_coeffs_b['j1'].value
        c2 = m.pdd_poly2_coeffs_c['j1'].value
        d2 = m.pdd_poly2_coeffs_d['j1'].value
        delta = m.pdd_smoothing_delta
        slope = m.pdd_slope

        for h in heads_to_test:
            m.head['j1'].value = h
            r1 = m.pdd['j1'].evaluate()
            p = h - node.elevation
            if p <= pmin:
                r2 = d - d_expected * slope * (p - pmin)
            elif p <= pmin + delta:
                r2 = d - d_expected * (a1*p**3 + b1*p**2 + c1*p + d1)
            elif p <= pnom - delta:
                r2 = d - d_expected * ((p - pmin)/(pnom - pmin))**0.5
            elif p <= pnom:
                r2 = d - d_expected * (a2*p**3 + b2*p**2 + c2*p + d2)
            else:
                r2 = d - d_expected * (slope*(p - pnom) + 1.0)
            # print(p, r1, r2, abs(r1 - r2))
            self.assertAlmostEqual(r1, r2, 12)
            der1 = m.pdd['j1'].ad(m.head['j1'], False)
            der2 = m.pdd['j1'].ad(m.head['j1'], True)
            der3 = approximate_derivative(m.pdd['j1'], m.head['j1'], 1e-6)
            self.assertAlmostEqual(der1, der2, 7)
            self.assertAlmostEqual(der1, der3, 7)
