import wntr
import pandas as pd
import pickle

inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
wn.options.duration = 24*3600
wn.options.hydraulic_timestep = 3600
sim = wntr.sim.ScipySimulator(wn)
res1 = sim.run_sim()

# An example of wn.reset_initial_values()
wn.reset_initial_values()
res2 = sim.run_sim()
# res2 now has the exact same results as res1

# An example of stopping and restarting a simulation
wn = wntr.network.WaterNetworkModel(inp_file)
wn.options.duration = 10*3600
wn.options.hydraulic_timestep = 3600
sim = wntr.sim.ScipySimulator(wn)
first_10_hours_of_results = sim.run_sim()
wn.options.duration = 24*3600
print 'running last 14 hours'
last_14_hours_of_results = sim.run_sim()
node_results = pd.concat([first_10_hours_of_results.node,last_14_hours_of_results.node],axis=1)
link_results = pd.concat([first_10_hours_of_results.link,last_14_hours_of_results.link],axis=1)
# node_results now has the exact same results as res1.node
# link_results now has the exact same results as res1.link

# An example using pickle
wn = wntr.network.WaterNetworkModel(inp_file)
wn.options.duration = 10*3600
wn.options.hydraulic_timestep = 3600
sim = wntr.sim.ScipySimulator(wn)
first_10_hours_of_results = sim.run_sim()
f=open('pickle_example.pickle','w')
pickle.dump(wn,f)
f.close()
f=open('pickle_example.pickle','r')
new_wn = pickle.load(f)
f.close()
new_wn.options.duration = 24*3600
sim = wntr.sim.ScipySimulator(new_wn)
print 'running last 14 hours'
last_14_hours_of_results = sim.run_sim()
node_results = pd.concat([first_10_hours_of_results.node,last_14_hours_of_results.node],axis=1)
link_results = pd.concat([first_10_hours_of_results.link,last_14_hours_of_results.link],axis=1)
# node_results now has the exact same results as res1.node
# link_results now has the exact same results as res1.link
