from nose.tools import *
import epanetlib as en
from os.path import abspath, dirname, join

testdir = dirname(abspath(__file__))
datadir = join(testdir,'..','..','..','networks')

def test_isOpen():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    assert_equal(0, enData.isOpen())
    enData.ENopen(enData.inpfile,'tmp.rpt')
    assert_equal(1, enData.isOpen())

def test_ENgetcount():
    enData = en.pyepanet.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp') 
    enData.ENopen(enData.inpfile,'tmp.rpt')
    nNodes = enData.ENgetcount(en.pyepanet.EN_NODECOUNT) 
    assert_equal(11, nNodes)
    nLinks = enData.ENgetcount(en.pyepanet.EN_LINKCOUNT) 
    assert_equal(13, nLinks)

