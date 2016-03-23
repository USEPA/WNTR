import wntr
import numpy as np
import matplotlib.pyplot as plt
import pickle

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

### SIMULATION ###
# Modify the water network model
wn.options.duration = 48*3600
wn.options.hydraulic_timestep = 1800
wn.options.report_timestep = 1800

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
failure_probability = {}
for k,v in pipe_diameters.iteritems():
    failure_probability[k] = v/sum(pipe_diameters.values())
    
# Define maximum iterations
Imax = 5

# Initialize dictonary to store results
results = {}

# Set random seed
np.random.seed(67823)

f=open('wn.pickle','w')
pickle.dump(wn,f)
f.close()

for i in range(Imax):
    
    # Select the number of leaks, random value between 1 and 5
    N = np.random.random_integers(1,5,1)
    
    # Select N unique pipes based on failure probability
    pipes_to_fail = np.random.choice(failure_probability.keys(), 5, 
                                     replace=False, 
                                     p=failure_probability.values())
    
    # Select time of failure, uniform dist, between 1 and 10 hours
    time_of_failure = np.round(np.random.uniform(1,10,1)[0], 2) 
    
    # Select duration of failure, uniform dist, between 12 and 24 hours
    duration_of_failure = np.round(np.random.uniform(12,24,1)[0], 2) 
    
    for pipe_to_fail in pipes_to_fail:
        pipe = wn.get_link(pipe_to_fail)
        leak_diameter = pipe.diameter*0.3
        leak_area=3.14159*(leak_diameter/2)**2
        wn.split_pipe_with_junction(pipe_to_fail, pipe_to_fail + '_A', pipe_to_fail + '_B',
                      pipe_to_fail+'leak_node')
        leak_node = wn.get_node(pipe_to_fail+'leak_node')           
        leak_node.add_leak(wn, area=leak_area, 
                          start_time=time_of_failure*3600, 
                          end_time=(time_of_failure + duration_of_failure)*3600)
    
    # Create simulation object of the PYOMO simulator
    sim = wntr.sim.WNTRSimulator(wn, pressure_driven=True)
    
    # Simulate hydraulics
    sim_name = 'Pipe Breaks: ' + str(pipes_to_fail) + ', Start Time: ' + \
                str(time_of_failure) + ', End Time: ' + \
                str(time_of_failure+duration_of_failure)
                
    print sim_name
    results[sim_name] = sim.run_sim()
    
    f=open('wn.pickle','r')
    wn = pickle.load(f)
    f.close()
    
### ANALYSIS ###
nzd_junctions = wn.query_node_attribute('base_demand', np.greater, 0, 
                                        node_type=wntr.network.Junction).keys()

result_names = results.keys()
for name in result_names:
    
    # Print power outage description for each iteration
    print name
    
    results[name].node.major_axis = results[name].node.major_axis/3600.0
    
    # Isolate node results at consumer nodes
    node_results = results[name].node.loc[:,:,nzd_junctions]
    
    # FDV, scenario k, time t
    FDV_kt = wntr.metrics.fdv(node_results, average_nodes=True)
    
    # FDV, scenario k, node n, time t
    FDV_knt = wntr.metrics.fdv(node_results)

    # Plot
    plt.figure()
    plt.subplot(2,1,1)
    plt.title(str(name))
    
    for node_name in nzd_junctions:
        pressure = FDV_knt.loc[:,node_name] 
        pressure.plot()
        plt.hold(True)
    
    FDV_knt.plot(ax=plt.gca(), legend=False)
    plt.hold(True)
    FDV_kt.plot(ax=plt.gca(), label='Average', color='k', linewidth=3.0, legend=False)
    plt.ylim( (-0.05, 1.05) )
    plt.ylabel('FDV')
    
    # Pressure in the tanks
    plt.subplot(2,1,2)
    
    for tank_name, tank in wn.tanks():
        tank_pressure = results[name].node['pressure'][tank_name]
        tank_pressure.plot(ax=plt.gca(),label=tank_name)
        plt.hold(True)
    
    plt.ylim(ymin=0, ymax=12)
    plt.legend()
    plt.ylabel('Tank Pressure (m)')
