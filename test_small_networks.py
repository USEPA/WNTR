import epanetlib as en
import matplotlib.pylab as plt

plt.close('all')

inp_file = 'networks/net_test_3.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Graph the network
#en.network.draw_graph(wn, title= wn.name)

# Simulate using EPANET
epanet_sim = en.sim.EpanetSimulator(wn)
epanet_results = epanet_sim.run_sim()

# Simulate using PYOMO
wn.set_nominal_pressures(constant_nominal_pressure = 20.0)
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
pyomo_results = pyomo_sim.run_sim()

# Compare results
node_list = [name for name,node in wn.nodes()]
t_step = range(len(pyomo_results.node['demand'][node_list[0]]))
link_list = [name for name,link in wn.links()]
tank_list = [name for name,node in wn.nodes(en.network.Tank)]

plt.subplot(311)
for tank_name in tank_list:
    plt.plot(t_step, pyomo_results.node['head'][tank_name],label=tank_name)
    plt.title('Tank levels')
    plt.ylabel('m')
plt.legend()

plt.subplot(312)
for node_name in node_list:
    plt.plot(t_step, pyomo_results.node['head'][node_name],label=node_name)
    plt.title('Node head')
    plt.ylabel('m')
plt.legend()

plt.subplot(313)
for node_name in node_list:
    plt.plot(t_step, pyomo_results.node['demand'][node_name],label=node_name)
    plt.title('Node Demand')
    plt.ylabel('m3/s')
plt.legend()

#plt.figure()
#epanet_results.node['demand'].plot(label='EPANET')
#pyomo_results.node['demand'].plot(label='PYOMO')
#plt.title('Node Demand')
#plt.legend()
#
#plt.figure()
#epanet_results.node['head'].plot(label='EPANET')
#pyomo_results.node['head'].plot(label='PYOMO')
#plt.title('Node Head')
#plt.legend()
#
#plt.figure()
#epanet_results.node['pressure'].plot(label='EPANET')
#pyomo_results.node['pressure'].plot(label='PYOMO')
#plt.title('Node Pressure')
#plt.legend()
#
#plt.figure()
#epanet_results.link['flowrate'].plot(label='EPANET')
#pyomo_results.link['flowrate'].plot(label='PYOMO')
#plt.title('Link Flowrate')
#plt.legend()
#
#plt.figure()
#epanet_results.link['velocity'].plot(label='EPANET')
#pyomo_results.link['velocity'].plot(label='PYOMO')
#plt.title('Link Velocity')
#plt.legend()


plt.show()
