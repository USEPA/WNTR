import pandas as pd
import numpy as np
import time
from memory_profiler import profile
from nose.tools import *

@nottest
@profile 
def test_pandas_panels(nnodes=100, ntimes=50, use_timedelta=False): 

    t0 = time.time()

    if use_timedelta:
        time_slice = pd.Timedelta(seconds = 5)
        time_index = pd.to_timedelta(np.arange(1,ntimes+1,1), unit='s')
    else:
        time_slice = 5
        time_index = np.arange(1,ntimes+1,1)
    
    node_index = np.arange(1,nnodes+1,1)
    
    node_demand = np.zeros((ntimes,nnodes))
    node_expected_demand = np.zeros((ntimes,nnodes))
    node_head = np.zeros((ntimes,nnodes))
    node_pressure = np.zeros((ntimes,nnodes))
    node_quality = np.zeros((ntimes,nnodes))
    node_type = np.zeros((ntimes,nnodes))
    
    # Simulators loop through time then nodes to gather results
    for t in range(len(time_index)):
        for n in range(len(node_index)):
    
            node_demand[t][n] = np.random.rand()
            node_expected_demand[t][n] = np.random.rand()
            node_head[t][n] = np.random.rand()
            node_pressure[t][n] = np.random.rand()
            node_quality[t][n] = np.random.rand()
            node_type[t][n] = np.random.rand()
    
    node_dictonary = {'demand': node_demand,
                      'expected_demand': node_expected_demand,
                      'head': node_head,
                      'pressure': node_pressure,
                      'quality': node_quality,
                      'type': node_type}   
     
    node_panel = pd.Panel(node_dictonary, major_axis=time_index, minor_axis=node_index)
    
    # Index into panel
    pressure_at_5hr = node_panel.loc['pressure', :, time_slice] # returns pd.Series
    pressure_at_node1 = node_panel.loc['pressure', 1, :] # returns pd.Series
    pressure_data = node_panel['pressure'] # returns pd.Dataframe
    node1_data = node_panel.loc[:,1,:] # returns pd.Dataframe
    node1_data_at_5hr = node1_data.loc[time_slice,:] # returns pd.Series
    
    t1 = time.time()
    print 'panel time: ',t1-t0

if __name__ == '__main__':
    nnodes = 100
    ntimes = 50
    use_timedelta = False

    test_pandas_panels(nnodes, ntimes, use_timedelta)
    
    
