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
import sys

def generateData(inp,nodes_to_measure=[],links_to_measure=[],node_params=['demand','head','pressure'],link_params=['flowrate'],duration_min=2880,time_step_min=15,freq=1, simulator='scipy'):
	wn = WaterNetworkModel()
	wn.name = inp
	parser = ParseWaterNetwork()
	parser.read_inp_file(wn, inp)
	
	# Choose simulator
	if simulator == 'scipy':
		network_sim = ScipySimulator(wn)
	elif simulator == 'pyomo':
		network_sim =  PyomoSimulator(wn)
	elif simulator == 'epanet':
		network_sim = EpanetSimulator(wn)
	else:
		print "ERROR: The simulator " + simulator + " is not within the simulator options.\n"
		sys.exit()
	# Run simulation
	network_sim._sim_duration_sec = duration_min*60     # this seems to be only in secs
	network_sim._hydraulic_step_sec = time_step_min*60 # this seems to be only in secs
	network_results = network_sim.run_sim()

	links = network_results.link
	nodes = network_results.node

	if len(nodes)==0 and len(links)==0:
		print "SIMULATION ERROR: Check epanet tmp.rpt file."
		sys.exit()

	# List of times
	n_timesteps = int(round(network_sim._sim_duration_sec/network_sim._hydraulic_step_sec))
	measure_times = [t for t in range(0,n_timesteps+1,freq)]

	# Helper function to map time to timestep
	dateToTimestep = lambda DateTime: (((DateTime.days*24+DateTime.hours)*60+DateTime.minutes)*60+DateTime.seconds)/network_sim._hydraulic_step_sec
	# Filter nodes
	node_params += ['type']
	node_params_to_drop = [c for c in nodes.columns if c not in node_params]
	nodes.drop(node_params_to_drop,inplace=True,axis=1)
	nodes = nodes[[dateToTimestep(dt) in measure_times and n in nodes_to_measure for n, dt in nodes.index]]
	network_results.node = nodes

	# Filter links
	link_params += ['type']
	link_params_to_drop = [c for c in links.columns if c not in link_params]
	links.drop(link_params_to_drop,inplace=True,axis=1)
	links = links[[dateToTimestep(dt) in measure_times and l in links_to_measure for l, dt in links.index]]
	network_results.link = links

	return network_results


inp_file = './networks/Net1_with_time_controls.inp'

run_time = 30  #minutes
time_step = 15 #minutes 
wn = WaterNetworkModel()
wn.name = inp_file
parser = ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)
network_sim =  PyomoSimulator(wn)
network_sim._sim_duration_sec = run_time*60
network_sim._hydraulic_step_sec = time_step*60 

# Run simulation 
simulation_results = network_sim.run_sim()

# Run calibration

# Get measurements
nodes_to_measure = ['10','11','13','21','22','23','31','32']
links_to_measure = ['110']
measurements = generateData(inp_file,
							nodes_to_measure,
							links_to_measure,
							node_params=['head','pressure'],
							link_params=['flowrate'],
							duration_min=run_time,
							time_step_min=time_step,
							freq=1,
							simulator='pyomo')
calibration_results = network_sim.run_calibration(measurements)

# Print results to .dat file
simulation_results.node.to_csv('simulation.dat')
calibration_results.node.to_csv('calibration.dat')


plt.figure()
calibration_results.node['demand'].plot(label='CALIBRATION')
simulation_results.node['demand'].plot(label='SIMULATION')
plt.title('Node Demand')
plt.legend()

plt.figure()
calibration_results.node['head'].plot(label='CALIBRATION')
simulation_results.node['head'].plot(label='SIMULATION')
plt.title('Node Head')
plt.legend()

plt.figure()
calibration_results.node['pressure'].plot(label='CALIBRATION')
simulation_results.node['pressure'].plot(label='SIMULATION')
plt.title('Node Pressure')
plt.legend()

plt.figure()
calibration_results.link['flowrate'].plot(label='CALIBRATION')
simulation_results.link['flowrate'].plot(label='SIMULATION')
plt.title('Link Flowrate')
plt.legend()
plt.show()

#sys.exit()
