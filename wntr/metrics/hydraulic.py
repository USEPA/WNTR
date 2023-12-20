"""
The wntr.metrics.hydraulic module contains hydraulic metrics.
"""
import wntr.network
import numpy as np
import pandas as pd
import networkx as nx
import math
from collections import Counter
import sys
from functools import reduce
    
import logging

logger = logging.getLogger(__name__)

def expected_demand(wn, start_time=None, end_time=None, timestep=None, category=None):
    """
    Compute expected demand at each junction and time using base demands
    and demand patterns along with the demand multiplier
    
    Parameters
    -----------
    wn : wntr WaterNetworkModel
        Water network model. The water network model is needed to 
        get demand timeseries at junctions and options related to 
        duration, timestep, and demand multiplier.
        
    start_time : int (optional)
        Start time in seconds, if None then value is set to 0
        
    end_time : int  (optional)
        End time in seconds, if None then value is set to wn.options.time.duration

    timestep : int (optional)
        Timestep, if None then value is set to wn.options.time.report_timestep
    
    category : str (optional)
        Demand category name.  If None, all demand categories are used.
            
    Returns
    -------
    A pandas DataFrame that contains expected demand in m3/s (index = times, columns = junction names).
    """
    if start_time is None:
        start_time = 0
    if end_time is None:
        end_time = wn.options.time.duration
    if timestep is None:
        timestep = wn.options.time.report_timestep
        
    exp_demand = {}
    tsteps = np.arange(start_time, end_time+timestep, timestep)
    for name, junc in wn.junctions():
        dem = []
        for ts in tsteps:
            dem.append(junc.demand_timeseries_list.at(ts, 
                       multiplier=wn.options.hydraulic.demand_multiplier, category=category))
        exp_demand[name] = dem 
    
    exp_demand = pd.DataFrame(index=tsteps, data=exp_demand)
    
    return exp_demand

def average_expected_demand(wn, category=None):
    """
    Compute average expected demand per day at each junction using base demands
    and demand patterns along with the demand multiplier
    
    Parameters
    -----------
    wn : wntr WaterNetworkModel
        Water network model. The water network model is needed to 
        get demand timeseries at junctions and options related to 
        duration, timestep, and demand multiplier.
    
    category : str (optional)
        Demand category name.  If None, all demand categories are used.
        
    Returns
    -------
    A pandas Series that contains average expected demand in m3/s (index = junction names).
    """
    L = [24*3600] # start with a 24 hour pattern
    for name, pattern in wn.patterns():
        L.append(len(pattern.multipliers)*wn.options.time.pattern_timestep)
    lcm = int(_lcml(L))
    
    start_time = wn.options.time.pattern_start
    end_time = start_time+lcm
    timestep = wn.options.time.pattern_timestep
        
    exp_demand = expected_demand(wn, start_time, end_time-timestep, timestep, category=category)
    ave_exp_demand = exp_demand.mean(axis=0)

    return ave_exp_demand

def _gcd(x,y):
  while y:
    if y<0:
      x,y=-x,-y
    x,y=y,x % y
    return x

def _gcdl(*list):
  return reduce(_gcd, *list)

def _lcm(x,y):
  return x*y / _gcd(x,y)

def _lcml(*list):
  return reduce(_lcm, *list)

def water_service_availability(expected_demand, demand):
    r"""
    Compute water service availability (WSA) at junctions, defined as follows:
        
    .. math:: WSA = \dfrac{demand}{expected\_demand}
        
    where 
    :math:`demand` is the actual demand computed from a hydraulic simulation, and 
    :math:`expected\_demand` is the expected demand computed from base demands and demand 
    patterns. Expected demand can be computed using the 
    :class:`~wntr.metrics.hydraulic.expected_demand` method.

    WSA can be averaged over times and/or nodes (see below).  If 
    expected demand is 0 for a particular junction, water service availability 
    will be set to NaN for that junction. 

    * To compute water service availability for each junction and timestep, 
      expected_demand and demand should be pandas DataFrames (index = times, columns = junction names). 
    
    * To compute an average water service availability for each junction (averaged over time), 
      expected_demand and demand should be a pandas Series, indexed by junction.  
      To convert a DataFrame (index = times, columns = junction names) to a 
      Series indexed by junction, use the following code:
    
        :math:`expected\_demand.sum(axis=0)`
		
        :math:`demand.sum(axis=0)`
    
    * To compute an average water service availability for each timestep (averaged over junctions), 
      expected_demand and demand should be a pandas Series, indexed by time.  
      To convert a DataFrame (index = times, columns = junction names) to a 
      Series indexed by time, use the following code:
        
        :math:`expected\_demand.sum(axis=1)`
		
        :math:`demand.sum(axis=1)`
        
    Parameters
    ----------
    expected_demand : pandas DataFrame or pandas Series (see note above)
        Expected demand at junctions 
    
    demand : pandas DataFrame or pandas Series (see note above)
        Actual demand (generally from a PDD hydraulic simulation) at junctions

    Returns
    -------
    A pandas DataFrame or pandas Series that contains water service 
    availability.
    """

    wsa = demand.div(expected_demand) 
    
    return wsa

def todini_index(head, pressure, demand, flowrate, wn, Pstar):
    """
    Compute Todini index, equations from :cite:p:`todi00`.

    The Todini index is related to the capability of a system to overcome
    failures while still meeting demands and pressures at the nodes. The
    Todini index defines resilience at a specific time as a measure of surplus
    power at each node and measures relative energy redundancy.

    Parameters
    ----------
    head : pandas DataFrame
        A pandas DataFrame containing node head 
        (index = times, columns = node names).
        
    pressure : pandas DataFrame
        A pandas DataFrame containing node pressure 
        (index = times, columns = node names).
        
    demand : pandas DataFrame
        A pandas DataFrame containing node demand 
        (index = times, columns = node names).
        
    flowrate : pandas DataFrame
        A pandas DataFrame containing pump flowrates 
        (index = times, columns = pump names).

    wn : wntr WaterNetworkModel
        Water network model.  The water network model is needed to 
        find the start and end node to each pump.
        
    Pstar : float
        Pressure threshold.

    Returns
    -------
    A pandas Series that contains a time-series of Todini indexes
    """

    Pout = demand.loc[:,wn.junction_name_list]*head.loc[:,wn.junction_name_list]
    elevation = head.loc[:,wn.junction_name_list]-pressure.loc[:,wn.junction_name_list]
    Pexp = demand.loc[:,wn.junction_name_list]*(Pstar+elevation)

    Pin_res = -demand.loc[:,wn.reservoir_name_list]*head.loc[:,wn.reservoir_name_list]

    headloss = pd.DataFrame()
    for name, link in wn.pumps():
        start_node = link.start_node_name
        end_node = link.end_node_name
        start_head = head.loc[:,start_node] # (m)
        end_head = head.loc[:,end_node] # (m)
        headloss[name] = end_head - start_head # (m)
        
    Pin_pump = flowrate.loc[:,wn.pump_name_list]*headloss.abs()

    todini = (Pout.sum(axis=1) - Pexp.sum(axis=1))/  \
        (Pin_res.sum(axis=1) + Pin_pump.sum(axis=1) - Pexp.sum(axis=1))
    
    return todini

def modified_resilience_index(pressure, elevation, Pstar, demand=None, per_junction=True):
    """
    Compute the modified resilience index, equations from :cite:p:`jasr08`.

    The modified resilience index is the total surplus power available at 
    demand junctions as a percentage of the total minimum required power at 
    demand junctions. The metric can be computed as a timeseries for each 
    junction or as a system average timeseries.

    Parameters
    ----------
    pressure : pandas DataFrame
        A pandas DataFrame containing junction pressure 
        (index = times, columns = junction names).
        
    elevation : pandas Series
        Junction elevation (which can be obtained using `wn.query_node_attribute('elevation')`)
        (index = junction names)
        
    Pstar : float
        Pressure threshold.
    
    demand : pandas DataFrame
        A pandas DataFrame containing junction demand (only needed if per_junction=False)
        (index = times, columns = junction names).

    per_junction : bool (optional)
        If True, compute the modified resilience index per junction.
        If False, compute the modified resilience index over all junctions.
        
    Returns
    -------
    pandas Series or DataFrame
        Modified resilience index time-series. If per_junction=True, columns=junction names.
    """
    assert isinstance(pressure, pd.DataFrame), "pressure must be a pandas DataFrame"
    assert isinstance(elevation, pd.Series), "elevation must be a pandas Series"
    assert sorted(pressure.columns) == sorted(elevation.index), "The columns in pressure must be the same as the index in elevation"
    assert isinstance(Pstar, (float, int)), "Pstar must be a float"
    assert isinstance(per_junction, bool), "per_junction must be a Boolean"
    if per_junction == False:
        assert isinstance(demand, pd.DataFrame), "demand must be a pandas DataFrame when per_junction=False"
        assert sorted(pressure.columns) == sorted(demand.columns), "The columns in pressure must be the same as the columns in demand"
    
    if per_junction:
        Pout = (pressure + elevation)
        Pexp =(Pstar + elevation)
        mri = (Pout - Pexp)/Pexp
    else:
        
        Pout = demand*(pressure + elevation)
        Pexp = demand*(Pstar + elevation)
        mri = (Pout.sum(axis=1) - Pexp.sum(axis=1))/Pexp.sum(axis=1)
    
    return mri

def tank_capacity(pressure, wn):
    """
    Compute tank capacity, the ratio of water volume stored in tanks to the 
    maximum volume of water that can be stored.

    Parameters
    ----------
    pressure : pandas DataFrame
        A pandas DataFrame containing tank water level (pressure) 
        (index = times, columns = tank names).
        
    wn : wntr WaterNetworkModel
        Water network model.  The water network model is needed to 
        get the tank object to compute current and max volume.
        
    Returns
    -------
    pandas DataFrame
        Tank capacity (index = times, columns = tank names)
    """
    
    assert isinstance(pressure, pd.DataFrame), "pressure must be a pandas DataFrame"
    assert isinstance(wn, wntr.network.WaterNetworkModel), "wn must be a wntr WaterNetworkModel"

    tank_capacity = pd.DataFrame(index=pressure.index, columns=pressure.columns)
    
    for name in wn.tank_name_list:
        tank = wn.get_node(name)
        max_volume = tank.get_volume(tank.max_level)
        tank_volume = tank.get_volume(pressure[name])
        tank_capacity[name] = tank_volume/max_volume
    
    return tank_capacity
    
def entropy(G, sources=None, sinks=None):
    """
    Compute entropy, equations from :cite:p:`awgb90`.

    Entropy is a measure of uncertainty in a random variable.
    In a water distribution network model, the random variable is
    flow in the pipes and entropy can be used to measure alternate flow paths
    when a network component fails.  A network that carries maximum entropy
    flow is considered reliable with multiple alternate paths.

    Parameters
    ----------
    G : NetworkX or WNTR graph
        Entropy is computed using a directed graph based on pipe flow direction.
        The 'weight' of each link is equal to the flow rate.

    sources : list of strings, optional (default = all reservoirs)
        List of node names to use as sources.

    sinks : list of strings, optional (default = all nodes)
        List of node names to use as sinks.

    Returns
    -------
    A tuple which includes:
        - A pandas Series that contains entropy for each node
        - System entropy (float)
    """

    if G.is_directed() == False:
        return

    if sources is None:
        sources = [key for key,value in nx.get_node_attributes(G,'type').items() if value == 'Reservoir' ]

    if sinks is None:
        sinks = G.nodes()

    S = {}
    Q = {}
    for nodej in sinks:
        if nodej in sources:
            S[nodej] = 0 # nodej is the source
            continue

        sp = [] # simple path
        if G.nodes[nodej]['type']  == 'Junction':
            for source in sources:
                if nx.has_path(G, source, nodej):
                    simple_paths = nx.all_simple_paths(G,source,target=nodej)
                    sp = sp + ([p for p in simple_paths])
                    # all_simple_paths was modified to check 'has_path' in the
                    # loop, but this is still slow for large networks
                    # what if the network was skeletonized based on series pipes
                    # that have the same flow direction?
                    # what about duplicating paths that have pipes in series?
                #print j, nodeid, len(sp)

        if len(sp) == 0:
            S[nodej] = np.nan # nodej is not connected to any sources
            continue

        # "dtype=object" is needed to create an array from a list of lists with differnet lengths
        sp = np.array(sp, dtype=object)

        # Uj = set of nodes on the upstream ends of links incident on node j
        Uj = G.predecessors(nodej)
        # qij = flow in link from node i to node j
        qij = []
        # aij = number of equivalnet independent paths through the link from node i to node j
        aij = []
        for nodei in Uj:
            mask = np.array([nodei in path for path in sp])
            # NDij = number of paths through the link from node i to node j
            NDij = sum(mask)
            if NDij == 0:
                continue
            temp = sp[mask]
            # MDij = links in the NDij path
            MDij = [(t[idx],t[idx+1]) for t in temp for idx in range(len(t)-1)]

            flow = 0
            for link in G[nodei][nodej].keys():
                flow = flow + G[nodei][nodej][link]['weight']
            qij.append(flow)

            # dk = degree of link k in MDij
            dk = Counter()
            for elem in MDij:
                # divide by the numnber of links between two nodes
                dk[elem] += 1/len(G[elem[0]][elem[1]].keys())
            V = np.array(list(dk.values()))
            aij.append(NDij*(1-float(sum(V - 1))/sum(V)))

        Q[nodej] = sum(qij) # Total flow into node j

        # Equation 7
        S[nodej] = 0
        for idx in range(len(qij)):
            if Q[nodej] != 0 and qij[idx]/Q[nodej] > 0:
                S[nodej] = S[nodej] - \
                    qij[idx]/Q[nodej]*math.log(qij[idx]/Q[nodej]) + \
                    qij[idx]/Q[nodej]*math.log(aij[idx])

    Q0 = sum(nx.get_edge_attributes(G, 'weight').values())

    # Equation 3
    S_ave = 0
    for nodej in sinks:
        if not np.isnan(S[nodej]):
            if nodej not in sources:
                if Q[nodej]/Q0 > 0:
                    S_ave = S_ave + \
                        (Q[nodej]*S[nodej])/Q0 - \
                        Q[nodej]/Q0*math.log(Q[nodej]/Q0)
                        
    S = pd.Series(S) # convert S to a series
    
    return [S, S_ave]
