import epanetlib as en
import matplotlib.pyplot as plt
import numpy as np

plt.close('all')

# Input
inp_file_name = 'networks/Net3.inp'

# Create enData
enData = en.pyepanet.ENepanet()
enData.ENopen(inp_file_name,'tmp.rpt')

# Read network coordinates 
pos = en.pyepanet.future.ENgetcoordinates(inp_file_name)

# Create multi-graph
MG = en.network.epanet_to_MultiGraph(enData, pos=pos)

# Run base hydarulic simulation and save data
enData.ENopenH()
[time, node_P, node_D, link_F, link_V] = en.sim.eps_hydraulic(enData)

# Compute todini index
flowunits = enData.ENgetflowunits()
t=0
Pstar = en.units.convert('Pressure', flowunits, 30) # m
P = dict(zip(node_P.keys(), en.units.convert('Pressure', flowunits, np.array(node_P.values())))) # m
D = dict(zip(node_D.keys(), en.units.convert('Demand', flowunits, np.array(node_D.values())))) # m3/s
todini = en.metrics.todini(enData, P, D, Pstar)
plt.figure()
plt.title('Todini Index')
plt.plot(time, todini)

# Create directed-graph
edge_attribute = dict(zip(link_F.keys(), np.array(link_F.values())[:,t]))    
DG = en.network.epanet_to_MultiDiGraph(enData, edge_attribute, pos=pos)

#Plot
en.network.draw_graph(DG, edge_attribute='weight', 
                      title='Directed-graph, Flow at time = 0')
                        
# Compute entropy
entropy = en.metrics.entropy(DG, enData)

# Compute network cost and GHG emissions
if flowunits in [0,1,2,3,4]:
    tank_cost = en.metrics.read_network_data('data/US_cost_tank.txt')
    pipe_cost = en.metrics.read_network_data('data/US_cost_pipe.txt')
    valve_cost = en.metrics.read_network_data('data/US_cost_valve.txt')
    pump_cost = 3783 # average from BWN-II
    pipe_ghg = en.metrics.read_network_data('data/US_ghg_pipe.txt')
else: 
    tank_cost = en.metrics.read_network_data('data/SI_cost_tank.txt')
    pipe_cost = en.metrics.read_network_data('data/SI_cost_pipe.txt')
    valve_cost = en.metrics.read_network_data('data/SI_cost_valve.txt')
    pump_cost = 3783 # average from BWN-II
    pipe_ghg = en.metrics.read_network_data('data/SI_ghg_pipe.txt')        

network_cost = en.metrics.cost(enData, tank_cost, pipe_cost, valve_cost, pump_cost)
print "Network Cost: $" + str(round(network_cost,2))

network_ghg = en.metrics.ghg_emissions(enData, pipe_ghg)
print "Network GHG Emissions: " + str(round(network_ghg,2))
