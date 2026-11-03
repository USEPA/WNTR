"""
The following example demonstrates how to import WNTR, create a water 
network model from an EPANET INP file, simulate hydraulics, and plot 
simulation results on the network.
"""
# Import WNTR
import wntr
import matplotlib.pyplot as plt

# Create a water network model
wn = wntr.network.WaterNetworkModel('examples/networks/CTOWN.inp')

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Plot results on the network
pressure_at_5hr = results.node['pressure'].loc[5*3600, :]
wntr.graphics.plot_network(wn, node_attribute=pressure_at_5hr, 
                           node_size=30, title='Pressure at 5 hours')

plt.show()