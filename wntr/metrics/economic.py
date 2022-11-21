"""
The wntr.metrics.economic module contains economic metrics.

.. rubric:: Contents

.. autosummary::

    annual_network_cost
    annual_ghg_emissions
    pump_power
    pump_energy
    pump_cost


"""
from wntr.network import Tank, Pipe, Pump, Valve
import numpy as np 
import pandas as pd 
import logging
import scipy

logger = logging.getLogger(__name__)

def annual_network_cost(wn, tank_cost=None, pipe_cost=None, prv_cost=None, 
                        pump_cost=None):
    """ 
    Compute annual network cost [SOKZ12]_.
    
    Use the closest value from the lookup tables to compute annual cost for each 
    component in the network.
    
    Parameters
    ----------
    wn : wntr WaterNetworkModel
        Water network model. The water network model is needed to 
        define tank volume, pipe and valve diameter, and pump power conditions.
    
    tank_cost : pandas Series, optional
        Annual tank cost indexed by volume 
        (default values below, from [SOKZ12]_).
    
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
    
    pipe_cost : pandas Series, optional
        Annual pipe cost per pipe length indexed by diameter
        (default values below, from [SOKZ12]_).
    
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
        
    prv_cost : pandas Series, optional
        Annual PRV valve cost indexed by diameter 
        (default values below, from [SOKZ12]_).
        
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
    
    pump_cost : pd.Series, optional
        Annual pump cost indexed by maximum power input to pump
        (default values below, from [SOKZ12]_).
        Maximum Power for a HeadPump is computed from the pump curve
        as follows:
        
        .. math:: Pmp = g*rho/eff*exp(ln(A/(B*(C+1)))/C)*(A - B*(exp(ln(A/(B*(C+1)))/C))^C)
        
        where 
        :math:`Pmp` is the maximum power (W), 
        :math:`g` is acceleration due to gravity (9.81 m/s^2), 
        :math:`rho` is the density of water (1000 kg/m^3), 
        :math:`eff` is the global efficiency (0.75 default),
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
    Annual network cost in dollars (float)
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

    # Tank construction cost - not only looking at direct volume capacity but also
    #                          but a rough estimate of the support structure size
    #                          below the tank.
    for node_name, node in wn.nodes(Tank):
        if node.vol_curve is None:
            tank_construction_volume = np.pi*(node.diameter/2)**2 *node.max_level
        else:
            vcurve = np.array(node.vol_curve.points)
            tank_volume = np.interp(node.max_level,vcurve[:,0],vcurve[:,1])
            avg_area = tank_volume / (node.max_level - node.min_level)
            tank_base_volume = node.min_level * avg_area
            tank_construction_volume = tank_volume + tank_base_volume 
        # choose the entry that is closest (keep the cost structure discreet)
        idx = np.argmin([np.abs(tank_cost.index - tank_construction_volume)])
        #print(node_name, tank_cost.iloc[idx])
        network_cost = network_cost + tank_cost.iloc[idx]

    # Pipe construction cost
    for link_name, link in wn.links(Pipe):
        idx = np.argmin([np.abs(pipe_cost.index - link.diameter)])
        #print(link_name, pipe_cost.iloc[idx], link.length)
        network_cost = network_cost + pipe_cost.iloc[idx]*link.length    

    # Pump construction cost
    for link_name, link in wn.head_pumps():
        coeff = link.get_head_curve_coefficients()
        A = coeff[0]
        B = coeff[1]
        C = coeff[2]
        Pmax = 9.81*1000*np.exp(np.log(A/(B*(C+1)))/C)*(A - B*(np.exp(np.log(A/(B*(C+1)))/C))**C)
        Pmax = Pmax / wn.options.energy.global_efficiency
        idx = np.argmin([np.abs(pump_cost.index - Pmax)])
        #print(link_name, Pmax, pump_cost.iloc[idx])
        network_cost = network_cost + pump_cost.iloc[idx]

    for link_name, link in wn.power_pumps():
        Pmax = link.power
        Pmax = Pmax / wn.options.energy.global_efficiency
        idx = np.argmin([np.abs(pump_cost.index - Pmax)])
        #print(link_name, Pmax, pump_cost.iloc[idx])
        network_cost = network_cost + pump_cost.iloc[idx]
        
    # PRV valve construction cost    
    for link_name, link in wn.links(Valve):        
        if link.valve_type == 'PRV':
            idx = np.argmin([np.abs(prv_cost.index - link.diameter)])
            #print(link_name, link.diameter, prv_cost.iloc[idx])
            network_cost = network_cost + prv_cost.iloc[idx]  

    return network_cost

def annual_ghg_emissions(wn, pipe_ghg=None):
    """ 
    Compute annual greenhouse gas emissions [SOKZ12]_.
    
    Use the closest value in the lookup table to compute annual GHG emissions 
    for each pipe in the network.
    
    Parameters
    ----------
    wn : wntr WaterNetworkModel
        Water network model. The water network model is needed to 
        define pipe diameter.
    
    pipe_ghg : pandas Series, optional
        Annual GHG emissions indexed by pipe diameter
        (default values below, from [SOKZ12]_).
        
        =============  ================================
        Diameter (mm)  Annualized EE (kg-CO2-e/m/yr)
        =============  ================================
        102             5.90
        152             9.71
        203             13.94
        254             18.43
        305             23.16
        356             28.09
        406             33.09
        457             38.35
        508             43.76
        610             54.99
        711             66.57
        762             72.58
        =============  ================================
    
    Returns
    ----------
    Annual greenhouse gas emissions (float)
    """
    
    # Initialize network GHG emissions
    network_ghg = 0
    
    # Set defaults
    if pipe_ghg is None:
        diameter = [4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 30] # inches
        diameter = np.array(diameter)*0.0254 # m
        cost =  [5.9, 9.71, 13.94, 18.43, 23.16, 28.09, 33.09, 38.35, 43.76, 54.99, 66.57, 72.58]
        pipe_ghg = pd.Series(cost, diameter)
        
    # GHG emissions from pipes
    for link_name, link in wn.links(Pipe):
        idx = np.argmin([np.abs(pipe_ghg.index - link.diameter)])
        #print(link_name, link.diameter, pipe_ghg.iloc[idx],link.length)
        network_ghg = network_ghg + pipe_ghg.iloc[idx]*link.length
       
    return network_ghg    

def pump_power(flowrate, head, wn):
    """
    Compute pump power.
    
    The computation uses pump flow rate, node head (used to compute headloss at
    each pump), and pump efficiency. Pump efficiency is defined in
    ``wn.options.energy.global_efficiency``. Pump efficiency curves are currently 
    not supported.

        wn.options.energy.global_efficiency = 75 # This means 75% or 0.75

    Parameters
    ----------
    flowrate : pandas DataFrame
        A pandas DataFrame containing pump flowrates 
        (index = times, columns = pump names).
    
    head : pandas DataFrame
        A pandas DataFrame containing node head 
        (index = times, columns = node names).
        
    wn: wntr WaterNetworkModel
        Water network model.  The water network model is needed to 
        define energy efficiency.

    Returns
    -------
    A DataFrame that contains pump power in W (index = times, columns = pump names).
    """
    
    pumps = wn.pump_name_list
    time = flowrate.index
    
    headloss = pd.DataFrame(data=None, index=time, columns=pumps)
    for pump_name, pump in wn.pumps():
        start_node = pump.start_node_name
        end_node = pump.end_node_name
        start_head = head.loc[:,start_node]
        end_head = head.loc[:,end_node]
        headloss.loc[:,pump_name] = end_head - start_head

    efficiency_dict = {}
    for pump_name, pump in wn.pumps():
        if pump.efficiency is None:
            efficiency_dict[pump_name] = [wn.options.energy.global_efficiency/100.0 for i in time]
        else:
            raise NotImplementedError('WNTR does not support pump efficiency curves yet.')
            # TODO: WNTR does not support pump efficiency curves yet
            # curve = wn.get_curve(pump.efficiency)
            # x = [point[0] for point in curve.points]
            # y = [point[1]/100.0 for point in curve.points]
            # interp = scipy.interpolate.interp1d(x, y, kind='linear')
            # efficiency_dict[pump_name] = interp(np.array(flowrate.loc[:, pump_name]))

    efficiency = pd.DataFrame(data=efficiency_dict, index=time, columns=pumps)

    power = 1000.0 * 9.81 * headloss * flowrate / efficiency # Watts = J/s

    return power

def pump_energy(flowrate, head, wn):
    """
    Compute the pump energy over time.
    
    The computation uses pump flow rate, node head (used to compute headloss at
    each pump), and pump efficiency. Pump efficiency is defined in
    ``wn.options.energy.global_efficiency``. Pump efficiency curves are currently 
    not supported.

        wn.options.energy.global_efficiency = 75 # This means 75% or 0.75

    Parameters
    ----------
    flowrate : pandas DataFrame
        A pandas DataFrame containing pump flowrates 
        (index = times, columns = pump names).
    
    head : pandas DataFrame
        A pandas DataFrame containing node head 
        (index = times, columns = node names).
        
    wn: wntr WaterNetworkModel
        Water network model.  The water network model is needed to 
        define energy efficiency.

    Returns
    -------
    A DataFrame that contains pump energy in J (index = times, columns = pump names).
    """
    
    power = pump_power(flowrate, head, wn) # Watts = J/s
    energy = power * wn.options.time.report_timestep # J = Ws
    
    return energy

def pump_cost(energy, wn):
    """
    Compute the pump cost over time. 
    
    Energy cost is defined in ``wn.options.energy.global_price``. Pump energy 
    price and price patterns are currently not supported. 

        wn.options.energy.global_price = 3.61e-8  # $/J; equal to $0.13/kW-h
        
    Parameters
    ----------
    energy : pandas DataFrame
        A pandas DataFrame containing pump energy (J), computed from ``wntr.metrics.pump_energy`` 
        (index = times, columns = pump names).
        
    wn: wntr WaterNetworkModel
        Water network model.  The water network model is needed to 
        define pump enery prices and patterns.
        
    Returns
    -----------
    A DataFrame that contains pump cost in $ (index = times, columns = pump names).
    
    """
    time = energy.index
    pumps = wn.pump_name_list
    
    # TODO: Need to get this unit tested and not just functionally tested
    if wn.options.energy.demand_charge is not None and wn.options.energy.demand_charge != 0:
        # Additional energy charge per maximum kilowatt usage
        raise ValueError('WNTR does not support demand charge yet.')
        
    price_dict = {}
    for pump_name, pump in wn.pumps():
        if pump.energy_price is None and pump.energy_pattern is None:
            if wn.options.energy.global_pattern is None:
                price_dict[pump_name] = [wn.options.energy.global_price for i in time]
            else:
                raise NotImplementedError('WNTR does not support price patterns yet.')
        elif pump.energy_pattern is None:
            if wn.options.energy.global_pattern is None:
                price_dict[pump_name] = [pump.energy_price for i in time]
            else:
                raise NotImplementedError('WNTR does not support price patterns yet.')
        else:
            raise NotImplementedError('WNTR does not support price patterns yet.')
            
    price = pd.DataFrame(data=price_dict, index=time, columns=pumps)
    
    pump_cost = energy * price
    
    return pump_cost
    
