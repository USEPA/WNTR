import wntr.aml as aml
import unittest
import numpy as np
from wntr.aml.aml import _OrderedNameDict


def compare_evaluation(self, m, true_r, true_j):
    m.set_structure()
    vec = m.get_x()
    r = m.evaluate_residuals(vec)
    j = m.evaluate_jacobian()

    for c in m.cons():
        self.assertAlmostEqual(true_r[c], r[c.index], 10)
        for v in m.vars():
            self.assertAlmostEqual(true_j[c][v], j[c.index, v.index], 10)

    m.release_structure()


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
        m.z = aml.Var(z)
        m.c1 = aml.Param(c1)

        expr = aml.Constraint(m.x + m.y + m.c1 + c2)

        self.assertAlmostEqual(expr.evaluate(), x + y + c1 + c2, 10)
        self.assertEqual(expr.ad(m.x), 1)
        self.assertEqual(expr.ad(m.y), 1)
        self.assertEqual(expr.ad(m.z), 0)

    def test_subtract(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        expr = aml.Constraint(m.x - m.y)
        self.assertAlmostEqual(expr.evaluate(), x - y, 10)
        self.assertEqual(expr.ad(m.x), 1)
        self.assertEqual(expr.ad(m.y), -1)

    def test_multiply(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        expr = aml.Constraint(m.x * m.y)
        self.assertAlmostEqual(expr.evaluate(), x * y, 10)
        self.assertEqual(expr.ad(m.x), y)
        self.assertEqual(expr.ad(m.y), x)

    def test_divide(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        expr = aml.Constraint(m.x / m.y)
        self.assertAlmostEqual(expr.evaluate(), x / y, 10)
        self.assertAlmostEqual(expr.ad(m.x), 1/y, 10)
        self.assertAlmostEqual(expr.ad(m.y), -x/y**2, 10)

    def test_power(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        expr = aml.Constraint(m.x**(m.y))
        self.assertAlmostEqual(expr.evaluate(), x ** y, 10)
        self.assertAlmostEqual(expr.ad(m.x), y*x**(y-1), 10)
        self.assertAlmostEqual(expr.ad(m.y), x**y * np.log(x), 10)

    @unittest.skip('exp is not implemented yet')
    def test_exp(self):
        m = aml.Model()
        x = 2.5
        m.x = aml.Var(x)

        expr = aml.exp(m.x)
        self.assertAlmostEqual(aml.value(expr), np.exp(x), 10)
        self.assertAlmostEqual(aml.value(expr.ad(m.x)), np.exp(x), 10)

    @unittest.skip('log is not implemented yet')
    def test_log(self):
        m = aml.Model()
        x = 2.5
        m.x = aml.Var(x)

        expr = aml.log(m.x)
        self.assertAlmostEqual(aml.value(expr), np.log(x), 10)
        self.assertAlmostEqual(aml.value(expr.ad(m.x)), 1/x, 10)

    @unittest.skip('exp is not implemented yet')
    def test_chain_rule(self):
        m = aml.Model()
        x = 1.1
        m.x = aml.Var(x)

        expr = aml.exp((m.x + m.x**0.5)**2) - m.x

        actual_deriv = np.exp((x + x**0.5)**2)*2*(x + x**0.5)*(1 + 0.5*x**(-0.5)) - 1
        self.assertAlmostEqual(aml.value(expr), np.exp((x + x**0.5)**2) - x, 10)
        self.assertAlmostEqual(aml.value(expr.ad(m.x)), actual_deriv, 10)


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

        true_con_values = _OrderedNameDict()
        true_con_values[m.con1] = x + 2 * y + c
        true_con_values[m.con2] = x ** 2 - y ** 2 + 10

        true_jac = _OrderedNameDict()
        true_jac[m.con1] = _OrderedNameDict()
        true_jac[m.con2] = _OrderedNameDict()
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
        true_jac[m.con3] = _OrderedNameDict()
        true_jac[m.con3][m.x] = y
        true_jac[m.con3][m.y] = x

        compare_evaluation(self, m, true_con_values, true_jac)

    def test_if_then_constraints(self):
        m = aml.Model()
        x = -4.5
        y = -3.7
        m.x = aml.Var(x)
        m.y = aml.Var(y)

        con1 = aml.ConditionalExpression()
        con1.add_condition(m.x + 1, -(-m.x)**1.852 - (-m.x)**2 - m.y)
        con1.add_condition(m.x - 1, m.x)
        con1.add_final_expr(m.x**1.852 + m.x**2 - m.y)
        m.con1 = aml.Constraint(con1)

        con2 = aml.ConditionalExpression()
        con2.add_condition(m.y + 1, -(-m.y)**(1.852) - (-m.y)**(2) - m.x)
        con2.add_condition(m.y - 1, m.y)
        con2.add_final_expr(m.y**(1.852) + m.y**(2) - m.x)
        m.con2 = aml.Constraint(con2)

        true_con_values = _OrderedNameDict()
        true_jac = _OrderedNameDict()
        true_con_values[m.con1] = -(abs(x)**1.852 + abs(x)**2) - y
        true_con_values[m.con2] = -(abs(y)**1.852 + abs(y)**2) - x
        true_jac[m.con1] = _OrderedNameDict()
        true_jac[m.con2] = _OrderedNameDict()
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
        true_con_values[m.con1] = x**1.852 + x**2 - y
        true_con_values[m.con2] = y**1.852 + y**2 - x
        true_jac[m.con1][m.x] = 1.852 * x ** 0.852 + 2 * x
        true_jac[m.con1][m.y] = -1
        true_jac[m.con2][m.x] = -1
        true_jac[m.con2][m.y] = 1.852 * y ** 0.852 + 2 * y
        compare_evaluation(self, m, true_con_values, true_jac)

        del true_con_values[m.con2]
        del true_jac[m.con2]
        del m.con2
        con2 = aml.ConditionalExpression()
        con2.add_condition(m.y + 1, -(-m.y)**2.852 - (-m.y)**3 - m.x)
        con2.add_condition(m.y - 1, m.y**2)
        con2.add_final_expr(m.y**2.852 + m.y**3 - m.x)
        m.con2 = aml.Constraint(con2)

        true_jac[m.con2] = _OrderedNameDict()
        x = -4.5
        y = -3.7
        m.x.value = x
        m.y.value = y
        true_con_values[m.con1] = -(abs(x)**1.852 + abs(x)**2) - y
        true_con_values[m.con2] = -(abs(y)**2.852 + abs(y)**3) - x
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
        true_con_values[m.con2] = y**2
        true_jac[m.con1][m.x] = 1
        true_jac[m.con1][m.y] = 0
        true_jac[m.con2][m.x] = 0
        true_jac[m.con2][m.y] = 2*y
        compare_evaluation(self, m, true_con_values, true_jac)

        x = 4.5
        y = 3.7
        m.x.value = x
        m.y.value = y
        true_con_values[m.con1] = x**1.852 + x**2 - y
        true_con_values[m.con2] = y**2.852 + y**3 - x
        true_jac[m.con1][m.x] = 1.852 * x ** 0.852 + 2 * x
        true_jac[m.con1][m.y] = -1
        true_jac[m.con2][m.x] = -1
        true_jac[m.con2][m.y] = 2.852 * y ** 1.852 + 3 * y ** 2
        compare_evaluation(self, m, true_con_values, true_jac)


class TestCSRJacobian(unittest.TestCase):
    def test_register_and_remove_constraint(self):
        m = aml.Model('wntr')
        m.x = aml.Var(2.0)
        m.y = aml.Var(3.0)
        m.z = aml.Var(4.0)
        m.v = aml.Var(10.0)
        m.c1 = aml.Constraint(m.x + m.y)
        m.c2 = aml.Constraint(m.x * m.y * m.v)
        m.c3 = aml.Constraint(m.z**3.0)
        m.c4 = aml.Constraint(m.x + 1.0 / m.v)
        m.set_structure()
        con_values = m.evaluate_residuals()
        A = m.evaluate_jacobian()

        true_con_values = _OrderedNameDict()
        true_con_values[m.c1] = 5.0
        true_con_values[m.c2] = 60.0
        true_con_values[m.c3] = 64.0
        true_con_values[m.c4] = 2.1
        for c in m.cons():
            self.assertTrue(true_con_values[c] == con_values[c.index])
        true_jac = _OrderedNameDict()
        true_jac[m.c1] = _OrderedNameDict()
        true_jac[m.c2] = _OrderedNameDict()
        true_jac[m.c3] = _OrderedNameDict()
        true_jac[m.c4] = _OrderedNameDict()
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

        m.release_structure()
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
        true_jac[m.c3][m.x] = 0.0
        true_jac[m.c3][m.y] = 0.0
        true_jac[m.c3][m.z] = 1.0
        true_jac[m.c3][m.v] = 0.0
        for c in m.cons():
            for v in m.vars():
                self.assertTrue(true_jac[c][v] == A[c.index, v.index])


if __name__ == '__main__':
    unittest.main()
