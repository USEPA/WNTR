import epanetlib as en
import matplotlib.pyplot as plt

plt.close('all')

inp_file = 'networks/net_test_1.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Simulate using PYOMO
wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
pyomo_sim.add_leak(leak_name = 'leak1', pipe_name = 'pipe2', leak_diameter=0.25, start_time = '0 days 02:00:00', fix_time = '0 days 10:00:00')
leak_results = pyomo_sim.run_sim()

# Plot Pyomo results
node_list = [name for name,node in wn.nodes()]
node_list.append('leak1')
t_step = range(len(leak_results.node['demand'][node_list[0]]))
link_list = [name for name,link in wn.links()]
link_list.remove('pipe2')
link_list.add('pipe2__A')
link_list.add('pipe2__B')
tank_list = [name for name,node in wn.nodes(en.network.Tank)]

if len(tank_list)>0:
    plt.subplot(311)
    for tank_name in tank_list:
        plt.plot(t_step, leak_results.node['head'][tank_name],label=tank_name)
        plt.title('Tank levels')
        plt.ylabel('m')
    plt.legend(loc=0)

if len(tank_list)>0:
    plt.subplot(312)
else:
    plt.subplot(211)
for node_name in node_list:
    plt.plot(t_step, leak_results.node['head'][node_name],label=node_name)
    plt.title('Node head')
    plt.ylabel('m')
plt.legend(loc=0)

if len(tank_list)>0:
    plt.subplot(313)
else:
    plt.subplot(212)
for node_name in node_list:
    plt.plot(t_step, leak_results.node['demand'][node_name],label=node_name)
    plt.title('Node Demand')
    plt.ylabel('m3/s')
plt.legend(loc=0)

plt.savefig('leak_fig')
plt.close()
