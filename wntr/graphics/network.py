"""
The wntr.graphics.network module includes methods plot the
water network model.
"""
import logging
import math
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.path as mpath
from matplotlib import animation
import matplotlib as mpl
import numpy as np

try:
    import plotly
except:
    plotly = None
try:
    import folium
except:
    folium = None
    
from wntr.graphics.color import custom_colormap

logger = logging.getLogger(__name__)


arrow_verts = [
    (0.0, 0.0),
    (0.5, 0.5),
    (0.5, -0.5),
    (0.0, 0.0),
]

arrow_marker = mpath.Path(arrow_verts)

def _get_angle(line, loc=0.5):
    # calculate orientation angle
    p1 = line.interpolate(loc-0.01, normalized=True)
    p2 = line.interpolate(loc+0.01, normalized=True)
    angle = math.atan2(p2.y-p1.y, p2.x - p1.x) # radians
    angle = math.degrees(angle)
    return angle

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

def plot_network(
    wn, node_attribute=None, link_attribute=None, title=None,
    node_size=20, node_range=None, node_alpha=1, node_cmap=None, node_labels=False,
    link_width=1, link_range=None, link_alpha=1, link_cmap=None, link_labels=False,
    add_colorbar=True, node_colorbar_label=None, link_colorbar_label=None, 
    directed=False, legend=False, ax=None, show_plot=True, filename=None):
    """
    Plot network graphic
	
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
		  
    title: str, optional
        Plot title 

    node_size: int, optional
        Node size 

    node_range: list, optional
        Node color range ([None,None] indicates autoscale)
        
    node_alpha: int, optional
        Node transparency
        
    node_cmap: matplotlib.pyplot.cm colormap or list of named colors, optional
        Node colormap 
        
    node_labels: bool, optional
        If True, the graph will include each node labelled with its name. 
        
    link_width: int, optional
        Link width
		
    link_range : list, optional
        Link color range ([None,None] indicates autoscale)
		
    link_alpha : int, optional
        Link transparency
    
    link_cmap: matplotlib.pyplot.cm colormap or list of named colors, optional
        Link colormap
        
    link_labels: bool, optional
        If True, the graph will include each link labelled with its name.
        
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

    show_plot: bool, optional
        If True, show plot with plt.show()
    
    filename : str, optional
        Filename used to save the figure
        
    Returns
    -------
    ax : matplotlib axes object  
    """
    if ax is None: # create a new figure
        plt.figure(facecolor='w', edgecolor='k')
        ax = plt.gca()
        
    if title is not None:
        ax.set_title(title)
    
    aspect = "equal"
    
    tank_marker = "D"
    reservoir_marker = "s"
    
    if link_cmap is None:
        link_cmap = plt.get_cmap('Spectral_r')
    if node_cmap is None:
        node_cmap = plt.get_cmap('Spectral_r')
        
    if link_range is None:
        link_range = (None, None)
    if node_range is None:
        node_range = (None, None)
    
    # use attribute name if no other label is provided
    if node_colorbar_label is None and isinstance(node_attribute, str):
        node_colorbar_label = node_attribute
    if link_colorbar_label is None and isinstance(link_attribute, str):
        link_colorbar_label = link_attribute 
        
    wn_gis = wn.to_gis()
    # add node_type so that node assets can be plotted separately
    wn_gis.junctions["node_type"] = "Junction"
    wn_gis.tanks["node_type"] = "Tank"
    wn_gis.reservoirs["node_type"] = "Reservoir"
    link_gdf = pd.concat((wn_gis.pipes, wn_gis.pumps, wn_gis.valves))
    node_gdf = pd.concat((wn_gis.junctions, wn_gis.tanks, wn_gis.reservoirs))
    
    # Node attribute
    node_kwds = {}
    node_cbar = add_colorbar
    if node_attribute is not None:
        node_gdf["_attribute"] = _format_node_attribute(node_attribute, wn)
        node_kwds["column"] = "_attribute"
        
        # handle cbar/cmap
        if isinstance(node_attribute, list):
            node_kwds["cmap"] = custom_colormap(2,["red", "red"])
            node_cbar = False
        elif isinstance(node_attribute, (dict, pd.Series, str)):
            node_kwds["cmap"] = node_cmap
            
            # manually extract min/max if no range is given
            node_attribute_values = node_gdf[node_kwds["column"]]
            if node_range[0] is None:
                node_kwds["vmin"] = np.nanmin(node_attribute_values)
            else:
                node_kwds["vmin"] = node_range[0]
            if node_range[1] is None:
                node_kwds["vmax"] = np.nanmax(node_attribute_values)
            else:
                node_kwds["vmax"] = node_range[1]
        else:
            raise TypeError("attribute must be dict, Series, list, or str")
    else:
        node_kwds["color"] = "black"
        node_cbar = False
        
    node_kwds["alpha"] = node_alpha
    node_kwds["markersize"] = node_size
    
    node_cbar_kwds = {}
    node_cbar_kwds["shrink"] = 0.5
    node_cbar_kwds["pad"] = 0.0
    node_cbar_kwds["alpha"] = node_alpha
    node_cbar_kwds["label"] = node_colorbar_label
    
    # Link attribute
    link_kwds = {}
    link_cbar = add_colorbar
    if link_attribute is not None:
        link_gdf["_attribute"] = pd.Series(_format_link_attribute(link_attribute, wn))
        link_kwds["column"] = "_attribute"
        
        # handle cbar/cmap
        if isinstance(link_attribute, list):
            link_kwds["cmap"] = custom_colormap(2,["red", "red"])
            link_cbar = False
        elif isinstance(link_attribute, (dict, pd.Series, str)):
            link_kwds["cmap"] = link_cmap
            
            # manually extract min/max if no range is given
            link_attribute_values = link_gdf[link_kwds["column"]]
            if link_range[0] is None:
                link_kwds["vmin"] = np.nanmin(link_attribute_values)
            else:
                link_kwds["vmin"] = link_range[0]
            if link_range[1] is None:
                link_kwds["vmax"] = np.nanmax(link_attribute_values)
            else:
                link_kwds["vmax"] = link_range[1]
        else:
            raise TypeError("attribute must be dict, Series, list, or str")
    else:
        link_kwds["color"] = "black"
        link_cbar = False
    
    link_kwds["linewidth"] = link_width
    link_kwds["alpha"] = link_alpha
    
    background_link_kwds = {}
    background_link_kwds["color"] = "grey"
    background_link_kwds["linewidth"] = link_width / 2
    background_link_kwds["alpha"] = link_alpha
    
    link_cbar_kwds = {}
    link_cbar_kwds["shrink"] = 0.5
    link_cbar_kwds["pad"] = 0.05
    link_cbar_kwds["label"] = link_colorbar_label
    link_cbar_kwds["alpha"] = link_alpha
    
    missing_node_kwds={"color": "black"}
    missing_link_kwds={"color": "black"}

    # plot nodes - each type is plotted separately to allow for different marker types
    node_gdf[node_gdf.node_type == "Junction"].plot(
        ax=ax, aspect=aspect, zorder=3, legend=False, label="Junction", missing_kwds=missing_node_kwds, **node_kwds)
    
    node_kwds["markersize"] = node_size * 2.0
    node_gdf[node_gdf.node_type == "Tank"].plot(
        ax=ax, aspect=aspect, zorder=4, marker=tank_marker, legend=False, label="Tank", missing_kwds=missing_node_kwds, **node_kwds)
    
    node_kwds["markersize"] = node_size * 3.0
    node_gdf[node_gdf.node_type == "Reservoir"].plot(
        ax=ax, aspect=aspect, zorder=5, marker=reservoir_marker, legend=False, label="Reservoir", missing_kwds=missing_node_kwds,**node_kwds)
    
    if node_cbar:
        sm = mpl.cm.ScalarMappable(cmap=node_kwds["cmap"])
        sm.set_clim(node_kwds["vmin"], node_kwds["vmax"])

        node_cbar = ax.figure.colorbar(sm, ax=ax, **node_cbar_kwds)
    
    # plot links
    # background
    link_gdf.plot(
        ax=ax, aspect=aspect, zorder=1, legend=False, **background_link_kwds)
    
    # main plot
    link_gdf.plot(
        ax=ax, aspect=aspect, zorder=2, legend=False, missing_kwds=missing_link_kwds, **link_kwds)
    
    if link_cbar:
        sm = mpl.cm.ScalarMappable(cmap=link_kwds["cmap"])
        sm.set_clim(link_kwds["vmin"], link_kwds["vmax"])

        link_cbar = ax.figure.colorbar(sm, ax=ax, **link_cbar_kwds)

    if node_labels:
        for x, y, label in zip(node_gdf.geometry.x, node_gdf.geometry.y, node_gdf.index):
            ax.annotate(label, xy=(x, y))#, xytext=(3, 3),)# textcoords="offset points")
            
    if link_labels:
        midpoints = link_gdf.geometry.apply(lambda x: x.interpolate(0.5, normalized=True))
        for x, y, label in zip(midpoints.geometry.x, midpoints.geometry.y, link_gdf.index):
            ax.annotate(label, xy=(x, y))#, xytext=(3, 3),)# textcoords="offset points") 
            
    if directed:
        link_gdf["_midpoint"] = link_gdf.geometry.interpolate(0.5, normalized=True)
        link_gdf["_angle"] = link_gdf.apply(lambda row: _get_angle(row.geometry), axis=1)
        for idx , row in link_gdf.iterrows():
            x,y = row["_midpoint"].x, row["_midpoint"].y
            angle = row["_angle"]
            ax.scatter(x,y, color="black", s=50, marker=(3,0, angle-90))

    if legend:
        handles, labels = ax.get_legend_handles_labels()
        leg = ax.legend(handles, labels, loc='upper right', title="Legend")
    
    ax.axis('off')
    
    if filename:
        plt.savefig(filename)
    
    if show_plot is True:
        plt.show(block=False)
    
    return ax

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
    G = wn.to_graph()
    
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
               add_legend=False, round_ndigits=2, zoom_start=13, 
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
        
    G = wn.to_graph()
    pos = nx.get_node_attributes(G,'pos')
    center = pd.DataFrame(pos).mean(axis=1)
    
    m = folium.Map(location=[center.iloc[1], center.iloc[0]], zoom_start=zoom_start, 
                   tiles='cartodbpositron')
    #folium.TileLayer('cartodbpositron').add_to(m)
    
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
                            
    if node_size > 0:
        for name, node in wn.nodes():
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
                                fill_color=color, radius=radius, fill_opacity=0.7, opacity=0.7).add_to(m)
            
    if link_width > 0:
        for name, link in wn.links():            
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
                            weight=weight, opacity=0.7).add_to(m)
    
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
    
    #plugins.Search(points, search_zoom=20, ).add_to(m)
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
    
    ax = plot_network(wn, node_attribute=initial_node_values, link_attribute=initial_link_values, title=title_name,
               node_size=node_size, node_range=node_range, node_alpha=node_alpha, node_cmap=node_cmap, node_labels=node_labels,
               link_width=link_width, link_range=link_range, link_alpha=link_alpha, link_cmap=link_cmap, link_labels=link_labels,
               add_colorbar=add_colorbar, directed=directed, ax=ax, show_plot=False)
        
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
        
        ax = plot_network(wn, node_attribute=node_values, link_attribute=link_values, title=title_name,
               node_size=node_size, node_range=node_range, node_alpha=node_alpha, node_cmap=node_cmap, node_labels=node_labels,
               link_width=link_width, link_range=link_range, link_alpha=link_alpha, link_cmap=link_cmap, link_labels=link_labels,
               add_colorbar=add_colorbar, directed=directed, ax=ax, show_plot=False)
        
        return ax
    
    anim = animation.FuncAnimation(fig, update, interval=50, frames=len(index), blit=False, repeat=repeat)
    
    return anim