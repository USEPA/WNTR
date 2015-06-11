from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
import epanetlib as en

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','..','networks')
packdir = join(testdir,'..','..','..')

def test_terminal_nodes():
    inp_file = join(datadir,'Net1.inp')
    wn = en.network.WaterNetworkModel()
    parser = en.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)

    G = wn._graph

    terminal_nodes = en.network.terminal_nodes(G)
    
    expected_nodes = ['2', '9']
    
    assert_list_equal(terminal_nodes, expected_nodes)

if __name__ == '__main__':
    pass