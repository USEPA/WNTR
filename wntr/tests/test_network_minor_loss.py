import unittest

import wntr


class TestMinorLosses(unittest.TestCase):
    def test_pipe_minor_loss(self):
        wn = wntr.network.WaterNetworkModel()
        wn.options.time.duration = 3600 * 2
        wn.add_reservoir(name="r1", base_head=20.0)
        wn.add_junction(name="j1", base_demand=0.1)
        wn.add_pipe(
            name="p1", start_node_name="r1", end_node_name="j1", minor_loss=100.0
        )
        wn.options.hydraulic.demand_model = "DDA"
        sim = wntr.sim.WNTRSimulator(wn)

        results1 = sim.run_sim()
        temp_inp_file = "temp.inp"
        wntr.network.write_inpfile(wn, temp_inp_file, "CMH")

        wn2 = wntr.network.WaterNetworkModel(temp_inp_file)
        sim = wntr.sim.EpanetSimulator(wn2)
        results2 = sim.run_sim()

        head1 = results1.node["head"].j1.iloc[0]
        head2 = results2.node["head"].j1.iloc[0]
        head_diff = abs(head1 - head2)
        self.assertLess(head_diff, 0.01)
