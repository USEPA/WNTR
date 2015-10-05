import wntr
import matplotlib.pylab as plt
import os

# Create a water network model
my_path = os.path.abspath(os.path.dirname(__file__))
inp_file = os.path.join(my_path,'networks','Net3.inp')
wn = wntr.network.WaterNetworkModel(inp_file)

# Simulate using EPANET
epanet_sim = wntr.sim.EpanetSimulator(wn)
epanet_results = epanet_sim.run_sim()

# Simulate using Scipy
scipy_sim = wntr.sim.ScipySimulator(wn)
scipy_results = scipy_sim.run_sim()

# Simulate using PYOMO
pyomo_sim = wntr.sim.PyomoSimulator(wn)
pyomo_results = pyomo_sim.run_sim()

# Compare results
plt.close('all')
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
