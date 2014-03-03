import epanetlib.pyepanet as pyepanet
from epanetlib.units import convert
import networkx as nx
import numpy as np

def todini(G, Pstar):
    
    flowunits = G.graph['flowunits']
    
    Pstar = convert('Pressure', flowunits, 30) # m
    P = nx.get_node_attributes(G,'pressure')
    D = nx.get_node_attributes(G,'demand')

    #P = dict(zip(node_P.keys(), convert('Pressure', flowunits, np.array(node_P.values())))) # m
    #D = dict(zip(node_D.keys(), convert('Demand', flowunits, np.array(node_D.values())))) # m3/s

    numer = 0
    denom1 = 0
    denom2 = 0
    
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            numer = numer + np.array(D[i])*(np.array(P[i]) - Pstar)
            denom2 = denom2 + np.array(D[i])*Pstar
        if G.node[i]['nodetype'] == pyepanet.EN_RESERVOIR:
            denom1 = denom1 - np.array(D[i])*np.array(P[i]) # switch sign on D.
          
    todini_index = numer/(denom1 - denom2)
    
    return todini_index.tolist()
    