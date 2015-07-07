# Simulate a pipe leak
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
"""
node_list = [name for name,node in wn.nodes()]
t_step = range(len(results.node['demand'][node_list[0]]))
link_list = [name for name,link in wn.links()]
tank_list = [name for name,node in wn.nodes(en.network.Tank)]

if len(tank_list)>0:
    fig = plt.figure(figsize=(11,6))
    ax = fig.add_subplot(111)
    for tank_name in tank_list:
        ax.plot(t_step, results.node['pressure'][tank_name],label=tank_name)
    ax.set_title('Tank levels')
    ax.set_xlabel('Timestep')
    ax.set_ylabel('m')
    ax.legend(loc=0, prop={'size':9})
    plt.gcf().subplots_adjust(bottom=0.2)
    plt.gcf().subplots_adjust(left=0.15)

fig = plt.figure(figsize=(11,6))
ax = fig.add_subplot(111)
for node_name in node_list:
    ax.plot(t_step, results.node['pressure'][node_name],label=node_name)
ax.set_title('Node Pressure')
ax.set_xlabel('Timestep')
ax.set_ylabel('m')
ax.legend(loc=0, prop={'size':9})
plt.gcf().subplots_adjust(bottom=0.2)
plt.gcf().subplots_adjust(left=0.15)

fig = plt.figure(figsize=(11,6))
ax = fig.add_subplot(111)
for node_name in node_list:
    ax.plot(t_step, results.node['demand'][node_name],label=node_name)
ax.set_title('Node Demand')
ax.set_xlabel('Timestep')
ax.set_ylabel('m3/s')
ax.legend(loc=0, prop={'size':9})
plt.gcf().subplots_adjust(bottom=0.2)
plt.gcf().subplots_adjust(left=0.15)

fig = plt.figure(figsize=(11,6))
ax = fig.add_subplot(111)
for link_name in link_list:
    ax.plot(t_step, results.link['flowrate'][link_name],label=link_name)
ax.set_title('Link Flowrate')
ax.set_xlabel('Timestep')
ax.set_ylabel('m3/s')
ax.legend(loc=0, prop={'size':9})
plt.gcf().subplots_adjust(bottom=0.2)
plt.gcf().subplots_adjust(left=0.15)
"""