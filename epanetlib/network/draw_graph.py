import networkx as nx
import matplotlib.pyplot as plt
import networkx_extensions as nx_ext

def draw_graph(G, node_attribute=None, edge_attribute=None, title=None, 
               node_size=20, node_range = [None,None], node_cmap=None,
               edge_width=1, edge_range = [None,None], edge_cmap=None, add_colorbar=True):
    r"""Draw networkx graph
    
    Parameters
    ----------
    G : graph
        A networkx graph
    
    node_attribute: str or dict, optional (default = None)
        If node_attribute is a string, then the node_attribute dictonary is 
        populated using node_attribute = nx.get_node_attributes(G,node_attribute)
        If node_attribute is a dict, then it shoud be in the format
        {nodeid: x} where nodeid is a string and x is a float
        
    edge_attribute: str or dict, optional (default = None)
        If edge_attribute is a string, then the edge_attribute dictonary is 
        populated using edge_attribute = nx_ext.edge_attribute_MG(G,edge_attribute)
        If edge_attribute is a dict, then it shoud be in the format
        {(nodeid1, nodeid2, linkid): x} where nodeid1 is a string, 
        nodeid2 is a string, linkid is a string,
        and x is a float.  nodeid1 is the start node and nodeid2 is the end node
        
    title: str, optional (default = None)
        
    node_size: int, optional (default = 20)
    
    edge_width: int, optional (default = 1)
    
    node_cmap: matplotlib.pyplot.cm colormap, optional (default = rainbow)
    
    edge_cmp: matplotlib.pyplot.cm colormap, optional (default = rainbow)
    
    Examples
    --------
    >>> enData = en.pyepanet.ENepanet()
    >>> enData.ENopen('Net1.inp','tmp.rpt')
    >>> pos = en.pyepanet.future.ENgetcoordinates('Net1.inp')
    >>> MG = en.network.epanet_to_MultiGraph(enData, pos=pos)
    >>> en.network.draw_graph(MG)
    
    Notes
    -----
    For more network draw options, see nx.draw_networkx
    
    """
    
    # Position
    pos = nx.get_node_attributes(G,'pos')
    if len(pos) == 0:
        pos = None
    
    # Node attribute
    if type(node_attribute) is str:
        node_attribute = nx.get_node_attributes(G,node_attribute)
    
    if node_attribute is None: 
        nodelist = None
        nodecolor = 'r'
    else:
        nodelist,nodecolor = zip(*node_attribute.items())
    
    # Edge attribute
    if type(edge_attribute) is str:
        edge_attribute = nx_ext.get_edge_attributes_MG(G,edge_attribute)

    if edge_attribute is None: 
        edgelist = None
        edgecolor = 'k'
    else:
        edgelist,edgecolor = zip(*edge_attribute.items())
    
    if node_cmap is None:
        node_cmap=plt.cm.rainbow
    if edge_cmap is None:
        edge_cmap=plt.cm.rainbow
        
    # Plot
    plt.figure(facecolor='w', edgecolor='k')
    if title is not None:
        plt.title(title)
    nodes = nx.draw_networkx_nodes(G, pos, with_labels=False, 
              nodelist=nodelist, node_color=nodecolor, node_size=node_size, cmap=node_cmap, vmin = node_range[0], vmax = node_range[1])
    edges = nx.draw_networkx_edges(G, pos, 
            edgelist=edgelist, edge_color=edgecolor, width=edge_width, edge_cmap=edge_cmap, edge_vmin = edge_range[0], edge_vmax = edge_range[1])
    if add_colorbar and node_attribute:
        plt.colorbar(nodes, shrink=0.5, pad = 0)
    if add_colorbar and edge_attribute:
        plt.colorbar(edges, shrink=0.5, pad = 0.05)
    plt.axis('off')
    """
    nx.draw_networkx(G, pos=pos, with_labels=False, 
        nodelist=nodelist, node_color=nodecolor, node_size=node_size, cmap=node_cmap, vmin = node_range[0], vmax = node_range[1],
        edgelist=edgelist, edge_color=edgecolor, width=edge_width, edge_cmap=edge_cmap, edge_vmin = edge_range[0], edge_vmax = edge_range[1])
    """