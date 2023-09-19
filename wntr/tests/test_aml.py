import unittest
from collections import OrderedDict

import numpy as np
import wntr.sim.aml as aml
from wntr.sim.solvers import NewtonSolver, SolverStatus


def compare_evaluation(self, m, true_r, true_j):
    m.set_structure()
    vec = m.get_x()
    r = m.evaluate_residuals(vec)
    j = m.evaluate_jacobian()

    for c in m.cons():
        self.assertAlmostEqual(true_r[c], r[c.index], 10)
        for v in m.vars():
            self.assertAlmostEqual(true_j[c][v], j[c.index, v.index], 10)


class TestModel(unittest.TestCase):
    def test_var_value_with_decrement(self):
        m = aml.Model()
        m.x = aml.Var()
        m.p = aml.Param(val=1)
        m.c = aml.Constraint(m.x - m.p)
        m.set_structure()
        opt = NewtonSolver({'TOL': 1e-8})
        status, msg, num_iter = opt.solve(m)
        self.assertEqual(status, SolverStatus.converged)
        self.assertAlmostEqual(m.x.value, 1)
        m.p.value = 2
        status, msg, num_iter = opt.solve(m)
        self.assertEqual(status, SolverStatus.converged)
        self.assertAlmostEqual(m.x.value, 2)
        del m.c
        m.c = aml.Constraint(m.x**0.5 - m.p)
        m.set_structure()
        self.assertAlmostEqual(m.x.value, 2)  # this is the real test here
        status, msg, num_iter = opt.solve(m)
        self.assertEqual(status, SolverStatus.converged)
        self.assertAlmostEqual(m.x.value, 4)


class TestExpression(unittest.TestCase):
    def test_add(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        z = 10.0
        c1 = 8.6
        c2 = 3.3
        m.x = aml.Var(x)
        m.y = aml.Var(y)
        m.c1 = aml.Param(c1)

        expr = m.x + m.y + m.c1 + c2

        self.assertAlmostEqual(expr.evaluate(), x + y + c1 + c2, 10)
        ders = expr.reverse_ad()
        self.assertEqual(ders[m.x], 1)
        self.assertEqual(ders[m.y], 1)

    def test_subtract(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        expr = m.x - m.y
        self.assertAlmostEqual(expr.evaluate(), x - y, 10)
        ders = expr.reverse_ad()
        self.assertEqual(ders[m.x], 1)
        self.assertEqual(ders[m.y], -1)

    def test_multiply(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        expr = m.x * m.y
        self.assertAlmostEqual(expr.evaluate(), x * y, 10)
        ders = expr.reverse_ad()
        self.assertEqual(ders[m.x], y)
        self.assertEqual(ders[m.y], x)

    def test_divide(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        expr = m.x / m.y
        self.assertAlmostEqual(expr.evaluate(), x / y, 10)
        ders = expr.reverse_ad()
        self.assertAlmostEqual(ders[m.x], 1 / y, 10)
        self.assertAlmostEqual(ders[m.y], -x / y ** 2, 10)

    def test_power(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        expr = m.x ** (m.y)
        self.assertAlmostEqual(expr.evaluate(), x ** y, 10)
        ders = expr.reverse_ad()
        self.assertAlmostEqual(ders[m.x], y * x ** (y - 1), 10)
        self.assertAlmostEqual(ders[m.y], x ** y * np.log(x), 10)

    def test_exp(self):
        m = aml.Model()
        x = 2.5
        m.x = aml.Var(x)

        expr = aml.exp(m.x)
        self.assertAlmostEqual(aml.value(expr), np.exp(x), 10)
        self.assertAlmostEqual(expr.reverse_ad()[m.x], np.exp(x), 10)

    def test_log(self):
        m = aml.Model()
        x = 2.5
        m.x = aml.Var(x)

        expr = aml.log(m.x)
        self.assertAlmostEqual(aml.value(expr), np.log(x), 10)
        self.assertAlmostEqual(expr.reverse_ad()[m.x], 1 / x, 10)

    def test_chain_rule(self):
        m = aml.Model()
        x = 1.1
        m.x = aml.Var(x)

        expr = aml.exp((m.x + m.x ** 0.5) ** 2) - m.x

        actual_deriv = (
            np.exp((x + x ** 0.5) ** 2) * 2 * (x + x ** 0.5) * (1 + 0.5 * x ** (-0.5))
            - 1
        )
        self.assertAlmostEqual(aml.value(expr), np.exp((x + x ** 0.5) ** 2) - x, 10)
        self.assertAlmostEqual(expr.reverse_ad()[m.x], actual_deriv, 10)


class TestConstraint(unittest.TestCase):
    def test_basic_constraints(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        c = 1.5
        m.x = aml.Var(x)
        m.y = aml.Var(y)
        m.c = aml.Param(c)

        m.con1 = aml.Constraint(m.x + 2.0 * m.y + m.c)
        m.con2 = aml.Constraint(m.x ** 2 - m.y ** 2 + 10)

        true_con_values = OrderedDict()
        true_con_values[m.con1] = x + 2 * y + c
        true_con_values[m.con2] = x ** 2 - y ** 2 + 10

        true_jac = OrderedDict()
        true_jac[m.con1] = OrderedDict()
        true_jac[m.con2] = OrderedDict()
        true_jac[m.con1][m.x] = 1
        true_jac[m.con1][m.y] = 2
        true_jac[m.con2][m.x] = 2 * x
        true_jac[m.con2][m.y] = -2 * y

        compare_evaluation(self, m, true_con_values, true_jac)

        del true_con_values[m.con2]
        del true_jac[m.con2]
        del m.con2
        m.con3 = aml.Constraint(m.x * m.y)
        true_con_values[m.con3] = x * y
        true_jac[m.con3] = OrderedDict()
        true_jac[m.con3][m.x] = y
        true_jac[m.con3][m.y] = x

        compare_evaluation(self, m, true_con_values, true_jac)

    def test_if_then_constraints(self):
        m = aml.Model()
        x = -4.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        e = aml.ConditionalExpression()
        e.add_condition(
            aml.inequality(body=m.x, ub=-1), -((-m.x) ** 1.852) - (-m.x) ** 2 - m.y
        )
        e.add_condition(aml.inequality(body=m.x, ub=1), m.x)
        e.add_final_expr(m.x ** 1.852 + m.x ** 2 - m.y)
        m.con1 = aml.Constraint(e)

        e = aml.ConditionalExpression()
        e.add_condition(
            aml.inequality(body=m.y, ub=-1), -((-m.y) ** (1.852)) - (-m.y) ** (2) - m.x
        )
        e.add_condition(aml.inequality(body=m.y, ub=1), m.y)
        e.add_final_expr(m.y ** (1.852) + m.y ** (2) - m.x)
        m.con2 = aml.Constraint(e)

        true_con_values = OrderedDict()
        true_jac = OrderedDict()
        true_con_values[m.con1] = -(abs(x) ** 1.852 + abs(x) ** 2) - y
        true_con_values[m.con2] = -(abs(y) ** 1.852 + abs(y) ** 2) - x
        true_jac[m.con1] = OrderedDict()
        true_jac[m.con2] = OrderedDict()
        true_jac[m.con1][m.x] = 1.852 * abs(x) ** 0.852 + 2 * abs(x)
        true_jac[m.con1][m.y] = -1
        true_jac[m.con2][m.x] = -1
        true_jac[m.con2][m.y] = 1.852 * abs(y) ** 0.852 + 2 * abs(y)
        compare_evaluation(self, m, true_con_values, true_jac)

        x = 0.5
        y = 0.3
        m.x.value = x
        m.y.value = y
        true_con_values[m.con1] = x
        true_con_values[m.con2] = y
        true_jac[m.con1][m.x] = 1
        true_jac[m.con1][m.y] = 0
        true_jac[m.con2][m.x] = 0
        true_jac[m.con2][m.y] = 1
        compare_evaluation(self, m, true_con_values, true_jac)

        x = 4.5
        y = 3.7
        m.x.value = x
        m.y.value = y
        true_con_values[m.con1] = x ** 1.852 + x ** 2 - y
        true_con_values[m.con2] = y ** 1.852 + y ** 2 - x
        true_jac[m.con1][m.x] = 1.852 * x ** 0.852 + 2 * x
        true_jac[m.con1][m.y] = -1
        true_jac[m.con2][m.x] = -1
        true_jac[m.con2][m.y] = 1.852 * y ** 0.852 + 2 * y
        compare_evaluation(self, m, true_con_values, true_jac)

        del true_con_values[m.con2]
        del true_jac[m.con2]
        del m.con2
        e = aml.ConditionalExpression()
        e.add_condition(
            aml.inequality(body=m.y, ub=-1), -((-m.y) ** 2.852) - (-m.y) ** 3 - m.x
        )
        e.add_condition(aml.inequality(body=m.y, ub=1), m.y ** 2)
        e.add_final_expr(m.y ** 2.852 + m.y ** 3 - m.x)
        m.con2 = aml.Constraint(e)

        true_jac[m.con2] = OrderedDict()
        x = -4.5
        y = -3.7
        m.x.value = x
        m.y.value = y
        true_con_values[m.con1] = -(abs(x) ** 1.852 + abs(x) ** 2) - y
        true_con_values[m.con2] = -(abs(y) ** 2.852 + abs(y) ** 3) - x
        true_jac[m.con1][m.x] = 1.852 * abs(x) ** 0.852 + 2 * abs(x)
        true_jac[m.con1][m.y] = -1
        true_jac[m.con2][m.x] = -1
        true_jac[m.con2][m.y] = 2.852 * abs(y) ** 1.852 + 3 * abs(y) ** 2
        compare_evaluation(self, m, true_con_values, true_jac)

        x = 0.5
        y = 0.3
        m.x.value = x
        m.y.value = y
        true_con_values[m.con1] = x
        true_con_values[m.con2] = y ** 2
        true_jac[m.con1][m.x] = 1
        true_jac[m.con1][m.y] = 0
        true_jac[m.con2][m.x] = 0
        true_jac[m.con2][m.y] = 2 * y
        compare_evaluation(self, m, true_con_values, true_jac)

        x = 4.5
        y = 3.7
        m.x.value = x
        m.y.value = y
        true_con_values[m.con1] = x ** 1.852 + x ** 2 - y
        true_con_values[m.con2] = y ** 2.852 + y ** 3 - x
        true_jac[m.con1][m.x] = 1.852 * x ** 0.852 + 2 * x
        true_jac[m.con1][m.y] = -1
        true_jac[m.con2][m.x] = -1
        true_jac[m.con2][m.y] = 2.852 * y ** 1.852 + 3 * y ** 2
        compare_evaluation(self, m, true_con_values, true_jac)


class TestCSRJacobian(unittest.TestCase):
    def test_register_and_remove_constraint(self):
        m = aml.Model()
        m.x = aml.Var(2.0)
        m.y = aml.Var(3.0)
        m.z = aml.Var(4.0)
        m.v = aml.Var(10.0)
        m.c1 = aml.Constraint(m.x + m.y)
        m.c2 = aml.Constraint(m.x * m.y * m.v)
        m.c3 = aml.Constraint(m.z ** 3.0)
        m.c4 = aml.Constraint(m.x + 1.0 / m.v)
        m.set_structure()
        con_values = m.evaluate_residuals()
        A = m.evaluate_jacobian()

        true_con_values = OrderedDict()
        true_con_values[m.c1] = 5.0
        true_con_values[m.c2] = 60.0
        true_con_values[m.c3] = 64.0
        true_con_values[m.c4] = 2.1
        for c in m.cons():
            self.assertTrue(true_con_values[c] == con_values[c.index])
        true_jac = OrderedDict()
        true_jac[m.c1] = OrderedDict()
        true_jac[m.c2] = OrderedDict()
        true_jac[m.c3] = OrderedDict()
        true_jac[m.c4] = OrderedDict()
        true_jac[m.c1][m.x] = 1.0
        true_jac[m.c1][m.y] = 1.0
        true_jac[m.c1][m.z] = 0.0
        true_jac[m.c1][m.v] = 0.0
        true_jac[m.c2][m.x] = 30.0
        true_jac[m.c2][m.y] = 20.0
        true_jac[m.c2][m.z] = 0.0
        true_jac[m.c2][m.v] = 6.0
        true_jac[m.c3][m.x] = 0.0
        true_jac[m.c3][m.y] = 0.0
        true_jac[m.c3][m.z] = 48.0
        true_jac[m.c3][m.v] = 0.0
        true_jac[m.c4][m.x] = 1.0
        true_jac[m.c4][m.y] = 0.0
        true_jac[m.c4][m.z] = 0.0
        true_jac[m.c4][m.v] = -0.01
        for c in m.cons():
            for v in m.vars():
                self.assertTrue(true_jac[c][v] == A[c.index, v.index])

        del m.c3
        m.c3 = aml.Constraint(m.z)
        m.set_structure()
        con_values = m.evaluate_residuals()
        A = m.evaluate_jacobian()

        true_con_values[m.c1] = 5.0
        true_con_values[m.c2] = 60.0
        true_con_values[m.c3] = 4.0
        true_con_values[m.c4] = 2.1
        for c in m.cons():
            self.assertTrue(true_con_values[c] == con_values[c.index])
        true_jac[m.c3] = OrderedDict()
        true_jac[m.c3][m.x] = 0.0
        true_jac[m.c3][m.y] = 0.0
        true_jac[m.c3][m.z] = 1.0
        true_jac[m.c3][m.v] = 0.0
        for c in m.cons():
            for v in m.vars():
                self.assertTrue(true_jac[c][v] == A[c.index, v.index])


class TestExceptions(unittest.TestCase):
    def test_structure_exception(self):
        m = aml.Model()
        m.x = aml.Var()
        m.c = aml.Constraint(m.x - 1)
        with self.assertRaises(RuntimeError):
            m.get_x()
        m.set_structure()
        m.get_x()
        m.y = aml.Var()
        m.c2 = aml.Constraint(m.x + m.y)
        with self.assertRaises(RuntimeError):
            m.get_x()
        m.set_structure()
        x = m.get_x()
        self.assertEqual(len(x), 2)


if __name__ == "__main__":
    unittest.main()
