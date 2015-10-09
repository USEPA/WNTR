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

# Compute fraction of delivered volume (FDV)
P_lower = 21.09 # m (30 psi)
#fdv = wntr.metrics.fraction_delivered_volume(results, P_lower, True)                                          
#print "Average FDV: " +str(np.mean(fdv.values()))
#wntr.network.draw_graph(wn, node_attribute = fdv, node_size = 40, title = 'FDV', 
#                      node_range= [0,1])

# Compute fraction of delivered demand (FDD)
demand_factor = 0.9 # 90% of requested demand
#fdd = wntr.metrics.fraction_delivered_demand(results, P_lower, demand_factor, 
#                                           True)
#print "Average FDD: " +str(np.mean(fdd.values()))
#wntr.network.draw_graph(wn, node_attribute = fdd, node_size = 40, title = 'FDD', 
#                      node_range = [0,1])

# Create list of node names
junctions = [node_name for node_name, node in wn.nodes(wntr.network.Junction)]

# Pressure stats
pressure = results.node.loc['pressure', :, junctions]
pressure_regulation = float(sum(pressure.min(axis=0) > P_lower))/len(junctions)
print "Fraction of nodes > 30 psi: " + str(pressure_regulation)
print "Average node pressure: " +str(pressure.mean()) + " m"
attr = dict(pressure.min(axis=0))
wntr.network.draw_graph(wn, node_attribute=attr, node_size=40, 
                      title= 'Min pressure')

# Compute population per node
# R = average volume of water consumed per capita per day
R = 0.00000876157 # m3/s (200 gallons/day)
# qbar = average demand per node...this needs to updated to reflect daily average
qbar = results.node.loc['demand', :, junctions].mean()
pop = qbar/R
total_population = pop.sum()
print "Total population: " + str(total_population)
wntr.network.draw_graph(wn, node_attribute=pop, node_range = [0,400], node_size=40,
                      title='Population, Total = ' + str(total_population))
              
# Compute todini index
todini = wntr.metrics.todini(results,wn, P_lower)
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
G_flowrate_36hrs = wntr.utils.weight_graph(wn._graph, link_attribute=attr)    

node_attr = results.node.loc['demand', t, :]
G_temp = wntr.utils.weight_graph(wn._graph, node_attribute=attr)    
 
# Compute betweenness-centrality time 36 hours
bet_cen = nx.betweenness_centrality(G_flowrate_36hrs)
bet_cen_trim = dict([(k,v) for k,v in bet_cen.iteritems() if v > 0.001])
wntr.network.draw_graph(wn, node_attribute=bet_cen, 
                      title='Betweenness Centrality', node_size=40)
central_pt_dom = sum(max(bet_cen.values()) - np.array(bet_cen.values()))/G_flowrate_36hrs.number_of_nodes()
print "Central point dominance: " + str(central_pt_dom)

# Compute all paths at time 36, for node 185
[S, Shat, sp, dk] = wntr.metrics.entropy(G_flowrate_36hrs, sink=['185'])
attr = dict( (k,1) for u,v,k,d in G_flowrate_36hrs.edges(keys=True,data=True))
for k in dk.keys():
    u = k[0]
    v = k[1]
    link = G_flowrate_36hrs.edge[u][v].keys()[0]
    attr[link] = 2 #dk[k]
cmap = plt.cm.jet
cmaplist = [cmap(i) for i in range(cmap.N)] # extract all colors from the .jet map
cmaplist[0] = (.5,.5,.5,1.0) # force the first color entry to be grey
cmaplist[cmap.N-1] = (1,0,0,1) # force the last color entry to be red
cmap = cmap.from_list('Custom cmap', cmaplist, cmap.N) # create the new map
wntr.network.draw_graph(wn, link_attribute=attr, link_cmap=cmap, link_width=1, 
                      node_attribute = {'River': 1, 'Lake': 1, '185': 1}, 
                      node_cmap=plt.cm.gray, node_size=30, title='dk')

# Calculate entropy for 1 day, all nodes
shat = []
for t in np.arange(0, 24*3600+1,3600): 
    attr = results.link.loc['flowrate', t, :]
    G_flowrate_t = wntr.utils.weight_graph(wn._graph, link_attribute=attr)    
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

# Compute network cost and GHG emissions
tank_cost = np.loadtxt('data/cost_tank.txt',skiprows=1)
pipe_cost = np.loadtxt('data/cost_pipe.txt',skiprows=1)
valve_cost = np.loadtxt('data/cost_valve.txt',skiprows=1)
pump_cost = 3783 # average from BWN-II
pipe_ghg = np.loadtxt('data/ghg_pipe.txt',skiprows=1)

network_cost = wntr.metrics.cost(wn, tank_cost, pipe_cost, valve_cost, pump_cost)
print "Network cost: $" + str(round(network_cost,2))

network_ghg = wntr.metrics.ghg_emissions(wn, pipe_ghg)
print "Network GHG emissions: " + str(round(network_ghg,2))
