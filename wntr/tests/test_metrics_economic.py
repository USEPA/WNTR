from nose.tools import *
from nose import SkipTest
from os.path import abspath, dirname, join
import pandas as pd
from pandas.util.testing import assert_frame_equal, assert_series_equal
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'networks_for_testing')
netdir = join(testdir,'..','..','examples','networks')


def test_annual_network_cost1():
    inp_file = join(netdir,'Net1.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    cost = wntr.metrics.annual_network_cost(wn)
    assert_almost_equal(cost, 460147, 0) 

def test_annual_network_cost2():
    # Network cost using a tank volume curve
    inp_file = join(datadir,'Anytown_multipointcurves.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    cost = wntr.metrics.annual_network_cost(wn)    
    assert_almost_equal(cost, 1201467.78, 0)
    
def test_annual_ghg_emissions():
    inp_file = join(netdir,'Net1.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    cost = wntr.metrics.annual_ghg_emissions(wn)
    assert_almost_equal(cost, 410278, 0) 
    
if __name__ == '__main__':
    test_annual_network_cost1()
    test_annual_network_cost2()
    test_annual_ghg_emissions()