# Modify Network Stucture/Operations/Controls and simulate hydraulics
import wntr

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Modify the water network model
wn.options.duration = 24*3600
wn.options.hydraulic_timestep = 1800
wn.options.report_timestep = 1800
for junction_name, junction in wn.nodes(wntr.network.Junction):
    junction.minimum_pressure = 0.0
    junction.nominal_pressure = 15.0

# Define pipe leaks
wn.split_pipe_with_junction('123','123A','123B','leak1')
leak1 = wn.get_node('leak1')
leak1.add_leak(area=3.14159/4.0*0.05**2, start_time=5*3600, end_time=20*3600)
wn.split_pipe_with_junction('225','225A','225B','leak2')
leak2 = wn.get_node('leak2')
leak2.add_leak(area=3.14159/4.0*0.1**2, start_time=7*3600, end_time=15*3600)

# Create simulation object of the PYOMO simulator
sim = wntr.sim.PyomoSimulator(wn, pressure_dependent = True)

# Define power outage at all pumps
sim.all_pump_outage(5*3600, 13*3600)

# Simulate hydraulics
results = sim.run_sim()
