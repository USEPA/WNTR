from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
#from sympy.physics import units
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','tests','networks_for_testing')
net1dir = join(testdir,'..','..','..','examples','networks')
packdir = join(testdir,'..','..','..')

epanet_unit_id = {'CFS': 0, 'GPM': 1, 'MGD': 2, 'IMGD': 3, 'AFD': 4,
                  'LPS': 5, 'LPM': 6, 'MLD': 7, 'CMH':  8, 'CMD': 9}
                  
def test_Net1():
    inp_file = join(net1dir,'Net1.inp') 
    
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    G = wn.get_graph_deep_copy()
    
    node = G.node
    elevation = wn.query_node_attribute('elevation')
    base_demand = wn.query_node_attribute('base_demand')
    edge = G.edge
    diameter = wn.query_link_attribute('diameter')
    length = wn.query_link_attribute('length')

    # Data from the INP file, converted using flowunits
    flowunits = epanet_unit_id[wn.options.units]
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
    expected_elevation = wntr.utils.convert('Elevation', flowunits, expected_elevation)
    
    expected_base_demand = {'11': 150, 
                            '10':   0, 
                            '13': 100, 
                            '12': 150, 
                            '21': 150, 
                            '22': 200, 
                            '23': 150, 
                            '32': 100, 
                            '31': 100}
    expected_base_demand = wntr.utils.convert('Demand', flowunits, expected_base_demand)
    
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
    expected_diameter = wntr.utils.convert('Pipe Diameter', flowunits, expected_diameter)
    
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
    expected_length = wntr.utils.convert('Length', flowunits, expected_length)
            
    assert_dict_equal(node, expected_node)
    assert_dict_equal(elevation, expected_elevation)
    assert_dict_equal(base_demand, expected_base_demand)
    
    assert_dict_equal(edge, expected_edge)
    assert_dict_equal(diameter, expected_diameter)
    assert_dict_equal(length, expected_length)
    
def test_query_node_attribute():
    inp_file = join(net1dir,'Net1.inp') 
    
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    elevation = 213.36 #700*float(units.ft/units.m) # ft to m
    nodes = wn.query_node_attribute('elevation', np.less, elevation)
    
    expected_nodes = ['13', '22', '23']
    
    assert_list_equal(nodes.keys(), expected_nodes)

def test_query_pipe_attribute():
    inp_file = join(net1dir,'Net1.inp') 
    
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    length = 1609.344 #5280*float(units.ft/units.m) # ft to m
    pipes = wn.query_link_attribute('length', np.greater, length)
    
    expected_pipes = ['10']
    
    assert_list_equal(pipes.keys(), expected_pipes)

def test_nzd_nodes():
    inp_file = join(net1dir,'Net1.inp') 
    
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    nzd_nodes = wn.query_node_attribute('base_demand', np.greater, 0.0)
    
    expected_nodes = ['11', '13', '12', '21', '22', '23', '32', '31']
    
    assert_list_equal(nzd_nodes.keys(), expected_nodes)
    
if __name__ == '__main__':
    test_Net1()
