import wntr
import matplotlib.pyplot as plt

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Define WQ scenarios
WQscenario = wntr.scenario.Waterquality('CHEM', '121', 'SETPOINT', 1000, 2*3600, 15*3600)

# Simulate hydraulics and water quality for each scenario
sim = wntr.sim.EpanetSimulator(wn)
results_CHEM = sim.run_sim(WQscenario)

MC = wntr.metrics.mass_contaminant_consumed(results_CHEM.node)
VC = wntr.metrics.volume_contaminant_consumed(results_CHEM.node, 0.001)
EC = wntr.metrics.extent_contaminant(results_CHEM.node, results_CHEM.link, wn, 0.001)

wntr.network.draw_graph(wn, node_attribute=MC.sum(axis=0), node_range = [0,400], node_size=40,
                      title='Total mass consumed')
    
plt.figure()           
EC.sum(axis=1).plot(title='Extent of contamination')
