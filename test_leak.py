import epanetlib as en
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

inp_file = 'networks/Net1.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Simulate using PYOMO
wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
pyomo_sim.add_leak(leak_name = 'leak1', pipe_name = '12', leak_diameter=0.05, start_time = '0 days 05:00:00', fix_time = '0 days 20:00:00')
pyomo_sim.add_leak(leak_name = 'leak2', pipe_name = '10', leak_diameter=0.05, start_time = '0 days 05:00:00', fix_time = '0 days 15:00:00')
pyomo_sim.add_leak(leak_name = 'leak3', pipe_name = '110', leak_diameter=0.05, start_time = '0 days 05:00:00', fix_time = '0 days 15:00:00')
leak_results = pyomo_sim.run_sim()

# Plot Pyomo results
node_list = [name for name,node in wn.nodes()]
t_step = range(len(leak_results.node['demand'][node_list[0]]))
link_list = [name for name,link in wn.links()]
tank_list = [name for name,node in wn.nodes(en.network.Tank)]

pdf = PdfPages('leak_fig.pdf')

if len(tank_list)>0:
    fig = plt.figure(figsize=(11,6))
    ax = fig.add_subplot(111)
    for tank_name in tank_list:
        ax.plot(t_step, leak_results.node['pressure'][tank_name],label=tank_name)
    ax.set_title('Tank levels')
    ax.set_xlabel('Timestep')
    ax.set_ylabel('m')
    ax.legend(loc=0, prop={'size':9})
    plt.gcf().subplots_adjust(bottom=0.2)
    plt.gcf().subplots_adjust(left=0.15)
    pdf.savefig()
    plt.close()

fig = plt.figure(figsize=(11,6))
ax = fig.add_subplot(111)
for node_name in node_list:
    ax.plot(t_step, leak_results.node['pressure'][node_name],label=node_name)
ax.set_title('Node Pressure')
ax.set_xlabel('Timestep')
ax.set_ylabel('m')
ax.legend(loc=0, prop={'size':9})
plt.gcf().subplots_adjust(bottom=0.2)
plt.gcf().subplots_adjust(left=0.15)
pdf.savefig()
plt.close()

fig = plt.figure(figsize=(11,6))
ax = fig.add_subplot(111)
for node_name in node_list:
    ax.plot(t_step, leak_results.node['demand'][node_name],label=node_name)
ax.set_title('Node Demand')
ax.set_xlabel('Timestep')
ax.set_ylabel('m3/s')
ax.legend(loc=0, prop={'size':9})
plt.gcf().subplots_adjust(bottom=0.2)
plt.gcf().subplots_adjust(left=0.15)
pdf.savefig()
plt.close()

fig = plt.figure(figsize=(11,6))
ax = fig.add_subplot(111)
for link_name in link_list:
    ax.plot(t_step, leak_results.link['flowrate'][link_name],label=link_name)
ax.set_title('Link Flowrate')
ax.set_xlabel('Timestep')
ax.set_ylabel('m3/s')
ax.legend(loc=0, prop={'size':9})
plt.gcf().subplots_adjust(bottom=0.2)
plt.gcf().subplots_adjust(left=0.15)
pdf.savefig()
plt.close()

pdf.close()

#for node_name in node_list:
#    print '\n\n\n\n',node_name
#    print leak_results.node['pressure'][node_name]
#    print leak_results.node['demand'][node_name]

#time = pd.timedelta_range(start = '0 days 13:00:00', end = '0 days 13:00:00')
#print '\n\n\n'
#print 'Node\t\tPressure\t\tHead\t\tDemand'
#for node_name in node_list:
#    print node_name,'\t\t',leak_results.node.at[(node_name,time[0]),'pressure'],'\t\t',leak_results.node.at[(node_name,time[0]),'head'],'\t\t',leak_results.node.at[(node_name,time[0]),'demand']
#
#print '\n\n\n'
#print 'Link\t\tFlowrate'
#for link_name in link_list:
#    print link_name,'\t\t',leak_results.link.at[(link_name,time[0]),'flowrate']
