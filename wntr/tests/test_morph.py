from nose.tools import *
from nose import SkipTest
import sys
from os.path import abspath, dirname, join
import pandas as pd
import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'networks_for_testing')
netdir = join(testdir,'..','..','examples','networks')

def test_scale_node_coordinates():
    
    inp_file = join(netdir, 'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    node = wn.get_node('123')
    coord = node.coordinates
    
    wn2 = wntr.morph.scale_node_coordinates(wn, 100)
    node2 = wn2.get_node('123')
    coord2 = node2.coordinates
    
    assert_equal(coord[0]*100, coord2[0])
    assert_equal(coord[1]*100, coord2[1])
    
    
def test_translate_node_coordinates():
    
    inp_file = join(netdir, 'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    node = wn.get_node('123')
    coord = node.coordinates
    
    wn2 = wntr.morph.translate_node_coordinates(wn, 5,10)
    node2 = wn2.get_node('123')
    coord2 = node2.coordinates
    
    assert_equal(coord[0]+5, coord2[0])
    assert_equal(coord[1]+10, coord2[1])
    

def test_rotate_node_coordinates():
    
    wn = wntr.network.WaterNetworkModel()
    wn.add_junction('J1', base_demand=5, elevation=100.0, coordinates=(2,0))
    
    wn2 = wntr.morph.rotate_node_coordinates(wn, 45)
    node2 = wn2.get_node('J1')
    coord2 = node2.coordinates
    
    assert_almost_equal(np.sqrt(2), coord2[0], 6)
    assert_almost_equal(np.sqrt(2), coord2[1], 6)


def test_UTM_to_latlong_to_UTM():
    
    if (sys.version_info.major == 3) and (sys.version_info.minor == 4):
        raise SkipTest # skip if python version == 3.4 (for utm)
        
    wn = wntr.network.WaterNetworkModel()
    wn.add_junction('J1', base_demand=5, elevation=100.0, 
                    coordinates=(351521.07,3886097.33))
    
    wn2 = wntr.morph.convert_node_coordinates_UTM_to_latlong(wn, 13, 'S')
    node2 = wn2.get_node('J1')
    coord2 = node2.coordinates
    
    assert_almost_equal(35.106766, coord2[0], 6)
    assert_almost_equal(-106.629181, coord2[1], 6)
    
    wn3 = wntr.morph.convert_node_coordinates_latlong_to_UTM(wn2)
    node3 = wn3.get_node('J1')
    coord3 = node3.coordinates
    
    assert_almost_equal(351521.07, coord3[0], 1)
    assert_almost_equal(3886097.33, coord3[1], 1)


def test_convert_node_coordinates_to_latlong():
    
    if (sys.version_info.major == 3) and (sys.version_info.minor == 4):
        raise SkipTest # skip if python version == 3.4 (for utm)
        
    inp_file = join(netdir, 'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    latlong_map = {'Lake':(35.0623, -106.6587), 
                   '219': (35.1918, -106.5248)}
    
    wn2 = wntr.morph.convert_node_coordinates_to_latlong(wn, latlong_map)
    
    for node_name in latlong_map.keys():
        node = wn2.get_node(node_name)
        coord = node.coordinates
        print(coord)
        assert_almost_equal(latlong_map[node_name][0], coord[0], 4)
        assert_almost_equal(latlong_map[node_name][1], coord[1], 4)
    
    
def test_split_pipe():
        
    inp_file = join(datadir, 'leaks.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    wn = wntr.morph.split_pipe(wn,'pipe1','pipe1__B','leak1')
    
    pipe = wn.get_link('pipe1')
    pipeB = wn.get_link('pipe1__B')
    
    assert_equal(True, 'leak1' in [name for name,n in wn.nodes()])
    assert_equal(True, 'leak1' in [name for name,n in wn.nodes(wntr.network.Junction)])
    assert_equal(True, 'pipe1' in [name for name,l in wn.links()])
    assert_equal(True, 'pipe1' in [name for name,l in wn.links(wntr.network.Pipe)])
    assert_equal(True, 'pipe1__B' in [name for name,l in wn.links()])
    assert_equal(True, 'pipe1__B' in [name for name,l in wn.links(wntr.network.Pipe)])
    assert_equal(pipe.end_node_name, 'leak1')
    assert_equal(pipeB.start_node_name, 'leak1')
    assert_equal(pipe.diameter, pipeB.diameter)
    assert_equal(pipe.roughness, pipeB.roughness)
    assert_equal(pipe.minor_loss, pipeB.minor_loss)
    assert_equal(pipe.initial_status, pipeB.initial_status)


def test_break_pipe():
        
    inp_file = join(datadir, 'leaks.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    wn = wntr.morph.break_pipe(wn,'pipe1','pipe1__B','leak1','leak2')
    
    pipe = wn.get_link('pipe1')
    pipeB = wn.get_link('pipe1__B')
    
    assert_equal(True, 'leak1' in [name for name,n in wn.nodes()])
    assert_equal(True, 'leak1' in [name for name,n in wn.nodes(wntr.network.Junction)])
    assert_equal(True, 'leak2' in [name for name,n in wn.nodes()])
    assert_equal(True, 'leak2' in [name for name,n in wn.nodes(wntr.network.Junction)])
    assert_equal(True, 'pipe1' in [name for name,l in wn.links()])
    assert_equal(True, 'pipe1' in [name for name,l in wn.links(wntr.network.Pipe)])
    assert_equal(True, 'pipe1__B' in [name for name,l in wn.links()])
    assert_equal(True, 'pipe1__B' in [name for name,l in wn.links(wntr.network.Pipe)])
    assert_equal(pipe.end_node_name, 'leak1')
    assert_equal(pipeB.start_node_name, 'leak2')
    assert_equal(pipe.diameter, pipeB.diameter)
    assert_equal(pipe.roughness, pipeB.roughness)
    assert_equal(pipe.minor_loss, pipeB.minor_loss)
    assert_equal(pipe.initial_status, pipeB.initial_status)
    
    
def test_skeletonize():
    
    inp_file = join(datadir, 'skeletonize.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    expected_total_demand = 12.1/264.172/60  # 12.1 GPM converted to m3/s

    expected_nums = pd.DataFrame(index=[0,4,8,12,24,36], columns=['num_nodes', 'num_links'])
    expected_nums.loc[0,:] = [wn.num_nodes, wn.num_links]
    expected_nums.loc[4,:] = [wn.num_nodes-5, wn.num_links-5]
    expected_nums.loc[8,:] = [wn.num_nodes-15, wn.num_links-18]
    expected_nums.loc[12,:] = [wn.num_nodes-21, wn.num_links-26]
    expected_nums.loc[24,:] = [wn.num_nodes-25, wn.num_links-30]
    expected_nums.loc[36,:] = [wn.num_nodes-29, wn.num_links-34]
    
    for i in [0,4,8,12,24,36]:
        skel_wn, skel_map = wntr.morph.skeletonize(wn, float(i)*0.0254, return_map=True, use_epanet=False)
        
        demand =  wntr.metrics.expected_demand(skel_wn)
        total_demand = demand.loc[0,:].sum()
        
        # Write skel_wn to an inp file, read it back in, then extract the demands
        skel_inp_file = 'skel_'+str(i)+'.inp'
        skel_wn.write_inpfile(skel_inp_file, 'GPM')
        skel_wn_io = wntr.network.WaterNetworkModel(skel_inp_file)
        demand_io =  wntr.metrics.expected_demand(skel_wn_io)
        total_demand_io = demand_io.loc[0,:].sum()

        #pipes = wn.query_link_attribute('diameter', np.less_equal, i*0.0254)
        #wntr.graphics.plot_network(wn, link_attribute = list(pipes.keys()), title=str(i))
        #wntr.graphics.plot_network(skel_wn, link_attribute='diameter', link_width=2, node_size=15, title=str(i))
        
        assert_almost_equal(total_demand.sum(), expected_total_demand,6)
        assert_almost_equal(total_demand_io.sum(), expected_total_demand,6)
        
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

    # add control to a link
    action = wntr.network.ControlAction(wn.get_link('60'), 'status', wntr.network.LinkStatus.Closed)
    condition = wntr.network.SimTimeCondition(wn, '==', 0)
    control = wntr.network.Control(condition=condition, then_action=action)
    wn.add_control('close_valve', control)
    
    # add control to a node
    action = wntr.network.ControlAction(wn.get_node('13'), 'elevation', 1)
    condition = wntr.network.SimTimeCondition(wn, '==', 0)
    control = wntr.network.Control(condition=condition, then_action=action)
    wn.add_control('raise_node', control)
    
    skel_wn = wntr.morph.skeletonize(wn, 12.0*0.0254, use_epanet=False)
    
    assert_equal(skel_wn.num_nodes, wn.num_nodes-17)
    assert_equal(skel_wn.num_links, wn.num_links-22)
    
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    # Change link 60 and 11 diameter to > 12, should get some results as above
    link = wn.get_link('60')
    link.diameter = 16*0.0254
    link = wn.get_link('11')
    link.diameter = 16*0.0254
    
    skel_wn = wntr.morph.skeletonize(wn, 12.0*0.0254, use_epanet=False)
    
    assert_equal(skel_wn.num_nodes, wn.num_nodes-17)
    assert_equal(skel_wn.num_links, wn.num_links-22)
    
    
def test_series_merge_properties():
    
    wn = wntr.network.WaterNetworkModel()
    
    wn.add_junction('J1', base_demand=5, elevation=100.0, coordinates=(0,0))
    wn.add_junction('J2', base_demand=8, elevation=50.0, coordinates=(1,0))
    wn.add_junction('J3', base_demand=5, elevation=25.0, coordinates=(2,0))
    wn.add_pipe('P12', 'J1', 'J2', length=350, diameter=8, 
                roughness=120, minor_loss=0.1, status='OPEN')
    wn.add_pipe('P23', 'J2', 'J3', length=250, diameter=6, 
                roughness=80, minor_loss=0.0, status='OPEN')
    
    # Add a source
    wn.add_reservoir('R', base_head=125, coordinates=(0,2))
    wn.add_pipe('PR', 'R', 'J1', length=100, diameter=12, roughness=100,
                minor_loss=0.0, status='OPEN')
    
    wn.options.time.duration = 0
    
    skel_wn = wntr.morph.skeletonize(wn, 8, branch_trim=False, 
            series_pipe_merge=True, parallel_pipe_merge=False, max_cycles=1, use_epanet=False)
    
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
                roughness=100, minor_loss=0, status='OPEN')
    # Add a source
    wn.add_reservoir('R', base_head=125, coordinates=(0,2))
    wn.add_pipe('PR', 'R', 'J1', length=100, diameter=450, roughness=100,
                minor_loss=0.0, status='OPEN')
    
    wn.options.time.duration = 0
    
    skel_wn = wntr.morph.skeletonize(wn, 300, branch_trim=False, 
            series_pipe_merge=False, parallel_pipe_merge=True, max_cycles=1, use_epanet=False)

    link = skel_wn.get_link('P12b') # pipe P12b is the dominant pipe
    
    assert_equal(link.length, 220)
    assert_equal(link.diameter, 300)
    assert_almost_equal(link.roughness, 165, 0)
    assert_equal(link.minor_loss, 0)
    assert_equal(link.status, 1) # open
    
    
def test_skeletonize_Net3():
    
    inp_file = join(netdir, 'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    skel_wn = wntr.morph.skeletonize(wn, 36.0*0.0254, use_epanet=False)
    
    assert_equal(wn.num_junctions, 92)
    assert_equal(skel_wn.num_junctions, 45)
    
    sim = wntr.sim.WNTRSimulator(wn)
    results_original = sim.run_sim()
    
    sim = wntr.sim.WNTRSimulator(skel_wn)
    results_skel = sim.run_sim()
    
    skel_junctions = skel_wn.junction_name_list
    
    pressure_orig = results_original.node['pressure'].loc[:,skel_junctions]
    pressure_skel = results_skel.node['pressure'].loc[:,skel_junctions]
    pressure_diff = abs(pressure_orig - pressure_skel)
    pressure_diff.index = pressure_diff.index/3600
    
    m50 = pressure_diff.quantile(0.50, axis=1)
    
    """
    import matplotlib.pylab as plt
    wntr.graphics.plot_network(wn, title='Original')
    wntr.graphics.plot_network(skel_wn, title='Skeletonized')
    plt.figure()
    m50.plot()
    print(m50.mean())
    """
    assert_less(m50.max(), 1.5)
    assert_less(m50.mean(), 0.15)

    
if __name__ == '__main__':
    test_skeletonize()

