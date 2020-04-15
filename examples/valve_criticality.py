import wntr
import matplotlib.pyplot as plt

def calc_valve_criticality(G, valve_layer, criticality_type='length', 
                           screen_updating=False):
    """

    Parameters
    ----------
    G: networkx MultiDiGraph
        Graph
        
    valve_layer: pandas DataFrame
        Valve layer, defined by node and link pairs (for example, valve 0 is 
        on link A and protects node B). The valve_layer DataFrame is indexed by
        valve number, with columns named 'node' and 'link'.
    
    criticality_type: string, optional
        Which type of criticality calculation to make for each valve.
        The default is 'length'. Other options are 'demand' and 'valve'.
    
    screen_updating: boolean, optional
        Determines whether to show valve criticality calculations realtime. 
        The default is False.

    Returns
    -------
    VC: dictionary
        A dictionary with valve numbers as keys and valve criticalities as 
        indexes. Also includes a 'Type' key which is used for plotting.

    """
    # Assess the number of valves in the system
    n_valves = len(valve_layer)
    
    # Assign a segment to each node and link, determine number of links/nodes in each segment
    node_segments, link_segments, seg_sizes = wntr.metrics.topographic.valve_segments(G, valve_layer)
   
    
    if criticality_type == 'length':
        # Calculate the length-based valve crticiality
        if screen_updating:
            print('Length-Based Valve Criticality')
        VC = {'Type': 'length'}
        
        link_lengths = wn.query_link_attribute('length')
        
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
            if screen_updating:    
                print('Valve: ', i, '\t\tVC_len = %.1f' %VC_len_i)
            VC[i] = VC_len_i
            
            
    if criticality_type == 'demand':
        # Calculate the demand-based valve crticiality
        if screen_updating:
            print('\n\nDemand-Based Valve Criticality')
        VC = {'Type': 'demand'}
        node_demands = wn.query_node_attribute('base_demand')
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
            if screen_updating:
                print('Valve: ', i, '\t\tVC_dem = %.1f' %VC_dem_i)
            VC[i] = VC_dem_i
            
            
    if criticality_type == 'valve':
        # Calculate valve-based valve criticality
        if screen_updating:
            print('\n\nValve-Based Valve Criticality')
        VC = {'Type': 'valve'}
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
            if screen_updating:
                print('Valve: ', i, '\t\tVC_val = ', VC_val_i)
            VC[i] = VC_val_i
            
    
    return VC
        
        
if __name__ == '__main__':
    plt.close('all')
    seed = 5
    
    # Create a water network model
    inp_file = 'networks/Net3.inp'
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    # Returns a networkx MultiDiGraph of the water network model for segmentation
    G = wn.get_graph()    
    
    # Generate a valve layer using strategic valve placement
    valve_layer = wntr.network.generate_valve_layer(wn, 'strategic', 1, 
                                                    seed=seed)
    
    # Select which type of valve criticality to calculate
    criticality_type = 'length' # options are 'length', 'demand', and 'valve'
    
    # Calculate the valve criticality for each valve
    valve_criticality = calc_valve_criticality(G, valve_layer, 
                                               criticality_type=criticality_type)
    
    # plot network results
    filename = 'valve_criticality_map'
    title = 'Valve Criticality: ' + valve_criticality['Type']
    fig, ax = plt.subplots(1, 1, figsize=(6, 6))
    wntr.graphics.plot_network(wn, valve_layer=valve_layer, 
                               valve_criticality=valve_criticality, 
                               title=title,
                               node_size=10, ax=ax, filename=filename)

    
    