import wntr
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import animation

plt.close('all')

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

sceanrio_TRACE = ['TRACE', '111']

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim(WQ = sceanrio_TRACE)

### Node Animation ###
node_values = results.node.loc[(slice(None), pd.Timedelta(hours = 0)), 'quality']
(nodes, edges) = wntr.network.draw_graph(wn, node_attribute=node_values, figsize=(14, 8), node_range = [0,100], node_size=30, title='Trace at 0 hours')
fig = plt.gcf()        

def update_nodes(frame_number):
    G = wn._graph
    
    nodelist = G.nodes()
    node_values = results.node.loc[(slice(None), pd.Timedelta(hours = frame_number)), 'quality']
    node_values = node_values[nodelist].values
    nodes.set_array(node_values)
    
    plt.title('Trace at ' + str(frame_number) +' hours')
    
    return nodes, edges
    
anim = animation.FuncAnimation(fig, update_nodes, frames=25, interval=400, repeat_delay = 1200, blit=True) # the movie flickers
# ani.save('node_animation_example.mp4') # movie does not save

### Link Animation ###
#link_values = results.link.loc[(slice(None), pd.Timedelta(hours = 0)), 'velocity']
#(nodes, edges) = wntr.network.draw_graph(wn, link_attribute=link_values, figsize=(14, 8), link_range = [0,3], link_width=2, title='Velocity at 0 hours')
#fig = plt.gcf()
#
#def update_edges(n):
#    G = wn._graph
#    
#    linklist = G.edges(keys=True)
#    linklist = [name for (start_node, end_node, name) in linklist]
#    link_values = results.link.loc[(slice(None), pd.Timedelta(hours = n)), 'velocity']
#    link_values = link_values[linklist].values
#    edges.set_array(link_values)
#    
#    plt.title('Velocity at ' + str(n) +' hours')
#    
#    return nodes, edges
#
#anim = animation.FuncAnimation(fig, update_edges, frames=25, interval=400, repeat_delay = 1200, blit=True) # the movie flickers
## ani.save('link_animation_example.mp4') # movie does not save