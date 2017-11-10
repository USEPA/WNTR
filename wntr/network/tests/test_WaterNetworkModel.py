from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','tests','networks_for_testing')
net1dir = join(testdir,'..','..','..','examples','networks')
packdir = join(testdir,'..','..','..')

epanet_unit_id = {'CFS': 0, 'GPM': 1, 'MGD': 2, 'IMGD': 3, 'AFD': 4,
                  'LPS': 5, 'LPM': 6, 'MLD': 7, 'CMH':  8, 'CMD': 9}

def test_Net1():
    inp_file = join(net1dir,'Net1.inp')

    parser = wntr.epanet.InpFile()
    wn = parser.read(inp_file)

    G = wn.get_graph_deep_copy()

    node = G.node
    elevation = wn.query_node_attribute('elevation')
    base_demand = wn.query_node_attribute('base_demand')
    edge = G.adj
    diameter = wn.query_link_attribute('diameter')
    length = wn.query_link_attribute('length')

    # Data from the INP file, converted using flowunits
    expected_node = {'11': {'type': 'junction', 'pos': (30.0, 70.0)},
                     '10': {'type': 'junction', 'pos': (20.0, 70.0)},
                     '13': {'type': 'junction', 'pos': (70.0, 70.0)},
                     '12': {'type': 'junction', 'pos': (50.0, 70.0)},
                     '21': {'type': 'junction', 'pos': (30.0, 40.0)},
                     '22': {'type': 'junction', 'pos': (50.0, 40.0)},
                     '23': {'type': 'junction', 'pos': (70.0, 40.0)},
                     '32': {'type': 'junction', 'pos': (50.0, 10.0)},
                     '31': {'type': 'junction', 'pos': (30.0, 10.0)},
                     '2':  {'type': 'tank', 'pos': (50.0, 90.0)},
                     '9':  {'type': 'reservoir', 'pos': (10.0, 70.0)}}

    expected_elevation = {'11': 710.0,
                          '10': 710.0,
                          '13': 695.0,
                          '12': 700.0,
                          '21': 700.0,
                          '22': 695.0,
                          '23': 690.0,
                          '32': 710.0,
                          '31': 700.0,
                          '2':  850.0}
    expected_elevation = wntr.epanet.util.HydParam.Elevation._to_si(wn._inpfile.flow_units, expected_elevation)

    expected_base_demand = {'11': 150,
                            '10':   0,
                            '13': 100,
                            '12': 150,
                            '21': 150,
                            '22': 200,
                            '23': 150,
                            '32': 100,
                            '31': 100}
    expected_base_demand = wntr.epanet.util.HydParam.Demand._to_si(wn._inpfile.flow_units, expected_base_demand)

    expected_edge = {'11': {'12': {'11':  {'type': 'pipe'}},
                            '21': {'111': {'type': 'pipe'}}},
                     '10': {'11': {'10':  {'type': 'pipe'}}},
                     '13': {'23': {'113': {'type': 'pipe'}}},
                     '12': {'13': {'12':  {'type': 'pipe'}},
                            '22': {'112': {'type': 'pipe'}}},
                     '21': {'31': {'121': {'type': 'pipe'}},
                            '22': {'21':  {'type': 'pipe'}}},
                     '22': {'32': {'122': {'type': 'pipe'}},
                            '23': {'22':  {'type': 'pipe'}}},
                     '23': {},
                     '32': {},
                     '31': {'32': {'31':  {'type': 'pipe'}}},
                     '2':  {'12': {'110': {'type': 'pipe'}}},
                     '9':  {'10': {'9':   {'type': 'pump'}}}}

    expected_diameter = {'11':  14.0,
                         '111': 10.0,
                         '10':  18.0,
                         '113':  8.0,
                         '12':  10.0,
                         '112': 12.0,
                         '121':  8.0,
                         '21':  10.0,
                         '122':  6.0,
                         '22':  12.0,
                         '31':   6.0,
                         '110': 18.0}
    expected_diameter = wntr.epanet.util.HydParam.PipeDiameter._to_si(wn._inpfile.flow_units, expected_diameter)

    expected_length = {'11':  5280.0,
                       '111': 5280.0,
                       '10': 10530.0,
                       '113': 5280.0,
                       '12':  5280.0,
                       '112': 5280.0,
                       '121': 5280.0,
                       '21':  5280.0,
                       '122': 5280.0,
                       '22':  5280.0,
                       '31':  5280.0,
                       '110':  200.0}
    expected_length = wntr.epanet.util.HydParam.Length._to_si(wn._inpfile.flow_units, expected_length)

    assert_dict_equal(dict(node), expected_node)
    assert_dict_equal(elevation, expected_elevation)
    assert_dict_equal(base_demand, expected_base_demand)

    assert_dict_equal(dict(edge), expected_edge)
    assert_dict_equal(diameter, expected_diameter)
    assert_dict_equal(length, expected_length)

def test_query_node_attribute():
    inp_file = join(net1dir,'Net1.inp')

    parser = wntr.epanet.InpFile()
    wn = parser.read(inp_file)

    elevation = 213.36 #700*float(units.ft/units.m) # ft to m
    nodes = wn.query_node_attribute('elevation', np.less, elevation)

    expected_nodes = set(['13', '22', '23'])

    assert_set_equal(set(nodes.keys()), expected_nodes)

def test_query_pipe_attribute():
    inp_file = join(net1dir,'Net1.inp')

    parser = wntr.epanet.InpFile()
    wn = parser.read(inp_file)

    length = 1609.344 #5280*float(units.ft/units.m) # ft to m
    pipes = wn.query_link_attribute('length', np.greater, length)

    expected_pipes = set(['10'])

    assert_set_equal(set(pipes.keys()), expected_pipes)

def test_nzd_nodes():
    inp_file = join(net1dir,'Net1.inp')

    parser = wntr.epanet.InpFile()
    wn = parser.read(inp_file)

    nzd_nodes = wn.query_node_attribute('base_demand', np.greater, 0.0)

    expected_nodes = set(['11', '13', '12', '21', '22', '23', '32', '31'])

    assert_set_equal(set(nzd_nodes.keys()), expected_nodes)

def test_name_list():
    inp_file = join(net1dir,'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    assert_in('10', wn.junction_name_list)
    assert_in('1', wn.tank_name_list)
    assert_in('River', wn.reservoir_name_list)
    assert_in('20', wn.pipe_name_list)
    assert_in('10', wn.pump_name_list)
    assert_equal(0, len(wn.valve_name_list))
    assert_in('1', wn.pattern_name_list)
    assert_in('1', wn.curve_name_list)
    assert_equal(0, len(wn.source_name_list))
#    assert_equal(0, len(wn._demand_name_list))
    assert_in('LINK10OPENATTIME3600', wn.control_name_list)

def test_add_get_remove_num():
    inp_file = join(net1dir,'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    wn.add_junction('new_junc')
    wn.get_node('new_junc')
    
    wn.add_tank('new_tank')
    wn.get_node('new_tank')
    
    wn.add_reservoir('new_reservoir')
    wn.get_node('new_reservoir')
    
    wn.add_pipe('new_pipe', '139', '131')
    wn.get_link('new_pipe')
    
    wn.add_pump('new_pump', '139', '131')
    wn.get_link('new_pump')
    
    wn.add_valve('new_valve', '139', '131')
    wn.get_link('new_valve')
    
    wn.add_pattern('new_pattern', [])
    wn.get_pattern('new_pattern')
    
    wn.add_curve('new_curve', 'HEAD', [])
    wn.get_curve('new_curve')
    
    wn.add_source('new_source', 'new_junc', 'CONCEN', 1, 'new_pattern')
    wn.get_source('new_source')
    
    nums = [wn.num_junctions,
           wn.num_tanks,
           wn.num_reservoirs,
           wn.num_pipes,
           wn.num_pumps,
           wn.num_valves,
           wn.num_patterns,
           wn.num_curves,
           wn.num_sources]
    expected = [93,4,3,118,3,1,6,3,1]
    assert_list_equal(nums, expected)
    
    wn.remove_node('new_junc')
    wn.remove_node('new_tank')
    wn.remove_node('new_reservoir')
    wn.remove_link('new_pipe')
    wn.remove_link('new_pump')
    wn.remove_link('new_valve')
    wn.remove_pattern('new_pattern')
    wn.remove_curve('new_curve')
    wn.remove_source('new_source')
    
    nums = [wn.num_junctions,
           wn.num_tanks,
           wn.num_reservoirs,
           wn.num_pipes,
           wn.num_pumps,
           wn.num_valves,
           wn.num_patterns,
           wn.num_curves,
           wn.num_sources]
    expected = [92,3,2,117,2,0,5,2,0]
    assert_list_equal(nums, expected)