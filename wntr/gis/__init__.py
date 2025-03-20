"""
The wntr.gis package contains methods to convert between water network models
and GIS formatted data and geospatial functions to snap data and find intersections.
"""
from wntr.gis.network import WaterNetworkGIS
from wntr.gis.geospatial import snap, intersect, sample_raster

