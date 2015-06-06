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
import pickle as pk
from calibration_utils import *

#import pyomo_utils as pyu

#inp_file = './networks/MyLinear.inp'
#inp_file = './networks/Net1_with_time_controls.inp'
#inp_file = './networks/Net3.inp'
inp_file = './networks/Net6_mod.inp'

run_time = 1440#minutes
time_step = 60 #minutes
pandas_result = False
with_noise = False
generate_measures = True
wn = WaterNetworkModel()
wn.name = inp_file
parser = ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

"""
from print_utils import *

network_simulator = PyomoSimulator(wn)
network_simulator._sim_duration_sec = run_time*60
network_simulator._hydraulic_step_sec = time_step*60
sim_results = network_simulator.run_sim(pandas_result=pandas_result)

network_simulator2 = PyomoSimulator(wn)
network_simulator2._sim_duration_sec = run_time*60
network_simulator2._hydraulic_step_sec = time_step*60
sim_results2 = network_simulator2.run_sim(pandas_result=pandas_result)

noise_dict = dict()
noise_dict['demand'] = 0.1
noise_dict['pressure'] = 0.0
noise_dict['head'] = 0.0
noise_dict['flowrate'] = 0.0
add_additive_noise(wn,sim_results2,noise_dict,tol=1e-5,truncated=False)
#print sim_results.link
#print sim_results2.link

compare_plot(sim_results,sim_results2,'demand',['junction'])
plt.figure()
compare_plot(sim_results,sim_results2,'head')
plt.figure()
compare_plot(sim_results,sim_results2,'flowrate')
plt.show()

sys.exit()
"""

if generate_measures:
	noise_dict = dict()
	noise_dict['demand'] = 0.000
	noise_dict['pressure'] = 0.00
	noise_dict['head'] = 0.000
	noise_dict['flowrate'] = 0.0

	nodes_to_measure = [n for n,N in wn.nodes(Tank)]
	#nodes_to_measure = wn._nodes.keys()
	#links_to_measure = [l for l,L in wn.links(Pump)]
	links_to_measure = wn._links.keys()
	print "Links: ",len(links_to_measure)
	print "Node: ",len(nodes_to_measure)
	print "Tanks:" ,len([n for n,N in wn.nodes(Tank)])
	print "Pumps:", len([l for l,L in wn.links(Pump)])
	t0= time.time()
	cdata = generate_calibration_data(wn,run_time*60,
		time_step*60, 
		noise_dict, 
		nodes_to_measure, 
		links_to_measure, 
		with_noise=with_noise, 
		truncated=False, 
		pandas_result=pandas_result,
		simulator = 'pyomo')
	print "TIME OF DATA GENERATION ", time.time() - t0
	if inp_file == './networks/Net6_mod.inp':
		links_with_controls = ['LINK-1843', 'LINK-1827']
		valves_to_check = ['LINK-1828','VALVE-3891', 'VALVE-3890']
		pumps = wn.links(Pump)
		for pname, p in pumps:
			links_with_controls.append(pname)
		cond_timed_controls = build_time_controls_dictionary(wn,cdata.sim_results,links_with_controls,valves_to_check)
	elif inp_file == './networks/Net3.inp':
		links_with_controls = ['335','330']
		cond_timed_controls = build_time_controls_dictionary(wn,cdata.sim_results,links_with_controls)
	else:
		print "CONTROLS NOT ADDED"
		cond_timed_controls = dict()

	cdata.time_controls_dict = cond_timed_controls
	cdata.status_dict = build_link_status_dictionary(wn, cdata.noise_sim_results)

	t0 = time.time()
	pk.dump( cdata, open( "measure_struc.p", "wb" ) )
	print "\nTime to pickle the data :", time.time() - t0
else:
	t0 = time.time()
	cdata = pk.load( open( "measure_struc.p", "rb" ) )
	print "\nTime to unpickle data :", time.time() - t0

"""
network_simulator2 = EpanetSimulator(wn)
network_simulator2._sim_duration_sec = cdata.sim_duration_sec
network_simulator2._hydraulic_step_sec = cdata.sim_time_step_sec
sim_results2 = network_simulator2.run_sim(pandas_result=pandas_result)
cdata.init_dict = build_initialization_dict(sim_results2)
"""

# Run calibration
calibrated_wn = copy.deepcopy(wn)
# Add the conditional controls as time controls
calibrated_wn.conditional_controls = dict()
add_time_controls(calibrated_wn, cdata.time_controls_dict)
network_cal =  PyomoSimulator(calibrated_wn)
network_cal._sim_duration_sec = cdata.sim_duration_sec
network_cal._hydraulic_step_sec = cdata.sim_time_step_sec

junctions_to_calibrate =  [n for n,N in wn.nodes(Junction)]
ro = [l for l,L in wn.links(Pipe)]
#pipes_to_calibrate = [ro[i] for i in range(10)]
pipes_to_calibrate = []
calibrate_lists = {'demand':junctions_to_calibrate,'roughness':pipes_to_calibrate}

calibration_results = network_cal.run_calibration(cdata.measurement_dict,
	calibrate_lists,
	#weights =  {'tank_level':1.0, 'pressure':1.0,'head':1.0, 'flowrate':1000.0, 'demand':1000.0},
	solver_options={'halt_on_ampl_error':'yes','bound_push':1e-12},
	weights =  {'tank_level':100.0, 'pressure':1.0,'head':1.0, 'flowrate':1000.0, 'demand':100.0},
	init_dict = cdata.init_dict,
	external_link_statuses = cdata.status_dict,
	regularization_dict = cdata.regularization_dict,
	pandas_result = pandas_result)


compare_plot(calibration_results,cdata.noise_sim_results,'demand')
plt.figure()
compare_plot(calibration_results,cdata.noise_sim_results,'head')
plt.figure()
compare_plot(calibration_results,cdata.noise_sim_results,'flowrate')
plt.show()
"""
print "\nDEMAND Differences\n"
printDifferences(calibration_results,cdata.noise_sim_results,'demand')
print "\nFLOWS Differences \n"
printDifferences(calibration_results,cdata.noise_sim_results,'flowrate')
"""

"""
plt.figure()
if 'head' in calibration_results.node.columns:
	calibration_results.node['head'].plot(label='ESTIMATION')
cdata.sim_results.node['head'].plot(label='SIM_ASSUMED_DEMAND')
if 'head' in cdata.noise_sim_results.node.columns:
	cdata.noise_sim_results.node['head'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Head')
plt.legend()

plt.figure()
if 'pressure' in calibration_results.node.columns:
	calibration_results.node['pressure'].plot(label='ESTIMATION')
cdata.sim_results.node['pressure'].plot(label='SIM_ASSUMED_DEMAND')
if 'pressure' in cdata.noise_sim_results.node.columns:
	cdata.noise_sim_results.node['pressure'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Pressure')
plt.legend()

plt.figure()
if 'demand' in calibration_results.node.columns:
	calibration_results.node['demand'].plot(label='ESTIMATION')
cdata.sim_results.node['demand'].plot(label='SIM_ASSUMED_DEMAND')
if 'demand' in cdata.noise_sim_results.node.columns:
	cdata.noise_sim_results.node['demand'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Demand')
plt.legend()

plt.figure()
calibration_results.link['flowrate'].plot(label='ESTIMATION')
cdata.sim_results.link['flowrate'].plot(label='SIM_ASSUMED_DEMAND')
cdata.noise_sim_results.link['flowrate'].plot(label='SIM_TRUE_DEMAND')
plt.title('Link Flowrate')
plt.legend()
plt.show()
"""




