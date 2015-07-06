import epanetlib as en
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

plt.close('all')

inp_file = 'networks/Net6_mod.inp'

# Create water network model from inp file
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Run a demand driven simulation and store results
pyomo_sim = en.sim.PyomoSimulator(wn,'DEMAND DRIVEN')
print '\nRunning Demand Driven Simulation'
res_demand_driven = pyomo_sim.run_sim()

# Run a pressure driven simulation with constant nominal pressure for all nodes
wn.set_nominal_pressures(constant_nominal_pressure = 40.0)
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
print '\nRunning pressure driven simulation with a single nominal pressure for all nodes'
res_with_const_PF = pyomo_sim.run_sim()

# Run a pressure driven simulation with varying nominal pressures
wn.set_nominal_pressures(res = res_demand_driven)
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
print '\nRunning pressure driven simulation with nomial pressures dependent on node'
res_with_varying_PF = pyomo_sim.run_sim()

# Run a simulation with pump outage
pyomo_sim = en.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
pyomo_sim.all_pump_outage('0 days 00:00:00', '0 days 24:00:00')
print '\nRunning pressure driven simulation with nominal pressures dependent on nodes and all pumps out'
res_with_outage = pyomo_sim.run_sim()

"""
# Saving results to a file
f = open('out.py','w')
f.write('Junct\tReq D\t\tConst PF\tConst D\t\tVar PF\t\tVar D\n')
for junction_name,junction in wn.nodes(en.network.Junction):
    for t in xrange(len(res_with_const_PF.node['pressure'][junction_name])):
        f.write('{0}\t{1:7.1e}\t\t40.0\t\t{2:7.1e}\t\t{3:7.1f}\t\t{4:7.1e}\n'.format(junction_name,res_demand_driven.node['expected_demand'][junction_name][t],res_with_const_PF.node['demand'][junction_name][t],junction.PF,res_with_varying_PF.node['demand'][junction_name][t]))
f.close()
"""

# Percent demand met = actual/expected
junctions_list = [name for name,node in wn.nodes(en.network.Junction)]
const_PF_percent_met = res_with_const_PF.node.loc[junctions_list, 'demand']/(res_with_const_PF.node.loc[junctions_list, 'expected_demand'])
vary_PF_percent_met = res_with_varying_PF.node.loc[junctions_list, 'demand']/(res_with_varying_PF.node.loc[junctions_list, 'expected_demand'])
outage_percent_met = res_with_outage.node.loc[junctions_list, 'demand']/(res_with_outage.node.loc[junctions_list, 'expected_demand'])

pdf = PdfPages('test_nom_P_all_nodes_net6_mod.pdf')

plt.subplot(311)
const_PF_percent_met.plot(color='k')
plt.title('Percent Met: Single Nominal Pressure for all Nodes')

plt.subplot(312)
vary_PF_percent_met.plot(color='k')
plt.title('Percent Met: Nominal Pressure dependent on Node')

plt.subplot(313)
outage_percent_met.plot(color='k')
plt.title('Percent Met: Pump Outage')

pdf.savefig()
plt.close()
pdf.close()


"""
pdf = PdfPages('test_nom_P_indiv_nodes_net6_mod.pdf')
t = range(len(res_demand_driven.node['demand'][junctions_list[0]]))
const_PF_percent_met = range(len(res_demand_driven.node['demand'][junctions_list[0]]))
vary_PF_percent_met = range(len(res_demand_driven.node['demand'][junctions_list[0]]))
outage_percent_met = range(len(res_demand_driven.node['demand'][junctions_list[0]]))
for junction_name, junction in wn.nodes(en.network.Junction):
    for i in t:
        const_PF_percent_met[i] = res_with_const_PF.node['demand'][junction_name][i]/res_with_const_PF.node['expected_demand'][junction_name][i]
        vary_PF_percent_met[i] = res_with_varying_PF.node['demand'][junction_name][i]/res_with_varying_PF.node['expected_demand'][junction_name][i]
        outage_percent_met[i] = res_with_outage.node['demand'][junction_name][i]/res_with_outage.node['expected_demand'][junction_name][i]
    plt.subplot(311)
    plt.plot(t,const_PF_percent_met)
    plt.title(junction_name)
    plt.subplot(312)
    plt.plot(t,vary_PF_percent_met)
    plt.subplot(313)
    plt.plot(t,outage_percent_met)
    pdf.savefig()
    plt.close()
pdf.close()
"""
