from epanetlib.network.ParseWaterNetwork import ParseWaterNetwork
from epanetlib.network.WaterNetworkModel import *
from epanetlib.sim.WaterNetworkSimulator import *
from epanetlib.sim.EpanetSimulator import *
from epanetlib.sim.ScipySimulator import *
from epanetlib.sim.PyomoSimulator import *
import matplotlib.pylab as plt
import epanetlib as en
import numpy as np
import networkx as nx
import pandas as pd
import time

plt.close('all')

inp_file_pdd = 'networks/Net1_PDD.inp'
inp_file_original = 'networks/Net1.inp'

# Create pressure dependent water network model
wn_pdd = WaterNetworkModel()
parser = ParseWaterNetwork()
parser.read_inp_file(wn_pdd, inp_file_pdd)

# Create and parse original water network model
wn_original = WaterNetworkModel()
parser_orig = ParseWaterNetwork()
parser_orig.read_inp_file(wn_original, inp_file_original)

pyomo_sim_pdd = PyomoSimulator(wn_pdd)
pyomo_sim_pdd.all_pump_outage('0 days 02:00:00', '1 days 00:00:00')
t0 = time.time()
pyomo_results_pdd = pyomo_sim_pdd.run_sim()
print "Overall simulation time: ", time.time()-t0
#exit()


pyomo_sim_original = PyomoSimulator(wn_original)
t0 = time.time()
pyomo_results_original = pyomo_sim_original.run_sim()
print "Overall simulation time: ", time.time()-t0


plt.figure()
pyomo_results_pdd.node['demand'].plot(label='PUMP OUTAGE')
pyomo_results_original.node['demand'].plot(label='ORIGINAL')
plt.title('Node Demand')
plt.legend()

plt.figure()
pyomo_results_pdd.node['head'].plot(label='PUMP OUTAGE')
pyomo_results_original.node['head'].plot(label='ORIGINAL')
plt.title('Node Head')
plt.legend()

plt.figure()
pyomo_results_pdd.node['pressure'].plot(label='PUMP OUTAGE')
pyomo_results_original.node['pressure'].plot(label='ORIGINAL')
plt.title('Node Pressure')
plt.legend()

plt.figure()
pyomo_results_pdd.link['flowrate'].plot(label='PUMP OUTAGE')
pyomo_results_original.link['flowrate'].plot(label='ORIGINAL')
plt.title('Link Flowrate')
plt.legend()

plt.figure()
pyomo_results_pdd.link['velocity'].plot(label='PUMP OUTAGE')
pyomo_results_original.link['velocity'].plot(label='ORIGINAL')
plt.title('Link Velocity')
plt.legend()

plt.show()

flow_diff_tol = 1e-3
head_diff_tol = 1e-3

print "DEMAND COMPARISON"
for node_name, node in wn_original.nodes():
    #    if isinstance(link, Pump):
    for t in pyomo_results_original.time:
        #epanet_flow = epanet_results.link.flowrate[link_name][t]
        orig_demand = pyomo_results_original.node.demand[node_name][t]
        pdd_demand = pyomo_results_pdd.node.demand[node_name][t]
        demand_diff = abs(orig_demand - pdd_demand)
        if demand_diff > flow_diff_tol:
            print node_name, t, demand_diff, "\t Original: ", orig_demand, "PDD: ", pdd_demand

print "PRESSURE COMPARISON"
for node_name, node in wn_original.nodes():
    #    if isinstance(link, Pump):
    for t in pyomo_results_original.time:
        #epanet_flow = epanet_results.link.flowrate[link_name][t]
        orig_pressure = pyomo_results_original.node.pressure[node_name][t]
        pdd_pressure = pyomo_results_pdd.node.pressure[node_name][t]
        pressure_diff = abs(orig_pressure - pdd_pressure)
        if pressure_diff > flow_diff_tol:
            print node_name, t, pressure_diff, "\t Original: ", orig_pressure, "PDD: ", pdd_pressure



"""
print "FLOW COMPARISON"
for link_name, link in wn.links():
    #    if isinstance(link, Pump):
    for t in epanet_results.time:
        epanet_flow = epanet_results.link.flowrate[link_name][t]
        pyomo_flow = pyomo_results.link.flowrate[link_name][t]
        flow_diff = abs(epanet_flow - pyomo_flow)
        if flow_diff > flow_diff_tol:
            print link_name, t, flow_diff, "\t Epanet: ", epanet_flow, "Pyomo: ", pyomo_flow
"""
print "Original demands at Tank"
print pyomo_results_original.node['demand']['2']
print "PDD demands at Tank"
print pyomo_results_pdd.node['demand']['2']
print "PDD pressure at Tank"
print pyomo_results_pdd.node['pressure']['2']

exit()

