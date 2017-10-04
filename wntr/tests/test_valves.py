import unittest
import wntr


class TestTCVs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_pipe_minor_loss(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.duration = 3600 * 4
        wn.add_reservoir(name='r1', base_head=20.0)
        wn.add_junction(name='j1', base_demand=0.0)
        wn.add_junction(name='j2', base_demand=0.1)
        wn.add_pipe(name='p1', start_node_name='r1', end_node_name='j1', length=10.0, diameter=0.3048,
                    roughness=100, minor_loss=0.0)
        wn.add_valve(name='v1', start_node_name='j1', end_node_name='j2', diameter=0.3048, valve_type='TCV',
                     minor_loss=30.0, setting=60.0)

        valve = wn.get_link('v1')
        open_action = wntr.network.ControlAction(valve, 'status', wntr.network.LinkStatus.Opened)
        control = wntr.network.TimeControl(wn, 7200, time_flag='SIM_TIME', daily_flag=False, control_action=open_action)
        wn.add_control('c1', control)

        sim = wntr.sim.WNTRSimulator(wn, mode='DD')

        results1 = sim.run_sim()

        sim = wntr.sim.EpanetSimulator(wn)
        results2 = sim.run_sim()

        for t in results2.time:
            head1 = results1.node['head', t, 'j2']
            head2 = results2.node['head', t, 'j2']
            head_diff = abs(head1 - head2)
            self.assertLess(head_diff, 0.01)
