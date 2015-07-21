import epanetlib as en
import matplotlib.pyplot as plt

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Modify the water network model
wn.time_options['DURATION'] = 24*3600
wn.set_nominal_pressures(constant_nominal_pressure = 15) 

# Create simulation object of the PYOMO simulator
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')

# Define pipe leaks
pyomo_sim.add_leak(leak_name = 'leak1', pipe_name = '123', leak_diameter=0.05, 
                   start_time = '0 days 05:00:00', fix_time = '0 days 20:00:00')
pyomo_sim.add_leak(leak_name = 'leak2', pipe_name = '225', leak_diameter=0.1, 
                   start_time = '0 days 07:00:00', fix_time = '0 days 15:00:00')

# Simulate hydraulics
results = pyomo_sim.run_sim()

# Plot results
plt.figure()
results.node.loc['leak1', 'demand'].plot()
results.link.loc['123__A', 'flowrate'].plot()
results.link.loc['123__B', 'flowrate'].plot()

plt.figure()
results.node.loc['leak2', 'demand'].plot()
results.link.loc['225__A', 'flowrate'].plot()
results.link.loc['225__B', 'flowrate'].plot()
