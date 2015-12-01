import wntr
import numpy as np
import matplotlib.pyplot as plt

plt.close('all')

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Compute population per node and average water consumed per day
qbar = wntr.metrics.average_water_consumed_perday(wn)
pop = wntr.metrics.population(wn)
total_population = pop.sum()
print "Total population: " + str(total_population)
wntr.network.draw_graph(wn, node_attribute=qbar, node_range = [0,0.03], node_size=40,
                      title='Average volume of water consumed per day')
wntr.network.draw_graph(wn, node_attribute=pop, node_range = [0,400], node_size=40,
                      title='Population, Total = ' + str(total_population))
                      
# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

junctions = [name for name, node in wn.nodes(wntr.network.Junction)]

# Calculate population impacted
pop_impacted = wntr.metrics.population_impacted(pop, results.node['pressure',:,junctions], np.less, 40)
plt.figure()
pop_impacted.sum(axis=1).plot(title='Total population with pressure < 40 m') 

# Calculate nodes impacted
nodes_impacted = wntr.metrics.query(results.node['pressure',:,junctions], np.less, 40)
wntr.network.draw_graph(wn, node_attribute=nodes_impacted.any(axis=0), node_size=40,
                      title='Nodes impacted')
