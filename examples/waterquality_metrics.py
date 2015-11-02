import wntr
import matplotlib.pyplot as plt
import numpy as np

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Define WQ scenarios
"""
Scenario format: 
QualityType, options = CHEM, AGE, or TRACE
Node, (used for CHEM and TRACE only) 
SourceType, options = CONCEN, MASS, FLOWPACED, or SETPOINT (used for CHEM only)
SourceQual, kg/m3 (used for CHEM only)
Start time, s  (used for CHEM only)
End time, s (used for CHEM only, -1 = simulation duration)
"""
sceanrio_CHEM = ['CHEM', '121', 'SETPOINT', 1000, 3600*2, 3600*15]
sceanrio_AGE = ['AGE']
sceanrio_TRACE = ['TRACE', '111']

# Simulate hydraulics and water quality for each scenario
sim = wntr.sim.EpanetSimulator(wn)
results_CHEM = sim.run_sim(WQ = sceanrio_CHEM)
results_AGE = sim.run_sim(WQ = sceanrio_AGE)
results_TRACE = sim.run_sim(WQ = sceanrio_TRACE)

# plot chem scenario
CHEM_at_5hr = results_CHEM.node.loc['quality', 5*3600, :]
wntr.network.draw_graph(wn, node_attribute=CHEM_at_5hr, node_size=20, 
                      title='Chemical concentration, time = 5 hours')
CHEM_at_node = results_CHEM.node.loc['quality', :, '208']
plt.figure()
CHEM_at_node.plot(title='Chemical concentration, node 208')

# Plot age scenario (convert to hours)
AGE_at_5hr = results_AGE.node.loc['quality', 5*3600, :]/3600.0
wntr.network.draw_graph(wn, node_attribute=AGE_at_5hr, node_size=20, 
                      title='Water age (hrs), time = 5 hours')
AGE_at_node = results_AGE.node.loc['quality', :, '208']/3600.0
plt.figure()
AGE_at_node.plot(title='Water age, node 208')

# Plot trace scenario 
TRACE_at_5hr = results_TRACE.node.loc['quality', 5*3600, :]
wntr.network.draw_graph(wn, node_attribute=TRACE_at_5hr, node_size=20, 
                      title='Trace percent, time = 5 hours')
TRACE_at_node = results_TRACE.node.loc['quality', :, '208']
plt.figure()
TRACE_at_node.plot(title='Trace percent, node 208')

MC = wntr.metrics.mass_contaminant_consumed(results_CHEM.node)
VC = wntr.metrics.volume_contaminant_consumed(results_CHEM.node, 0.001)
EC = wntr.metrics.extent_contaminant(results_CHEM.node, results_CHEM.link, wn, 0.001)

# Calculate average water age (last 48 hours)
age = results_AGE.node.loc['quality',:,:]
age_last_48h = age.loc[age.index[-1]-48*3600:age.index[-1]]/3600
age_last_48h.index = age_last_48h.index/3600
age_last_48h.plot(legend=False)
plt.ylabel('Water age (h)')
plt.xlabel('Time (h)')
wntr.network.draw_graph(wn, node_attribute=age_last_48h.mean(), 
                      title='Average water age (last 48 hours)', node_size=40)
print "Average water age (last 48 hours): " +str(age_last_48h.mean().mean()) + " hr"

# Chemical concentration stats
chem_upper_bound = 750 
chem = results_CHEM.node.loc['quality', :, :]
mask = wntr.metrics.query(chem, np.greater, chem_upper_bound)
chem_regulation = mask.any(axis=0) # True for any time
wntr.network.draw_graph(wn, node_attribute=chem_regulation, node_size=40, 
                      title= 'Nodes with conc > upper bound')
wntr.network.draw_graph(wn, node_attribute=chem.max(axis=0), node_size=40, 
                      title= 'Max concentration')
print "Fraction of nodes > chem upper bound: " + str(chem_regulation.sum())
print "Average node concentration: " +str(chem.mean().mean())
