import unittest
from os.path import abspath, dirname, join

import wntr.epanet.toolkit

testdir = dirname(abspath(__file__))
datadir = join(testdir, "..", "..", "examples", "networks")


class TestEpanetToolkit(unittest.TestCase):
    def test_isOpen(self):
        enData = wntr.epanet.toolkit.ENepanet()
        enData.inpfile = join(datadir, "Net1.inp")
        self.assertEqual(0, enData.isOpen())
        enData.ENopen(enData.inpfile, "temp.rpt")
        self.assertEqual(1, enData.isOpen())

    def test_ENgetcount(self):
        enData = wntr.epanet.toolkit.ENepanet()
        enData.inpfile = join(datadir, "Net1.inp")
        enData.ENopen(enData.inpfile, "temp.rpt")
        nNodes = enData.ENgetcount(wntr.epanet.util.EN.NODECOUNT)
        self.assertEqual(11, nNodes)
        nLinks = enData.ENgetcount(wntr.epanet.util.EN.LINKCOUNT)
        self.assertEqual(13, nLinks)
        elev0 = enData.ENgetnodevalue(2,wntr.epanet.util.EN.ELEVATION)
        enData.ENsetnodevalue(2, wntr.epanet.util.EN.ELEVATION, 715.0)
        elev1 = enData.ENgetnodevalue(2,wntr.epanet.util.EN.ELEVATION)
        self.assertEqual(710.0, elev0)
        self.assertEqual(715.0, elev1)

if __name__ == "__main__":
    unittest.main()
