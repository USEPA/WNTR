import unittest
import pandas as pd
from os.path import abspath, dirname, join
import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, 'networks_for_testing')
ex_datadir = join(testdir,'..','..','examples','networks')


class TestSegmentation(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        inp_file = join(ex_datadir, 'Net3.inp')
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        G = self.wn.get_graph()
        self.valves = pd.read_csv(join(test_datadir, 'valve_layer_stategic_1.csv'), index_col=0, dtype='object')
        self.node_segments, self.link_segments, self.seg_size = wntr.metrics.topographic.valve_segments(G, self.valves)
        
    @classmethod
    def tearDownClass(self):
        pass

        
    def test_valve_criticality_length(self):
        # test Net3        
#        import matplotlib
#        cmap = matplotlib.colors.ListedColormap(np.random.rand(num_segments,3))
#        wntr.graphics.plot_network(self.wn2, node_segments, link_segments, valve_layer=valves,
#                                   node_cmap=cmap, link_cmap=cmap,
#                                   node_range=[0.5,num_segments+0.5], 
#                                   link_range=[0.5,num_segments+0.5])

        # Gather the link lengths for the length-based criticality calculation
        link_lengths = self.wn.query_link_attribute('length')
    
        # Calculate the length-based valve criticality for each valve
        valve_crit = wntr.metrics.topographic.valve_criticality_length(link_lengths, 
                                                                   self.valves, 
                                                                   self.node_segments, 
                                                                   self.link_segments)
        
        # import csv    
        # with open('valve_crit_length.csv', 'w', newline="") as csv_file:  
        #     writer = csv.writer(csv_file)
        #     for key, value in valve_crit.items():
        #        writer.writerow([key, value])
        
        # # plot valve criticality results with the network
        # filename = 'valve_criticality_map.jpg'
        # title = 'Valve Criticality: ' + valve_crit['Type']
        # wntr.graphics.plot_network(self.wn, valve_layer=self.valves, 
        #                            valve_criticality=valve_crit, 
        #                            title=title, node_size=10, filename=filename)
        
        
        del valve_crit['Type']
        expected_valve_crit = pd.read_csv(join(test_datadir, 'valve_crit_length.csv'), 
                                              index_col=0, 
                                              squeeze=True).to_dict()
        for valve in range(max(valve_crit, key=int)):
            self.assertEqual(round(valve_crit[valve],4), round(expected_valve_crit[valve],4))
 
    def test_valve_criticality_demand(self):
        # test Net3
#        import matplotlib
#        cmap = matplotlib.colors.ListedColormap(np.random.rand(num_segments,3))
#        wntr.graphics.plot_network(self.wn2, node_segments, link_segments, valve_layer=valves,
#                                   node_cmap=cmap, link_cmap=cmap,
#                                   node_range=[0.5,num_segments+0.5], 
#                                   link_range=[0.5,num_segments+0.5])

        # Gather the node demands for the demand-based criticality calculation
        node_demands = self.wn.query_node_attribute('base_demand')
    
        # Calculate the demand-based valve criticality for each valve
        valve_crit = wntr.metrics.topographic.valve_criticality_demand(node_demands, 
                                                                   self.valves, 
                                                                   self.node_segments, 
                                                                   self.link_segments)

        
        # import csv    
        # with open('valve_crit_demand.csv', 'w', newline="") as csv_file:  
        #     writer = csv.writer(csv_file)
        #     for key, value in valve_crit.items():
        #         writer.writerow([key, value])
        
        # # plot valve criticality results with the network
        # filename = 'valve_criticality_map.jpg'
        # title = 'Valve Criticality: ' + valve_crit['Type']
        # wntr.graphics.plot_network(self.wn, valve_layer=self.valves, 
        #                            valve_criticality=valve_crit, 
        #                            title=title, node_size=10, filename=filename)
        
        del valve_crit['Type']        
        expected_valve_crit = pd.read_csv(join(test_datadir, 'valve_crit_demand.csv'), 
                                              index_col=0, 
                                              squeeze=True).to_dict()
        for valve in range(max(valve_crit, key=int)):
            self.assertEqual(round(valve_crit[valve],4), round(expected_valve_crit[valve],4))

    def test_valve_criticality(self):
        # test Net3
#        import matplotlib
#        cmap = matplotlib.colors.ListedColormap(np.random.rand(num_segments,3))
#        wntr.graphics.plot_network(self.wn2, node_segments, link_segments, valve_layer=valves,
#                                   node_cmap=cmap, link_cmap=cmap,
#                                   node_range=[0.5,num_segments+0.5], 
#                                   link_range=[0.5,num_segments+0.5])

    
        # Calculate the valve-based valve criticality for each valve
        valve_crit = wntr.metrics.topographic.valve_criticality(self.valves, 
                                                                self.node_segments, 
                                                                self.link_segments)

        # import csv    
        # with open('valve_crit_valve.csv', 'w', newline="") as csv_file:  
        #     writer = csv.writer(csv_file)
        #     for key, value in valve_crit.items():
        #         writer.writerow([key, value])
        
        # # plot valve criticality results with the network
        # filename = 'valve_criticality_map.jpg'
        # title = 'Valve Criticality: ' + valve_crit['Type']
        # wntr.graphics.plot_network(self.wn, valve_layer=self.valves, 
        #                            valve_criticality=valve_crit, 
        #                            title=title, node_size=10, filename=filename)
                
        del valve_crit['Type']        
        expected_valve_crit = pd.read_csv(join(test_datadir, 'valve_crit_valve.csv'), 
                                              index_col=0, 
                                              squeeze=True).to_dict()

        self.assertDictEqual(valve_crit, expected_valve_crit)

        
if __name__ == '__main__':
    unittest.main() 