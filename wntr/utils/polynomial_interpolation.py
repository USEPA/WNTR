"""Functions for a polynomial interpolation using cubic spline."""

def cubic_spline(x1, x2, f1, f2, df1, df2):
    """
    Method to compute the coefficients of a smoothing polynomial.

    Parameters
    ----------
    x1: float
        point on the x-axis at which the smoothing polynomial begins
    x2: float
        point on the x-axis at which the smoothing polynomial ens
    f1: float
        function evaluated at x1
    f2: float
        function evaluated at x2
    df1: float
        derivative evaluated at x1
    df2: float
        derivative evaluated at x2

    Returns
    -------
    A tuple with the smoothing polynomail coefficients starting with the cubic term.
    """
    a = (2 * (f1 - f2) - (x1 - x2) * (df2 + df1)) / (x2 ** 3 - x1 ** 3 + 3 * x1 * x2 * (x1 - x2))
    b = (df1 - df2 + 3 * (x2 ** 2 - x1 ** 2) * a) / (2 * (x1 - x2))
    c = df2 - 3 * x2 ** 2 * a - 2 * x2 * b
    d = f2 - x2 ** 3 * a - x2 ** 2 * b - x2 * c
    return a, b, c, d

