import epanetlib.pyepanet as pyepanet
from operator import itemgetter
    
def cost(enData, tank_cost, pipe_cost, valve_cost, pump_cost):

    network_cost = 0
    
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT) 
    for i in range(nNodes):
        node_id = enData.ENgetnodeid(i+1)
        node_type = enData.ENgetnodetype(i+1)
        if node_type == 0: # junction
            pass
        elif node_type == 1: # reservoir:
            pass
        elif node_type == 2: # tank
            tank_diameter = enData.ENgetnodevalue(i+1, pyepanet.EN_TANKDIAM)
            tank_minlevel = enData.ENgetnodevalue(i+1, pyepanet.EN_MINLEVEL)
            tank_maxlevel = enData.ENgetnodevalue(i+1, pyepanet.EN_MAXLEVEL)
            tank_volume = (tank_diameter/2)**2*(tank_maxlevel-tank_minlevel)
            diff = [abs(float(x) - tank_volume) for x in tank_cost.keys()]
            loc = min(enumerate(diff), key=itemgetter(1))[0] 
            
            network_cost = network_cost + tank_cost[tank_cost.keys()[loc]]
            
        else:
            print "Undefined node type for " + node_id
            
    nLinks = enData.ENgetcount(pyepanet.EN_LINKCOUNT)    
    for i in range(nLinks):
        link_id = enData.ENgetlinkid(i+1)
        link_type = enData.ENgetlinktype(i+1)
        if link_type in [0,1]: # pipe
            link_diameter = enData.ENgetlinkvalue(i+1, pyepanet.EN_DIAMETER)
            link_length = enData.ENgetlinkvalue(i+1, pyepanet.EN_LENGTH)
            diff = [abs(float(x) - link_diameter) for x in pipe_cost.keys()]
            loc = min(enumerate(diff), key=itemgetter(1))[0] 
            
            network_cost = network_cost + pipe_cost[pipe_cost.keys()[loc]]*link_length
            
        elif link_type in [2]: # pump
            network_cost = network_cost + pump_cost
        
        elif link_type in [3,4,5,6,7,8]: # valve 
            link_diameter = enData.ENgetlinkvalue(i+1, pyepanet.EN_DIAMETER)
            diff = [abs(float(x) - link_diameter) for x in valve_cost.keys()]
            loc = min(enumerate(diff), key=itemgetter(1))[0] 
            
            network_cost = network_cost + valve_cost[valve_cost.keys()[loc]]
            
        else:
            print "Undefined link type for " + link_id
    
    return network_cost
    
    