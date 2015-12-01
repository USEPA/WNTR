import logging

logger = logging.getLogger('wntr.metrics.query')

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
    