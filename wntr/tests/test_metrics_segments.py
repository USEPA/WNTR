import unittest
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import networkx as nx
import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestSegmentation(unittest.TestCase):
    @classmethod
    def setUpClass(self):

        inp_file1 = join(test_datadir, "CCWI17-HermanMahmoud.inp")
        self.wn1 = wntr.network.WaterNetworkModel(inp_file1)

        inp_file2 = join(ex_datadir, "Net3.inp")
        self.wn2 = wntr.network.WaterNetworkModel(inp_file2)

    @classmethod
    def tearDownClass(self):
        pass

    def test_segmentation_small(self):
        # test a small network
        G = self.wn1.to_graph()

        valves = [
            ["p1", "n1"],  # valve 0 is on link p1 and protects node n1
            ["p3", "n2"],
            ["p7", "n5"],
            ["p7", "n6"],
            ["p8", "n6"],
        ]
        valves = pd.DataFrame(valves, columns=["link", "node"])

        (
            node_segments,
            link_segments,
            seg_size,
        ) = wntr.metrics.topographic.valve_segments(G, valves)

        max_seg_size = seg_size.sum(axis=1).max()
        self.assertEqual(max_seg_size, 11)
        self.assertEqual(seg_size.shape[0], 4)

    def test_segmentation_random(self):
        # test Net3
        G = self.wn2.to_graph()
        valves = pd.read_csv(
            join(test_datadir, "valve_layer_random.csv"), index_col=0, dtype="object"
        )

        (
            node_segments,
            link_segments,
            seg_size,
        ) = wntr.metrics.topographic.valve_segments(G, valves)
        max_seg_size = seg_size.sum(axis=1).max()
        num_segments = seg_size.shape[0]

        #        node_segments.to_csv('node_segments_random.csv')
        #        link_segments.to_csv('link_segments_random.csv')

        expected_node_segments = pd.read_csv(
            join(test_datadir, "node_segments_random.csv"), index_col=0
        ).squeeze()
        expected_link_segments = pd.read_csv(
            join(test_datadir, "link_segments_random.csv"), index_col=0
        ).squeeze()
        expected_node_segments.astype("int32")
        expected_link_segments.astype("int32")

        #        import matplotlib
        #        cmap = matplotlib.colors.ListedColormap(np.random.rand(num_segments,3))
        #        wntr.graphics.plot_network(self.wn2, node_segments, link_segments, valve_layer=valves,
        #                                   node_cmap=cmap, link_cmap=cmap,
        #                                   node_range=[0.5,num_segments+0.5],
        #                                   link_range=[0.5,num_segments+0.5])

        self.assertListEqual(list(node_segments), list(expected_node_segments))
        self.assertListEqual(list(link_segments), list(expected_link_segments))

        self.assertEqual(max_seg_size, 125)
        self.assertEqual(num_segments, 23)

    def test_segmentation_strategic(self):
        # test Net3
        G = self.wn2.to_graph()
        valves = pd.read_csv(
            join(test_datadir, "valve_layer_stategic_1.csv"),
            index_col=0,
            dtype="object",
        )

        (
            node_segments,
            link_segments,
            seg_size,
        ) = wntr.metrics.topographic.valve_segments(G, valves)
        max_seg_size = seg_size.sum(axis=1).max()
        num_segments = seg_size.shape[0]

        #        node_segments.to_csv('node_segments_strategic.csv')
        #        link_segments.to_csv('link_segments_strategic.csv')

        expected_node_segments = pd.read_csv(
            join(test_datadir, "node_segments_strategic.csv"), index_col=0
        ).squeeze()
        expected_link_segments = pd.read_csv(
            join(test_datadir, "link_segments_strategic.csv"), index_col=0
        ).squeeze()
        expected_node_segments.astype("int32")
        expected_link_segments.astype("int32")

        #        import matplotlib
        #        cmap = matplotlib.colors.ListedColormap(np.random.rand(num_segments,3))
        #        wntr.graphics.plot_network(self.wn2, node_segments, link_segments, valve_layer=valves,
        #                                   node_cmap=cmap, link_cmap=cmap,
        #                                   node_range=[0.5,num_segments+0.5],
        #                                   link_range=[0.5,num_segments+0.5])

        self.assertListEqual(list(node_segments), list(expected_node_segments))
        self.assertListEqual(list(link_segments), list(expected_link_segments))

        self.assertEqual(max_seg_size, 3)
        self.assertEqual(num_segments, 119)

    def test_compare_segmentations(self):
            #compare results from two segmentation algorithms
            G = self.wn2.to_graph()
            
            strategic_valve_layer = wntr.network.generate_valve_layer(
                self.wn2, 'strategic', 1, seed = 123
                )

            (node_segments, 
            link_segments, 
            segment_size) = wntr.metrics.valve_segments(G, strategic_valve_layer)

            (old_node_segments, 
            old_link_segments, 
            old_segment_size) = matrix_valve_segments(G, strategic_valve_layer)

            # basic length checks
            self.assertEqual(len(old_node_segments), len(node_segments))
            self.assertEqual(len(old_link_segments), len(link_segments))
            self.assertEqual(len(old_segment_size), len(segment_size))

            """
            Warning: the following three tests assumes that algorithms output 
            same labels for segment classes, which may not always be the case.
            If this test fails, consider looking into a comparison
            that checks if segment groups are the same, rather
            than exact labelling.
            TODO: use a set-of-sets approach to properly compare
            segmentations without relying on above assumption.
            """
            for link in link_segments.index:
                self.assertEqual(
                    link_segments.loc[link],
                    old_link_segments.loc[link]
                    )

            for node in node_segments.index:
                self.assertEqual(
                    node_segments.loc[node],
                    old_node_segments.loc[node]
                    )

            # check segment sizes
            for k in segment_size.index:
                self.assertTrue(
                    (old_segment_size.loc[k]==segment_size.loc[k]).all()
                    )

def matrix_valve_segments(G, valve_layer):
    """
    Valve segmentation
    This is the original wntr implementation of a segmentation
    method. It is here primarily for use as a "checker" for the
    connected components implementation.

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
    AC = nx.incidence_matrix(uG).astype('int').todense().T
    AC = pd.DataFrame(AC, columns=matrix_node_names, index=matrix_link_names, dtype=int)
    
    # Valve-node connectivity matrix
    VC = pd.DataFrame(0, columns=matrix_node_names, index=matrix_link_names)
    for i, row in valve_layer.iterrows():
        VC.at['L_'+row['link'], 'N_'+row['node']] = 1
    
    # Valve deficient matrix (anti-valve matrix)
    VD = AC - VC
    del AC, VC
    
    # Direct connectivity matrix
    NI = pd.DataFrame(np.identity(len(matrix_node_names)),
                      index = matrix_node_names, columns = matrix_node_names)
    LI = pd.DataFrame(np.identity(len(matrix_link_names)),
                      index = matrix_link_names, columns = matrix_link_names)
    DC_left = pd.concat([NI, VD], sort=False)
    DC_right = pd.concat([VD.T, LI], sort=False)
    del LI, VD
    DC = pd.concat([DC_left, DC_right], axis=1, sort=False)
    del DC_left, DC_right
    DC = DC.astype(int)

    # initialization for looping routine
    seg_index = 0
    
    # pre-processing to find isolated elements before looping
    seg_label = {}

    # find links with valves on either end -kb
    for start_node, end_node, link_name in links:
        link_valves = valve_layer[valve_layer['link']==link_name]
        if set(link_valves['node']) >= set([start_node, end_node]):
            seg_index += 1
            seg_label['L_'+link_name] = seg_index

    # find nodes with valves
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
    # transpose to align with numpy's row major default
    DC_np = DC_np.transpose()
    # vector of length nodes+links where the ith entry is the segment number of node/link i
    seg_label_DC = np.zeros(shape=(len(DC.index)), dtype=int)

    # Loop over all nodes and links to grow segments
    for i in range(seg_label_DC.shape[0]):
        
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
                # p_seg_DC = DC_np + seg_DC # this is slow
                connected_to_seg = np.sum(
                    DC_np[:,seg_DC.nonzero()[0]],axis=1
                    ).nonzero()[0]

                # Nodes and links that are connected to the segment
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
                seg_DC = np.zeros(seg_DC.shape)
                seg_DC[DC_np[i,:].nonzero()] = 1
                seg_DC[np.sum(DC_np[connected_to_seg,:],axis=0).nonzero()[0]] = 1
                # test = set(DC_np[i,:].nonzero()[0])<=set(np.sum(p_seg_DC[connected_to_seg,:],axis=0).nonzero()[0])
                # print("LOG index comparison: "+str(test))

                # seg_DC = np.clip(seg_DC,0,1)       
                DC_np[connected_to_seg,:] = seg_DC
    
            # print(i, seg_size)
    
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

if __name__ == "__main__":
    unittest.main()
