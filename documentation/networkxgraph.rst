NetworkX graph
======================================

WNTR uses NetworkX data objects to store network connectivity as a graph.  
NetworkX includes numerous methods to analyze the structure of complex networks.
For more information on NetworkX, see https://networkx.github.io/.

WNTR includes a custom Graph Class, 
:doc:`WntrMultiDiGraph</apidoc/wntr.network.WntrMultiDiGraph>`. 
This class inherits from NetworkX MulitDigraph and includes additional methods 
that are specific to WNTR. The graph stores the start 
and end node of each link, node coordinates, and node and link types. 
WNTR updates the graph as elements are added and removed from the water network model.  
The example **networkx_graph.py** can be used to generate a graph from a water network model.

A copy of the graph can an be obtained using the following function.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 7
	
The graph is stored as a nested dictionary.  The nodes and edges of the graph 
can be accessed using the following.

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 9-11

The graph can be used to access NetworkX methods, for example

.. literalinclude:: ../examples/networkx_graph.py
   :lines: 2,13-16