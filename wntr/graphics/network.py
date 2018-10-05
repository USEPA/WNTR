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
    plt = None
try:
    import plotly
except:
    plotly = None
try:
    import folium
except:
    folium = None
import logging

logger = logging.getLogger(__name__)

def _format_node_attribute(node_attribute, wn):
    
    if isinstance(node_attribute, str):
        node_attribute = wn.query_node_attribute(node_attribute)
    if isinstance(node_attribute, list):
        node_attribute = dict(zip(node_attribute,[1]*len(node_attribute)))
    if isinstance(node_attribute, pd.Series):
        node_attribute = dict(node_attribute)
    
    return node_attribute

def _format_link_attribute(link_attribute, wn):
    
    if isinstance(link_attribute, str):
        link_attribute = wn.query_link_attribute(link_attribute)
    if isinstance(link_attribute, list):
        link_attribute = dict(zip(link_attribute,[1]*len(link_attribute)))
    if isinstance(link_attribute, pd.Series):
        link_attribute = dict(link_attribute)
            
    return link_attribute
        
def plot_network(wn, node_attribute=None, link_attribute=None, title=None,
               node_size=20, node_range = [None,None], node_cmap=None, node_labels=False,
               link_width=1, link_range = [None,None], link_cmap=None, link_labels=False,
               add_colorbar=True, directed=False, ax=None):
    """
    Plot network graphic using networkx. 

    Parameters
    ----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object

    node_attribute : str, list, pd.Series, or dict, optional
        (default = None)

        - If node_attribute is a string, then a node attribute dictionary is
          created using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node in the list is given a 
          value of 1.
        - If node_attribute is a pd.Series, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float. 
        - If node_attribute is a dict, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float

    link_attribute : str, list, pd.Series, or dict, optional
        (default = None)

        - If link_attribute is a string, then a link attribute dictionary is
          created using edge_attribute = wn.query_link_attribute(str)
        - If link_attribute is a list, then each link in the list is given a 
          value of 1.
        - If link_attribute is a pd.Series, then it should be in the format
          {linkid: x} where linkid is a string and x is a float. 
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
    
    if plt is None:
        raise ImportError('matplotlib is required')

    if node_cmap is None:
        node_cmap = plt.cm.Spectral_r
    if link_cmap is None:
        link_cmap = plt.cm.Spectral_r
    if ax is None: # create a new figure
        plt.figure(facecolor='w', edgecolor='k')
        ax = plt.gca()
        
    # Graph
    G = wn.get_graph()
    if not directed:
        G = G.to_undirected()

    # Position
    pos = nx.get_node_attributes(G,'pos')
    if len(pos) == 0:
        pos = None

    # Define node properties
    if node_attribute is not None:
        node_attribute_from_list = False
        if isinstance(node_attribute, list):
            node_attribute_from_list = True
            add_colorbar = False
        node_attribute = _format_node_attribute(node_attribute, wn)
        nodelist,nodecolor = zip(*node_attribute.items())
        if node_attribute_from_list:
            nodecolor = 'r'
    else:
        nodelist = None
        nodecolor = 'k'
    
    if link_attribute is not None:
        if isinstance(link_attribute, list):
            link_cmap = custom_colormap(2, ['red', 'black'])
            add_colorbar = False
        link_attribute = _format_link_attribute(link_attribute, wn)
        
        # Replace link_attribute dictionary defined as
        # {link_name: attr} with {(start_node, end_node, link_name): attr}
        attr = {}
        for link_name, value in link_attribute.items():
            link = wn.get_link(link_name)
            attr[(link.start_node_name, link.end_node_name, link_name)] = value
        link_attribute = attr
        
        linklist,linkcolor = zip(*link_attribute.items())
    else:
        linklist = None
        linkcolor = 'k'
    
    if title is not None:
        ax.set_title(title)
        
    edges = nx.draw_networkx_edges(G, pos, edge_color='grey', width=0.75, ax=ax)
    
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
            labels[(link.start_node_name, link.end_node_name)] = link_name
        nx.draw_networkx_edge_labels(G, pos, labels, font_size=7, ax=ax)
    if add_colorbar and node_attribute:
        plt.colorbar(nodes, shrink=0.5, pad=0, ax=ax)
    if add_colorbar and link_attribute:
        plt.colorbar(edges, shrink=0.5, pad=0.05, ax=ax)
    ax.axis('off')

    return nodes, edges

def plot_interactive_network(wn, node_attribute=None, title=None,
               node_size=8, node_range=[None,None], node_cmap='Jet', node_labels=True,
               link_width=1, add_colorbar=True, reverse_colormap=False,
               figsize=[700, 450], round_ndigits=2, filename=None, auto_open=True):
    """
    Create an interactive scalable network graphic using networkx and plotly.  

    Parameters
    ----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object

    node_attribute : str, list, pd.Series, or dict, optional
        (default = None)

        - If node_attribute is a string, then a node attribute dictionary is
          created using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node in the list is given a 
          value of 1.
        - If node_attribute is a pd.Series, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float.
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
    if plotly is None:
        raise ImportError('plotly is required')
        
    # Graph
    G = wn.get_graph()
    
    # Node attribute
    if node_attribute is not None:
        if isinstance(node_attribute, list):
            node_cmap = 'Red'
            print(node_cmap)
            add_colorbar = False
        node_attribute = _format_node_attribute(node_attribute, wn)
    else:
        add_colorbar = False
        
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
            cmin=node_range[0], # TODO: Not sure this works
            cmax=node_range[1], # TODO: Not sure this works
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
                node_info = wn.get_node(node).node_type + ' ' + str(node) + ', '+ \
                            str(round(node_attribute[node],round_ndigits))
                node_trace['text'].append(node_info)
        except:
            node_trace['marker']['color'].append('#888')
            if node_labels:
                node_info = wn.get_node(node).node_type + ' ' + str(node)
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

def plot_leaflet_network(wn, node_attribute=None, link_attribute=None, 
               node_size=4, node_range=[None,None], node_cmap=['cornflowerblue', 'forestgreen', 'gold', 'firebrick'], 
               node_cmap_bins = 'cut', node_labels=True,
               link_width=2, link_range=[None,None], link_cmap=['cornflowerblue', 'forestgreen', 'gold', 'firebrick'], 
               link_cmap_bins = 'cut', link_labels=True,
               add_legend=False, round_ndigits=2, zoom_start=15, filename='folium.html'):
    
    """
    Create the network on a Leaflet map using folium.  
    """
    if folium is None:
        raise ImportError('folium is required')
    
    if node_attribute is not None:
        if isinstance(node_attribute, list):
            node_cmap=['red']
        node_attribute = _format_node_attribute(node_attribute, wn)
        node_attribute = pd.Series(node_attribute)
        if node_range[0] is not None:
            node_attribute[node_attribute < node_range[0]] = node_range[0]
        if node_range[1] is not None:
            node_attribute[node_attribute > node_range[1]] = node_range[1]
        if node_cmap_bins == 'cut':
            node_colors, node_bins = pd.cut(node_attribute, len(node_cmap), 
                                            labels=node_cmap, retbins =True)
        elif node_cmap_bins == 'qcut':
            node_colors, node_bins = pd.qcut(node_attribute, len(node_cmap), 
                                             labels=node_cmap, retbins =True)
        
    if link_attribute is not None:
        if isinstance(link_attribute, list):
            link_cmap=['red']
        link_attribute = _format_link_attribute(link_attribute, wn)
        link_attribute = pd.Series(link_attribute)
        if link_range[0] is not None:
            link_attribute[link_attribute < link_range[0]] = link_range[0]
        if link_range[1] is not None:
            link_attribute[link_attribute > link_range[1]] = link_range[1]
        if link_cmap_bins == 'cut':
            link_colors, link_bins  = pd.cut(link_attribute, len(link_cmap), 
                                             labels=link_cmap, retbins =True)
        elif link_cmap_bins == 'qcut':
            link_colors, link_bins  = pd.qcut(link_attribute, len(link_cmap), 
                                              labels=link_cmap, retbins =True)
        
    G = wn.get_graph()
    pos = nx.get_node_attributes(G,'pos')
    center = pd.DataFrame(pos).mean(axis=1)
    
    m = folium.Map(location=[center.iloc[1], center.iloc[0]], zoom_start=zoom_start)
    folium.TileLayer('cartodbpositron').add_to(m)
    
    for name, node in wn.nodes():
        loc = (node.coordinates[1], node.coordinates[0])
        radius = node_size
        color = 'black'
        if node_labels:
            popup = node.node_type + ': ' + name
        else:
            popup = None
                
        if node_attribute is not None:
            if name in node_attribute.index:
                color = node_colors[name]
                if node_labels:
                    popup = node.node_type + ' ' + name + ', ' + \
                            '{:.{prec}f}'.format(node_attribute[name], prec=round_ndigits)
            else:
                radius = 0
        
        folium.CircleMarker(loc, popup=popup, color=color, fill=True, 
                            fill_color=color, radius=radius, fill_opacity=0.7, opacity=0.7).add_to(m)
        
    for name, link in wn.links():
        start_loc = (link.start_node.coordinates[1], link.start_node.coordinates[0])
        end_loc = (link.end_node.coordinates[1], link.end_node.coordinates[0])
        weight = link_width
        color='black'
        if link_labels:
            popup = link.link_type + ': ' + name
        else:
            popup = None
        
        if link_attribute is not None:
            if name in link_attribute.index:
                color = link_colors[name]
                if link_labels:
                    popup = link.link_type + ' ' + name + ', ' + \
                        '{:.{prec}f}'.format(link_attribute[name], prec=round_ndigits)
            else:
                weight = 1.5
        
        folium.PolyLine([start_loc, end_loc], popup=popup, color=color, 
                        weight=weight, opacity=0.7).add_to(m)
    
    height=0
    if node_attribute is not None:
        height = height + 50+len(node_cmap)*20
    if link_attribute is not None:
        height= height + 50+len(link_cmap)*20
    if (add_legend) & (len(node_cmap) > 1) & (len(link_cmap) > 1):
        legend_html = """<div style="position: fixed; 
        bottom: 50px; left: 50px; width: 150px; height: """+str(height)+"""px; 
        background-color:white;z-index:9999; font-size:14px; ">"""
        if (node_attribute is not None) & (len(node_cmap) > 1):
            legend_html = legend_html + """<br>
            &nbsp;&nbsp;&nbsp; <b>Node legend</b> <br> """
            for color, val in zip(node_cmap, node_bins[0:-1]):
                val = '{:.{prec}f}'.format(val, prec=round_ndigits)
                legend_html = legend_html + """
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i class="fa fa-circle fa-1x" 
                style="color:"""+ color +""" "></i> >= """+ val +""" <br>"""
        if (link_attribute is not None) & (len(link_cmap) > 1):
            legend_html = legend_html + """<br>
            &nbsp;&nbsp;&nbsp; <b>Link legend</b> <br>"""
            for color, val in zip(link_cmap, link_bins[0:-1]):
                val = '{:.{prec}f}'.format(val, prec=round_ndigits)
                legend_html = legend_html + """
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i class="fa fa-square fa-1x" 
                style="color:"""+ color +""" "></i> >= """+ val +""" <br>"""
        legend_html = legend_html + """</div>"""
        m.get_root().html.add_child(folium.Element(legend_html))
    
    #plugins.Search(points, search_zoom=20, ).add_to(m)
    #m.add_child(folium.LatLngPopup())
    folium.LayerControl().add_to(m)
    
    m.save(filename)
 