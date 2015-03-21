from epanetlib.network.ParseWaterNetwork import ParseWaterNetwork
from epanetlib.network.WaterNetworkModel import *
from epanetlib.sim.WaterNetworkSimulator import *
from epanetlib.sim.EpanetSimulator import *
from epanetlib.sim.PyomoSimulator import *
import matplotlib.pylab as plt
import epanetlib as en
import numpy as np 
import networkx as nx
import pandas as pd

plt.close('all')

inp_file = 'networks/Net1_with_time_controls.inp'


### THE OLD WAY
enData = en.pyepanet.ENepanet()
enData.inpfile = inp_file
enData.ENopen(enData.inpfile,'tmp.rpt')
G = en.network.epanet_to_MultiDiGraph(enData)
G = en.sim.eps_hydraulic(enData, G)

D = pd.DataFrame(nx.get_node_attributes(G,'demand'))
D.plot(title='Node Demand')
H = pd.DataFrame(nx.get_node_attributes(G,'head'))
H.plot(title='Node Head')
P = pd.DataFrame(nx.get_node_attributes(G,'pressure'))
P.plot(title='Node Pressure')
V = pd.DataFrame(nx.get_edge_attributes(G,'velocity'))
V.plot(title='Link Velocity')
F = pd.DataFrame(nx.get_edge_attributes(G,'flow'))
F.plot(title='Link Flowrate')

### THE NEW WAY
# Create a water network model
wn = WaterNetworkModel()
parser = ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Graph the network
en.network.draw_graph(wn, title= wn.name)

# Simulate using EPANET
epanet_sim = EpanetSimulator(wn)
epanet_results = epanet_sim.run_sim()

# Simulate using PYOMO
pyomo_sim = PyomoSimulator(wn)
pyomo_results = pyomo_sim.run_sim()

# Compare results
print epanet_results.node.shape
print pyomo_results.node.shape

plt.figure()
epanet_results.node['demand'].plot(label='EPANET')
pyomo_results.node['demand'].plot(label='PYOMO')
plt.title('Node Demand')
plt.legend()

plt.figure()
epanet_results.node['head'].plot(label='EPANET')
pyomo_results.node['head'].plot(label='PYOMO')
plt.title('Node Head')
plt.legend()

plt.figure()
epanet_results.node['pressure'].plot(label='EPANET')
pyomo_results.node['pressure'].plot(label='PYOMO')
plt.title('Node Pressure')
plt.legend()

plt.figure()
epanet_results.link['flowrate'].plot(label='EPANET')
pyomo_results.link['flowrate'].plot(label='PYOMO')
plt.title('Link Flowrate')
plt.legend()

plt.figure()
epanet_results.link['velocity'].plot(label='EPANET')
pyomo_results.link['velocity'].plot(label='PYOMO')
plt.title('Link Velocity')
plt.legend()

# We could Pandas testing utilities to compare DataFrames, 
# other options can be added to use almost_equal
from pandas.util.testing import assert_frame_equal
assert_frame_equal(epanet_results.node, pyomo_results.node, check_less_precise=True) 
assert_frame_equal(epanet_results.link, pyomo_results.link, check_less_precise=True) 

