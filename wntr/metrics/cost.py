from wntr.network import Tank, Pipe, Pump, Valve
import numpy as np 
import pandas as pd 

def cost(wn, tank_cost=None, pipe_cost=None, prv_cost=None, pump_cost=None):
    """ Compute network cost.
    Use the closest value from the lookup tables to compute cost for each 
    component in the network.
    
    Parameters
    ----------
    tank_cost : pd.Series (optional, default values below, from [1])
        Annual tank cost indexed by volume
    
        =============  ================================
        Volume (m3)    Annual Cost ($/yr) 
        =============  ================================
        500             14020
        1000            30640
        2000            61210
        3750            87460
        5000            122420
        10000           174930
        =============  ================================
    
    pipe_cost : pd.Series (optional, default values below, from [1])
        Annual pipe cost per pipe length indexed by diameter
    
        =============  ================================
        Diameter (in)  Annual Cost ($/m/yr) 
        =============  ================================
        4               8.31
        6              10.10
        8              12.10
        10             12.96
        12             15.22
        14             16.62
        16             19.41
        18             22.20
        20             24.66
        24             35.69
        28             40.08
        30             42.60
        =============  ================================
        
    prv_cost : pd.Series (optional, default values below, from [1])
        Annual PRV valve cost indexed by diameter 
        
        =============  ================================
        Diameter (in)  Annual Cost ($/m/yr) 
        =============  ================================
        4              323
        6              529
        8              779
        10             1113
        12             1892
        14             2282
        16             4063
        18             4452
        20             4564
        24             5287
        28             6122
        30             6790
        =============  ================================

    pump_cost : float (optional, default values below, from [1])
        Average cost per year.  
        TODO: This should be based on max power or pump curve
        
        ==================  ================================
        Maximum power (kW)  Annual Cost ($/yr) 
        ==================  ================================
        45.24               4133
        31.67               3563
        49.76               4339
        22.62               3225
        22.62               3225
        24.88               3307
        11.31               2850
        54.28               4554
        38.00               3820
        59.71               4823
        ==================  ================================

    References
    ----------
    [1] Salomons E, Ostfeld A, Kapelan Z, Zecchin A, Marchi A, Simpson A. (2012).
    water networks II - Adelaide 2012 (BWN-II). In Proceedings of the 2012 Water Distribution
    Systems Analysis Conference, September 24-27, Adelaide, South Australia, Australia.
    """
    # Initialize network construction cost
    network_cost = 0
    
    # Set defaults
    if tank_cost is None:
        volume = [500, 1000, 2000, 3750, 5000, 10000] 
        cost =  [14020, 30640, 61210, 87460, 122420, 174930]
        tank_cost = pd.Series(cost, volume)
        
    if pipe_cost is None:
        diameter = [4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 30] # inch
        diameter = np.array(diameter)*0.0254 # m
        cost =  [8.31, 10.1, 12.1, 12.96, 15.22, 16.62, 19.41, 22.2, 24.66, 35.69, 40.08, 42.6]
        pipe_cost = pd.Series(cost, diameter)
        
    if prv_cost is None:
        diameter = [4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 30] # inch
        diameter = np.array(diameter)*0.0254 # m
        cost =  [323, 529, 779, 1113, 1892, 2282, 4063, 4452, 4564, 5287, 6122, 6790]
        prv_cost = pd.Series(cost, diameter)

    if pump_cost is None:
        pump_cost = 3783
        
    # Tank construction cost
    for node_name, node in wn.nodes(Tank):
        tank_volume = (node.diameter/2)**2*(node.max_level-node.min_level)
        idx = np.argmin(np.abs(tank_cost.index - tank_volume))
        network_cost = network_cost + tank_cost.iloc[idx]
    
    # Pipe construction cost
    for link_name, link in wn.links(Pipe):
        idx = np.argmin(np.abs(pipe_cost.index - link.diameter))
        network_cost = network_cost + pipe_cost.iloc[idx]*link.length    
    
    # Pump construction cost
    for link_name, link in wn.links(Pump):        
        network_cost = network_cost + pump_cost
        
    # PRV valve construction cost    
    for link_name, link in wn.links(Valve):        
        if link.valve_type == 'PRV':
            idx = np.argmin(np.abs(prv_cost.index - link.diameter))
            network_cost = network_cost + prv_cost.iloc[idx]  
    
    return network_cost
