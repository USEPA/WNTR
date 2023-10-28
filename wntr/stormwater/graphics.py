import logging
import networkx as nx
import matplotlib.pylab as plt

from wntr.graphics.network import plot_network
from wntr.graphics.curve import plot_fragility_curve
from wntr.graphics.color import custom_colormap, random_colormap

logger = logging.getLogger(__name__)

def plot_network_directed(swn, attribute):
    G = swn.to_graph()
    G_attr = swn.to_graph(link_weight=attribute, modify_direction=True)
    
    plt.figure(facecolor='w', edgecolor='k')
    ax = plt.gca()
    pos = nx.get_node_attributes(G, 'pos')
    nx.draw_networkx_edges(G, pos, edge_color='grey', width=0.5, ax=ax)
    nx.draw_networkx(G_attr, pos=pos, with_labels=False, node_size=3, ax=ax)

# def plot_network(swn, node_attribute=None, link_attribute=None, title=None,
#                node_size=20, node_range=[None,None], node_alpha=1, node_cmap=None, node_labels=False,
#                link_width=1, link_range=[None,None], link_alpha=1, link_cmap=None, link_labels=False,
#                add_colorbar=True, node_colorbar_label='Node', link_colorbar_label='Link', 
#                directed=False, ax=None, filename=None):
    
#     if ax is None:  # create a new figure
#         plt.figure(facecolor="w", edgecolor="k")
#         ax = plt.gca()
        
#     #for subcatch in swn.subcatchments['geometry']:
#     #    ax.plot(*subcatch.boundary.xy, c='gray', linewidth=0.5)
    
#     _plot_network(swn, node_attribute, link_attribute, title, 
#                   node_size, node_range, node_alpha, node_cmap, node_labels,
#                   link_width, link_range, link_alpha, link_cmap, link_labels,
#                   add_colorbar, node_colorbar_label, link_colorbar_label, 
#                   directed, ax=ax, filename=filename)
