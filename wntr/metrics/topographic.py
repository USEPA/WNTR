"""
The wntr.metrics.topographic module contains topographic metrics that are not
available directly with NetworkX.  Functions in this module operate on a 
NetworkX MultiDiGraph, which can be created by calling ``G = wn.get_graph()``

.. rubric:: Contents

.. autosummary::

    terminal_nodes
    bridges
    central_point_dominance
    spectral_gap
    algebraic_connectivity
    critical_ratio_defrag

"""
import networkx as nx
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def terminal_nodes(G):
    """
    Nodes with degree 1

    Parameters
    ----------
    G : networkx MultiDiGraph
        Graph

    Returns
    -------
    List of terminal nodes
    
    """
    node_degree = dict(G.degree())
    terminal_nodes = [k for k,v in node_degree.items() if v == 1]

    return terminal_nodes

def bridges(G):
    """
    Bridge links

    Parameters
    ----------
    G : networkx MultiDiGraph
        Graph

    Returns
    -------
    List of links that are bridges
    
    """
    uG = G.to_undirected() # uses an undirected graph
    bridge_links = []
    bridges = nx.bridges(nx.Graph(uG)) # not implemented for multigraph
    for br in bridges:
        for key in uG[br[0]][br[1]].keys():
            bridge_links.append(key)
        
    return bridge_links

def central_point_dominance(G):
    """
    Central point dominance
    
    Parameters
    ----------
    G : networkx MultiDiGraph
        Graph
        
    Returns
    -------
    Central point dominance (float)
    
    """
    uG = G.to_undirected() # uses an undirected graph
    bet_cen = nx.betweenness_centrality(nx.Graph(uG)) # not implemented for multigraph 
    bet_cen = list(bet_cen.values())
    cpd = sum(max(bet_cen) - np.array(bet_cen))/(len(bet_cen)-1)

    return cpd

def spectral_gap(G):
    """
    Spectral gap
    
    Difference in the first and second eigenvalue of the adjacency matrix
    
    Parameters
    ----------
    G : networkx MultiDiGraph
        Graph
        
    Returns
    -------
    Spectral gap (float)
    
    """
    uG = G.to_undirected() # uses an undirected graph
    eig = nx.adjacency_spectrum(uG)
    spectral_gap = abs(eig[0] - eig[1])

    return spectral_gap.real

def algebraic_connectivity(G):
    """
    Algebraic connectivity
    
    Second smallest eigenvalue of the normalized Laplacian matrix of a network

    Parameters
    ----------
    G : networkx MultiDiGraph
        Graph
        
    Returns
    -------
    Algebraic connectivity (float)
    
    """
    uG = G.to_undirected() # uses an undirected graph
    eig = nx.laplacian_spectrum(uG)
    eig = np.sort(eig)
    alg_con = eig[1]

    return alg_con

def critical_ratio_defrag(G):
    """
    Critical ratio of defragmentation

    Parameters
    ----------
    G : networkx MultiDiGraph
        Graph
        
    Returns
    -------
    Critical ratio of defragmentation (float)
    
    """
    node_degree = dict(G.degree())
    tmp = np.mean(pow(np.array(list(node_degree.values())),2))
    fc = 1-(1/((tmp/np.mean(list(node_degree.values())))-1))

    return fc


def _links_in_simple_paths(G, sources, sinks):
    """
    Count all links in a simple path between sources and sinks

    Parameters
    -----------
    sources : list
        List of source nodes
    sinks : list
        List of sink nodes

    Returns
    -------
    Dictionary with the number of times each link is involved in a path
    
    """
    link_names = [name for (node1, node2, name) in list(G.edges(keys=True))]
    link_count = pd.Series(data = 0, index=link_names)

    for sink in sinks:
        for source in sources:
            if nx.has_path(G, source, sink):
                paths = nx.all_simple_paths(G,source,target=sink)
                for path in paths:
                    for i in range(len(path)-1):
                        links = list(G[path[i]][path[i+1]].keys())
                        for link in links:
                            link_count[link] = link_count[link]+1

    return link_count

def valve_segments(G, valves):
    
    uG = G.to_undirected()
    
    node_names = list(uG.nodes())
    link_names = [k for u,v,k in uG.edges(keys=True)] 
    
    # Pipe-node connectivity matrix
    A = nx.incidence_matrix(uG).todense().T
    AC = pd.DataFrame(A, columns=node_names, index=link_names, dtype=int)

    # Valve-node connectivity matrix
    VC = pd.DataFrame(0, columns=node_names, index=link_names)
    for i, row in valves.iterrows():
        VC.at[row['link'], row['node']] = 1
        
    # Deficient matrix
    VD = AC - VC
    
    # Initialize valve segment matrix
    # Add a row and column at the ends for node and pipe segment labeling
    VS = VD.copy()
    VS.loc['seg',:] = 0
    VS.loc[:,'seg'] = 0
    
    # Identify columns and rows with no elements
    column_with_no_element = VD.columns[VD.sum(axis=0) == 0]
    row_with_no_element = VD.index[VD.sum(axis=1) == 0]
    
    # Assign segments to fully protected nodes and pipes
    num_segments = 0
    for node in column_with_no_element:
        num_segments = num_segments+1
        VS.at['seg',node] = num_segments 
    for pipe in row_with_no_element:
        num_segments = num_segments+1
        VS.at[pipe,'seg'] = num_segments
        
    # Remove fully protected nodes and pipes from analysis matrix
    VD.drop(row_with_no_element, axis=0, inplace=True)
    VD.drop(column_with_no_element, axis=1, inplace=True)
    
    # Assign segments to other nodes and pipes. Loop through remaining nodes.
    for node in VD.columns:
        print(node)
        pipes = VD.index[VD[node]==1]  # identify unprotected pipes at node
        connected_segment = np.max(VS.loc[pipes,'seg'])
        if connected_segment > 0: # at least one unprotected pipe is already assigned a segment. Connect current node to that segment.
            VS.at['seg',node] = connected_segment
            VS.loc[pipes,'seg'] = connected_segment
        else: # unprotected pipes not already assigned a segment. Make a new segment.
            if VS.at['seg',node] == 0 and (VS.loc[pipes,'seg'] == 0).any():
                num_segments = num_segments+1
                VS.at['seg',node] = num_segments
                VS.loc[pipes,'seg'] = num_segments
            elif VS.at['seg',node] != 0:
                VS.loc[pipes,'seg'] = VS.at['seg',node]
    
    VS = VS.astype(int)
    
    #NS = VS.loc['seg', node_names]
    #PS = VS.loc[link_names, 'seg']
    
    return VS