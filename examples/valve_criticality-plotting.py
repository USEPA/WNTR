import wntr
import matplotlib.pyplot as plt
import time

plt.close('all')
seed = 5

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Returns a networkx MultiDiGraph of the water network model for segmentation
G = wn.get_graph()    

# Generate a valve layer using strategic valve placement
valve_layer = wntr.network.generate_valve_layer(wn, 'strategic', 1, seed=seed)
n_valves = len(valve_layer)

# Assign a segment to each node and link, determine number of links/nodes in each segment
node_segments, link_segments, seg_sizes = wntr.metrics.topographic.valve_segments(G, valve_layer)

# Query link lengths and node demands for criticality calculations
link_lengths = wn.query_link_attribute('length')
node_demands = wn.query_node_attribute('base_demand')

tic = time.time()


# Calculate the length-based valve crticiality
print('Length-Based Valve Criticality')
VC_len = {'Type': 'length'}

for i in range(n_valves):
    # identify the node-side and link-side segments
    node_seg = node_segments[valve_layer.loc[i,'node']]
    link_seg = link_segments[valve_layer.loc[i,'link']]
    
    # if the node and link are in the same segment, set criticality to 0
    if node_seg == link_seg:
        VC_len_i = 0
    else:
        # calculate total length of links in the node segment
        links_in_node_seg = link_segments[link_segments == node_seg].index
        L_node = link_lengths[links_in_node_seg].sum()
        # calculate total length of links in the link segment
        links_in_link_seg = link_segments[link_segments == link_seg].index
        L_link = link_lengths[links_in_link_seg].sum()
        # calculate link length criticality for the valve
        if L_node == 0 and L_link == 0:
            VC_len_i = 0.0
        else:
            VC_len_i = 100 * ((L_link + L_node) / max(L_link, L_node) - 1)
        
    print('Valve: ', i, '\t\tVC_len = %.1f' %VC_len_i)
    VC_len[i] = VC_len_i


# Calculate the demand-based valve crticiality
print('\n\nDemand-Based Valve Criticality')
VC_dem = {'Type': 'demand'}

for i in range(n_valves):
    # identify the node-side and link-side segments
    node_seg = node_segments[valve_layer.loc[i,'node']]
    link_seg = link_segments[valve_layer.loc[i,'link']]
    
    # if the node and link are in the same segment, set criticality to 0
    if node_seg == link_seg:
        VC_dem_i = 0.0
    else:
        # calculate total demand in the node segment
        nodes_in_node_seg = node_segments[node_segments == node_seg].index
        D_node = node_demands[nodes_in_node_seg].sum()
        # calculate total demand in the link segment
        nodes_in_link_seg = node_segments[node_segments == link_seg].index
        D_link = node_demands[nodes_in_link_seg].sum()
        # calculate demand criticality for the valve
        if D_node == 0 and D_link == 0:
            VC_dem_i = 0
        else:
            VC_dem_i = 100 * ((D_link + D_node) / max(D_link, D_node) - 1)
        
    print('Valve: ', i, '\t\tVC_dem = %.1f' %VC_dem_i)
    VC_dem[i] = VC_dem_i


# Calculate valve-based valve criticality
print('\n\nValve-Based Valve Criticality')
VC_val = {'Type': 'valve'}

for i in range(n_valves):
    # identify the node-side and link-side segments
    node_seg = node_segments[valve_layer.loc[i,'node']]
    link_seg = link_segments[valve_layer.loc[i,'link']]
    
    # if the node and link are in the same segment, set criticality to 0
    if node_seg == link_seg:
        VC_val_i = 0
    
    else:
        V_list = []
        # identify links and nodes in surrounding segments
        links_in_segs = link_segments[(link_segments == link_seg) | (link_segments == node_seg)].index
        nodes_in_segs = node_segments[(node_segments == link_seg) | (node_segments == node_seg)].index
        # add unique valves to the V_list from the link list
        for link in links_in_segs:
            valves = valve_layer[valve_layer['link'] == link].index
            if len(valves) == 0:
                pass
            else:
                for valve in valves:
                    if valve in V_list:
                        pass
                    else:
                        V_list.append(valve)
        # add unique valves to the V_list from the node list
        for node in nodes_in_segs:
            valves = valve_layer[valve_layer['node'] == node].index
            if len(valves) == 0:
                pass
            else:
                for valve in valves:
                    if valve in V_list:
                        pass
                    else:
                        V_list.append(valve)
        # calculate valve-based criticality for the valve
        # count the number of valves in the list, minus the valve in question
        VC_val_i = len(V_list) - 1
        
    print('Valve: ', i, '\t\tVC_val = ', VC_val_i)
    VC_val[i] = VC_val_i

print('\n\nValve Criticality Analysis Time: ', round(time.time() - tic,2))


# plot network results
VC = VC_val
title = 'Valve Criticality: ', VC['Type']
fig, ax = plt.subplots(1, 1, figsize=(6, 6))
# this line requires changes to the wntr.graphics.plot_network code
wntr.graphics.plot_network(wn, valve_layer=valve_layer, 
                           valve_criticality=VC, 
                           title=title,
                           node_size=10, ax=ax)
plt.savefig(str(VC['Type'])+'-based_valve_criticality_map.pdf')