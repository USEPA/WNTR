import networkx as nx
from wntr.network.WntrMultiDiGraph import _all_simple_paths
import math
import numpy as np
from collections import Counter

def entropy(G, sources=None, sinks=None):
    """ 
    Compute entropy, equations from [1].
    
    Entropy is a measure of uncertainty in a random variable.  
    In a water distribution network model, the random variable is 
    flow in the pipes and entropy can be used to measure alternate flow paths
    when a network component fails.  A network that carries maximum entropy 
    flow is considered reliable with multiple alternate paths.  

    Parameters
    ----------
    G : NetworkX or WNTR graph
        Entropy is computed using a directed graph based on pipe flow direction.  
        The 'weight' of each link is equal to the flow rate.
    
    sources : list of strings, optional (default = all reservoirs)
        List of node names to use as sources.
        
    sinks : list of strings, optional (default = all nodes)
        List of node names to use as sinks.
        
    Returns
    -------
    S : dict
        Node entropy, {node name: entropy value}
        
    Shat : float
        System entropy

    Examples
    --------
    The following example computes entropy using Net3 flow directions at time 3600 s.
    
    >>> inp_file = 'networks/Net3.inp'
    >>> wn = wntr.network.WaterNetworkModel(inp_file)
    >>> sim = wntr.sim.EpanetSimulator(wn)
    >>> results = sim.run_sim()
    >>> G = wn.get_graph_deep_copy()
    >>> attr = results.link.loc['flowrate', 3600, :]
    >>> G.weight_graph(link_attribute=attr) 
    >>> [S, Shat] = wntr.metrics.entropy(G)
    >>> wntr.network.draw_graph(wn, node_attribute = S, title = 'Node entropy")
    >>> Shat
    4.05
    
    References
    -----------
    [1] Awumah K, Goulter I, Bhatt SK. (1990). Assessment of reliability in 
    water distribution networks using entropy based measures. Stochastic 
    Hydrology and Hydraulics, 4(4), 309-320 
    """
    
    if G.is_directed() == False:
        return
    
    if sources is None:
        sources = [key for key,value in nx.get_node_attributes(G,'type').items() if value == 'reservoir' ]
    
    if sinks is None:
        sinks = G.nodes()
        
    S = {}  
    Q = {}
    for nodej in sinks:
        if nodej in sources:
            S[nodej] = 0 # nodej is the source
            continue 
        
        sp = [] # simple path
        if G.node[nodej]['type']  == 'junction':
            for source in sources:
                if nx.has_path(G, source, nodej):
                    simple_paths = _all_simple_paths(G,source,target=nodej)
                    sp = sp + ([p for p in simple_paths]) 
                    # all_simple_paths was modified to check 'has_path' in the
                    # loop, but this is still slow for large networks
                    # what if the network was skeletonized based on series pipes 
                    # that have the same flow direction?
                    # what about duplicating paths that have pipes in series?
                #print j, nodeid, len(sp)
        
        if len(sp) == 0:
            S[nodej] = np.nan # nodej is not connected to any sources
            continue 
           
        sp = np.array(sp)
        
        # Uj = set of nodes on the upstream ends of links incident on node j
        Uj = G.predecessors(nodej)
        # qij = flow in link from node i to node j
        qij = [] 
        # aij = number of equivalnet independent paths through the link from node i to node j
        aij = [] 
        for nodei in Uj:
            mask = np.array([nodei in path for path in sp])
            # NDij = number of paths through the link from node i to node j
            NDij = sum(mask) 
            if NDij == 0:
                continue  
            temp = sp[mask]
            # MDij = links in the NDij path
            MDij = [(t[idx],t[idx+1]) for t in temp for idx in range(len(t)-1)] 
        
            flow = 0
            for link in G[nodei][nodej].keys():
                flow = flow + G[nodei][nodej][link]['weight']
            qij.append(flow)
            
            # dk = degree of link k in MDij
            dk = Counter() 
            for elem in MDij:
                # divide by the numnber of links between two nodes
                dk[elem] += 1/len(G[elem[0]][elem[1]].keys()) 
            
            aij.append(NDij*(1-float(sum(np.array(dk.values()) - 1))/sum(dk.values())))
            
        Q[nodej] = sum(qij) # Total flow into node j
        
        # Equation 7
        S[nodej] = 0
        for idx in range(len(qij)):
            if qij[idx]/Q[nodej] > 0:
                S[nodej] = S[nodej] - \
                    qij[idx]/Q[nodej]*math.log(qij[idx]/Q[nodej]) + \
                    qij[idx]/Q[nodej]*math.log(aij[idx])
                    
    Q0 = sum(nx.get_edge_attributes(G, 'weight').values())   

    # Equation 3
    Shat = 0
    for nodej in sinks:
        if not np.isnan(S[nodej]):
            if nodej not in sources:
                if Q[nodej]/Q0 > 0:
                    Shat = Shat + \
                        (Q[nodej]*S[nodej])/Q0 - \
                        Q[nodej]/Q0*math.log(Q[nodej]/Q0)
        
    return [S, Shat] 
