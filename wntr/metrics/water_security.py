"""
The wntr.metrics.water_security module contains water security metrics.
"""
import numpy as np
import wntr.network
import pandas as pd
import logging

logger = logging.getLogger(__name__)

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
    deltaT = node_results['quality'].index[1] # this assumes constant timedelta
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
    deltaT = node_results['quality'].index[1] # this assumes constant timedelta
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
    -----------
    [1] EPA, U. S. (2015). Water security toolkit user manual version 1.3. 
    Technical report, U.S. Environmental Protection Agency
    """
    flow_rate = link_results['flowrate']
    pipe_names = wn.pipe_name_list
    node_quality = node_results['quality']
    link_length = []
    link_start_node = []
    link_end_node = []
    for name in pipe_names:
        link = wn.get_link(name)
        link_start_node.append(link.start_node)
        link_end_node.append(link.end_node)
        link_length.append(link.length)
    link_start_node = pd.Series(index=pipe_names, data=link_start_node)
    link_end_node = pd.Series(index=pipe_names, data=link_end_node)
    link_length = pd.Series(index=pipe_names, data=link_length)
    
    flow_dir = np.sign(flow_rate.loc[:,pipe_names])
    node_contam = node_quality > detection_limit
    pos_flow = np.array(node_contam.loc[:,link_start_node])
    neg_flow = np.array(node_contam.loc[:,link_end_node])
    link_contam = ((flow_dir>0)&pos_flow) | ((flow_dir<0)&neg_flow)
    contam_len = (link_contam * link_length).cummax()
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
