
"""
TODO This file needs to be updated to use the WaterNetworkModel
TODO Metrics must be updated to use NetworkResults
"""

import epanetlib as en
import numpy as np
import networkx as nx
from sympy.physics import units
import matplotlib.pyplot as plt

plt.close('all')

# Define water pressure unit in meters
if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa

pressure_lower_bound = 30*float(units.psi/units.waterpressure) # psi to m
demand_factor = 0.9 # 90% of requested demand

inp_file = 'networks/Net3.inp'
adjust_demand = False

####### OLD WAY - BEGIN #######
# Create enData for G
enData = en.pyepanet.ENepanet()
enData.inpfile = inp_file
enData.ENopen(enData.inpfile,'tmp.rpt')

# Create MultiDiGraph and plot as an undirected network
G = en.network.epanet_to_MultiDiGraph(enData)
en.network.draw_graph_OLD(G.to_undirected(), title=enData.inpfile)

# Run hydarulic simulation and save data
G = en.sim.eps_hydraulic(enData, G)

## Fraction of delivered volume (FDV)
#fdv = en.metrics.fraction_delivered_volume_old(G, pressure_lower_bound)
#print "Average FDV: " +str(np.mean(fdv.values()))
#en.network.draw_graph_OLD(G.to_undirected(), node_attribute=fdv, 
#                      title= 'FDV', node_range=[0,1])
#
## Fraction of delivered demand (FDD)
#fdd = en.metrics.fraction_delivered_demand_old(G, pressure_lower_bound, demand_factor)
#print "Average FDD: " +str(np.mean(fdd.values()))
#en.network.draw_graph_OLD(G.to_undirected(), node_attribute=fdd, 
#                      title= 'FDD', node_range=[0,1])     
####### OLD WAY - END #######

####### NEW WAY - BEGIN #######
# Create a water network model for results object
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Simulate using EPANET
epanet_sim = en.sim.EpanetSimulator(wn)
epanet_results = epanet_sim.run_sim()


# Fraction of delivered volume (FDV)
fdv = en.metrics.fraction_delivered_volume(epanet_results, pressure_lower_bound, adjust_demand)
print "Average FDV: " +str(np.mean(fdv.values()))
en.network.draw_graph_OLD(G.to_undirected(), node_attribute=fdv, 
                      title= 'FDV', node_range=[0,1])

# Fraction of delivered demand (FDD)
fdd = en.metrics.fraction_delivered_demand(epanet_results, pressure_lower_bound, demand_factor, adjust_demand)
print "Average FDD: " +str(np.mean(fdd.values()))
en.network.draw_graph_OLD(G.to_undirected(), node_attribute=fdd, 
                      title= 'FDD', node_range=[0,1])
####### NEW WAY - END #######

# Pressure stats
head = nx.get_node_attributes(G,'head')
elevation = nx.get_node_attributes(G,'elevation')
pressure = np.array(head.values()) - np.array(elevation.values(),ndmin=2).T
pressure_regulation = float(sum(np.min(pressure,axis=1) > pressure_lower_bound))/G.number_of_nodes()
print "Fraction of nodes > 30 psi: " + str(pressure_regulation)
pressure_psi = pressure*float(units.waterpressure/units.psi) # m to psi
print "Average node pressure: " +str(np.mean(pressure_psi)) + " psi"
attr = dict(zip(G.nodes(), list(np.min(pressure, 1) < pressure_lower_bound)))
attr2 = dict([(k,v) for k,v in attr.iteritems() if v > 0])
en.network.draw_graph_OLD(G.to_undirected(), node_attribute=attr2, title= 'Pressure')

# Compute population per node
qbar = en.metrics.average_demand_perday(G) # average volume of water consumed per day, m3/day
R = 0.757082 # average volume of water consumed per capita per day, m3/day (=200 gall/day)
pop = en.metrics.population(qbar,R)
total_population = sum(pop.values())
print "Total population: " + str(total_population)
en.network.draw_graph_OLD(G.to_undirected(), node_attribute=pop, node_range = [0,400],
                      title='Population, Total = ' + str(total_population))
              
# Compute todini index
#todini = en.metrics.todini(G, pressure_lower_bound)
todini = en.metrics.todini(epanet_results,wn, pressure_lower_bound)
plt.figure()
plt.plot(np.array(G.graph['time'])/3600, todini)
plt.ylabel('Todini Index')
plt.xlabel('Time, hr')
print "Todini Index"
print "  Mean: " + str(np.mean(todini))
print "  Max: " + str(np.max(todini))
print "  Min: " + str(np.min(todini))

# Compute betweenness-centrality time 36
t=36
attr = dict( ((u,v,k),d['flow'][t]) for u,v,k,d in G.edges(keys=True,data=True) if 'flow' in d)
G0 = en.network.epanet_to_MultiDiGraph(enData, edge_attribute=attr)
bet_cen = nx.betweenness_centrality(G0)  
bet_cen2 = dict([(k,v) for k,v in bet_cen.iteritems() if v > 0.001])
en.network.draw_graph_OLD(G, node_attribute=bet_cen2, 
                      title='Betweenness Centrality at time ' + str(t), node_size=40, node_range=[0.001, 0.005])
central_pt_dom = sum(max(bet_cen.values()) - np.array(bet_cen.values()))/G.number_of_nodes()
print "Central point dominance at time " + str(t) + ": " + str(central_pt_dom)

# Compute all paths at time 36, for node 185
[S, Shat, sp, dk] = en.metrics.entropy(G0, sink=['185'])
attr = dict( ((u,v,k),1) for u,v,k,d in G.edges(keys=True,data=True))
for k in dk.keys():
    u = k[0]
    v = k[1]
    link = G0.edge[u][v].keys()[0]
    attr[(u,v,link)] = 2 #dk[k]
cmap = plt.cm.jet
cmaplist = [cmap(i) for i in range(cmap.N)] # extract all colors from the .jet map
cmaplist[0] = (.5,.5,.5,1.0) # force the first color entry to be grey
cmaplist[cmap.N-1] = (1,0,0,1) # force the last color entry to be red
cmap = cmap.from_list('Custom cmap', cmaplist, cmap.N) # create the new map
en.network.draw_graph_OLD(G.to_undirected(), edge_attribute=attr, edge_cmap=cmap, edge_width=1, 
                      node_attribute={'River': 1, 'Lake': 1, '185': 1}, node_cmap=plt.cm.gray, node_size=30, 
                      title='dk')

# Calculate entropy for all times, all nodes
shat = []
for t in range(len(G.graph['time'])): 
    # Create MultiDiGraph for entropy
    attr = dict( ((u,v,k),d['flow'][t]) for u,v,k,d in G.edges(keys=True,data=True) if 'flow' in d)
    G0 = en.network.epanet_to_MultiDiGraph(enData, edge_attribute=attr)
    #en.network.draw_graph_OLD(G0, edge_attribute='weight', 
    #                      title='Flow at time = ' + str(G.graph['time'][t]))
    entropy = en.metrics.entropy(G0)
    #en.network.draw_graph_OLD(G, node_attribute=entropy[0],
    #                      title='Entropy, Flow at time = ' + str(G.graph['time'][t]))
    shat.append(entropy[1])
plt.figure()
plt.plot(np.array(G.graph['time'])/3600, shat)   
plt.ylabel('System Entropy')
plt.xlabel('Time, hr') 
print "Entropy"
print "  Mean: " + str(np.mean(shat))
print "  Max: " + str(np.nanmax(shat))
print "  Min: " + str(np.nanmin(shat))

plt.figure()
plt.scatter(todini, shat)
plt.ylabel('System Entropy')
plt.xlabel('Todini Index') 

# Compute network cost and GHG emissions
tank_cost = np.loadtxt('data/cost_tank.txt',skiprows=1)
pipe_cost = np.loadtxt('data/cost_pipe.txt',skiprows=1)
valve_cost = np.loadtxt('data/cost_valve.txt',skiprows=1)
pump_cost = 3783 # average from BWN-II
pipe_ghg = np.loadtxt('data/ghg_pipe.txt',skiprows=1)

network_cost = en.metrics.cost(G, tank_cost, pipe_cost, valve_cost, pump_cost)
print "Network cost: $" + str(round(network_cost,2))

network_ghg = en.metrics.ghg_emissions(G, pipe_ghg)
print "Network GHG emissions: " + str(round(network_ghg,2))
