import networkx as nx
from epanetlib.network.network_topography import all_simple_paths
import math
import numpy as np
from collections import Counter

def entropy(G, sink = None):
    
    if G.is_directed() == False:
        return
    
    sources = [key for key,value in nx.get_node_attributes(G,'type').items() if value == 'reservoir' ]
    
    if sink is None:
        sink = G.nodes()
        
    S = {}  
    Q = {}
    for nodej in sink:
        if nodej in sources:
            S[nodej] = 0 # nodej is the source
            continue 
        
        sp = [] # simple path
        if G.node[nodej]['type']  == 'junction':
            for source in sources:
                if nx.has_path(G, source, nodej):
                    simple_paths = all_simple_paths(G,source,target=nodej)
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
    for nodej in sink:
        if not np.isnan(S[nodej]):
            if nodej not in sources:
                if Q[nodej]/Q0 > 0:
                    Shat = Shat + \
                        (Q[nodej]*S[nodej])/Q0 - \
                        Q[nodej]/Q0*math.log(Q[nodej]/Q0)
        
    return [S, Shat, sp, dk] 
