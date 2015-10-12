from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','tests','networks_for_testing')
packdir = join(testdir,'..','..','..')

def test_terminal_nodes():
    inp_file = join(datadir,'Net1.inp')
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)

    G = wn.get_graph_deep_copy()
    terminal_nodes = G.terminal_nodes()
    
    expected_nodes = ['2', '9']
    
    assert_list_equal(terminal_nodes, expected_nodes)

if __name__ == '__main__':
    test_terminal_nodes()
