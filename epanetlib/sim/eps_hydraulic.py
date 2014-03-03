import epanetlib.pyepanet as pyepanet
from epanetlib.network import epanet_to_MultiDiGraph
import numpy as np

def eps_hydraulic(enData, G=None):
    
    if G == None:
        G = epanet_to_MultiDiGraph(enData)
    
    enData.ENinitH(0)
    
    for i in G.nodes():
        G.node[i]['pressure'] = []
        G.node[i]['demand'] = []
        
    for u,v,k in G.edges(keys=True):
        G[u][v][k]['flow'] = []
        G[u][v][k]['velocity'] = []
        
    while True:
        t = enData.ENrunH()
        if np.mod(t,enData.ENgettimeparam(1)) == 0:
            G.graph['time'] = G.graph['time'] + [t]
            for i in G.nodes():
                nodeindex = enData.ENgetnodeindex(i)
                G.node[i]['pressure'].append(enData.ENgetnodevalue(nodeindex, pyepanet.EN_HEAD))
                G.node[i]['demand'].append(enData.ENgetnodevalue(nodeindex, pyepanet.EN_DEMAND))
            for u,v,k in G.edges(keys=True):
                linkindex = enData.ENgetlinkindex(k)
                G[u][v][k]['flow'].append(enData.ENgetlinkvalue(linkindex, pyepanet.EN_FLOW))
                G[u][v][k]['velocity'].append(enData.ENgetlinkvalue(linkindex, pyepanet.EN_VELOCITY))
        tstep = enData.ENnextH()
        if tstep <= 0:
            break
    
    return G
    
"""
    if G == None:
        G = epanet_to_MultiGraph(enData)
        
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT)
    nLinks = enData.ENgetcount(pyepanet.EN_LINKCOUNT) 
    
    enData.ENinitH(0)

    nodekey = []
    edgekey = []
    
    node_P = []
    node_D = []
    link_F = []
    link_V = []
            
    for i in range(nNodes):
        nodeid = enData.ENgetnodeid(i+1)
        nodekey.append(nodeid)
        G.node[nodeid]['pressure'] = []
        G.node[nodeid]['demand'] = []
        
    for i in range(nLinks):
        node1, node2 = enData.ENgetlinknodes(i+1)
        node1id = enData.ENgetnodeid(node1)
        nodeid2 = enData.ENgetnodeid(node2)
        linkid = enData.ENgetlinkid(i+1)
        edgekey.append((enData.ENgetnodeid(node1), enData.ENgetnodeid(node2), linkid))
        G[node1id][nodeid2][linkid]['flow'] = []
        G[node1id][nodeid2][linkid]['velocity'] = []
        
    while True:
        t = enData.ENrunH()
        if np.mod(t,enData.ENgettimeparam(1)) == 0:
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

     
    node_D = dict(zip(nodekey, node_D))      
    node_P = dict(zip(nodekey, node_P))      
    link_F = dict(zip(edgekey, link_F))      
    link_V = dict(zip(edgekey, link_V))      
    
    nx.set_node_attributes(G,'demand', node_D)
    nx.set_node_attributes(G,'pressure', node_P)
    networkx_extensions.set_edge_attributes_MG(G,'flow', link_F)
    networkx_extensions.set_edge_attributes_MG(G,'velocity', link_V)
"""
    