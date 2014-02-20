from nose.tools import *
import epanetlib as en
from os.path import abspath, dirname, join

testdir = dirname(abspath(__file__))

def test_layout1():
    inp_file_name = join(testdir,'Awumah_layout1.inp') 
    enData = en.pyepanet.ENepanet()
    print enData
    enData.ENopen(inp_file_name,'tmp.rpt')
    pos = en.pyepanet.future.ENgetcoordinates(inp_file_name)
    keys = [('1', '2', '2'), ('2', '3', '3'), ('1', '4', '4'), ('2', '5', '5'), ('4', '5', '6'),
        ('3', '6', '7'), ('4', '7', '8'), ('5', '8', '9'), ('6', '9', '10'), 
        ('7', '10', '11'), ('10', '11', '12'), ('9', '12', '13')]
    values = [940.7, 550.0, 659.3, 290.7, 59.3, 400.0, 450.0, 200.0, 300.0, 250.0, 150.0, 100.0]
    edge_attribute = dict(zip(keys, values))   
    DG = en.network.epanet_to_MultiDiGraph(enData, edge_attribute, pos=pos)
    entropy = en.metrics.entropy(DG, enData)
    
    assert_almost_equals(2.280, entropy)
