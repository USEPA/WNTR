"""
The GIS data created using this file is stored in examples/data. The data has 
no CRS, the units are based on Net1. However, when the geojson files are read 
back into a geopandas DataFrame, the CRS is assumed to be epsg:4326
https://epsg.io/4326, World Geodetic System in degrees.
Because this is a geographic CRS, geometry.length prints a warning that it is
likely incorrect.  
"""
import numpy as np
import pandas as pd
import matplotlib.pylab as plt
from scipy.spatial import Voronoi
import geopandas as gpd
import shapely
import shapely.geometry
import shapely.ops

import wntr

plt.close('all')
np.random.seed(321)

wn = wntr.network.WaterNetworkModel('../../../examples/networks/Net1.inp')

# Create a convex hull to clip data
coords = wn.query_node_attribute('coordinates')
coord_vals = pd.DataFrame.from_records(coords.values, columns=['x', 'y'])
hull_geom = shapely.geometry.MultiPoint(coords.values).convex_hull
hull_geom = hull_geom.buffer(10)
hull_data = gpd.GeoDataFrame(pd.DataFrame([{'geometry': hull_geom}]), crs=None)

### Generate polygons - demographic data
points = np.random.random((9, 2))*100
corners = np.array([[0,0],[0,100],[100,100],[100,0]])
points = np.append(points, corners, axis=0)
vor = Voronoi(points)

line_data = []
for line in vor.ridge_vertices:
    if -1 not in line:
        line_data.append(shapely.geometry.LineString(vor.vertices[line]))
poly_data = []
for poly in shapely.ops.polygonize(line_data):
    poly_data.append({'mean_income': np.round(np.random.normal(67000,30000),0),
                      'mean_age': np.round(np.random.normal(40,10), 0),
                      'population': np.round(np.random.normal(5000,1500), 0),
                      'geometry': poly})   
    
demographic_data = gpd.GeoDataFrame(pd.DataFrame(poly_data), crs=None)
demographic_data = gpd.clip(demographic_data, hull_geom) 
demographic_data.reset_index(drop=True, inplace=True)

ax = demographic_data.plot(column='mean_income', alpha=0.5, cmap='bone', vmin=0, vmax=100000)
wntr.graphics.plot_network(wn, ax=ax)

print(demographic_data.crs)
demographic_data.length

demographic_data.to_file('Net1_demographic_data.geojson', driver='GeoJSON')
demographic_data2 = gpd.read_file('Net1_demographic_data.geojson')

print(demographic_data2.crs)
demographic_data2.length

### Generate polygons - landslide hazard zones with probability of failure
poly_data = []
poly_data.append({'Pr': 0.5,  'geometry': shapely.geometry.Polygon([[27,23],[28,45],[25,65],[31,56],[32,35]]).buffer(2)})
poly_data.append({'Pr': 0.75, 'geometry': shapely.geometry.Polygon([[42,2],[45,27],[35,85]]).buffer(2)})
poly_data.append({'Pr': 0.9, 'geometry': shapely.geometry.Polygon([[60,44],[61,34],[58,36]]).buffer(2)})

landslide_data = gpd.GeoDataFrame(pd.DataFrame(poly_data), crs=None)

ax = landslide_data.plot(column='Pr', cmap='bone', vmin=0, vmax=1)
wntr.graphics.plot_network(wn, ax=ax)

landslide_data.crs = None
landslide_data.to_file('Net1_landslide_data.geojson', driver='GeoJSON')


### Generate lines - earthquake fault lines with probability of a mag 7 earthquake
line_data = []
line_data.append({'Pr': 0.5,  'geometry': shapely.geometry.LineString([[36,2],[44,44],[85,85]])})
line_data.append({'Pr': 0.75, 'geometry': shapely.geometry.LineString([[42,2],[45,27],[38,56],[30,85]])})
line_data.append({'Pr': 0.9,  'geometry': shapely.geometry.LineString([[40,2],[50,50],[60,85]])})
line_data.append({'Pr': 0.25, 'geometry': shapely.geometry.LineString([[30,2],[35,30],[40,50],[60,80]])})

earthquake_data = gpd.GeoDataFrame(pd.DataFrame(line_data), crs=None)

ax = earthquake_data.plot(column='Pr', cmap='bone', vmin=0, vmax=1)
wntr.graphics.plot_network(wn, ax=ax)

earthquake_data.crs = None
earthquake_data.to_file('Net1_earthquake_data.geojson', driver='GeoJSON')

### Generate points - hydrant locations with fire flow requirements in GPM
point_data = []
point_data.append({'demand': 5000, 'geometry': shapely.geometry.Point([48.2,37.2])})        
point_data.append({'demand': 1500, 'geometry': shapely.geometry.Point([71.8,68.3])})
point_data.append({'demand': 8000, 'geometry': shapely.geometry.Point([51.2,71.1])})  

hydrant_locations = gpd.GeoDataFrame(pd.DataFrame(point_data), crs=None)

ax = hydrant_locations.plot(column='demand', cmap='bone', vmin=0, vmax=10000)
wntr.graphics.plot_network(wn, ax=ax)

hydrant_locations.crs = None
hydrant_locations.to_file('Net1_hydrant_data.geojson', driver='GeoJSON')

### Generate points - valve locations
point_data = []
point_data.append({'geometry': shapely.geometry.Point([56.5, 41.5])})        
point_data.append({'geometry': shapely.geometry.Point([32.1, 67.6])})
point_data.append({'geometry': shapely.geometry.Point([52.7, 86.3])})  

valve_locations = gpd.GeoDataFrame(pd.DataFrame(point_data), crs=None)

ax = valve_locations.plot()
wntr.graphics.plot_network(wn, ax=ax)

valve_locations.crs = None
valve_locations.to_file('Net1_valve_data.geojson', driver='GeoJSON')
