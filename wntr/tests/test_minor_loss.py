import unittest
from nose import SkipTest
import wntr


class TestMinorLosses(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        pass

    @classmethod
    def tearDownClass(self):
        pass

    def test_pipe_minor_loss(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 2
        wn.add_reservoir(name='r1', base_head=20.0)
        wn.add_junction(name='j1', base_demand=0.1)
        wn.add_pipe(name='p1', start_node_name='r1', end_node_name='j1', minor_loss=100.0)
        sim = wntr.sim.WNTRSimulator(wn, mode='DD')

        results1 = sim.run_sim()
        wn.write_inpfile('tmp.inp', 'CMH')
        
        raise SkipTest # EPANET seg faults (on Travis)
        
        wn2 = wntr.network.WaterNetworkModel('tmp.inp')
        sim = wntr.sim.EpanetSimulator(wn2)
        results2 = sim.run_sim()

        head1 = results1.node['head'].loc[0, 'j1']
        head2 = results2.node['head'].loc[0, 'j1']
        head_diff = abs(head1-head2)
        self.assertLess(head_diff, 0.01)
