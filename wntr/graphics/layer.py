"""
The wntr.graphics.layer module includes methods plot
water network data layers.
"""
import logging
import networkx as nx
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd_module
    from shapely.geometry import Point
except Exception:
    gpd_module = None


def plot_valve_layer(wn, valve_layer, valve_attribute=None, title=None,
               valve_size=15, valve_range=[None,None], valve_cmap=None, add_colorbar=True,
               colorbar_label=None, include_network=True, ax=None, filename=None, backend='nx'):
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

    include_network: bool, optional
        Include a plot of the water network

    ax: matplotlib axes object, optional
        Axes for plotting (None indicates that a new figure with a single
        axes will be used)

    filename : str, optional
        Filename used to save the figure

    backend: str, optional
        Backend used for plotting:
        'nx' for networkx (default)
        'gpd' for geopandas

    Returns
    -------
    ax : matplotlib axes object
    """
    if backend == 'nx':
        ax = _plot_valve_layer_nx(wn, valve_layer, valve_attribute=valve_attribute, title=title,
               valve_size=valve_size, valve_range=valve_range, valve_cmap=valve_cmap,
               add_colorbar=add_colorbar, colorbar_label=colorbar_label,
               include_network=include_network, ax=ax, filename=filename)
    elif backend == 'gpd':
        ax = _plot_valve_layer_gpd(wn, valve_layer, valve_attribute=valve_attribute, title=title,
               valve_size=valve_size, valve_range=valve_range, valve_cmap=valve_cmap,
               add_colorbar=add_colorbar, colorbar_label=colorbar_label,
               include_network=include_network, ax=ax, filename=filename)
    else:
        raise Exception(f"Backend choice {backend} unrecognized. Please use 'nx' for networkx or 'gpd' for geopandas.")
    return ax


def _plot_valve_layer_nx(wn, valve_layer, valve_attribute=None, title=None,
               valve_size=15, valve_range=[None,None], valve_cmap=None, add_colorbar=True,
               colorbar_label=None, include_network=True, ax=None, filename=None):
    """
    Plot valve layer using the networkx backend.
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

    if add_colorbar and valve_attribute is not None:
        clb = plt.colorbar(sc, shrink=0.5, pad=0.05, ax=ax)
        clb.ax.set_title(colorbar_label, fontsize=10)
        clb.mappable.set_clim(valve_range[0],valve_range[1])

    if filename:
        plt.savefig(filename)

    return ax


def _plot_valve_layer_gpd(wn, valve_layer, valve_attribute=None, title=None,
               valve_size=15, valve_range=[None,None], valve_cmap=None, add_colorbar=True,
               colorbar_label=None, include_network=True, ax=None, filename=None):
    """
    Plot valve layer using the geopandas backend. Valve markers are drawn at
    zorder=6, above all elements rendered by _plot_network_gpd (max zorder=5).
    """

    if gpd_module is None:
        raise ImportError('geopandas and shapely are required for the gpd backend')

    if ax is None:
        plt.figure(facecolor='w', edgecolor='k')
        ax = plt.gca()

    if title is not None:
        ax.set_title(title)

    wn_gis = wn.to_gis()
    link_gdf = pd.concat((wn_gis.pipes, wn_gis.pumps, wn_gis.valves))

    if include_network:
        link_gdf.plot(ax=ax, aspect="equal", color='grey', linewidth=0.5, zorder=1)

    valve_points = []
    valve_indices = []
    for valve_name, (pipe_name, node_name) in valve_layer.iterrows():
        pipe = wn.get_link(pipe_name)
        if pipe_name not in link_gdf.index:
            print("Not valid")
            continue
        geom = link_gdf.loc[pipe_name, "geometry"]
        if node_name == pipe.start_node_name:
            valve_points.append(geom.interpolate(0.1, normalized=True))
        elif node_name == pipe.end_node_name:
            valve_points.append(geom.interpolate(0.9, normalized=True))
        else:
            print("Not valid")
            continue
        valve_indices.append(valve_name)

    valve_gdf = gpd_module.GeoDataFrame(index=valve_indices, geometry=valve_points)

    valve_kwds = {"marker": "v", "markersize": valve_size, "zorder": 6, "aspect": "equal", "legend": False}

    if valve_attribute is not None:
        valve_gdf["_attribute"] = pd.Series(valve_attribute).reindex(valve_indices)
        valve_kwds["column"] = "_attribute"
        if valve_cmap is not None:
            valve_kwds["cmap"] = valve_cmap
        if valve_range[0] is not None:
            valve_kwds["vmin"] = valve_range[0]
        if valve_range[1] is not None:
            valve_kwds["vmax"] = valve_range[1]
    else:
        valve_kwds["color"] = "k"

    valve_gdf.plot(ax=ax, **valve_kwds)

    if add_colorbar and valve_attribute is not None:
        attr_values = valve_gdf["_attribute"]
        vmin = valve_range[0] if valve_range[0] is not None else attr_values.min()
        vmax = valve_range[1] if valve_range[1] is not None else attr_values.max()
        cmap = valve_cmap if valve_cmap is not None else plt.get_cmap('Spectral_r')
        sm = mpl.cm.ScalarMappable(cmap=cmap)
        sm.set_clim(vmin, vmax)
        clb = ax.figure.colorbar(sm, ax=ax, shrink=0.5, pad=0.05)
        clb.ax.set_title(colorbar_label, fontsize=10)

    ax.axis('off')

    if filename:
        plt.savefig(filename)

    return ax
