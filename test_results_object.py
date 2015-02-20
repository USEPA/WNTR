

from epanetlib.network.ParseWaterNetwork import ParseWaterNetwork
from epanetlib.network.WaterNetworkModel import *
from epanetlib.sim.WaterNetworkSimulator import *
import matplotlib.pylab as plt
import epanetlib as en
import numpy as np 
import networkx as nx
import pandas as pd

wn = WaterNetworkModel()
parser = ParseWaterNetwork()

parser.read_inp_file(wn, 'networks/Net1.inp')

sim = WaterNetworkSimulator(wn)

# Example of setting node and edge attribute from
# the network class and plotting the graph
#for i,l in wn.links.iteritems():
#    if isinstance(l,Pump):
#        print i, wn.get_pump_coefficients(i)

print wn.time_options

print "*********************"
print "*********************"

#for node_name, node in wn.Nodes():
#    if wn.isJunction(node_name):
#        print node_name, node.elevation

results = sim.run_pyomo_sim()

#print results.link
#print results.node.demand['11']['0 day 0 hours':'0 day 10 hours']

print "---------------------------------------"
print "Demand at node 11  between 0 to 5 hours"
print "---------------------------------------"
demand_11 = results.node.demand['11']
print demand_11['0 day 0 hours':'0 day 5 hours 0 min']
print "---------------------------------------"

print "------------------"
print "Flowrate at link 1 "
print "------------------"
print results.link.flowrate['10']
print "------------------"

print "------------------"
print "Pressure at time 12 hours "
print "------------------"
print results.node.pressure[:, '0 day 12 hours']
print "------------------"




