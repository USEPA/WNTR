from wntr.network import Tank, Pipe, Pump, Valve
import numpy as np  

def cost(wn, tank_cost, pipe_cost, valve_cost, pump_cost):
    """ Compute network cost.
    
    Parameters
    ----------
    tank_cost : pd.Series
        index = tank volume (m3)
        col = annual cost ($)
    """
    
    # Initialize network construction cost
    network_cost = 0
    
    # Tank construction cost
    for node_name, node in wn.nodes(Tank):
        tank_diameter = wn.get_node(node_name).diameter
        tank_minlevel = wn.get_node(node_name).min_level
        tank_maxlevel = wn.get_node(node_name).max_level
        tank_volume = (tank_diameter/2)**2*(tank_maxlevel-tank_minlevel)
        idx = (np.abs(tank_cost[:,0]-tank_volume)).argmin()
        network_cost = network_cost + tank_cost[idx,1]
    
    # Pipe construction cost
    for link_name, link in wn.links(Pipe):
        link_length = wn.get_link(link_name).length
        link_diameter = wn.get_link(link_name).diameter
        idx = (np.abs(pipe_cost[:,0]-link_diameter)).argmin()
        network_cost = network_cost + pipe_cost[idx,1]*link_length   
    
    # Pump construction cost
    for link_name, link in wn.links(Pump):        
        network_cost = network_cost + pump_cost
        
    # Valve construction cost    
    for link_name, link in wn.links(Valve):        
        link_diameter =  wn.get_link(link_name).diameter
        idx = (np.abs(valve_cost[:,0]-link_diameter)).argmin()
        network_cost = network_cost + valve_cost[idx,1]
    
    return network_cost
