import unittest
from os.path import abspath, dirname, join, exists

import wntr.epanet.toolkit

testdir = dirname(abspath(__file__))
datadir = join(testdir, "..", "..", "examples", "networks")


class TestEpanetToolkit(unittest.TestCase):
    
    def test_isOpen(self):
        for version in [2.0, 2.2,]:
            enData = wntr.epanet.toolkit.ENepanet(version=version)
            enData.inpfile = join(datadir, "Net1.inp")
            self.assertEqual(0, enData.isOpen())
            enData.ENopen(enData.inpfile, "temp.rpt")
            self.assertEqual(1, enData.isOpen())

    def test_ENgetcount(self):
        for version in [2.0, 2.2,]:
            enData = wntr.epanet.toolkit.ENepanet(version=version)
            enData.inpfile = join(datadir, "Net1.inp")
            enData.ENopen(enData.inpfile, "temp.rpt")
            
            nNodes = enData.ENgetcount(wntr.epanet.util.EN.NODECOUNT)
            self.assertEqual(11, nNodes)
            nLinks = enData.ENgetcount(wntr.epanet.util.EN.LINKCOUNT)
            self.assertEqual(13, nLinks)
    
    def test_ENgetflowunits(self):
        for version in [2.0, 2.2,]:
            enData = wntr.epanet.toolkit.ENepanet(version=version)
            enData.inpfile = join(datadir, "Net1.inp")
            enData.ENopen(enData.inpfile, "temp.rpt")
            
            flowunit = enData.ENgetflowunits()
            assert(flowunit==1) # GPM
        
    def test_EN_timeparam(self):
        for version in [2.0, 2.2,]:
            enData = wntr.epanet.toolkit.ENepanet(version=version)
            enData.inpfile = join(datadir, "Net1.inp")
            enData.ENopen(enData.inpfile, "temp.rpt")
            
            duration = enData.ENgettimeparam(0)
            assert(duration==86400) # s
            enData.ENsettimeparam(0, 200)
            duration = enData.ENgettimeparam(0)
            assert(duration==200)
        
    def test_ENgetindex_ENgetvalue(self):
        for version in [2.0, 2.2,]:
            enData = wntr.epanet.toolkit.ENepanet(version=version)
            enData.inpfile = join(datadir, "Net1.inp")
            enData.ENopen(enData.inpfile, "temp.rpt")
            
            node_index = enData.ENgetnodeindex('10') 
            assert(node_index == 1) 
            node_val = enData.ENgetnodevalue(node_index, 0) # ELEVATION = 0
            assert(node_val == 710) 
            enData.ENsetnodevalue(node_index, 0, 170.5)
            node_val = enData.ENgetnodevalue(node_index, 0) # ELEVATION = 0
            assert(node_val == 170.5) 
            
            
            link_index = enData.ENgetlinkindex('11') 
            assert(link_index == 2) 
            link_val = enData.ENgetlinkvalue(link_index, 0) # DIAMETER = 0
            assert(link_val == 14) 
            enData.ENsetlinkvalue(link_index, 0, 16.5)
            link_val = enData.ENgetlinkvalue(link_index, 0) # DIAMETER = 0
            assert(link_val == 16.5) 
        
    def test_ENsaveinpfile(self):
        for version in [2.0, 2.2,]:
            enData = wntr.epanet.toolkit.ENepanet(version=version)
            enData.inpfile = join(datadir, "Net1.inp")
            enData.ENopen(enData.inpfile, "temp.rpt")
            
            enData.ENsaveinpfile("temp_Net1_toolkit.inp") 
            file_exists = exists("temp_Net1_toolkit.inp")
            assert file_exists
        
    def test_runepanet(self):
        inpfile = join(datadir, "Net1.inp")
        wntr.epanet.toolkit.runepanet(inpfile, "temp_runepanet.rpt", "temp_runepanet.bin")
                 
        reader = wntr.epanet.io.BinFile()
        results = reader.read("temp_runepanet.bin")
        
        assert(isinstance(results, wntr.sim.results.SimulationResults))
        assert(results.node['pressure'].shape == (25,11))
        
    def test_runepanet_step(self):
        for version in [2.0, 2.2,]:
            enData = wntr.epanet.toolkit.ENepanet(version=version)
            enData.inpfile = join(datadir, "Net1.inp")
            enData.ENopen(enData.inpfile, "temp_runepanet_step.rpt", "temp_runepanet_step.bin")
            
            enData.ENopenH()
            enData.ENinitH(0)
            t = 0
            while True:
                enData.ENrunH()
                tstep = enData.ENnextH()
                t = t + tstep
                if (tstep <= 0):
                    break
            
            enData.ENcloseH()

            assert (t == 86400)

if __name__ == "__main__":
    unittest.main()
