from __future__ import print_function
from nose.tools import *
from nose import SkipTest
from os.path import abspath, dirname, join
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','..','examples','networks')
packdir = join(testdir,'..','..','..')

"""
Compare results to EPANET GUI using Net3 and Source Quality at
121          SETPOINT      100000  mg/L
121          FLOWPACED     100000  mg/L
121          MASS          6000000000  mg/min
River        CONCEN        100000   mg/L
"""

def test_epanet_binary_reader():
    #raise SkipTest
    inp_file = join(datadir,'Net3.inp')
    bin_file = 'tmp.bin'

    wn = wntr.network.WaterNetworkModel(inp_file)
    WQ = wntr.scenario.Waterquality('CHEM', ['121'], 'SETPOINT', 100, 0, -1)

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim(WQ, file_prefix='tmp', binary_file=True)

    enbin = wntr.epanet.BinFile()
    enbin.read(bin_file)
    expected = 91661.72*(1e-6/0.001) # Node '159' at hour 6
    simOut = results.node.loc['quality', 6*3600, '159']
    binOut = enbin.results.node.loc['quality', 6*3600, '159']
    diff = abs((simOut-binOut)/expected)
    assert_less(diff, 0.0001) # 0.01% error


if __name__ == '__main__':
    #test_setpoint_waterquality_simulation()
    #test_flowpaced_waterquality_simulation()
    #test_mass_waterquality_simulation()
    #test_conc_waterquality_simulation()
    #test_age_waterquality_simulation()
    test_epanet_binary_reader()
