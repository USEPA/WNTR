import epanetlib as en
import matplotlib.pylab as plt

plt.close('all')

inp_file = 'networks/Net1_with_time_controls.inp'
#inp_file = 'networks/Net1.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Graph the network
en.network.draw_graph(wn, title= wn.name)

# Simulate using EPANET
epanet_sim = en.sim.EpanetSimulator(wn)
epanet_results = epanet_sim.run_sim()

# Simulate using Scipy
scipy_sim = en.sim.ScipySimulator(wn)
scipy_results = scipy_sim.run_sim()

# Simulate using PYOMO
pyomo_sim = en.sim.PyomoSimulator(wn)
pyomo_results = pyomo_sim.run_sim()

# Compare results
plt.figure()
epanet_results.node['demand'].plot(label='EPANET')
scipy_results.node['demand'].plot(label='SCIPY')
pyomo_results.node['demand'].plot(label='PYOMO')
plt.title('Node Demand')
plt.legend()

plt.figure()
epanet_results.node['head'].plot(label='EPANET')
scipy_results.node['head'].plot(label='SCIPY')
pyomo_results.node['head'].plot(label='PYOMO')
plt.title('Node Head')
plt.legend()

plt.figure()
epanet_results.node['pressure'].plot(label='EPANET')
scipy_results.node['pressure'].plot(label='SCIPY')
pyomo_results.node['pressure'].plot(label='PYOMO')
plt.title('Node Pressure')
plt.legend()

plt.figure()
epanet_results.link['flowrate'].plot(label='EPANET')
scipy_results.link['flowrate'].plot(label='SCIPY')
pyomo_results.link['flowrate'].plot(label='PYOMO')
plt.title('Link Flowrate')
plt.legend()

plt.figure()
epanet_results.link['velocity'].plot(label='EPANET')
scipy_results.link['velocity'].plot(label='SCIPY')
pyomo_results.link['velocity'].plot(label='PYOMO')
plt.title('Link Velocity')
plt.legend()
