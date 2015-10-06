import pandas as pd
import numpy as np
import time
from memory_profiler import profile
from nose.tools import *

@nottest
#@profile 
def test_pandas_panels(nnodes=100, ntimes=50, flag='PANEL', use_timedelta=False): 

    t0 = time.time()

    if use_timedelta:
        time_slice = pd.Timedelta(seconds = 5)
        time_index = pd.to_timedelta(np.arange(1,ntimes+1,1), unit='s')
    else:
        time_slice = 5
        time_index = np.arange(1,ntimes+1,1)
    
    node_index = np.arange(1,nnodes+1,1)
    node_names = ['Node' + str(n) for n in node_index]
    
    if flag is 'PANEL':
        node_panel = pd.Panel(items=['demand', 'expected_demand', 'head', 'pressure', 'quality', 'type'], major_axis=node_index, minor_axis=node_names, dtype='object')
    
    if flag is 'ARRAY':
        nan_array = np.empty((ntimes,nnodes), dtype='object')
        nan_array[:] = np.nan
        node_dictonary = {'demand': nan_array,
                          'expected_demand': nan_array,
                          'head': nan_array ,
                          'pressure': nan_array,
                          'quality': nan_array,
                          'type': nan_array}
    if flag is 'LIST':
        node_dictonary = {'demand': [],
                          'expected_demand': [],
                          'head': [] ,
                          'pressure': [],
                          'quality': [],
                          'type': []}
                              
                      
    # Simulators loop through time then nodes to gather results
    for t_count, t in enumerate(time_index):
        for n_count, name in enumerate(node_names):
            
            if flag is 'PANEL':
                node_panel.set_value('demand', t, name, 1)
                node_panel.set_value('expected_demand', t, name, 2)
                node_panel.set_value('head', t, name, 3)
                node_panel.set_value('pressure', t, name, 4)
                node_panel.set_value('quality', t, name, 5)
                node_panel.set_value('type', t, name, 'junction')
                
            if flag is 'ARRAY':
                node_dictonary['demand'][t_count][n_count] = 1
                node_dictonary['expected_demand'][t_count][n_count] = 2
                node_dictonary['head'][t_count][n_count] = 3
                node_dictonary['pressure'][t_count][n_count] = 4
                node_dictonary['quality'][t_count][n_count] = 5
                node_dictonary['type'][t_count][n_count] = 'junction'
            
            if flag is 'LIST':
                node_dictonary['demand'].append(1)
                node_dictonary['expected_demand'].append(2)
                node_dictonary['head'].append(3)
                node_dictonary['pressure'].append(4)
                node_dictonary['quality'].append(5)
                node_dictonary['type'].append('junction')
                
            
    if flag is 'ARRAY':
        node_panel = pd.Panel(node_dictonary, major_axis=time_index, minor_axis=node_names)
    
    if flag is 'LIST':
        for key, value in node_dictonary.iteritems():
            node_dictonary[key] = np.array(value).reshape((ntimes, nnodes))
        node_panel = pd.Panel(node_dictonary, major_axis=time_index, minor_axis=node_names)

    
    # Index into panel
    pressure_at_5hr = node_panel.loc['pressure', time_slice, :] # returns pd.Series
    pressure_at_node1 = node_panel.loc['pressure', :, 'Node1'] # returns pd.Series
    pressure_data = node_panel['pressure'] # returns pd.Dataframe
    node1_data = node_panel.loc[:,:,'Node1'] # returns pd.Dataframe
    node1_data_at_5hr = node1_data.loc[time_slice,:] # returns pd.Series
    
    t1 = time.time()
    print 'panel time: ',t1-t0, ' ', flag

    return node_panel
    
if __name__ == '__main__':
    nnodes = 100 
    ntimes = 50
    use_timedelta = False

    node_panel = test_pandas_panels(nnodes, ntimes, 'PANEL', use_timedelta)
    node_panel = test_pandas_panels(nnodes, ntimes, 'ARRAY', use_timedelta) # panel from np.array
    node_panel = test_pandas_panels(nnodes, ntimes, 'LIST', use_timedelta) # panel from lists
    
