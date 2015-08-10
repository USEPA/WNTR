from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
import matplotlib.pyplot as plt
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','tests','networks_for_testing')
packdir = join(testdir,'..','..','..')

import functools
from nose import SkipTest

def expected_failure(test):
    @functools.wraps(test)
    def inner(*args, **kwargs):
        try:
            test(*args, **kwargs)
        except Exception:
            raise SkipTest
        else:
            raise AssertionError('Failure expected')
    return inner
    
def test_Todini_Fig2_optCost_GPM():
    inp_file = join(datadir,'Todini_Fig2_optCost_GPM.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    todini = wntr.metrics.todini(results, wn, 30) # h* = 30 m
    
    print 'Todini: Fig2_optCost'
    print todini[0]
    
    expected = 0.22
    error = abs((todini[0] - expected)/expected)
    assert_less(error, 0.1) # 10% error

def test_Todini_Fig2_optCost_CMH():
    inp_file = join(datadir,'Todini_Fig2_optCost_CMH.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    todini = wntr.metrics.todini(results, wn, 30) # h* = 30 m
    
    print 'Todini: Fig2_optCost'
    print todini[0]
    
    expected = 0.22
    error = abs((todini[0] - expected)/expected)
    assert_less(error, 0.1) # 10% error
    
def test_Todini_Fig2_solA_GPM():
    inp_file = join(datadir,'Todini_Fig2_solA_GPM.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    todini = wntr.metrics.todini(results, wn, 30) # h* = 30 m
    
    print 'Todini: Fig2_solA'
    print todini[0]
    
    expected = 0.41
    error = abs((todini[0] - expected)/expected)
    assert_less(error, 0.1) # 10% error

def test_Todini_Fig2_solA_CMH():
    inp_file = join(datadir,'Todini_Fig2_solA_CMH.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    todini = wntr.metrics.todini(results, wn, 30) # h* = 30 m
    
    print 'Todini: Fig2_solA'
    print todini[0]
    
    expected = 0.41
    error = abs((todini[0] - expected)/expected)
    assert_less(error, 0.1) # 10% error

@expected_failure
def test_BWSN_Network_2():
    inp_file = join(datadir,'BWSN_Network_2.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    todini = wntr.metrics.todini(results, wn, 21.1)
    # len(time) <> len(todini) becuase the hydrulic simulation ends at 27 hours
    # the system is disconnected at that time
    
    todini = np.array(todini)
    Tave = np.mean(todini)
    Tmax = max(todini)
    Tmin = min(todini)
    
    print 'Todini: BWSN_Network_2'
    print "  average index: " + str(Tave)
    print "  max index: " + str(Tmax)
    print "  min index: " + str(Tmin)
    
    expected_Taverage = 0.836
    error = abs((Tave - expected_Taverage)/expected_Taverage)
    assert_less(error, 0.1) # 10% error
    
    expected_Tmax = 0.930
    error = abs((Tmax - expected_Tmax)/expected_Tmax)
    assert_less(error, 0.1) # 10% error
    
    expected_Tmin = 0.644
    error = abs((Tmin - expected_Tmin)/expected_Tmin)
    assert_less(error, 0.1) # 10% error
    
@expected_failure
def test_Net6():
    inp_file = join(datadir,'Net6_mod.inp') 

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.network.ParseWaterNetwork()
    parser.read_inp_file(wn, inp_file)
    
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    todini = wntr.metrics.todini(results, wn, 21.1)
    
    todini = np.array(todini)
    Tave = np.mean(todini)
    Tmax = max(todini)
    Tmin = min(todini)
    
    print 'Todini: Net6'
    print "  average index: " + str(Tave)
    print "  max index: " + str(Tmax)
    print "  min index: " + str(Tmin)
    
    expected_Taverage = 0.267
    error = abs((Tave - expected_Taverage)/expected_Taverage)
    assert_less(error, 0.1) # 10% error
    
    expected_Tmax = 0.547
    error = abs((Tmax - expected_Tmax)/expected_Tmax)
    assert_less(error, 0.1) # 10% error
    
    expected_Tmin = 0.075
    error = abs((Tmin - expected_Tmin)/expected_Tmin)
    assert_less(error, 0.1) # 10% error
    
if __name__ == '__main__':
    test_BWSN_Network_2()
