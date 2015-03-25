from epanetlib.network.ParseWaterNetwork import ParseWaterNetwork
from epanetlib.network.WaterNetworkModel import *
from epanetlib.sim.WaterNetworkSimulator import *
from epanetlib.sim.EpanetSimulator import *
from epanetlib.sim.ScipySimulator import *
import matplotlib.pylab as plt
import epanetlib as en
import numpy as np 
import networkx as nx
import pandas as pd

plt.close('all')

inp_file = 'networks/Net3.inp'

### THE NEW WAY
# Create a water network model
wn = WaterNetworkModel()
parser = ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Simulate using EPANET
epanet_sim = EpanetSimulator(wn)
epanet_results = epanet_sim.run_sim()

# Simulate using SCIPY
scipy_sim = ScipySimulator(wn)
scipy_results = scipy_sim.run_sim()

# Compare results
print epanet_results.node.shape
print scipy_results.node.shape

plt.figure()
epanet_results.node['demand'].plot(label='EPANET')
scipy_results.node['demand'].plot(label='SCIPY')
plt.title('Node Demand')
plt.legend()

plt.figure()
epanet_results.node['head'].plot(label='EPANET')
scipy_results.node['head'].plot(label='SCIPY')
plt.title('Node Head')
plt.legend()

plt.figure()
epanet_results.node['pressure'].plot(label='EPANET')
scipy_results.node['pressure'].plot(label='SCIPY')
plt.title('Node Pressure')
plt.legend()

plt.figure()
epanet_results.link['flowrate'].plot(label='EPANET')
scipy_results.link['flowrate'].plot(label='SCIPY')
plt.title('Link Flowrate')
plt.legend()

plt.figure()
epanet_results.link['velocity'].plot(label='EPANET')
scipy_results.link['velocity'].plot(label='SCIPY')
plt.title('Link Velocity')
plt.legend()

plt.show()

#print epanet_results.link.flowrate['213']
#print scipy_results.link.flowrate['213']

# We could Pandas testing utilities to compare DataFrames, 
# other options can be added to use almost_equal
from pandas.util.testing import assert_frame_equal
#assert_frame_equal(epanet_results.node, scipy_results.node, check_less_precise=True) 
#assert_frame_equal(epanet_results.link, scipy_results.link, check_less_precise=True) 

