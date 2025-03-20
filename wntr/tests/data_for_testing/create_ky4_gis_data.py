"""
The GIS data file created using this script is stored in examples/data and 
used in model_development.ipynb
 
"""
from os.path import join
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx

import wntr

ex_datadir = join("..", "..", "..", "examples", "networks")

# Creates the disconnected pipe data used in the demo
np.random.seed(456)

inp_file = join(ex_datadir, "ky4.inp")
wn = wntr.network.WaterNetworkModel(inp_file)
wn_gis = wn.to_gis(crs = "EPSG:3547") # ft
original_pipes = wn_gis.pipes

distance_threshold = 100 # same units as crs (ft)

# Create imperfect pipe data
disconnected_pipes = original_pipes.copy()
for i, line in disconnected_pipes.iterrows():
    angle = np.random.uniform(-5,5,1)[0]
    geom = gpd.GeoSeries(line['geometry'])
    length = geom.length[0]
    if length < 1000:
        geom = geom.rotate(angle)
    if length > 25:
        val = np.random.uniform(0,25,1)[0]
        factor = 1-(val/length)
        geom = geom.scale(factor, factor)
    disconnected_pipes.loc[i,'geometry'] = geom[0]

original_pipes = wn_gis.pipes
disconnected_pipes = disconnected_pipes

pipes, junctions = wntr.gis.connect_lines(disconnected_pipes, 
                                          distance_threshold, plot=True)

gis_data = wntr.gis.WaterNetworkGIS({"junctions": junctions,
                                     "pipes": pipes})
wn = wntr.network.from_gis(gis_data)
G = wn.to_graph()
uG = G.to_undirected()
print(nx.number_connected_components(uG))
largest_cc = max(nx.connected_components(uG), key=len)
cc = pd.Series(None, index=wn.node_name_list)
for cluster, nodes in enumerate(sorted(nx.connected_components(uG), key=len, reverse=True)):
    cc.loc[list(nodes)] = cluster
        
ax = wntr.graphics.plot_network(wn, cc)
ax = disconnected_pipes.plot(ax=ax, color='r', label='Disconnected lines')

assert nx.is_connected(uG)
assert nx.number_connected_components(uG) == 1

disconnected_pipes.rename(columns={'check_valve':'cv'}, inplace=True)
disconnected_pipes.to_file('ky4_disconnected_pipes.geojson', driver="GeoJSON") 