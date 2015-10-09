import networkx as nx
import numpy as np

def weight_graph(G, node_attribute={}, link_attribute={}):
    """ Return a weighted graph based on node and link attributes.
    The weighted graph changes the direction of the original link if the weight is negative.
    
    Parameters
    ----------
    G : graph
        A networkx graph
    
    node_attribute :  dict or pandas Series
        node attributes
    
    link_attribues : dict or pandas Series
        link attributes
      
    Returns
    -------
    G : weighted graph
        A networkx weighted graph
    """

    for node_name in G.nodes():
        try:
            value = node_attribute[node_name]
            
            nx.set_node_attributes(G, 'weight', {node_name: value})
        except:
            pass
    
    for (node1, node2, link_name) in G.edges(keys=True):
        try:
            value = link_attribute[link_name]
        
            if value < 0: # change the direction of the link and value
                link_type = G[node1][node2][link_name]['type'] # 'type' should be the only other attribute on G.edge
                G.remove_edge(node1, node2, link_name)
                G.add_edge(node2, node1, link_name)
                nx.set_edge_attributes(G, 'type', {(node2, node1, link_name): link_type})
                nx.set_edge_attributes(G, 'weight', {(node2, node1, link_name): -value})
            else:
                nx.set_edge_attributes(G, 'weight', {(node1, node2, link_name): value})
        except:
                pass
    return G