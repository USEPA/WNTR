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
    
        =============  =============  ================================
        Diameter (in)   Diameter (m)  Annual Cost ($/m/yr) 
        =============  =============  ================================
        4              0.102          8.31
        6              0.152          10.10
        8              0.203          12.10
        10             0.254          12.96
        12             0.305          15.22
        14             0.356          16.62
        16             0.406          19.41
        18             0.457          22.20
        20             0.508          24.66
        24             0.610          35.69
        28             0.711          40.08
        30             0.762          42.60
        =============  =============  ================================
        
    prv_cost : pd.Series (optional, default values below, from [1])
        Annual PRV valve cost indexed by diameter 
        
        =============  =============  ================================
        Diameter (in)   Diameter (m)  Annual Cost ($/m/yr) 
        =============  =============  ================================
        4              0.102          323
        6              0.152          529
        8              0.203          779
        10             0.254          1113
        12             0.305          1892
        14             0.356          2282
        16             0.406          4063
        18             0.457          4452
        20             0.508          4564
        24             0.610          5287
        28             0.711          6122
        30             0.762          6790
        =============  =============  ================================
    
    pump_cost : pd.Series (optional, default values below, from [1])
        Annual pump cost indexed by maximum power.  Maximum Power is computed 
        from the pump curve and pump efficiency as follows:
        
        .. math:: Pmp = g*rho/eff*exp(ln(A/(B*(C+1)))/C)*(A - B*(exp(ln(A/(B*(C+1)))/C))^C)
        
        where 
        :math:`Pmp` is the maximum power (W), 
        :math:`g` is acceleration due to gravity (9.81 m/s^2), 
        :math:`rho` is the density of water (1000 kg/m^3), 
        :math:`eff` is the overall pump efficiency (0.75), 
        :math:`A`, :math:`B`, and :math:`C` are the pump curve coefficients.

        ==================  ================================
        Maximum power (W)   Annual Cost ($/yr) 
        ==================  ================================
        11310               2850
        22620               3225
        24880               3307
        31670               3563
        38000               3820
        45240               4133
        49760               4339
        54280               4554
        59710               4823
        ==================  ================================

    Returns
    ----------
    network_cost : float
        Annual network cost in dollars
        
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
        Pmp = [11310, 22620, 24880, 31670, 38000, 45240, 49760, 54280, 59710]
        cost =  [2850, 3225, 3307, 3563, 3820, 4133, 4339, 4554, 4823]
        pump_cost = pd.Series(cost, Pmp)
        
    # Tank construction cost
    for node_name, node in wn.nodes(Tank):
        tank_volume = (node.diameter/2)**2*(node.max_level-node.min_level)
        idx = np.argmin([np.abs(tank_cost.index - tank_volume)])
        network_cost = network_cost + tank_cost.iloc[idx]
    
    # Pipe construction cost
    for link_name, link in wn.links(Pipe):
        idx = np.argmin([np.abs(pipe_cost.index - link.diameter)])
        network_cost = network_cost + pipe_cost.iloc[idx]*link.length    
    
    # Pump construction cost
    for link_name, link in wn.links(Pump):      
        coeff = link.get_head_curve_coefficients()
        A = coeff[0]
        B = coeff[1]
        C = coeff[2]
        # TODO: efficiency should be read from the inp file
        eff = 0.75
        Pmax = 9.81*1000/eff*np.exp(np.log(A/(B*(C+1)))/C)*(A - B*(np.exp(np.log(A/(B*(C+1)))/C))**C)
        idx = np.argmin([np.abs(pump_cost.index - Pmax)])
        network_cost = network_cost + pump_cost.iloc[idx]
        
    # PRV valve construction cost    
    for link_name, link in wn.links(Valve):        
        if link.valve_type == 'PRV':
            idx = np.argmin([np.abs(prv_cost.index - link.diameter)])
            network_cost = network_cost + prv_cost.iloc[idx]  
    
    return network_cost
