from nose.tools import *
from nose import SkipTest
from os.path import abspath, dirname, join
import numpy as np
import wntr
import networkx as nx

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','tests','networks_for_testing')
packdir = join(testdir,'..','..','..')

def test_central_point_dominance():
    """
    Pandit, Arka, and John C. Crittenden. "Index of network resilience
    (INR) for urban water distribution systems." Nature (2012).
    """

    raise SkipTest
    
    inp_file = join(datadir,'Anytown.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel(inp_file)
            
    G = wn.get_graph_deep_copy()
    
    CPD = G.central_point_dominance()

    print 'num_links = ',wn.num_links()
    print 'num_nodes = ',wn.num_nodes()
    print 'CPD = ',CPD
    print 'expected CPD = ',0.28
    error = abs(0.28-CPD)
    assert_less(error, 0.01)
    assert_equal(wn.num_links(),41)
    assert_equal(wn.num_nodes(),22)

def test_diameter():
    """
    Pandit, Arka, and John C. Crittenden. "Index of network resilience
    (INR) for urban water distribution systems." Nature (2012).
    """

    raise SkipTest
    
    inp_file = join(datadir,'Anytown.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel(inp_file)
            
    G = wn.get_graph_deep_copy()
    udG = G.to_undirected()
    
    diameter = nx.diameter(udG)
    
    error = abs(5.0-diameter)
    assert_less(error, 0.01)

def test_characteristic_path_length():
    """
    Pandit, Arka, and John C. Crittenden. "Index of network resilience
    (INR) for urban water distribution systems." Nature (2012).
    """

    raise SkipTest
    
    inp_file = join(datadir,'Anytown.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel(inp_file)
            
    G = wn.get_graph_deep_copy()
    udG = G.to_undirected()
    
    CPL = nx.average_shortest_path_length(udG)
    
    print 'CPL = ',CPL
    print 'expected CPL = ',1.24
    error = abs(1.24-CPL)
    assert_less(error, 0.01)

def test_algebraic_connectivity():
    """
    Pandit, Arka, and John C. Crittenden. "Index of network resilience
    (INR) for urban water distribution systems." Nature (2012).
    """

    raise SkipTest
    
    inp_file = join(datadir,'Anytown.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel(inp_file)
    G = wn.get_graph_deep_copy()
    AC = G.algebraic_connectivity()

    print 'AC = ',AC
    print 'expected AC = ',0.56
    error = abs(0.56-AC)
    assert_less(error, 0.01)

def test_crit_ratio_defrag():
    """
    Pandit, Arka, and John C. Crittenden. "Index of network resilience
    (INR) for urban water distribution systems." Nature (2012).
    """

    raise SkipTest
    
    inp_file = join(datadir,'Anytown.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel(inp_file)
    G = wn.get_graph_deep_copy()
    CRD = G.critical_ratio_defrag()

    print 'CRD = ',CRD
    print 'expected CRD = ',0.63
    error = abs(0.63-CRD)
    assert_less(error, 0.01)


if __name__ == '__main__':
    test_central_point_dominance()
