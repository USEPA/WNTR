"""
The wntr.graphics.network module includes methods plot the
water network model.
"""
import networkx as nx
import pandas as pd
from wntr.graphics.color import custom_colormap
try:
    import matplotlib.pyplot as plt
except:
    pass
try:
    import plotly
except:
    pass
import logging

logger = logging.getLogger(__name__)

def plot_network(wn, node_attribute=None, link_attribute=None, title=None,
               node_size=20, node_range = [None,None], node_cmap=plt.cm.jet, node_labels=False,
               link_width=1, link_range = [None,None], link_cmap=plt.cm.jet, link_labels=False,
               add_colorbar=True, directed=False, ax=None):
    """
    Plot network graphic using networkx. 

    Parameters
    ----------
    wn : WaterNetworkModel
        A WaterNetworkModel object

    node_attribute : str, list, pd.Series, or dict, optional
        (default = None)

        - If node_attribute is a string, then a node attribute dictionary is
          created using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node in the list is given a 
          value of 1.
        - If node_attribute is a pd.Series, then it should be in the format
          {(nodeid,time): x} or {nodeid: x} where nodeid is a string and x is 
          a float. The time index is not used in the plot.
        - If node_attribute is a dict, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float

    link_attribute : str, list, pd.Series, or dict, optional
        (default = None)

        - If link_attribute is a string, then a link attribute dictionary is
          created using edge_attribute = wn.query_link_attribute(str)
        - If link_attribute is a list, then each link in the list is given a 
          value of 1.
        - If link_attribute is a pd.Series, then it should be in the format
          {(linkid,time): x} or {linkid: x} where linkid is a string and x is 
          a float. The time index is not used in the plot.
        - If link_attribute is a dict, then it should be in the format
          {linkid: x} where linkid is a string and x is a float.

    title : str, optional
        Plot title (default = None)

    node_size : int, optional
        Node size (default = 10)

    node_range : list, optional
        Node range (default = [None,None], autoscale)

    node_cmap : matplotlib.pyplot.cm colormap, optional
        Node colormap (default = jet)
        
    node_labels: bool, optional
        If True, the graph will include each node labelled with its name. 
        (default = False)
        
    link_width : int, optional
        Link width (default = 1)

    link_range : list, optional
        Link range (default = [None,None], autoscale)

    link_cmap : matplotlib.pyplot.cm colormap, optional
        Link colormap (default = jet)
        
    link_labels: bool, optional
        If True, the graph will include each link labelled with its name. 
        (default = False)
        
    add_colorbar : bool, optional
        Add colorbar (default = True)

    directed : bool, optional
        If True, plot the directed graph (default = False, converts the graph 
        to undirected)
    
    ax : matplotlib axes object, optional
        Axes for plotting (default = None, creates a new figure with a single 
        axes)
        
    Returns
    -------
    nodes, edges

    Notes
    -----
    For more network draw options, see nx.draw_networkx
    """

    if ax is None: # create a new figure
        plt.figure(facecolor='w', edgecolor='k')
        ax = plt.gca()
        
    # Graph
    G = wn.get_graph_deep_copy()
    if not directed:
        G = G.to_undirected()

    # Position
    pos = nx.get_node_attributes(G,'pos')
    if len(pos) == 0:
        pos = None

    # Node attribute
    node_attr_from_list = False
    if isinstance(node_attribute, str):
        node_attribute = wn.query_node_attribute(node_attribute)
    if isinstance(node_attribute, list):
        node_attribute = dict(zip(node_attribute,[1]*len(node_attribute)))
        node_attr_from_list = True
    if isinstance(node_attribute, pd.Series):
        if node_attribute.index.nlevels == 2: # (nodeid, time) index
            # drop time
            node_attribute.reset_index(level=1, drop=True, inplace=True) 
        node_attribute = dict(node_attribute)
    
    # Define node list, color, and colormap
    if node_attribute is None:
        nodelist = None
        nodecolor = 'k'
    else:
        nodelist,nodecolor = zip(*node_attribute.items())
        if node_attr_from_list:
            nodecolor = 'r'
            add_colorbar = False
        
    # Link attribute
    link_attr_from_list = False
    if isinstance(link_attribute, str):
        link_attribute = wn.query_link_attribute(link_attribute)
    if isinstance(link_attribute, list):
        all_link_attribute = dict(zip(wn.link_name_list,[0]*len(wn.link_name_list)))
        for link in link_attribute:
            all_link_attribute[link] = 1
        link_attribute = all_link_attribute
        link_attr_from_list = True
    if isinstance(link_attribute, pd.Series):
        if link_attribute.index.nlevels == 2: # (linkid, time) index
            # drop time
            link_attribute.reset_index(level=1, drop=True, inplace=True) 
        link_attribute = dict(link_attribute)
        
    # Replace link_attribute dictionary defined as
    # {link_name: attr} with {(start_node, end_node, link_name): attr}
    if link_attribute is not None:
        attr = {}
        for link_name, value in link_attribute.items():
            link = wn.get_link(link_name)
            attr[(link.start_node, link.end_node, link_name)] = value
        link_attribute = attr
    if type(link_width) is dict:
        attr = {}
        for link_name, value in link_width.items():
            link = wn.get_link(link_name)
            attr[(link.start_node, link.end_node, link_name)] = value
        link_width = attr
    
    # Define link list, color, and colormap
    if link_attribute is None:
        linklist = None
        linkcolor = 'k'
    else:
        linklist,linkcolor = zip(*link_attribute.items())
        if link_attr_from_list:
            link_cmap = custom_colormap(2, ['black', 'red'])
            add_colorbar = False
            
    if type(link_width) is dict:
        linklist2,link_width = zip(*link_width.items())
        if not linklist == linklist2:
            logger.warning('Link color and width do not share the same \
                           indexes, link width changed to 1.')
            link_width = 1
        
    if title is not None:
        ax.set_title(title)

    nodes = nx.draw_networkx_nodes(G, pos, with_labels=False, 
            nodelist=nodelist, node_color=nodecolor, node_size=node_size, 
            cmap=node_cmap, vmin=node_range[0], vmax = node_range[1], 
            linewidths=0, ax=ax)
    edges = nx.draw_networkx_edges(G, pos, edgelist=linklist, 
            edge_color=linkcolor, width=link_width, edge_cmap=link_cmap, 
            edge_vmin=link_range[0], edge_vmax=link_range[1], ax=ax)
    if node_labels:
        labels = dict(zip(wn.node_name_list, wn.node_name_list))
        nx.draw_networkx_labels(G, pos, labels, font_size=7, ax=ax)
    if link_labels:
        labels = {}
        for link_name in wn.link_name_list:
            link = wn.get_link(link_name)
            labels[(link.start_node, link.end_node)] = link_name
        nx.draw_networkx_edge_labels(G, pos, labels, font_size=7, ax=ax)
    if add_colorbar and node_attribute:
        plt.colorbar(nodes, shrink=0.5, pad=0, ax=ax)
    if add_colorbar and link_attribute:
        plt.colorbar(edges, shrink=0.5, pad=0.05, ax=ax)
    ax.axis('off')

    return nodes, edges

def plot_interactive_network(wn, node_attribute=None, title=None,
               node_size=8, node_range = [None,None], node_cmap='Jet', node_labels=True,
               link_width=1, add_colorbar=True, reverse_colormap=False,
               figsize=[700, 450], round_ndigits=2, filename=None, auto_open=True):
    """
    Create an interactive scalable network graphic using networkx and plotly.  

    Parameters
    ----------
    wn : WaterNetworkModel
        A WaterNetworkModel object

    node_attribute : str, list, pd.Series, or dict, optional
        (default = None)

        - If node_attribute is a string, then a node attribute dictionary is
          created using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node in the list is given a 
          value of 1.
        - If node_attribute is a pd.Series, then it should be in the format
          {(nodeid,time): x} or {nodeid: x} where nodeid is a string and x is 
          a float.
          The time index is not used in the plot.
        - If node_attribute is a dict, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float

    title : str, optional
        Plot title (default = None)

    node_size : int, optional
        Node size (default = 8)

    node_range : list, optional
        Node range (default = [None,None], autoscale)

    node_cmap : palette name string, optional
        Node colormap, options include Greys, YlGnBu, Greens, YlOrRd, Bluered, 
        RdBu, Reds, Blues, Picnic, Rainbow, Portland, Jet, Hot, Blackbody, 
        Earth, Electric, Viridis (default = Jet)
    
    node_labels: bool, optional
        If True, the graph will include each node labelled with its name and 
        attribute value. (default = True)
        
    link_width : int, optional
        Link width (default = 1)
    
    add_colorbar : bool, optional
        Add colorbar (default = True)
        
    reverse_colormap : bool, optional
        Reverse colormap (default = True)
        
    figsize: list, optional
        Figure size in pixels, default= [700, 450]

    round_ndigits : int, optional
        Number of digits to round node values used in the label (default = 2)
        
    filename : string, optional
        HTML file name (default=None, temp-plot.html)
    """

    # Graph
    G = wn.get_graph_deep_copy()
    
    # Node attribute
    if isinstance(node_attribute, str):
        node_attribute = wn.query_node_attribute(node_attribute)
    if isinstance(node_attribute, list):
        node_attribute = dict(zip(node_attribute,[1]*len(node_attribute)))
    if isinstance(node_attribute, pd.Series):
        if node_attribute.index.nlevels == 2: # (nodeid, time) index
            # drop time
            node_attribute.reset_index(level=1, drop=True, inplace=True) 
        node_attribute = dict(node_attribute)

    # Create edge trace
    edge_trace = plotly.graph_objs.Scatter(
        x=[], 
        y=[], 
        text=[],
        hoverinfo='text',
        mode='lines',
        line=plotly.graph_objs.Line(
            #colorscale=link_cmap,
            #reversescale=reverse_colormap,
            color='#888', #[], 
            width=link_width))
    for edge in G.edges():
        x0, y0 = G.node[edge[0]]['pos']
        x1, y1 = G.node[edge[1]]['pos']
        edge_trace['x'] += [x0, x1, None]
        edge_trace['y'] += [y0, y1, None]
#        try:
#            # Add link attributes
#            link_name = G[edge[0]][edge[1]].keys()[0]
#            edge_trace['line']['color'].append(pipe_attr[link_name])
#            edge_info = 'Edge ' + str(link_name)
#            edge_trace['text'].append(edge_info)
#        except:
#            pass
#    edge_trace['colorbar']['title'] = 'Link colorbar title'
    
    # Create node trace      
    node_trace = plotly.graph_objs.Scatter(
        x=[], 
        y=[], 
        text=[],
        hoverinfo='text',
        mode='markers', 
        marker=plotly.graph_objs.Marker(
            showscale=add_colorbar,
            colorscale=node_cmap, 
            cmin=node_range[0],
            cmax=node_range[1],
            reversescale=reverse_colormap,
            color=[], 
            size=node_size,         
            #opacity=0.75,
            colorbar=dict(
                thickness=15,
                xanchor='left',
                titleside='right'),
            line=dict(width=1)))
    for node in G.nodes():
        x, y = G.node[node]['pos']
        node_trace['x'].append(x)
        node_trace['y'].append(y)
        try:
            # Add node attributes
            node_trace['marker']['color'].append(node_attribute[node])
            #node_trace['marker']['size'].append(node_size)
            # Add node labels
            if node_labels:
                node_info = 'Node ' + str(node) + ', '+ \
                            str(round(node_attribute[node],round_ndigits))
                node_trace['text'].append(node_info)
        except:
            node_trace['marker']['color'].append('#888')
            if node_labels:
                node_info = 'Node ' + str(node)
                node_trace['text'].append(node_info)
            #node_trace['marker']['size'].append(5)
    #node_trace['marker']['colorbar']['title'] = 'Node colorbar title'
    
    # Create figure
    data = plotly.graph_objs.Data([edge_trace, node_trace])
    layout = plotly.graph_objs.Layout(
                    title=title,
                    titlefont=dict(size=16),
                    showlegend=False, 
                    width=figsize[0],
                    height=figsize[1],
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=plotly.graph_objs.XAxis(showgrid=False, 
                            zeroline=False, showticklabels=False),
                    yaxis=plotly.graph_objs.YAxis(showgrid=False, 
                            zeroline=False, showticklabels=False))
    
    fig = plotly.graph_objs.Figure(data=data,layout=layout)
    if filename:
        plotly.offline.plot(fig, filename=filename, auto_open=auto_open)  
    else:
        plotly.offline.plot(fig, auto_open=auto_open)  
