"""
The wntr.gis.geospatial module contains functions to snap data and find 
intersects with polygons.
"""
import os.path
import warnings

import pandas as pd
import numpy as np

try:
    from shapely.geometry import MultiPoint, LineString, Point, shape

    has_shapely = True
except ModuleNotFoundError:
    has_shapely = False

try:
    import geopandas as gpd

    has_geopandas = True
except ModuleNotFoundError:
    gpd = None
    has_geopandas = False


def snap_points_to_points(points, wn_points, tolerance):
    """
    Returns new points with coordinates snapped to nearest junctions in the network.

    Parameters
    ----------
    points : GeoPandas GeoDataFrame
        A pandas.DataFrame object with a 'geometry' column populated by 
        'POINT' geometries.
    wn_points : GeoPandas GeoDataFrame
        A pandas.DataFrame object with a 'geometry' column populated by 
        'POINT' geometries.
    tolerance : float
        the maximum allowable distance (in the junction coordinate system) 
        to search for a junction from a point and nearby junctions.

    Returns
    -------
    GeoPandas GeoDataFrame
        Snapped points (index = point index, columns = stats)
        Columns include:
            - Node: closest node to each point
            - Geometry: GeoPandas Point object of each point snapped to the nearest node
            - Snap_distance: distance between original and snapped points
            - Elevation: snapped point elevation 

    """       
    isinstance(points, gpd.GeoDataFrame)
    assert(points['geometry'].geom_type).isin(['Point']).all()
    isinstance(wn_points, gpd.GeoDataFrame)
    assert(wn_points['geometry'].geom_type).isin(['Point']).all()

    # modify lines dataframe to include "name" as a separate column
    wn_points = wn_points.reset_index()  
    # save node geometries in another column
    wn_points["node_geom"] = wn_points.geometry
    snapped_points = points.sjoin_nearest(wn_points, how="left", max_distance=tolerance)
    # calculate distance between "geometry" and "node_geom"
    snapped_points["snap_distance"] = snapped_points.geometry.distance(gpd.GeoSeries(snapped_points.node_geom, crs=wn_points.crs))
    snapped_points.geometry = snapped_points["node_geom"]
    wn_points.drop("node_geom", inplace=True, axis=1)
    snapped_points = snapped_points.rename(columns={"name":"node"})
    snapped_points = snapped_points[["node", "geometry", "snap_distance", "elevation"]] # "n" (# points within tolerance)
    snapped_points = gpd.GeoDataFrame(snapped_points, geometry="geometry")    
    snapped_points.index.name = 'name'
    return snapped_points
    
def snap_points_to_lines(points, wn_lines, tolerance):
    """
    Returns new points with coordinates snapped to the nearest lines.

    Parameters
    ----------
    points : GeoPandas GeoDataFrame
        A pandas.DataFrame object with a 'geometry' column populated by 
        'POINT' geometries.
    wn_lines : GeoPandas GeoDataFrame
        A pandas.DataFrame object with a 'geometry' column populated by 
        'LINESTRING' or 'MULTILINESTRING' geometries.
    tolerance : float
        the maximum allowable distance (in the line coordinate system) 
        between a point and nearby line to move the point to the line.
    
    Returns
    -------
    GeoPandas GeoDataFrame
        Snapped points (index = point index, columns = stats)
        Columns include:
            - Link: closest line to each point
            - Node: start or end node closest to the point along the line
            - Geometry: GeoPandas Point object each point snapped to the nearest point on closest lines
            - Snap_distance: distance between original and snapped points
            - Distance_along_line: normalized distance of snapped points along the lines from the start node (0.0) and end node (1.0)
    """   
    isinstance(points, gpd.GeoDataFrame)
    assert(points['geometry'].geom_type).isin(['Point']).all()
    isinstance(points, gpd.GeoDataFrame)
    assert(wn_lines['geometry'].geom_type).isin(['LineString','MultiLineString']).all()
    
    # modify lines dataframe to include "name" as a separate column
    wn_lines = wn_lines.reset_index()
    # determine how far to look around each point for lines
    bbox = points.bounds + [-tolerance, -tolerance, tolerance, tolerance]       
    # determine which links are close to each point
    hits = bbox.apply(lambda row: list(wn_lines.loc[list(wn_lines.sindex.intersection(row))]['name']), axis=1)        
    closest = pd.DataFrame({
        # index of points table
        "point": np.repeat(hits.index, hits.apply(len)),
        # name of link
        "name": np.concatenate(hits.values)
        })
    # Merge the closest dataframe with the lines dataframe on the line names
    closest = pd.merge(closest, wn_lines, on="name")
    # rename the line "name" column header to "link"
    closest = closest.rename(columns={"name":"link"})
    # Join back to the original points to get their geometry
    # rename the point geometry as "points"
    closest = closest.join(points.geometry.rename("points"), on="point")
    # Convert back to a GeoDataFrame, so we can do spatial ops
    closest = gpd.GeoDataFrame(closest, geometry="geometry", crs=wn_lines.crs)    
    # Calculate distance between the point and nearby links
    closest["snap_distance"] = closest.geometry.distance(gpd.GeoSeries(closest.points, crs=wn_lines.crs))
    # Sort on ascending snap distance, so that closest goes to top
    closest = closest.sort_values(by=["snap_distance"])        
    # group by the index of the points and take the first, which is the closest line
    closest = closest.groupby("point").first()        
    # construct a GeoDataFrame of the closest lines
    closest = gpd.GeoDataFrame(closest, geometry="geometry", crs=wn_lines.crs)
    # position of nearest point from start of the line
    pos = closest.geometry.project(gpd.GeoSeries(closest.points))        
    # get new point location geometry
    snapped_points = closest.geometry.interpolate(pos)
    snapped_points = gpd.GeoDataFrame(data=closest ,geometry=snapped_points, crs=wn_lines.crs)
    # determine whether the snapped point is closer to the start or end node
    snapped_points["distance_along_line"] = closest.geometry.project(snapped_points, normalized=True)
    snapped_points.loc[snapped_points["distance_along_line"]<0.5, "node"] = closest["start_node_name"]
    snapped_points.loc[snapped_points["distance_along_line"]>=0.5, "node"] = closest["end_node_name"]
    snapped_points = snapped_points.reindex(columns=["link", "node", "geometry", "snap_distance", "distance_along_line"])
    snapped_points.index.name = 'name'
    return snapped_points


def _intersect(elements, polygons, column):
   
    isinstance(polygons, gpd.GeoDataFrame)
    
    intersects = gpd.sjoin(elements, polygons, op='intersects')
    
    n = intersects.groupby('name')[column].count()
    val_sum = intersects.groupby('name')[column].sum()
    val_min = intersects.groupby('name')[column].min()
    val_max = intersects.groupby('name')[column].max()
    val_average = intersects.groupby('name')[column].mean()
    
    polygon_indices = intersects.groupby('name')['index_right'].apply(list)
    polygon_values = intersects.groupby('name')[column].apply(list)

    
    stats = pd.DataFrame(index=elements.index, data={'N': n,
                                                     'Sum': val_sum,
                                                     'Min': val_min, 
                                                     'Max': val_max, 
                                                     'Average': val_average,
                                                     'Polygons': polygon_indices,
                                                     'Values': polygon_values})
    
    stats['N'] = stats['N'].fillna(0)
    stats.loc[stats['Polygons'].isnull(), 'Polygons'] = stats.loc[stats['Polygons'].isnull(), 'Polygons'] .apply(lambda x: [])
    stats.loc[stats['Values'].isnull(), 'Values'] = stats.loc[stats['Values'].isnull(), 'Values'] .apply(lambda x: [])
    
    return stats


def intersect_points_with_polygons(points, polygons, column):
    """
    Identify polygons that intersect points and return statistics on the 
    intersecting polygon values.
    
    Each polygon is assigned a value based on a column of data in the polygons
    GeoDataFrame.  The function returns information about the intersection 
    for each point. 
    
    Parameters
    ----------
    points : geopandas GeoDataFrame
        GeoDataFrame containing Point geometries, generally a GeoDataFrame 
        containing water network junctions, tanks, or reservoirs
    polygons : geopandas GeoDataFrame
        GeoDataFrame containing Polygon or MultiPolygon geometries
    column : str
        Column name in the polygons GeoDataFrame used to assign a value to each 
        polygon.
    
    Returns
    -------
    pandas DataFrame
        Intersection statistics (index = point names, columns = stats)
        Columns include:
            - N: number of intersecting polygons
            - Sum: sum of the intersecting polygon values
            - Min: minimum value of the intersecting polygons
            - Max: maximum value of the intersecting polygons
            - Average: average value of the intersecting polygons
            - Polygons: list of intersecting polygon names
            - Values: list of intersecting polygon values
    
    """
    
    isinstance(points, gpd.GeoDataFrame)
    assert (points['geometry'].geom_type).isin(['Point']).all()
    isinstance(polygons, gpd.GeoDataFrame)
    assert (polygons['geometry'].geom_type).isin(['Polygon', 'MultiPolygon']).all()
    isinstance(column, str)
    assert column in polygons.columns
    
    stats = _intersect(points, polygons, column)
    return stats


def intersect_lines_with_polygons(lines, polygons, column):
    """
    Identify polygons that intersect lines and return statistics on the 
    intersecting polygon values.
    
    Each polygon is assigned a value based on a column of data in the polygons
    GeoDataFrame.  The function returns information about the intersection 
    for each line, including the weighted average (based on intersection length). 
    
    Parameters
    ----------
    lines : geopandas GeoDataFrame
        GeoDataFrame containing LineString or MultiLineString geometries, 
        generally a GeoDataFrame containing water network pipes
    polygons : geopandas GeoDataFrame
        GeoDataFrame containing Polygon or MultiPolygon geometries
    column : str
        Column name in the polygons GeoDataFrame used to assign a value to each 
        polygon.
    
    Returns
    -------
    pandas DataFrame
        Intersection statistics (index = point names, columns = stats)
        Columns include:
            - N: number of intersecting polygons
            - Sum: sum of the intersecting polygon values
            - Min: minimum value of the intersecting polygons
            - Max: maximum value of the intersecting polygons
            - Average: average value of the intersecting polygons
            - Weighted average: weighted average value of the intersecting polygons (based on intersection length)
            - Polygons: list of intersecting polygon names
            - Values: list of intersecting polygon values
    
    """

    isinstance(lines, gpd.GeoDataFrame)
    assert (lines['geometry'].geom_type).isin(['LineString', 'MultiLineString']).all()
    isinstance(polygons, gpd.GeoDataFrame)
    assert (polygons['geometry'].geom_type).isin(['Polygon', 'MultiPolygon']).all()
    isinstance(column, str)
    assert column in polygons.columns
    #isinstance(return_weighted_average, bool)
    
    stats = _intersect(lines, polygons, column)
    
    stats['Weighted Average'] = 0
    line_length = lines.length
    for i in polygons.index:
        polygon = gpd.GeoDataFrame(polygons.loc[[i],:], crs=None)
        lines_subset = lines.loc[stats['Polygons'].apply(lambda x: i in x),:]
        #print(i, lines_subset)
        clip = gpd.clip(lines_subset, polygon) 
            
        if len(clip.index) > 0:
            val = float(polygon[column])
            
            weighed_val = clip.length/line_length[clip.index]*val
            assert (weighed_val <= val).all()
            stats.loc[clip.index, 'Weighted Average'] = stats.loc[clip.index, 'Weighted Average'] + weighed_val
            
    stats['Weighted Average'] = stats['Weighted Average']/stats['N']
    
    return stats