import numpy as np
import scipy.sparse as sp
import copy

class NewtonSolver(object):
    def __init__(self, options={}):
        self._options = options

    def solve(self, Residual, Jacobian, x0, args):

        x = copy.copy(x0)

        num_vars = len(x)

        if 'MAXITER' not in self._options:
            maxiter = 1000
        else:
            maxiter = self._options['MAXITER']

        if 'TOL' not in self._options:
            tol = 1e-6
        else:
            tol = self._options['TOL']

        if 'BT_C' not in self._options:
            bt_c = 0.0001
        else:
            bt_c = self._options['BT_C']

        if 'BT_RHO' not in self._options:
            rho = 0.5
        else:
            rho = self._options['BT_C']

        if 'BT_MAXITER' not in self._options:
            bt_maxiter = 100
        else:
            bt_maxiter = self._options['BT_MAXITER']

        if 'BACKTRACKING' not in self._options:
            bt = False
        else:
            bt = self._options['BACKTRACKING']


        for iter in xrange(maxiter):
            r = Residual(x, args)
            J = Jacobian(x, args)
            #J = Jfunc(x)

            r_norm = np.max(r)

            #print iter, r_norm

            if r_norm < tol:
                return [x, iter]

            d = -sp.linalg.spsolve(J,r)
            #d = -np.linalg.solve(J, r)


            # Backtracking
            alpha = 1
            if bt:
                for iter_bt in xrange(bt_maxiter):
                    x_ = x + alpha*d
                    lhs = np.max(Residual(x_, args))
                    #rhs = np.max(r + bt_c*alpha*J*d)
                    rhs = r_norm
                    #print "     ", iter, iter_bt, alpha
                    if lhs < rhs:
                        x = x_
                        break
                    else:
                        alpha = alpha*rho

                if iter_bt+1 >= bt_maxiter:
                    raise RuntimeError("Backtracking failed. ")
            else:
                x = x + d

        raise RuntimeError("No solution found.")



