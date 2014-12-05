from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np

import sys
sys.path.append('C:\kaklise\EPA-Resilience\Evaluation_Tool')
import epanetlib as en

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','..','networks')

def test_terminal_nodes():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    G = en.network.epanet_to_MultiDiGraph(enData)

    terminal_nodes = en.metrics.terminal_nodes(G)
    
    expected_nodes = ['2', '9']
    
    assert_list_equal(terminal_nodes, expected_nodes)

def test_nzd_nodes():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    G = en.network.epanet_to_MultiDiGraph(enData)

    nzd_nodes = en.metrics.nzd_nodes(G)
    
    expected_nodes = ['11', '13', '12', '21', '22', '23', '32', '31']
    
    assert_list_equal(nzd_nodes, expected_nodes)
    
def test_tank_nodes():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    G = en.network.epanet_to_MultiDiGraph(enData)

    tank_nodes = en.metrics.tank_nodes(G)
    
    expected_nodes = ['12']
    
    assert_list_equal(tank_nodes, expected_nodes)
    
def test_query_node_attribute():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    G = en.network.epanet_to_MultiDiGraph(enData)
    
    elevation = en.units.convert('Elevation', 1, 700) # ft to m
    nodes = en.metrics.query_node_attribute(G, 'elevation', np.less, elevation)
    
    expected_nodes = ['13', '22', '23']
    
    assert_list_equal(nodes, expected_nodes)

def test_query_pipe_attribute():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    G = en.network.epanet_to_MultiDiGraph(enData)
    
    length = en.units.convert('Length', 1, 5280) # ft to m
    pipes = en.metrics.query_pipe_attribute(G, 'length', np.greater, length)
    
    linkid = []
    for i in range(len(pipes)):
        linkid.append(pipes[i][2])
    
    expected_pipes = ['10']
    
    assert_list_equal(linkid, expected_pipes)
    
if __name__ == '__main__':
    test_query_pipe_attribute()