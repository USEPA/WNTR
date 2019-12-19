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
    G : networkx MultiDiGraph
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
    G : networkx MultiDiGraph
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
    G : networkx MultiDiGraph
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
    G : networkx MultiDiGraph
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
    G : networkx MultiDiGraph
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
    G : networkx MultiDiGraph
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
    sources : list
        List of source nodes
    sinks : list
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


def valve_segments(G, valves, pandas_flag=False, output_flag=False):
    """
    Valve segmentation

    Parameters
    -----------
    valves : list
        List of valves, denoted by node and pipe pairs
    pandas_flag : boolean
        Boolean to select Pandas (True) or Numpy (False) algorithm
    output_flag : boolean
        Boolean to include more output (True) or less (False)

    Returns
    -------
    output_flag = True : Two Pandas series (node and link segment number), 
        total number of segments, and number of nodes+links in largest
        segment
    output_flag = False : Two Pandas series (node and link segment number)
    
    """
    
    uG = G.to_undirected()
    
    node_names = ['N_'+n for n in list(uG.nodes())]
    link_names = ['L_'+k for u,v,k in uG.edges(keys=True)] 
    
    # Pipe-node connectivity matrix
    A = nx.incidence_matrix(uG).todense().T
    AC = pd.DataFrame(A, columns=node_names, index=link_names, dtype=int)
    
    # Valve-node connectivity matrix
    VC = pd.DataFrame(0, columns=node_names, index=link_names)
    for i, row in valves.iterrows():
        VC.at['L_'+row['link'], 'N_'+row['node']] = 1
    
    # Valve deficient matrix
    VD = AC - VC

    # Build Direct connectivity matrix, DC
    NI = pd.DataFrame(np.identity(len(node_names)),
                      index = node_names, columns = node_names)
    LI = pd.DataFrame(np.identity(len(link_names)),
                      index = link_names, columns = link_names)
    DC_left = pd.concat([NI, VD], sort=False)
    DC_right = pd.concat([VD.T, LI], sort=False)
    DC = pd.concat([DC_left, DC_right], axis=1, sort=False)
    DC = DC.astype(int)
    
    # initialization for looping routine
    seg_index = 0
    
    if pandas_flag == True:
        
        ''' Pandas valve segmentation routine '''

        # vector of length nodes+links where the ith entry is the segment number of node/link i
        seg_label = pd.Series(0, index=DC.index, dtype=int)
        
        # Loop over all nodes and links to grow segments
        for i in seg_label.index:
            
            # Only assign a seg_label if node/link doesn't already have one
            if seg_label.at[i] == 0:
                
                # Advance segment label and assign to node/link, mark as assigned
                seg_index += 1
                seg_label.at[i] = seg_index
                
                seg_size = (seg_label == seg_index).sum()
                
                flag = True
                
                #print(i)
                
                # Nodes and links that are part of the segment
                seg = set([i])
                
                # Unlabeled nodes and links
                unlabeled = set(seg_label.index[seg_label == 0])
                 
                # Connectivitiy of the segment
                seg_DC = pd.Series(0, index=DC.columns)
                seg_DC.loc[seg] = 1
                
                while flag:
        
                    # Connectivity of the unlabeled nodes and links
                    unlabeled_DC = DC.loc[:,unlabeled]
                    
                    # Potential connectivitiy of the segment
                    p_seg_DC = unlabeled_DC.add(seg_DC, axis=0)
                    
                    # Nodes and links that are connected to the segement
                    #temp = p_seg_DC.max(axis=0) # This line is slow when the dataframe is large
                    temp = p_seg_DC.values.max(axis=0)
                    connected_to_seg = set(p_seg_DC.columns[temp > 1])
                    
                    #print('    ', connected_to_seg)
                    
                    # Update direct connectivity matrix and segment label
                    #DC.loc[:,connected_to_seg] = p_seg_DC.loc[:,connected_to_seg] # This line is slow
                    DC.loc[:,connected_to_seg].update(p_seg_DC.loc[:,connected_to_seg]) 
                    seg_label[connected_to_seg] = seg_index
                    
                    new_seg_size = (seg_label == seg_index).sum()
                    if seg_size == new_seg_size:
                        flag = False
                    else:
                        seg_size = new_seg_size
                    
                    # Update seg, unabled, and seg_DC
                    seg.update(connected_to_seg)
                    unlabeled = unlabeled.difference(connected_to_seg)
                    seg_DC.loc[connected_to_seg] = 1 # this is slow
                    
        #        print(i, seg_size)
    
    else:
        
        ''' Numpy valve segmentation routine '''
        
        DC_np = DC.to_numpy() # requires Pandas v.0.24.0

        # vector of length nodes+links where the ith entry is the segment number of node/link i
        seg_label_np = np.zeros(shape=(len(DC.index)), dtype=int)

        
        # Loop over all nodes and links to grow segments
        for i in range(len(seg_label_np)):
            
            # Only assign a seg_label if node/link doesn't already have one
            if seg_label_np[i] == 0:
                
                # Advance segment label and assign to node/link, mark as assigned
                seg_index += 1
                seg_label_np[i] = seg_index
               
                # Initialize segment size
                seg_size = (seg_label_np == seg_index).sum()
                 
                flag = True
                
                #print(i)
        
                # Nodes and links that are part of the segment
                seg = np.where(seg_label_np == seg_index)[0]
            
                # Connectivitiy of the segment
                seg_DC = np.zeros(shape=(DC_np.shape[0]), dtype=int)
                seg_DC[seg] = 1
        
                while flag:          
                   
                    # Potential connectivitiy of the segment      
                    p_seg_DC = DC_np + seg_DC[:,None] # this is slow
                    
                    # Nodes and links that are connected to the segment
                    temp = np.max(p_seg_DC,axis=0) # this is somewhat slow
                    connected_to_seg = np.where(temp > 1)[0]   
                    seg_DC[connected_to_seg] = 1
          
                    # Label nodes/links connected to the segment
                    seg_label_np[connected_to_seg] = seg_index
                    
                    # Find new segment size
                    new_seg_size = (seg_label_np == seg_index).sum()
                        
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
        
        seg_label = pd.Series(seg_label_np, index=DC.index, dtype=int)  

    # Separate node and link segments
    # remove leading N_ and L_ from node and link names
    node_segments = seg_label[node_names]
    link_segments = seg_label[link_names]
    node_segments.index = node_segments.index.str[2::]
    link_segments.index = link_segments.index.str[2::]  
    
    if output_flag == True:
              
        num_segments = max(node_segments.max(), link_segments.max())
        
        seg_link_sizes = link_segments.value_counts().rename('link')
        seg_node_sizes = node_segments.value_counts().rename('node')
        seg_sizes = pd.concat([seg_link_sizes, seg_node_sizes], axis=1).fillna(0)
        max_elements = int(seg_sizes.sum(axis=1).max())
        
#        seg_total_size = seg_sizes.sum(axis=1)        
#        max_links_or_nodes = int(seg_sizes.max().max())

        return node_segments, link_segments, num_segments, max_elements

    else:
        
        return node_segments, link_segments