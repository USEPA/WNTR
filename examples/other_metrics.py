import wntr
import numpy as np
import matplotlib.pyplot as plt

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
                   
# Compute population per node
pop = wntr.metrics.population(wn)
total_population = pop.sum()
print "Total population: " + str(total_population)
wntr.network.draw_graph(wn, node_attribute=pop, node_range = [0,400], node_size=40,
                      title='Population, Total = ' + str(total_population))
                      
# Find population and nodes impacted by pressure less than 40 m
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()
junctions = [name for name, node in wn.junctions()]
pop_impacted = wntr.metrics.population_impacted(pop, results.node['pressure',:,junctions], np.less, 40)
plt.figure()
pop_impacted.sum(axis=1).plot(title='Total population with pressure < 40 m') 
nodes_impacted = wntr.metrics.query(results.node['pressure',:,junctions], np.less, 40)
wntr.network.draw_graph(wn, node_attribute=nodes_impacted.any(axis=0), node_size=40,
                      title='Nodes impacted')

# Copute network cost
network_cost = wntr.metrics.cost(wn)
print "Network cost: $" + str(round(network_cost,2))

# COmpute green house gas emissions
network_ghg = wntr.metrics.ghg_emissions(wn)
print "Network GHG emissions: " + str(round(network_ghg,2))
