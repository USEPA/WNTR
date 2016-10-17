import wntr

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Access node and link panels
print results.node
print results.link

# Access the pressure and demand at node '123' at 1 hour
print results.node.loc[['pressure', 'demand'], 3600, '123']

# Access the pressure for all nodes and times
print results.node.loc['pressure', :, :]

# Plot time-series
pressure_at_node123 = results.node.loc['pressure', :, '123']
pressure_at_node123.plot()

# Plot attribute on the network
pressure_at_1hr = results.node.loc['pressure', 3600, :]
flowrate_at_1hr = results.link.loc['flowrate', 3600, :]
wntr.network.draw_graph(wn, node_attribute=pressure_at_1hr, 
                        link_attribute=flowrate_at_1hr)

# Store results to an excel file
results.node.to_excel('node_results.xls')
results.link.to_excel('link_results.xls')
