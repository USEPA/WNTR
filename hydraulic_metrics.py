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

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

nHours = 48
wn.time_options['DURATION'] = nHours*3600
wn.time_options['HYDRAULIC TIMESTEP'] = 3600

# Add options and conditional controls for PDD
wn.options['MINIMUM PRESSURE'] = 0 # m
wn.options['NOMINAL PRESSURE'] = 40*float(units.psi/units.waterpressure) # psi to m      

# Simulate using Pyomo
sim = en.sim.PyomoSimulator(wn)
results = sim.run_sim()

nzd_junctions = wn.query_node_attribute('base_demand', np.greater, 0, node_type=en.network.Junction).keys()
junctions = [node_name for node_name, node in wn.nodes(en.network.Junction)]

# Fraction of delivered volume (FDV)
#fdv = en.metrics.fraction_delivered_volume(results, pressure_lower_bound)
#print "Average FDV: " +str(np.mean(fdv.values()))
#en.network.draw_graph_OLD(G.to_undirected(), node_attribute=fdv, 
#                      title= 'FDV', node_range=[0,1])

# Fraction of delivered demand (FDD)
#fdd = en.metrics.fraction_delivered_demand(G, pressure_lower_bound, demand_factor)
#print "Average FDD: " +str(np.mean(fdd.values()))
#en.network.draw_graph_OLD(G.to_undirected(), node_attribute=fdd, 
#                      title= 'FDD', node_range=[0,1])

# Pressure stats
pressure = results.node.loc[(junctions, slice(None)), 'pressure']
pressure_regulation = float(sum(pressure.min(level=0) > pressure_lower_bound))/len(junctions)
print "Fraction of nodes > 30 psi: " + str(pressure_regulation)
print "Average node pressure: " +str(pressure.mean()) + " m"
attr = dict(pressure.min(level=0))
en.network.draw_graph(wn, node_attribute=attr, node_size=40, title= 'Min pressure')

# Compute population per node
demand = results.node.loc[(junctions, slice(None)), 'demand']
qbar = en.metrics.average_demand_perday(demand) # average volume of water consumed per day, m3/day
R = 200*float((units.gallon/units.day)/(units.m**3/units.day)) # average volume of water consumed per capita per day, m3/day
pop = en.metrics.population(qbar,R)
total_population = sum(pop.values())
print "Total population: " + str(total_population)
en.network.draw_graph(wn, node_attribute=pop, node_range = [0,400],
                      title='Population, Total = ' + str(total_population))
              
# Compute todini index
todini = en.metrics.todini(G, pressure_lower_bound)
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
G = wn.get_graph_copy()
flowrate = results.link.loc[(slice(None), pd.Timedelta(hours = t)), 'flowrate']
for index, value in flowrate.iteritems():
    link_name = index[0]
    link = wn.get_link(link_name)
    if value < 0:
        G.remove_edge(link.start_node(), link.end_node(), link_name)
        G.add_edge(link.end_node(), link.start_node(), link_name)
        
bet_cen = nx.betweenness_centrality(G)
bet_cen_trim = dict([(k,v) for k,v in bet_cen.iteritems() if v > 0.001])
en.network.draw_graph(wn, node_attribute=bet_cen, title='Betweenness Centrality', node_size=40)
central_pt_dom = sum(max(bet_cen.values()) - np.array(bet_cen.values()))/G.number_of_nodes()
print "Central point dominance: " + str(central_pt_dom)

# Compute all paths at time 36, for node 185
[S, Shat, sp, dk] = en.metrics.entropy(G, sink=['185'])
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
