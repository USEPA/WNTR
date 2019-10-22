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
