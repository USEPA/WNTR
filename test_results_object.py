

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

sim = PyomoSimulator(wn)

# Example of setting node and edge attribute from
# the network class and plotting the graph
#for i,l in wn.links.iteritems():
#    if isinstance(l,Pump):
#        print i, wn.get_pump_coefficients(i)

#print wn.time_options

#for node_name, node in wn.Nodes():
#    if wn.isJunction(node_name):
#        print node_name, node.elevation


results = sim.run_sim()

print results.link.flowrate



