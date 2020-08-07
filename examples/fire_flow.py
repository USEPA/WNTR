"""
The following example uses WNTR to perform a hydraulic simulation of the 
network both with and without fire fighting flow demands.
"""
import matplotlib.pyplot as plt
import wntr

plt.close('all')

# Create a water network model both with and without fire fighting demand
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
wn_fire = wntr.network.WaterNetworkModel(inp_file)

# Add fire demand
fire_name = 'fire_pattern'
fire_flow_demand = 0.252 # 4000 gal/min = 0.252 m3/s
fire_start = 10*3600
fire_end = 36*3600
node = wn_fire.get_node('197')
node.add_fire_fighting_demand(wn_fire, fire_flow_demand, wn.options.time.pattern_timestep, wn.options.time.duration, 'fire_pattern', fire_start, fire_end)

# Simulate hydraulics with and without fire
sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
results = sim.run_sim()
fire_sim = wntr.sim.WNTRSimulator(wn_fire, mode='PDD')
fire_results = fire_sim.run_sim()

# Plot resulting differences on the network
pressure_at_24hr = results.node['pressure'].loc[24*3600, :]
fire_pressure_at_24hr = fire_results.node['pressure'].loc[24*3600, :]
pressure_difference = fire_pressure_at_24hr - pressure_at_24hr
wntr.graphics.plot_network(wn, node_attribute=pressure_difference, node_size=30, 
                        title='Nominal - Fire Fighting \npressure difference at 24 hours')


