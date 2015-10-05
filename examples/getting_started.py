import wntr
import os

# Create a water network model
my_path = os.path.abspath(os.path.dirname(__file__))
inp_file = os.path.join(my_path,'networks','Net3.inp')
wn = wntr.network.WaterNetworkModel(inp_file)

# Graph the network
wntr.network.draw_graph(wn, title=wn.name)

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Plot results on the network
pressure_at_5hr = results.node.loc[(slice(None), 5*3600), 'pressure']
#pressure_at_5hr = results.node.loc['pressure', :, 5*3600]
wntr.network.draw_graph(wn, node_attribute=pressure_at_5hr, node_size=30, 
                        title='Pressure at 5 hours')
