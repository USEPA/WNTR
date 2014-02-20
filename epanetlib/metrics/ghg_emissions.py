import epanetlib.pyepanet as pyepanet
from operator import itemgetter
    
def ghg_emissions(enData, pipe_ghg):
    
    network_ghg = 0
    
    nLinks = enData.ENgetcount(pyepanet.EN_LINKCOUNT)    
    for i in range(nLinks):
        link_id = enData.ENgetlinkid(i+1)
        link_type = enData.ENgetlinktype(i+1)
        if link_type in [0,1]: # pipe
            link_diameter = enData.ENgetlinkvalue(i+1, pyepanet.EN_DIAMETER)
            link_length = enData.ENgetlinkvalue(i+1, pyepanet.EN_LENGTH)
            diff = [abs(float(x) - link_diameter) for x in pipe_ghg.keys()]
            loc = min(enumerate(diff), key=itemgetter(1))[0] 
            
            network_ghg = network_ghg + pipe_ghg[pipe_ghg.keys()[loc]]*link_length
            
        elif link_type in [2]: # pump
            pass
        
        elif link_type in [3,4,5,6,7,8]: # valve 
            pass
            
        else:
            print "Undefined link type for " + link_id
    
    return network_ghg
    
    