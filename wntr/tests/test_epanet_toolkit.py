from nose.tools import *
import wntr.epanet.toolkit
from os.path import abspath, dirname, join

testdir = dirname(abspath(__file__))
datadir = join(testdir,'..','..','examples','networks')

def test_isOpen():
    enData = wntr.epanet.toolkit.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp')
    assert_equal(0, enData.isOpen())
    enData.ENopen(enData.inpfile,'temp.rpt')
    assert_equal(1, enData.isOpen())

def test_ENgetcount():
    enData = wntr.epanet.toolkit.ENepanet()
    enData.inpfile = join(datadir,'Net1.inp')
    enData.ENopen(enData.inpfile,'temp.rpt')
    nNodes = enData.ENgetcount(wntr.epanet.util.EN.NODECOUNT)
    assert_equal(11, nNodes)
    nLinks = enData.ENgetcount(wntr.epanet.util.EN.LINKCOUNT)
    assert_equal(13, nLinks)

