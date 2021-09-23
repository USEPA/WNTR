"""
The wntr.metrics.misc module contains metrics that do not fall into the
topographic, hydraulic, water quality, water security, or economic categories.

.. rubric:: Contents

.. autosummary::

    query
    population
    population_impacted

"""
from wntr.metrics.hydraulic import average_expected_demand
import logging

logger = logging.getLogger(__name__)

def query(arg1, operation, arg2):
    """
    Returns a boolean mask using comparison operators, i.e. "arg1 operation arg2".
    For example, this can be used to return the node-time pairs 
    when demand < 90% expected demand.

    Parameters
    -----------
    arg1 : pandas DataFrame, pandas Series, numpy array, list, scalar
        Argument 1

    operation : numpy ufunc
        Numpy universal comparison function, options = np.greater,
        np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

    arg2 : same size and type as arg1, or a scalar
        Argument 2

    Returns
    -------
    A boolean mask (same size and type as arg1)
    """
    try:
        mask = operation(arg1, arg2)
    except AttributeError:
        logger.error('operation(arg1, arg2) failed')

    return mask

def population(wn, R=0.00000876157):
    r"""
    Compute population per node, rounded to the nearest integer [USEPA15]_.

    .. math:: pop=\dfrac{Average\ expected\ demand}{R}

    Parameters
    -----------
    wn : wntr WaterNetworkModel
        Water network model. The water network model is needed to 
        get demand timeseries at junctions and options related to 
        duration, timestep, and demand multiplier.

    R : float (optional, default = 0.00000876157 m3/s = 200 gallons/day)
        Average volume of water consumed per capita per day in m3/s

    Returns
    -------
    A pandas Series that contains population per node
    """

    ave_ex_dem = average_expected_demand(wn)
    pop = ave_ex_dem/R

    return pop.round()


def population_impacted(pop, arg1, operation=None, arg2=None):
    """
    Computes population impacted using comparison operators.
    For example, this can be used to find the population impacted when 
    demand < 90% expected.

    Parameters
    -----------
    pop : pd.Series (index = node names)
         A pandas Series that contains population per node

    arg1 : pd.DataFrame (columns = node names) or pd.Series (index = node names)
        Argument 1

    operation : numpy.ufunc
        Numpy universal comparison function, options = np.greater,
        np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

    arg2 : same size and type as arg1, or a scalar
        Argument 2
        
    Returns
    --------
    A pandas Series that contains population impacted per node
    """
    mask = query(arg1, operation, arg2)
    pop_impacted = mask.multiply(pop)

    return pop_impacted
