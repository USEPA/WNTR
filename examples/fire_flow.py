"""
The following example runs hydraulic simulations with and without fire 
fighting flow demand added to a single junction.
"""
import wntr

# Create a water network model and simulate under nominal conditions
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Add fire demand and simulate
fire_flow_demand = 0.252 # 4000 gal/min = 0.252 m3/s
fire_start = 10*3600
fire_end = 36*3600
node = wn.get_node('197')
node.add_fire_fighting_demand(wn, fire_flow_demand, fire_start, fire_end)
sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
fire_results = sim.run_sim()

# Reset initial values and simulate hydraulics under nominal conditions
wn.reset_initial_values()
node.remove_fire_fighting_demand(wn)
sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
results = sim.run_sim()

# Plot resulting differences on the network
pressure_at_24hr = results.node['pressure'].loc[24*3600, :]
fire_pressure_at_24hr = fire_results.node['pressure'].loc[24*3600, :]
pressure_difference = fire_pressure_at_24hr - pressure_at_24hr
wntr.graphics.plot_network(wn, node_attribute=pressure_difference, node_size=30, 
                        title='Nominal - Fire Fighting \npressure difference at 24 hours')
