import pandas as pd
import numpy as np
import wntr
import networkx as nx

#@profile 
def test_pandas_pivottable(nnodes, ntimes, use_timedelta): 
    
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
            node_demand.append(np.random.rand())
            node_expected_demand.append(np.random.rand())
            node_head.append(np.random.rand())
            node_pressure.append(np.random.rand())
            node_quality.append(np.random.rand())
            node_type.append(np.random.rand())    
        
    node_dictonary = {'time': node_times,
                       'node': node_name,
                       'demand': node_demand,
                       'expected_demand': node_expected_demand,
                       'head': node_head,
                       'pressure': node_pressure,
                       'quality': node_quality,
                       'type': node_type}
                                   
    node_data_frame = pd.DataFrame(node_dictonary)
    
    node_pivot_table = pd.pivot_table(node_data_frame,
                      values=['demand', 'expected_demand', 'head', 'pressure', 'quality', 'type'],
                      index=['node', 'time'],
                      aggfunc= lambda x: x)
    
    # Index into pivot table
    pressure_at_5hr = node_pivot_table.loc[(slice(None), time_slice), 'pressure'] # returns a multiindex pd.Series
    pressure_at_node1 = node_pivot_table.loc[(1, slice(None)), 'pressure'] # returns a multiindex pd.Series
    pressure_data = node_pivot_table['pressure'] # returns a multiindex pd.Series
    node1_data = node_pivot_table.loc[(1, slice(None)), :] # returns a multiindex pd.Series
    node1_data_at_5hr = node1_data.loc[(1,time_slice),:] # returns pd.Series

if __name__ == '__main__':
    nnodes = 100
    ntimes = 50
    use_timedelta = True

    test_pandas_pivottable(nnodes, ntimes, use_timedelta)