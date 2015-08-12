import wntr
import pandas as pd

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Graph the network
wntr.network.draw_graph(wn, title=wn.name)

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim(demo=True)

# Plot results on the network
pressure_at_5hr = results.node.loc[(slice(None), pd.Timedelta(hours = 5)), 'pressure']
wntr.network.draw_graph(wn, node_attribute=pressure_at_5hr, node_size=30, 
                        title='Pressure at 5 hours')
