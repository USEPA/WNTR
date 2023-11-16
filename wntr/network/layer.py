"""
The wntr.network.layer module includes methods to generate network layers
(information that is not stored in the water network model or the graph).
"""
import numpy as np
import pandas as pd
import random

def generate_valve_layer(wn, placement_type='strategic', n=1, seed=None):
    """
    Generate valve layer data, which can be used in valve segmentation analysis.

    Parameters
    -----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object
        
    placement_type : string
        Options include 'strategic' and 'random'.  
        
        - If 'strategic', n is the number of pipes from each node that do not 
          contain a valve. In this case, n is generally 0, 1 or 2 
          (i.e. N, N-1, N-2 valve placement).
        - If 'random', then n randomly placed valves are used to define the 
          valve layer.
        
    n : int
        
        - If 'strategic', n is the number of pipes from each node that do not 
          contain a valve.
        - If 'random', n is the number of number of randomly placed valves.
        
    seed : int or None
        Random seed
       
    Returns
    ---------
    valve_layer : pandas DataFrame
        Valve layer, defined by node and link pairs (for example, valve 0 is 
        on link A and protects node B). The valve_layer DataFrame is indexed by
        valve number, with columns named 'node' and 'link'.
    """
    
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    valve_layer = []
    if placement_type=='random':
        all_valves = []
        for pipe_name, pipe in wn.pipes():
            all_valves.append((pipe_name, pipe.start_node_name))
            all_valves.append((pipe_name, pipe.end_node_name))

        for valve_tuple in random.sample(all_valves, n):
            pipe_name, node_name = valve_tuple
            valve_layer.append([pipe_name, node_name])
            
    elif placement_type == 'strategic':
        for node_name, node in wn.nodes():
            links = wn.get_links_for_node(node_name)
            for l in np.random.choice(links, max(len(links)-n,0), replace=False):
                valve_layer.append([l, node_name])
            
    valve_layer = pd.DataFrame(valve_layer, columns=['link', 'node'])  
    
    return valve_layer