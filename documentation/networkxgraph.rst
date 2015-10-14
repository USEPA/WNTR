NetworkX graph
======================================

WNTR uses NetworkX data objects to store network connectivity as a graph.  
NetworkX includes numerous methods to analyse the structure of complex networks.
For more infomation on NetworkX, see https://networkx.github.io/.

WNTR includes a custom Graph Class, 
:doc:`WntrMultiDiGraph</apidoc/wntr.network.WntrMultiDiGraph>`. 
This class inherits from NetworkX MulitDigraph and includes additional methods 
that are specific to WNTR. The graph stores the start 
and end node of each link, node coordinates, and node and link types. 
WNTR updates the graph as elements are added and removed from the water network model.  
A copy of the graph can an be obtained using the following function::

	>>> G = wn.get_graph_deep_copy()
	
The graph is stored as a nested dictonary.  The nodes and edges of the graph 
can be accessed using the following::

	>>> G.node[name]
	{'type': 'junction', 'pos': (42.11, 8.67)}
	>>> G.edge[name]
	{'225': {'257': {'type': 'pipe'}}, '219': {'251': {'type': 'pipe'}}}

where 'name' is a node name.

The graph can be used to access NetworkX methods, for example::

	>>> import networkx as nx
	>>> node_degree = G.degree()
	>>> bet_cen = nx.betweenness_centrality(G)