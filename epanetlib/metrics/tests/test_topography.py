from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','..','networks')
packdir = join(testdir,'..','..','..')

import sys
sys.path.append(packdir)
import epanetlib as en

def test_terminal_nodes():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    G = en.network.epanet_to_MultiDiGraph(enData)

    terminal_nodes = en.metrics.terminal_nodes(G)
    
    expected_nodes = ['2', '9']
    
    assert_list_equal(terminal_nodes, expected_nodes)

def test_tank_nodes():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    G = en.network.epanet_to_MultiDiGraph(enData)

    tank_nodes = en.metrics.tank_nodes(G)
    
    expected_nodes = ['12']
    
    assert_list_equal(tank_nodes, expected_nodes)
    
if __name__ == '__main__':
    pass