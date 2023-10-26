import networkx as nx
import itertools

from wntr.metrics.topographic import *

def upstream_nodes(G, source_node):
    """
    Steady state upstream nodes from a source node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph
    source_node : str
        Source node name
    
    Returns
    --------
    List of upstream node names
    
    """
    nodes = list(nx.traversal.bfs_tree(G, source_node, reverse=True))
    return nodes

def upstream_edges(G, source_node):
    """
    Steady state upstream edges from a source node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph
    source_node : str
        Source node name
    
    Returns
    --------
    List of upstream edge names
    
    """
    # NOTE: 'edge_bfs' yields edges even if they extend back to an already
    # explored node while 'bfs_edges' yields the edges of the tree that results
    # from a breadth-first-search (BFS) so no edges are reported if they extend
    # to already explored nodes.  AND Extracting edge names from u,v is slower
    # edge_uv = list(nx.traversal.bfs_edges(G, node, reverse=False))
    # uG = G.to_undirected()
    # edges = []
    # for u,v in edge_uv:
    # edges.extend(list(uG[u][v].keys()))
    edge_uvko = list(nx.traversal.edge_bfs(G, source_node, orientation='reverse'))
    edges = [k for u,v,k,orentation in edge_uvko]  
    return edges

def downstream_nodes(G, source_node):
    """
    Steady state downstream nodes from a source node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph
    source_node : str
        Source node name
    
    Returns
    --------
    List of downstream node names
    
    """
    nodes = list(nx.traversal.bfs_tree(G, source_node, reverse=False))
    return nodes

def downstream_edges(G, source_node):
    """
    Steady state downstream edges from a source node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph
    source_node : str
        Source node name
    
    Returns
    --------
    List of downstream edge names
    
    """
    edge_uvko = list(nx.traversal.edge_bfs(G, source_node, orientation='original'))
    edges = [k for u,v,k,orentation in edge_uvko]  
    return edges
