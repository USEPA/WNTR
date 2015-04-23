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
import pyomo_utils as pyu

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
		dict_percentage['pressure'] = measurements.node['pressure'].mean()*0.05
		dict_percentage['head'] = measurements.node['head'].max()*0.005
		dict_percentage['flowrate'] = measurements.link['flowrate'].mean()*0.02
		dict_percentage['velocity'] = measurements.link['velocity'].mean()*0.02

	nodes = measurements.node.index.get_level_values('node').drop_duplicates()
	links = measurements.link.index.get_level_values('link').drop_duplicates()

	node_measured_properties = measurements.node.columns
	link_measured_properties = measurements.link.columns

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
					value = measurements.node[mp][n][dt] 
					if mp is 'demand':
						value = value - meas_error if(value+meas_error<0) else value + meas_error
						measurements.node[mp][n][dt] = value
					else:
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


def add_noise2(wn, measurements,dict_percentage=None):
	if dict_percentage is None:
		dict_percentage = dict()
		dict_percentage['demand'] = 0.02
		dict_percentage['pressure'] = 0.05
		dict_percentage['head'] = 0.005
		dict_percentage['flowrate'] = 0.02

	nodes = measurements.node.index.get_level_values('node').drop_duplicates()
	links = measurements.link.index.get_level_values('link').drop_duplicates()

	node_measured_properties = measurements.node.columns
	link_measured_properties = measurements.link.columns

	# gives an indication of how much noise was added
	noise_magnitude = dict()

	# Add noise to node properties
	node_noise_properties = set(node_measured_properties).intersection(dict_percentage.keys())
	for mp in node_noise_properties:
		count_error = 0
		noise_magnitude[mp] = 0.0
		if dict_percentage[mp]>0.0:
			if mp == 'demand':
				for n in nodes:
					node = wn.get_node(n)
					if isinstance(node,Junction):
						times = measurements.node[mp][n].index
						base = node.base_demand
						std = dict_percentage[mp]*base
						if std>0:
							for dt in times:
								meas_error = np.random.normal(0.0, std)
								value = measurements.node[mp][n][dt] 
								value = value - meas_error if(value+meas_error<0) else value + meas_error
								measurements.node[mp][n][dt] = value
								noise_magnitude[mp] += abs(meas_error)
								count_error += 1
				
			else:
				base = measurements.node[mp].mean()
				std = dict_percentage[mp]*base
				for n in nodes:
					times = measurements.node[mp][n].index
					for dt in times:
						meas_error = np.random.normal(0.0, std)
						measurements.node[mp][n][dt] += meas_error
						noise_magnitude[mp] += abs(meas_error)
						count_error += 1
		if count_error>0:
			noise_magnitude[mp] = noise_magnitude[mp]/count_error

	# Add noise to link properties
	link_noise_properties = set(link_measured_properties).intersection(dict_percentage.keys())
	for mp in link_noise_properties:
		count_error = 0
		noise_magnitude[mp] = 0.0
		base = measurements.link[mp].max()/2.0
		std = base*dict_percentage[mp]
		if std>0:
			for l in links:
				times = measurements.link[mp][l].index
				for dt in times:
					meas_error = np.random.normal(0.0, std)
					value = measurements.link[mp][l][dt]
					# Dont want to change direction of the flow by applying noise and dont apply noise to zero flows
					if value>0:
						measurements.link[mp][l][dt] = value + meas_error if (value+meas_error)>0 else value - meas_error
					elif value<0:
						measurements.link[mp][l][dt] = value + meas_error if (value+meas_error)<0 else value - meas_error
					noise_magnitude[mp] += abs(meas_error)
					count_error += 1
		if count_error>0:
			noise_magnitude[mp] = noise_magnitude[mp]/count_error

	return noise_magnitude


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


def build_fix_demand_dictionary(simulator,result_object):
	dateToTimestep = lambda DateTime: (((DateTime.days*24+DateTime.hours)*60+DateTime.minutes)*60+DateTime.seconds)/simulator._hydraulic_step_sec
	demands = dict()
	nodes = result_object.node.index.get_level_values('node').drop_duplicates()
	for n in nodes:
		times = result_object.node['demand'][n].index
		for dt in times:
			t = dateToTimestep(dt)
			demands[(n,t)] = times = result_object.node['demand'][n][dt]
	return demands

def get_conditional_controls_in_time(result_object, subject_to_conditions = None):

	dateToTime = lambda DateTime: ((DateTime.days*24+DateTime.hours)*60+DateTime.minutes)*60+DateTime.seconds
	controls = dict()
	if subject_to_conditions is None:
		links = result_object.link.index.get_level_values('link').drop_duplicates()
	else:
		all_links=set(result_object.link.index.get_level_values('link').drop_duplicates())
		links = all_links.intersection(set(subject_to_conditions))
	for l in links:
		times = result_object.link['flowrate'][l].index
		open_times = list()
		closed_times = list()
		for j in range(1,len(times)):
			t = times[j]
			pt = times[j-1]
			flow = result_object.link['flowrate'][l][t]
			pflow = result_object.link['flowrate'][l][pt] 
			if flow!=0 and pflow==0:
				open_times.append(dateToTime(t))
			elif flow==0 and pflow!=0:
				closed_times.append(dateToTime(t))
		if closed_times or open_times:
			controls[l] = dict()
			controls[l]['open_times'] = open_times
			controls[l]['closed_times'] = closed_times
			controls[l]['active_times'] = []
	return controls

def get_valve_status_updates(wn, result_object, valves_to_check = None, tol=1e-4):
	dateToTime = lambda DateTime: ((DateTime.days*24+DateTime.hours)*60+DateTime.minutes)*60+DateTime.seconds
	status = dict()

	if valves_to_check is None:
		valves =  result_object.link[result_object.link['type']=='valve']
		valves = valves.index.get_level_values('link').drop_duplicates()
	else:
		all_valves = set([result_object.link['type']=='valve'].index.get_level_values('link').drop_duplicates())
		valves = all_valves.intersection(set(valves_to_check))

	for v in valves:
		times = result_object.link['flowrate'][v].index
		open_times = list()
		closed_times = list()
		active_times = list()
		# it will append all time steps
		valve = wn.get_link(v)
		end_node_name = valve.end_node()
		end_node = wn.get_node(end_node_name)
		prev_status = 0
		for t in times:
			if abs(result_object.node['pressure'][end_node_name][t]-valve.setting)<tol:
				if prev_status!=1:
					active_times.append(dateToTime(t))
					prev_status=1
			else:
				if result_object.link['flowrate'][v][t]==0:
					if prev_status!=2:
						closed_times.append(dateToTime(t))
						prev_status=2
				else:
					if prev_status!=3:
						open_times.append(dateToTime(t))
						prev_status=3
		status[v] = dict()
		status[v]['open_times']=open_times
		status[v]['closed_times']=closed_times
		status[v]['active_times']=active_times
	return status


def add_time_controls(wn,dict_time_controls):
	print dict_time_controls
	for l in dict_time_controls.keys():
		open_times =  dict_time_controls[l]['open_times']
		closed_times = dict_time_controls[l]['closed_times']
		active_times = dict_time_controls[l]['active_times']
		wn.add_time_control(l,open_times,closed_times,active_times)

def plotResults(results1,results2,prop,ln_name):
	nodes = results1.node.index.get_level_values('node').drop_duplicates()
	links = results1.link.index.get_level_values('link').drop_duplicates()

	if ln_name in nodes:
		x = [results2.node[prop][ln_name][t] for t in results2.node[prop][ln_name].index]
		y = [results1.node[prop][ln_name][t] for t in results1.node[prop][ln_name].index]
		tt = [t for t in range(len(results1.node[prop][ln_name].index))]
	elif ln_name in links:
		x = [results2.link[prop][ln_name][t] for t in results2.link[prop][ln_name].index]
		y = [results1.link[prop][ln_name][t] for t in results1.link[prop][ln_name].index]
		tt = [t for t in range(len(results1.link[prop][ln_name].index))]
	else:
		print "Element not found\n"
		return None
	plt.plot(tt,y,label='results1_'+ln_name)
	plt.plot(tt,x,label='results2_'+ln_name)
	plt.legend()



def printDifferences(results1,results2,prop,tol=1e-2):
	
	nodes = results1.node.index.get_level_values('node').drop_duplicates()
	links = results1.link.index.get_level_values('link').drop_duplicates() 

	nodes1 = results1.node
	links1 = results1.link
	nodes2 = results2.node
	links2 = results2.link

	if prop in nodes1.columns:
		for n in nodes:
			for t in nodes1[prop][n].index:
				if abs(nodes1[prop][n][t]-nodes2[prop][n][t])>tol: 
					print n," ",t," ",nodes1[prop][n][t], nodes2[prop][n][t], abs(nodes1[prop][n][t]-nodes2[prop][n][t]) 
	elif prop in links1.columns:
		for l in links:
			for t in links1[prop][l].index:
				if abs(links1[prop][l][t]-links2[prop][l][t])>tol: 
					print l," ",t," ",links1[prop][l][t], links2[prop][l][t], abs(links1[prop][l][t]-links2[prop][l][t])
	else:
		print "Property not in the results file"
		

#inp_file = './networks/MyLinear.inp'
#inp_file = './networks/Net1_with_time_controls.inp'
#inp_file = './networks/Net2.inp'
#inp_file = './networks/Net3.inp'
inp_file = './networks/Net6_mod.inp'

run_time = 60 #minutes
time_step = 60 #minutes
with_noise = False
wn = WaterNetworkModel()
wn.name = inp_file
parser = ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)
network_sim =  PyomoSimulator(wn)
network_sim._sim_duration_sec = run_time*60
network_sim._hydraulic_step_sec = time_step*60 

# Run simulation 
result_assumed_demands = network_sim.run_sim()


if inp_file == './networks/Net6_mod.inp':
	links_with_controls = ['LINK-1843']
	pumps = wn.links(Pump)
	for pname, p in pumps:
		links_with_controls.append(pname)
	cond_timed_controls = get_conditional_controls_in_time(result_assumed_demands,links_with_controls)
	valve_status = get_valve_status_updates(wn,result_assumed_demands)
	cond_timed_controls.update(valve_status)

elif inp_file == './networks/Net3.inp':
	links_with_controls = ['335','330']
	cond_timed_controls = get_conditional_controls_in_time(result_assumed_demands,links_with_controls)
else:
	cond_timed_controls = dict()

"""
t_link = '101'
x = [result_assumed_demands.link['flowrate'][t_link][t] for t in result_assumed_demands.link['flowrate'][t_link].index]
tt = [t for t in range(len(result_assumed_demands.link['flowrate'][t_link].index))]
plt.figure()
plt.plot(tt,x,label='estimation')
plt.legend()
plt.show()

"""

# with DMA
dma_dict = dict()

junctions = wn.nodes(Junction)
for n in junctions:
	if n[1].demand_pattern_name is None:
		dma_dict[n[0]]='1'
	else:
		dma_dict[n[0]]=n[1].demand_pattern_name

#print dma_dict
"""
flowrate_noise = 0.01*result_assumed_demands.node['demand'].max()/2.0
pressure_noise = 0.02*result_assumed_demands.node['pressure'].max()/2.0
head_noise = 0.005*result_assumed_demands.node['head'].max()/2.0
"""
if with_noise:
	demand_noise = 0.1
	pressure_noise = 0.01
	head_noise = 0.001
	flowrate_noise = 0.01
else:
	demand_noise = 0.0
	pressure_noise = 0.0
	head_noise = 0.0
	flowrate_noise = 0.0

# Add noise to demands
result_true_demands = copy.deepcopy(result_assumed_demands)
#error1 = add_noise(result_true_demands,{'demand':flowrate_noise})


error1 = add_noise2(wn,result_true_demands,{'demand':demand_noise})
"""
#error1 = add_noise2(wn,result_true_demands,{'demand':demand_noise,'pressure':pressure_noise,'head':head_noise,'flowrate':flowrate_noise})
print error1
plt.figure()
result_assumed_demands.node['demand'].plot(label='SIM_ASSUMED_DEMAND')
result_true_demands.node['demand'].plot(label='SIM_TRUE_STATES')
plt.title('Node Demand')
plt.legend()

plt.figure()
result_assumed_demands.node['pressure'].plot(label='SIM_ASSUMED_DEMAND')
result_true_demands.node['pressure'].plot(label='SIM_TRUE_STATES')
plt.title('Node Pressure')
plt.legend()

plt.figure()
result_assumed_demands.node['head'].plot(label='SIM_ASSUMED_DEMAND')
result_true_demands.node['head'].plot(label='SIM_TRUE_STATES')
plt.title('Node Head')
plt.legend()

plt.figure()
result_assumed_demands.link['flowrate'].plot(label='SIM_ASSUMED_DEMAND')
result_true_demands.link['flowrate'].plot(label='SIM_TRUE_STATES')
plt.title('Link Flowrate')
plt.legend()
plt.show()
sys.exit()
"""
to_fix =  build_fix_demand_dictionary(network_sim,result_true_demands)

wn_true_demands = copy.deepcopy(wn)

# run true demand simulation
network_sim_true_demand =  PyomoSimulator(wn_true_demands)
network_sim_true_demand._sim_duration_sec = run_time*60
network_sim_true_demand._hydraulic_step_sec = time_step*60 
result_true_states = network_sim_true_demand.run_sim(fixed_demands=to_fix)


"""
plt.figure()
result_assumed_demands.node['demand'].plot(label='SIM_ASSUMED_DEMAND')
result_true_states.node['demand'].plot(label='SIM_TRUE_STATES')
plt.title('Node Demand')
plt.legend()
plt.show()
sys.exit()
"""

# Run calibration

# Get measurements
#nodes_to_measure = ['9','10','11','12','13','21','22','23','31','32','2']
#links_to_measure = []
nodes_to_measure = wn._nodes.keys()
links_to_measure = wn._links.keys()




true_states = get_measurements_from_sim_result(copy.deepcopy(result_true_states),
							nodes_to_measure,
							links_to_measure,
							node_params=['head','demand'],
							link_params=['flowrate'],
							duration_min=run_time,
							time_step_min=time_step,
							freq=1)

true_measurements = copy.deepcopy(true_states)
#error2 = add_noise(true_measurements,{'pressure':pressure_noise,'flowrate':flowrate_noise,'head':head_noise})
error2 = add_noise2(wn,true_measurements,{'pressure':pressure_noise,'head':head_noise,'flowrate':flowrate_noise})

"""
plt.figure()
true_measurements.node['demand'].plot(label='NOISE')
result_assumed_demands.node['demand'].plot(label='SIM_TRUE_STATES')
plt.title('Node Demand')
plt.legend()

plt.figure()
true_measurements.node['pressure'].plot(label='NOISE')
result_true_states.node['pressure'].plot(label='SIM_TRUE_STATES')
plt.title('Node Pressure')
plt.legend()

plt.figure()
true_measurements.node['head'].plot(label='NOISE')
result_true_states.node['head'].plot(label='SIM_TRUE_STATES')
plt.title('Node Head')
plt.legend()

plt.figure()
true_measurements.link['flowrate'].plot(label='NOISE')
result_true_states.link['flowrate'].plot(label='NOT NOISE')
plt.title('Link Flowrate')
plt.legend()
plt.ylabel('flow (m3)')
plt.show()
sys.exit()
"""

# d* instead of d double dag
true_measurements.node['demand']=result_assumed_demands.node['demand']

"""
select_measurements_per_property({'demand':['10','22','13','21'],
									'pressure':['11','23','31','32']},
									{},
									true_measurements)
"""

calibrated_wn = copy.deepcopy(wn)
# Add the conditional controls as time controls

calibrated_wn.conditional_controls = dict()
add_time_controls(calibrated_wn, cond_timed_controls)
network_cal =  PyomoSimulator(calibrated_wn)
network_cal._sim_duration_sec = run_time*60
network_cal._hydraulic_step_sec = time_step*60 
#check_results = network_cal.run_sim()
#printDifferences(check_results,check_results,'demand',tol=1e-4)


calibration_results = network_cal.run_calibration(true_measurements,
		weights =  {'tank_level':1.0, 'pressure':1.0,'head':1.0, 'flowrate':10000.0, 'demand':10000.0},
#		dma_dict=None,
		positive_demand=True)
#		positive_demand=True,
#		dma_dict=dma_dict,
#		fix_base_demand=True)

print "Error accumulation true demand\n",error1 
print "Error accumulation true measurements\n",error2 

# Print results to .dat file
result_assumed_demands.node['demand'].to_csv('simulation.dat')
calibration_results.node['demand'].to_csv('calibration.dat')

"""
print "\nDEMANDS\n"
printDifferences(calibration_results,result_assumed_demands,'demand')
print "\nFLOWS\n"
printDifferences(calibration_results,result_assumed_demands,'flowrate')
"""
plt.figure()
if 'head' in calibration_results.node.columns:
	calibration_results.node['head'].plot(label='ESTIMATION')
result_assumed_demands.node['head'].plot(label='SIM_ASSUMED_DEMAND')
if 'head' in result_true_states.node.columns:
	result_true_states.node['head'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Head')
plt.legend()

plt.figure()
if 'pressure' in calibration_results.node.columns:
	calibration_results.node['pressure'].plot(label='ESTIMATION')
result_assumed_demands.node['pressure'].plot(label='SIM_ASSUMED_DEMAND')
if 'pressure' in result_true_states.node.columns:
	result_true_states.node['pressure'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Pressure')
plt.legend()

plt.figure()
if 'demand' in calibration_results.node.columns:
	calibration_results.node['demand'].plot(label='ESTIMATION')
result_assumed_demands.node['demand'].plot(label='SIM_ASSUMED_DEMAND')
if 'demand' in result_true_states.node.columns:
	result_true_states.node['demand'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Demand')
plt.legend()

plt.figure()
calibration_results.link['flowrate'].plot(label='ESTIMATION')
result_assumed_demands.link['flowrate'].plot(label='SIM_ASSUMED_DEMAND')
result_true_states.link['flowrate'].plot(label='SIM_TRUE_DEMAND')
plt.title('Link Flowrate')
plt.legend()

plt.show()



