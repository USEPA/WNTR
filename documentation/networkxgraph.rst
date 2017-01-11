NetworkX graph
======================================

WNTR uses NetworkX data objects to store network connectivity as a graph.  
The graph stores the start and end node of each link, node coordinates, and node and link types. 
WNTR updates the graph as elements are added and removed from the water network model.  
NetworkX includes numerous methods to analyze the structure of complex networks.
For more information on NetworkX, see https://networkx.github.io/.
WNTR includes a custom Graph Class, 
:doc:`WntrMultiDiGraph</apidoc/wntr.network.WntrMultiDiGraph>`. 
This class inherits from NetworkX MulitDigraph and includes additional methods 
that are specific to WNTR. 
The example **networkx_graph.py** can be used to generate a graph from a water network model.

A copy of the graph can an be obtained using the following function.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 8
	
The graph is stored as a nested dictionary.  The nodes and links (note that links are called `edges` in the graph)
can be accessed using the following.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 10-12

The graph can be used to access NetworkX methods, for example

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 3,14-17