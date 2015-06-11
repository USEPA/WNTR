import epanetlib as en
import numpy as np
import networkx as nx
from sympy.physics import units
import matplotlib.pyplot as plt
import pandas as pd

plt.close('all')

## Define water pressure unit in meters
if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa
if not units.find_unit('gallon'):
    units.gallon = 4*units.quart
    
pressure_lower_bound = 30*float(units.psi/units.waterpressure) # psi to m
demand_factor = 0.9 # 90% of requested demand

inp_file = 'networks/Net3.inp'

# Create a water network model for results object
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Simulate hydrulics
sim = en.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Fraction of delivered volume (FDV)
adjust_demand_flag = True
fdv = en.metrics.fraction_delivered_volume(results, 
                                           pressure_lower_bound, 
                                           adjust_demand_flag)                                          
print "Average FDV: " +str(np.mean(fdv.values()))

en.network.draw_graph(wn                    , 
                      node_attribute = fdv  , 
                      node_size      = 40   ,
                      title          = 'FDV', 
                      node_range     = [0,1])

# Fraction of delivered demand (FDD)
fdd = en.metrics.fraction_delivered_demand(results, 
                                           pressure_lower_bound, 
                                           demand_factor, 
                                           adjust_demand_flag)
print "Average FDD: " +str(np.mean(fdd.values()))

en.network.draw_graph(wn                    , 
                      node_attribute = fdd  , 
                      node_size      = 40   ,
                      title          = 'FDD', 
                      node_range     = [0,1])

# Create list of node names
junctions = [node_name for node_name, node in wn.nodes(en.network.Junction)]

# Pressure stats
pressure = results.node.loc[(junctions, slice(None)), 'pressure']
pressure_regulation = float(sum(pressure.min(level=0) > pressure_lower_bound))/len(junctions)
print "Fraction of nodes > 30 psi: " + str(pressure_regulation)
print "Average node pressure: " +str(pressure.mean()) + " m"
attr = dict(pressure.min(level=0))
en.network.draw_graph(wn, node_attribute=attr, node_size=40, title= 'Min pressure')

# Compute population per node
qbar = en.metrics.average_demand_perday(results) # average volume of water consumed per day, m3/day
R = 200*float((units.gallon/units.day)/(units.m**3/units.day)) # average volume of water consumed per capita per day, m3/day
pop = en.metrics.population(qbar,R)
total_population = sum(pop.values())
print "Total population: " + str(total_population)
en.network.draw_graph(wn, node_attribute=pop, node_range = [0,400], node_size=40,
                      title='Population, Total = ' + str(total_population))
              
# Compute todini index
#todini = en.metrics.todini(G, pressure_lower_bound)
todini = en.metrics.todini(results,wn, pressure_lower_bound)
plt.figure()
plt.plot(todini)
plt.ylabel('Todini Index')
plt.xlabel('Time, hr')
print "Todini Index"
print "  Mean: " + str(np.mean(todini))
print "  Max: " + str(np.max(todini))
print "  Min: " + str(np.min(todini))

# Create a weighted graph for flowrate at time 36 hours
t = pd.Timedelta(hours = 36)
attr = results.link.loc[(slice(None), t), 'flowrate']
G_flowrate_36hrs = wn.get_weighted_graph_copy(link_attribute=attr)

node_attr = results.node.loc[(slice(None), t), 'demand']
G_temp = wn.get_weighted_graph_copy(node_attribute=node_attr)
 
# Compute betweenness-centrality time 36 hours
bet_cen = nx.betweenness_centrality(G_flowrate_36hrs)
bet_cen_trim = dict([(k,v) for k,v in bet_cen.iteritems() if v > 0.001])
en.network.draw_graph(wn, node_attribute=bet_cen, title='Betweenness Centrality', node_size=40)
central_pt_dom = sum(max(bet_cen.values()) - np.array(bet_cen.values()))/G_flowrate_36hrs.number_of_nodes()
print "Central point dominance: " + str(central_pt_dom)

# Compute all paths at time 36, for node 185
[S, Shat, sp, dk] = en.metrics.entropy(G_flowrate_36hrs, sink=['185'])
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
en.network.draw_graph(wn, link_attribute=attr, link_cmap=cmap, link_width=1, 
                      node_attribute={'River': 1, 'Lake': 1, '185': 1}, node_cmap=plt.cm.gray, node_size=30, 
                      title='dk')

# Calculate entropy for 1 day, all nodes
T = pd.timedelta_range(start=pd.Timedelta(hours = 0), end=pd.Timedelta(hours = 24), freq='H')
shat = []
for t in T: 
    attr = results.link.loc[(slice(None), t), 'flowrate']
    G_flowrate_t = wn.get_weighted_graph_copy(link_attribute=attr)
    entropy = en.metrics.entropy(G_flowrate_t)
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

network_cost = en.metrics.cost(wn, tank_cost, pipe_cost, valve_cost, pump_cost)
print "Network cost: $" + str(round(network_cost,2))

network_ghg = en.metrics.ghg_emissions(wn, pipe_ghg)
print "Network GHG emissions: " + str(round(network_ghg,2))
