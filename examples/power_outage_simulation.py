# Simulate a power outage and restoration
import epanetlib as en
import matplotlib.pylab as plt
import numpy as np

plt.close('all')

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Modify the water network model
wn.time_options['DURATION'] = 24*3600
wn.set_nominal_pressures(constant_nominal_pressure = 15) 

# Create simulation object of the PYOMO simulator
sim = en.sim.PyomoSimulator(wn, 'PRESSURE DRIVEN')

# Define power outage at all pumps
start_time = '0 days 02:00:00' 
end_time = '0 days 18:00:00' 
sim.all_pump_outage(start_time, end_time)

# Simulate hydraulics
results = sim.run_sim()

# Compute fraction delivered volume and plot results on the network
fdv = en.metrics.fraction_delivered.fraction_delivered_volume(results, np.NaN)
en.network.draw_graph(wn, node_attribute=fdv, node_size=30, 
                      title='Fraction Delivered Volume')
