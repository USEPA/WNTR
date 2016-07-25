from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','tests','networks_for_testing')
net1dir = join(testdir,'..','..','..','examples','networks')
packdir = join(testdir,'..','..','..')

def test_terminal_nodes():
    inp_file = join(net1dir,'Net1.inp')
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)

    G = wn.get_graph_deep_copy()
    terminal_nodes = G.terminal_nodes()
    
    expected_nodes = ['2', '9']
    
    assert_list_equal(terminal_nodes, expected_nodes)

def test_Net1_MultiDiGraph():
    inp_file = join(net1dir,'Net1.inp') 
    wn = wntr.network.WaterNetworkModel(inp_file)
    G = wn.get_graph_deep_copy()

    node = {'11': {'pos': (30.0, 70.0),'type': 'junction'}, 
            '10': {'pos': (20.0, 70.0),'type': 'junction'}, 
            '13': {'pos': (70.0, 70.0),'type': 'junction'}, 
            '12': {'pos': (50.0, 70.0),'type': 'junction'}, 
            '21': {'pos': (30.0, 40.0),'type': 'junction'}, 
            '22': {'pos': (50.0, 40.0),'type': 'junction'}, 
            '23': {'pos': (70.0, 40.0),'type': 'junction'}, 
            '32': {'pos': (50.0, 10.0),'type': 'junction'}, 
            '31': {'pos': (30.0, 10.0),'type': 'junction'}, 
            '2':  {'pos': (50.0, 90.0),'type': 'tank'},
            '9':  {'pos': (10.0, 70.0),'type': 'reservoir'}}
            
    edge = {'11': {'12': {'11':  {'type': 'pipe'}}, 
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

    assert_dict_contains_subset(node, G.node)
    assert_dict_contains_subset(edge, G.edge)
    
if __name__ == '__main__':
    test_Net1()
