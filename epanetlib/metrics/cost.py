import epanetlib.pyepanet as pyepanet
import numpy as np  

def cost(G, tank_cost, pipe_cost, valve_cost, pump_cost):

    network_cost = 0
    
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            pass
        elif G.node[i]['nodetype'] == pyepanet.EN_RESERVOIR:
            pass
        elif G.node[i]['nodetype'] == pyepanet.EN_TANK:
            tank_diameter = G.node[i]['tank_diameter']
            tank_minlevel = G.node[i]['tank_minlevel']
            tank_maxlevel = G.node[i]['tank_maxlevel']
            tank_volume = (tank_diameter/2)**2*(tank_maxlevel-tank_minlevel)
            idx = (np.abs(tank_cost[:,0]-tank_volume)).argmin()
            network_cost = network_cost + tank_cost[idx,1]

    for i,j,k in G.edges(keys=True):
        if G.edge[i][j][k]['linktype']  in [pyepanet.EN_CVPIPE, pyepanet.EN_PIPE]:
            link_length = G.edge[i][j][k]['length']
            link_diameter = G.edge[i][j][k]['diameter']
            idx = (np.abs(pipe_cost[:,0]-link_diameter)).argmin()
            network_cost = network_cost + pipe_cost[idx,1]*link_length
            
        elif G.edge[i][j][k]['linktype']  == pyepanet.EN_PUMP:
            network_cost = network_cost + pump_cost
        
        elif G.edge[i][j][k]['linktype']  in [pyepanet.EN_PRV, pyepanet.EN_PSV, 
                pyepanet.EN_PBV, pyepanet.EN_FCV, pyepanet.EN_TCV, pyepanet.EN_GPV]:
            link_diameter =  G.edge[i][j][k]['diameter']
            idx = (np.abs(valve_cost[:,0]-link_diameter)).argmin()
            network_cost = network_cost + valve_cost[idx,1]
    
    return network_cost
"""
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
    
"""