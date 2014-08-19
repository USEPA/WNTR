import epanetlib.pyepanet as pyepanet
import numpy as np  
    
def ghg_emissions(G, pipe_ghg):
    
    network_ghg = 0
       
    for i,j,k in G.edges(keys=True):
        if G.edge[i][j][k]['linktype']  in [pyepanet.EN_CVPIPE, pyepanet.EN_PIPE]:
            link_length = G.edge[i][j][k]['length']
            link_diameter = G.edge[i][j][k]['diameter']
            idx = (np.abs(pipe_ghg[:,0]-link_diameter)).argmin()
            network_ghg = network_ghg + pipe_ghg[idx,1]*link_length
            
        elif G.edge[i][j][k]['linktype']  == pyepanet.EN_PUMP:
            pass
        
        elif G.edge[i][j][k]['linktype']  in [pyepanet.EN_PRV, pyepanet.EN_PSV, 
                pyepanet.EN_PBV, pyepanet.EN_FCV, pyepanet.EN_TCV, pyepanet.EN_GPV]:
            pass
    
    return network_ghg
    
    