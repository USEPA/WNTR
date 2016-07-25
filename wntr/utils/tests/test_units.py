from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','..','networks')
packdir = join(testdir,'..','..','..')

def test_Concentration():
    typestring = 'Concentration'
    data_expected = 1 # kg/m3
    data = 1000 # mg/L
    for flowunit in range(10):
        execute_test(typestring, flowunit, data, data_expected)

def test_Demand():
    data_expected = 1 # m/s
    for typestring in ['Demand', 'Flow']:
        for flowunit in range(10):
            if flowunit == 0:
                data = 35.3146667 # ft3/s
            elif flowunit == 1:
                data = 15850.3231 # gall/min
            elif flowunit == 2:
                data = 22.8244653 # million gall/d
            elif flowunit == 3:
                data = 19 # million imperial gall/d
            elif flowunit == 4:
                data = 70.0456199 # acre-feet/day
            elif flowunit == 5:
                data = 1000 # L/s
            elif flowunit == 6:
                data = 60000 # L/min
            elif flowunit == 7:
                data = 86.4 # million L/d
            elif flowunit == 8:
                data = 3600 # m3/h
            elif flowunit == 9:
                data = 86400 # m3/d
            execute_test(typestring, flowunit, data, data_expected)

def test_Emitter_Coefficient():
    pass
    
def test_Pipe_Diameter():
    typestring = 'Pipe Diameter'
    data_expected = 1 # m    
    for flowunit in range(10):
        if flowunit in [0,1,2,3,4]:
            data = 39.3701 # in
        elif flowunit in [5,6,7,8,9]:
            data = 1000 # mm
        execute_test(typestring, flowunit, data, data_expected)
        
def test_Length():
    data_expected = 1 # m
    for typestring in ['Tank Diameter', 'Elevation', 'Hydraulic Head', 'Length']:
        for flowunit in range(10):
            if flowunit in [0,1,2,3,4]:
                data = 3.28084 # ft
            elif flowunit in [5,6,7,8,9]:
                data = 1 # m
            execute_test(typestring, flowunit, data, data_expected)
    
def test_Velocity():
    typestring = 'Velocity'   
    data_expected = 1 # m/s     
    for flowunit in range(10):
        if flowunit in [0,1,2,3,4]:
            data = 3.28084 # ft/s
        elif flowunit in [5,6,7,8,9]:
            data = 1 # m/s
        execute_test(typestring, flowunit, data, data_expected)
    
    # test list
    data = np.array([10,20,30]) # ft/s
    data_expected = [3.048,  6.096,  9.144] # m/s
    execute_test_list(typestring, 1, data, data_expected)
    
def test_Energy():
    typestring = 'Energy'    
    data_expected = 1000000 # J    
    data = 0.277777777778 # kW*hr
    for flowunit in range(10):        
        execute_test(typestring, flowunit, data, data_expected)

def test_Power():
    typestring = 'Power'    
    data_expected = 1000 # W    
    for flowunit in range(10):
        if flowunit in [0,1,2,3,4]:
            data = 1.34102209 # hp
        elif flowunit in [5,6,7,8,9]:
            data = 1 # kW
        execute_test(typestring, flowunit, data, data_expected)
        
def test_Pressure():
    typestring = 'Pressure'    
    data_expected = 1 # m    
    for flowunit in range(10):
        if flowunit in [0,1,2,3,4]:
            data = 1.421970206324753 # psi
        elif flowunit in [5,6,7,8,9]:
            data = 1 # m
        execute_test(typestring, flowunit, data, data_expected)

def test_Source_Mass_Injection():
    typestring = 'Source Mass Injection'    
    data_expected = 1 # mass/s
    data = 60 # mass/min
    for flowunit in range(10):
        execute_test(typestring, flowunit, data, data_expected)

def test_Volume():
    typestring = 'Volume'    
    data_expected = 1 # m3   
    for flowunit in range(10):
        if flowunit in [0,1,2,3,4]:
            data = 35.3147 # ft3
        elif flowunit in [5,6,7,8,9]:
            data = 1 # m3
        execute_test(typestring, flowunit, data, data_expected)

def test_Water_Age():
    typestring = 'Water Age'    
    data_expected = 1 # s
    data = 0.000277778 # hr
    for flowunit in range(10):
        execute_test(typestring, flowunit, data, data_expected)

@nottest        
def execute_test(typestring, flowunit, data, data_expected):
    data_convert = wntr.utils.convert(typestring, flowunit, data)
    data_convert = round(data_convert,3)
    assert_equal(data_convert, data_expected)

@nottest
def execute_test_list(typestring, flowunit, data, data_expected):
    data_convert = wntr.utils.convert(typestring, flowunit, data)
    data_convert = [round(k,3) for k in data_convert]
    assert_list_equal(data_convert, data_expected)
    
if __name__ == '__main__':
    test_Demand()
        