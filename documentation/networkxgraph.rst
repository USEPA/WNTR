NetworkX graph
======================================

WNTR uses NetworkX data objects to store network connectivity as a graph.  
A **graph** is a collection of nodes that are connected by links.  
For water networks, nodes represent junctions, tanks, and reservoirs while links represent pipes, pumps, and valves.

Water networks are stored as directed multigraphs. 
A **directed multigraph** is a graph with direction associated with links and 
the graph can have multiple links with the same start and end node. 
A simple example is shown in :numref:`fig-graph`.
For water networks, the link direction is from the start node to the end node. 
The link direction is used as a reference to track flow direction in the network.
Multiple links with the same start and end node can be used to represent redundant pipes or backup pumps.
In WNTR, the graph stores 
the start and end node of each link, 
the node coordinates, 
and node and link types (i.e tank, reservoir, valve). 
WNTR updates the graph as elements are added and removed from the water network model.  

.. _fig-graph:
.. figure:: figures/graph.png
   :scale: 75 %
   :alt: Directed multigraph

   Example directed multigraph.
   
NetworkX includes numerous methods to analyze the structure of complex networks.
For more information on NetworkX, see https://networkx.github.io/.
WNTR includes a custom Graph Class, 
:meth:`~wntr.network.graph.WntrMultiDiGraph`.
This class inherits from NetworkX MulitDigraph and includes additional methods 
that are specific to WNTR. 
The example **networkx_graph.py** can be used to generate a graph from a water network model.
  
A copy of the graph can an be obtained using the following function.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 9
	
The graph is stored as a nested dictionary.  The nodes and links (note that links are called `edges` in NetworkX)
can be accessed using the following.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 12-14

The graph can be used to access NetworkX methods, for example

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 3,17-20
  
Some methods in NetworkX require that networks are undirected.  
A **undirected graph** is a graph with no direction associated with links.
The following NetworkX method can be used to convert a directed graph to an undirected graph.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 23

Some methods in NetworkX require that networks are connected.     
A **connected graph** is a graph where a path exists between every node in the network (i.e. no node is disconnected).  
The following NetworkX method can be used to check if a graph is connected.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 26

Some methods in NetworkX can use weighted graphs.
A **weighted graph** is a graph in which each link is given a weight.  
The WNTR method :meth:`~wntr.network.graph.WntrMultiDiGraph.weight_graph` can be used to weight the graph by any attribute.
In the following example, the graph is weighted by length.  This graph can then be used to compute path lengths.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 29-30
	