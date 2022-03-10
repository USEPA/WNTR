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


def snap_points_to_points(points1, points2):
    pass

def snap_points_to_lines(points, lines):
    pass


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