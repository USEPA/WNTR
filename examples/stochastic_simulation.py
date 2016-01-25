import wntr
import numpy as np
import matplotlib.pyplot as plt

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

### SIMULATION ###
# Modify the water network model
wn.options.duration = 24*3600
wn.options.hydraulic_timestep = 1800
wn.options.report_timestep = 1800

# Set nominal pressures
for name, node in wn.junctions():
    node.nominal_pressure = 15

# Define set of pumps
pump_names = [pump_name for pump_name, pump in wn.pumps()]

# Define maximum iterations
Imax = 5

# Initialize dictonary to store results
results = {}

# Set random seed
np.random.seed(67823)

for i in range(Imax):
    
    # Select a pump to fail, random selection
    pump_to_fail = np.random.choice(pump_names)
    pump = wn.get_link(pump_to_fail)
    
    # Select time of failure, normal dist, mean = 4 hours, stdev = 1 hour
    time_of_failure = np.round(np.random.normal(4,1,1), 2) 
    
    # Select duration of failure, normal dist, mean = 15 hours, stdev = 5 hours
    duration_of_failure = np.round(np.random.normal(15,5,1), 2) 
    
    # Add power outage
    wn.add_pump_outage(pump_to_fail, time_of_failure[0]*3600, 
                       (time_of_failure[0] + duration_of_failure[0])*3600)
            
    # Create simulation object of the PYOMO simulator
    sim = wntr.sim.ScipySimulator(wn, pressure_driven=True)
    
    # Simulate hydraulics
    sim_name = pump_to_fail + '_' + \
                str(time_of_failure[0]) + '_' + \
                str(duration_of_failure[0])
                
    print sim_name
    results[sim_name] = sim.run_sim()
    
    wn.reset_initial_values()
    
    
### ANALYSIS ###
nzd_junctions = wn.query_node_attribute('base_demand', np.greater, 0, 
                                        node_type=wntr.network.Junction).keys()

result_names = results.keys()
for name in result_names:
    
    # Print power outage description for each iteration
    print 'Power outage iteration'
    print name
    
    # Isolate node results at consumer nodes
    node_results = results[name].node.loc[:,:,nzd_junctions]
    
    # FDV, scenario k, time t
    FDV_kt = wntr.metrics.fdv(node_results, average_nodes=True)
    
    # FDV, scenario k, node n, time t
    FDV_knt = wntr.metrics.fdv(node_results)

    # Plot
    plt.figure()
    plt.subplot(2,1,1)
    plt.title('Power outage\n' + str(name))
    
    for node_name in nzd_junctions:
        pressure = FDV_knt.loc[:,node_name] 
        pressure.plot()
        plt.hold(True)
    
    FDV_knt = FDV_knt.unstack().T 
    FDV_knt.plot(ax=plt.gca(), legend=False)
    plt.hold(True)
    FDV_kt.plot(ax=plt.gca(), label='Average', color='k', linewidth=3.0, legend=False)
    plt.ylim( (-0.05, 1.05) )
    plt.ylabel('FDV')
    
    # Pressure in the tanks
    plt.subplot(2,1,2)
    
    for tank_name, tank in wn.tanks():
        tank_pressure = results[name].node['pressure'][tank_name]
        tank_pressure.index = tank_pressure.index.format() 
        tank_pressure.plot(ax=plt.gca(),label=tank_name)
        plt.hold(True)
    
    plt.ylim(ymin=0, ymax=12)
    plt.legend()
    plt.ylabel('Tank Pressure (m)')
