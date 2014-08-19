import epanetlib as en
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

plt.close('all')

# Create enData
enData = en.pyepanet.ENepanet()
enData.inpfile = 'networks/Net3.inp'
enData.ENopen(enData.inpfile,'tmp.rpt')

# Create MultiDiGraph and plot as an undirected network
G = en.network.epanet_to_MultiDiGraph(enData)
en.network.draw_graph(G.to_undirected(), title=enData.inpfile)

# Setup timesteps for analysis, default = 0:EN_REPORTSTEP:EN_DURATION
duration = enData.ENgettimeparam(en.pyepanet.EN_DURATION)
timestep = enData.ENgettimeparam(en.pyepanet.EN_REPORTSTEP)
tstart = 24*3600
G.graph['time'] = range(tstart,duration+1,timestep)

# Run hydarulic simulation and save data
G = en.sim.eps_hydraulic(enData, G)

# Run hydarulic simulation and save data
G = en.sim.eps_waterqual(enData, G)

# Chlorine concentration stats
lower_bound = en.units.convert('Concentration', 1, 0.2) # mg/L to kg/m3
upper_bound = en.units.convert('Concentration', 1, 4) # mg/L to kg/m3
CL = nx.get_node_attributes(G,'quality')
CL = np.array(CL.values())
CL_regulation = float(sum((np.min(CL,axis=1) > lower_bound) & (np.max(CL,axis=1) < upper_bound)))/G.number_of_nodes()
print "Fraction of nodes > 0.2 mg/L and < 4 mg/L CL: " + str(CL_regulation)
CL_mgL = en.units.convert('Concentration', G.graph['flowunits'], CL, MKS=False)
print "Average CL concentration: " +str(np.mean(CL_mgL)) + " mg/L"

# Calculate mass of water consumed
MC = en.metrics.health_impacts.MC(G) 
total_MC = sum(MC.values())
print "Mass of Water Consumed: " + str(total_MC)
en.network.draw_graph(G.to_undirected(), node_attribute=MC, node_range = [0,100000],
                      title='Mass of Water Consumed, Total = ' + str(total_MC))
                      
# Calculate average water age
enData.ENsetqualtype(en.pyepanet.EN_AGE,0,0,0)
enData.ENgetqualtype() 
G = en.sim.eps_waterqual(enData, G)
age = nx.get_node_attributes(G,'quality')
age = np.array(age.values())
age_h = en.units.convert('Water Age', G.graph['flowunits'], age, MKS=False)
print "Average water age: " +str(np.mean(age_h))
