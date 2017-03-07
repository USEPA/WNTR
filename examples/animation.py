import wntr
import matplotlib.pyplot as plt
from matplotlib import animation

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Simulate trace contaminant
wn.options.quality = 'TRACE'
wn.options.quality_value = '111'

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Animate trace percent
fig = plt.figure(figsize=(12,10), facecolor='w')
values = results.node.loc['quality', :, :]
initial_values = values.loc[0, :]
nodes, edges = wntr.graphics.draw_graph(wn, node_attribute=initial_values, 
    plt_fig=fig, node_range = [0,100], node_size=30, title='Trace at 0 hours')
    
def update(n):
  node_values = values.loc[n*3600, :]
  fig.clf()    
  nodes, edges = wntr.graphics.draw_graph(wn, node_attribute=node_values, 
    plt_fig=fig, node_range = [0,100], node_size=30, title='Trace at ' + str(n) +' hours')
  return nodes, edges

anim = animation.FuncAnimation(fig, update, interval=50, frames=97, blit=False, repeat=False)
