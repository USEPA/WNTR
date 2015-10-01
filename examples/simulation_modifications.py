# Modify Network Stucture/Operations/Controls and simulate hydraulics
import wntr

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Modify the water network model
wn.time_options['DURATION'] = 24*3600
wn.time_options['HYDRAULIC TIMESTEP'] = 1800
wn.time_options['REPORT TIMESTEP'] = 1800
wn.set_nominal_pressures(constant_nominal_pressure = 15) 

# Define pipe leaks
wn.add_leak(leak_name = 'leak1', pipe_name = '123', leak_diameter=0.05, 
                    start_time = 5*3600, fix_time = 20*3600)
wn.add_leak(leak_name = 'leak2', pipe_name = '225', leak_diameter=0.1, 
                   start_time = 7*3600, fix_time = 15*3600)

# Create simulation object of the PYOMO simulator
sim = wntr.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')

# Define power outage at all pumps
sim.all_pump_outage(5*3600, 13*3600)

# Simulate hydraulics
results = sim.run_sim()
