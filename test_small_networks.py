import epanetlib as en
import matplotlib.pylab as plt

# This is a git test line

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
wn.set_nominal_pressures(constant_nominal_pressure = 15.0, units = 'm')
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
pyomo_results = pyomo_sim.run_sim()

# Plot Pyomo results
node_list = [name for name,node in wn.nodes()]
t_step = range(len(pyomo_results.node['demand'][node_list[0]]))
link_list = [name for name,link in wn.links()]
tank_list = [name for name,node in wn.nodes(en.network.Tank)]

if len(tank_list)>0:
    plt.subplot(311)
    for tank_name in tank_list:
        plt.plot(t_step, pyomo_results.node['head'][tank_name],label=tank_name)
        plt.title('Tank levels')
        plt.ylabel('m')
    plt.legend(loc=0)

if len(tank_list)>0:
    plt.subplot(312)
else:
    plt.subplot(211)
for node_name in node_list:
    plt.plot(t_step, pyomo_results.node['head'][node_name],label=node_name)
    plt.title('Node head')
    plt.ylabel('m')
    plt.ylim(-10,100)
plt.legend(loc=0)

if len(tank_list)>0:
    plt.subplot(313)
else:
    plt.subplot(212)
for node_name in node_list:
    plt.plot(t_step, pyomo_results.node['demand'][node_name],label=node_name)
    plt.title('Node Demand')
    plt.ylabel('m3/s')
plt.legend(loc=0)

plt.savefig('pyomo_tmp_fig')
plt.close()

# Plot epanet results
if len(tank_list)>0:
    plt.subplot(311)
    for tank_name in tank_list:
        plt.plot(t_step, epanet_results.node['head'][tank_name],label=tank_name)
        plt.title('Tank levels')
        plt.ylabel('m')
    plt.legend(loc=0)

if len(tank_list)>0:
    plt.subplot(312)
else:
    plt.subplot(211)
for node_name in node_list:
    plt.plot(t_step, epanet_results.node['head'][node_name],label=node_name)
    plt.title('Node head')
    plt.ylabel('m')
    plt.ylim(-10,100)
plt.legend(loc=0)

if len(tank_list)>0:
    plt.subplot(313)
else:
    plt.subplot(212)
for node_name in node_list:
    plt.plot(t_step, epanet_results.node['demand'][node_name],label=node_name)
    plt.title('Node Demand')
    plt.ylabel('m3/s')
plt.legend(loc=0)

plt.savefig('epanet_tmp_fig')
plt.close()

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
