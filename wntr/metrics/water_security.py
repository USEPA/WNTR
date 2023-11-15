"""
The wntr.metrics.water_security module contains water security metrics.
"""
import numpy as np
import wntr.network
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def mass_contaminant_consumed(demand, quality, detection_limit=0):
    """ Mass of contaminant consumed :cite:p:`usepa15`.
    
    Parameters
    ----------
    demand : pandas DataFrame
        A pandas DataFrame containing junction demand
        (index = times, columns = junction names).
    
    quality : pandas DataFrame
        A pandas DataFrame containing junctions water quality
        (index = times, columns = junction names).
    
    detection_limit : float
        Contaminant detection limit.
        
    Returns
    --------
    A pandas DataFrame containing mass consumed
    """
    
    maskQ = np.greater(quality, detection_limit)
    maskD = np.greater(demand, 0) # positive demand
    deltaT = quality.index[1] # this assumes constant timedelta
    MC = demand*deltaT*quality[maskQ]*maskD # m3/s * s * kg/m3 - > kg
    
    return MC

def volume_contaminant_consumed(demand, quality, detection_limit=0):
    """ Volume of contaminant consumed :cite:p:`usepa15`.
    
    Parameters
    ----------
    demand : pandas DataFrame
        A pandas DataFrame containing junctions demand
        (index = times, columns = junction names).
    
    quality : pandas DataFrame
        A pandas DataFrame containing junctions water quality
        (index = times, columns = junction names).
    
    detection_limit : float
        Contaminant detection limit
    
    Returns
    --------
    A pandas DataFrame containing volume consumed
    """
    
    maskQ = np.greater(quality, detection_limit)
    maskD = np.greater(demand, 0) # positive demand
    deltaT = quality.index[1] # this assumes constant timedelta
    VC = demand*deltaT*maskQ*maskD # m3/s * s * bool - > m3
    
    return VC

def extent_contaminant(quality, flowrate, wn, detection_limit=0):
    """ 
    Extent of contaminant in the pipes :cite:p:`usepa15`.
    
    Parameters
    ----------
    quality : pandas DataFrame
        A pandas DataFrame containing node water quality
        (index = times, columns = node names).
    
    flowrate : pandas DataFrame
        A pandas DataFrame containing pipe flowrate
        (index = times, columns = pipe names).
        
    wn : wntr WaterNetworkModel
        Water network model.  The water network model is needed to 
        get pipe length, and pipe start and end node.
        
    detection_limit : float
        Contaminant detection limit.
    
    Returns
    -------
    A pandas Series with extent of contamination (m)
    """
    pipe_names = wn.pipe_name_list
    link_length = []
    link_start_node = []
    link_end_node = []
    for name in pipe_names:
        link = wn.get_link(name)
        link_start_node.append(link.start_node_name)
        link_end_node.append(link.end_node_name)
        link_length.append(link.length)
    link_start_node = pd.Series(index=pipe_names, data=link_start_node)
    link_end_node = pd.Series(index=pipe_names, data=link_end_node)
    link_length = pd.Series(index=pipe_names, data=link_length)
    
    # flow_dir, pos_flow, neg_flow, link_contam are indexed by pipe names (col) 
    # and times (rows)
    flow_dir = np.sign(flowrate.loc[:,pipe_names])
    node_contam = quality > detection_limit
    pos_flow = np.array(node_contam.loc[:,link_start_node])
    neg_flow = np.array(node_contam.loc[:,link_end_node])
    link_contam = ((flow_dir>0)&pos_flow) | ((flow_dir<0)&neg_flow)
    
    # contam_len is cummax over time (has the node ever been contaminated)
    contam_len = (link_contam * link_length).cummax()
    
    # EC is a time series with the sum across nodes
    EC = contam_len.sum(axis=1)
    
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
#    Compute volume of water ingested for each node and timestep
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
