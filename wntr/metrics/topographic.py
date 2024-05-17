"""
The wntr.metrics.topographic module contains topographic metrics that are not
available directly with NetworkX.  Functions in this module operate on a 
NetworkX MultiDiGraph, which can be created by calling ``G = wn.to_graph()``
"""
import networkx as nx
import numpy as np
import pandas as pd
import logging
import warnings

logger = logging.getLogger(__name__)

def terminal_nodes(G):
    """
    Nodes with degree 1

    Parameters
    ----------
    G: networkx MultiDiGraph
        Graph

    Returns
    -------
    List of terminal nodes
    
    """
    node_degree = dict(G.degree())
    terminal_nodes = [k for k,v in node_degree.items() if v == 1]

    return terminal_nodes

def bridges(G):
    """
    Bridge links

    Parameters
    ----------
    G: networkx MultiDiGraph
        Graph

    Returns
    -------
    List of links that are bridges
    
    """
    uG = G.to_undirected() # uses an undirected graph
    bridge_links = []
    bridges = nx.bridges(nx.Graph(uG)) # not implemented for multigraph
    for br in bridges:
        for key in uG[br[0]][br[1]].keys():
            bridge_links.append(key)
        
    return bridge_links

def central_point_dominance(G):
    """
    Central point dominance
    
    Parameters
    ----------
    G: networkx MultiDiGraph
        Graph
        
    Returns
    -------
    Central point dominance (float)
    
    """
    uG = G.to_undirected() # uses an undirected graph
    bet_cen = nx.betweenness_centrality(nx.Graph(uG)) # not implemented for multigraph 
    bet_cen = list(bet_cen.values())
    cpd = sum(max(bet_cen) - np.array(bet_cen))/(len(bet_cen)-1)

    return cpd

def spectral_gap(G):
    """
    Spectral gap
    
    Difference in the first and second eigenvalue of the adjacency matrix
    
    Parameters
    ----------
    G: networkx MultiDiGraph
        Graph
        
    Returns
    -------
    Spectral gap (float)
    
    """
    uG = G.to_undirected() # uses an undirected graph
    eig = nx.adjacency_spectrum(uG)
    spectral_gap = abs(eig[0] - eig[1])

    return spectral_gap.real

def algebraic_connectivity(G):
    """
    Algebraic connectivity
    
    Second smallest eigenvalue of the normalized Laplacian matrix of a network

    Parameters
    ----------
    G: networkx MultiDiGraph
        Graph
        
    Returns
    -------
    Algebraic connectivity (float)
    
    """
    uG = G.to_undirected() # uses an undirected graph
    eig = nx.laplacian_spectrum(uG)
    eig = np.sort(eig)
    alg_con = eig[1]

    return alg_con

def critical_ratio_defrag(G):
    """
    Critical ratio of defragmentation

    Parameters
    ----------
    G: networkx MultiDiGraph
        Graph
        
    Returns
    -------
    Critical ratio of defragmentation (float)
    
    """
    node_degree = dict(G.degree())
    tmp = np.mean(pow(np.array(list(node_degree.values())),2))
    fc = 1-(1/((tmp/np.mean(list(node_degree.values())))-1))

    return fc


def _links_in_simple_paths(G, sources, sinks):
    """
    Count all links in a simple path between sources and sinks

    Parameters
    -----------
    G: networkx MultiDiGraph
        Graph
    sources: list
        List of source nodes
    sinks: list
        List of sink nodes

    Returns
    -------
    Dictionary with the number of times each link is involved in a path
    
    """
    link_names = [name for (node1, node2, name) in list(G.edges(keys=True))]
    link_count = pd.Series(data = 0, index=link_names)

    for sink in sinks:
        for source in sources:
            if nx.has_path(G, source, sink):
                paths = nx.all_simple_paths(G,source,target=sink)
                for path in paths:
                    for i in range(len(path)-1):
                        links = list(G[path[i]][path[i+1]].keys())
                        for link in links:
                            link_count[link] = link_count[link]+1

    return link_count

def valve_segments(G, valve_layer):
    """
    Valve segmentation

    Parameters
    -----------
    G: networkx MultiDiGraph
        Graph
    valve_layer: pandas DataFrame
        Valve layer, defined by node and link pairs (for example, valve 0 is 
        on link A and protects node B). The valve_layer DataFrame is indexed by
        valve number, with columns named 'node' and 'link'.

    Returns
    -------
    node_segments: pandas Series
       Segment number for each node, indexed by node name
    link_segments: pandas Series
        Segment number for each link, indexed by link name
    segment_size: pandas DataFrame
        Number of nodes and links in each segment. The DataFrame is indexed by 
        segment number, with columns named 'node' and 'link'.
    """
    

    # First check for duplicate valves
    if valve_layer.duplicated().any():
        valve_layer.drop_duplicates(inplace = True)
        warnings.warn('One or more valves were duplicated in `valve_layer`; duplicates are ignored.', stacklevel=0)

    # Convert the graph to an undirected graph
    uG = G.to_undirected()

    # Node and link names
    # Append N_ and L_ to node and link names to account for naming overlap
    node_names = ['N_'+n for n in uG.nodes()]
    link_names = ['L_'+k for u,v,k in uG.edges(keys=True)]
    all_names = node_names + link_names

    # Initialization for labelling
    seg_index = 0
    seg_label = np.zeros(shape=(len(all_names)), dtype=int)

    # Find and label links isolated by valves, EG 0|----|0
    for start_node, end_node, link_name in uG.edges(keys=True):
        link_valves = valve_layer[valve_layer['link']==link_name]
        if set(link_valves['node']) >= set([start_node, end_node]):
            seg_index += 1
            seg_label[all_names.index('L_'+link_name)] = seg_index

    # Find and label nodes isolated by valves, EG 0----|0|----0
    for node_name in node_names:
        node_valves = valve_layer[valve_layer['node']==node_name]
        node_links = [k for u,v,k in uG.edges(node_name[2:], keys=True)]
        if set(node_valves['link']) >= set(node_links):
            seg_index += 1
            seg_label[all_names.index(node_name)] = seg_index
    
    # Collect valved link names
    valved_link_names = list(valve_layer['link'].unique()) 

    # Remove valved edges from G
    valved_edges = []
    for edge in uG.edges:
        link_name = edge[2]
        if link_name in valved_link_names:
            valved_edges.append(edge)
    uG.remove_edges_from(valved_edges)

    ## Label unvalved portion of graph using connected components

    # Assign labels to nodes
    for component in nx.connected_components(uG):
        # component is a set of node names
        seg_index += 1
        for node in component:
            index = all_names.index('N_'+node)
            seg_label[index] = seg_index

    # Assign labels to links based on labelling of their nodes
    for edge in uG.edges(keys=True):
        node1, node2, link_name = edge
        node1 = all_names.index('N_'+node1)
        link_index = all_names.index('L_'+link_name)
        seg_label[link_index] = seg_label[node1]

    ## Label valved portion of graph
    for valved_edge in valved_edges:
        node1_name, node2_name, link_name = valved_edge
        link_valves = valve_layer[valve_layer['link']==link_name]
        link_index = all_names.index('L_'+link_name)

        # When link only has one valved node, locate unvalved node
        # and label link and unvalved node together
        if link_valves.shape[0] == 1:
            both_node_names = [node1_name, node2_name]
            valved_node_name = link_valves.iloc[0]['node']
            both_node_names.remove(valved_node_name)
            unvalved_node_name = both_node_names[0]
            unvalved_node_index = all_names.index('N_'+unvalved_node_name)
            if seg_label[unvalved_node_index] == 0:
                seg_index += 1
                seg_label[unvalved_node_index] = seg_index
                seg_label[link_index] = seg_index
            else:
                seg_label[link_index] = seg_label[unvalved_node_index]

        # Links with link_valves.size == 2 are already labelled (isolated link)
        elif link_valves.shape[0] == 2:
            continue
        else:
            raise Exception("Each link should have a maximum of two valves.")


    # Finalize results
    seg_labels_index = all_names
    seg_label = pd.Series(seg_label, index=seg_labels_index, dtype=int)

    node_segments = seg_label[node_names]
    link_segments = seg_label[link_names]

    # Remove "N_" and "L_" from nodes and links
    node_segments.index = node_segments.index.str[2::]
    link_segments.index = link_segments.index.str[2::]

    # Extract segment sizes, for nodes and links
    seg_link_sizes = link_segments.value_counts().rename('link')
    seg_node_sizes = node_segments.value_counts().rename('node')
    seg_sizes = pd.concat([seg_link_sizes, seg_node_sizes], axis=1).fillna(0)
    seg_sizes = seg_sizes.astype(int)

    return node_segments, link_segments, seg_sizes


def valve_segment_attributes(valve_layer, node_segments, link_segments, 
                             demand=None, length=None):
    """
    Valve segment attributes include 1) the number of valves surrounding each valve
    and (optionally) the increase in segment demand if a given valve is removed and 
    the increase in segment pipe length if a given valve is removed. 
    
    The increase in segment demand is  expressed as a fraction of the 
    max segment demand associated with that valve.  Likewise, 
    the increase in segment pipe length is expressed as a fraction of the 
    max segment pipe length associated with that valve.
	
    Parameters
    ----------
    valve_layer: pandas DataFrame
        Valve layer, defined by node and link pairs (for example, valve 0 is 
        on link A and protects node B). The valve_layer DataFrame is indexed by
        valve number, with columns named 'node' and 'link'.
    
    node_segments: pandas Series
       Segment number for each node, indexed by node name.
       node_segments can be computed using `wntr.metrics.topographic.valve_segments`
       
    link_segments: pandas Series
        Segment number for each link, indexed by link name. 
        link_segments can be computed using `wntr.metrics.topographic.valve_segments`

    demands: pandas Series, optional
        Node demand, the average expected node demand can be computed using 
        wntr.metrics.average_expected_demand(wn). 
        Demand from simulation results can also be used.
        
    lengths: pandas Series, optional
        A list of 'length' attributes for each link in the network.
        The output from wn.query_link_attribute('length')

    Returns
    -------
    pandas DataFrame 
        Valve segement attributes, indexed by valve number, that contains:
    
       * num_surround: number of valves surrounding each valve
       * demand_increase: increase in segment demand if a given valve is removed, expressed as a fraction
       * length_increase: increase in segment pipe length if a given valve is removed, expressed as a fraction
    """
    valve_attr = pd.DataFrame()
    
    valve_attr['num_surround'] = _valve_criticality(valve_layer, node_segments, link_segments)
    
    if demand is not None:
        valve_attr['demand_increase'] = _valve_criticality_demand(demand, valve_layer, node_segments, link_segments)
    
    if length is not None:
        valve_attr['length_increase'] = _valve_criticality_length(length, valve_layer, node_segments, link_segments)
                                           
    return valve_attr

def _valve_criticality(valve_layer, node_segments, link_segments):
    """
	Returns the number of valves surrounding each valve
	
    """
    # Assess the number of valves in the system
    n_valves = len(valve_layer)   

    # Calculate valve-based valve criticality
    VC = {}
    for i in range(n_valves):
        # identify the node-side and link-side segments
        node_seg = node_segments[valve_layer.loc[i,'node']]
        link_seg = link_segments[valve_layer.loc[i,'link']] 
        # if the node and link are in the same segment, set criticality to 0
        if node_seg == link_seg:
            VC_val_i = 0 
        else:
            V_list = []
            # identify links and nodes in surrounding segments
            links_in_segs = link_segments[(link_segments == link_seg) | (link_segments == node_seg)].index
            nodes_in_segs = node_segments[(node_segments == link_seg) | (node_segments == node_seg)].index
            # add unique valves to the V_list from the link list
            for link in links_in_segs:
                valves = valve_layer[valve_layer['link'] == link].index
                if len(valves) == 0:
                    pass
                else:
                    for valve in valves:
                        if valve in V_list:
                            pass
                        else:
                            V_list.append(valve)
            # add unique valves to the V_list from the node list
            for node in nodes_in_segs:
                valves = valve_layer[valve_layer['node'] == node].index
                if len(valves) == 0:
                    pass
                else:
                    for valve in valves:
                        if valve in V_list:
                            pass
                        else:
                            V_list.append(valve)
            # calculate valve-based criticality for the valve
            # count the number of valves in the list, minus the valve in question
            VC_val_i = len(V_list) - 1

        VC[i] = VC_val_i
    
    VC = pd.Series(VC)
    
    return VC

def _valve_criticality_length(link_lengths, valve_layer, node_segments, link_segments):
    """
	Returns the ratio of the segment lengths on either side of the valve
    """
    # Assess the number of valves in the system
    n_valves = len(valve_layer)   

    # Calculate the length-based valve crticiality
    VC = {}
    
    for i in range(n_valves):
		# identify the node-side and link-side segments
        node_seg = node_segments[valve_layer.loc[i,'node']]
        link_seg = link_segments[valve_layer.loc[i,'link']]
        
        # if the node and link are in the same segment, set criticality to 0
        if node_seg == link_seg:
            VC_len_i = 0
        else:
            # calculate total length of links in the node segment
            links_in_node_seg = link_segments[link_segments == node_seg].index
            n_ixs = link_lengths.index.intersection(links_in_node_seg)
            L_node = link_lengths[n_ixs].sum()

            # calculate total length of links in the link segment
            links_in_link_seg = link_segments[link_segments == link_seg].index
            l_ixs = link_lengths.index.intersection(links_in_link_seg)
            L_link = link_lengths[l_ixs].sum()

            # calculate link length criticality for the valve
            if L_node == 0 and L_link == 0:
                VC_len_i = 0.0
            else:
                VC_len_i = (L_link + L_node) / max(L_link, L_node) - 1

        VC[i] = VC_len_i
    
    VC = pd.Series(VC)
    
    return VC

def _valve_criticality_demand(node_demands, valve_layer, node_segments, link_segments):
    """
	Returns the ratio of node demands on either side of a valve.
    """
    # Assess the number of valves in the system
    n_valves = len(valve_layer)         

    # Calculate the demand-based valve crticiality
    VC = {}

    for i in range(n_valves):
        # identify the node-side and link-side segments
        node_seg = node_segments[valve_layer.loc[i,'node']]
        link_seg = link_segments[valve_layer.loc[i,'link']] 
        # if the node and link are in the same segment, set criticality to 0
        if node_seg == link_seg:
            VC_dem_i = 0.0
        else:
            # calculate total demand in the node segment
            nodes_in_node_seg = node_segments[node_segments == node_seg].index
            n_ixs = node_demands.index.intersection(nodes_in_node_seg)
            D_node = node_demands.loc[n_ixs].sum()

            # calculate total demand in the link segment
            nodes_in_link_seg = node_segments[node_segments == link_seg].index
            l_ixs = node_demands.index.intersection(nodes_in_link_seg)
            D_link = node_demands[l_ixs].sum()

            # calculate demand criticality for the valve
            if D_node == 0 and D_link == 0:
                VC_dem_i = 0
            else:
                VC_dem_i = (D_link + D_node) / max(D_link, D_node) - 1

        VC[i] = VC_dem_i
    
    VC = pd.Series(VC)
    
    return VC

