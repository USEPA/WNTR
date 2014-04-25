import epanetlib.pyepanet as pyepanet
from epanetlib.units import convert
import networkx as nx
import numpy as np

def todini(G, Pstar):
    
    flowunits = G.graph['flowunits']
    
    h_star = convert('Pressure', flowunits, Pstar) # m

    POut = {}
    PExp = {}
    PInRes = {}
    PInPump = {}
    
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            h = convert('Hydraulic Head', flowunits, np.array(G.node[i]['head'])) # m
            e = convert('Elevation', flowunits, G.node[i]['elevation'])# m
            q = convert('Demand', flowunits, np.array(G.node[i]['demand'])) # m3/s
            POut[i] = q*h
            PExp[i] = q*(h_star+e)
        if G.node[i]['nodetype'] == pyepanet.EN_RESERVOIR:
            H = convert('Hydraulic Head', flowunits, np.array(G.node[i]['head'])) # m
            Q = convert('Demand', flowunits, np.array(G.node[i]['demand'])) # m3/s
            PInRes[i] = -Q*H # switch sign on Q.
    
    for i,j,k in G.edges(keys=True):
        if G.edge[i][j][k]['linktype']  == pyepanet.EN_PUMP:
            h = convert('Hydraulic Head', flowunits, np.array(G.edge[i][j][k]['headloss'])) # m
            e = convert('Elevation', flowunits, G.node[i]['elevation'])# m
            q = convert('Flow', flowunits, np.array(G.edge[i][j][k]['flow'])) # m3/s
            PInPump[k] = q*(abs(h)+e)
            
    todini_index = (sum(POut.values()) - sum(PExp.values()))/  \
        (sum(PInRes.values()) + sum(PInPump.values()) - sum(PExp.values()))
    
    return todini_index.tolist()
    