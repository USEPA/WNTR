.. raw:: latex

    \clearpage

Network morphology
======================================

The water network model morphology can be modified is several ways using WNTR, including
network skeletonization and modifying node coordinates.

Network skeletonization
----------------------------
The goal of network skeletonization is to reduce the size of a water network model with minimal impact on system behavoir.
Network skeletonization in WNTR follows the procedure outlined in [WCSG03]_.  
The skeletonization process retains all tanks, reservoirs, valves, and pumps, along with all junctions and pipes that are associated with controls.
Junction demands and demand patterns are retained in the skeletonized model, as described below.
Pipes that falls below a user defined pipe diameter threshold are candidates for removal based on three operations, including:

1. **Branch trimming**: Dead-end pipes that are below the pipe diameter threshold are removed from the model (:numref:`fig-branch-trim`).  
   The demand and demand pattern assigned to the dead-end junction is moved to the junction that is retained in the model.  
   Dead-end pipes that are connected to tanks or reservoirs cannot be removed from the model.
   
	.. _fig-branch-trim:
	.. figure:: figures/skel_branch.png
	   :scale: 100 %
	   :alt: Branch trim
	   
	   Branch trimming.
	  
2. **Series pipe merge**: Pipes in series are merged if both pipes are below the pipe diameter threshold (:numref:`fig-series-merge`).  
   The demand and demand pattern assigned to the connecting junction is moved to the nearest junction that is retained in the model.
   The merged pipe is assigned the following equivalent properties:
   
   .. math:: D_{m} = max\left(D_{1}, D_{2}\right)
   .. math:: L_{m} = L_{1} + L_{2}
   .. math:: C_{m} = \left(\frac{L_{m}}{{D_{m}}^{4.87}}\right)^{0.54}\left(\frac{L_{1}}{{D_{1}}^{4.87}{C_{1}}^{1.85}}+\frac{L_{2}}{{D_{2}}^{4.87}{C_{2}}^{1.85}}\right)^{-0.54}
   
   where 
   :math:`D_{m}` is the diameter of the merged pipe, :math:`D_{1}` and :math:`D_{2}` are the diameters of the original pipes, 
   :math:`L_{m}` is the length of the merged pipe, :math:`L_{1}` and :math:`L_{2}` are the lengths of the original pipes, 
   :math:`C_{m}` is the Hazen-Williams roughness coefficient of the merged pipe, and :math:`C_{1}` and :math:`C_{2}` are the Hazen-Williams roughness coefficients of the original pipes. 
   Note, if the original pipes have the same diameter, :math:`D_{m}` is based on the pipe name that comes first in alphabetical order.
   Minor loss and pipe status of the merged pipe are set equal to minor loss and pipe status for the pipe selected for max diameter.
   
	.. _fig-series-merge:
	.. figure:: figures/skel_series.png
	   :scale: 100 %
	   :alt: Series merge
	   
	   Series pipe merge.
	   
3. **Parallel pipe merge**: Pipes in parallel are merged if both pipes are below the pipe diameter threshold (:numref:`fig-parallel-merge`).  
   This operation does not reduce the number of junctions in the system.
   The merged pipe is assigned the following equivalent properties:
   
   .. math:: D_{m} = max\left(D_{1}, D_{2}\right)
   .. math:: L_{m} = \text{Length of the pipe selected for max diameter}
   .. math:: C_{m} = \left(\frac{L_{m}^{0.54}}{{D_{m}}^{2.63}}\right)\left(\frac{C_{1}{D_{1}}^{2.63}}{{L_{1}}^{0.54}}+\frac{C_{2}{D_{2}}^{2.63}}{{L_{2}}^{0.54}}\right)
   
   where
   :math:`D_{m}` is the diameter of the merged pipe, :math:`D_{1}` and :math:`D_{2}` are the diameters of the original pipes, 
   :math:`L_{m}` is the length of the merged pipe, :math:`L_{1}` and :math:`L_{2}` are the lengths of the original pipes, 
   :math:`C_{m}` is the Hazen-Williams roughness coefficient of the merged pipe, and :math:`C_{1}` and :math:`C_{2}` are the Hazen-Williams roughness coefficients of the original pipes. 
   Note, if the original pipes have the same diameter, :math:`D_{m}` is based on the pipe name that comes first in alphabetical order.
   Minor loss and pipe status of the merged pipe are set equal to minor loss and pipe status for the pipe selected for max diameter.
   
   .. _fig-parallel-merge:
   .. figure:: figures/skel_parallel.png
      :scale: 100 %
      :alt: Parallel merge
	  
      Parallel pipe merge
	  
The :class:`~wntr.network.morph.skeletonize` function is used to perform network skeletonization.
The iterative algorithm first loops over all candidate pipes (pipes below the pipe diameter threshold) and removes branch pipes.  
Then the algorithm loops over all candidate pipes and merges pipes in series.
Finally, the algorithm loops over all candidate pipes and merges pipes in parallel.
This initial set of operations can generate new branch pipes, pipes in series, and pipes in parallel.
This cycle repeats until the network can no longer be reduced.  
The user can specify if branch trimming, series pipe merge, and/or parallel pipe merge should be included in the skeletonization operations.  
The user can also specify a maximum number of cycles to include in the process.

Results from network skeletonization include the skeletonized water network model and (optionally) 
a "skeletonization map" which maps original network nodes to skeletonized network nodes.  
The skeletonization map is a dictionary where 
the keys are original network nodes and 
the values are a list of nodes in the skeletonized network that were merged as a result of skeletonization operations.  
For example, if 'Junction 1' was merged into 'Junction 2' as 
part of network skeletonization, then the skeletonization map would contain the following information::

	{
	'Junction 1': [],
	'Junction 2': ['Junction 1', 'Junction 2']
	}

This map indicates that the skeletonized network does not contain 'Junction 1', and that 'Junction 2' in the 
skeletonized network is the merged product of the original 'Junction 1' and 'Junction 2'.  
'Junction 2' in the skeletonized network will therefore contain demand and demand patterns from 
the original 'Junction 1' and 'Junction 2'

The following example performs network skeletonization on Net6 using a pipe diameter threshold of 12 inches.
The skeletonization procedure reduces the number of nodes in the network from approximately 3000 to approximately 1000 (:numref:`fig-skel-example`).
After simulating hydraulics on both the original and skeletonized network, node pressure can be compared to 
determine how skeletonization impacts system behavoir. :numref:`fig-skel-hydraulics` shows the median (dark blue line) and 
the 25th to 75th percentile (shaded region) for node pressure throughout the network over a 4 day simulation.
Pressure differences are generally less than 2 meters in this example.

.. doctest::
    :hide:

    >>> import wntr
    >>> import numpy as np
    >>> from __future__ import print_function
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net6.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net6.inp')
    ...

.. doctest::

    >>> skel_wn = wntr.network.morph.skeletonize(wn, 12*0.0254)
    >>> wntr.graphics.plot_network(wn, title='Original') # #doctest: +ELLIPSIS
	(<matplotlib.collections.PathCollection object ...
    >>> wntr.graphics.plot_network(skel_wn, title='Skeletonized') #doctest: +ELLIPSIS
	(<matplotlib.collections.PathCollection object ...
	
.. _fig-skel-example:
.. figure:: figures/skel_example.png
   :scale: 100 %
   :alt: Skeletonization example
   
   Original and skeletonized Net6.

.. doctest::

    >>> sim = wntr.sim.EpanetSimulator(wn)
    >>> results_original = sim.run_sim()
    >>> sim = wntr.sim.EpanetSimulator(skel_wn)
    >>> results_skel = sim.run_sim()
    >>> pressure_orig = results_original.node['pressure'].loc[:,skel_wn.junction_name_list]
    >>> pressure_skel = results_skel.node['pressure'].loc[:,skel_wn.junction_name_list]
    >>> pressure_diff = abs(pressure_orig - pressure_skel)

.. _fig-skel-hydraulics:
.. figure:: figures/skel_hydraulics.png
   :scale: 100 %
   :alt: Skeletonization example
   
   Pressure differences between the original and skeletonized Net6.


Modifying node coordinates
----------------------------

WNTR includes several functions to modify node coordinates, including:

1. Scale node coordinates
2. Shift node coordinates
3. Rotate node coordinates
4. Translate node coordinates
5. Convert node coordinates from lat-long to UTM

