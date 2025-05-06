"""
The wntr.gis.geospatial module contains functions to snap data and find 
intersects with polygons.
"""

import pandas as pd
import numpy as np
import matplotlib.pylab as plt
from scipy.spatial.distance import cdist
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram

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
    
try:
    import rasterio
    has_rasterio = True
except ModuleNotFoundError:
    rasterio = None
    has_rasterio = False


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
            - node: start or end node of Line in B that is closest to the snapped point (if B contains columns "start_node_name" and "end_node_name")
            - snap_distance: distance between Point A and snapped point
            - line_position: normalized distance of snapped point along Line in B from the start node (0.0) and end node (1.0)
            - geometry: GeoPandas Point object of the snapped point
    """   
    if not has_shapely or not has_geopandas:
        raise ModuleNotFoundError('shapley and geopandas are required')
        
    assert isinstance(A, gpd.GeoDataFrame)
    assert(A['geometry'].geom_type).isin(['Point']).all()
    assert isinstance(B, gpd.GeoDataFrame)
    assert (B['geometry'].geom_type).isin(['Point', 'LineString', 'MultiLineString']).all()
    assert A.crs == B.crs
    
    # Modify B to include "indexB" as a separate column
    B = B.reset_index(names='indexB')
    
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
        
    # Collect only point/link pairs within snap distance radius
    # This is needed because B.sindex.intersection(row) above can return false positives
    closest = closest[closest['snap_distance'] <= tolerance]
    
    # Sort on ascending snap distance, so that closest goes to top
    closest = closest.sort_values(by=["snap_distance", "indexB"]) 
       
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
        if ("start_node_name" in closest.columns) and ("end_node_name" in closest.columns):
            snapped_points.loc[snapped_points["line_position"]<0.5, "node"] = closest["start_node_name"]
            snapped_points.loc[snapped_points["line_position"]>=0.5, "node"] = closest["end_node_name"]
            snapped_points = snapped_points[["link", "node", "snap_distance", "line_position", "geometry"]]
        else:
            snapped_points = snapped_points[["link", "snap_distance", "line_position", "geometry"]]
        snapped_points.index.name = None
        
    return snapped_points

def _background(A, B):
    
    hull_geom = A.union_all().convex_hull
    hull_data = gpd.GeoDataFrame(pd.DataFrame([{'geometry': hull_geom}]), crs=A.crs)
    
    background_geom = hull_data.overlay(B, how='difference').union_all()
   
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
    intersects : DataFrame
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
        
    assert isinstance(A, gpd.GeoDataFrame)
    assert (A['geometry'].geom_type).isin(['Point', 'LineString', 
                                           'MultiLineString', 'Polygon', 
                                           'MultiPolygon']).all()
    assert isinstance(B, gpd.GeoDataFrame)
    assert (B['geometry'].geom_type).isin(['Point', 'LineString', 
                                           'MultiLineString', 'Polygon', 
                                           'MultiPolygon']).all()
    if isinstance(B_value, str):
        assert B_value in B.columns
    assert isinstance(include_background, bool)
    assert isinstance(background_value, (int, float))
    assert A.crs == B.crs, "A and B must have the same crs."
    
    if include_background:
        background = _background(A, B)
        if B_value is not None:
            background[B_value] = background_value
        B = pd.concat([B, background])
    
    B_original_index_name = B.index.name
    B.index.name = None

    intersects = gpd.sjoin(A, B, predicate='intersects')
    intersects.index.name = '_tmp_index_name' # set a temp index name for grouping
    
    # Sort values by index and intersecting object
    intersects['sort_order'] = 1 # make sure 'BACKGROUND' is listed first
    intersects.loc[intersects['index_right'] == 'BACKGROUND', 'sort_order'] = 0
    intersects.sort_values(['_tmp_index_name', 'sort_order', 'index_right'], inplace=True)
    
    n = intersects.groupby('_tmp_index_name')['geometry'].count()
    B_indices = intersects.groupby('_tmp_index_name')['index_right'].apply(list)
    stats = pd.DataFrame(index=A.index.copy(), data={'intersections': B_indices,
                                              'n': n,})
    stats['n'] = stats['n'].fillna(0)
    stats['n'] = stats['n'].apply(int)
    stats.loc[stats['intersections'].isnull(), 'intersections'] = stats.loc[stats['intersections'].isnull(), 'intersections'] .apply(lambda x: [])
    
    if B_value is not None:
        stats['values'] = intersects.groupby('_tmp_index_name')[B_value].apply(list)
        stats['sum'] = intersects.groupby('_tmp_index_name')[B_value].sum()
        stats['min'] = intersects.groupby('_tmp_index_name')[B_value].min()
        stats['max'] = intersects.groupby('_tmp_index_name')[B_value].max()
        stats['mean'] = intersects.groupby('_tmp_index_name')[B_value].mean()
        
        stats = stats.reindex(['intersections', 'values', 'n', 'sum', 'min', 'max', 'mean'], axis=1)
        stats.loc[stats['values'].isnull(), 'values'] = stats.loc[stats['values'].isnull(), 'values'] .apply(lambda x: [])
        
    weighted_mean = False
    if (A['geometry'].geom_type).isin(['LineString', 'MultiLineString']).all():
        if (B['geometry'].geom_type).isin(['Polygon', 'MultiPolygon']).all():
            weighted_mean = True
            
    if weighted_mean and B_value is not None:
        stats['weighted_mean'] = 0.0
        A_length = A.length
        covered_length = pd.Series(0.0, index = A.index)
        
        for i in B.index:
            B_geom = gpd.GeoDataFrame(B.loc[[i],:], crs=B.crs)
            val = float(B_geom.iloc[0][B_value])
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
    
    # Restore B's index
    B.index.name = B_original_index_name
    
    return stats


def sample_raster(A, filepath, bands=1):
    """Sample a raster (e.g., GeoTIFF file) using Points in GeoDataFrame A. 
    
    This function can take either a filepath to a raster or a virtual raster 
    (VRT), which combines multiple raster tiles into a single object. The 
    function opens the raster(s) and samples it at the coordinates of the point 
    geometries in A. This function assigns nan to values that match the 
    raster's `nodata` attribute. These sampled values are returned as a Series 
    which has an index matching A.

    Parameters
    ----------
    A : GeoDataFrame
        GeoDataFrame containing Point geometries
    filepath : str
        Path to raster or alternatively a virtual raster (VRT)
    bands : int or list[int] (optional, default = 1)
        Index or indices of the bands to sample (using 1-based indexing)

    Returns
    -------
    Series
        Pandas Series containing the sampled values for each geometry in gdf
    """
    # further functionality could include other geometries (Line, Polygon),
    # and use of multiprocessing to speed up querying.
    if not has_rasterio:
        raise ModuleNotFoundError('rasterio is required')
    
    assert (A['geometry'].geom_type == "Point").all()
    assert isinstance(filepath, str)
    assert isinstance(bands, (int, list))
    
    with rasterio.open(filepath) as raster:
        xys = zip(A.geometry.x, A.geometry.y)
        
        values = np.array(
            tuple(raster.sample(xys, bands)), dtype=float # force to float to allow for conversion of nodata to nan
        ).squeeze()
        
    values[values == raster.nodata] = np.nan
    values = pd.Series(values, index=A.index)
    
    return values


def connect_lines(lines, threshold, plot=False):
    """
    Connect lines by identifying start and end nodes that are within a 
    threshold distance

    Parameters
    ----------
    lines : gpd.GeoDataFrame
        GeoDataFrame with LineString geometry
    tolerance : float
        Maximum distance between line endpoints, used to define connecting 
        Point geometry
    plot : bool
        Boolean indicating if a plot is created for the dendogram, and original and connected lines
        
    Returns
    -------
    Tuple[line GeoDataFrame, node GeoDataFrame]
        * line GeoDataFrame contains LineString geometry, start_node_name, and 
          end_node_name, along with original columns in lines
        * node GeoDataFrame contains connecting Point geometry and node names
    """
    if not has_shapely or not has_geopandas:
        raise ModuleNotFoundError('shapley and geopandas are required')
    
    original_lines = lines
    lines = lines.copy()

    # Create start and end node name and Point geometry for each line
    nodes = []
    geometry = []
    lines['start_node_name'] = None #create new columns
    lines['end_node_name'] = None
    j = 0
    for i, line in lines.iterrows(): # loop through every line
        try:
            geom = line.geometry.geoms[0]
        except:
            geom = line.geometry
        
        geometry.append(Point([geom.coords[0][0], geom.coords[0][1]])) 
        nodes.append({'Line': i, 'Node': j}) #node list holds the line ID
        #unique number for each start node and end node for each line 
        lines.loc[i,'start_node_name'] = j
        j = j+1
            
        geometry.append(Point([geom.coords[-1][0], geom.coords[-1][1]]))
        nodes.append({'Line': i, 'Node': j})
        lines.loc[i,'end_node_name'] = j
        j = j+1
            
    nodes = gpd.GeoDataFrame(nodes, geometry=geometry)
    nodes.set_crs(lines.crs, inplace=True)
    
    # Create a distance matrix
    points = nodes['geometry']
    coords = points.apply(lambda geom: (geom.x, geom.y)).tolist()
    condensed = pdist(coords)
    D = squareform(condensed)
    D = pd.DataFrame(D, index=nodes.index, columns=nodes.index)
    
    # Several options exist for linkage and fcluster below 
    # currently using ward/euclidean/distance
    
    # Compute a linkage model
    Z = linkage(condensed, method='ward', metric='euclidean', optimal_ordering=True)
    
    # Form clusters
    #clusters = fcluster(Z, threshold, criterion='inconsistent', depth=2)
    clusters = fcluster(Z, threshold, criterion='distance')
    #clusters = fcluster(Z, threshold, criterion='monocrit')
    #clusters = fcluster(Z, threshold, criterion='maxclust')
    #clusters = fcluster(Z, threshold, criterion='maxclust_monocrit')
    clusters = pd.Series(clusters, index=nodes.index)
    nodes['supernode'] = clusters.copy()
    
    # Update lines GeoDataFrame with start and end supernode names
    map_node_to_supernode = nodes['supernode']
    lines['start_node_name'] = map_node_to_supernode[lines['start_node_name']].values
    lines['end_node_name'] = map_node_to_supernode[lines['end_node_name']].values
    
    # Remove lines with the same start and end node name
    lines = lines.loc[~(lines['start_node_name'] == lines['end_node_name']),:]
    
    # Create a nodes GeoDataFrame with centroid of each supernode
    supernode_name = []
    supernode_geom = []
    for name, group in nodes.groupby('supernode'):
        supernode_name.append(name)
        supernode_geom.append(group.dissolve().centroid[0])
    nodes = gpd.GeoDataFrame({'Node': supernode_name}, geometry=supernode_geom)
    nodes.set_index('Node', inplace=True)
    nodes.index.name = None
    nodes.crs = lines.crs
    
    # Convert names to string
    nodes.index = nodes.index.astype(str)
    lines['start_node_name'] = lines['start_node_name'].astype(str)
    lines['end_node_name'] = lines['end_node_name'].astype(str)
    
    # Add start and end node Points to LineStrings
    start_coords = nodes.loc[lines['start_node_name']]
    end_coords = nodes.loc[lines['end_node_name']]
    for i, (line_name, row) in enumerate(lines.iterrows()):
        line = row['geometry']
        l_coords = list(line.coords)
        start_point = nodes.loc[row['start_node_name'], 'geometry']
        end_point = nodes.loc[row['end_node_name'], 'geometry']
        if start_point.coords[0] != l_coords[0]:
            l_coords.insert(0, start_point.coords[0])
        if end_point.coords[0] != l_coords[-1]:
            l_coords.append(end_point.coords[0])
        lines.loc[line_name, 'geometry'] = LineString(l_coords)
    
    if plot:
  
        plt.figure(figsize=(10, 5))
        dendro = dendrogram(Z)

        #unique_clusters = np.unique(clusters)
        #colors = plt.cm.get_cmap('tab10', len(unique_clusters))  # Use a colormap with enough colors
        #color_dict = {cluster: colors(i) for i, cluster in enumerate(unique_clusters)}
        #dendro = dendrogram(Z, color_threshold=threshold, link_color_func=lambda k: color_dict[k])

        plt.title('Hierarchical Cluster Dendrogram')
        plt.xlabel('Data Point Indexes')
        plt.ylabel('Distance')
        
        plt.figure()
        ax = plt.gca()
        ax = original_lines.plot(ax=ax, color='r', label='Disconnected lines')
        ax = lines.plot(ax=ax, color='k', linewidth=6, alpha=0.35, label='Connected lines')
        ax = nodes.plot(ax=ax, color='k', label='Connected nodes')
        ax.legend()
        bounds = ax.axis('equal')
        plt.tight_layout()
        plt.axis('off')
    
    return lines, nodes
