import wntr
import numpy as np
import matplotlib.pylab as plt

plt.close('all')

# Simulate hydraulics and water quality
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
wn.options.duration = 48*3600
for name, node in wn.junctions():
    node.nominal_pressure = 60
sim = wntr.sim.ScipySimulator(wn, pressure_driven=True)
results = sim.run_sim()
       
# Isolate node results at consumer nodes (nzd = non-zero demand)
nzd_junctions = wn.query_node_attribute('base_demand', np.greater, 0, 
                                        node_type=wntr.network.Junction).keys()
node_results = results.node.loc[:, :, nzd_junctions]

# Compute population per node
pop = wntr.metrics.population(wn)

# Compute FDV, FDD, and FDQ, change average_times and average_nodes to average results
quality_upper_bound = 0.0035 # kg/m3 (3.5 mg/L)                   
demand_factor = 0.9
average_times = False
average_nodes = False
fdv = wntr.metrics.fdv(node_results, average_times, average_nodes)
fdd = wntr.metrics.fdd(node_results, demand_factor, average_times, average_nodes)
#fdq = wntr.metrics.fdq(node_results, quality_upper_bound, average_times, average_nodes)

# Plot results
if average_times == False and average_nodes == False:
    fdv.plot(ylim=(-0.05, 1.05), legend=False, title='FDV for each node and time')
    
    fdd.plot(ylim=(-0.05, 1.05),legend=False,  title='FDD for each node and time')
    # Fraction of nodes with reduced demand
    fdd_fraction_impacted = 1-fdd.sum(axis=1)/fdd.shape[1]
    plt.figure()
    fdd_fraction_impacted.plot(ylim=(-0.05, 1.05), title='Fraction of nodes not receiving adaquate demand')        
    # Population impacted by reduced demand
    fdd_pop_impacted = wntr.metrics.population_impacted(pop, fdd, np.less, 1)
    plt.figure()
    fdd_pop_impacted.plot(legend=False, title='Population not receiving adaquate demand')        
    # Timeseries of fraction of population not meeting demand
    plt.figure()
    fdd_pop_impacted.sum(axis=1).plot(title='Total population not receiving adaquate demand') 
    
elif average_times == True and average_nodes == False:
    wntr.network.draw_graph(wn, node_attribute=fdv, node_size=40, 
                            node_range=[0,1], title='FDV averaged over all times')
    wntr.network.draw_graph(wn, node_attribute=fdd, node_size=40, 
                            node_range=[0,1], title='FDD averaged over all times')
    
elif average_times == False and average_nodes == True:
    plt.figure()
    fdv.plot(ylim=(-0.05, 1.05), title='FDV averaged over all nodes')
    plt.figure()
    fdd.plot(ylim=(-0.05, 1.05), title='FDD averaged over all nodes')
