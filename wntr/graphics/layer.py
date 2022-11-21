"""
The wntr.graphics.layer module includes methods plot
water network data layers.
"""
import logging
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

def plot_valve_layer(wn, valve_layer, valve_attribute=None, title=None,
               valve_size=15, valve_range=[None,None], valve_cmap=None, add_colorbar=True, 
               colorbar_label=None, include_network=True, ax=None, filename=None):
    """
    Plot valve layer
    
    Parameters
    ----------
    wn: wntr WaterNetworkModel
        A WaterNetworkModel object
    
    valve_layer: pd.Dataframe, optional
        Valve layer, defined by node and link pairs (for example, valve 0 is 
        on link A and protects node B). The valve_layer DataFrame is indexed by
        valve number, with columns named 'node' and 'link'.
    
    valve_attribute: pd.Series, optional
        Attribute for each valve
        
    title: str, optional
        Plot title 

    valve_size: int, optional
        Node size 
    
    valve_range: list, optional
        Value range used to scale colormap ([None,None] indicates autoscale)
        
    valve_cmap: matplotlib.pyplot.cm colormap or named color, optional
        Valve colormap 

    add_colorbar: bool, optional
        Add colorbar
    
    colorbar_label: str, optional
        Node colorbar label
    
    include_network: bool, options
        Include a plot of the water network 
        
    ax: matplotlib axes object, optional
        Axes for plotting (None indicates that a new figure with a single 
        axes will be used)
        
    filename : str, optional
        Filename used to save the figure
        
    Returns
    -------
    ax : matplotlib axes object  
    """

    if ax is None: # create a new figure
        plt.figure(facecolor='w', edgecolor='k')
        ax = plt.gca()
        
    # Graph, undirected
    G = wn.to_graph().to_undirected()

    # Position
    pos = nx.get_node_attributes(G,'pos')
    if len(pos) == 0:
        pos = None

    if title is not None:
        ax.set_title(title)
    
    if include_network:
        nx.draw_networkx_edges(G, pos, edge_color='grey', width=0.5, ax=ax)
        
    ax.axis('off')
    
    valve_coordinates = []
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
        valve_coordinates.append((x0 + dx * 0.1, y0 + dy * 0.1))
    
    valve_coordinates = np.array(valve_coordinates)
    
    if valve_attribute is not None: 
        sc = ax.scatter(valve_coordinates[:,0], valve_coordinates[:,1], s=valve_size, c=valve_attribute, marker='v', cmap=valve_cmap)  
    else:
        sc = ax.scatter(valve_coordinates[:,0], valve_coordinates[:,1], valve_size, 'k', 'v')   
 
    if add_colorbar:
        clb = plt.colorbar(sc, shrink=0.5, pad=0.05, ax=ax)
        clb.ax.set_title(colorbar_label, fontsize=10)
        clb.mappable.set_clim(valve_range[0],valve_range[1])
        
    if filename:
        plt.savefig(filename)
        
    return ax
