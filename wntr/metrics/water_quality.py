from wntr.metrics.hydraulic import _average_attribute
import logging

logger = logging.getLogger(__name__)

def fdq(node_results, Qstar, average_times=False, average_nodes=False):
    """
    Compute fraction delivered quality (FDQ), equations modified from [1]. 
    The metric can be averaged over times and/or nodes.
    
    Parameters
    ----------
    node_results : pd.Panel
        A pandas Panel containing node results. 
        Items axis = attributes, Major axis = times, Minor axis = node names
        FDQ uses 'quality' attrbute.
        
    Qstar : float
        Water quality threshold.
        
    average_times : bool (default = False)
        Flag to determine if calculations are to be averaged over each time
        step. If false, FDV calculations will be performed for each time step.
        If true, FDV calculations will be averaged over all time steps.
    
    average_nodes : bool (default = False)
        Flag to determine if calculations are to be averaged over each node. 
        If false, FDV calculations will be performed for each node. If true, FDV
        calculations will be averaged over all nodes.

    Returns 
    -------    
    fdq : pd.DataFrame, pd.Series, or scalar (depending on node and time averaging)
        Fraction of delivered quality
        
    References
    ----------
    [1] Ostfeld A, Kogan D, Shamir U. (2002). Reliability simulation of water
    distribution systems - single and multiquality, Urban Water, 4, 53-61
    """

    quality = _average_attribute(node_results['quality'], average_times, average_nodes)
    
    fdq = (quality >= Qstar)+0 
            
    return fdq

