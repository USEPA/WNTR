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

class calibration_data_struct:
    def __init__(self):
        self.sim_results = None
        self.noise_sim_results = None
        self.measurement_dict = None
        self.time_controls_dict = None
        self.status_dict = None
        self.init_dict = None
        self.regularization_dict = None
        self.sim_duration_sec = None
        self.sim_time_step_sec = None

def get_measurements_from_sim_result(network_results,nodes_to_measure=[],links_to_measure=[],node_params=['demand','head','pressure'],link_params=['flowrate']):

	links = network_results.link
	nodes = network_results.node

	if isinstance(links,dict) and isinstance(nodes,dict):
		
		back_nodes = copy.deepcopy(nodes)
		for node_type, node_type_vals in nodes.iteritems():
			for param, param_vals in node_type_vals.iteritems():
				if param in node_params:
					if nodes_to_measure:
						for node, times in param_vals.iteritems():
							if node not in nodes_to_measure:
								del back_nodes[node_type][param][node]
				else:
					del back_nodes[node_type][param]

		# remove empty entries
		for node_type, node_type_vals in back_nodes.iteritems():
			for param in back_nodes[node_type].keys():
				if not back_nodes[node_type][param]:
					del back_nodes[node_type][param]
		for node_type in back_nodes.keys():
			if not back_nodes[node_type]:
				del back_nodes[node_type]
		"""

		for node_type, node_type_vals in nodes.iteritems():
			for param in node_type_vals.keys():
				if param in node_params:
					if nodes_to_measure:
						for node in nodes[node_type][param].keys():
							if node not in nodes_to_measure:
								del nodes[node_type][param][node]
				else:
					del nodes[node_type][param]

		# remove empty entries
		for node_type, node_type_vals in nodes.iteritems():
			for param in nodes[node_type].keys():
				if not nodes[node_type][param]:
					del nodes[node_type][param]
		for node_type in nodes.keys():
			if not nodes[node_type]:
				del nodes[node_type]
		"""
		back_links = copy.deepcopy(links)
		for link_type, link_type_vals in links.iteritems():
			for param, param_vals in link_type_vals.iteritems():
				if param in link_params:
					if links_to_measure:
						for link, times in param_vals.iteritems():
							if link not in links_to_measure:
								del back_links[link_type][param][link]
				else:
					del back_links[link_type][param]

		# remove empty entries
		for link_type, link_type_vals in back_links.iteritems():
			for param in link_type_vals.keys():
				if not back_links[link_type][param]:
					del back_links[link_type][param]
		for link_type in back_links.keys():
			if not back_links[link_type]:
				del back_links[link_type]
		"""

		for link_type, link_type_vals in links.iteritems():
			for param in link_type_vals.keys():
				if param in link_params:
					if links_to_measure:
						for link in links[link_type][param].keys():
							if link not in links_to_measure:
								del links[link_type][param][link]
				else:
					del links[link_type][param]

		# remove empty entries
		for link_type, link_type_vals in links.iteritems():
			for param in link_type_vals.keys():
				if not links[link_type][param]:
					del links[link_type][param]
		for link_type in links.keys():
			if not links[link_type]:
				del links[link_type]
		"""
		network_results.node = back_nodes
		network_results.link = back_links
	else:
		if len(nodes)==0 and len(links)==0:
			RuntimeError("Non measurements to select.")

		# List of times
		time_step_sec = float(network_results.simulator_options['hydraulic_time_step']) 
		duration_min = network_results.simulator_options['duration']
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

def add_additive_noise(wn,measurements,dict_percentage,tol=1e-5,truncated=True):
	noise_magnitude = dict()
	if isinstance(measurements.node,dict) and isinstance(measurements.link,dict):
		# Add noise to node measurements
		parameters_to_add_noise = [key for key,vals in dict_percentage.iteritems() if vals>0.0]
		for node_type, param_list in measurements.node.iteritems():
			for param, node_list in param_list.iteritems():
				if param in parameters_to_add_noise:
					if dict_percentage[param]>0.0:
						count_error = 0
						noise_magnitude[param] = 0.0
						for n, tvals in node_list.iteritems():
							node = wn.get_node(n)
							if param == 'demand':
								if isinstance(node,Junction):
									measures = tvals.values()
									mean = sum(m for m in measures)/float(len(measures))
									std = dict_percentage[param]*mean
									for t, meas in tvals.iteritems():
										if meas>tol:
											if truncated:
												meas_error = truncnorm.rvs(0.0, np.inf, 0.0, std) 
											else:
												meas_error = np.random.normal(0.0, std)
											measurements.node[node_type][param][n][t] += meas_error
											noise_magnitude[param] += abs(meas_error)
											count_error += 1
							else:
								measures = tvals.values()
								mean = sum(abs(m) for m in measures)/float(len(measures))
								std = dict_percentage[mp]*mean
								for t, meas in tvals.iteritems():
									if abs(meas)>tol:
										if truncated:
											meas_error = truncnorm.rvs(0.0, np.inf, 0.0, std) 
										else:
											meas_error = np.random.normal(0.0, std)
										measurements.node[node_type][param][n][t] += meas_error
										noise_magnitude[param] += abs(meas_error)
										count_error += 1
						if count_error>0:
							noise_magnitude[param] = noise_magnitude[param]/float(count_error)

		# Add noise to node measurements
		for link_type, param_list in measurements.link.iteritems():
			for param, link_list in param_list.iteritems():
				if param in parameters_to_add_noise:
					if dict_percentage[param]>0.0:
						count_error = 0
						noise_magnitude[param] = 0.0
						for l, tvals in link_list.iteritems():
							measures = tvals.values()
							mean = sum(abs(m) for m in measures)/float(len(measures))
							std = dict_percentage[param]*mean
							for t, meas in tvals.iteritems():
								if abs(meas)>tol:
									if truncated:
										meas_error = truncnorm.rvs(0.0, np.inf, 0.0, std) 
									else:
										meas_error = np.random.normal(0.0, std)
									measurements.link[link_type][param][l][t] += meas_error
									noise_magnitude[param] += abs(meas_error)
									count_error += 1
						if count_error>0:
							noise_magnitude[param] = noise_magnitude[param]/float(count_error)

	else:
		nodes = measurements.node.index.get_level_values('node').drop_duplicates()
		links = measurements.link.index.get_level_values('link').drop_duplicates()

		node_measured_properties = measurements.node.columns
		link_measured_properties = measurements.link.columns
		# gives an indication of how much noise was added
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
							#base = node.base_demand
							base = measurements.node[mp][n].mean()
							#print measurements.node[mp][n]
							#print base, node.base_demand
							std = dict_percentage[mp]*base
							for dt in times:
								if measurements.node[mp][n][dt]>tol:
									if truncated:
										meas_error = truncnorm.rvs(0.0, np.inf, 0.0, std) 
									else:
										meas_error = np.random.normal(0.0, std)
									measurements.node[mp][n][dt] += meas_error
									noise_magnitude[mp] += abs(meas_error)
									count_error += 1
				else:
					for n in nodes:
						base = measurements.node[mp][n].mean()
						std = dict_percentage[mp]*base
						times = measurements.node[mp][n].index
						for dt in times:
							if measurements.node[mp][n][dt]<-tol or measurements.node[mp][n][dt]>tol:
								if truncated:
									meas_error = truncnorm.rvs(0.0, np.inf, 0.0, std) 
								else:
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
			if dict_percentage[mp]>0.0:
				for l in links:
					base = sum(abs(v) for v in measurements.link[mp][l])/float(len(measurements.link[mp][l].index))
					std = base*dict_percentage[mp]
					times = measurements.link[mp][l].index
					for dt in times:
						if measurements.link[mp][l][dt]<-tol or measurements.link[mp][l][dt]>tol:
							if truncated:
								meas_error = truncnorm.rvs(0.0, np.inf, 0.0, std)  
							else:
								meas_error = np.random.normal(0.0, std)
								measurements.link[mp][l][dt] += meas_error
								noise_magnitude[mp] += abs(meas_error)
								count_error += 1
			if count_error>0:
				noise_magnitude[mp] = noise_magnitude[mp]/count_error
	return noise_magnitude

def build_fix_demand_dictionary(result_object):
	time_step_sec = float(result_object.simulator_options['hydraulic_time_step']) 
	demands = dict()
	if isinstance(result_object.node,dict):
		for node_type in result_object.node.iterkeys():
			for node in result_object.node[node_type]['demand'].iterkeys():
				for time in result_object.node[node_type]['demand'][node].iterkeys():
					t = time/time_step_sec
					demands[(node,t)] = result_object.node[node_type]['demand'][node][time]
	else:
		nodes = result_object.node.index.get_level_values('node').drop_duplicates()
		for n in nodes:
			times = result_object.node['demand'][n].index
			for dt in times:
				t = dt.total_seconds()/time_step_sec
				demands[(n,t)] = result_object.node['demand'][n][dt]
	return demands

def build_measurement_dictionary(result_object, ignore_parameters=['expected_demand', 'type', 'velocity']):
	if isinstance(result_object.node,dict) and isinstance(result_object.link,dict):
		measurements = copy.deepcopy(result_object.node)
		measurements.update(copy.deepcopy(result_object.link))
		for meas_type in measurements.iterkeys():
			for param in measurements[meas_type].keys():
				if param in ignore_parameters:
					del measurements[meas_type][param]
	else:
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
					measurements[nt][param][n] = dict()
					node_measure_times = param_measurements[n].index
					for dt in node_measure_times:
						t = dt.total_seconds()
						measurements[nt][param][n][t] = param_measurements[n][dt]
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
					measurements[lt][param][l] = dict()
					link_measure_times = param_measurements[l].index
					for dt in link_measure_times:
						t = dt.total_seconds()
						measurements[lt][param][l][t] = param_measurements[l][dt]
	
	return measurements


def get_node_type(node):
	if isinstance(node,Junction):
		node_type =  'junction'
	elif isinstance(node,Tank):
		node_type =  'tank'
	elif isinstance(node,Reservoir):
		node_type =  'reservoir'
	else:
		raise RuntimeError(l + 'is not an element of the network.')
	return node_type

def get_link_type(link):
	if isinstance(link,Pipe):
		link_type =  'pipe'
	elif isinstance(link,Valve):
		link_type =  'valve'
	elif isinstance(link,Pump):
		link_type =  'pump'
	else:
		raise RuntimeError(l + 'is not an element of the network.')
	return link_type

def build_link_status_dictionary(wn, result_object,tol=1e-6):
	status = dict()
	if isinstance(result_object.link,dict) and isinstance(result_object.node,dict):
		type_meas = 'flowrate'
		for link_type in result_object.link.iterkeys():
			status[link_type] = dict()
			if link_type == 'valve':
				for l, tvals in result_object.link[link_type][type_meas].iteritems():
					status[link_type][l] = dict()
					valve = wn.get_link(l)
					end_node_name = valve.end_node()
					end_node = wn.get_node(end_node_name)
					node_type = get_node_type(end_node)
					for t, flow in tvals.iteritems():
						p_end_node = result_object.node[node_type]['pressure'][end_node_name][t]
						if abs(p_end_node-valve.setting)<tol:
							status[link_type][l][t] = 2
						else:
							if flow<=tol and flow>=-tol:
								status[link_type][l][t] = 0
							else:
								status[link_type][l][t] = 1
			else:
				for l, tvals in result_object.link[link_type][type_meas].iteritems():
					status[link_type][l] = dict()
					for t, flow in tvals.iteritems():
						if flow<=tol and flow>=-tol:
							status[link_type][l][t] = 0
						else:
							status[link_type][l][t] = 1

	else:
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


def get_conditional_controls_in_time(wn,result_object, subject_to_conditions = None, tol=1e-6):
	controls = dict()
	if isinstance(result_object.link,dict) and isinstance(result_object.node,dict):
		all_links = set([l for link_type in result_object.link.iterkeys() for l in result_object.link[link_type]['flowrate'].iterkeys()])
		if subject_to_conditions is None:
			links = all_links
		else:
			links = all_links.intersection(set(subject_to_conditions))
		
		for l in links:
			link = wn.get_link(l)
			link_type = get_link_type(link)
			open_times = list()
			closed_times = list()
			times = result_object.link[link_type]['flowrate'][l].keys()
			times.sort()
			for j in range(1,len(times)):
				t = times[j]
				pt = times[j-1]
				flow = result_object.link[link_type]['flowrate'][l][t]
				pflow = result_object.link[link_type]['flowrate'][l][pt]
				if not (flow<=tol and flow>=-tol) and (pflow<=tol and pflow>=-tol):
					open_times.append(t)
				elif (flow<=tol and flow>=-tol) and not (pflow<=tol and pflow>=-tol):
					closed_times.append(t)
			if closed_times or open_times:
				controls[l] = dict()
				controls[l]['open_times'] = open_times
				controls[l]['closed_times'] = closed_times
				controls[l]['active_times'] = []
	else:
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
	if isinstance(result_object.link,dict) and isinstance(result_object.node,dict):
		if valves_to_check is not None:
			all_links = set([l for link_type in result_object.link.iterkeys() for l in result_object.link[link_type]['flowrate'].iterkeys()])
			valves = all_links.intersection(set(valves_to_check))
		else:
			valves = set([l for link_type in result_object.link.iterkeys() for l in result_object.link[link_type]['flowrate'].iterkeys() if link_type=='valve'])

		for v in valves:
			open_times = list()
			closed_times = list()
			active_times = list()
			valve = wn.get_link(v)
			link_type = get_link_type(valve)
			times = result_object.link[link_type]['flowrate'][v].keys()
			times.sort()
			# it will append all time steps
			end_node_name = valve.end_node()
			end_node = wn.get_node(end_node_name)
			end_node_type = get_node_type(end_node)
			prev_status = 0
			for t in times:
				flow = result_object.link[link_type]['flowrate'][v][t]
				if valve._base_status == 'CV':
					if flow<=tol and flow>=-tol:
						closed_times.append(t)
					else:
						open_times.append(t)
				else:
					if link_type == 'valve':
						p_end_node = result_object.node[end_node_type]['pressure'][end_node_name][t]
						if abs(p_end_node-valve.setting)<tol:
							if prev_status!=1:
								active_times.append(t)
								prev_status=1
						else:
							if flow<=tol and flow>=-tol:
								if prev_status!=2:
									closed_times.append(t)
									prev_status=2
							else:
								if prev_status!=3:
									open_times.append(t)
									prev_status=3
			status[v] = dict()
			status[v]['open_times']=open_times
			status[v]['closed_times']=closed_times
			status[v]['active_times']=active_times


	else:
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
	timed_controls = get_conditional_controls_in_time(wn,result_object,links_with_controls)
	valve_status = get_valve_status_updates(wn,result_object,valves_to_check)
	timed_controls.update(valve_status)
	return timed_controls


def add_time_controls(wn,dict_time_controls):
	for l in dict_time_controls.keys():
		open_times =  dict_time_controls[l]['open_times']
		closed_times = dict_time_controls[l]['closed_times']
		active_times = dict_time_controls[l]['active_times']
		wn.add_time_control(l,open_times,closed_times,active_times)

#from time_utils import *
#@run_lineprofile(follow=[])

def generate_calibration_data(wn, duration_sec, time_step_sec, noise_dict, nodes_to_measure, links_to_measure, with_noise=False, truncated=True, pandas_result=True, simulator='pyomo'):
	# container
	data = calibration_data_struct()

	# simulator
	if simulator=='epanet':
		network_simulator = EpanetSimulator(wn)
	else:
		network_simulator = PyomoSimulator(wn)
	network_simulator._sim_duration_sec = duration_sec
	network_simulator._hydraulic_step_sec = time_step_sec
	data.sim_results = network_simulator.run_sim(solver_options={'halt_on_ampl_error':'yes','bound_push':1e-12},
		pandas_result=pandas_result)
	data.init_dict = build_initialization_dict(data.sim_results)
	if with_noise and noise_dict['demand']>0.0:
		result_true_demands = copy.deepcopy(data.sim_results)
		error1 = add_additive_noise(wn,result_true_demands,{'demand':noise_dict['demand']},truncated=truncated)
		print "Accumulation error in demands\n",error1
		to_fix =  build_fix_demand_dictionary(result_true_demands)
		network_simulator_noise = PyomoSimulator(wn)
		network_simulator_noise._sim_duration_sec = duration_sec
		network_simulator_noise._hydraulic_step_sec = time_step_sec
		data.noise_sim_results = network_simulator_noise.run_sim(fixed_demands=to_fix,pandas_result=pandas_result)

	else:
		data.noise_sim_results = copy.deepcopy(data.sim_results)

	

	true_measurements = get_measurements_from_sim_result(copy.deepcopy(data.noise_sim_results),
							nodes_to_measure,
							links_to_measure,
							node_params=['head'],
							link_params=['flowrate'])

	if with_noise:
		#true_measurements.plot_link_attribute(links_to_plot=['204'])
		error2 = add_additive_noise(wn,true_measurements,noise_dict,truncated=truncated) 
		print "Accumulation error in measurements\n",error2
	
	# store measurements in dictionary
	data.measurement_dict = build_measurement_dictionary(true_measurements)
	#from print_utils import *
	#pretty_print_dict(data.measurement_dict)
	# estimate for regularization term
	data.regularization_dict = build_regularization_dict(data.sim_results)
	data.sim_duration_sec = duration_sec
	data.sim_time_step_sec = time_step_sec

	return data

def build_initialization_dict(result_object):
	return build_measurement_dictionary(result_object, ignore_parameters=['expected_demand', 'type', 'velocity', 'pressure'])

def build_regularization_dict(result_object,ignore_parameters=['expected_demand', 'type', 'velocity', 'pressure','head','flowrate']):
	return build_measurement_dictionary(result_object, ignore_parameters)

def compare_plot(results1,results2,parameter_to_compare,type_meas=[]):
	
	r1 = build_measurement_dictionary(results1)
	r2 = build_measurement_dictionary(results2)

	l1 = list()
	l2 = list()

	if not type_meas:
		type_meas = r1.keys()

	for node_type in r1.keys():
		if node_type in type_meas:
			for param in r1[node_type].keys():
				if param == parameter_to_compare:
					for node in r1[node_type][param].keys():
						for t in r1[node_type][param][node].keys():
							l1.append(r1[node_type][param][node][t])
							l2.append(r2[node_type][param][node][t])
							#if abs(r1[node_type][param][node][t]-r2[node_type][param][node][t])>1e-1:
							#	print node_type," ",param,node,t,r1[node_type][param][node][t],r2[node_type][param][node][t]

	#for i in range(len(l1)):
	#	print l1[i],"  ", l2[i]
	min_max = [min(min(l1),min(l2)),max(max(l1),max(l2))]
	plt.plot(min_max,min_max)
	plt.title(parameter_to_compare + ' Net3')
	plt.xlabel('PYOMO')
	plt.ylabel('EPANET')
	plt.plot(l1,l2,'r.')
	

def printDifferences(results1,results2,prop,tol=1e-2):
	if isinstance(results1.link,dict) and isinstance(results1.node,dict):
		dict_res1 = build_measurement_dictionary(results1)
		dict_res2 = build_measurement_dictionary(results2)
		r = 0.0
		residual = copy.deepcopy(dict_res1)
		print "Type  Parameter  name  time  result1  result2"
		for node_type in residual.keys():
			for param in residual[node_type].keys():
				for node in residual[node_type][param].keys():
					for t in residual[node_type][param][node].keys():
						residual[node_type][param][node][t] = abs(dict_res1[node_type][param][node][t])-abs(dict_res2[node_type][param][node][t])
						if residual[node_type][param][node][t]>tol:							
							print node_type + "  " + param + "  " + node + "  " + t + "  " +  dict_res1[node_type][param][node][t] + "  " + dict_res2[node_type][param][node][t]
						r += residual[node_type][param][node][t]

		print "Total residual: ", r
	else:
		nodes = results1.node.index.get_level_values('node').drop_duplicates()
		links = results1.link.index.get_level_values('link').drop_duplicates() 

		nodes1 = results1.node
		links1 = results1.link
		nodes2 = results2.node
		links2 = results2.link

		print "name  time  result1  result2"
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



