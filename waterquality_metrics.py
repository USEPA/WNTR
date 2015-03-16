"""
TODO This file needs to be updated to use the WaterNetworkModel (EPANET ONLY)
TODO Metrics must be updated to use NetworkResults
"""

import epanetlib as en
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from sympy.physics import units

plt.close('all')

quality_lower_bound = 0.2*float((units.mg/units.l)/(units.kg/units.m**3)) # mg/L to kg/m3
quality_upper_bound = 4*float((units.mg/units.l)/(units.kg/units.m**3)) # mg/L to kg/m3

# Create enData
enData = en.pyepanet.ENepanet()
enData.inpfile = 'networks/Net3_wSource.inp'
enData.ENopen(enData.inpfile,'tmp.rpt')

# Define a concentration source (I DON'T THINK THIS WORKS)
#enData.ENsetqualtype(en.pyepanet.EN_CHEM, 'Chlorine', 'mg/L', '')
#nodeid = enData.ENgetnodeindex('121')
#enData.ENsetnodevalue(nodeid, en.pyepanet.EN_SOURCEQUAL, 4)

# Create MultiDiGraph and plot as an undirected network
G = en.network.epanet_to_MultiDiGraph(enData)
en.network.draw_graph_OLD(G.to_undirected(), title=enData.inpfile)

# Setup timesteps for analysis, default = 0:EN_REPORTSTEP:EN_DURATION
duration = enData.ENgettimeparam(en.pyepanet.EN_DURATION)
timestep = enData.ENgettimeparam(en.pyepanet.EN_REPORTSTEP)
tstart = 24*3600
G.graph['time'] = range(tstart,duration+1,timestep)

# Run hydarulic simulation and save data
G = en.sim.eps_hydraulic(enData, G)

# Run hydarulic simulation and save data
G = en.sim.eps_waterqual(enData, G)

# Fraction of delivered quality (FDQ)
fdq = en.metrics.fraction_delivered_quality(G, quality_upper_bound)
print "Average FDQ: " +str(np.mean(fdq.values()))
en.network.draw_graph_OLD(G.to_undirected(), node_attribute=fdq, title= 'FDQ')

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
en.network.draw_graph_OLD(G.to_undirected(), node_attribute=MC, node_range = [0,100000],
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