import wntr
import matplotlib.pyplot as plt

# Create a water network model and setup simulation
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
sim = wntr.sim.EpanetSimulator(wn)

# Run chemical concentration scenario and plot results
WQscenario = wntr.scenario.Waterquality('CHEM', ['121', '123'], 'SETPOINT', 1000, 2*3600, 15*3600)
results = sim.run_sim(WQscenario)
CHEM_at_5hr = results.node.loc['quality', 5*3600, :]
wntr.network.draw_graph(wn, node_attribute=CHEM_at_5hr, node_size=20, 
                      title='Chemical concentration, time = 5 hours')
CHEM_at_node = results.node.loc['quality', :, '208']
plt.figure()
CHEM_at_node.plot(title='Chemical concentration, node 208')

# Run age scenario and plot results
WQscenario = wntr.scenario.Waterquality('AGE')
results = sim.run_sim(WQscenario)
AGE_at_5hr = results.node.loc['quality', 5*3600, :]/3600.0 # convert to hours
wntr.network.draw_graph(wn, node_attribute=AGE_at_5hr, node_size=20, 
                      title='Water age (hrs), time = 5 hours')
AGE_at_node = results.node.loc['quality', :, '208']/3600.0
plt.figure()
AGE_at_node.plot(title='Water age, node 208')

# Run trace scenario and plot results
WQscenario = wntr.scenario.Waterquality('TRACE', ['111'])
results = sim.run_sim(WQscenario)
TRACE_at_5hr = results.node.loc['quality', 5*3600, :]
wntr.network.draw_graph(wn, node_attribute=TRACE_at_5hr, node_size=20, 
                      title='Trace percent, time = 5 hours')
TRACE_at_node = results.node.loc['quality', :, '208']
plt.figure()
TRACE_at_node.plot(title='Trace percent, node 208')