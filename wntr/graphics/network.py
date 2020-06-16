"""
The wntr.graphics.network module includes methods plot the
water network model.
"""
import logging
import networkx as nx
import pandas as pd
import os
from wntr.morph import convert_node_coordinates_to_longlat
from wntr.epanet import FlowUnits
try:
    import matplotlib.pyplot as plt
    from matplotlib import animation
except:
    plt = None
try:
    import plotly
except:
    plotly = None
try:
    import folium
    import folium.plugins
except:
    folium = None
try:
    import json
except:
    json = None    
from wntr.graphics.color import custom_colormap

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
               node_size=20, node_range=[None,None], node_alpha=1, node_cmap=None, node_labels=False,
               link_width=1, link_range=[None,None], link_alpha=1, link_cmap=None, link_labels=False,
               valve_layer=None, valve_criticality=None, add_colorbar=True, node_colorbar_label='Node', link_colorbar_label='Link', 
               directed=False, ax=None, filename=None):
    """
    Plot network graphic

    Parameters
    ----------
    wn: wntr WaterNetworkModel
        A WaterNetworkModel object

    node_attribute: None, str, list, pd.Series, or dict, optional

        - If node_attribute is a string, then a node attribute dictionary is
          created using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node in the list is given a 
          value of 1.
        - If node_attribute is a pd.Series, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float. 
        - If node_attribute is a dict, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float

    link_attribute: None, str, list, pd.Series, or dict, optional

        - If link_attribute is a string, then a link attribute dictionary is
          created using edge_attribute = wn.query_link_attribute(str)
        - If link_attribute is a list, then each link in the list is given a 
          value of 1.
        - If link_attribute is a pd.Series, then it should be in the format
          {linkid: x} where linkid is a string and x is a float. 
        - If link_attribute is a dict, then it should be in the format
          {linkid: x} where linkid is a string and x is a float.

    title: str, optional
        Plot title 

    node_size: int, optional
        Node size 

    node_range: list, optional
        Node range ([None,None] indicates autoscale)
        
    node_alpha: int, optional
        Node transparency
        
    node_cmap: matplotlib.pyplot.cm colormap or list of named colors, optional
        Node colormap 
        
    node_labels: bool, optional
        If True, the graph will include each node labelled with its name. 
        
    link_width: int, optional
        Link width

    link_range: list, optional
        Link range ([None,None] indicates autoscale)

    link_alpha: int, optional
        Link transparency
    
    link_cmap: matplotlib.pyplot.cm colormap or list of named colors, optional
        Link colormap
        
    link_labels: bool, optional
        If True, the graph will include each link labelled with its name.
        
    valve_layer: pd.Dataframe, optional
        list of valves with their associated link and node
    
    valve_criticality:
        A dictionary of valve: criticality values. Includes "Type" key for plotting.
        See valve-criticality-plotting.py
        
    add_colorbar: bool, optional
        Add colorbar

    node_colorbar_label: str, optional
        Node colorbar label
        
    link_colorbar_label: str, optional
        Link colorbar label
        
    directed: bool, optional
        If True, plot the directed graph
    
    ax: matplotlib axes object, optional
        Axes for plotting (None indicates that a new figure with a single 
        axes will be used)
        
    Returns
    -------
    nodes, edges : matplotlib objects for network nodes and edges

    Notes
    -----
    For more network draw options, see nx.draw_networkx
    """
    
    if plt is None:
        raise ImportError('matplotlib is required')

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
    add_node_colorbar = add_colorbar
    if node_attribute is not None:
        
        if isinstance(node_attribute, list):
            if node_cmap is None:
                node_cmap = ['red', 'red']
            add_node_colorbar = False
        
        if node_cmap is None:
            node_cmap = plt.cm.Spectral_r
        elif isinstance(node_cmap, list):
            if len(node_cmap) == 1:
                node_cmap = node_cmap*2
            node_cmap = custom_colormap(len(node_cmap), node_cmap)  
         
        node_attribute = _format_node_attribute(node_attribute, wn)
        nodelist,nodecolor = zip(*node_attribute.items())

    else:
        nodelist = None
        nodecolor = 'k'
    
    add_link_colorbar = add_colorbar
    if link_attribute is not None:
        
        if isinstance(link_attribute, list):
            if link_cmap is None:
                link_cmap = ['red', 'red']
            add_link_colorbar = False

        if link_cmap is None:
            link_cmap = plt.cm.Spectral_r
        elif isinstance(link_cmap, list):
            if len(link_cmap) == 1:
                link_cmap = link_cmap*2
            link_cmap = custom_colormap(len(link_cmap), link_cmap)  
            
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
        
    edge_background = nx.draw_networkx_edges(G, pos, edge_color='grey', 
                                             width=0.5, ax=ax)
    
    nodes = nx.draw_networkx_nodes(G, pos, with_labels=False, 
            nodelist=nodelist, node_color=nodecolor, node_size=node_size, 
            alpha=node_alpha, cmap=node_cmap, vmin=node_range[0], vmax = node_range[1], 
            linewidths=0, ax=ax)
    edges = nx.draw_networkx_edges(G, pos, edgelist=linklist, 
            edge_color=linkcolor, width=link_width, alpha=link_alpha, edge_cmap=link_cmap, 
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
    if add_node_colorbar and node_attribute:
        clb = plt.colorbar(nodes, shrink=0.5, pad=0, ax=ax)
        clb.ax.set_title(node_colorbar_label, fontsize=10)
    if add_link_colorbar and link_attribute:
        clb = plt.colorbar(edges, shrink=0.5, pad=0.05, ax=ax)
        clb.ax.set_title(link_colorbar_label, fontsize=10)
    ax.axis('off')
    
    if valve_layer is not None:
        if valve_criticality is not None:
            print(valve_criticality['Type'])
            # set the color scheme
            if valve_criticality['Type'] == 'valve':
                vc_temp = valve_criticality.copy()
                del vc_temp['Type']
                max_criticality = max(vc_temp.values())
            else:
                max_criticality = 100
        for valve_name, (pipe_name, node_name) in valve_layer.iterrows():
            pipe = wn.get_link(pipe_name)
            if node_name == pipe.start_node_name:
                start_node = pipe.start_node
                end_node = pipe.end_node
            elif node_name == pipe.end_node_name:
                start_node = pipe.end_node
                end_node = pipe.start_node
            else:
                print("Not valid")
                continue
            x0 = start_node.coordinates[0]
            dx = end_node.coordinates[0] - x0
            y0 = start_node.coordinates[1]
            dy = end_node.coordinates[1] - y0
            valve_coordinates = (x0 + dx * 0.1,
                                     y0 + dy * 0.1)
            if valve_criticality is not None:
                crit_value = valve_criticality[valve_name]/max_criticality
                if crit_value > 0.75:
                    color = 'r'
                if crit_value > 0.5 and crit_value <= 0.75:
                    color = 'y'
                if crit_value <= 0.5:
                    color = 'b'
                ax.scatter(valve_coordinates[0], valve_coordinates[1], s=25, c=color, marker='v')   
            else:
                ax.scatter(valve_coordinates[0], valve_coordinates[1], 15, 'r', 'v')   
    
    if filename:
        plt.savefig(filename)
        
    return nodes, edges

def plot_interactive_network(wn, node_attribute=None, node_attribute_name = 'Value', title=None,
               node_size=8, node_range=[None,None], node_cmap='Jet', node_labels=True,
               link_width=1, add_colorbar=True, reverse_colormap=False,
               figsize=[700, 450], round_ndigits=2, add_to_node_popup=None, 
               filename='plotly_network.html', auto_open=True):
    """
    Create an interactive scalable network graphic using plotly.  

    Parameters
    ----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object

    node_attribute : None, str, list, pd.Series, or dict, optional

        - If node_attribute is a string, then a node attribute dictionary is
          created using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node in the list is given a 
          value of 1.
        - If node_attribute is a pd.Series, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float.
          The time index is not used in the plot.
        - If node_attribute is a dict, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float

    node_attribute_name : str, optional 
        The node attribute name, which is used in the node popup and node legend

    title : str, optional
        Plot title

    node_size : int, optional
        Node size

    node_range : list, optional
        Node range ([None,None] indicates autoscale)

    node_cmap : palette name string, optional
        Node colormap, options include Greys, YlGnBu, Greens, YlOrRd, Bluered, 
        RdBu, Reds, Blues, Picnic, Rainbow, Portland, Jet, Hot, Blackbody, 
        Earth, Electric, Viridis
    
    node_labels: bool, optional
        If True, the graph will include each node labelled with its name and 
        attribute value.
        
    link_width : int, optional
        Link width
    
    add_colorbar : bool, optional
        Add colorbar
        
    reverse_colormap : bool, optional
        Reverse colormap
        
    figsize: list, optional
        Figure size in pixels

    round_ndigits : int, optional
        Number of digits to round node values used in the label
    
    add_to_node_popup : None or pd.DataFrame, optional
        To add additional information to the node popup, use a DataFrame with 
        node name as index and attributes as values.  Column names will be added
        to the popup along with each value for a given node.
        
    filename : string, optional
        HTML file name
    
    auto_open : bool, optional
        Open the HTML file after creation
    """
    if plotly is None:
        raise ImportError('plotly is required')
        
    # Graph
    G = wn.get_graph()
    
    # Node attribute
    if node_attribute is not None:
        if isinstance(node_attribute, list):
            node_cmap = 'Reds'
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
        line=dict(
            #colorscale=link_cmap,
            #reversescale=reverse_colormap,
            color='#888', #[], 
            width=link_width))
    for edge in G.edges():
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        edge_trace['x'] += tuple([x0, x1, None])
        edge_trace['y'] += tuple([y0, y1, None])
#        try:
#            # Add link attributes
#            link_name = G[edge[0]][edge[1]].keys()[0]
#            edge_trace['line']['color'] += tuple([pipe_attr[link_name]])
#            edge_info = 'Edge ' + str(link_name)
#            edge_trace['text'] += tuple([edge_info])
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
        marker=dict(
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
        x, y = G.nodes[node]['pos']
        node_trace['x'] += tuple([x])
        node_trace['y'] += tuple([y])
        try:
            # Add node attributes
            node_trace['marker']['color'] += tuple([node_attribute[node]])
            #node_trace['marker']['size'].append(node_size)

            # Add node labels
            if node_labels:
                node_info = wn.get_node(node).node_type + ': ' + str(node) + '<br>'+ \
                            node_attribute_name + ': ' + str(round(node_attribute[node],round_ndigits))
                if add_to_node_popup is not None:
                    if node in add_to_node_popup.index:
                        for key, val in add_to_node_popup.loc[node].iteritems():
                            node_info = node_info + '<br>' + \
                                key + ': ' + '{:.{prec}f}'.format(val, prec=round_ndigits)
                            
                node_trace['text'] += tuple([node_info])
        except:
            node_trace['marker']['color'] += tuple(['#888'])
            if node_labels:
                node_info = wn.get_node(node).node_type + ': ' + str(node)
                
                node_trace['text'] += tuple([node_info])
            #node_trace['marker']['size'] += tuple([5])
    #node_trace['marker']['colorbar']['title'] = 'Node colorbar title'    
    
    # Create figure
    data = [edge_trace, node_trace]
    layout = plotly.graph_objs.Layout(
                    title=title,
                    titlefont=dict(size=16),
                    showlegend=False, 
                    width=figsize[0],
                    height=figsize[1],
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    
    fig = plotly.graph_objs.Figure(data=data,layout=layout)

    if filename:
        plotly.offline.plot(fig, filename=filename, auto_open=auto_open)  
    else:
        plotly.offline.plot(fig, auto_open=auto_open)  

def plot_leaflet_network(wn, node_attribute=None, link_attribute=None, 
               node_attribute_name = 'Value', 
               link_attribute_name = 'Value',
               node_size=2, node_range=[None,None], 
               node_cmap=['cornflowerblue', 'forestgreen', 'gold', 'firebrick'], 
               node_cmap_bins = 'cut', node_labels=True,
               link_width=2, link_range=[None,None], 
               link_cmap=['cornflowerblue', 'forestgreen', 'gold', 'firebrick'], 
               link_cmap_bins='cut', link_labels=True,
               blank_background=False, add_legend=False, round_ndigits=2, zoom_start=13, 
               add_to_node_popup=None, add_to_link_popup=None,
               filename='leaflet_network.html'):
    """
    Create an interactive scalable network graphic on a Leaflet map using folium.  

    Parameters
    ----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object

    node_attribute : None, str, list, pd.Series, or dict, optional

        - If node_attribute is a string, then a node attribute dictionary is
          created using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node in the list is given a 
          value of 1.
        - If node_attribute is a pd.Series, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float. 
        - If node_attribute is a dict, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float

    link_attribute : None, str, list, pd.Series, or dict, optional

        - If link_attribute is a string, then a link attribute dictionary is
          created using edge_attribute = wn.query_link_attribute(str)
        - If link_attribute is a list, then each link in the list is given a 
          value of 1.
        - If link_attribute is a pd.Series, then it should be in the format
          {linkid: x} where linkid is a string and x is a float. 
        - If link_attribute is a dict, then it should be in the format
          {linkid: x} where linkid is a string and x is a float.

    node_attribute_name : str, optional 
        The node attribute name, which is used in the node popup and node legend
        
    link_attribute_name : str, optional 
        The link attribute name, which is used in the link popup and link legend
        
    node_size : int, optional
        Node size 

    node_range : list, optional
        Node range ([None,None] indicates autoscale)

    node_cmap : list of color names, optional
        Node colors 
    
    node_cmap_bins: string, optional
        Node color bins, 'cut' or 'qcut'
    
    node_labels: bool, optional
        If True, the graph will include each node labelled with its name. 
        
    link_width : int, optional
        Link width

    link_range : list, optional
        Link range ([None,None] indicates autoscale)

    link_cmap : list of color names, optional
        Link colors
    
    link_cmap_bins: string, optional
        Link color bins, 'cut' or 'qcut'
        
    link_labels: bool, optional
        If True, the graph will include each link labelled with its name. 
    
    blank_background: bool, optional
        If True, the leaflet plot will have a blank background instead of 
        a geogaphical map. 
    
    add_legend: bool, optional
         Add a legend to the map
    
    round_ndigits : int, optional
        Rounds digits in the popup
        
    zoom_start : int, optional
        Zoom start used to set initial scale of the map
    
    add_to_node_popup : None or pd.DataFrame, optional
        To add additional information to the node popup, use a DataFrame with 
        node name as index and attributes as values.  Column names will be added
        to the popup along with each value for a given node.
        
    add_to_link_popup : None or pd.DataFrame, optional
        To add additional information to the link popup, use a DataFrame with 
        link name as index and attributes as values.  Column names will be added
        to the popup along with each value for a given link.
        
    filename : str, optional
        Filename used to save the map
    """
    
    if folium is None:
        raise ImportError('folium is required')
    
    # format node attributes for plotting
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
    
    # format link attributes for plotting
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

    # use node locations to center the map
    G = wn.get_graph()
    pos = nx.get_node_attributes(G,'pos')
    pos_pd = pd.DataFrame(pos)
    map_center = pos_pd.mean(axis=1)
             
    if blank_background is True:    
    # add a white geojson blank background and re-center the map   
        rel_location = pos_pd.copy()
        for node in rel_location.columns:
            rel_location[node] = rel_location[node] - map_center
        max_dist = max((rel_location**2).sum(axis=0)**0.5)
        corner_dist = (2*max_dist**2)**0.5
        wn.add_junction('dummy_node1', coordinates=(map_center[0]-corner_dist,
                                                    map_center[1]-corner_dist)
                        )
        wn.add_junction('dummy_node2', coordinates=(map_center[0]+corner_dist,
                                                    map_center[1]+corner_dist)
                        )
        longlat_map = {'dummy_node1': (-100.125, 39.825),
                       'dummy_node2': (-99.825, 40.125)}
        wn = convert_node_coordinates_to_longlat(wn, longlat_map)
        wn.remove_node('dummy_node1')
        wn.remove_node('dummy_node2')
        G = wn.get_graph()
        new_pos = nx.get_node_attributes(G,'pos')
        new_pos_pd = pd.DataFrame(new_pos)
        new_map_center = new_pos_pd.mean(axis=1)
        map_location = [new_map_center.iloc[1], new_map_center.iloc[0]]
        m = folium.Map(location=map_location, zoom_start=12, min_zoom=12, 
                       tiles='cartodbpositron')
        blank_geojson = {"type":"Feature",
                         "geometry":{"type":"Polygon",
                                           "coordinates":[[[-100.25,39.7],
                                                           [-100.25,40.2],
                                                           [-99.7,40.2],
                                                           [-99.7,39.7],
                                                           [-100.25,39.7]]]}}
        style_function = lambda x: {'fill-color': '#fff', 
                                    'color': '#fff', 'fillOpacity': 1}
        folium.GeoJson(blank_geojson, style_function=style_function, 
                       name='Background').add_to(m)
    else:
        # map node locations to map locations
        map_location = [map_center.iloc[1], map_center.iloc[0]]
        m = folium.Map(location=map_location, zoom_start=zoom_start, 
                       tiles='cartodbpositron')    
    
    
    
    # Node popup
    node_popup = {k: '' for k in wn.node_name_list}
    if node_labels:
        for name, node in wn.nodes():
            node_popup[name] = node.node_type + ': ' + name
            if node_attribute is not None:
                if name in node_attribute.index:
                    node_popup[name] = node_popup[name] + '<br>' + \
                        node_attribute_name + ': ' + '{:.{prec}f}'.format(node_attribute[name], prec=round_ndigits)
            if add_to_node_popup is not None:
                if name in add_to_node_popup.index:
                    for key, val in add_to_node_popup.loc[name].iteritems():
                        node_popup[name] = node_popup[name] + '<br>' + \
                            key + ': ' + '{:.{prec}f}'.format(val, prec=round_ndigits)
                 
    # Link popup
    link_popup = {k: '' for k in wn.link_name_list}
    if link_labels:
        for name, link in wn.links():
            link_popup[name] = link.link_type + ': ' + name
            if link_attribute is not None:
                if name in link_attribute.index:
                    link_popup[name] = link_popup[name] + '<br>' + \
                        link_attribute_name + ': ' + '{:.{prec}f}'.format(link_attribute[name], prec=round_ndigits)
            if add_to_link_popup is not None:
                if name in add_to_link_popup.index:
                    for key, val in add_to_link_popup.loc[name].iteritems():
                        link_popup[name] = link_popup[name] + '<br>' + \
                            key + ': ' + '{:.{prec}f}'.format(val, prec=round_ndigits)

    # Add pipes, pumps, and valves as separate featuregroups to the network
    if link_width > 0:
        # add pipes
        pipe_featuregroup = folium.map.FeatureGroup(name='Pipes')
        for name, link in wn.pipes():            
            start_loc = (link.start_node.coordinates[1], link.start_node.coordinates[0])
            end_loc = (link.end_node.coordinates[1], link.end_node.coordinates[0])
            weight = link_width
            color='black'
            if link_labels:
                popup = link_popup[name]
            else:
                popup = None
            
            if link_attribute is not None:
                if name in link_attribute.index:
                    color = link_colors[name]
                else:
                    weight = 1.5
            
            folium.PolyLine([start_loc, end_loc], popup=popup, color=color, 
                            weight=weight, name=name, opacity=0.7
                            ).add_to(pipe_featuregroup)
        pipe_featuregroup.add_to(m)     
        # # 4/15/20 - search feature not yet available for featuregroups
        # pipe_search = folium.plugins.Search(layer=pipe_featuregroup, 
        #                 geom_type='Line', placeholder="Search for a pipe", 
        #                 collapsed=False, search_label='name', 
        #                 position='topright').add_to(m)
        
        # add pumps
        pump_featuregroup = folium.map.FeatureGroup(name='Pumps')
        for name, link in wn.pumps():            
            start_loc = (link.start_node.coordinates[1], link.start_node.coordinates[0])
            end_loc = (link.end_node.coordinates[1], link.end_node.coordinates[0])
            weight = link_width
            color='black'
            if link_labels:
                popup = link_popup[name]
            else:
                popup = None
            
            if link_attribute is not None:
                if name in link_attribute.index:
                    color = link_colors[name]
                else:
                    weight = 1.5
            
            folium.PolyLine([start_loc, end_loc], popup=popup, color=color, 
                            weight=weight, name=name, opacity=0.7
                            ).add_to(pump_featuregroup)
        pump_featuregroup.add_to(m) 
        # # 4/15/20 - search feature not yet available for featuregroups
        # pump_search = folium.plugins.Search(layer=pump_featuregroup, 
        #                 geom_type='Line', placeholder="Search for a pump", 
        #                 collapsed=False, search_label='name', 
        #                 position='topright').add_to(m)
        
        # add valves
        valve_featuregroup = folium.map.FeatureGroup(name='Valves')
        for name, link in wn.valves():            
            start_loc = (link.start_node.coordinates[1], link.start_node.coordinates[0])
            end_loc = (link.end_node.coordinates[1], link.end_node.coordinates[0])
            weight = link_width
            color='black'
            if link_labels:
                popup = link_popup[name]
            else:
                popup = None
            
            if link_attribute is not None:
                if name in link_attribute.index:
                    color = link_colors[name]
                else:
                    weight = 1.5
            
            folium.PolyLine([start_loc, end_loc], popup=popup, color=color, 
                            weight=weight, name=name, opacity=0.7
                            ).add_to(valve_featuregroup)
        valve_featuregroup.add_to(m)
        # # 4/15/20 - search feature not yet available for featuregroups        
        # valve_search = folium.plugins.Search(layer=valve_featuregroup, 
        #                 geom_type='Line', placeholder="Search for a valve", 
        #                 collapsed=False, search_label='name', 
        #                 position='topright').add_to(m)
            
    # Add junctions, reservoirs, and tanks as separate featuregroups to the network            
    if node_size > 0:
        # add junctions
        junction_featuregroup = folium.map.FeatureGroup(name='Junctions')
        for name, node in wn.junctions():
            loc = (node.coordinates[1], node.coordinates[0])
            radius = node_size
            color = 'black'
            if node_labels:
                popup = node_popup[name]
            else:
                popup = None
                    
            if node_attribute is not None:
                if name in node_attribute.index:
                    color = node_colors[name]
                else:
                    radius = 0.1
            
            folium.CircleMarker(loc, popup=popup, color=color, fill=True, 
                                fill_color=color, radius=radius, 
                                fill_opacity=0.7, opacity=0.7, label=node
                                ).add_to(junction_featuregroup)
        junction_featuregroup.add_to(m)
        # # 4/15/20 - search feature not yet available for featuregroups
        # junction_search = folium.plugins.Search(layer=junction_featuregroup, 
        #                 geom_type='point', placeholder="Search for a junction", 
        #                 collapsed=False, search_label='label',
        #                 position='topright').add_to(m)
        
        # add reservoirs
        reservoir_featuregroup = folium.map.FeatureGroup(name='Reservoirs')
        for name, node in wn.reservoirs():
            loc = (node.coordinates[1], node.coordinates[0])
            radius = node_size
            color = 'black'
            if node_labels:
                popup = node_popup[name]
            else:
                popup = None
            if node_attribute is not None:
                if name in node_attribute.index:
                    color = node_colors[name]
                else:
                    radius = 0.1
            folium.CircleMarker(loc, popup=popup, color=color, fill=True, 
                                fill_color=color, radius=radius, 
                                fill_opacity=0.7, opacity=0.7, label=node
                                ).add_to(reservoir_featuregroup)
        reservoir_featuregroup.add_to(m)
        # # 4/15/20 - search feature not yet available for featuregroups
        # reservoir_search = folium.plugins.Search(layer=reservoir_featuregroup, 
        #                 geom_type='point', placeholder="Search for a reservoir", 
        #                 collapsed=False, search_label='label',
        #                 position='topright').add_to(m)
        
        # add tanks
        tank_featuregroup = folium.map.FeatureGroup(name='Tanks')
        for name, node in wn.tanks():
            loc = (node.coordinates[1], node.coordinates[0])
            radius = node_size
            color = 'black'
            if node_labels:
                popup = node_popup[name]
            else:
                popup = None
                    
            if node_attribute is not None:
                if name in node_attribute.index:
                    color = node_colors[name]
                else:
                    radius = 0.1
            folium.CircleMarker(loc, popup=popup, color=color, fill=True, 
                                fill_color=color, radius=radius, 
                                fill_opacity=0.7, opacity=0.7, label=node
                                ).add_to(tank_featuregroup)            
        
        tank_featuregroup.add_to(m)
        # # 4/15/20 - search feature not yet available for featuregroups
        # tank_search = folium.plugins.Search(layer=tank_featuregroup, 
        #                 geom_type='point', placeholder="Search for a tank", 
        #                 collapsed=False, search_label='label',
        #                 position='topright').add_to(m)
        
    if (add_legend) & ((len(node_cmap) >= 1) or (len(link_cmap) >= 1)):
        if node_attribute is not None:  #Produce node legend
            height = 50+len(node_cmap)*20 + (int(len(node_attribute_name)/20) + 1)*20
            node_legend_html = """<div style="position: fixed; 
        bottom: 50px; left: 50px; width: 150px; height: """+str(height)+"""px; 
        background-color:white;z-index:9999; font-size:14px; "><br>
            <b><P ALIGN=CENTER>""" + "Node Legend: " + node_attribute_name + """</b> </P>"""
            for color, val in zip(node_cmap, node_bins[0:-1]):
                val = '{:.{prec}f}'.format(val, prec=round_ndigits)
                node_legend_html += """
                &emsp;<i class="fa fa-circle fa-1x" 
                style="color:"""+ color +""" "></i> >= """+ val +""" <br>"""
            node_legend_html += """</div>"""
            m.get_root().html.add_child(folium.Element(node_legend_html))
 			
        if link_attribute is not None:   #Produce link legend
            height = 50+len(link_cmap)*20 + (int(len(link_attribute_name)/20) + 1)*20
            link_legend_html = """<div style="position: fixed; 
 			bottom: 50px; left: 250px; width: 150px; height: """+str(height)+"""px; 
 			background-color:white;z-index:9999; font-size:14px; "><br>
            <b><P ALIGN=CENTER>""" + "Link Legend: " + link_attribute_name + """</b> </P>"""
            for color, val in zip(link_cmap, link_bins[0:-1]):
                val = '{:.{prec}f}'.format(val, prec=round_ndigits)
                link_legend_html += """
                &emsp;<i class="fa fa-minus fa-1x" 
                style="color:"""+ color +""" "></i> >= """+ val +""" <br>"""
            link_legend_html += """</div>"""
            m.get_root().html.add_child(folium.Element(link_legend_html))
    

    #if add_longlat_popup:
    #    m.add_child(folium.LatLngPopup())

    folium.LayerControl().add_to(m)
    
    m.save(filename)
 
def network_animation(wn, node_attribute=None, link_attribute=None, title=None,
               node_size=20, node_range=[None,None], node_alpha=1, node_cmap=None, node_labels=False,
               link_width=1, link_range=[None,None], link_alpha=1, link_cmap=None, link_labels=False,
               add_colorbar=True, directed=False, ax=None, repeat=True):
    """
    Create a network animation

    Parameters
    ----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object

    node_attribute : pd.DataFrame, optional
        Node attributes stored in a pandas DataFrames, where the index is 
        time and columns are the node name 

    link_attribute : pd.DataFrame, optional
        Link attributes stored in a pandas DataFrames, where the index is 
        time and columns are the link name 

    title : str, optional
        Plot title 

    node_size : int, optional
        Node size 

    node_range : list, optional
        Node range ([None,None] indicates autoscale)
        
    node_alpha : int, optional
        Node transparency
        
    node_cmap : matplotlib.pyplot.cm colormap or list of named colors, optional
        Node colormap 
        
    node_labels: bool, optional
        If True, the graph will include each node labelled with its name. 
        
    link_width : int, optional
        Link width

    link_range : list, optional
        Link range ([None,None] indicates autoscale)

    link_alpha : int, optional
        Link transparency
    
    link_cmap : matplotlib.pyplot.cm colormap or list of named colors, optional
        Link colormap
        
    link_labels: bool, optional
        If True, the graph will include each link labelled with its name. 
        
    add_colorbar : bool, optional
        Add colorbar

    directed : bool, optional
        If True, plot the directed graph
    
    repeat : bool, optional
        If True, the animation will repeat
        
    Returns
    -------
    matplotlib animation
    """
    
    if node_attribute is not None:
        node_index = node_attribute.index
        initial_node_values = node_attribute.iloc[0, :]
        if node_range[0] is None:
            node_range[0] = node_attribute.min().min()
        if node_range[1] is None:
            node_range[1] = node_attribute.max().max()
    else:
        node_index = None
        initial_node_values = None
        
    if link_attribute is not None:
        link_index = link_attribute.index
        initial_link_values = link_attribute.iloc[0, :]
        if link_range[0] is None:
            link_range[0] = link_attribute.min().min()
        if link_range[1] is None:
            link_range[1] = link_attribute.max().max()
    else:
        link_index = None
        initial_link_values = None
    
    if (node_index is not None) & (link_index is not None):
        if len(node_index.symmetric_difference(link_index)) > 0:
            print('Node attribute index does not equal link attribute index')
            return
        index = node_index
    elif node_index is not None:
        index = node_index
    elif link_index is not None:
        index = link_index
    else:
        print('Node attributes or link attributes must be included')
        return
    
    if ax is None: # create a new figure
        fig = plt.figure(facecolor='w', edgecolor='k')
        ax = plt.gca()
            
    if title is not None:
        title_name = title + ', ', str(index[0])
    else:
        title_name = '0'
    
    nodes, edges = plot_network(wn, node_attribute=initial_node_values, link_attribute=initial_link_values, title=title_name,
               node_size=node_size, node_range=node_range, node_alpha=node_alpha, node_cmap=node_cmap, node_labels=node_labels,
               link_width=link_width, link_range=link_range, link_alpha=link_alpha, link_cmap=link_cmap, link_labels=link_labels,
               add_colorbar=add_colorbar, directed=directed, ax=ax)
        
    def update(n):
        if node_attribute is not None:
            node_values = node_attribute.iloc[n, :]
        else:
            node_values = None
        
        if link_attribute is not None:
            link_values = link_attribute.iloc[n, :]
        else:
            link_values = None
            
        if title is not None:
            title_name = title + ', ' + str(index[n])
        else:
            title_name = str(n)
        
        fig.clf()  
        ax = plt.gca()
        
        nodes, edges = plot_network(wn, node_attribute=node_values, link_attribute=link_values, title=title_name,
               node_size=node_size, node_range=node_range, node_alpha=node_alpha, node_cmap=node_cmap, node_labels=node_labels,
               link_width=link_width, link_range=link_range, link_alpha=link_alpha, link_cmap=link_cmap, link_labels=link_labels,
               add_colorbar=add_colorbar, directed=directed, ax=ax)
        
        return nodes, edges
    
    anim = animation.FuncAnimation(fig, update, interval=50, frames=len(index), blit=False, repeat=repeat)
    
    return anim

def wn_to_geojson(wn, to_file=True):
    """
    Write a minimal geojson representation of the Water Network.

    Parameters
    ----------
    wn: wntr WaterNetworkModel object
        The network to be make the geojson from
    to_file: Boolean, default=False
        To save the geojson representation as a file in the directory of the
        inp file
    Returns
    -------
    wn_geojson: dict in geojson format
        geojson spatial representation of the water network
    """
    if json is None:
        raise ImportError('json is required')
    inp_path = os.path.abspath(wn.name)
    # Translate the nodes to geojson.
    wn_geojson = {"type": "FeatureColllection",
                  "features": []
                  }
    for name, node in wn.nodes():
        feature = {"type": "Feature",
                   "geometry": {"type": "Point",
                                "coordinates": list(node.coordinates)
                                },
                   "id": name,
                   "properties": {"ID": name,
                                  }
                   }
        if node.node_type == 'Junction':
            feature['properties']["Base Demand (gpm)"] = node.base_demand/FlowUnits.GPM.factor
        else:
            feature['properties']["Base Demand (gpm)"] = node.node_type
        wn_geojson["features"].append(feature)
    # Translate the links to geojson.
    for name, link in wn.links():
        link = wn.get_link(link)
        start = list(link.start_node.coordinates)
        end = list(link.end_node.coordinates)
        feature = {"type": "Feature",
                   "geometry": {"type": "LineString",
                                "coordinates": [start, end]
                                },
                   "id": name,
                   "properties": {"ID": name
                                  }
                   }
        link_type = link.link_type
        if link_type == 'Pump':
            feature['properties']["Pipe Diameter (in)"] = "Pump"
        else:
            feature['properties']["Pipe Diameter (in)"] = round(link.diameter * 39.3701)
        wn_geojson["features"].append(feature)
    if to_file:
        # Write out the network to the file.
        output_file = inp_path.split('.inp')[0] + '.json'
        with open(output_file, 'w') as fp:
            json.dump(wn_geojson, fp)
    return wn_geojson