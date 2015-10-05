import wntr
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import os

# Create a water network model
my_path = os.path.abspath(os.path.dirname(__file__))
inp_file = os.path.join(my_path,'networks','Net3.inp')
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
CHEM_at_5hr = results_CHEM.node.loc[(slice(None), 5*3600), 'quality']
CHEM_at_5hr.reset_index(level=1, drop=True, inplace=True)
attr = dict(CHEM_at_5hr)
wntr.network.draw_graph(wn, node_attribute=attr, node_size=20, 
                      title='Chemical concentration, time = 5 hours')
CHEM_at_node = results_CHEM.node.loc[('208', slice(None)), 'quality']
plt.figure()
CHEM_at_node.plot(title='Chemical concentration, node 208')

# Plot age scenario (convert to hours)
AGE_at_5hr = results_AGE.node.loc[(slice(None), 5*3600), 'quality']/3600
AGE_at_5hr.reset_index(level=1, drop=True, inplace=True)
attr = dict(AGE_at_5hr)
wntr.network.draw_graph(wn, node_attribute=attr, node_size=20, 
                      title='Water age (hrs), time = 5 hours')
AGE_at_node = results_AGE.node.loc[('208', slice(None)), 'quality']/3600
plt.figure()
AGE_at_node.plot(title='Water age, node 208')

# Plot trace scenario 
TRACE_at_5hr = results_TRACE.node.loc[(slice(None), 5*3600), 'quality']
TRACE_at_5hr.reset_index(level=1, drop=True, inplace=True)
attr = dict(TRACE_at_5hr)
wntr.network.draw_graph(wn, node_attribute=attr, node_size=20, 
                      title='Trace percent, time = 5 hours')
TRACE_at_node = results_TRACE.node.loc[('208', slice(None)), 'quality']
plt.figure()
TRACE_at_node.plot(title='Trace percent, node 208')

quality_lower_bound = 0.0002 # kg/m3 (0.2 mg/L)
quality_upper_bound = 0.004 # kg/m3 (4 mg/L)

"""
UPDATE
# Fraction of delivered quality (FDQ)
fdq = en.metrics.fraction_delivered_quality(G, quality_upper_bound)
print "Average FDQ: " +str(np.mean(fdq.values()))
en.network.draw_graph(wn, node_attribute=fdq, title= 'FDQ')

# Chlorine concentration stats
CL = nx.get_node_attributes(G,'quality')
CL = np.array(CL.values())
CL_regulation = float(sum((np.min(CL,axis=1) > quality_lower_bound) & (np.max(CL,axis=1) < quality_upper_bound)))/G.number_of_nodes()
print "Fraction of nodes > 0.2 mg/L and < 4 mg/L CL: " + str(CL_regulation)
CL_mgL = CL*float((units.kg/units.m**3)/(units.mg/units.l)) # kg/m3 to mg/L
print "Average CL concentration: " +str(np.mean(CL_mgL)) + " mg/L"

# Calculate mass of water consumed
MC = en.metrics.health_impacts.MC(G) 
total_MC = sum(MC.values())
print "Mass of water consumed: " + str(total_MC)
en.network.draw_graph(wn, node_attribute=MC, node_range = [0,100000],
                      title='Mass of Water Consumed, Total = ' + str(total_MC))
                      
# Calculate average water age (last 48 hours)
enData.ENsetqualtype(en.pyepanet.EN_AGE,0,0,0)
enData.ENgetqualtype() 
G = en.sim.eps_waterqual(enData, G)
age = nx.get_node_attributes(G,'quality')
age_h = np.array(age.values())*float(units.second/units.hour) # s to h
age_h_last_48h = age_h[:,age_h.shape[1]-round((48*3600)/timestep):]
plt.figure()
plt.plot(age_h_last_48h.transpose())
plt.ylabel('Water age (last 48 hours)')
plt.xlabel('Time (s)')
ave_age = dict(zip(age.keys(),np.mean(age_h_last_48h,1)))
en.network.draw_graph_OLD(G, node_attribute=ave_age, 
                      title='Average water age (last 48 hours)', node_size=40)
print "Average water age (last 48 hours): " +str(np.mean(age_h_last_48h)) + " hr"
"""
