import epanetlib as en
import matplotlib.pylab as plt

plt.close('all')

inp_file = 'networks/net_test_1.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Graph the network
#en.network.draw_graph(wn, title= wn.name)

# Simulate using PYOMO
wn.set_nominal_pressures(constant_nominal_pressure = 20.0, units = 'm')
wn.add_leak('leak1','2',leak_diameter=0.3)
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
leak_results = pyomo_sim.run_sim()

# Plot Pyomo results
node_list = [name for name,node in wn.nodes()]
t_step = range(len(leak_results.node['demand'][node_list[0]]))
link_list = [name for name,link in wn.links()]
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
