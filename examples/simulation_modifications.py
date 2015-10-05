# Modify Network Stucture/Operations/Controls and simulate hydraulics
import wntr
import os

# Create a water network model
my_path = os.path.abspath(os.path.dirname(__file__))
inp_file = os.path.join(my_path,'networks','Net3.inp')
wn = wntr.network.WaterNetworkModel(inp_file)

# Modify the water network model
wn.options.duration = 24*3600
wn.options.hydraulic_timestep = 1800
wn.options.report_timestep = 1800
for junction_name, junction in wn.nodes(wntr.network.Junction):
    junction.minimum_pressure = 0.0
    junction.nominal_pressure = 15.0

# Define pipe leaks
wn.add_leak(leak_name = 'leak1', pipe_name = '123', leak_diameter=0.05, 
                    start_time = 5*3600, fix_time = 20*3600)
wn.add_leak(leak_name = 'leak2', pipe_name = '225', leak_diameter=0.1, 
                   start_time = 7*3600, fix_time = 15*3600)

# Create simulation object of the PYOMO simulator
sim = wntr.sim.PyomoSimulator(wn, pressure_dependent = True)

# Define power outage at all pumps
sim.all_pump_outage(5*3600, 13*3600)

# Simulate hydraulics
results = sim.run_sim()
