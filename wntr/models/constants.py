import logging
from wntr.utils.polynomial_interpolation import cubic_spline

logger = logging.getLogger(__name__)


def hazen_williams_params(m):
    m.hw_k = 10.666829500036352
    m.hw_exp = 1.852
    m.hw_minor_exp = 2

    m.hw_q1 = 0.0002
    m.hw_q2 = 0.0004
    m.hw_m = 0.001

    x1 = m.hw_q1
    x2 = m.hw_q2
    f1 = m.hw_m * m.hw_q1
    f2 = m.hw_q2 ** m.hw_exp
    df1 = m.hw_m
    df2 = m.hw_exp * m.hw_q2 ** (m.hw_exp - 1)
    a, b, c, d = cubic_spline(x1, x2, f1, f2, df1, df2)
    m.hw_a = a
    m.hw_b = b
    m.hw_c = c
    m.hw_d = d


