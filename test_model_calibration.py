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
from calibration_utils import *
#import pyomo_utils as pyu

#inp_file = './networks/MyLinear.inp'
#inp_file = './networks/Net1_with_time_controls.inp'
#inp_file = './networks/Net2.inp'
#inp_file = './networks/Net3.inp'
inp_file = './networks/Net6_mod.inp'

run_time = 480#minutes
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
	links_with_controls = ['LINK-1843', 'LINK-1827']
	pumps = wn.links(Pump)
	for pname, p in pumps:
		links_with_controls.append(pname)
	cond_timed_controls = get_conditional_controls_in_time(result_assumed_demands,links_with_controls)
	valves_to_check = ['LINK-1828','VALVE-3891', 'VALVE-3890']
	valve_status = get_valve_status_updates(wn,result_assumed_demands,valves_to_check)
	cond_timed_controls.update(valve_status)

elif inp_file == './networks/Net3.inp':
	links_with_controls = ['335','330']
	cond_timed_controls = get_conditional_controls_in_time(result_assumed_demands,links_with_controls)
else:
	print "CONTROLS NOT ADDED"
	cond_timed_controls = dict()

print cond_timed_controls

# with DMA
dma_dict = dict()

junctions = wn.nodes(Junction)
for n in junctions:
	if n[1].demand_pattern_name is None:
		dma_dict[n[0]]='1'
	else:
		dma_dict[n[0]]=n[1].demand_pattern_name

if with_noise:
	demand_noise = 0.0002
	pressure_noise = 0.01
	head_noise = 0.00001
	flowrate_noise = 0.00
else:
	demand_noise = 0.0
	pressure_noise = 0.0
	head_noise = 0.0
	flowrate_noise = 0.0

# Add noise to demands
result_true_demands = copy.deepcopy(result_assumed_demands)
error1 = add_noise2(wn,result_true_demands,{'demand':demand_noise})
to_fix =  build_fix_demand_dictionary(result_true_demands)
wn_true_demands = copy.deepcopy(wn)

# run true demand simulation
network_sim_true_demand =  PyomoSimulator(wn_true_demands)
network_sim_true_demand._sim_duration_sec = run_time*60
network_sim_true_demand._hydraulic_step_sec = time_step*60 
result_true_states = network_sim_true_demand.run_sim(fixed_demands=to_fix)

# Run calibration
nodes_to_measure = wn._nodes.keys()
links_to_measure = wn._links.keys()
true_states = get_measurements_from_sim_result(copy.deepcopy(result_true_states),
							nodes_to_measure,
							links_to_measure,
							node_params=['head'],
							link_params=['flowrate'],
							duration_min=run_time)

true_measurements = copy.deepcopy(true_states)
#error2 = add_noise(true_measurements,{'pressure':pressure_noise,'flowrate':flowrate_noise,'head':head_noise})
error2 = add_noise2(wn,true_measurements,{'pressure':pressure_noise,'head':head_noise,'flowrate':flowrate_noise})

# d* instead of d double dag
true_measurements.node['demand']=result_assumed_demands.node['demand']

calibrated_wn = copy.deepcopy(wn)
# Add the conditional controls as time controls
calibrated_wn.conditional_controls = dict()
add_time_controls(calibrated_wn, cond_timed_controls)
network_cal =  PyomoSimulator(calibrated_wn)
network_cal._sim_duration_sec = run_time*60
network_cal._hydraulic_step_sec = time_step*60 

calibration_results = network_cal.run_calibration(true_measurements,
		weights =  {'tank_level':1.0, 'pressure':1.0,'head':1.0, 'flowrate':10000.0, 'demand':10000.0},
#		dma_dict=None,
		positive_demand=True)
#		positive_demand=True,
#		dma_dict=dma_dict,
#		fix_base_demand=True)

#print "Error accumulation true demand\n",error1 
#print "Error accumulation true measurements\n",error2 

# Print results to .dat file

print "\nDEMAND Differences\n"
printDifferences(calibration_results,result_assumed_demands,'demand')
print "\nFLOWS Differences \n"
printDifferences(calibration_results,result_assumed_demands,'flowrate')

"""
true_measurements.plot_link_attribute(['VALVE-3890','VALVE-3891'],'flowrate',legend='true')
calibration_results.plot_link_attribute(['VALVE-3890','VALVE-3891'],'flowrate',legend='calib')
result_assumed_demands.plot_link_attribute(['VALVE-3890','VALVE-3891'],'flowrate',legend='base')
plt.ylim(-0.01,0.05)
plt.show()
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




