import epanetlib as en
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

plt.close('all')

quality_lower_bound = en.units.convert('Concentration', 1, 0.2) # mg/L to kg/m3
quality_upper_bound = en.units.convert('Concentration', 1, 4) # mg/L to kg/m3

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

# Fraction of delivered quality (FDQ)
fdq = en.metrics.fraction_delivered_quality(G, quality_upper_bound)
print "Average FDQ: " +str(np.mean(fdq.values()))
en.network.draw_graph(G.to_undirected(), node_attribute=fdq, title= 'FDQ')

# Chlorine concentration stats
CL = nx.get_node_attributes(G,'quality')
CL = np.array(CL.values())
CL_regulation = float(sum((np.min(CL,axis=1) > quality_lower_bound) & (np.max(CL,axis=1) < quality_upper_bound)))/G.number_of_nodes()
print "Fraction of nodes > 0.2 mg/L and < 4 mg/L CL: " + str(CL_regulation)
CL_mgL = en.units.convert('Concentration', G.graph['flowunits'], CL, MKS=False)
print "Average CL concentration: " +str(np.mean(CL_mgL)) + " mg/L"

# Calculate mass of water consumed
MC = en.metrics.health_impacts.MC(G) 
total_MC = sum(MC.values())
print "Mass of water consumed: " + str(total_MC)
en.network.draw_graph(G.to_undirected(), node_attribute=MC, node_range = [0,100000],
                      title='Mass of Water Consumed, Total = ' + str(total_MC))
                      
# Calculate average water age
enData.ENsetqualtype(en.pyepanet.EN_AGE,0,0,0)
enData.ENgetqualtype() 
G = en.sim.eps_waterqual(enData, G)
age = nx.get_node_attributes(G,'quality')
temp = np.array(age.values())
age2 = dict(zip(age.keys(),np.mean(temp,1)/3600))
en.network.draw_graph(G, node_attribute=age2, 
                      title='Average water age', node_size=40)
age = np.array(age.values())
age_h = en.units.convert('Water Age', G.graph['flowunits'], age, MKS=False)
print "Average water age: " +str(np.mean(age_h)) + " hr"
