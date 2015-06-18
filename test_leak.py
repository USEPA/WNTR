import epanetlib as en
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

inp_file = 'networks/net_test_2.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Simulate using PYOMO
wn.set_nominal_pressures(constant_nominal_pressure = 15.0)
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
pyomo_sim.add_leak(leak_name = 'leak1', pipe_name = 'pipe2', leak_diameter=0.2, start_time = '0 days 02:00:00', fix_time = '0 days 10:00:00')
leak_results = pyomo_sim.run_sim()

# Plot Pyomo results
node_list = [name for name,node in wn.nodes()]
node_list.append('leak1')
t_step = range(len(leak_results.node['demand'][node_list[0]]))
link_list = [name for name,link in wn.links()]
link_list.remove('pipe2')
link_list.append('pipe2__A')
link_list.append('pipe2__B')
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

