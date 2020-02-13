.. raw:: latex

    \clearpage
	
Data layers
======================================

Data layers contain data which is not part of the water network model or graph, but can be used in analysis.
Currently, WNTR includes a data format for valve layers, additional data layers can be added in the future.

.. _valve_layer:

Valve layer
------------

While valves are typically included in the water network model, the user can also define a valve layer to be used in additional analysis.
If the valves are not used in the hydraulic analysis, this can help reduce the size of the network.
A valve layer can be used to groups links and nodes into segments based on the location of isolation valves.
In a valve layer, each valve is defined by a node and link pair (for example, valve 0 is on link 333 and protects node 601).
WNTR includes a method to generate valve layers based on random or strategic placement.  The strategic placement specifies the number 
of pipes (n) from each node that do not contain a valve.  In this case, n is generally 0, 1 or 2 (i.e. N, N-1, N-2 valve placement).

The following example generates a random valve placement with 40 valves.

.. doctest::
    :hide:

    >>> import wntr
    >>> import networkx as nx
    >>> import numpy as np
    >>> import matplotlib.pylab as plt
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')

    
.. doctest::

    >>> valve_layer = wntr.network.generate_valve_layer(wn, 'random', 40)
    
The valve layer can be included in water network graphics, as shown below.

.. doctest::

    >>> nodes, edges = wntr.graphics.plot_network(wn, node_size=7, valve_layer=valve_layer)
    
.. doctest::
    :hide:

    >>> plt.tight_layout()
    >>> plt.savefig('valve_layer.png', dpi=300)
    
.. _fig-network:
.. figure:: figures/valve_layer.png
   :width: 640
   :alt: Network
   
   Example N-1 valve layer.