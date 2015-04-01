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
import copy
import sys

def generateData(wn,nodes_to_measure=[],links_to_measure=[],node_params=['demand','head','pressure'],link_params=['flowrate'],duration_min=2880,time_step_min=15,freq=1, simulator='scipy'):
	
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

def get_measurements_from_sim_result(network_results,nodes_to_measure=[],links_to_measure=[],node_params=['demand','head','pressure'],link_params=['flowrate'],duration_min=2880,time_step_min=15,freq=1):

	links = network_results.link
	nodes = network_results.node

	if len(nodes)==0 and len(links)==0:
		print "SIMULATION ERROR: Check epanet tmp.rpt file."
		sys.exit()

	# List of times
	n_timesteps = int(round(duration_min/time_step_min))
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


def select_measurements_per_property(dict_nodes,dict_links,measurements):
	nodes = measurements.node.index.get_level_values('node').drop_duplicates()
	links = measurements.link.index.get_level_values('link').drop_duplicates()

	node_measured_properties = measurements.node.columns
	link_measured_properties = measurements.link.columns

 	node_nan_properties = set(node_measured_properties).intersection(dict_nodes.keys())
	for n in nodes:
		for mp in node_nan_properties:
			if n not in dict_nodes[mp]:
				measurements.node[mp][n] = np.nan

	link_nan_properties = set(link_measured_properties).intersection(dict_links.keys())
	for l in links:
		for mp in link_nan_properties:
			if l not in dict_links[mp]:
				measurements.link[mp][l] = np.nan

def add_noise(measurements,dict_percentage=None):
	if dict_percentage is None:
		dict_percentage = dict()
		dict_percentage['demand'] = measurements.node['demand'].mean()*0.02
		dict_percentage['pressure'] = measurements.node['pressure'].meam()*0.05
		dict_percentage['head'] = measurements.node['head'].max()*0.005
		dict_percentage['flowrate'] = measurements.link['flowrate'].mean()*0.02
		dict_percentage['velocity'] = measurements.link['velocity'].mean()*0.02

	nodes = measurements.node.index.get_level_values('node').drop_duplicates()
	links = measurements.link.index.get_level_values('link').drop_duplicates()

	node_measured_properties = measurements.node.columns
	link_measured_properties = measurements.link.columns

	print dict_percentage

	error = dict()
	node_noise_properties = set(node_measured_properties).intersection(dict_percentage.keys())
	for mp in node_noise_properties:
		error[mp] = 0.0
		std = dict_percentage[mp]
		if dict_percentage[mp]>0.0:
			for n in nodes:
				times = measurements.node[mp][n].index
				for dt in times:
					meas_error = np.random.normal(0.0, std)
					measurements.node[mp][n][dt] += meas_error
					error[mp] += meas_error

	link_noise_properties = set(link_measured_properties).intersection(dict_percentage.keys())
	for mp in link_noise_properties:
		error[mp] = 0.0
		std = dict_percentage[mp]
		if dict_percentage[mp]>0.0:
			for l in links:
				times = measurements.link[mp][l].index
				for dt in times:
					meas_error = np.random.normal(0.0, std)
					measurements.link[mp][l][dt] += meas_error
					error[mp] += meas_error
	return error


def set_water_network_demands(wn,result_object):
	junctions = wn.nodes(Junction)
	node_results = result_object.node
	found = False
	for n in junctions:
		node = n[1]
		node.base_demand = 1.0
		node.demand_pattern_name = str(node)+"_pattern"
		node_pattern = [d for d in node_results['demand'][str(node)]]
		wn.add_pattern(str(node)+"_pattern",node_pattern)
	wn.time_options['PATTERN TIMESTEP'] = wn.time_options['HYDRAULIC TIMESTEP']

inp_file = './networks/Net1_with_time_controls.inp'
#inp_file = './networks/Net2.inp'
#inp_file = './networks/c-town_true_network.inp'

run_time = 1440 #minutes
time_step = 15 #minutes
wn = WaterNetworkModel()
wn.name = inp_file
parser = ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)
network_sim =  PyomoSimulator(wn)
network_sim._sim_duration_sec = run_time*60
network_sim._hydraulic_step_sec = time_step*60 

# Run simulation 
result_assumed_demands = network_sim.run_sim()

# with DMA
dma_dict = dict()

junctions = wn.nodes(Junction)
for n in junctions:
	if n[1].demand_pattern_name is None:
		if n[1].base_demand!=0:
			dma_dict[n[0]]='1'
	else:
		dma_dict[n[0]]=n[1].demand_pattern_name

#print dma_dict

flowrate_noise = 0.05*result_assumed_demands.node['demand'].max()/2.0
pressure_noise = 0.02*result_assumed_demands.node['pressure'].max()/2.0
head_noise = 0.005*result_assumed_demands.node['head'].max()/2.0

# Add noise to demands
result_true_demands = copy.deepcopy(result_assumed_demands)
error1 = add_noise(result_true_demands,{'demand':flowrate_noise})

wn_true_demands = copy.deepcopy(wn)

# run true demand simulation
network_sim_true_demand =  PyomoSimulator(wn_true_demands)
network_sim_true_demand._sim_duration_sec = run_time*60
network_sim_true_demand._hydraulic_step_sec = time_step*60 
result_true_states = network_sim_true_demand.run_sim(fixed_demands = result_true_demands)


# Run calibration

# Get measurements
#nodes_to_measure = ['9','10','11','12','13','21','22','23','31','32','2']
#links_to_measure = ['110']
nodes_to_measure = wn._nodes.keys()
links_to_measure = wn._links.keys()

true_states = get_measurements_from_sim_result(copy.deepcopy(result_true_states),
							nodes_to_measure,
							links_to_measure,
							node_params=['pressure','head','demand'],
							link_params=['flowrate'],
							duration_min=run_time,
							time_step_min=time_step,
							freq=1)

true_measurements = copy.deepcopy(true_states)
error2 = add_noise(true_measurements,{'pressure':pressure_noise,'flowrate':flowrate_noise,'head':head_noise})

# d* instead of d double dag
true_measurements.node['demand']=result_assumed_demands.node['demand']

"""
select_measurements_per_property({'demand':['10','22','13','21'],
									'pressure':['11','23','31','32']},
									{},
									true_measurements)
"""

calibration_results = network_sim.run_calibration(true_measurements,
		weights =  {'tank_level':1.0, 'pressure':1.0, 'flowrate':1000.0, 'demand':1.0},
		dma_dict=None)
#		dma_dict=dma_dict,
#		fix_base_demand=True)


print "Error accumulation true demand\n",error1 
print "Error accumulation true measurements\n",error2 

# Print results to .dat file
result_assumed_demands.node.to_csv('simulation.dat')
calibration_results.node.to_csv('calibration.dat')


plt.figure()
if 'demand' in calibration_results.node.columns:
	calibration_results.node['demand'].plot(label='CALIBRATION')
result_assumed_demands.node['demand'].plot(label='SIM_ASSUMED_DEMAND')
if 'demand' in result_true_states.node.columns:
	result_true_states.node['demand'].plot(label='SIM_TRUE_STATES')
plt.title('Node Demand')
plt.legend()

plt.figure()
if 'head' in calibration_results.node.columns:
	calibration_results.node['head'].plot(label='CALIBRATION')
result_assumed_demands.node['head'].plot(label='SIM_ASSUMED_DEMAND')
if 'head' in result_true_states.node.columns:
	result_true_states.node['head'].plot(label='SIM_TRUE_STATES')
plt.title('Node Head')
plt.legend()

plt.figure()
if 'pressure' in calibration_results.node.columns:
	calibration_results.node['pressure'].plot(label='CALIBRATION')
result_assumed_demands.node['pressure'].plot(label='SIM_ASSUMED_DEMAND')
if 'pressure' in result_true_states.node.columns:
	result_true_states.node['pressure'].plot(label='SIM_TRUE_STATES')
plt.title('Node Pressure')
plt.legend()

plt.figure()
calibration_results.link['flowrate'].plot(label='CALIBRATION')
result_assumed_demands.link['flowrate'].plot(label='SIM_ASSUMED_DEMAND')
result_true_states.link['flowrate'].plot(label='SIM_TRUE_STATES')
plt.title('Link Flowrate')
plt.legend()
plt.show()


#sys.exit()
