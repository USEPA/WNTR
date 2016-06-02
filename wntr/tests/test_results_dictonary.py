import pandas as pd
import numpy as np
import time
#from memory_profiler import profile
from nose.tools import *

@nottest
#@profile 
def test_results_dictonary(nnodes=100, ntimes=50, use_timedelta=False): 

    t0 = time.time()
    
    if use_timedelta:
        time_slice = pd.Timedelta(seconds = 5)
        time_index = pd.to_timedelta(np.arange(1,ntimes+1,1), unit='s')
    else:
        time_slice = 5
        time_index = np.arange(1,ntimes+1,1)
    
    node_index = np.arange(1,nnodes+1,1)
    
    node_times = []
    node_name = []
    node_demand = []
    node_expected_demand = []
    node_head = []
    node_pressure = []
    node_quality = []
    node_type = []
    
    # Simulators loop through time then nodes to gather results
    for t in time_index:
        for n in node_index:
                
            node_times.append(t)
            node_name.append(n)
            node_demand.append(1)
            node_expected_demand.append(2)
            node_head.append(3)
            node_pressure.append(4)
            node_quality.append(5)
            node_type.append('junction')    
    
    epanet_sim_results = {}
    epanet_sim_results['node_name'] = node_name
    epanet_sim_results['node_type'] = node_type
    epanet_sim_results['node_times'] = node_times
    epanet_sim_results['node_head'] = node_head
    epanet_sim_results['node_demand'] = node_demand
    epanet_sim_results['node_expected_demand'] = node_expected_demand
    epanet_sim_results['node_pressure'] = node_pressure
    epanet_sim_results['node_quality'] = node_quality

    node_dict = dict()
    node_types = set(epanet_sim_results['node_type'])
    map_properties = dict()
    map_properties['node_demand'] = 'demand'
    map_properties['node_head'] = 'head'
    map_properties['node_pressure'] = 'pressure'
    map_properties['node_quality'] = 'quality'
    map_properties['node_expected_demand'] = 'expected_demand'
    N = len(epanet_sim_results['node_name'])
    n_nodes = nnodes
    T = N/n_nodes
    print T
    for node_type in node_types:
        node_dict[node_type] = dict()
        for prop, prop_name in map_properties.iteritems():
            node_dict[node_type][prop_name] = dict()
            for i in xrange(n_nodes):
                node_name = epanet_sim_results['node_name'][i]
                n_type = 'Node'
                if n_type == node_type:
                    node_dict[node_type][prop_name][node_name] = dict()
                    for ts in xrange(T):
                        time_sec = ts
                        #print i+n_nodes*ts
                        node_dict[node_type][prop_name][node_name][time_sec] = epanet_sim_results[prop][i+n_nodes*ts]

    # Index into dict
    #pressure_at_5hr = ???
    #pressure_at_node1 = ???
    #pressure_data = node_dict['pressure']
    #node1_data = ???
    #node1_data_at_5hr = ???
    
    t1 = time.time()
    print 'dictonary time: ',t1-t0

    return node_dict
    
if __name__ == '__main__':
    nnodes = 100
    ntimes = 50
    use_timedelta = False

    node_dict = test_results_dictonary(nnodes, ntimes, use_timedelta)
    
    
