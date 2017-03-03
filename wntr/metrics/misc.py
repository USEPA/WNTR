"""
The wntr.metrics.misc module contains metrics that do not fall into the 
topographic, hydraulic, water quality, water security, or economic categories.
"""
from wntr.network import Junction
import pandas as pd
import numpy as np
import sys
import logging

if sys.version_info >= (3,0):
    from functools import reduce
    
logger = logging.getLogger(__name__)

def query(arg1, operation, arg2):
    """
    Return a boolean mask using comparison operators, i.e. "arg1 operation arg2". 
    For example, find the node-time pairs when demand < 90% expected demand.
    
    Parameters
    ----------- 
    arg1 : pd.Panel, pd.DataFrame, pd.Series, np.array, list, scalar
        Argument 1

    operation : numpy.ufunc
        Numpy universal comparison function, options = np.greater, 
        np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal

    arg2 : same size and type as arg1, or a scalar
        Argument 2
        
    Returns
    -------
    mask : same size and type as arg1
        contains bool
        
    Examples
    ---------
    >>> wntr.metrics.query(1, np.greater, 2)
    False
    >>> wntr.metrics.query([1,2,3], np.not_equal, [5,2,1])
    array([ True, False,  True], dtype=bool)
    >>> wntr.metrics.query(results.node['demand'], np.less_equal, 0.9*results.node['expected_demand'])
    """
    try:
        mask = operation(arg1, arg2)
    except AttributeError:
        logger.error('operation(arg1, arg2) failed')
    
    return mask
    
def average_water_consumed(wn):
    """
    Compute average water consumed at each node, qbar, computed as follows:
    
    .. math:: qbar=\dfrac{\sum_{k=1}^{K}\sum_{t=1}^{lcm_n}qbase_n m_n(k,t mod (L(k)))}{lcm_n}
    
    where 
    :math:`K` is the number of demand patterns at node :math:`n`,
    :math:`L(k)` is the number of time steps in pattern :math:`k`,
    :math:`lcm_n` is the least common multiple of the demand patterns time steps for node :math:`n`, 
    :math:`qbase_n` is the base demand at node :math:`n` and 
    :math:`m_n(k,t mod L(k))` is the demand multiplier specified in pattern :math:`k` for node :math:`n` at time :math:`t mod L(k)`. 
        
    For example, if a node has two demand patterns specified in the EPANET input (INP) file, and 
    one pattern repeats every 6 hours and the other repeats every 12 hours, the first 
    pattern will be repeated once, making its total duration effectively 12 hours. 
    If any :math:`m_n(k,t mod L(k))` value is less than 0, then that node's population is 0.  
    
    Parameters
    -----------
    wn : WaterNetworkModel
    
    Returns
    -------
    qbar : pd.Series
        A pandas Series that contains average water consumed per node, in m3/s
        
    """
    qbar = pd.Series()
    for name, node in wn.nodes(Junction):
        # Future release should support mutliple base demand and demand patterns per node
        numdemands = 1
        
        L = {}
        pattern = {}
        for i in range(numdemands):
            pattern_name = node.demand_pattern_name
            if not pattern_name:
                pattern_name = wn.options.pattern
            pattern[i] = wn.get_pattern(pattern_name)
            L[i] = len(pattern[i])
        lcm_n = _lcml(L.values())
        
        qbar_n = 0
        for i in range(numdemands):    
            base_demand = node.base_demand
            for t in range(lcm_n):
                m = pattern[i][np.mod(t,len(pattern[i]))]
                qbar_n = qbar_n + base_demand*m/lcm_n
        qbar[name] = qbar_n    
           
    return qbar

def _gcd(x,y):
  while y:
    if y<0:
      x,y=-x,-y
    x,y=y,x % y
    return x

def _gcdl(*list):
  return reduce(_gcd, *list)

def _lcm(x,y):
  return x*y / _gcd(x,y)

def _lcml(*list):
  return reduce(_lcm, *list)

def population(wn, R=0.00000876157):
    """
    Compute population per node, rounded to the nearest integer, equation from [1]
    
    .. math:: pop=\dfrac{qbar}{R}
    
    Parameters
    -----------
    wn : WaterNetworkModel
    
    R : float (optional, default = 0.00000876157 m3/s = 200 gallons/day)
        Average volume of water consumed per capita per day in m3/s
        
    Returns
    -------
    pop : pd.Series
        A pandas Series that contains population per node
        
    References
    ----------
    [1] EPA, U. S. (2015). Water security toolkit user manual version 1.3. 
    Technical report, U.S. Environmental Protection Agency
    """
    qbar = average_water_consumed(wn)
    pop = qbar/R
    
    return pop.round()


def population_impacted(pop, arg1, operation=None, arg2=None):
    """
    Compute population impacted using using comparison operators.
    For example, find the population impacted when demand < 90% expected.
    
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
        
    Examples
    ---------
    >>> temp = pd.Series(data = np.random.rand(len(nzd_junctions)), index=nzd_junctions)
    >>> pop_impacted1 = wntr.metrics.population_impacted(pop, temp, np.greater, 0.5)
    >>> pop_impacted2 = wntr.metrics.population_impacted(pop, fdd, np.less, 1)
    """
    mask = query(arg1, operation, arg2)
    pop_impacted = mask.multiply(pop)
    
    return pop_impacted
