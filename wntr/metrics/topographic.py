import logging
import networkx as nx
import numpy as np

logger = logging.getLogger('wntr.metrics.topographic')

def average_shortest_path_length_source_to_junction(wn, weight=None):
    """Compute the average shortest path between sources and
    junctions. Sources are considered tanks and reservoirs. In other
    words, this method will obtain the shortest path length between
    each (source, junction) pair and then average these values. Note
    that this method considers the graph to be undirected.

    Parameters
    ----------
    wn: a WaterNetworkModel object

    Returns
    -------
    L: float
       The average shortest path length between sources and junctions.
    weight: string or None
       The edge attribute to be used as a weight. If None, every edge/link has a weight of 1.

    """

    G = wn.get_graph_deep_copy()
    udG = G.to_undirected()

    shortest_path_length_list = []
    for junction_name, junction in wn.junctions():
        for tank_name, tank in wn.tanks():
            shortest_path_length_list.append(nx.shortest_path_length(udG,tank_name,junction_name,weight))
        for reservoir_name, reservoir in wn.reservoirs():
            shortest_path_length_list.append(nx.shortest_path_length(udG,reservoir_name,junction_name,weight))

    avg_shortest_path_length = np.average(shortest_path_length_list)

    return avg_shortest_path_length

def eccentricity_source_to_junction(wn, weight=None):
    """
    For each junction, determine the maximum shortest path length
    between that junction and all sources (sources are considered
    tanks and reservoirs). Note that this method condiders the graph to be undirected.

    Parameters
    ----------
    wn: a WaterNetworkModel object
    weight: string or None
       The edge attribute to be used as a weight. If None, every edge/link has a weight of 1.

    Returns
    -------
    D: dict
       A dictionary keyed by junction name. The values are the maximum
       shortest path lengths between the corresponding junction and
       all sources.
    """

    G = wn.get_graph_deep_copy()
    udG = G.to_undirected()

    D = {}

    for junction_name, junction in wn.junctions():
        shortest_lengths_j = []
        for tank_name, tank in wn.tanks():
            shortest_lengths_j.append(nx.shortest_path_length(udG,tank_name,junction_name,weight))
        for reservoir_name, reservoir in wn.reservoirs():
            shortest_lengths_j.append(nx.shortest_path_length(udG,reservoir_name,junction_name,weight))
        D[junction_name] = np.max(shortest_lengths_j)

    return D

def min_shortest_path_length_source_to_junction(wn, weight=None):
    """
    For each junction, determine the minimum shortest path length
    between that junction and all sources (sources are considered
    tanks and reservoirs). Note that this method considers the graph to be undirected.

    Parameters
    ----------
    wn: a WaterNetworkModel object
    weight: string or None
       The edge attribute to be used as a weight. If None, every edge/link has a weight of 1.

    Returns
    -------
    D: dict
       A dictionary keyed by junction name. The values are the minimum
       shortest path lengths between the corresponding junction and
       all sources.
    """

    G = wn.get_graph_deep_copy()
    udG = G.to_undirected()

    D = {}

    for junction_name, junction in wn.junctions():
        shortest_lengths_j = []
        for tank_name, tank in wn.tanks():
            shortest_lengths_j.append(nx.shortest_path_length(udG,tank_name,junction_name,weight))
        for reservoir_name, reservoir in wn.reservoirs():
            shortest_lengths_j.append(nx.shortest_path_length(udG,reservoir_name,junction_name,weight))
        D[junction_name] = np.min(shortest_lengths_j)

    return D

def average_connectivity_source_to_junction(wn):
    """
    Compute the average over all (source, junction) pairs of the
    minimum number of links that must be removed to disconnect the
    source and the junction. Sources are considered tanks and
    reservoirs. Note that this method considers the graph to be
    undirected.

    Parameters
    ----------
    wn: a WaterNetworkModel object

    Returns
    -------
    C: float
       The average connectivity between sources and junctions.

    """

    G = wn.get_graph_deep_copy()
    udG = G.to_undirected()

    connectivity_list = []
    for junction_name, junction in wn.junctions():
        for tank_name, tank in wn.tanks():
            connectivity_list.append(nx.edge_connectivity(udG,tank_name,junction_name))
        for reservoir_name, reservoir in wn.reservoirs():
            connectivity_list.append(nx.edge_connectivity(udG,reservoir_name,junction_name))

    avg_connectivity = np.average(connectivity_list)

    return avg_connectivity

def reachability_source_to_junction(wn):
    """For each junction, compute the minimum number of links that must
    be removed to disconnect the junction from all sources. Sources
    are considered tanks and reservoirs. Note that this method
    considers the graph to be undirected.

    Parameters
    ----------
    wn: a WaterNetworkModel object

    Returns
    -------
    D: dict
       A dictionary keyed by junction name where the value is the
       minimum number of links that must be removed to separate that
       junction from all sources.

    """

    G = wn.get_graph_deep_copy()
    udG = G.to_undirected()

    D = {}
    for junction_name, junction in wn.junctions():
        cut_set = set()
        for tank_name, tank in wn.tanks():
            cut_set = cut_set.union(nx.minimum_edge_cut(udG,tank_name,junction_name))
        for reservoir_name, reservoir in wn.reservoirs():
            cut_set = cut_set.union(nx.minimum_edge_cut(udG,reservoir_name,junction_name))
        D[junction_name] = len(cut_set)

    return D

def central_point_dominance(wn):
    print 'blah'
