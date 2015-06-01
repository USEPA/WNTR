import epanetlib as en
import pandas as pd

# Create Network
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, 'networks/net_test_3.inp')

# Modify Network/Controls
wn.time_options['DURATION'] = 3600*10 # set the simulation duration to 10 hours
wn.add_conditional_controls('pump1','junction1',5.0,'CLOSED','BELOW') # close pump1 if junction1 pressure drops below 5 meters
wn.set_nominal_pressures(constant_nominal_pressure = 30.0) # Set nominal pressure to 30 meters for all nodes

# Run Simulation
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
s1_results = pyomo_sim.run_sim()

# Modify Network/Controls
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
pyomo_sim.add_pump_outage('pump1','0 days 02:00:00','0 days 25:00:00') # add a pump outage at pump1

# Run another simulation
s2_results = pyomo_sim.run_sim()

# Output
fdv1 = en.metrics.fraction_delivered.fraction_delivered_volume(s1_results, 15.0)
fdv2 = en.metrics.fraction_delivered.fraction_delivered_volume(s2_results, 15.0)

print fdv1
print fdv2

