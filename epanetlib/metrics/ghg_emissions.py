from epanetlib.network import Pipe
import numpy as np  
    
def ghg_emissions(wn, pipe_ghg):
    
    # Initialize network GHG emissions
    network_ghg = 0
    
    # GHG emissions from pipes
    for link_name, link in wn.links(Pipe):
        link_length = wn.get_link(link_name).length
        link_diameter = wn.get_link(link_name).diameter
        idx = (np.abs(pipe_ghg[:,0]-link_diameter)).argmin()
        network_ghg = network_ghg + pipe_ghg[idx,1]*link_length
       
    return network_ghg    