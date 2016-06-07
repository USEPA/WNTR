from wntr.network import Pipe
import numpy as np
import pandas as pd  
    
def ghg_emissions(wn, pipe_ghg=None):
    """ Compute greenhouse gas emissions.
    Use the closest value in the lookup table to compute GHG emissions 
    for each pipe in the network.
    
    Parameters
    ----------
    pipe_ghg : pd.Series (optional, default values below, from [1])
        Annual GHG emissions indexed by pipe diameter
        
        =============  ================================
        Diameter (mm)  Annualised EE (kg-CO2-e/m/yr)
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
    network_ghg : float
        Annual greenhouse gas emissions
        
    References
    ----------
    [1] Salomons E, Ostfeld A, Kapelan Z, Zecchin A, Marchi A, Simpson A. (2012).
    water networks II - Adelaide 2012 (BWN-II). In Proceedings of the 2012 Water Distribution
    Systems Analysis Conference, September 24-27, Adelaide, South Australia, Australia.
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
        network_ghg = network_ghg + pipe_ghg.iloc[idx]*link.length
       
    return network_ghg    
    