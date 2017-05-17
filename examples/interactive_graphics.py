import wntr
import plotly
import matplotlib.pylab as plt

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Extract simulation results to plot
pressure_at_5hr = results.node.loc['pressure', 5*3600, :]

# Create static network graphics
wntr.graphics.plot_network(wn, node_attribute='elevation', title='Elevation')
wntr.graphics.plot_network(wn, node_attribute=['123', '199'], title='Node 123 and 199')
wntr.graphics.plot_network(wn, node_attribute=pressure_at_5hr, title='Pressure at 5 hours')
    
## Create interactive scalable network graphics
wntr.graphics.plot_interactive_network(wn, node_attribute='elevation', 
    title='Elevation', filename='elevation.html')
wntr.graphics.plot_interactive_network(wn, node_attribute=['123', '199'], 
    title='Node 123 and 199', filename='nodes.html')
wntr.graphics.plot_interactive_network(wn, node_attribute=pressure_at_5hr, 
    title='Pressure at 5 hours', filename='pressure5hr.html')

# Create interactive scalable time series graphics
fig = plt.figure()
ax = plt.gca()
pressure_at_node123 = results.node.loc['pressure', :, '123']
pressure_at_node123.plot(ax=ax)
plotly.offline.plot_mpl(fig, filename='pressure_at123_timeseries.html', auto_open=False) 

fig = plt.figure()
ax = plt.gca()
pressure = results.node.loc['pressure', :, :]
pressure.plot(legend=False, ax=ax)
plotly.offline.plot_mpl(fig, filename='pressure_timeseries.html', auto_open=False) 