from __future__ import print_function
import unittest
import sys
import os
import time
import numpy as np
from os.path import abspath, dirname, join

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir,'networks_for_testing')
ex_datadir = join(testdir,'..','..','examples','networks')
results_dir = join(testdir,'performance_results')

class TestPerformance(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(results_dir)
        import wntr
        self.wntr = wntr

        files = [f for f in os.listdir(results_dir)]
        if 'performance_results.py' in files:
            import performance_results as past_results

            self.year = past_results.year
            self.month = past_results.month
            self.day = past_results.day

            self.Net1_total_sim_time = past_results.Net1_total_sim_time
            self.Net3_total_sim_time = past_results.Net3_total_sim_time
            self.Net6_mod_total_sim_time = past_results.Net6_mod_total_sim_time

            self.Net1_time_per_step = past_results.Net1_time_per_step
            self.Net3_time_per_step = past_results.Net3_time_per_step
            self.Net6_mod_time_per_step = past_results.Net6_mod_time_per_step

            self.Net1_num_steps = past_results.Net1_num_steps
            self.Net3_num_steps = past_results.Net3_num_steps
            self.Net6_mod_num_steps = past_results.Net6_mod_num_steps

            self.Net1_avg_head_diff = past_results.Net1_avg_head_diff
            self.Net3_avg_head_diff = past_results.Net3_avg_head_diff
            self.Net6_mod_avg_head_diff = past_results.Net6_mod_avg_head_diff

            self.Net1_avg_demand_diff = past_results.Net1_avg_demand_diff
            self.Net3_avg_demand_diff = past_results.Net3_avg_demand_diff
            self.Net6_mod_avg_demand_diff = past_results.Net6_mod_avg_demand_diff

            self.Net1_avg_flow_diff = past_results.Net1_avg_flow_diff
            self.Net3_avg_flow_diff = past_results.Net3_avg_flow_diff
            self.Net6_mod_avg_flow_diff = past_results.Net6_mod_avg_flow_diff

            self.Net1_head_diff_std_dev = past_results.Net1_head_diff_std_dev
            self.Net3_head_diff_std_dev = past_results.Net3_head_diff_std_dev
            self.Net6_mod_head_diff_std_dev = past_results.Net6_mod_head_diff_std_dev

            self.Net1_demand_diff_std_dev = past_results.Net1_demand_diff_std_dev
            self.Net3_demand_diff_std_dev = past_results.Net3_demand_diff_std_dev
            self.Net6_mod_demand_diff_std_dev = past_results.Net6_mod_demand_diff_std_dev

            self.Net1_flow_diff_std_dev = past_results.Net1_flow_diff_std_dev
            self.Net3_flow_diff_std_dev = past_results.Net3_flow_diff_std_dev
            self.Net6_mod_flow_diff_std_dev = past_results.Net6_mod_flow_diff_std_dev

        else:
            self.year = []
            self.month = []
            self.day = []

            self.Net1_total_sim_time = []
            self.Net3_total_sim_time = []
            self.Net6_mod_total_sim_time = []

            self.Net1_time_per_step = []
            self.Net3_time_per_step = []
            self.Net6_mod_time_per_step = []

            self.Net1_num_steps = []
            self.Net3_num_steps = []
            self.Net6_mod_num_steps = []

            self.Net1_avg_head_diff = []
            self.Net3_avg_head_diff = []
            self.Net6_mod_avg_head_diff = []

            self.Net1_avg_demand_diff = []
            self.Net3_avg_demand_diff = []
            self.Net6_mod_avg_demand_diff = []

            self.Net1_avg_flow_diff = []
            self.Net3_avg_flow_diff = []
            self.Net6_mod_avg_flow_diff = []

            self.Net1_head_diff_std_dev = []
            self.Net3_head_diff_std_dev = []
            self.Net6_mod_head_diff_std_dev = []

            self.Net1_demand_diff_std_dev = []
            self.Net3_demand_diff_std_dev = []
            self.Net6_mod_demand_diff_std_dev = []

            self.Net1_flow_diff_std_dev = []
            self.Net3_flow_diff_std_dev = []
            self.Net6_mod_flow_diff_std_dev = []

        self.year.append(time.localtime().tm_year)
        self.month.append(time.localtime().tm_mon)
        self.day.append(time.localtime().tm_mday)

    @classmethod
    def tearDownClass(self):
        f = open(os.path.join(results_dir, 'performance_results.py'),'w')
        f.write('year = {0}\n'.format(self.year))
        f.write('month = {0}\n'.format(self.month))
        f.write('day = {0}\n'.format(self.day))

        f.write('Net1_total_sim_time = {0}\n'.format(self.Net1_total_sim_time))
        f.write('Net3_total_sim_time = {0}\n'.format(self.Net3_total_sim_time))
        f.write('Net6_mod_total_sim_time = {0}\n'.format(self.Net6_mod_total_sim_time))

        f.write('Net1_time_per_step = {0}\n'.format(self.Net1_time_per_step))
        f.write('Net3_time_per_step = {0}\n'.format(self.Net3_time_per_step))
        f.write('Net6_mod_time_per_step = {0}\n'.format(self.Net6_mod_time_per_step))

        f.write('Net1_num_steps = {0}\n'.format(self.Net1_num_steps))
        f.write('Net3_num_steps = {0}\n'.format(self.Net3_num_steps))
        f.write('Net6_mod_num_steps = {0}\n'.format(self.Net6_mod_num_steps))

        f.write('Net1_avg_head_diff = {0}\n'.format(self.Net1_avg_head_diff))
        f.write('Net3_avg_head_diff = {0}\n'.format(self.Net3_avg_head_diff))
        f.write('Net6_mod_avg_head_diff = {0}\n'.format(self.Net6_mod_avg_head_diff))

        f.write('Net1_avg_demand_diff = {0}\n'.format(self.Net1_avg_demand_diff))
        f.write('Net3_avg_demand_diff = {0}\n'.format(self.Net3_avg_demand_diff))
        f.write('Net6_mod_avg_demand_diff = {0}\n'.format(self.Net6_mod_avg_demand_diff))

        f.write('Net1_avg_flow_diff = {0}\n'.format(self.Net1_avg_flow_diff))
        f.write('Net3_avg_flow_diff = {0}\n'.format(self.Net3_avg_flow_diff))
        f.write('Net6_mod_avg_flow_diff = {0}\n'.format(self.Net6_mod_avg_flow_diff))

        f.write('Net1_head_diff_std_dev = {0}\n'.format(self.Net1_head_diff_std_dev))
        f.write('Net3_head_diff_std_dev = {0}\n'.format(self.Net3_head_diff_std_dev))
        f.write('Net6_mod_head_diff_std_dev = {0}\n'.format(self.Net6_mod_head_diff_std_dev))

        f.write('Net1_demand_diff_std_dev = {0}\n'.format(self.Net1_demand_diff_std_dev))
        f.write('Net3_demand_diff_std_dev = {0}\n'.format(self.Net3_demand_diff_std_dev))
        f.write('Net6_mod_demand_diff_std_dev = {0}\n'.format(self.Net6_mod_demand_diff_std_dev))

        f.write('Net1_flow_diff_std_dev = {0}\n'.format(self.Net1_flow_diff_std_dev))
        f.write('Net3_flow_diff_std_dev = {0}\n'.format(self.Net3_flow_diff_std_dev))
        f.write('Net6_mod_flow_diff_std_dev = {0}\n'.format(self.Net6_mod_flow_diff_std_dev))

        f.close()

    def test_Net1_performance(self):
        t0 = time.time()
        inp_file = join(ex_datadir, 'Net1.inp')
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        t1 = time.time()

        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        head_diff_list = []
        demand_diff_list = []
        flow_diff_list = []
        for name, node in wn.nodes():
            for t in results.time:
                head_diff_n = abs(results.node.at['head',t,name]-epa_res.node.at['head',t,name])
                demand_diff_n = abs(results.node.at['demand',t,name]-epa_res.node.at['demand',t,name])
                head_diff_list.append(head_diff_n)
                demand_diff_list.append(demand_diff_n)
        for name, link in wn.links():
            for t in results.time:
                flow_diff_l = abs(results.link.at['flowrate',t,name]-epa_res.link.at['flowrate',t,name])
                flow_diff_list.append(flow_diff_l)

        self.Net1_avg_head_diff.append(np.average(head_diff_list))
        self.Net1_avg_demand_diff.append(np.average(demand_diff_list))
        self.Net1_avg_flow_diff.append(np.average(flow_diff_list))

        self.Net1_head_diff_std_dev.append(np.std(head_diff_list))
        self.Net1_demand_diff_std_dev.append(np.std(demand_diff_list))
        self.Net1_flow_diff_std_dev.append(np.std(flow_diff_list))

        self.Net1_total_sim_time.append(t1-t0)
        self.Net1_time_per_step.append(np.average(sim.time_per_step))
        self.Net1_num_steps.append(len(sim.time_per_step))


        self.assertLess(np.average(head_diff_list), 6e-5)
        self.assertLess(np.average(demand_diff_list), 2.3e-8)
        self.assertLess(np.average(flow_diff_list), 5e-8)
        self.assertLess(np.std(head_diff_list), .00015)
        self.assertLess(np.std(demand_diff_list), 1.1e-7)
        self.assertLess(np.std(flow_diff_list), 1.3e-7)

    def test_Net3_performance(self):
        t0 = time.time()

        inp_file = join(ex_datadir, 'Net3.inp')
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        t1 = time.time()

        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        head_diff_list = []
        demand_diff_list = []
        flow_diff_list = []
        for name, node in wn.nodes():
            for t in results.time:
                head_diff_n = abs(results.node.at['head',t,name]-epa_res.node.at['head',t,name])
                demand_diff_n = abs(results.node.at['demand',t,name]-epa_res.node.at['demand',t,name])
                head_diff_list.append(head_diff_n)
                demand_diff_list.append(demand_diff_n)
        for name, link in wn.links():
            for t in results.time:
                flow_diff_l = abs(results.link.at['flowrate',t,name]-epa_res.link.at['flowrate',t,name])
                flow_diff_list.append(flow_diff_l)

        self.Net3_avg_head_diff.append(np.average(head_diff_list))
        self.Net3_avg_demand_diff.append(np.average(demand_diff_list))
        self.Net3_avg_flow_diff.append(np.average(flow_diff_list))

        self.Net3_head_diff_std_dev.append(np.std(head_diff_list))
        self.Net3_demand_diff_std_dev.append(np.std(demand_diff_list))
        self.Net3_flow_diff_std_dev.append(np.std(flow_diff_list))

        self.Net3_total_sim_time.append(t1-t0)
        self.Net3_time_per_step.append(np.average(sim.time_per_step))
        self.Net3_num_steps.append(len(sim.time_per_step))

        self.assertLess(np.average(head_diff_list), 3e-5)
        self.assertLess(np.average(demand_diff_list), 1.5e-8)
        self.assertLess(np.average(flow_diff_list), 2.0e-7)
        self.assertLess(np.std(head_diff_list), 3e-5)
        self.assertLess(np.std(demand_diff_list), 1.1e-7)
        self.assertLess(np.std(flow_diff_list), 1.3e-6)

    def test_Net6_mod_performance(self):
        t0 = time.time()

        inp_file = join(ex_datadir,'Net6.inp')
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.options.duration = 24*3600
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = sim.run_sim()

        t1 = time.time()

        epa_sim = self.wntr.sim.EpanetSimulator(wn)
        epa_res = epa_sim.run_sim()

        head_diff_list = []
        demand_diff_list = []
        flow_diff_list = []
        for name, node in wn.nodes():
            for t in results.time:
                head_diff_n = abs(results.node.at['head',t,name]-epa_res.node.at['head',t,name])
                demand_diff_n = abs(results.node.at['demand',t,name]-epa_res.node.at['demand',t,name])
                head_diff_list.append(head_diff_n)
                demand_diff_list.append(demand_diff_n)
        for name, link in wn.links():
            for t in results.time:
                flow_diff_l = abs(results.link.at['flowrate',t,name]-epa_res.link.at['flowrate',t,name])
                flow_diff_list.append(flow_diff_l)

        self.Net6_mod_avg_head_diff.append(np.average(head_diff_list))
        self.Net6_mod_avg_demand_diff.append(np.average(demand_diff_list))
        self.Net6_mod_avg_flow_diff.append(np.average(flow_diff_list))

        self.Net6_mod_head_diff_std_dev.append(np.std(head_diff_list))
        self.Net6_mod_demand_diff_std_dev.append(np.std(demand_diff_list))
        self.Net6_mod_flow_diff_std_dev.append(np.std(flow_diff_list))

        self.Net6_mod_total_sim_time.append(t1-t0)
        self.Net6_mod_time_per_step.append(np.average(sim.time_per_step))
        self.Net6_mod_num_steps.append(len(sim.time_per_step))

        self.assertLess(np.average(head_diff_list), .006)
        self.assertLess(np.average(demand_diff_list), 9e-6)
        self.assertLess(np.average(flow_diff_list), 9e-5)
        self.assertLess(np.std(head_diff_list), .07)
        self.assertLess(np.std(demand_diff_list), .0009)
        self.assertLess(np.std(flow_diff_list), .003)

if __name__ == '__main__':
    unittest.main()
