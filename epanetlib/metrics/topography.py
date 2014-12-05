import epanetlib.pyepanet as pyepanet
import numpy as np

def terminal_nodes(G):
    """ Get all nodes with degree 1
    
    Parameters
    ----------
    G : graph
        A networkx graph
        
    Returns
    -------
    terminal_nodes : list
        list of node indexes
    """
    
    node_degree = G.degree() 
    terminal_nodes = [k for k,v in node_degree.iteritems() if v == 1]
    
    return terminal_nodes

def nzd_nodes(G):
    """ Get all nodes with a base demand > 0
        
    Parameters
    ----------
    G : graph
        A networkx graph
        
    Returns
    -------
    nzd_nodes : list
        list of node indexes
    """
    
    nzd_nodes = query_node_attribute(G, 'base_demand', np.greater, 0)
    
    return nzd_nodes
    
def tank_nodes(G):
    """ Get all nodes connected to a tank
        
    Parameters
    ----------
    G : graph
        A networkx graph
        
    Returns
    -------
    nzd_nodes : list
        list of node indexes
    """
    
    tank_nodes = []
    G = G.to_undirected()
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_TANK:
            tank_nodes.extend(G.neighbors(i))
            
    return tank_nodes
    
def query_pipe_attribute(G, attribute, operation, value):
    """ Query pipe attributes, for example get all pipe diameters > treshold
        
    Parameters
    ----------
    G : graph
        A networkx graph
    
    attribute: string
        Pipe attribute
        
    operation: np option
        options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal    
        
    value: scalar
        treshold
        
    Returns
    -------
    pipes : list
        list of tuples (node1, node2, linkid)
    """
    pipes = []
    for i,j,k in G.edges(keys=True):
        pipe_attribute = G.edge[i][j][k][attribute]
        if not np.isnan(pipe_attribute):
            if operation(pipe_attribute, value):
                pipes.append((i,j,k))
            
    return pipes
    
def query_node_attribute(G, attribute, operation, value):
    """ Query node attributes, for example get all nodes with elevation <= treshold
        
    Parameters
    ----------
    G : graph
        A networkx graph
    
    attribute: string
        Pipe attribute
        
    operation: np option
        options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal    
        
    value: scalar
        treshold
        
    Returns
    -------
    pipes : list
        list of nodeid
    """
    nodes = []
    for i in G.nodes():
        node_attribute = G.node[i][attribute]
        if not np.isnan(node_attribute):
            if operation(node_attribute, value):
                nodes.append(i)
            
    return nodes