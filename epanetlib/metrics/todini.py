import epanetlib.pyepanet as pyepanet
import numpy as np

def todini(G, Pstar):
    
    POut = {}
    PExp = {}
    PInRes = {}
    PInPump = {}
    
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            h = np.array(G.node[i]['head']) # m
            e = G.node[i]['elevation'] # m
            q = np.array(G.node[i]['demand']) # m3/s
            POut[i] = q*h
            PExp[i] = q*(Pstar+e)
        if G.node[i]['nodetype'] == pyepanet.EN_RESERVOIR:
            H = np.array(G.node[i]['head']) # m
            Q = np.array(G.node[i]['demand']) # m3/s
            PInRes[i] = -Q*H # switch sign on Q.
    
    for i,j,k in G.edges(keys=True):
        if G.edge[i][j][k]['linktype']  == pyepanet.EN_PUMP:
            h = np.array(G.edge[i][j][k]['headloss'])  # m
            e = G.node[i]['elevation'] # m
            q = np.array(G.edge[i][j][k]['flow']) # m3/s
            PInPump[k] = q*(abs(h))
    
    todini_index = (sum(POut.values()) - sum(PExp.values()))/  \
        (sum(PInRes.values()) + sum(PInPump.values()) - sum(PExp.values()))
    
    return todini_index.tolist()
    