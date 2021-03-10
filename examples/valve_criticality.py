"""
The following example uses the valve placement, segmentation, and criticality 
calculation algorithms in WNTR to create valves, analyze the network, and plot 
valves on a network colored by criticality.
"""

import wntr
import matplotlib.pyplot as plt

plt.close('all')
seed = 5

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Generate a valve layer using strategic valve placement
valve_layer = wntr.network.generate_valve_layer(wn, 'strategic', 2, seed=seed)

# Returns a networkx MultiDiGraph of the water network model for segmentation
G = wn.get_graph()   
 
# Calculate segment number for each node and link
node_segments, link_segments, seg_sizes = wntr.metrics.topographic.valve_segments(G, valve_layer)

# Use one of three methods to calculate valve criticality
valve_criticality_type = 'length' # options: 'length', 'demand', 'valve'
if valve_criticality_type == 'length':
    # Gather the link lengths for the length-based criticality calculation
    link_lengths = wn.query_link_attribute('length')

    # Calculate the length-based valve criticality for each valve
    valve_crit = wntr.metrics.topographic.valve_criticality_length(link_lengths, 
                                                               valve_layer, 
                                                               node_segments, 
                                                               link_segments)
if valve_criticality_type == 'demand':
    # Gather the link lengths for the demand-based criticality calculation
    node_demands = wn.query_node_attribute('base_demand')

    # Calculate the length-based valve criticality for each valve
    valve_crit = wntr.metrics.topographic.valve_criticality_demand(node_demands, 
                                                               valve_layer, 
                                                               node_segments, 
                                                               link_segments)
if valve_criticality_type == 'valve':
    # Calculate the valve-based valve criticality for each valve
    valve_crit = wntr.metrics.topographic.valve_criticality(valve_layer, 
                                                               node_segments, 
                                                               link_segments)

# plot valve criticality results with the network
filename = 'valve_criticality_map'
title = 'Valve Criticality: ' + valve_crit['Type']
wntr.graphics.plot_network(wn, valve_layer=valve_layer, 
                           valve_criticality=valve_crit, 
                           title=title, node_size=10, filename=filename)
