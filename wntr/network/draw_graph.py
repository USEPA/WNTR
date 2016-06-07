import networkx as nx
try:
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
except:
    pass
import pandas as pd
import logging

logger = logging.getLogger('wntr.network.draw_graph')

def draw_graph(wn, node_attribute=None, link_attribute=None, title=None, 
               node_size=10, node_range = [None,None], node_cmap=None,
               link_width=1, link_range = [None,None], link_cmap=None, 
               add_colorbar=True, figsize=None, dpi=None, directed=False, node_labels=False,plt_fig=None):

    r"""Draw a WaterNetworkModel networkx graph
    
    Parameters
    ----------
    wn : WaterNetworkModel
        A WaterNetworkModel object
    
    node_attribute : str, list, pd.Series, or dict, optional 
        (default = None)
        
        - If node_attribute is a string, then the node_attribute dictonary is 
          populated using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node is given a value of 1.
        - If node_attribute is a pd.Series, then it shoud be in the format
          {(nodeid,time): x} or {nodeid: x} where nodeid is a string and x is a float. 
          The time index is not used in the plot.
        - If node_attribute is a dict, then it shoud be in the format
          {nodeid: x} where nodeid is a string and x is a float
        
    link_attribute : str, list, pd.Series, or dict, optional 
        (default = None)
        
        - If link_attribute is a string, then the link_attribute dictonary is 
          populated using edge_attribute = wn.query_link_attribute(str)
        - If link_attribute is a list, then each link is given a value of 1.
        - If link_attribute is a pd.Series, then it shoud be in the format
          {(linkid,time): x} or {linkid: x} where linkid is a string and x is a float. 
          The time index is not used in the plot.
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

    node_labels: bool, optional
        If True, the graph will have each node labeled with its name.
        (default = False)
        
    Returns
    -------
    Figure
    
    Examples
    --------
    >>> wn = en.network.WaterNetworkModel('Net1.inp')
    >>> en.network.draw_graph(wn)

    Notes
    -----
    For more network draw options, see nx.draw_networkx
    
    """
    if plt_fig is None:
        plt.figure(facecolor='w', edgecolor='k')
        
    # Graph    
    G = wn.get_graph_deep_copy()
    if not directed:
        G = G.to_undirected()
    
    # Position
    pos = nx.get_node_attributes(G,'pos')
    if len(pos) == 0:
        pos = None
    
    # Node attribute
    if isinstance(node_attribute, str):
        node_attribute = wn.query_node_attribute(node_attribute)
    if isinstance(node_attribute, list):
        node_attribute = dict(zip(node_attribute,[1]*len(node_attribute)))
    if isinstance(node_attribute, pd.Series):
        if node_attribute.index.nlevels == 2: # (nodeid, time) index
            node_attribute.reset_index(level=1, drop=True, inplace=True) # drop time
        node_attribute = dict(node_attribute)
    
    # Define node list, color, and colormap
    if node_attribute is None: 
        nodelist = None
        nodecolor = 'k'
    else:
        nodelist,nodecolor = zip(*node_attribute.items())
    if node_cmap is None:
        node_cmap=plt.cm.jet
        
    # Link attribute
    if isinstance(link_attribute, str):
        link_attribute = wn.query_link_attribute(link_attribute)
    if isinstance(link_attribute, list):
        link_attribute = dict(zip(link_attribute,[1]*len(link_attribute)))
    if isinstance(link_attribute, pd.Series):
        if link_attribute.index.nlevels == 2: # (linkid, time) index
            link_attribute.reset_index(level=1, drop=True, inplace=True) # drop time
        link_attribute = dict(link_attribute)
    
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
            logger.warning('Link color and width do not share the same indexes, link width changed to 1.')
            link_width = 1
    if link_cmap is None:
        link_cmap=plt.cm.jet
        
    # Plot
    #plt.figure(facecolor='w', edgecolor='k', figsize=figsize, dpi=dpi)
    
    if title is not None:
        plt.title(title)

    if node_labels:
        nodes = nx.draw_networkx_labels(G, pos,
                                       nodelist=nodelist, node_color=nodecolor, node_size=node_size, cmap=node_cmap, vmin = node_range[0], vmax = node_range[1],linewidths=0)
    else:
        nodes = nx.draw_networkx_nodes(G, pos, with_labels=False, 
                                       nodelist=nodelist, node_color=nodecolor, node_size=node_size, cmap=node_cmap, vmin = node_range[0], vmax = node_range[1],linewidths=0)
    edges = nx.draw_networkx_edges(G, pos, 
                                   edgelist=linklist, edge_color=linkcolor, width=link_width, edge_cmap=link_cmap, edge_vmin = link_range[0], edge_vmax = link_range[1])
    if add_colorbar and node_attribute:
        plt.colorbar(nodes, shrink=0.5, pad = 0)
    if add_colorbar and link_attribute:
        plt.colorbar(edges, shrink=0.5, pad = 0.05)
    plt.axis('off')
    
    return nodes, edges

def custom_colormap(numcolors=11, colors=['blue','white','red']):
    """ 
    Create a custom colormap
    Default is blue to white to red with 11 colors.  
    Colors can be specified in any way understandable by matplotlib.colors.ColorConverter.to_rgb()
    """
    cmap = LinearSegmentedColormap.from_list(name='custom', 
                                             colors = colors,
                                             N=numcolors)
    return cmap
    
