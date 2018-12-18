from nose.tools import *
from nose import SkipTest
from os.path import abspath, dirname, join
import numpy as np
import pandas as pd
import networkx as nx
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'networks_for_testing')
netdir = join(testdir,'..','..','examples','networks')

def test_skeletonize():
    inp_file = join(datadir, 'skeletonize.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    expected_total_demand = 0.000763391376  # 12.1 GPM

    expected_nums = pd.DataFrame(index=[0,4,8,12,24,36], columns=['num_nodes', 'num_links'])
    expected_nums.loc[0,:] = [wn.num_nodes, wn.num_links]
    expected_nums.loc[4,:] = [wn.num_nodes-5, wn.num_links-5]
    expected_nums.loc[8,:] = [wn.num_nodes-15, wn.num_links-18]
    expected_nums.loc[12,:] = [wn.num_nodes-21, wn.num_links-26]
    expected_nums.loc[24,:] = [wn.num_nodes-25, wn.num_links-30]
    expected_nums.loc[36,:] = [wn.num_nodes-29, wn.num_links-34]
    
    for i in [0,4,8,12,24,36]:
        skel_wn, skel_map = wntr.network.morph.skeletonize(wn, i*0.0254, return_map=True)
        
        demand =  wntr.metrics.expected_demand(skel_wn)
        total_demand = demand.loc[0,:].sum()
        
        #pipes = wn.query_link_attribute('diameter', np.less_equal, i*0.0254)
        #wntr.graphics.plot_network(wn, link_attribute = list(pipes.keys()), title=str(i))
        #wntr.graphics.plot_network(skel_wn, link_attribute='diameter', link_width=2, node_size=15, title=str(i))
        
        assert_almost_equal(total_demand.sum(), expected_total_demand,6)
        assert_equal(skel_wn.num_nodes, expected_nums.loc[i,'num_nodes'])
        assert_equal(skel_wn.num_links, expected_nums.loc[i,'num_links'])
        
        if i == 0:
            expected_map = {} # 1:1 map
            for name in wn.node_name_list:
                expected_map[name] = [name]
            assert_dict_contains_subset(expected_map, skel_map)
        
        if i == 4:
            expected_map_subset = {}
            expected_map_subset['15'] = ['15', '14', '16']
            expected_map_subset['30'] = ['30', '32']
            expected_map_subset['56'] = ['56', '57']
            expected_map_subset['59'] = ['59', '64']
            expected_map_subset['14'] = []
            expected_map_subset['16'] = []
            expected_map_subset['32'] = []
            expected_map_subset['57'] = []
            expected_map_subset['64'] = []
            assert_dict_contains_subset(expected_map_subset, skel_map)

def test_skeletonize_with_controls():
    inp_file = join(datadir, 'skeletonize.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    # add controls
    action = wntr.network.ControlAction(wn.get_link('60'), 'status', wntr.network.LinkStatus.Closed)
    condition = wntr.network.SimTimeCondition(wn, '==', 0)
    control = wntr.network.Control(condition=condition, then_action=action)
    wn.add_control('close_valve', control)
    
    skel_wn = wntr.network.morph.skeletonize(wn, 12*0.0254)
    
    #pipes = wn.query_link_attribute('diameter', np.less_equal, 12*0.0254)
    #wntr.graphics.plot_network(wn, link_attribute = list(pipes.keys()))
    #wntr.graphics.plot_network(skel_wn, link_attribute='diameter', link_width=2, node_size=15)
    
    assert_equal(skel_wn.num_nodes, 20)
    assert_equal(skel_wn.num_links, 24)
        
    # TODO: finish test
    
def test_series_merge_properties():
    wn = wntr.network.WaterNetworkModel()
    
    wn.add_junction('J1', base_demand=5, elevation=100.0, coordinates=(0,0))
    wn.add_junction('J2', base_demand=8, elevation=50.0, coordinates=(1,0))
    wn.add_junction('J3', base_demand=5, elevation=25.0, coordinates=(2,0))
    wn.add_pipe('P12', 'J1', 'J2', length=350, diameter=8, 
                roughness=120, minor_loss=0.1, status='OPEN')
    wn.add_pipe('P23', 'J2', 'J3', length=250, diameter=6, 
                roughness=80, minor_loss=0.0, status='CLOSED')
    
    # Add a source
    wn.add_reservoir('R', base_head=125, coordinates=(0,2))
    wn.add_pipe('PR', 'R', 'J1', length=100, diameter=12, roughness=100,
                minor_loss=0.0, status='OPEN')
    
    wn.options.time.duration = 0
    
    skel_wn = wntr.network.morph.skeletonize(wn, 8, branch_trim=False, 
            series_pipe_merge=True, parallel_pipe_merge=False, max_iterations=1)
    
    link = skel_wn.get_link('P12') # pipe P12 is the dominant pipe
    
    assert_equal(link.length, 600)
    assert_equal(link.diameter, 8)
    assert_almost_equal(link.roughness, 55, 0)
    assert_equal(link.minor_loss, 0.1)
    assert_equal(link.status, 1) # open

def test_parallel_merge_properties():
    wn = wntr.network.WaterNetworkModel()
    
    wn.add_junction('J1', base_demand=5, elevation=100.0, coordinates=(0,0))
    wn.add_junction('J2', base_demand=8, elevation=50.0, coordinates=(1,0))
    wn.add_pipe('P12a', 'J1', 'J2', length=280, diameter=250, 
                roughness=120, minor_loss=0.1, status='OPEN')
    wn.add_pipe('P12b', 'J1', 'J2', length=220, diameter=300, 
                roughness=100, minor_loss=0, status='CLOSED')
    # Add a source
    wn.add_reservoir('R', base_head=125, coordinates=(0,2))
    wn.add_pipe('PR', 'R', 'J1', length=100, diameter=450, roughness=100,
                minor_loss=0.0, status='OPEN')
    
    wn.options.time.duration = 0
    
    skel_wn = wntr.network.morph.skeletonize(wn, 300, branch_trim=False, 
            series_pipe_merge=False, parallel_pipe_merge=True, max_iterations=1)

    link = skel_wn.get_link('P12b') # pipe P12b is the dominant pipe
    
    assert_equal(link.length, 220)
    assert_equal(link.diameter, 300)
    assert_almost_equal(link.roughness, 165, 0)
    assert_equal(link.minor_loss, 0)
    assert_equal(link.status, 0) # closed
    
if __name__ == '__main__':
    #test_skeletonize()
    test_skeletonize_with_controls()
    #test_series_merge_properties()
    #test_parallel_merge_properties()
    

