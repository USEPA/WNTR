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

def _snap(points, wn_elements, tolerance):    
    # modify lines dataframe to include "name" as a separate column
    wn_elements = wn_elements.reset_index()
    # determine how far to look around each point for lines
    bbox = points.bounds + [-tolerance, -tolerance, tolerance, tolerance]       
    # determine which links are close to each point
    hits = bbox.apply(lambda row: list(wn_elements.loc[list(wn_elements.sindex.intersection(row))]['name']), axis=1)        
    closest = pd.DataFrame({
        # index of points table
        "point": np.repeat(hits.index, hits.apply(len)),
        # name of link
        "name": np.concatenate(hits.values)
        })
    # Merge the closest dataframe with the lines dataframe on the line names
    closest = pd.merge(closest, wn_elements, on="name")
    # rename the line "name" column header to "link"
    closest = closest.rename(columns={"name":"wn_element"})
    # Join back to the original points to get their geometry
    # rename the point geometry as "points"
    closest = closest.join(points.geometry.rename("points"), on="point")
    # Convert back to a GeoDataFrame, so we can do spatial ops
    closest = gpd.GeoDataFrame(closest, geometry="geometry", crs=wn_elements.crs)    
    # Calculate distance between the point and nearby links
    closest["snap_distance"] = closest.geometry.distance(gpd.GeoSeries(closest.points, crs=wn_elements.crs))
    # Sort on ascending snap distance, so that closest goes to top
    closest = closest.sort_values(by=["snap_distance"])        
    # group by the index of the points and take the first, which is the closest line
    closest = closest.groupby("point").first()        
    # construct a GeoDataFrame of the closest lines
    closest = gpd.GeoDataFrame(closest, geometry="geometry", crs=wn_elements.crs)
    return closest

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
    
    snapped_points = _snap(points, wn_points, tolerance)
    snapped_points = snapped_points.rename(columns={"wn_element":"node"})
    snapped_points = snapped_points.reindex(columns=["node", "snap_distance", "geometry"])
    snapped_points.index.name = None #'name'
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
    
    closest = _snap(points, wn_lines, tolerance)
    closest = closest.rename(columns={"wn_element":"link"})
    # position of nearest point from start of the line
    pos = closest.geometry.project(gpd.GeoSeries(closest.points))        
    # get new point location geometry
    snapped_points = closest.geometry.interpolate(pos)
    snapped_points = gpd.GeoDataFrame(data=closest ,geometry=snapped_points, crs=wn_lines.crs)
    # determine whether the snapped point is closer to the start or end node
    snapped_points["distance_along_line"] = closest.geometry.project(snapped_points, normalized=True)
    snapped_points.loc[snapped_points["distance_along_line"]<0.5, "node"] = closest["start_node_name"]
    snapped_points.loc[snapped_points["distance_along_line"]>=0.5, "node"] = closest["end_node_name"]
    snapped_points = snapped_points.reindex(columns=["link", "node", "snap_distance", "distance_along_line", "geometry"])
    snapped_points.index.name = None #'name'
    return snapped_points


def intersect(A, B, B_column):
    """
    Identify geometries that intersect and return statistics on the 
    intersecting values.
    
    The function returns information about the intersection for each geometry 
    in A. Each geometry in B is assigned a value based on a column of data in 
    that GeoDataFrame.  
    
    Parameters
    ----------
    A : geopandas GeoDataFrame
        GeoDataFrame containing Point or Line geometries, generally a GeoDataFrame 
        containing water network junctions, tanks, reservoirs, pipes, pumps, or valves.
    B : geopandas GeoDataFrame
        GeoDataFrame containing Line or Polygon geometries, generally an external dataset
    B_column : str
        Column name in the B GeoDataFrame used to assign a value to each geometry.
    
    Returns
    -------
    pandas DataFrame
        Intersection statistics (index = A.index, columns = stats)
        Columns include:
            - n: number of intersecting geometries
            - sum: sum of the intersecting geometry values
            - min: minimum value of the intersecting geometry
            - max: maximum value of the intersecting geometry
            - average: average value of the intersecting geometry
            - weighted_average: weighted average value of intersecting geometries (only if A contains Lines and B contains Polygons)
            - intersections: list of intersecting geometry indicies
            - values: list of intersecting geometry values
            
    """
    isinstance(A, gpd.GeoDataFrame)
    assert (A['geometry'].geom_type).isin(['Point', 'LineString', 'MultiLineString']).all()
    isinstance(B, gpd.GeoDataFrame)
    assert (B['geometry'].geom_type).isin(['LineString', 'MultiLineString', 'Polygon', 'MultiPolygon']).all()
    isinstance(B_column, str)
    assert B_column in B.columns
    
    intersects = gpd.sjoin(A, B, op='intersects')
    
    n = intersects.groupby('name')[B_column].count()
    val_sum = intersects.groupby('name')[B_column].sum()
    val_min = intersects.groupby('name')[B_column].min()
    val_max = intersects.groupby('name')[B_column].max()
    val_average = intersects.groupby('name')[B_column].mean()
    
    B_indices = intersects.groupby('name')['index_right'].apply(list)
    B_values = intersects.groupby('name')[B_column].apply(list)

    stats = pd.DataFrame(index=A.index, data={'n': n,
                                              'sum': val_sum,
                                              'min': val_min, 
                                              'max': val_max, 
                                              'average': val_average,
                                              'intersections': B_indices,
                                              'values': B_values})
    
    stats['n'] = stats['n'].fillna(0)
    stats.loc[stats['intersections'].isnull(), 'intersections'] = stats.loc[stats['intersections'].isnull(), 'intersections'] .apply(lambda x: [])
    stats.loc[stats['values'].isnull(), 'values'] = stats.loc[stats['values'].isnull(), 'values'] .apply(lambda x: [])
    
    weighted_average = False
    if (A['geometry'].geom_type).isin(['LineString', 'MultiLineString']).all():
        if (B['geometry'].geom_type).isin(['Polygon', 'MultiPolygon']).all():
            weighted_average = True
            
    if weighted_average:
        stats['weighted_average'] = 0
        A_length = A.length
        for i in B.index:
            B_geom = gpd.GeoDataFrame(B.loc[[i],:], crs=None)
            A_subset = A.loc[stats['intersections'].apply(lambda x: i in x),:]
            #print(i, lines_subset)
            clip = gpd.clip(A_subset, B_geom) 
                
            if len(clip.index) > 0:
                val = float(B_geom[B_column])
                
                weighed_val = clip.length/A_length[clip.index]*val
                assert (weighed_val <= val).all()
                stats.loc[clip.index, 'weighted_average'] = stats.loc[clip.index, 'weighted_average'] + weighed_val
                
        stats['weighted_average'] = stats['weighted_average']/stats['n']
    
    return stats


if __name__ == '__main__':
    print('new script')