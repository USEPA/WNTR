.. raw:: latex

    \clearpage

.. doctest::
    :hide:

    >>> import wntr
    >>> import numpy as np
    >>> from __future__ import print_function
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')
	
Graphics
======================================

The :class:`wntr.graphics` module includes several functions to plot water network models and plot 
fragility and pump curves.

Networks
--------------------
Basic network graphics can be generated using the 
function :class:`~wntr.graphics.plot_network`.
This function requires matplotlib and networkx (both required dependencies of WNTR).  
The user can supply a wide range of plotting attributes, including
node attributes, node size, node colormap and range, 
link attributes, link width, and link colormap and range.

The following example plots the network along with node elevation.

.. doctest::

    >>> wntr.graphics.plot_network(wn, node_attribute='elevation')

.. _fig-overview:
.. figure:: figures/plot_network.png
   :scale: 100 %
   :alt: Network
   
   Example basic network graphic.
   
Interactive networks
---------------------------------

Interactive network graphics can be generated using the 
function :class:`~wntr.graphics.plot_interactive_network`.
**This function requires the Python package plotly, which is an optional dependency of WNTR.**  
This function produces an HTML file that the user can pan, zoom, and hover-over network elements.
The user can supply a wide range of plotting attributes, including
node attributes, node size, and node colormap and range, and link width  However, 
link attributes currently cannot be displayed on the graphic.

For example, ...

.. doctest::

    >>> wntr.graphics.plot_interactive_network(wn, node_attribute='elevation')

.. _fig-overview:
.. figure:: figures/plot_interactive_network.png
   :scale: 100 %
   :alt: Network
   
   Example interactive network graphic.
   
Interactive Leaflet networks
------------------------------------------
Interactive Leaflet network graphics can be generated using the 
function :class:`~wntr.graphics.plot_leaflet_network`.
**This function requires the Python package folium, which is an optional dependency of WNTR.** 
This function produces an HTML file that overlays the network model onto a Leaflet map.
The network model should have coordinates in latitude, longitude.  
See :ref:`modify_node_coords` for more information on converting node coordinates to latitude, longitude.
The user can supply a wide range of plotting attributes, including
node attributes, node size, node colormap and range, 
link attributes, link width, and link colormap and range.

For example, ...

.. doctest::

    >>> wntr.graphics.plot_leaflet_network(wn)

.. _fig-overview:
.. figure:: figures/plot_leaflet_network.png
   :scale: 50 %
   :alt: Network
   
   Example interactive Leaflet network graphic.
   
Fragility curves
-----------------


.. doctest::

    >>> from scipy.stats import lognorm
    >>> FC = wntr.scenario.FragilityCurve()
    >>> FC.add_state('Minor', 1, {'Default': lognorm(0.5,scale=0.3)})
    >>> FC.add_state('Major', 2, {'Default': lognorm(0.5,scale=0.7)}) 
    >>> wntr.graphics.plot_fragility_curve(FC, xlabel='Peak Ground Acceleration (g)')

.. _fig-fragility:
.. figure:: figures/fragility_curve.png
   :scale: 100 %
   :alt: Fragility curve

   Example fragility curve.
   
Pump curves
-----------------

.. doctest::

    >>> pump = wn.get_link('10')
    >>> wntr.graphics.plot_pump_curve(pump)

.. _fig-fragility:
.. figure:: figures/plot_pump_curve.png
   :scale: 100 %
   :alt: Pump curve

   Example pump curve.
   