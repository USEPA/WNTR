"""
The wntr.metrics.misc module contains metrics that do not fall into the
topographic, hydraulic, water quality, water security, or economic categories.

.. rubric:: Contents

.. autosummary::

    query
    population
    population_impacted

"""
from wntr.network import Junction
from wntr.metrics.hydraulic import expected_demand
import pandas as pd
import numpy as np
import sys
import logging

if sys.version_info >= (3,0):
    from functools import reduce

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
    """
    Compute population per node, rounded to the nearest integer [USEPA15]_.

    .. math:: pop=\dfrac{expected_demand}{R}

    Parameters
    -----------
    wn : wntr WaterNetworkModel

    R : float (optional, default = 0.00000876157 m3/s = 200 gallons/day)
        Average volume of water consumed per capita per day in m3/s

    Returns
    -------
    A pandas Series that contains population per node
    """

    ex_dem = expected_demand(wn)
    pop = ex_dem.mean(axis=0)/R

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
