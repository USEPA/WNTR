import wntr.aml as aml
import unittest
import numpy as np
from scipy.sparse import csr_matrix


class TestExpression(unittest.TestCase):
    def test_add(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        z = 10.0
        c1 = 8.6
        c2 = 3.3
        m.x = aml.create_var(x)
        m.y = aml.create_var(y)
        m.z = aml.create_var(z)
        m.c1 = aml.create_param(c1)

        expr = m.x + m.y + m.c1 + c2

        self.assertAlmostEqual(expr.evaluate(), x + y + c1 + c2, 10)
        self.assertEqual(expr.ad(m.x), 1)
        self.assertEqual(expr.ad(m.y), 1)
        self.assertEqual(expr.ad(m.z), 0)

    def test_subtract(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.create_var(x)
        m.y = aml.create_var(y)

        expr = m.x - m.y
        self.assertAlmostEqual(expr.evaluate(), x - y, 10)
        self.assertEqual(expr.ad(m.x), 1)
        self.assertEqual(expr.ad(m.y), -1)

    def test_multiply(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.create_var(x)
        m.y = aml.create_var(y)

        expr = m.x * m.y
        self.assertAlmostEqual(expr.evaluate(), x * y, 10)
        self.assertEqual(expr.ad(m.x), y)
        self.assertEqual(expr.ad(m.y), x)

    def test_divide(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.create_var(x)
        m.y = aml.create_var(y)

        expr = m.x / m.y
        self.assertAlmostEqual(expr.evaluate(), x / y, 10)
        self.assertAlmostEqual(expr.ad(m.x), 1/y, 10)
        self.assertAlmostEqual(expr.ad(m.y), -x/y**2, 10)

    def test_power(self):
        m = aml.Model()
        x = 2.5
        y = -3.7
        m.x = aml.create_var(x)
        m.y = aml.create_var(y)

        expr = m.x**(m.y)
        self.assertAlmostEqual(expr.evaluate(), x ** y, 10)
        self.assertAlmostEqual(expr.ad(m.x), y*x**(y-1), 10)
        self.assertAlmostEqual(expr.ad(m.y), x**y * np.log(x), 10)

    @unittest.skip('exp is not implemented yet')
    def test_exp(self):
        m = aml.Model()
        x = 2.5
        m.x = aml.create_var(x)

        expr = aml.exp(m.x)
        self.assertAlmostEqual(aml.value(expr), np.exp(x), 10)
        self.assertAlmostEqual(aml.value(expr.ad(m.x)), np.exp(x), 10)

    @unittest.skip('log is not implemented yet')
    def test_log(self):
        m = aml.Model()
        x = 2.5
        m.x = aml.create_var(x)

        expr = aml.log(m.x)
        self.assertAlmostEqual(aml.value(expr), np.log(x), 10)
        self.assertAlmostEqual(aml.value(expr.ad(m.x)), 1/x, 10)

    @unittest.skip('exp is not implemented yet')
    def test_chain_rule(self):
        m = aml.Model()
        x = 1.1
        m.x = aml.create_var(x)

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
        m.x = aml.create_var(x)
        m.y = aml.create_var(y)
        m.c = aml.create_param(c)

        m.con1 = aml.create_constraint(m.x + m.y + m.c)
        m.con2 = aml.create_constraint(m.x**2 - m.y**2 + 10)

        vec = m.get_x()
        r = m.evaluate_residuals(vec)
        j = m.evaluate_jacobian().toarray()
        true_j = [[1,1],[2*x,-2*y]]
        self.assertTrue(np.all(r == [x+y+c, x**2-y**2+10]))
        self.assertTrue(np.all(j == true_j))

        del m.con2
        m.con3 = aml.create_constraint(m.x*m.y)
        r = m.evaluate_residuals(vec)
        j = m.evaluate_jacobian().toarray()
        true_j = [[1, 1], [y, x]]
        self.assertTrue(np.all(r == [x+y+c, x*y]))
        self.assertTrue(np.all(j == true_j))

    def test_if_then_constraints(self):
        m = aml.Model()
        x = -4.5
        y = -3.7
        m.x = aml.create_var(x)
        m.y = aml.create_var(y)

        con1 = aml.create_conditional_constraint()
        con1.add_condition(m.x + 1, -(-m.x)**1.852 - (-m.x)**2 - m.y)
        con1.add_condition(m.x - 1, m.x)
        con1.add_final_expr(m.x**1.852 + m.x**2 - m.y)
        m.con1 = con1

        con2 = aml.create_conditional_constraint()
        con2.add_condition(m.y + 1, -(-m.y)**(1.852) - (-m.y)**(2) - m.x)
        con2.add_condition(m.y - 1, m.y)
        con2.add_final_expr(m.y**(1.852) + m.y**(2) - m.x)
        m.con2 = con2

        vec = m.get_x()
        r = m.evaluate_residuals(vec)
        j = m.evaluate_jacobian().toarray()
        true_r = [-(abs(x)**1.852 + abs(x)**2) - y, -(abs(y)**1.852 + abs(y)**2) - x]
        true_j = [[1.852*abs(x)**0.852 + 2*abs(x), -1],[-1, 1.852*abs(y)**0.852 + 2*abs(y)]]
        self.assertTrue(np.all(r==true_r))
        for i in range(len(true_j)):
            for k in range(len(true_j[i])):
                self.assertAlmostEqual(true_j[i][k], j[i,k], 10)

        x = 0.5
        y = 0.3
        vec[0] = x
        vec[1] = y
        r = m.evaluate_residuals(vec)
        j = m.evaluate_jacobian().toarray()
        true_r = [x, y]
        true_j = [[1, 0],[0, 1]]
        self.assertTrue(np.all(r==true_r))
        for i in range(len(true_j)):
            for k in range(len(true_j[i])):
                self.assertAlmostEqual(true_j[i][k], j[i,k], 10)

        x = 4.5
        y = 3.7
        vec[0] = x
        vec[1] = y
        r = m.evaluate_residuals(vec)
        j = m.evaluate_jacobian().toarray()
        true_r = [x**1.852 + x**2 - y, y**1.852 + y**2 - x]
        true_j = [[1.852*x**0.852 + 2*x, -1],[-1, 1.852*y**0.852 + 2*y]]
        self.assertTrue(np.all(r==true_r))
        for i in range(len(true_j)):
            for k in range(len(true_j[i])):
                self.assertAlmostEqual(true_j[i][k], j[i,k], 10)

        del m.con2
        con2 = aml.create_conditional_constraint()
        con2.add_condition(m.y + 1, -(-m.y)**(2.852) - (-m.y)**(3) - m.x)
        con2.add_condition(m.y - 1, m.y**(2))
        con2.add_final_expr(m.y**(2.852) + m.y**(3) - m.x)
        m.con2 = con2

        vec = m.get_x()
        x = -4.5
        y = -3.7
        vec[0] = x
        vec[1] = y
        r = m.evaluate_residuals(vec)
        j = m.evaluate_jacobian().toarray()
        true_r = [-(abs(x)**1.852 + abs(x)**2) - y, -(abs(y)**2.852 + abs(y)**3) - x]
        true_j = [[1.852*abs(x)**0.852 + 2*abs(x), -1],[-1, 2.852*abs(y)**1.852 + 3*abs(y)**2]]
        self.assertTrue(np.all(r==true_r))
        for i in range(len(true_j)):
            for k in range(len(true_j[i])):
                self.assertAlmostEqual(true_j[i][k], j[i,k], 10)

        x = 0.5
        y = 0.3
        vec[0] = x
        vec[1] = y
        r = m.evaluate_residuals(vec)
        j = m.evaluate_jacobian().toarray()
        true_r = [x, y**2]
        true_j = [[1, 0],[0, 2*y]]
        self.assertTrue(np.all(r==true_r))
        for i in range(len(true_j)):
            for k in range(len(true_j[i])):
                self.assertAlmostEqual(true_j[i][k], j[i,k], 10)

        x = 4.5
        y = 3.7
        vec[0] = x
        vec[1] = y
        r = m.evaluate_residuals(vec)
        j = m.evaluate_jacobian().toarray()
        true_r = [x**1.852 + x**2 - y, y**2.852 + y**3 - x]
        true_j = [[1.852*x**0.852 + 2*x, -1],[-1, 2.852*y**1.852 + 3*y**2]]
        self.assertTrue(np.all(r==true_r))
        for i in range(len(true_j)):
            for k in range(len(true_j[i])):
                self.assertAlmostEqual(true_j[i][k], j[i,k], 10)


class TestCSRJacobian(unittest.TestCase):
    def test_register_and_remove_constraint(self):
        x = aml.create_var(2.0)
        y = aml.create_var(3.0)
        z = aml.create_var(4.0)
        v = aml.create_var(10.0)
        x.index = 0
        y.index = 1
        z.index = 2
        v.index = 3
        c1 = aml.create_constraint(x + y)
        c1.index = 0
        c2 = aml.create_constraint(x * y * v)
        c2.index = 1
        c3 = aml.create_constraint(z**3.0)
        c3.index = 2
        c4 = aml.create_constraint(x + 1.0 / v)
        c4.index = 3
        cons = [c1, c2, c3, c4]
        j = aml.CSRJacobian()
        j.add_constraint(c1)
        j.add_constraint(c2)
        j.add_constraint(c3)
        j.add_constraint(c4)
        con_values = [con.evaluate() for con in cons]
        j_values = j.evaluate(len(j.cons))
        A = csr_matrix((j_values, j.get_col_ndx(), j.get_row_nnz()), shape=(4, 4))

        true_con_values = [5.0, 60.0, 64.0, 2.1]
        self.assertTrue(np.all(np.array(true_con_values) == np.array(con_values)))
        true_jac = np.array([[1.0, 1.0, 0.0, 0.0],
                             [30.0, 20.0, 0.0, 6.0],
                             [0.0, 0.0, 48.0, 0.0],
                             [1.0, 0.0, 0.0, -0.01]])
        self.assertTrue(np.all(true_jac == A.toarray()))

        cons.remove(c3)
        j.remove_constraint(c3)
        c3 = aml.create_constraint(z)
        cons.append(c3)
        j.add_constraint(c3)
        con_values = [con.evaluate() for con in cons]
        true_con_values = [5.0, 60.0, 2.1, 4.0]
        self.assertTrue(np.all(np.array(true_con_values) == np.array(con_values)))
        j_values = j.evaluate(len(j.cons))
        A = csr_matrix((j_values, j.get_col_ndx(), j.get_row_nnz()), shape=(4, 4))
        true_jac = np.array([[1.0, 1.0, 0.0, 0.0],
                             [30.0, 20.0, 0.0, 6.0],
                             [1.0, 0.0, 0.0, -0.01],
                             [0.0, 0.0, 1.0, 0.0]])
        self.assertTrue(np.all(true_jac == A.toarray()))
