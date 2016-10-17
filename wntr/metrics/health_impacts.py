import numpy as np
import wntr.network
import pandas as pd
import logging

logger = logging.getLogger('wntr.metrics.health_impacts')

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
    for name, node in wn.nodes(wntr.network.Junction):
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
    mask = wntr.metrics.query(arg1, operation, arg2)
    pop_impacted = mask.multiply(pop)
    
    return pop_impacted

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

def mass_contaminant_consumed(node_results):
    """ Mass of contaminant consumed, equation from [1].
    
    Parameters
    ----------
    node_results : pd.Panel
        A pandas Panel containing node results. 
        Items axis = attributes, Major axis = times, Minor axis = node names
        Mass of contaminant consumed uses 'demand' and quality' attrbutes.
    
     References
    ----------
    [1] EPA, U. S. (2015). Water security toolkit user manual version 1.3. 
    Technical report, U.S. Environmental Protection Agency
    """
    maskD = np.greater(node_results['demand'], 0) # positive demand
    deltaT = node_results.major_axis[1] # this assumes constant timedelta
    MC = node_results['demand']*deltaT*node_results['quality']*maskD # m3/s * s * kg/m3 - > kg
    
    return MC
     
def volume_contaminant_consumed(node_results, detection_limit):
    """ Volume of contaminant consumed, equation from [1].
    
    Parameters
    ----------
    node_results : pd.Panel
        A pandas Panel containing node results. 
        Items axis = attributes, Major axis = times, Minor axis = node names
        Volume of contaminant consumed uses 'demand' and quality' attrbutes.
    
    detection_limit : float
        Contaminant detection limit
    
     References
    ----------
    [1] EPA, U. S. (2015). Water security toolkit user manual version 1.3. 
    Technical report, U.S. Environmental Protection Agency
    """
    maskQ = np.greater(node_results['quality'], detection_limit)
    maskD = np.greater(node_results['demand'], 0) # positive demand
    deltaT = node_results.major_axis[1] # this assumes constant timedelta
    VC = node_results['demand']*deltaT*maskQ*maskD # m3/s * s * bool - > m3
    
    return VC
    
def extent_contaminant(node_results, link_results, wn, detection_limit):
    """ Extent of contaminant in the pipes, equation from [1].
    
    Parameters
    ----------
    node_results : pd.Panel
        A pandas Panel containing node results. 
        Items axis = attributes, Major axis = times, Minor axis = node names
        Extent of contamination uses the 'quality' attribute.
    
    link_results : pd.Panel
        
    detection_limit : float
        Contaminant detection limit.
    
    Returns
    -------
    EC : pd.Series
        Extent of contaminantion (m)
    
     References
    ----------
    [1] EPA, U. S. (2015). Water security toolkit user manual version 1.3. 
    Technical report, U.S. Environmental Protection Agency
    """
    G = wn.get_graph_deep_copy()
    EC = pd.DataFrame(index = node_results.major_axis, columns = node_results.minor_axis, data = 0)
    L = pd.DataFrame(index = node_results.major_axis, columns = node_results.minor_axis, data = 0)

    for t in node_results.major_axis:
        # Weight the graph
        attr = link_results.loc['flowrate', t, :]   
        G.weight_graph(link_attribute=attr)  
        
        # Compute pipe_length associated with each node at time t
        for node_name in G.nodes():
            for downstream_node in G.successors(node_name):
                for link_name in G[node_name][downstream_node].keys():
                    link = wn.get_link(link_name)
                    if isinstance(link, wntr.network.Pipe):
                        L.loc[t,node_name] = L.loc[t,node_name] + link.length
                    
    mask = np.greater(node_results['quality'], detection_limit)
    EC = L*mask
        
    #total_length = [link.length for link_name, link in wn.links(wntr.network.Pipe)]
    #sum(total_length)
    #L.sum(axis=1)
        
    return EC
    
#def cumulative_dose():
#    """
#    Compute cumulative dose for person p at node n at time step t
#    """
#    d_npt = 0
#    return d_npt
#
#def ingestion_model_timing(node_results, method='D24'):
#    """
#    Compute volume of water ingested for each node and timestep, equations from [1]
#   
#    Parameters
#    -----------
#    wn : WaterNetworkModel
#    
#    method : string
#        Options = D24, F5, and P5
#        
#    Returns
#    -------
#    Vnpt : pd.Series
#        A pandas Series that contains the volume of water ingested for each node and timestep
#        
#    References
#    ----------
#    [1] EPA, U. S. (2015). Water security toolkit user manual version 1.3. 
#    Technical report, U.S. Environmental Protection Agency
#    """
#    if method == 'D24':
#        Vnpt = 1
#    elif method == 'F5':
#        Vnpt = 1
#    elif method == 'P5':
#        Vnpt = 1
#    else:
#        logger.warning('Invalid ingestion timing model')
#        return
#    
#    return Vnpt
#    
#def ingestion_model_volume(method ='M'):
#    """
#    Compute per capita ingestion volume in m3/s for each person p at node n.
#    """
#    
#    if method == 'M':
#        Vnp = 1
#    elif method == 'P':
#        Vnp = 1 # draw from a distribution, for each person at each node
#    else:
#        logger.warning('Invalid ingestion volume model')
#        return
#
#    return Vnp
#  
#def population_dosed(node_results):
#    PD = 0
#    return PD
#
#def population_exposed(node_results):
#    PE = 0
#    return PE
#
#def population_killed(node_results):
#    PK = 0
#    return PK
