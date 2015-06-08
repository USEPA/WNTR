import networkx as nx
import matplotlib.pyplot as plt

def draw_graph(wn, node_attribute=None, link_attribute=None, title=None, 
               node_size=10, node_range = [None,None], node_cmap=None,
               link_width=1, link_range = [None,None], link_cmap=None, 
               add_colorbar=True, figsize=None, directed=False):

    r"""Draw a WaterNetworkModel networkx graph
    
    Parameters
    ----------
    wn : WaterNetworkModel
        A WaterNetworkModel object
    
    node_attribute : str, list, or dict, optional 
        (default = None)
        
        - If node_attribute is a string, then the node_attribute dictonary is 
          populated using node_attribute = wn.get_node_attribute(str)
        - If node_attribute is a list, then each node is given a value of 1.
        - If node_attribute is a dict, then it shoud be in the format
          {nodeid: x} where nodeid is a string and x is a float
        
    link_attribute : str, list, or dict, optional 
        (default = None)
        
        - If link_attribute is a string, then the link_attribute dictonary is 
          populated using edge_attribute = wn.get_link_attribute(str)
        - If link_attribute is a list, then each link is given a value of 1.
        - If link_attribute is a dict, then it shoud be in the format
          {linkid: x} where linkid is a string and x is a float.  
        
    title : str, optional 
        (default = None)
        
    node_size : int, optional 
        (default = 10)
    
    node_range : list, optional 
        (default = [None,None])
    
    node_cmap : matplotlib.pyplot.cm colormap, optional 
        (default = jet)
    
    link_width : int, optional 
        (default = 1)
    
    link_range : list, optional 
        (default = [None,None])
    
    link_cmap : matplotlib.pyplot.cm colormap, optional 
        (default = jet)
    
    add_colorbar : bool, optional 
        (default = True)
    
    directed : bool, optional 
        (default = False)
        
    Returns
    -------
    Figure
    
    Examples
    --------
    >>> wn = en.network.WaterNetworkModel()
    >>> parser = en.network.ParseWaterNetwork()
    >>> parser.read_inp_file(wn, 'Net1.inp')
    >>> en.network.draw_graph(wn)

    Notes
    -----
    For more network draw options, see nx.draw_networkx
    
    """
    
    # Graph    
    G = wn._graph
    if not directed:
        G = G.to_undirected()
    
    # Position
    pos = nx.get_node_attributes(G,'pos')
    if len(pos) == 0:
        pos = None
    
    # Node attribute
    if type(node_attribute) is str:
        node_attribute = wn.get_node_attribute(node_attribute)
    if type(node_attribute) is list:
        node_attribute = dict(zip(node_attribute,[1]*len(node_attribute)))
    # Define node list, color, and colormap
    if node_attribute is None: 
        nodelist = None
        nodecolor = 'k'
    else:
        nodelist,nodecolor = zip(*node_attribute.items())
    if node_cmap is None:
        node_cmap=plt.cm.jet
        
    # Link attribute
    if type(link_attribute) is str:
        link_attribute = wn.get_link_attribute(link_attribute)
    if type(link_attribute) is list:
        link_attribute = dict(zip(link_attribute,[1]*len(link_attribute)))
    # Replace link_attribute dictonary defined as
    # {link_name: attr} with {(start_node, end_node, link_name): attr}
    if link_attribute is not None:  
        attr = {}
        for link_name, value in link_attribute.iteritems():
            link = wn.get_link(link_name)
            attr[(link.start_node(), link.end_node(), link_name)] = value
        link_attribute = attr
    if type(link_width) is dict:
        attr = {}
        for link_name, value in link_width.iteritems():
            link = wn.get_link(link_name)
            attr[(link.start_node(), link.end_node(), link_name)] = value
        link_width = attr
        
    # Define link list, color, and colormap
    if link_attribute is None: 
        linklist = None
        linkcolor = 'k'
    else:
        linklist,linkcolor = zip(*link_attribute.items())
    if type(link_width) is dict:
        linklist2,link_width = zip(*link_width.items())
        if not linklist == linklist2:
            print "Link color and width do not share the same indexes, link width changed to 1."
            link_width = 1
    if link_cmap is None:
        link_cmap=plt.cm.jet
        
    # Plot
    plt.figure(facecolor='w', edgecolor='k', figsize=figsize)
    if title is not None:
        plt.title(title)
    nodes = nx.draw_networkx_nodes(G, pos, with_labels=False, 
              nodelist=nodelist, node_color=nodecolor, node_size=node_size, cmap=node_cmap, vmin = node_range[0], vmax = node_range[1])
    edges = nx.draw_networkx_edges(G, pos, 
            edgelist=linklist, edge_color=linkcolor, width=link_width, edge_cmap=link_cmap, edge_vmin = link_range[0], edge_vmax = link_range[1])
    if add_colorbar and node_attribute:
        plt.colorbar(nodes, shrink=0.5, pad = 0)
    if add_colorbar and link_attribute:
        plt.colorbar(edges, shrink=0.5, pad = 0.05)
    plt.axis('off')
