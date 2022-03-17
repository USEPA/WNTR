.. raw:: latex

    \clearpage
	
GIS capabilities
======================================

Convert a model to GeoDataFrames
---------------------------------------------------

- convert wn to gpd

.. doctest::
    :hide:

    >>> import wntr
    >>> import numpy as np
    >>> import pandas as pd
	>>> import geopandas as gpd
    >>> import matplotlib.pylab as plt
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net1.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net1.inp')
	
.. doctest::
	
    >>> wn_gis = wntr.gis.network.wn_to_gis(wn)
	
	
	
- write gpd to geojson, shapefiles
- create wn from gpd (topography only)


Work with geospatial data
-------------------------------

- Snap point to water network point. 

.. doctest::
    :hide:
	
    >>> points = [(48.2,37.2), (70.8,69.3), (54.5, 40.5), (51.2, 71.1), (32.1, 67.6), (51.7, 87.3)]
    >>> point_data = []
    >>> for i, pts in enumerate(points):
    ...     geometry = Point(pts)
    ...     point_data.append({'geometry': geometry})            
    >>> points = gpd.GeoDataFrame(DataFrame(point_data), crs=None)

.. doctest::

    >>> snapped_points = wntr.gis.snap_points_to_points(points, wn_gis, tolerance=5.0)
    >>> print(snapped_points.head(1))
		node	snap_distance	geometry
	0	22	3.33		POINT(50,40)
	
   
- Snap point to water network line. This can be used to snap valves to a network, which can then be used to assign each link/node a valve segment.

.. doctest::

    >>> snapped_points = wntr.gis.snap_points_to_lines(points, wn_gis, tolerance=5.0)
    >>> print(snapped_points.head(1))
		link	node	snap_distance	distance_along_line	geometry
	0	122	22	1.8		0.09			POINT(50,37.2)
    >>> G = wn.get_graph()
    >>> node_segments, link_segments, segment_size = wntr.metric.topographic.valve_segments(G,snapped_points)
    
.. _fig-snapped_points:
.. figure:: figures/snapped_points.png
   :width: 600
   :alt: Snapped points to points or lines

   Example snapped points to points (junctions) or lines (links).

   
- intersect polygon with water network point
- intersect polygon with water network line

