import epanetlib as en
import matplotlib.pyplot as plt

plt.close('all')

# Create enData
enData = en.pyepanet.ENepanet()
enData.inpfile = 'networks/Net3.inp'
enData.ENopen(enData.inpfile,'tmp.rpt')

# Create MultiDiGraph
G = en.network.epanet_to_MultiDiGraph(enData)
en.network.draw_graph(G.to_undirected(), title=enData.inpfile)

# Run base hydarulic simulation and save data
enData.ENopenH()
G = en.sim.eps_hydraulic(enData, G)

# Compute todini index
todini = en.metrics.todini(G, 30)
plt.figure()
plt.title('Todini Index')
plt.plot(G.graph['time'], todini)

# Create MultiDiGraph for entropy
t = 0
attr = dict( ((u,v,k),d['flow'][t]) for u,v,k,d in G.edges(keys=True,data=True) if 'flow' in d)
G0 = en.network.epanet_to_MultiDiGraph(enData, edge_attribute=attr)
en.network.draw_graph(G0, edge_attribute='weight', 
                      title='Flow at time = ' + str(G.graph['time'][t]))
entropy = en.metrics.entropy(G0)

t = 100
attr = dict( ((u,v,k),d['flow'][t]) for u,v,k,d in G.edges(keys=True,data=True) if 'flow' in d)
G1 = en.network.epanet_to_MultiDiGraph(enData, edge_attribute=attr)
en.network.draw_graph(G1, edge_attribute='weight', 
                      title='Flow at time = ' + str(G.graph['time'][t]))
entropy = en.metrics.entropy(G1)

# Compute network cost and GHG emissions
flowunits = G.graph['flowunits']
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
