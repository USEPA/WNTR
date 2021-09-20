import unittest
import warnings
from os.path import abspath, dirname, join

import matplotlib.pylab as plt
import numpy as np
import wntr
import wntr.sim.realtime as rt

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

### These tests need to be updated to be real tests, not graphics and use additional networks


class Test_Reset_Conditions(unittest.TestCase):
    @classmethod
    def setUpClass(self):

        self.inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(self.inp_file)
        self.wn = wn
        wn.options.quality.trace_node = "River"
        wn.options.time.duration = 100 * 3600
        wn.options.time.hydraulic_timestep = 60
        sim = wntr.sim.EpanetSimulator(wn)
        self.benchmarck_results = sim.run_sim()
        for control_name in wn.control_name_list:
            wn.remove_control(control_name)
        self.commands = """3600,P10-RIC/STATUS,1
54000,P10-RIC/STATUS,0
90000,P10-RIC/STATUS,1
140400,P10-RIC/STATUS,0
176400,P10-RIC/STATUS,1
226800,P10-RIC/STATUS,0
262800,P10-RIC/STATUS,1
313200,P10-RIC/STATUS,0
349200,P10-RIC/STATUS,1
399600,P10-RIC/STATUS,0
435600,P10-RIC/STATUS,1
486000,P10-RIC/STATUS,0
522000,P10-RIC/STATUS,1
572400,P10-RIC/STATUS,0
"""
        with open("step_test.in", 'w') as ctrlin:
            ctrlin.write(self.commands)
        
        self.controls = [
            [ "T1-LI/PV", np.less, 149, "P335-RIC/STATUS", 1],
            [ "T1-LI/PV", np.greater, 151, "P335-RIC/STATUS", 0],
            [ "T1-LI/PV", np.less, 149, "MOV330/STATUS", 0],
            [ "T1-LI/PV", np.greater, 151, "MOV330/STATUS", 1],
        ]

        self.nodesens = [
            ("T1-LI/PV", "1", "head"),
            ("T2-LI/PV", "2", "head"),
            ("T3-LI/PV", "3", "head"),
            ("J123-FI/PV", "123", "demand"),
            ("J125-FI/PV", "125", "demand"),
            ("J125-QUAL", "125", "quality"),
        ]
        self.linksens = [
            ("P10-FI/PV", "10", "flow"),
            ("P335-FI/PV", "335", "flow"),
            ("MOV330-FI/PV", "330", "flow"),
        ]
        self.controllers = [
            ("P335-RIC/STATUS", "335", "status"),
            ("MOV330/STATUS", "330", "status"),
            ("P10-RIC/STATUS", "10", "status"),
        ]


    @classmethod
    def tearDownClass(self):
        pass

    def test_epanet_basic(self):
        sim = rt.EpanetStepwiseSimulator(self.wn)
        prov = rt.RealtimeProvider(timelimit=self.wn.options.time.duration,
            outfile="step_test.out",
            infile="step_test.in",
            controls=self.controls)
        for sensor in self.nodesens:
            sim.add_sensor_instrument(sensor[0], 'node', sensor[1], sensor[2])
        for sensor in self.linksens:
            sim.add_sensor_instrument(sensor[0], 'link', sensor[1], sensor[2])
        for controller in self.controllers:
            sim.add_controller_instrument(controller[0], controller[1], controller[2])
        
        sim.initialize(transmit=prov.proc_sensors, receive=prov.proc_controllers, stop=prov.check_time, file_prefix="step_test")
        sim.run_sim()
        res = sim.close()
        

if __name__ == "__main__":
    unittest.main()
