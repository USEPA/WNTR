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

# def plot_network_directed(swn, attribute):
#     G = swn.to_graph()
#     G_attr = swn.to_graph(link_weight=attribute, modify_direction=True)
    
#     plt.figure(facecolor='w', edgecolor='k')
#     ax = plt.gca()
#     pos = nx.get_node_attributes(G, 'pos')
#     nx.draw_networkx_edges(G, pos, edge_color='grey', width=0.5, ax=ax)
#     nx.draw_networkx(G_attr, pos=pos, with_labels=False, node_size=3, ax=ax)

def plot_network(swn, node_attribute=None, link_attribute=None, subcatchment_attribute=None, title=None,
                node_size=20, node_range=[None,None], node_alpha=1, node_cmap=None, node_labels=False,
                link_width=1, link_range=[None,None], link_alpha=1, link_cmap=None, link_labels=False,
                add_colorbar=True, node_colorbar_label='Node', link_colorbar_label='Link', 
                directed=False, ax=None, filename=None):
    
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
            subcatchments.boundary.plot(color='darkblue', linewidth=0.5, alpha=0.5, ax=ax)
        else:
            subcatchments.plot(column=subcatchment_attribute, linewidth=0.5, alpha=0.5, ax=ax)
            
    _plot_network(swn, node_attribute, link_attribute, title, 
                   node_size, node_range, node_alpha, node_cmap, node_labels,
                   link_width, link_range, link_alpha, link_cmap, link_labels,
                   add_colorbar, node_colorbar_label, link_colorbar_label, 
                   directed, ax=ax, filename=filename)
