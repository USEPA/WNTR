import wntr
import matplotlib.pylab as plt

# Create a water network model
inp_file = 'networks/Net3.inp'
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
plt.figure(figsize=(6,10))
plt.subplot(3,1,1)
plt.plot(epanet_results.node['demand'])
plt.title('EPANET, Node Demand')
plt.subplot(3,1,2)
plt.plot(epanet_results.node['demand'] - scipy_results.node['demand'])
plt.title('EPANET - SCIPY, Node Demand')
plt.subplot(3,1,3)
plt.plot(epanet_results.node['demand'] - pyomo_results.node['demand'])
plt.title('EPANET - PYOMO, Node Demand')

plt.figure(figsize=(6,10))
plt.subplot(3,1,1)
plt.plot(epanet_results.node['head'])
plt.title('EPANET, Node Head')
plt.subplot(3,1,2)
plt.plot(epanet_results.node['head'] - scipy_results.node['head'])
plt.title('EPANET - SCIPY, Node Head')
plt.subplot(3,1,3)
plt.plot(epanet_results.node['head'] - pyomo_results.node['head'])
plt.title('EPANET - PYOMO, Node Head')

plt.figure(figsize=(6,10))
plt.subplot(3,1,1)
plt.plot(epanet_results.node['pressure'])
plt.title('EPANET, Node Pressure')
plt.subplot(3,1,2)
plt.plot(epanet_results.node['pressure'] - scipy_results.node['pressure'])
plt.title('EPANET - SCIPY, Node Pressure')
plt.subplot(3,1,3)
plt.plot(epanet_results.node['pressure'] - pyomo_results.node['pressure'])
plt.title('EPANET - PYOMO, Node Pressure')

plt.figure(figsize=(6,10))
plt.subplot(3,1,1)
plt.plot(epanet_results.link['flowrate'])
plt.title('EPANET, Link Flowrate')
plt.subplot(3,1,2)
plt.plot(epanet_results.link['flowrate'] - scipy_results.link['flowrate'])
plt.title('EPANET - SCIPY, Link Flowrate')
plt.subplot(3,1,3)
plt.plot(epanet_results.link['flowrate'] - pyomo_results.link['flowrate'])
plt.title('EPANET - PYOMO, Link Flowrate')

plt.figure(figsize=(6,10))
plt.subplot(3,1,1)
plt.plot(epanet_results.link['velocity'])
plt.title('EPANET, Link Velocity')
plt.subplot(3,1,2)
plt.plot(epanet_results.link['velocity'] - scipy_results.link['velocity'])
plt.title('EPANET - SCIPY, Link Velocity')
plt.subplot(3,1,3)
plt.plot(epanet_results.link['velocity'] - pyomo_results.link['velocity'])
plt.title('EPANET - PYOMO, Link Velocity')
