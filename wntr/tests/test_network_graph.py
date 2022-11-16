import unittest
from os.path import abspath, dirname, join
from unittest import SkipTest

import networkx as nx
import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
netdir = join(testdir, "..", "..", "examples", "networks")


class TestNetworkGraphs(unittest.TestCase):
    def test_weight_graph(self):
        inp_file = join(netdir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        node_weight = wn.query_node_attribute("elevation")
        link_weight = wn.query_link_attribute("length")

        G = wn.to_graph(node_weight, link_weight)

        self.assertEqual(G.nodes["111"]["weight"], 10 * 0.3048)
        self.assertEqual(G["159"]["161"]["177"]["weight"], 2000 * 0.3048)

    def test_weighted_graph_modify_direction(self):
        inp_file = join(netdir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file) 
        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim()
        flowrate = results.link['flowrate'].iloc[-1,:]
        G = wn.to_graph(link_weight=flowrate, modify_direction=True)
        
        # Positive flow, flowrate == graph weight
        name = '173'
        pipe = wn.get_link(name)

        self.assertEqual(flowrate[name],
                         G.edges[pipe.start_node_name, pipe.end_node_name, name]['weight'])
        
        # Negative flow, -flowrate == graph weight
        name = '109'
        pipe = wn.get_link(name)
        
        self.assertEqual(-flowrate[name],
                         G.edges[pipe.end_node_name, pipe.start_node_name, name]['weight'])

    def test_terminal_nodes(self):
        inp_file = join(netdir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        G = wn.to_graph()

        terminal_nodes = wntr.metrics.terminal_nodes(G)
        expected = set(["2", "9"])
        self.assertSetEqual(set(terminal_nodes), expected)

    def test_bridges(self):
        inp_file = join(netdir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        G = wn.to_graph()

        bridges = wntr.metrics.bridges(G)
        expected = set(["9", "10", "110"])
        self.assertSetEqual(set(bridges), expected)

    def test_diameter(self):
        inp_file = join(datadir, "Anytown.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        for pump in wn.pump_name_list[:-1]:  # remove 2 of the 3 pumps
            wn.remove_link(pump)
        G = wn.to_graph()
        udG = G.to_undirected()
        val = nx.diameter(udG)
        excepted = 7  # Davide Soldi et al. (2015) Procedia Engineering
        self.assertEqual(val, excepted)

    def test_central_point_dominance(self):
        inp_file = join(datadir, "Anytown.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        for pump in wn.pump_name_list[:-1]:  # remove 2 of the 3 pumps
            wn.remove_link(pump)
        G = wn.to_graph()

        val = wntr.metrics.central_point_dominance(G)
        expected = 0.23  # Davide Soldi et al. (2015) Procedia Engineering
        error = abs(expected - val)
        self.assertLess(error, 0.01)

    def test_spectral_gap(self):
        inp_file = join(datadir, "Anytown.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        for pump in wn.pump_name_list[:-1]:  # remove 2 of the 3 pumps
            wn.remove_link(pump)
        G = wn.to_graph()

        val = wntr.metrics.spectral_gap(G)
        expected = 1.5149  # Davide Soldi et al. (2015) Procedia Engineering
        error = abs(expected - val)
        self.assertLess(error, 0.01)

    def test_algebraic_connectivity(self):
        inp_file = join(datadir, "Anytown.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        for pump in wn.pump_name_list[:-1]:  # remove 2 of the 3 pumps
            wn.remove_link(pump)
        G = wn.to_graph()

        val = wntr.metrics.algebraic_connectivity(G)
        expected = 0.1708  # Davide Soldi et al. (2015) Procedia Engineering
        error = abs(expected - val)
        raise SkipTest
        self.assertLess(error, 0.01)

    def test_crit_ratio_defrag(self):
        inp_file = join(datadir, "Anytown.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        for pump in wn.pump_name_list[:-1]:  # remove 2 of the 3 pumps
            wn.remove_link(pump)
        G = wn.to_graph()

        val = wntr.metrics.critical_ratio_defrag(G)
        expected = 0.63  # Pandit et al. (2012) Critical Infrastucture Symposium
        error = abs(expected - val)
        raise SkipTest
        self.assertLess(error, 0.01)

    def test_Net1_MultiDiGraph(self):
        inp_file = join(netdir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        G = wn.to_graph()

        node = {
            "11": {"pos": (30.0, 70.0), "type": "Junction"},
            "10": {"pos": (20.0, 70.0), "type": "Junction"},
            "13": {"pos": (70.0, 70.0), "type": "Junction"},
            "12": {"pos": (50.0, 70.0), "type": "Junction"},
            "21": {"pos": (30.0, 40.0), "type": "Junction"},
            "22": {"pos": (50.0, 40.0), "type": "Junction"},
            "23": {"pos": (70.0, 40.0), "type": "Junction"},
            "32": {"pos": (50.0, 10.0), "type": "Junction"},
            "31": {"pos": (30.0, 10.0), "type": "Junction"},
            "2": {"pos": (50.0, 90.0), "type": "Tank"},
            "9": {"pos": (10.0, 70.0), "type": "Reservoir"},
        }

        edge = {
            "11": {"12": {"11": {"type": "Pipe"}}, "21": {"111": {"type": "Pipe"}}},
            "10": {"11": {"10": {"type": "Pipe"}}},
            "13": {"23": {"113": {"type": "Pipe"}}},
            "12": {"13": {"12": {"type": "Pipe"}}, "22": {"112": {"type": "Pipe"}}},
            "21": {"31": {"121": {"type": "Pipe"}}, "22": {"21": {"type": "Pipe"}}},
            "22": {"32": {"122": {"type": "Pipe"}}, "23": {"22": {"type": "Pipe"}}},
            "23": {},
            "32": {},
            "31": {"32": {"31": {"type": "Pipe"}}},
            "2": {"12": {"110": {"type": "Pipe"}}},
            "9": {"10": {"9": {"type": "Pump"}}},
        }

        self.assertEqual(dict(node, **G.nodes), node)
        # assert_dict_contains_subset(node, G.nodes)
        self.assertEqual(dict(edge, **G.adj), edge)
        # assert_dict_contains_subset(edge, G.adj)


if __name__ == "__main__":
    unittest.main()
