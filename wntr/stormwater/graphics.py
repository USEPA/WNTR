"""
The wntr.stormwater.graphics module contains methods to 
generate graphics.
"""
import logging
import networkx as nx
import matplotlib.pylab as plt
import pandas as pd

try:
    from shapely.geometry import LineString, Point, Polygon
    has_shapely = True
except ModuleNotFoundError:
    has_shapely = False

try:
    import geopandas as gpd
    has_geopandas = True
except ModuleNotFoundError:
    has_geopandas = False

from wntr.graphics.network import plot_network as _plot_network
from wntr.graphics.curve import plot_fragility_curve
from wntr.graphics.color import custom_colormap, random_colormap

logger = logging.getLogger(__name__)


def plot_network(swn, node_attribute=None, link_attribute=None, subcatchment_attribute=None, title=None,
                node_size=20, node_range=[None,None], node_alpha=1, node_cmap=None, node_labels=False,
                link_width=1, link_range=[None,None], link_alpha=1, link_cmap=None, link_labels=False,
                subcatchment_width=1, subcatchment_range=[None,None], subcatchment_alpha=0.5, subcatchment_cmap=None,
                add_colorbar=True, node_colorbar_label='Node', link_colorbar_label='Link', 
                directed=False, ax=None, filename=None):
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
    
    subcatchment_attribute : None, str
        Name of the subcatchment attribute to plot (only supports string, 
        which must be a column name in swn.subcatchments)
    
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
    
    subcatchment_width: int, optional
        Subcatchment width
    
    subcatchment_range: list, optional
        Subcatchment color range ([None,None] indicates autoscale)
    
    subcatchment_alpha : int, optional
        Subcatchment transparency
    
    subcatchment_cmap: matplotlib.pyplot.cm colormap or list of named colors, optional
        Subcatchment colormap
    
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
    
    if ax is None:  # create a new figure
        plt.figure(facecolor="w", edgecolor="k")
        ax = plt.gca()
    
    if isinstance(node_attribute, str):
        node_attribute = swn.nodes[node_attribute]
    if isinstance(link_attribute, str):
        link_attribute = swn.links[link_attribute]
    
    if (swn.subcatchments.shape[0] > 0) and (swn.polygons.shape[0] > 0):
        if not has_shapely or not has_geopandas:
            raise ModuleNotFoundError('shapley and geopandas are required')
        geom = {}
        for subcatch_name in swn.subcatchments.index:
            vertices = swn.polygons.loc[swn.polygons.index == subcatch_name,:].values
            geom[subcatch_name] = Polygon(vertices)
        geom = pd.Series(geom)
        subcatchments = gpd.GeoDataFrame(swn.subcatchments, geometry=geom)
        
        if subcatchment_attribute is None:
            subcatchments.boundary.plot(color='darkblue', 
                                        linewidth=subcatchment_width, 
                                        vmin=subcatchment_range[0], 
                                        vmax=subcatchment_range[1],
                                        alpha=subcatchment_alpha, 
                                        cmap=subcatchment_cmap,
                                        ax=ax)
        else:
            subcatchments.plot(column=subcatchment_attribute, 
                               linewidth=subcatchment_width, 
                               vmin=subcatchment_range[0], 
                               vmax=subcatchment_range[1],
                               alpha=subcatchment_alpha, 
                               cmap=subcatchment_cmap,
                               ax=ax)
            
    _plot_network(swn, node_attribute, link_attribute, title, 
                   node_size, node_range, node_alpha, node_cmap, node_labels,
                   link_width, link_range, link_alpha, link_cmap, link_labels,
                   add_colorbar, node_colorbar_label, link_colorbar_label, 
                   directed, ax=ax, filename=filename)
