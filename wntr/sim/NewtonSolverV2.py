import numpy as np
import scipy.sparse as sp
import copy
import time

class NewtonSolverV2(object):
    def __init__(self, options={}):
        self._options = options
        self._total_linear_solver_time = 0

        if 'MAXITER' not in self._options:
            self.maxiter = 1000
        else:
            self.maxiter = self._options['MAXITER']

        if 'TOL' not in self._options:
            self.tol = 1e-6
        else:
            self.tol = self._options['TOL']

        if 'BT_C' not in self._options:
            self.bt_c = 0.0001
        else:
            self.bt_c = self._options['BT_C']

        if 'BT_RHO' not in self._options:
            self.rho = 0.5
        else:
            self.rho = self._options['BT_C']

        if 'BT_MAXITER' not in self._options:
            self.bt_maxiter = 100
        else:
            self.bt_maxiter = self._options['BT_MAXITER']

        if 'BACKTRACKING' not in self._options:
            self.bt = False
        else:
            self.bt = self._options['BACKTRACKING']


    def solve(self, Residual, Jacobian, x0):

        x = copy.copy(x0)

        num_vars = len(x)

        # MAIN NEWTON LOOP
        for iter in xrange(self.maxiter):
            r = Residual(x)
            J = Jacobian(x)
            #J = Jfunc(x)

            r_norm = np.max(r)

            #print iter, r_norm

            if r_norm < self.tol:
                return [x, iter]
            
            # Call Linear solver
            t0 = time.time()
            d = -sp.linalg.spsolve(J,r)
            #d = -np.linalg.solve(J, r)
            self._total_linear_solver_time += time.time() - t0

            # Backtracking
            alpha = 1
            if self.bt:
                for iter_bt in xrange(self.bt_maxiter):
                    x_ = x + alpha*d
                    lhs = np.max(Residual(x_, args))
                    #rhs = np.max(r + self.bt_c*alpha*J*d)
                    rhs = r_norm
                    #print "     ", iter, iter_bt, alpha
                    if lhs < rhs:
                        x = x_
                        break
                    else:
                        alpha = alpha*self.rho

                if iter_bt+1 >= self.bt_self.maxiter:
                    raise RuntimeError("Backtracking failed. ")
            else:
                x = x + d

        raise RuntimeError("No solution found.")



