import epanetlib as en
import pandas as pd
import resilience_metrics as metrics

# Create an instance of WaterNetworkModel
wn = en.network.WaterNetworkModel()

# Create an instance of ParseWaterNetwork
parser = en.network.ParseWaterNetwork()

# Populate the WaterNetworkModel with an inp file
parser.read_inp_file(wn, 'networks/net_test_3.inp')

# Modify options, controls, etc.
# Add pump outages, leaks, etc.
wn.time_options['DURATION'] = 3600*30 # set the simulation duration to 30 hours
wn.conditional_controls['pump1']['closed_below']=[('junction1',5)] # close pump1 if junction1 pressure drops below 5 meters
wn.set_nominal_pressures(constant_nominal_pressure = 30.0)

# Create a PyomoSimulator object
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')

# Run a simulation
s1_results = pyomo_sim.run_sim()

# Add a pump outage
pyomo_sim.add_pump_outage('pump1','0 days 02:00:00','0 days 25:00:00')

# Run another simulation
s2_results = pyomo_sim.run_sim()

# Add a leak and run another simulation
pyomo_sim.add_leak('leak1','pipe1', leak_diameter=0.1, start='0 days 02:00:00', end='0 days 10:00:00')
s3_results = pyomo_sim.run_sim()

# Apply desired metrics and save figures
FDV(results = [s1_results,s2_results,s3_results], average_over = ['scenario','node'], format='plot')
