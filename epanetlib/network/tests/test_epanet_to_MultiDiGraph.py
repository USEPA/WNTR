from nose.tools import *
import epanetlib as en
from os.path import abspath, dirname, join

testdir = dirname(abspath(__file__))
datadir = join(testdir,'..','..','..','networks')

def test_Net1():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    G = en.network.epanet_to_MultiDiGraph(enData)

    node = {'11': {'elevation': 710.0, 'nodetype': 0, 'pos': (30.0, 70.0)}, 
            '10': {'elevation': 710.0, 'nodetype': 0, 'pos': (20.0, 70.0)}, 
            '13': {'elevation': 695.0, 'nodetype': 0, 'pos': (70.0, 70.0)}, 
            '12': {'elevation': 700.0, 'nodetype': 0, 'pos': (50.0, 70.0)}, 
            '21': {'elevation': 700.0, 'nodetype': 0, 'pos': (30.0, 40.0)}, 
            '22': {'elevation': 695.0, 'nodetype': 0, 'pos': (50.0, 40.0)}, 
            '23': {'elevation': 690.0, 'nodetype': 0, 'pos': (70.0, 40.0)}, 
            '32': {'elevation': 710.0, 'nodetype': 0, 'pos': (50.0, 10.0)}, 
            '31': {'elevation': 700.0, 'nodetype': 0, 'pos': (30.0, 10.0)}, 
            '2':  {'elevation': 850.0, 'nodetype': 2, 'pos': (50.0, 90.0)}, 
            '9':  {'elevation': 800.0, 'nodetype': 1, 'pos': (10.0, 70.0)}}
            
    edge = {'11': {'12': {'11':  {'linktype': 1, 'diameter': 14.0, 'length': 5280.0}}, 
                   '21': {'111': {'linktype': 1, 'diameter': 10.0, 'length': 5280.0}}}, 
            '10': {'11': {'10':  {'linktype': 1, 'diameter': 18.0, 'length': 10530.0}}}, 
            '13': {'23': {'113': {'linktype': 1, 'diameter': 8.0,  'length': 5280.0}}}, 
            '12': {'13': {'12':  {'linktype': 1, 'diameter': 10.0, 'length': 5280.0}}, 
                   '22': {'112': {'linktype': 1, 'diameter': 12.0, 'length': 5280.0}}}, 
            '21': {'31': {'121': {'linktype': 1, 'diameter': 8.0,  'length': 5280.0}}, 
                   '22': {'21':  {'linktype': 1, 'diameter': 10.0, 'length': 5280.0}}}, 
            '22': {'32': {'122': {'linktype': 1, 'diameter': 6.0,  'length': 5280.0}}, 
                   '23': {'22':  {'linktype': 1, 'diameter': 12.0, 'length': 5280.0}}}, 
            '23': {}, 
            '32': {}, 
            '31': {'32': {'31':  {'linktype': 1, 'diameter': 6.0,  'length': 5280.0}}}, 
            '2':  {'12': {'110': {'linktype': 1, 'diameter': 18.0, 'length': 200.0}}}, 
            '9':  {'10': {'9':   {'linktype': 2, 'diameter': 0.0,  'length': 0.0}}}}

    assert_dict_contains_subset(node, G.node)
    assert_dict_contains_subset(edge, G.edge)
    
def test_Net1_edge_attribute():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    keys = [('11', '12', '11'), ('11', '21', '111'), ('10', '11', '10'), 
            ('13', '23', '113'), ('12', '13', '12'), ('12', '22', '112'), 
            ('21', '31', '121'), ('21', '22', '21'), ('22', '32', '122'), 
            ('22', '23', '22'), ('31', '32', '31'), ('2', '12', '110'), 
            ('9', '10', '9')]
    values = [1, 2, 3, 4, 5, 6, 7, -8, -9, -10, -11, -12, -13]
    edge_attribute = dict(zip(keys, values))   
    
    G = en.network.epanet_to_MultiDiGraph(enData, edge_attribute)
    
    node = {'11': {'elevation': 710.0, 'nodetype': 0, 'pos': (30.0, 70.0)}, 
            '10': {'elevation': 710.0, 'nodetype': 0, 'pos': (20.0, 70.0)}, 
            '13': {'elevation': 695.0, 'nodetype': 0, 'pos': (70.0, 70.0)}, 
            '12': {'elevation': 700.0, 'nodetype': 0, 'pos': (50.0, 70.0)}, 
            '21': {'elevation': 700.0, 'nodetype': 0, 'pos': (30.0, 40.0)}, 
            '22': {'elevation': 695.0, 'nodetype': 0, 'pos': (50.0, 40.0)}, 
            '23': {'elevation': 690.0, 'nodetype': 0, 'pos': (70.0, 40.0)}, 
            '32': {'elevation': 710.0, 'nodetype': 0, 'pos': (50.0, 10.0)}, 
            '31': {'elevation': 700.0, 'nodetype': 0, 'pos': (30.0, 10.0)}, 
            '2':  {'elevation': 850.0, 'nodetype': 2, 'pos': (50.0, 90.0)}, 
            '9':  {'elevation': 800.0, 'nodetype': 1, 'pos': (10.0, 70.0)}}
    
    edge = {'11': {'12': {'11':  {'linktype': 1, 'diameter': 14.0, 'length': 5280.0,  'weight': 1}}, 
                   '21': {'111': {'linktype': 1, 'diameter': 10.0, 'length': 5280.0,  'weight': 2}}}, 
            '10': {'11': {'10':  {'linktype': 1, 'diameter': 18.0, 'length': 10530.0, 'weight': 3}}, 
                   '9':  {'9':   {'linktype': 2, 'diameter': 0.0,  'length': 0.0,     'weight': 13}}}, 
            '13': {'23': {'113': {'linktype': 1, 'diameter': 8.0,  'length': 5280.0,  'weight': 4}}}, 
            '12': {'13': {'12':  {'linktype': 1, 'diameter': 10.0, 'length': 5280.0,  'weight': 5}}, 
                   '2':  {'110': {'linktype': 1, 'diameter': 18.0, 'length': 200.0,   'weight': 12}}, 
                   '22': {'112': {'linktype': 1, 'diameter': 12.0, 'length': 5280.0,  'weight': 6}}}, 
            '21': {'31': {'121': {'linktype': 1, 'diameter': 8.0,  'length': 5280.0,  'weight': 7}}}, 
            '22': {'21': {'21':  {'linktype': 1, 'diameter': 10.0, 'length': 5280.0,  'weight': 8}}}, 
            '23': {'22': {'22':  {'linktype': 1, 'diameter': 12.0, 'length': 5280.0,  'weight': 10}}}, 
            '32': {'31': {'31':  {'linktype': 1, 'diameter': 6.0,  'length': 5280.0,  'weight': 11}}, 
                   '22': {'122': {'linktype': 1, 'diameter': 6.0,  'length': 5280.0,  'weight': 9}}}, 
            '31': {}, 
            '2':  {}, 
            '9':  {}}
    
    assert_dict_contains_subset(node, G.node)
    assert_dict_contains_subset(edge, G.edge)
    
    
    