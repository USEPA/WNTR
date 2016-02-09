import numpy as np
import scipy.sparse as sp
import copy
import time
import warnings

warnings.filterwarnings("error",'Matrix is exactly singular',sp.linalg.MatrixRankWarning)

class NewtonSolver(object):
    def __init__(self, options={}):
        self._options = options
        self._total_linear_solver_time = 0

        if 'MAXITER' not in self._options:
            self.maxiter = 100
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
            self.bt_maxiter = 50
        else:
            self.bt_maxiter = self._options['BT_MAXITER']

        if 'BACKTRACKING' not in self._options:
            self.bt = True
        else:
            self.bt = self._options['BACKTRACKING']


    def solve(self, Residual, Jacobian, x0):

        x = copy.copy(x0)

        num_vars = len(x)

        I = sp.csr_matrix((np.ones(num_vars),(range(num_vars),range(num_vars))),shape=(num_vars,num_vars))
        I = 10*I
        use_r_ = False

        # MAIN NEWTON LOOP
        for iter in xrange(self.maxiter):
            if use_r_:
                r = r_
                r_norm = lhs
            else:
                r = Residual(x)
                r_norm = np.max(abs(r))

            J = Jacobian(x)

            #print iter, r_norm

            if r_norm < self.tol:
                return [x, iter, 1]
            
            # Call Linear solver
            #t0 = time.time()
            try:
                d = -sp.linalg.spsolve(J,r)
            except sp.linalg.MatrixRankWarning:
                print 'Jacobian is singular. Adding regularization term.'
                J = J+I
                d = -sp.linalg.spsolve(J,r)
            #d = -np.linalg.solve(J, r)
            #self._total_linear_solver_time += time.time() - t0

            # Backtracking
            alpha = 1.0
            if self.bt and iter>=10:
                use_r_ = True
                for iter_bt in xrange(self.bt_maxiter):
                    #print alpha
                    x_ = x + alpha*d
                    r_ = Residual(x_)
                    if iter_bt > 0:
                        last_lhs = lhs
                        lhs = np.max(abs(r_))
                    else:
                        lhs = np.max(abs(r_))
                        last_lhs = lhs + 1.0
                    #rhs = np.max(r + self.bt_c*alpha*J*d)
                    rhs = r_norm
                    #print "     ", iter, iter_bt, alpha
                    if lhs <= 0.95*rhs or lhs>last_lhs:
                        x = x_
                        break
                    else:
                        alpha = alpha*self.rho

                if iter_bt+1 >= self.bt_maxiter:
                    raise RuntimeError("Backtracking failed. ")
            else:
                x = x + d
            #print 'alpha = ',alpha

        return [x, iter, 0]
        #raise RuntimeError("No solution found.")



