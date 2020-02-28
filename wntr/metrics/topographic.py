"""
The wntr.metrics.topographic module contains topographic metrics that are not
available directly with NetworkX.  Functions in this module operate on a 
NetworkX MultiDiGraph, which can be created by calling ``G = wn.get_graph()``

.. rubric:: Contents

.. autosummary::

    terminal_nodes
    bridges
    central_point_dominance
    spectral_gap
    algebraic_connectivity
    critical_ratio_defrag
    valve_segments

"""
import networkx as nx
import numpy as np
import pandas as pd
import logging

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
    # Convert the graph to an undirected graph
    uG = G.to_undirected()
    
    # Node and link names
    nodes = list(uG.nodes()) # list of node names
    links = list(uG.edges(keys=True)) # list of tuples with start node, end node, link name
    
    # Append N_ and L_ to node and link names, used in matrices
    matrix_node_names = ['N_'+n for n in nodes]
    matrix_link_names = ['L_'+k for u,v,k in links]

    # Pipe-node connectivity matrix
    A = nx.incidence_matrix(uG).todense().T
    AC = pd.DataFrame(A, columns=matrix_node_names, index=matrix_link_names, dtype=int)
    
    # Valve-node connectivity matrix
    VC = pd.DataFrame(0, columns=matrix_node_names, index=matrix_link_names)
    for i, row in valve_layer.iterrows():
        VC.at['L_'+row['link'], 'N_'+row['node']] = 1
    
    # Valve deficient matrix (anti-valve matrix)
    VD = AC - VC

    # Direct connectivity matrix
    NI = pd.DataFrame(np.identity(len(matrix_node_names)),
                      index = matrix_node_names, columns = matrix_node_names)
    LI = pd.DataFrame(np.identity(len(matrix_link_names)),
                      index = matrix_link_names, columns = matrix_link_names)
    DC_left = pd.concat([NI, VD], sort=False)
    DC_right = pd.concat([VD.T, LI], sort=False)
    DC = pd.concat([DC_left, DC_right], axis=1, sort=False)
    DC = DC.astype(int)

    # initialization for looping routine
    seg_index = 0
    
    # pre-processing to find isolated elements before looping
    seg_label = {}

    for start_node, end_node, link_name in links:
        link_valves = valve_layer[valve_layer['link']==link_name]
        if set(link_valves['node']) >= set([start_node, end_node]):
            seg_index += 1
            seg_label['L_'+link_name] = seg_index
            
    for node_name in nodes:
        node_valves = valve_layer[valve_layer['node']==node_name]
        node_links = [k for u,v,k in uG.edges(node_name, keys=True)]
        if set(node_valves['link']) >= set(node_links):
            seg_index += 1
            seg_label['N_'+node_name] = seg_index
    
    # drop previously found isolated elements before looping
    DC = DC.drop(seg_label.keys())
    DC = DC.drop(seg_label.keys(), axis=1)   
    
    DC_np = DC.to_numpy() # requires Pandas v.0.24.0

    # vector of length nodes+links where the ith entry is the segment number of node/link i
    seg_label_DC = np.zeros(shape=(len(DC.index)), dtype=int)

    # Loop over all nodes and links to grow segments
    for i in range(len(seg_label_DC)):
        
        # Only assign a seg_label if node/link doesn't already have one
        if seg_label_DC[i] == 0:
            
            # Advance segment label and assign to node/link, mark as assigned
            seg_index += 1
            seg_label_DC[i] = seg_index
           
            # Initialize segment size
            seg_size = (seg_label_DC == seg_index).sum()
             
            flag = True
            
            #print(i)
    
            # Nodes and links that are part of the segment
            seg = np.where(seg_label_DC == seg_index)[0]
        
            # Connectivity of the segment
            seg_DC = np.zeros(shape=(DC_np.shape[0]), dtype=int)
            seg_DC[seg] = 1
    
            while flag:          
               
                # Potential connectivity of the segment      
                p_seg_DC = DC_np + seg_DC[:,None] # this is slow
                
                # Nodes and links that are connected to the segment
                temp = np.max(p_seg_DC,axis=0) # this is somewhat slow
                connected_to_seg = np.where(temp > 1)[0]   
                seg_DC[connected_to_seg] = 1
      
                # Label nodes/links connected to the segment
                seg_label_DC[connected_to_seg] = seg_index
                
                # Find new segment size
                new_seg_size = (seg_label_DC == seg_index).sum()
                    
                # Check for progress
                if seg_size == new_seg_size:
                    flag = False
                else:
                    seg_size = new_seg_size
          
                # Update seg_DC and DC_np
                seg_DC = DC_np[:,i] + np.sum(
                                        p_seg_DC[:,connected_to_seg],axis=1
                                        ) # this is slow
                seg_DC = np.clip(seg_DC,0,1)          
                DC_np[:,connected_to_seg] = np.repeat(
                                            seg_DC,len(connected_to_seg)).reshape(
                                            len(seg_DC),len(connected_to_seg))
                                            # this is somewhat slow
    
    #        print(i, seg_size)
    
    # combine pre-processed and looped results
    seg_labels = list(seg_label.values()) + list(seg_label_DC)
    seg_labels_index = list(seg_label.keys()) + list(DC.index)
    seg_label = pd.Series(seg_labels, index=seg_labels_index, dtype=int)

    # Separate node and link segments
    # remove leading N_ and L_ from node and link names
    node_segments = seg_label[matrix_node_names]
    link_segments = seg_label[matrix_link_names]
    node_segments.index = node_segments.index.str[2::]
    link_segments.index = link_segments.index.str[2::]  
    
    # Extract segment sizes, for nodes and links
    seg_link_sizes = link_segments.value_counts().rename('link')
    seg_node_sizes = node_segments.value_counts().rename('node')
    seg_sizes = pd.concat([seg_link_sizes, seg_node_sizes], axis=1).fillna(0)
    seg_sizes = seg_sizes.astype(int)
    
    return node_segments, link_segments, seg_sizes

