import numpy as np
import scipy.sparse as sp
import warnings
import logging
import enum

warnings.filterwarnings("error",'Matrix is exactly singular', sp.linalg.MatrixRankWarning)
np.set_printoptions(precision=3, threshold=10000, linewidth=300)

logger = logging.getLogger(__name__)


class SolverStatus(enum.IntEnum):
    converged = 1
    error = 0


class NewtonSolver(object):
    """
    Newton Solver class.
    """
    
    def __init__(self, options=None):
        if options is None:
            options = {}
        self._options = options

        if 'MAXITER' not in self._options:
            self.maxiter = 3000
        else:
            self.maxiter = self._options['MAXITER']

        if 'TOL' not in self._options:
            self.tol = 1e-6
        else:
            self.tol = self._options['TOL']

        if 'BT_RHO' not in self._options:
            self.rho = 0.5
        else:
            self.rho = self._options['BT_RHO']

        if 'BT_MAXITER' not in self._options:
            self.bt_maxiter = 100
        else:
            self.bt_maxiter = self._options['BT_MAXITER']

        if 'BACKTRACKING' not in self._options:
            self.bt = True
        else:
            self.bt = self._options['BACKTRACKING']

        if 'BT_START_ITER' not in self._options:
            self.bt_start_iter = 0
        else:
            self.bt_start_iter = self._options['BT_START_ITER']

        if 'THREADS' not in self._options:
            self.num_threads = 4
        else:
            self.num_threads = self._options['THREADS']

    def solve(self, model):
        """

        Parameters
        ----------
        model: wntr.aml.Model

        Returns
        -------
        status: SolverStatus
        message: str
        """
        logger_level = logger.getEffectiveLevel()

        x = model.get_x()
        if len(x) == 0:
            return SolverStatus.converged, 'No variables or constraints', 0

        use_r_ = False

        # MAIN NEWTON LOOP
        for outer_iter in range(self.maxiter):
            if use_r_:
                r = r_
                r_norm = new_norm
            else:
                r = model.evaluate_residuals(num_threads=self.num_threads)
                r_norm = np.max(abs(r))

            if logger_level <= 1:
                if outer_iter < self.bt_start_iter:
                    logger.log(1, 'iter: {0:<4d} norm: {1:<10.2e}'.format(outer_iter, r_norm))

            if r_norm < self.tol:
                return SolverStatus.converged, 'Solved Successfully', outer_iter

            J = model.evaluate_jacobian(x=None)

            # Call Linear solver
            try:
                d = -sp.linalg.spsolve(J, r, permc_spec='COLAMD', use_umfpack=False)
            except sp.linalg.MatrixRankWarning:
                return SolverStatus.error, 'Jacobian is singular at iteration ' + str(outer_iter), outer_iter

            # Backtracking
            alpha = 1.0
            if self.bt and outer_iter >= self.bt_start_iter:
                use_r_ = True
                for iter_bt in range(self.bt_maxiter):
                    x_ = x + alpha*d
                    model.load_var_values_from_x(x_)
                    r_ = model.evaluate_residuals(num_threads=self.num_threads)
                    new_norm = np.max(abs(r_))
                    if new_norm < (1.0-0.0001*alpha)*r_norm:
                        x = x_
                        break
                    else:
                        alpha = alpha*self.rho

                if iter_bt+1 >= self.bt_maxiter:
                    return SolverStatus.error, 'Line search failed at iteration ' + str(outer_iter), outer_iter
                if logger_level <= 1:
                    logger.log(1, 'iter: {0:<4d} norm: {1:<10.2e} alpha: {2:<10.2e}'.format(outer_iter, new_norm, alpha))
            else:
                x += d
                model.load_var_values_from_x(x)
            
        return SolverStatus.error, 'Reached maximum number of iterations: ' + str(outer_iter), outer_iter



