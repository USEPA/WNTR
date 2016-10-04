import wntr
import pandas as pd
import pickle
import matplotlib.pylab as plt

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Simulate using EPANET
epanet_sim = wntr.sim.EpanetSimulator(wn)
epanet_sim_results = epanet_sim.run_sim()

# Simulate using Scipy
wntr_sim = wntr.sim.WNTRSimulator(wn)
wntr_sim_results = wntr_sim.run_sim()

# Compare link flowrate results
plt.figure(figsize=(6,10))
plt.subplot(2,1,1)
plt.plot(epanet_sim_results.link['flowrate'])
plt.title('EPANET, Link Flowrate')
plt.subplot(2,1,2)
plt.plot(epanet_sim_results.link['flowrate'] - wntr_sim_results.link['flowrate'])
plt.title('EPANET - WNTR, Link Flowrate')

# Reset the water network and run again
wn = wntr.network.WaterNetworkModel(inp_file)
sim = wntr.sim.WNTRSimulator(wn)
res1 = sim.run_sim()
wn.reset_initial_values()
res2 = sim.run_sim()
# res2 has the exact same results as res1

# Stop and restart a simulation
wn = wntr.network.WaterNetworkModel(inp_file)
wn.options.duration = 10*3600
wn.options.hydraulic_timestep = 3600
sim = wntr.sim.WNTRSimulator(wn)
first_10_hours_of_results = sim.run_sim()
wn.options.duration = 24*3600
print 'running last 14 hours'
last_14_hours_of_results = sim.run_sim()
node_results = pd.concat([first_10_hours_of_results.node,last_14_hours_of_results.node],axis=1)
link_results = pd.concat([first_10_hours_of_results.link,last_14_hours_of_results.link],axis=1)
# node_results now has the exact same results as res1.node
# link_results now has the exact same results as res1.link

# Stop a simulation and save the water network model to a file
# Open the file and continue running
wn = wntr.network.WaterNetworkModel(inp_file)
wn.options.duration = 10*3600
wn.options.hydraulic_timestep = 3600
sim = wntr.sim.WNTRSimulator(wn)
first_10_hours_of_results = sim.run_sim()
f=open('pickle_example.pickle','w')
pickle.dump(wn,f)
f.close()
f=open('pickle_example.pickle','r')
new_wn = pickle.load(f)
f.close()
new_wn.options.duration = 24*3600
sim = wntr.sim.WNTRSimulator(new_wn)
print 'running last 14 hours'
last_14_hours_of_results = sim.run_sim()
node_results = pd.concat([first_10_hours_of_results.node,last_14_hours_of_results.node],axis=1)
link_results = pd.concat([first_10_hours_of_results.link,last_14_hours_of_results.link],axis=1)
# node_results now has the exact same results as res1.node
# link_results now has the exact same results as res1.link
