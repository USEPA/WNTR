import wntr
import matplotlib.pyplot as plt
from matplotlib import animation

plt.close('all')

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

WQscenario = wntr.scenario.Waterquality('TRACE', ['111'])

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim(WQscenario)

### Node Animation ###
node_values = results.node.loc['quality', 0, :]
(nodes, edges) = wntr.network.draw_graph(wn, node_attribute=node_values, figsize=(14, 8), node_range = [0,100], node_size=30, title='Trace at 0 hours')
fig = plt.gcf()        

def update_nodes(frame_number):
    G = wn.get_graph_deep_copy()
    
    nodelist = G.nodes()
    node_values = results.node.loc['quality', frame_number*3600, :]
    node_values = node_values[nodelist].values
    nodes.set_array(node_values)
    
    plt.title('Trace at ' + str(frame_number) +' hours')
    return nodes, edges
    
anim = animation.FuncAnimation(fig, update_nodes, frames=25, interval=400, repeat_delay = 1200, blit=True, repeat=False) # the movie flickers
#anim.save('node_animation_example.mp4') # movie does not save

### Link Animation ###
#link_values = results.link.loc['velocity',0,:]
#(nodes, edges) = wntr.network.draw_graph(wn, link_attribute=link_values, figsize=(14, 8), link_range = [0,3], link_width=2, title='Velocity at 0 hours')
#fig = plt.gcf()
#
#def update_edges(n):
#    G = wn.get_graph_deep_copy()
#    
#    linklist = G.edges(keys=True)
#    linklist = [name for (start_node, end_node, name) in linklist]
#    link_values = results.link.loc['velocity', n*3600,:]
#    link_values = link_values[linklist].values
#    edges.set_array(link_values)
#    
#    plt.title('Velocity at ' + str(n) +' hours')
#    
#    return nodes, edges
#
#anim = animation.FuncAnimation(fig, update_edges, frames=25, interval=400, repeat_delay = 1200, blit=True) # the movie flickers
## ani.save('link_animation_example.mp4') # movie does not save
