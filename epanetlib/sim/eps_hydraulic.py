import epanetlib.pyepanet as pyepanet
import numpy as np
import epanetlib.units as units

def eps_hydraulic(enData, convert=False):
    
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT)
    nLinks = enData.ENgetcount(pyepanet.EN_LINKCOUNT) 
    
    enData.ENinitH(0)

    nodekey = []
    edgekey = []
    
    time = []
    node_P = []
    node_D = []
    link_F = []
    link_V = []
            
    for i in range(nNodes):
        nodekey.append(enData.ENgetnodeid(i+1))
    
    for i in range(nLinks):
        node1, node2 = enData.ENgetlinknodes(i+1)
        linkid = enData.ENgetlinkid(i+1)
        edgekey.append((enData.ENgetnodeid(node1), enData.ENgetnodeid(node2), linkid))

    while True:
        t = enData.ENrunH()
        if np.mod(t,enData.ENgettimeparam(1)) == 0:
            time.append(t)
            for i in range(nNodes):
                node_P.append(enData.ENgetnodevalue(i+1, pyepanet.EN_HEAD))
                node_D.append(enData.ENgetnodevalue(i+1, pyepanet.EN_DEMAND))
            for i in range(nLinks):
                link_F.append(enData.ENgetlinkvalue(i+1, pyepanet.EN_FLOW))
                link_V.append(enData.ENgetlinkvalue(i+1, pyepanet.EN_VELOCITY))
        tstep = enData.ENnextH()
        if tstep <= 0:
            break

    node_P = np.array(node_P).reshape((-1,nNodes)).T
    node_D = np.array(node_D).reshape((-1,nNodes)).T
    link_F = np.array(link_F).reshape((-1,nLinks)).T
    link_V = np.array(link_V).reshape((-1,nLinks)).T
     
    if convert:
        flowunits = enData.ENgetflowunits()
        node_P = units.convert('Pressure', flowunits, node_P)
        node_D = units.convert('Demand', flowunits, node_D)
        link_F = units.convert('Flow', flowunits, link_F)
        link_V = units.convert('Velocity', flowunits, link_V)
    
    node_D = dict(zip(nodekey, node_D))      
    node_P = dict(zip(nodekey, node_P))      
    link_F = dict(zip(edgekey, link_F))      
    link_V = dict(zip(edgekey, link_V))      
    
    return [time, node_P, node_D, link_F, link_V]
    