import networkx as nx
import matplotlib.pyplot as plt
import networkx_extensions as nx_ext

def draw_graph(G, node_attribute=None, edge_attribute=None, title=None, 
               node_size=20, edge_width=1, 
               node_cmap=None, edge_cmap=None):
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
    plt.figure()
    if title is not None:
        plt.title(title)
    nx.draw_networkx(G, pos=pos, with_labels=False, 
        nodelist=nodelist, node_color=nodecolor, node_size=node_size, cmap=node_cmap,
        edgelist=edgelist, edge_color=edgecolor, width=edge_width, edge_cmap=edge_cmap)