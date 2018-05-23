import wntr
import unittest
import math


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

        t1_head = 10
        j1_head = 0

        m.source_head['t1'].value = t1_head
        m.head['j1'].value = j1_head

        for f in flows_to_test:
            m.flow['p1'].value = f
            r1 = m.hazen_williams_headloss['p1'].evaluate()
            if f <= 0:
                r2 = abs_hw(pipe, f, m) + abs_minor_loss(pipe, f) + t1_head - j1_head
            else:
                r2 = abs_hw(pipe, f, m) + abs_minor_loss(pipe, f) - t1_head + j1_head
            self.assertAlmostEqual(r1, r2, 12)
