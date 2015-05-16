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

class pickler_struct:
    def __init__(self):
        self.sim_results = None
        self.noise_sim_results = None
        self.measurement_dict = None
        self.time_controls_dict = None
        self.status_dict = None

#import pyomo_utils as pyu

#inp_file = './networks/MyLinear.inp'
#inp_file = './networks/Net1_with_time_controls.inp'
#inp_file = './networks/Net3.inp'
inp_file = './networks/Net6_mod.inp'

run_time = 1440#minutes
time_step = 60 #minutes
with_noise = False
generate_measures = True
wn = WaterNetworkModel()
wn.name = inp_file
parser = ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)


if generate_measures:
	noise_dict = dict()
	noise_dict['demand'] = 0.0002
	noise_dict['pressure'] = 0.01
	noise_dict['head'] = 0.0001
	noise_dict['flowrate'] = 0.00

	nodes_to_measure = wn._nodes.keys()
	links_to_measure = wn._links.keys()
	result_meas = generate_measurements(wn,run_time*60,time_step*60, noise_dict, nodes_to_measure, links_to_measure, with_noise=with_noise)
	result_assumed_demands = result_meas[0]
	result_true_states = result_meas[1]
	true_measurements_dict = result_meas[2]

	if inp_file == './networks/Net6_mod.inp':
		links_with_controls = ['LINK-1843', 'LINK-1827']
		valves_to_check = ['LINK-1828','VALVE-3891', 'VALVE-3890']
		pumps = wn.links(Pump)
		for pname, p in pumps:
			links_with_controls.append(pname)
		cond_timed_controls = build_time_controls_dictionary(wn,result_assumed_demands,links_with_controls,valves_to_check)
	elif inp_file == './networks/Net3.inp':
		links_with_controls = ['335','330']
		cond_timed_controls = build_time_controls_dictionary(wn,result_assumed_demands,links_with_controls)
	else:
		print "CONTROLS NOT ADDED"
		cond_timed_controls = dict()

	status_dict = build_link_status_dictionary(wn, result_assumed_demands)

	stored = pickler_struct()
	stored.sim_results = result_assumed_demands
	stored.noise_sim_results = result_true_states
	stored.measurement_dict = true_measurements_dict
	stored.time_controls_dict = cond_timed_controls
	stored.status_dict = status_dict
	pk.dump( stored, open( "measure_struc.p", "wb" ) )
else:
	stored = pk.load( open( "measure_struc.p", "rb" ) )


# Run calibration
calibrated_wn = copy.deepcopy(wn)
# Add the conditional controls as time controls
calibrated_wn.conditional_controls = dict()
add_time_controls(calibrated_wn, stored.time_controls_dict)
network_cal =  PyomoSimulator(calibrated_wn)
network_cal._sim_duration_sec = run_time*60
network_cal._hydraulic_step_sec = time_step*60  

calibration_results = network_cal.run_calibration(stored.measurement_dict,
		weights =  {'tank_level':1.0, 'pressure':1.0,'head':1.0, 'flowrate':10000.0, 'demand':10000.0},
		external_link_statuses = stored.status_dict)
#		dma_dict=None,
#		dma_dict=dma_dict,
#		fix_base_demand=True)

#print "Error accumulation true demand\n",error1 
#print "Error accumulation true measurements\n",error2 

"""
print "\nDEMAND Differences\n"
printDifferences(calibration_results,stored.sim_results,'demand')
print "\nFLOWS Differences \n"
printDifferences(calibration_results,stored.sim_results,'flowrate')
"""
"""
true_measurements.plot_link_attribute(['VALVE-3890','VALVE-3891'],'flowrate',legend='true')
calibration_results.plot_link_attribute(['VALVE-3890','VALVE-3891'],'flowrate',legend='calib')
stored.sim_results.plot_link_attribute(['VALVE-3890','VALVE-3891'],'flowrate',legend='base')
plt.ylim(-0.01,0.05)
plt.show()
"""
"""
plt.figure()
if 'head' in calibration_results.node.columns:
	calibration_results.node['head'].plot(label='ESTIMATION')
stored.sim_results.node['head'].plot(label='SIM_ASSUMED_DEMAND')
if 'head' in stored.noise_sim_results.node.columns:
	stored.noise_sim_results.node['head'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Head')
plt.legend()

plt.figure()
if 'pressure' in calibration_results.node.columns:
	calibration_results.node['pressure'].plot(label='ESTIMATION')
stored.sim_results.node['pressure'].plot(label='SIM_ASSUMED_DEMAND')
if 'pressure' in stored.noise_sim_results.node.columns:
	stored.noise_sim_results.node['pressure'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Pressure')
plt.legend()

plt.figure()
if 'demand' in calibration_results.node.columns:
	calibration_results.node['demand'].plot(label='ESTIMATION')
stored.sim_results.node['demand'].plot(label='SIM_ASSUMED_DEMAND')
if 'demand' in stored.noise_sim_results.node.columns:
	stored.noise_sim_results.node['demand'].plot(label='SIM_TRUE_DEMAND')
plt.title('Node Demand')
plt.legend()

plt.figure()
calibration_results.link['flowrate'].plot(label='ESTIMATION')
stored.sim_results.link['flowrate'].plot(label='SIM_ASSUMED_DEMAND')
stored.noise_sim_results.link['flowrate'].plot(label='SIM_TRUE_DEMAND')
plt.title('Link Flowrate')
plt.legend()
plt.show()
"""




