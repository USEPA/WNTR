import unittest
from os.path import abspath, dirname, join, exists
import pprint
from wntr.network.base import LinkStatus
import wntr

testdir = dirname(abspath(__file__))
datadir = join(testdir, "..", "..", "examples", "networks")


class TestEpanetSimulatorStep(unittest.TestCase):

    def test_run(self):
        # inp_file = join(datadir, "Net1.inp")
        inp_file = join(datadir, "Net6.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 1
        wn.options.time.duration = 24 * 3600
        # wn.options.time.duration = 4 * 24 * 3600
        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim()

    def test_step(self):
        # inp_file = join(datadir, "Net1_no-controls.inp")
        inp_file = join(datadir, "Net6.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        wn.options.time.hydraulic_timestep = 1
        wn.options.time.duration = 24 * 3600
        sim = wntr.sim.EpanetSimulator(wn)
        node_sensors = None # list([('2', 'head')])  #list([('*', 'demand',), ('*', 'head',), ('*', 'pressure',), ('*', 'quality',)])
        link_sensors = None # list([('9', 'status')])  #None #list([('*', 'LINKQUAL',), ('*', 'flow',), ('*', 'velocity',), ('*', 'headloss',), ('*', 'status',), ('*', 'setting',), ])
        results = list()
        t, ret = sim.step_init(file_prefix='test_epanet_simulator', node_sensors=node_sensors, link_sensors=link_sensors)
        results.append((t, ret))
        while t >= 0:
            """
            LINK 9 OPEN IF NODE 2 BELOW 110
            LINK 9 CLOSED IF NODE 2 ABOVE 140
            """
            set_values = None
            # if ret['node']['head']['2'] - 850.0 < 110.0 and ret['link']['status']['9'] == int(wntr.network.base.LinkStatus.Closed):
            #     set_values = [('9', 'status', wntr.network.base.LinkStatus.Open)]
            # if ret['node']['head']['2'] - 850.0 > 140.0 and ret['link']['status']['9'] == int(wntr.network.base.LinkStatus.Open):
            #     set_values = [('9', 'status', wntr.network.base.LinkStatus.Closed)]
            t, ret = sim.step_sim(set_values=set_values)
            results.append(ret)
            if t > 23.5 * 3600:
                sim.step_kill()
        sim.step_end()
