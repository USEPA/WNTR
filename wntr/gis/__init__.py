"""
The wntr.gis package contains methods to convert between water network models
and GIS formatted data and geospatial functions to snap data and find intersections.
"""
from wntr.gis.network import WaterNetworkGIS, wn_to_gis, gis_to_wn
from wntr.gis.geospatial import snap_points_to_points, snap_points_to_lines, \
    intersect_points_with_polygons, intersect_lines_with_polygons

