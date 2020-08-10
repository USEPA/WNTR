"""
The following example uses WNTR to perform a hydraulic simulation of the 
network both with and without fire fighting flow demands.
"""
import wntr

# Create a water network model and simulate under nominal conditions
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
results = sim.run_sim()

# Add fire demand
fire_name = 'fire_pattern'
fire_flow_demand = 0.252 # 4000 gal/min = 0.252 m3/s
fire_start = 10*3600
fire_end = 36*3600
node = wn.get_node('197')
node.add_fire_fighting_demand(wn, fire_flow_demand, fire_start, fire_end)

# Reset initial values and simulate hydraulics with fire flow conditions
wn.reset_initial_values()
sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
fire_results = sim.run_sim()

# Plot resulting differences on the network
pressure_at_24hr = results.node['pressure'].loc[24*3600, :]
fire_pressure_at_24hr = fire_results.node['pressure'].loc[24*3600, :]
pressure_difference = fire_pressure_at_24hr - pressure_at_24hr
wntr.graphics.plot_network(wn, node_attribute=pressure_difference, node_size=30, 
                        title='Nominal - Fire Fighting \npressure difference at 24 hours')
