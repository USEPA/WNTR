import geopandas as gpd
import matplotlib.pylab as plt
import wntr

plt.close('all')

crs = "EPSG:3089" # ft

hidden=True
distance_threshold = 100.0

### Create a model from geospatial data ###

if hidden:
    # TODO, hide in the notebook or check in the geojson files
    wn0 = wntr.network.WaterNetworkModel("networks/ky4.inp")
    wn0.options.time.duration = 24*3600
    sim = wntr.sim.EpanetSimulator(wn0)
    results0 = sim.run_sim()
    pressure0 = results0.node['pressure'].loc[24*3600, :]
    wntr.graphics.plot_network(wn0, node_attribute=pressure0, 
                               node_size=30, title='Pressure')
    wntr.network.io.write_geojson(wn0, 'data/ky4', crs=crs)
    
    # junctions should have base demand (see PR)
    aed0 = wntr.metrics.average_expected_demand(wn0)
    print(aed0)
    for name, control in wn0.controls():
        print(name, control)
    for name, pattern in wn0.patterns():
        print(name, pattern.multipliers)

 
# Option 1, direct from GeoJSON files
geojson_files = {'junctions': 'data/ky4_junctions.geojson', 
                 'tanks': 'data/ky4_tanks.geojson',
                 'reservoirs': 'data/ky4_reservoirs.geojson',
                 'pipes': 'data/ky4_pipes.geojson',
                 'pumps': 'data/ky4_pumps.geojson'}
wn = wntr.network.read_geojson(geojson_files)

# Option 2, from GeoDataFrames
junctions = gpd.read_file("data/ky4_junctions.geojson", crs=crs)
tanks = gpd.read_file("data/ky4_tanks.geojson", crs=crs)
reservoirs = gpd.read_file("data/ky4_reservoirs.geojson", crs=crs)
pipes = gpd.read_file("data/ky4_pipes.geojson", crs=crs)
pumps = gpd.read_file("data/ky4_pumps.geojson", crs=crs)

junctions.set_index('name', inplace=True)
tanks.set_index('name', inplace=True)
reservoirs.set_index('name', inplace=True)
pipes.set_index('name', inplace=True)
pumps.set_index('name', inplace=True)

gis_data = wntr.gis.WaterNetworkGIS({'junctions': junctions,
                                     'tanks': tanks,
                                     'reservoirs': reservoirs,
                                     'pipes': pipes, 
                                     'pumps': pumps})
wn = wntr.network.from_gis(gis_data)

# Add initial status
pump = wn.get_link('~@Pump-1')
pump.initial_status = 'Closed'

# Add controls
if hidden:
    inpfile_units = wn.options.hydraulic.inpfile_units
    flow_units = wntr.epanet.util.FlowUnits[inpfile_units]
    line =  'LINK ~@Pump-1 OPEN IF NODE T-3 BELOW  90.75'
    control = wntr.epanet.io._read_control_line(line, wn, flow_units, 'Pump1_open')
    print(control)
    line =  'LINK ~@Pump-1 CLOSED IF NODE T-3 ABOVE  105.75'
    control = wntr.epanet.io._read_control_line(line, wn, flow_units, 'Pump1_open')
    print(control)

line =  'LINK ~@Pump-1 OPEN IF NODE T-3 BELOW  27.6606'
wn.add_control('Pump1_open', line)
line =  'LINK ~@Pump-1 CLOSED IF NODE T-3 ABOVE  32.2326'
wn.add_control('Pump1_closed', line)

# Add patterns
multipliers = [0.33, 0.25, 0.209, 0.209, 0.259, 0.36, 
              0.529, 0.91, 1.2, 1.299, 1.34, 1.34,
              1.32, 1.269, 1.25, 1.25, 1.279, 1.37,
              1.519, 1.7, 1.75, 1.669, 0.899, 0.479]
default_pattern_name = wn.options.hydraulic.pattern
wn.add_pattern(default_pattern_name, multipliers)

aed = wntr.metrics.average_expected_demand(wn)
print(aed)

# Run simulation, plot_results
# TODO, this shoudl be 24, but the simulation doesn't run to completion, due to demands?
wn.options.time.duration = 0 #24*3600
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()
pressure = results.node['pressure'].loc[0, :]
wntr.graphics.plot_network(wn, node_attribute=pressure, 
                           node_size=30, title='Pressure')



### Create a model from imperfect geospatial data ###

# Load pipe data 
# Missing junctions (no start and end node names or locations)
# Pipe endpoints are not aligned
if hidden:
    diconnected_pipes = gpd.read_file("data/ky4_pipes_broken.geojson")
    #pipes.set_index('index', inplace=True)
    #del pipes['start_node']
    #del pipes['end_node_n']
    pipesA, junctionsA = wntr.gis.geospatial.reconnect_network(diconnected_pipes, distance_threshold)
    
    fig, ax = plt.subplots()
    diconnected_pipes.plot(color='b', linewidth=4, ax=ax)
    pipesA.plot(color='r', linewidth=2, ax=ax)
    junctionsA.plot(color='k', ax=ax)

# TODO, recreate this file using complete column names and no start or end node names
# TODO rename the file 'ky4_diconnected_pipes.geojson'
# TODO rename 'index' to 'name'
# TODO same crs as above
diconnected_pipes = gpd.read_file("data/ky4_pipes_broken.geojson", crs=crs)
if hidden:
    diconnected_pipes.set_index('index', inplace=True)
    del diconnected_pipes['start_node']
    del diconnected_pipes['end_node_n']
pipes, junctions = wntr.gis.geospatial.connect_lines(diconnected_pipes, distance_threshold)

fig, ax = plt.subplots()
diconnected_pipes.plot(color='b', linewidth=4, ax=ax)
pipes.plot(color='r', linewidth=2, ax=ax)
junctions.plot(color='k', ax=ax)

# The following lines should not be needed, see PR
junctions['node_type'] = 'Junction'
pipes['link_type'] = 'Pipe'

# Assign elevation to junctions - using raster
# TODO
junctions['elevation'] = 100

# Load reservoir - complete dataset, location and head
reservoirs = gpd.read_file("data/ky4_reservoirs.geojson", crs=crs)
reservoirs.set_index('name', inplace=True)
# TODO snap reservoirs to nearest junction
#snap_reservoirs = wntr.gis.snap(reservoirs, junctions, distance_threshold)

# Load tank data - complete dataset, location, min/max level, diameter
tanks = gpd.read_file("data/ky4_tanks.geojson", crs=crs)
tanks.set_index('name', inplace=True)
# TODO snap tanks to nearest junction

# Load pump data - location, settings, start, end node)
pumps = gpd.read_file("data/ky4_pumps.geojson", crs=crs)
pumps.set_index('name', inplace=True)
# TODO snap end points to nearest junction, add pump and close bipass?



# build the wn_gis object
# TODO, add back in tanks, reservoirs, and pumps
gis_data = wntr.gis.WaterNetworkGIS({'junctions': junctions,
                                     #'tanks': tanks,
                                     #'reservoirs': reservoirs,
                                     'pipes': pipes, 
                                     #'pumps': pumps
                                     })
wn = wntr.network.from_gis(gis_data) # TODO this won't work until PR 452 is merged

# Add controls, initial status, and pattern (same code as above)

# Add demands, estimated from building size
buildings = gpd.read_file("data/ky4_buildings.geojson", crs=crs)
buildings['area'] = buildings.area
buildings['base_demand'] = buildings['area']/0.00001

buildings.geometry = buildings.geometry.centroid
snap_buildings = wntr.gis.snap(buildings, junctions, distance_threshold)
buildings['junction'] = snap_buildings['node']

category = None
pattern_name = '1'
for i, row in buildings.iterrows():
    junction_name = buildings.loc[i, 'junction']
    if junction_name is None:
        continue
    base_demand = buildings.loc[i, 'base_demand']
    junction = wn.get_node(junction_name)
    junction.demand_timeseries_list.append((base_demand, pattern_name, category))

# Run simulation, plot_results
wn.options.time.duration = 24*3600
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()
pressure = results.node['pressure'].loc[24*3600, :]
wntr.graphics.plot_network(wn, node_attribute=pressure, 
                           node_size=30, title='Pressure')




