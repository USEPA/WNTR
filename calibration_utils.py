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
import time


def get_measurements_from_sim_result(network_results,nodes_to_measure=[],links_to_measure=[],node_params=['demand','head','pressure'],link_params=['flowrate'],duration_min=2880):

	links = network_results.link
	nodes = network_results.node

	if len(nodes)==0 and len(links)==0:
		print "SIMULATION ERROR: Check epanet tmp.rpt file."
		sys.exit()

	# List of times
	time_step_sec = float(network_results.simulator_options['hydraulic_time_step']) 
	n_timesteps = int(round(duration_min/time_step_sec*60))
	measure_times = [t for t in range(n_timesteps+1)]

	# Helper function to map time to timestep
	dateToTimestep = lambda DateTime: DateTime.total_seconds()/time_step_sec
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


def build_fix_demand_dictionary(result_object):
	time_step_sec = float(result_object.simulator_options['hydraulic_time_step']) 
	demands = dict()
	nodes = result_object.node.index.get_level_values('node').drop_duplicates()
	for n in nodes:
		times = result_object.node['demand'][n].index
		for dt in times:
			t = dt.total_seconds()/time_step_sec
			demands[(n,t)] = times = result_object.node['demand'][n][dt]
	return demands

def build_measurement_dictionary(result_object, ignore_parameters=['expected_demand', 'type', 'velocity']):
	measurements = dict()
	type_nodes = set(result_object.node['type'].values)
	# nodes
	for nt in type_nodes:
		measurements[nt] = dict()
		node_measurements = result_object.node[result_object.node['type'] == nt]
		columns = node_measurements.columns.values
		parameters = [p for p in columns if p not in ignore_parameters]
		node_names = node_measurements.index.get_level_values('node').drop_duplicates()
		for param in parameters:
			measurements[nt][param] = dict()
			all_param_measurements = node_measurements[param]
			param_measurements = all_param_measurements.dropna()
			for n in node_names:
				node_measure_times = param_measurements[n].index
				for dt in node_measure_times:
					t = dt.total_seconds()
					measurements[nt][param][n,t] = param_measurements[n][dt]
	# links
	type_links = set(result_object.link['type'].values)
	for lt in type_links:
		measurements[lt] = dict()
		link_measurements = result_object.link[result_object.link['type'] == lt]
		columns = link_measurements.columns.values
		parameters = [p for p in columns if p not in ignore_parameters]
		link_names = link_measurements.index.get_level_values('link').drop_duplicates()
		for param in parameters:
			measurements[lt][param] = dict()
			all_param_measurements = link_measurements[param]
			param_measurements = all_param_measurements.dropna()
			for l in link_names:
				link_measure_times = param_measurements[l].index
				for dt in link_measure_times:
					t = dt.total_seconds()
					measurements[lt][param][l,t] = param_measurements[l][dt]
	return measurements

def build_link_status_dictionary(wn, result_object,tol=1e-6):
	status = dict()
	type_links = set(result_object.link['type'].values)
	for lt in type_links:
		status[lt] = dict()
		link_measurements = result_object.link[result_object.link['type'] == lt]
		link_names = link_measurements['flowrate'].index.get_level_values('link').drop_duplicates()
		if lt == 'valve':
			for l in link_names:
				valve = wn.get_link(l)
				end_node_name = valve.end_node()
				end_node = wn.get_node(end_node_name)
				status[lt][l] = dict()
				link_measure_times = result_object.link['flowrate'][l].index
				for dt in link_measure_times:
					t = dt.total_seconds()
					if abs(result_object.node['pressure'][end_node_name][dt]-valve.setting)<tol:
						status[lt][l][t] = 2
					else:
						flow = result_object.link['flowrate'][l][dt]
						if flow<=tol and flow>=-tol:
							status[lt][l][t] = 0
						else:
							status[lt][l][t] = 1
		else:
			for l in link_names:
				status[lt][l] = dict()
				link_measure_times = result_object.link['flowrate'][l].index
				for dt in link_measure_times:
					t = dt.total_seconds()
					flow = result_object.link['flowrate'][l][dt]
					if flow<=tol and flow>=-tol:
						status[lt][l][t] = 0
					else:
						status[lt][l][t] = 1
	return status


def get_conditional_controls_in_time(result_object, subject_to_conditions = None, tol=1e-6):
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
			if not (flow<=tol and flow>=-tol) and (pflow<=tol and pflow>=-tol):
				open_times.append(t.total_seconds())
			elif (flow<=tol and flow>=-tol) and not (pflow<=tol and pflow>=-tol):
				closed_times.append(t.total_seconds())
		if closed_times or open_times:
			controls[l] = dict()
			controls[l]['open_times'] = open_times
			controls[l]['closed_times'] = closed_times
			controls[l]['active_times'] = []
	return controls

def get_valve_status_updates(wn, result_object, valves_to_check = None, tol=1e-4):
	status = dict()
	valves =  result_object.link[result_object.link['type']=='valve']
	valves = valves.index.get_level_values('link').drop_duplicates()
	if valves_to_check is not None:
		all_links= set(result_object.link.index.get_level_values('link').drop_duplicates())
		valves = all_links.intersection(set(valves_to_check))

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
		tol = 1e-5
		for t in times:
			if valve._base_status == 'CV':
				if result_object.link['flowrate'][v][t]<=tol and result_object.link['flowrate'][v][t]>=-tol:
					closed_times.append(t.total_seconds())
				else:
					open_times.append(t.total_seconds())
			else:
				if abs(result_object.node['pressure'][end_node_name][t]-valve.setting)<tol:
					if prev_status!=1:
						active_times.append(t.total_seconds())
						prev_status=1
				else:
					if result_object.link['flowrate'][v][t]<=tol and result_object.link['flowrate'][v][t]>=-tol:
						if prev_status!=2:
							closed_times.append(t.total_seconds())
							prev_status=2
		    			else:
		    				if prev_status!=3:
		    					open_times.append(t.total_seconds())
		    					prev_status=3
		status[v] = dict()
		status[v]['open_times']=open_times
		status[v]['closed_times']=closed_times
		status[v]['active_times']=active_times
	return status


def build_time_controls_dictionary(wn, result_object, links_with_controls = None, valves_to_check = None):
	timed_controls = get_conditional_controls_in_time(result_object,links_with_controls)
	valve_status = get_valve_status_updates(wn,result_object,valves_to_check)
	timed_controls.update(valve_status)
	return timed_controls


def add_time_controls(wn,dict_time_controls):
	for l in dict_time_controls.keys():
		open_times =  dict_time_controls[l]['open_times']
		closed_times = dict_time_controls[l]['closed_times']
		active_times = dict_time_controls[l]['active_times']
		wn.add_time_control(l,open_times,closed_times,active_times)

def generate_measurements(wn, duration_sec, time_step_sec, noise_dict, nodes_to_measure, links_to_measure, with_noise=False):
	network_simulator = PyomoSimulator(wn)
	network_simulator._sim_duration_sec = duration_sec
	network_simulator._hydraulic_step_sec = time_step_sec
	result_assumed_demands = network_simulator.run_sim()
	if with_noise:
		result_true_demands = copy.deepcopy(result_assumed_demands)
		error1 = add_noise2(wn,result_true_demands,{'demand':noise_dict['demand']})
		to_fix =  build_fix_demand_dictionary(result_true_demands)

		network_simulator_noise = PyomoSimulator(wn)
		network_simulator_noise._sim_duration_sec = duration_sec
		network_simulator_noise._hydraulic_step_sec = time_step_sec
		result_true_states = network_simulator_noise.run_sim(fixed_demands=to_fix)
	else:
		result_true_states = copy.deepcopy(result_assumed_demands)

	true_states = get_measurements_from_sim_result(copy.deepcopy(result_true_states),
							nodes_to_measure,
							links_to_measure,
							node_params=['head'],
							link_params=['flowrate'],
							duration_min=network_simulator._sim_duration_sec/60.0)

	true_measurements = copy.deepcopy(true_states)
	if with_noise:
		error2 = add_noise2(wn,true_measurements,noise_dict)
		print "Error accumulation demands\n",error1 
		print "Error accumulation measurements\n",error2


	# estimate for regularization term
	true_measurements.node['demand']=result_assumed_demands.node['demand']
	true_measurements_dict = build_measurement_dictionary(true_measurements)
	return (result_assumed_demands, result_true_states, true_measurements_dict)


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
