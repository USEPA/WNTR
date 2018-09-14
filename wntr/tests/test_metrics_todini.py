from __future__ import print_function
from nose.tools import *
from os.path import abspath, dirname, join
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'networks_for_testing')


def test_Todini_Fig2_optCost_GPM():
    inp_file = join(datadir,'Todini_Fig2_optCost_GPM.inp')

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel(inp_file)

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    head = results.node['head']
    pressure = results.node['pressure']
    demand = results.node['demand']
    flowrate = results.link['flowrate']
    todini = wntr.metrics.todini_index(head, pressure, demand, flowrate, wn, 30) # h* = 30 m

    expected = 0.22
    error = abs(todini[0] - expected)
    print(todini[0], expected, error)
    assert_less(error, 0.01) 

def test_Todini_Fig2_optCost_CMH():
    inp_file = join(datadir,'Todini_Fig2_optCost_CMH.inp')

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.epanet.InpFile()
    wn = parser.read(inp_file)

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    head = results.node['head']
    pressure = results.node['pressure']
    demand = results.node['demand']
    flowrate = results.link['flowrate']
    todini = wntr.metrics.todini_index(head, pressure, demand, flowrate, wn, 30) # h* = 30 m

    expected = 0.22
    error = abs(todini[0] - expected)
    print(todini[0], expected, error)
    assert_less(error, 0.01) 

def test_Todini_Fig2_solA_GPM():
    inp_file = join(datadir,'Todini_Fig2_solA_GPM.inp')

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.epanet.InpFile()
    wn = parser.read(inp_file)

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim(file_prefix='tmp_tod_solA_GPM')

    # Compute todini index
    head = results.node['head']
    pressure = results.node['pressure']
    demand = results.node['demand']
    flowrate = results.link['flowrate']
    todini = wntr.metrics.todini_index(head, pressure, demand, flowrate, wn, 30) # h* = 30 m
    
    expected = 0.41
    error = abs(todini[0] - expected)
    print(todini[0], expected, error)
    assert_less(error, 0.03) 

def test_Todini_Fig2_solA_CMH():
    inp_file = join(datadir,'Todini_Fig2_solA_CMH.inp')

    # Create a water network model for results object
    wn = wntr.network.WaterNetworkModel()
    parser = wntr.epanet.InpFile()
    wn = parser.read(inp_file)

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    # Compute todini index
    head = results.node['head']
    pressure = results.node['pressure']
    demand = results.node['demand']
    flowrate = results.link['flowrate']
    todini = wntr.metrics.todini_index(head, pressure, demand, flowrate, wn, 30) # h* = 30 m
    
    expected = 0.41
    error = abs(todini[0] - expected)
    print(todini[0], expected, error)
    assert_less(error, 0.03) 

if __name__ == '__main__':
    test_Todini_Fig2_solA_GPM()
