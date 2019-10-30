"""
The following example runs multiple realizations of pipe leak scenarios where 
each pipe is assigned a probability failure related to pipe diameter and leak
locations and durations are drawn from probability distributions. Water service
availability and tank water level is plotted for each realization.
"""
import numpy as np
import matplotlib.pyplot as plt
import pickle
import wntr

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Modify the water network model
wn.options.time.duration = 48*3600
wn.options.time.hydraulic_timestep = 1800
wn.options.time.report_timestep = 1800

# Set nominal pressures
for name, node in wn.junctions():
    node.nominal_pressure = 15

# Define failure probability for each pipe, based on pipe diameter. Failure
# probability must sum to 1.  Net3 has a few pipes with diameter = 99 inches,
# to exclude these from the set of feasible leak locations, use
# query_link_attribute
pipe_diameters = wn.query_link_attribute('diameter', np.less_equal,
                                         0.9144,  # 36 inches = 0.9144 m
                                         link_type=wntr.network.Pipe)
failure_probability = pipe_diameters/pipe_diameters.sum()

# Pickle the network model and reload it for each realization
f=open('wn.pickle','wb')
pickle.dump(wn,f)
f.close()

# Run 5 realizations
results = {} # Initialize dictionary to store results
np.random.seed(67823) # Set random seed
for i in range(5):

    # Select the number of leaks, random value between 1 and 5
    N = np.random.randint(1,5+1)

    # Select N unique pipes based on failure probability
    pipes_to_fail = np.random.choice(failure_probability.index, 5,
                                     replace=False,
                                     p=failure_probability.values)

    # Select time of failure, uniform dist, between 1 and 10 hours
    time_of_failure = np.round(np.random.uniform(1,10,1)[0], 2)

    # Select duration of failure, uniform dist, between 12 and 24 hours
    duration_of_failure = np.round(np.random.uniform(12,24,1)[0], 2)
    
    # Add leaks to the model
    for pipe_to_fail in pipes_to_fail:
        pipe = wn.get_link(pipe_to_fail)
        leak_diameter = pipe.diameter*0.3
        leak_area=3.14159*(leak_diameter/2)**2
        wn = wntr.morph.split_pipe(wn, pipe_to_fail, pipe_to_fail + '_B', pipe_to_fail+'leak_node')
        leak_node = wn.get_node(pipe_to_fail+'leak_node')
        leak_node.add_leak(wn, area=leak_area,
                          start_time=time_of_failure*3600,
                          end_time=(time_of_failure + duration_of_failure)*3600)

    # Simulate hydraulics and store results
    sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
    print('Pipe Breaks: ' + str(pipes_to_fail) + ', Start Time: ' + \
                str(time_of_failure) + ', End Time: ' + \
                str(time_of_failure+duration_of_failure))
    results[i] = sim.run_sim()
    
    # Reload the water network model
    f=open('wn.pickle','rb')
    wn = pickle.load(f)
    f.close()

# Plot water service availability and tank water level for each realization
for i in results.keys():
    
    # Water service availability at each junction and time
    expected_demand = wntr.metrics.expected_demand(wn)
    demand = results[i].node['demand'].loc[:,wn.junction_name_list]
    wsa_nt = wntr.metrics.water_service_availability(expected_demand, demand)
    
    # Average water service availability at each time
    wsa_t = wntr.metrics.water_service_availability(expected_demand.sum(axis=1), 
                                                  demand.sum(axis=1))
                               
    # Tank water level
    tank_level = results[i].node['pressure'].loc[:,wn.tank_name_list]
    
    # Plot results
    plt.figure()
    
    plt.subplot(2,1,1)
    wsa_nt.plot(ax=plt.gca(), legend=False)
    wsa_t.plot(ax=plt.gca(), label='Average', color='k', linewidth=3.0, legend=False)
    plt.ylim( (-0.05, 1.05) )
    plt.ylabel('Water service availability')
    
    plt.subplot(2,1,2)
    tank_level.plot(ax=plt.gca())
    plt.ylim(ymin=0, ymax=12)
    plt.legend()
    plt.ylabel('Tank water level (m)')