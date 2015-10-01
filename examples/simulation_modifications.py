# Modify Network Stucture/Operations/Controls and simulate hydraulics
import wntr

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Modify the water network model
wn.options.duration = 24*3600
wn.options.hydraulic_timestep = 1800
wn.options.report_timestep = 1800
wn.set_nominal_pressures(constant_nominal_pressure = 15) 

# Define pipe leaks
wn.add_leak(leak_name = 'leak1', pipe_name = '123', leak_diameter=0.05, 
                    start_time = '0 days 05:00:00', fix_time = '0 days 20:00:00')
wn.add_leak(leak_name = 'leak2', pipe_name = '225', leak_diameter=0.1, 
                   start_time = '0 days 07:00:00', fix_time = '0 days 15:00:00')

# Create simulation object of the PYOMO simulator
sim = wntr.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')

# Define power outage at all pumps
start_time = '0 days 05:00:00' 
end_time = '0 days 13:00:00' 
sim.all_pump_outage(start_time, end_time)

# Simulate hydraulics
results = sim.run_sim()
