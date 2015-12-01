import wntr
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

plt.close('all')

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Create list of node names
junctions = [name for name, node in wn.junctions()]

# Define pressure lower bound
P_lower = 21.09 # m (30 psi)

# Query pressure
pressure = results.node.loc['pressure', :, junctions]
mask = wntr.metrics.query(pressure, np.greater, P_lower)
pressure_regulation = mask.all(axis=0).sum() # True over all time
print "Fraction of nodes > 30 psi: " + str(pressure_regulation)
print "Average node pressure: " +str(pressure.mean().mean()) + " m"
wntr.network.draw_graph(wn, node_attribute=pressure.min(axis=0), node_size=40, 
                      title= 'Min pressure')
              
# Compute todini index
todini = wntr.metrics.todini(results.node,results.link,wn, P_lower)
plt.figure()
plt.plot(todini)
plt.ylabel('Todini Index')
plt.xlabel('Time, hr')
print "Todini Index"
print "  Mean: " + str(np.mean(todini))
print "  Max: " + str(np.max(todini))
print "  Min: " + str(np.min(todini))

# Create a weighted graph for flowrate at time 36 hours
t = 36*3600
attr = results.link.loc['flowrate', t, :]   
G_flowrate_36hrs = wn.get_graph_deep_copy()
G_flowrate_36hrs.weight_graph(link_attribute=attr)     
 
# Compute betweenness-centrality time 36 hours
bet_cen = nx.betweenness_centrality(G_flowrate_36hrs)
wntr.network.draw_graph(wn, node_attribute=bet_cen, 
                      title='Betweenness Centrality', node_size=40)
central_pt_dom = G_flowrate_36hrs.central_point_dominance()
print "Central point dominance: " + str(central_pt_dom)

# Compute entropy at time 36, for node 185
[S, Shat] = wntr.metrics.entropy(G_flowrate_36hrs, sources=None, sinks=['185'])

# Plot all simple paths between the Lake/River and node 185
link_count = G_flowrate_36hrs.links_in_simple_paths(sources=['Lake', 'River'], sinks=['185'])
wntr.network.draw_graph(wn, link_attribute=link_count, link_width=1, 
                        node_attribute = {'River': 1, 'Lake': 1, '185': 1}, 
                        node_size=30, title='Link count in paths')
        
# Calculate entropy for 1 day, all nodes
shat = []
G_flowrate_t = wn.get_graph_deep_copy()
for t in np.arange(0, 24*3600+1,3600): 
    attr = results.link.loc['flowrate', t, :]
    G_flowrate_t.weight_graph(link_attribute=attr) 
    entropy = wntr.metrics.entropy(G_flowrate_t)
    shat.append(entropy[1])
plt.figure()
plt.plot(shat)   
plt.ylabel('System Entropy')
plt.xlabel('Time, hr') 
print "Entropy"
print "  Mean: " + str(np.mean(shat))
print "  Max: " + str(np.nanmax(shat))
print "  Min: " + str(np.nanmin(shat))
