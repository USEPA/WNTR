
# coding: utf-8

## WNTR Demo: Earthquake Scenario

##### Import python packages, including WNTR

# In[ ]:

get_ipython().magic(u'matplotlib inline')

import numpy as np
import pandas as pd
import pickle
import matplotlib.pylab as plt
import wntr

np.random.seed(12345)


##### Create a water network model using an EPANET inp file

# In[ ]:

inp_file = '../networks/Net6_mod.inp'
wn = wntr.network.WaterNetworkModel(inp_file)


##### Define earthquake epicenter, magnitude, and depth

# In[ ]:

epicenter = (210,110) # x,y location
magnitude = 5 # Richter scale
depth = 10000 # m, shallow depth


##### Plot location of epicenter on the network

# In[ ]:

wntr.network.draw_graph(wn, node_size=0, figsize=(10,8), dpi=100)
plt.hold('True')
plt.scatter(epicenter[0], epicenter[1], s=1000, c='r', marker='*', zorder=2)


##### Generate the earthquake scenario

# In[ ]:

#This scenario assumes uniform pipe and soil type throughout the network.  These parameters can be set for individual pipes
#PGA = 0.001 g (0.01 m/s2) – perceptible by people
#PGA = 0.02  g (0.2  m/s2) – people lose their balance
#PGA = 0.50  g (5 m/s2) – very high; well-designed buildings can survive if the duration is short
#Repair rate of 1/km (0.001/m) has been suggested as an upper bound

earthquake = wntr.scenario.Earthquake(epicenter, magnitude, depth)
earthquake.generate(wn, coordinate_scale=500, correct_length=False)

print "Min, Max, Average PGA: " + str(np.round(np.min(earthquake.pga.values()),2)) + ", " + str(np.round(np.max(earthquake.pga.values()),2)) + ", " + str(np.round(np.mean(earthquake.pga.values()),2)) + " m/s2"
print "Min, Max, Average repair rate: " + str(np.round(np.min(earthquake.repair_rate.values()),5)) + ", " + str(np.round(np.max(earthquake.repair_rate.values()),5)) + ", " + str(np.round(np.mean(earthquake.repair_rate.values()),5)) + " per m"
print "Number of pipe failures: " + str(len(earthquake.pipes_to_leak))


##### Plot peak ground acceleration

# In[ ]:

wntr.network.draw_graph(wn, link_attribute=earthquake.pga, node_size=0, link_width=1.5, link_range=[0, np.max(earthquake.pga.values())], title='Peak ground acceleration', figsize=(12,8), dpi=100)


##### Plot repair rate (# of repairs needed per m)

# In[ ]:

wntr.network.draw_graph(wn, link_attribute=earthquake.repair_rate, node_size=0, link_width=1.5, link_range=[0,np.max(earthquake.repair_rate.values())], title='Repair rate', figsize=(12,8), dpi=100)


##### Plot location of pipes with leaks

# In[ ]:

wntr.network.draw_graph(wn, link_attribute=earthquake.probability_of_leak, node_size=0, link_width=1.5, title='Probability of pipe failure', figsize=(12,8), dpi=100)

gray_red_colormap = wntr.network.custom_colormap(2, colors = ['0.75','red'])
wntr.network.draw_graph(wn, link_attribute=earthquake.pipe_status, node_size=0, link_width=1.5, link_cmap=gray_red_colormap, link_range=[0,1], title='Failed pipes (in red)', add_colorbar=False, figsize=(10,8), dpi=100)


##### Add leaks to the model and simulate hydraulics

# In[ ]:

# The simulation uses pressure driven hydraulics and leak models to account for loss.
wn.set_nominal_pressures(constant_nominal_pressure = 15) 
wn.time_options['DURATION'] = 24*3600
wn.time_options['HYDRAULIC TIMESTEP'] = 1200
wn.time_options['REPORT TIMESTEP'] = 1200
sim = wntr.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')

time_of_failure = 5 # time of failure
duration_of_failure = 20 # Select duration of failure     
for pipe_name in earthquake.pipes_to_leak:
    # Select leak diameter, uniform dist, between 0.01 and pipe diameter 
    pipe_diameter = wn.get_link(pipe_name).diameter
    leak_diameter = np.round(np.random.uniform(0.01,0.25*pipe_diameter,1), 2) 
    # Add pipe leak to the simulator
    sim.add_leak(leak_name = "Leak"+pipe_name, pipe_name = pipe_name, leak_diameter = leak_diameter[0], 
                 start_time = pd.Timedelta(time_of_failure, unit='h'), fix_time = pd.Timedelta(time_of_failure + duration_of_failure, unit='h'))
        
results = sim.run_sim(demo='demo_Net6.pickle')
#pickle.dump(results, open('demo_Net6.pickle', 'wb'))
#results = pickle.load(open('demo_Net6.pickle', 'rb'))


##### Plot results

# In[ ]:

wn_nodes = [node_name for node_name, node in wn.nodes(wntr.network.Junction)]
pressure_at_24hr = results.node.loc[(wn_nodes, pd.Timedelta(hours = 24)), 'pressure']
wntr.network.draw_graph(wn, node_attribute=pressure_at_24hr, node_size=20, node_range = [0,np.max(pressure_at_24hr)], title='Pressure at 24 hours', figsize=(12,8), dpi=100)

# Node pressure
plt.figure(figsize=(12,5), dpi=100)
for name, node in wn.nodes(wntr.network.Junction):
    pressure = results.node['pressure'][name]
    pressure.index = pressure.index.format() 
    pressure.plot()
    plt.hold(True)
plt.ylim(ymin=0)
plt.ylabel('Node Pressure (m)')

# Tank pressure
plt.figure(figsize=(12,5), dpi=100)
for name, tank in wn.nodes(wntr.network.Tank):
    pressure = results.node['pressure'][name]
    pressure.index = pressure.index.format() 
    pressure.plot(label=name)
    plt.hold(True)
plt.ylim(ymin=0, ymax=12)
plt.ylabel('Tank Pressure (m)')
#plt.legend()

# Fraction delivered volume
nzd_junctions = wn.query_node_attribute('base_demand', np.greater, 0, node_type=wntr.network.Junction).keys()  
FDV_kt = results.node.loc[nzd_junctions, 'demand'].sum(level=1)/results.node.loc[nzd_junctions, 'expected_demand'].sum(level=1) # FDV, scenario k, time t
FDV_knt = results.node.loc[nzd_junctions, 'demand']/results.node.loc[nzd_junctions, 'expected_demand'] # FDV, scenario k, node n, time t 
plt.figure(figsize=(12,5), dpi=100)
FDV_kt.index = FDV_kt.index.format() 
FDV_kt.plot(label='Average', color='k', linewidth=3.0, legend=False)
plt.hold(True)
FDV_knt = FDV_knt.unstack().T 
FDV_knt.index = FDV_knt.index.format() 
FDV_knt.plot(ax=plt.gca(), legend=False)
plt.ylim(ymin=-0.05, ymax=1.05)
plt.ylabel('FDV')


# In[ ]:



