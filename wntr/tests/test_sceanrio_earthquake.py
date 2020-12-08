from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
import pandas as pd
from pandas.util.testing import assert_frame_equal, assert_series_equal
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','tests','networks_for_testing')
netdir = join(testdir,'..','..','examples','networks')

def test_distance_to_epicenter():
    inp_file = join(netdir,'Net1.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    earthquake = wntr.scenario.Earthquake((40,55), 5, 10000.0)
    
    """
    Junction 12 is at (50,70)
    """
    R = earthquake.distance_to_epicenter(wn,wntr.network.Junction)
    expected = np.sqrt(np.power(50-40,2)+np.power(70-55,2))
    assert_less(np.abs(R['12']-expected), 1E-5) 

    wn = wntr.morph.scale_node_coordinates(wn,100)
    R = earthquake.distance_to_epicenter(wn,wntr.network.Junction)
    expected = np.sqrt(np.power(5000-40,2)+np.power(7000-55,2))
    assert_less(np.abs(R['12']-expected), 1E-5) 

def test_correction_factor():
    earthquake = wntr.scenario.Earthquake((40,55), 5, 10000.0)
    
    data = pd.DataFrame(columns=['Diameter', 'Material', 'Topography', 'Liquifaction'], index=['P1', 'P2', 'P3'])
    data.loc['P1',:] = ['Small', 'ACP', 'Narrow valley', 'Total']
    data.loc['P2',:] = ['Medium', 'PV', 'Terrace', 'Partial']
    data.loc['P3',:] = ['Large', 'SP', 'Stiff alluvial', 'None']
    C = earthquake.correction_factor(data)
    expected = pd.Series([1*1.2*3.2*2.4,0.8*1*1.5*2,0.5*0.3*0.4*1],index=['P1','P2','P3'])
    assert_series_equal(C,expected)
    
def test_pga_attenuation():
    R = pd.Series({'1': 1000.0}) 
    
    earthquake = wntr.scenario.Earthquake((0, 0), 5, 10000.0)
    
    pga = earthquake.pga_attenuation_model(R, method=1)
    #print(pga['1'])
    assert_less(np.abs(pga['1']-1.3275E-1), 1E-5) 
    
    pga = earthquake.pga_attenuation_model(R, method=2)
    #print(pga['1'])
    assert_less(np.abs(pga['1']-9.6638E-2), 1E-6) 
    
    pga = earthquake.pga_attenuation_model(R, method=3)
    #print(pga['1'])
    assert_less(np.abs(pga['1']-1.2789E-3), 1E-7) 
    
    pga = earthquake.pga_attenuation_model(R)
    #print(pga['1'])
    assert_less(np.abs(pga['1']-7.6887E-2), 1E-6) 
    
def test_pgv_attenuation():
    R = pd.Series({'1':1000}) 
    
    # Yu and Jin, 2008
    earthquake = wntr.scenario.Earthquake((0, 0), 5, 0)
    pgv = earthquake.pgv_attenuation_model(R, method=1)
    assert_less(np.abs(pgv['1']-0.0531), 0.0001) 
    
    earthquake = wntr.scenario.Earthquake((0, 0), 7, 0)
    pgv = earthquake.pgv_attenuation_model(R, method=1)
    assert_less(np.abs(pgv['1']-1.8829), 0.0001) 
    
    earthquake = wntr.scenario.Earthquake((0, 0), 5, 0)
    pgv = earthquake.pgv_attenuation_model(R, method=2)
    assert_less(np.abs(pgv['1']-0.0884), 0.0001) 
    
    earthquake = wntr.scenario.Earthquake((0, 0), 7, 0)
    pgv = earthquake.pgv_attenuation_model(R, method=2)
    assert_less(np.abs(pgv['1']-2.3361), 0.0001) 
    
    earthquake = wntr.scenario.Earthquake((0, 0), 5, 0)
    pgv = earthquake.pgv_attenuation_model(R)
    assert_less(np.abs(pgv['1']-0.0707), 0.0001) 
    
    earthquake = wntr.scenario.Earthquake((0, 0), 7, 0)
    pgv = earthquake.pgv_attenuation_model(R)
    assert_less(np.abs(pgv['1']-2.1095), 0.0001) 

def test_repair_rate():
    
    PGV = pd.Series({'1':0.0531}) 
    C = pd.Series({'1':0.5}) 
    earthquake = wntr.scenario.Earthquake((0, 0), 0, 0)
    
    RR = earthquake.repair_rate_model(PGV, C=1, method=1)
    assert_less(np.abs(RR['1']-1.2823E-5), 1E-9) 
    
    RR = earthquake.repair_rate_model(PGV, C, method=1)
    assert_less(np.abs(RR['1']-6.4113E-6), 1E-10) 
    
    RR = earthquake.repair_rate_model(PGV, C=1, method=2)
    assert_less(np.abs(RR['1']-8.4132E-6), 1E-10) 
    
    RR = earthquake.repair_rate_model(PGV, C, method=2)
    assert_less(np.abs(RR['1']-4.2066E-6), 1E-10) 
    
if __name__ == '__main__':
    test_correction_factor()
