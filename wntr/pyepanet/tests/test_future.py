from nose.tools import *
import wntr
from os.path import abspath, dirname, join

testdir = dirname(abspath(__file__))
datadir = join(testdir,'..','..','..','examples','networks')

def test_ENgetcoordinates():
    enData = wntr.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    pos1 = wntr.pyepanet.future.ENgetcoordinates(enData.inpfile)
    pos2 = {'11': (30.0, 70.0), 
            '10': (20.0, 70.0), 
            '13': (70.0, 70.0), 
            '12': (50.0, 70.0), 
            '21': (30.0, 40.0), 
            '22': (50.0, 40.0), 
            '23': (70.0, 40.0), 
            '32': (50.0, 10.0), 
            '31': (30.0, 10.0), 
            '2':  (50.0, 90.0), 
            '9':  (10.0, 70.0)}
            
    assert_dict_equal(pos1, pos2)
    
