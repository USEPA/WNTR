"""
The wntr.stormwater.metrics module includes methods to compute
topographic and hydraulic metrics.
"""
import networkx as nx
import pandas as pd

from wntr.metrics.topographic import *
from wntr.stormwater.network import StormWaterNetworkModel

def headloss(head, swn, link_names=None):
    """
    Headloss across links [ft or m]

    Parameters
    ------------
    head : pandas DataFrame
        Head values at nodes, from simulation results
        (index = times, columns = node names)
    swn : wntr StormWaterNetworkModel
        Stormwater network model, used to extract start and end
        nodes from links.
    link_names : list of strings (optional, default = swn.link_name_list)
        List of link names

    Returns
    --------
    pandas DataFrame with headloss in feet (US Customary units) or meters
    (SI Units) (index = times, columns = link names)

    """
    assert isinstance(head, pd.DataFrame)
    assert isinstance(swn, StormWaterNetworkModel)
    assert isinstance(link_names, (type(None), list))
    
    if link_names is None:
        link_names = swn.link_name_list
        
    time = head.index
    headloss = pd.DataFrame(data=None, index=time, columns=link_names)

    for name in link_names:
        link = swn.get_link(name)
        start_node = link.start_node_name
        end_node = link.end_node_name
        start_head = head.loc[:, start_node]
        end_head = head.loc[:, end_node]
        headloss.loc[:, name] = end_head - start_head

    return headloss


def pump_power(flowrate, headloss, flow_units, efficiency=100):
    """
    Pump power [kW]

    Parameters
    ------------
    flowrate : pandas DataFrame
        Pump flowrate, from simulation results
        (index = times, columns = pump names)
    headloss : pandas DataFrame
        Pump headloss, from simulation results (see `headloss` function)
        (index = times, columns = pump names)
    flow_units : str
        Stormwater network model flow units
    efficiency : float (optional, default = 100)
        Pump efficiency

    Returns
    --------
    pandas DataFrame with pump power in kW 
    (index = times, columns = pump names)

    """
    assert isinstance(flowrate, pd.DataFrame)
    assert isinstance(headloss, pd.DataFrame)
    assert isinstance(flow_units, str)
    assert flow_units in ['CFS', 'GPM', 'MGD', 'CMS', 'LPS', 'MLD']
    assert isinstance(efficiency, (int, float))
    assert 0 <= efficiency <= 100
    
    # Convert headloss to meters
    if flow_units in ['CFS', 'GPM ', 'MGD']:
        headloss = headloss*0.3048

    # Convert all flow units to CMS
    if flow_units == 'CFS':
        flowrate = flowrate*(0.3048**3)
    elif flow_units == 'GPM':
        flowrate = flowrate*15850.3
    elif flow_units == 'MGD':
        flowrate = flowrate*(15850.3/(24*60*1e6))
    elif flow_units == 'LPS':
        flowrate = flowrate*0.001
    elif flow_units == 'MLD':
        flowrate = flowrate*(0.001/(24*3600*1e6))

    power_W = 1000.0 * 9.81 * headloss * flowrate / (efficiency/100) # Watts = J/s
    power_kW = power_W/1000

    return power_kW

def pump_energy(flowrate, headloss, flow_units, efficiency=100):
    """
    Pump energy use [kW-hr]
    
    Parameters
    ------------
    flowrate : pandas DataFrame
        Pump flowrate, from simulation results
        (index = times, columns = pump names)
    headloss : pandas DataFrame
        Pump headloss, from simulation results (see `headloss` function)
        (index = times, columns = pump names)
    flow_units : str
        Stormwater network model flow units
    efficiency : float (optional, default = 100)
        Pump efficiency
        
    Returns
    --------
    pandas DataFrame with pump energy in kW-hr 
    (index = times, columns = pump names)
    
    """
    assert isinstance(flowrate, pd.DataFrame)
    assert isinstance(headloss, pd.DataFrame)
    assert isinstance(flow_units, str)
    assert flow_units in ['CFS', 'GPM', 'MGD', 'CMS', 'LPS', 'MLD']
    assert isinstance(efficiency, (int, float))
    assert 0 <= efficiency <= 100
    
    power_kW = pump_power(flowrate, headloss, flow_units, efficiency) 
    time_delta = flowrate.index[1] - flowrate.index[0]
    time_hrs = time_delta.seconds/3600
    
    energy_kW_hr = power_kW * time_hrs # kW*hr
    return energy_kW_hr

def conduit_available_volume(volume, capacity, threshold=1):
    """
    Conduit available volume, up to a capacity threshold [ft^3 or m^3].
    A returned value of NaN indicates that the conduit has exceeded the 
    capacity threshold.
    
    Parameters
    ------------
    volume : pandas Series
        Conduit volume, see `swn.conduit_volume (index = conduit names)
    capacity : pandas DataFrame
        Conduit capacity, from simulation results
        (index = times, columns = conduit names)
    threshold : float (optional, default = 1)
        Capacity threshold
    
    Returns
    -------
    pandas DataFrame with conduit available volume in ft^3 or m^3 
    (index = times, columns = conduit names)
                
    """
    assert isinstance(volume, pd.Series)
    assert isinstance(capacity, (pd.Series, pd.DataFrame))
    assert isinstance(threshold, (int, float))
    assert 0 <= threshold <= 1
    
    available_volume = volume*(threshold - capacity)
    available_volume[available_volume < 0] = None
    
    return available_volume

def conduit_travel_time(length, velocity):
    """
    Conduit travel time [s], computed as length divided by velocity
    
    Parameters
    ----------
    length : pandas Series
        Conduit length
    velocity : pandas DataFrame
        Conduit velocity, from simulation results
        (index = times, columns = conduit names)
        
    Returns
    -------
    pandas DataFrame with conduit travel time
    (index = times, columns = conduit names)
    
    """
    assert isinstance(length, pd.Series)
    assert isinstance(velocity, (pd.Series, pd.DataFrame))
    
    travel_time = length/velocity

    return travel_time


def conduit_time_to_capacity(volume, flowrate, flow_units, connected=False):
    """
    Conduit time to capacity [s] based on a steady state flowrate, computed as 
    volume divided by flowrate or total volume / max flowrate, 
    depending on the connected input parameter.
    
    This function can also use steady state available volume in place of 
    volume to consider conduits that are not empty, see 
    `conduit_available_volume` function.
    
    Parameters
    ------------
    volume : pandas Series
        Conduit volume (or steady state available volume) in ft^3 or m^3,
        (index = conduit names)
    flowrate :  pandas Series
        Steady state conduit flowrate, from simulation results
        (index = conduit names)
    flow_units : str
        Stormwater network model flow units
    connected : bool (default = False)
        If connected = False, each conduit is treated individually and 
        time_to_capacity = available_volume/flowrate
        If connected = True, the collection of conduits is considered an 
        isolated connected system and 
        time_to_capacity = sum(available_volume)/max(flowrate)
    
    Returns
    -------
    pandas Series (if connected = False) or single value
    (if connected = True) with the time to capacity
    
    """
    assert isinstance(volume, pd.Series)
    assert isinstance(flowrate, pd.Series)
    assert isinstance(flow_units, str)
    assert flow_units in ['CFS', 'GPM', 'MGD', 'CMS', 'LPS', 'MLD']
    assert isinstance(connected, bool)
    
    # Convert flowrate
    if flow_units == 'GPM': # convert to CFS
        cflowrate = flowrate*(1/7.48052)*(1/60)
    elif flow_units == 'MGD': # convert to CFS
        cflowrate = (flowrate*1E6)*(1/7.48052)*(1/86400)
    elif flow_units == 'LPS': # convert to CMS
        cflowrate = flowrate*(1/1000)
    elif flow_units == 'MLD': # convert to CMS
        cflowrate = (flowrate*1E6)*(1/1000)*(1/86400)
    else:
        cflowrate = flowrate # CFS or CMS
    
    if connected:
        time_to_capacity = volume.sum()/cflowrate.max()
    else:
        time_to_capacity = volume/cflowrate

    return time_to_capacity


def shortest_path_nodes(G, source_node, target_node):
    """
    Nodes along the shortest path from a source to target node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph, directed using steady state flow direction
    source_node : str
        Source node name
    target_node : str
        Target node name
        
    Returns
    --------
    List of node names in the path (including the source and target node)
    
    """
    assert isinstance(G, nx.MultiDiGraph)
    assert isinstance(source_node, str)
    assert isinstance(target_node, str)
    
    assert nx.has_path(G, source_node, target_node), \
                       "No path between " + source_node + " and " + target_node
    
    node_list = nx.shortest_path(G, source_node, target_node)
    return node_list

def shortest_path_edges(G, source_node, target_node):
    """
    Edges along the shortest path from a source to target node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph, directed using steady state flow direction
    source_node : str
        Source node name
    target_node : str
        Target node name
        
    Returns
    --------
    List of edge names in the path
    
    """
    assert isinstance(G, nx.MultiDiGraph)
    assert isinstance(source_node, str)
    assert isinstance(target_node, str)
    
    node_list = shortest_path_nodes(G, source_node, target_node)
    edge_list = [set(G[u][v]) for u,v in zip(node_list, node_list[1:])]
    edge_list = list(set().union(*edge_list))
    return edge_list
                
def upstream_nodes(G, source_node):
    """
    Upstream nodes from a source node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph, directed using steady state flow direction
    source_node : str
        Source node name
    
    Returns
    --------
    List of upstream node names (including the source node)
    
    """
    assert isinstance(G, nx.MultiDiGraph)
    assert isinstance(source_node, str)

    nodes = list(nx.traversal.bfs_tree(G, source_node, reverse=True))
    return nodes

def upstream_edges(G, source_node):
    """
    Upstream edges from a source node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph, directed using steady state flow direction
    source_node : str
        Source node name
    
    Returns
    --------
    List of upstream edge names
    
    """
    assert isinstance(G, nx.MultiDiGraph)
    assert isinstance(source_node, str)
    
    # NOTE: 'edge_bfs' yields edges even if they extend back to an already
    # explored node while 'bfs_edges' yields the edges of the tree that results
    # from a breadth-first-search (BFS) so no edges are reported if they extend
    # to already explored nodes.  AND Extracting edge names from u,v is slower
    # edge_uv = list(nx.traversal.bfs_edges(G, node, reverse=False))
    # uG = G.to_undirected()
    # edges = []
    # for u,v in edge_uv:
    # edges.extend(list(uG[u][v].keys()))
    edge_uvko = list(nx.traversal.edge_bfs(G, source_node, 
                                           orientation='reverse'))
    edges = [k for u,v,k,orentation in edge_uvko]  
    return edges

def downstream_nodes(G, source_node):
    """
    Downstream nodes from a source node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph, directed using steady state flow direction
    source_node : str
        Source node name
    
    Returns
    --------
    List of downstream node names (including the source node)
    
    """
    assert isinstance(G, nx.MultiDiGraph)
    assert isinstance(source_node, str)
    
    nodes = list(nx.traversal.bfs_tree(G, source_node, reverse=False))
    return nodes

def downstream_edges(G, source_node):
    """
    Downstream edges from a source node
    
    Parameters
    ------------
    G : networkX MultiDiGraph
        Graph, directed using steady state flow direction
    source_node : str
        Source node name
    
    Returns
    --------
    List of downstream edge names
    
    """
    assert isinstance(G, nx.MultiDiGraph)
    assert isinstance(source_node, str)
    
    edge_uvko = list(nx.traversal.edge_bfs(G, source_node, 
                                           orientation='original'))
    edges = [k for u,v,k,orentation in edge_uvko]  
    return edges
