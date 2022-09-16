"""
The wntr.gis.geospatial module contains functions to snap data and find 
intersects with polygons.
"""

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


def snap(A, B, tolerance):  
    """
    Snap Points in A to Points or Lines in B

    For each Point geometry in A, the function returns snapped Point geometry 
    and associated element in B. Note the CRS of A must equal the CRS of B.
    
    Parameters
    ----------
    A : geopandas GeoDataFrame
        GeoDataFrame containing Point geometries.
    B : geopandas GeoDataFrame
        GeoDataFrame containing Point, LineString, or MultiLineString geometries.
    tolerance : float
        Maximum allowable distance (in the coordinate reference system units) 
        between Points in A and Points or Lines in B.  
    
    Returns
    -------
    GeoPandas GeoDataFrame
        Snapped points (index = A.index, columns = defined below)
        
        If B contains Points, columns include:
            - node: closest Point in B to Point in A
            - snap_distance: distance between Point in A and snapped point
            - geometry: GeoPandas Point object of the snapped point
        
        If B contains Lines or MultiLineString, columns include:
            - link: closest Line in B to Point in A
            - node: start or end node of Line in B that is closest to the snapped point
            - snap_distance: distance between Point A and snapped point
            - line_position: normalized distance of snapped point along Line in B from the start node (0.0) and end node (1.0)
            - geometry: GeoPandas Point object of the snapped point
    """   
    if not has_shapely or not has_geopandas:
        raise ModuleNotFoundError('shapley and geopandas are required')
        
    isinstance(A, gpd.GeoDataFrame)
    assert(A['geometry'].geom_type).isin(['Point']).all()
    isinstance(B, gpd.GeoDataFrame)
    assert (B['geometry'].geom_type).isin(['Point', 'LineString', 'MultiLineString']).all()
    assert A.crs == B.crs
    
    # Modify B to include "indexB" as a separate column
    B = B.reset_index()
    B.rename(columns={'index':'indexB'}, inplace=True)
    
    # Define the coordinate reference system, based on B
    crs = B.crs
    
    # Determine which Bs are closest to each A
    bbox = A.bounds + [-tolerance, -tolerance, tolerance, tolerance]       
    hits = bbox.apply(lambda row: list(B.loc[list(B.sindex.intersection(row))]['indexB']), axis=1)        
    closest = pd.DataFrame({
        # index of points table
        "point": np.repeat(hits.index, hits.apply(len)),
        # name of link
        "indexB": np.concatenate(hits.values)
        })
    
    # Merge the closest dataframe with the lines dataframe on the line names
    closest = pd.merge(closest, B, on="indexB")

    # Join back to the original points to get their geometry
    # rename the point geometry as "points"
    closest = closest.join(A.geometry.rename("points"), on="point")
    
    # Convert back to a GeoDataFrame, so we can do spatial ops
    closest = gpd.GeoDataFrame(closest, geometry="geometry", crs=crs)  
    
    # Calculate distance between the point and nearby links
    closest["snap_distance"] = closest.geometry.distance(gpd.GeoSeries(closest.points, crs=crs))
    
    # Sort on ascending snap distance, so that closest goes to top
    closest = closest.sort_values(by=["snap_distance"]) 
       
    # group by the index of the points and take the first, which is the closest line
    closest = closest.groupby("point").first()      
    
    # construct a GeoDataFrame of the closest elements of B
    closest = gpd.GeoDataFrame(closest, geometry="geometry", crs=crs)
    
    # Reset B index
    B.set_index('indexB', inplace=True)
    B.index.name = None
    
    # snap to points
    if B['geometry'].geom_type.isin(['Point']).all():
        snapped_points = closest.rename(columns={"indexB":"node"})
        snapped_points = snapped_points[["node", "snap_distance", "geometry"]]
        snapped_points.index.name = None      
        
    # snap to lines
    if B['geometry'].geom_type.isin(['LineString', 'MultiLineString']).all():
        closest = closest.rename(columns={"indexB":"link"})        
        # position of nearest point from start of the line
        pos = closest.geometry.project(gpd.GeoSeries(closest.points))        
        # get new point location geometry
        snapped_points = closest.geometry.interpolate(pos)
        snapped_points = gpd.GeoDataFrame(data=closest ,geometry=snapped_points, crs=crs)
        # determine whether the snapped point is closer to the start or end node
        snapped_points["line_position"] = closest.geometry.project(snapped_points, normalized=True)
        snapped_points.loc[snapped_points["line_position"]<0.5, "node"] = closest["start_node_name"]
        snapped_points.loc[snapped_points["line_position"]>=0.5, "node"] = closest["end_node_name"]
        snapped_points = snapped_points[["link", "node", "snap_distance", "line_position", "geometry"]]
        snapped_points.index.name = None
        
    return snapped_points

def _backgound(A, B):
    
    hull_geom = A.unary_union.convex_hull
    hull_data = gpd.GeoDataFrame(pd.DataFrame([{'geometry': hull_geom}]), crs=A.crs)
    
    background_geom = hull_data.overlay(B, how='difference').unary_union
   
    background = gpd.GeoDataFrame(pd.DataFrame([{'geometry': background_geom}]), crs=A.crs)
    background.index = ['BACKGROUND']
    
    return background


def intersect(A, B, B_value=None, include_background=False, background_value=0):
    """
    Intersect Points, Lines or Polygons in A with Points, Lines, or Polygons in B.
    Return statistics on the intersection.
    
    The function returns information about the intersection for each geometry 
    in A. Each geometry in B is assigned a value based on a column of data in 
    that GeoDataFrame.  Note the CRS of A must equal the CRS of B.
    
    Parameters
    ----------
    A : geopandas GeoDataFrame
        GeoDataFrame containing Point, LineString, or Polygon geometries
    B : geopandas GeoDataFrame
        GeoDataFrame containing  Point, LineString, or Polygon geometries
    B_value : str or None (optional)
        Column name in B used to assign a value to each geometry.
        Default is None.
    include_background : bool (optional) 
         Include background, defined as space covered by A that is not covered by B 
         (overlay difference between A and B). The background geometry is added
         to B and is given the name 'BACKGROUND'. Default is False.
    background_value : int or float (optional)
        The value given to background space. This value is used in the intersection 
        statistics if a B_value column name is provided. Default is 0.
        
    Returns
    -------
    pandas DataFrame
        Intersection statistics (index = A.index, columns = defined below)
        Columns include:
            - n: number of intersecting B geometries
            - intersections: list of intersecting B indices
            
        If B_value is given:
            - values: list of intersecting B values
            - sum: sum of the intersecting B values
            - min: minimum of the intersecting B values
            - max: maximum of the intersecting B values
            - mean: mean of the intersecting B values
            
        If A contains Lines and B contains Polygons:
            - weighted_mean: weighted mean of intersecting B values

    """
    if not has_shapely or not has_geopandas:
        raise ModuleNotFoundError('shapley and geopandas are required')
        
    isinstance(A, gpd.GeoDataFrame)
    assert (A['geometry'].geom_type).isin(['Point', 'LineString', 
                                           'MultiLineString', 'Polygon', 
                                           'MultiPolygon']).all()
    isinstance(B, gpd.GeoDataFrame)
    assert (B['geometry'].geom_type).isin(['Point', 'LineString', 
                                           'MultiLineString', 'Polygon', 
                                           'MultiPolygon']).all()
    if isinstance(B_value, str):
        assert B_value in B.columns
    isinstance(include_background, bool)
    isinstance(background_value, (int, float))
    assert A.crs == B.crs
    
    if include_background:
        background = _backgound(A, B)
        if B_value is not None:
            background[B_value] = background_value
        B = B.append(background)
        
    intersects = gpd.sjoin(A, B, predicate='intersects')
    intersects.index.name = 'name'
    
    n = intersects.groupby('name')['geometry'].count()
    B_indices = intersects.groupby('name')['index_right'].apply(list)
    stats = pd.DataFrame(index=A.index, data={'intersections': B_indices,
                                              'n': n,})
    stats['n'] = stats['n'].fillna(0)
    stats['n'] = stats['n'].apply(int)
    stats.loc[stats['intersections'].isnull(), 'intersections'] = stats.loc[stats['intersections'].isnull(), 'intersections'] .apply(lambda x: [])
    
    if B_value is not None:
        stats['values'] = intersects.groupby('name')[B_value].apply(list)
        stats['sum'] = intersects.groupby('name')[B_value].sum()
        stats['min'] = intersects.groupby('name')[B_value].min()
        stats['max'] = intersects.groupby('name')[B_value].max()
        stats['mean'] = intersects.groupby('name')[B_value].mean()
        
        stats = stats.reindex(['intersections', 'values', 'n', 'sum', 'min', 'max', 'mean'], axis=1)
        stats.loc[stats['values'].isnull(), 'values'] = stats.loc[stats['values'].isnull(), 'values'] .apply(lambda x: [])
        
    weighted_mean = False
    if (A['geometry'].geom_type).isin(['LineString', 'MultiLineString']).all():
        if (B['geometry'].geom_type).isin(['Polygon', 'MultiPolygon']).all():
            weighted_mean = True
            
    if weighted_mean and B_value is not None:
        stats['weighted_mean'] = 0
        A_length = A.length
        covered_length = pd.Series(0, index = A.index)
        
        for i in B.index:
            B_geom = gpd.GeoDataFrame(B.loc[[i],:], crs=B.crs)
            val = float(B_geom[B_value])
            A_subset = A.loc[stats['intersections'].apply(lambda x: i in x),:]
            #print(i, lines_subset)
            A_clip = gpd.clip(A_subset, B_geom) 
            A_clip_length = A_clip.length
            A_clip_index = A_clip.index
            
            if A_clip_length.shape[0] > 0:
                fraction_length = A_clip_length/A_length[A_clip_index]
                covered_length[A_clip_index] = covered_length[A_clip_index] + fraction_length
                weighed_val = fraction_length*val
                stats.loc[A_clip_index, 'weighted_mean'] = stats.loc[A_clip_index, 'weighted_mean'] + weighed_val
        
        # Normalize weighted mean by covered length (can be over 1 if polygons overlap)
        # Can be less than 1 if there are gaps (when background is not used)
        stats['weighted_mean'] = stats['weighted_mean']/covered_length
        
        # Covered_length is NaN if length A is 0, set weighted mean to mean
        stats.loc[covered_length.isna(), 'weighted_mean'] = stats.loc[covered_length.isna(), 'mean']
        
        # No intersection, set weighted mean to NaN
        stats.loc[stats['n']==0, 'weighted_mean'] = np.NaN
        
    stats.index.name = None
    
    return stats
