import epanetlib as en
import matplotlib.pyplot as plt



# Create Network
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, 'networks/net_test_3.inp')



# Modify Network/Controls
# Most modifications to the network/controls are done through the WaterNetworkModel object as below.
wn.time_options['DURATION'] = 3600*10 # set the simulation duration to 10 hours
wn.add_conditional_controls('pump1','junction1',5.0,'CLOSED','BELOW') # close pump1 if junction1 pressure drops below 5 meters
wn.set_nominal_pressures(constant_nominal_pressure = 30.0) # Set nominal pressure to 30 meters for all nodes



# Run Simulation and save results
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
s1_results = pyomo_sim.run_sim()



# Modify Network/Controls
# Pump outages are applied through the PyomoSimulator object rather than the WaterNetworkModel object.
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN') # Currently, the PyomoSimulator object needs to be recreated for each simulation
pyomo_sim.add_pump_outage('pump1','0 days 02:00:00','0 days 25:00:00') # add a pump outage at pump1



# Run another simulation and save results
s2_results = pyomo_sim.run_sim()



# Output
fdv1 = en.metrics.fraction_delivered.fraction_delivered_volume(s1_results, 15.0)
fdv2 = en.metrics.fraction_delivered.fraction_delivered_volume(s2_results, 15.0)

print 'fraction delivered volume without pump outage: ',fdv1
print 'fraction delivered volume with pump outage:    ',fdv2



# Plot actual demand delivered and junction2 head for both scenarios 
t_step = range(len(s1_results.node['demand']['junction2']))

plt.plot(t_step, s1_results.node['demand']['junction2'],label='Regular Operation')
plt.plot(t_step, s2_results.node['demand']['junction2'],label='Pump Outage')
plt.ylabel('Junction2 Demand (m3/s)')
plt.xlabel('Time Step')
plt.legend(loc=0)

plt.savefig('user_example_fig')
plt.close()
