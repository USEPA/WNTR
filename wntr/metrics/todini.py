import wntr.network
import numpy as np
import pandas as pd

def todini(node_results, link_results, wn, Pstar):
    """
    Compute Todini index, equations from [1].
    
    The Todini index is related to the capability of a system to overcome 
    failures while still meeting demands and pressures at the nodes. The 
    Todini index defines resilience at a specific time as a measure of surplus 
    power at each node and measures relative energy redundancy. 

    Parameters
    ----------
    node_results : pd.Panel
        A pandas Panel containing node results. 
        Items axis = attributes, Major axis = times, Minor axis = node names
        todini index uses 'head', 'pressure', and 'demand' attrbutes.
        
    link_results : pd.Panel
        A pandas Panel containing link results. 
        Items axis = attributes, Major axis = times, Minor axis = link names
        todini index uses the 'flowrate' attrbute.
        
    wn : Water Network Model
        A water network model.  The water network model is needed to find the start and end node to each pump.
        
    Pstar : float
        Pressure threshold.
        
    Returns
    -------
    todini_index : pd.Series
        Time-series of Todini indexes

    Examples
    --------
    The following example computes the Todini index using a pressure threshold of 21.09 m (30 psi).
    
    >>> inp_file = 'networks/Net3.inp'
    >>> wn = wntr.network.WaterNetworkModel(inp_file)
    >>> sim = wntr.sim.EpanetSimulator(wn)
    >>> results = sim.run_sim()
    >>> todini = wntr.metrics.todini(results,wn,21.09)
    >>> todini.plot()
    
    References
    -----------
    [1] Todini E. (2000). Looped water distribution networks design using a 
    resilience index based heuristic approach. Urban Water, 2(2), 115-122.
    """
    
    POut = {}
    PExp = {}
    PInRes = {}
    PInPump = {}
     
    for name, node in wn.nodes(wntr.network.Junction):
        h = np.array(node_results.loc['head',:,name]) # m
        p = np.array(node_results.loc['pressure',:,name])
        e = h - p # m
        q = np.array(node_results.loc['demand',:,name]) # m3/s
        POut[name] = q*h
        PExp[name] = q*(Pstar+e)
    
    for name, node in wn.nodes(wntr.network.Reservoir):
        H = np.array(node_results.loc['head',:,name]) # m
        Q = np.array(node_results.loc['demand',:,name]) # m3/s
        PInRes[name] = -Q*H # switch sign on Q.
    
    for name, link in wn.links(wntr.network.Pump):
        start_node = link._start_node_name
        end_node = link._end_node_name
        h_start = np.array(node_results.loc['head',:,start_node]) # (m)
        h_end = np.array(node_results.loc['head',:,end_node]) # (m)
        h = h_start - h_end # (m) 
        q = np.array(link_results.loc['flowrate',:,name]) # (m^3/s)
        PInPump[name] = q*(abs(h)) # assumes that pumps always add energy to the system
    
    todini_index = (sum(POut.values()) - sum(PExp.values()))/  \
        (sum(PInRes.values()) + sum(PInPump.values()) - sum(PExp.values()))
    
    todini_index = pd.Series(data = todini_index.tolist(), index = node_results.major_axis)
    
    return todini_index