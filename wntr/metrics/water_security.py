import numpy as np
import wntr.network
import pandas as pd
import sys
import logging

logger = logging.getLogger(__name__)

if sys.version_info >= (3,0):
    from functools import reduce

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
