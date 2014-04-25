import epanetlib.pyepanet as pyepanet
from epanetlib.network import epanet_to_MultiDiGraph
import numpy as np

def eps_hydraulic(enData, G=None):
    
    if G == None:
        G = epanet_to_MultiDiGraph(enData)
    
    enData.ENinitH(0)
    
    for i in G.nodes():
        G.node[i]['head'] = []
        G.node[i]['demand'] = []
        
    for u,v,k in G.edges(keys=True):
        G[u][v][k]['flow'] = []
        G[u][v][k]['velocity'] = []
        G[u][v][k]['headloss'] = []
        
    while True:
        t = enData.ENrunH()
        if np.mod(t,enData.ENgettimeparam(1)) == 0:
            G.graph['time'] = G.graph['time'] + [t]
            for i in G.nodes():
                nodeindex = enData.ENgetnodeindex(i)
                G.node[i]['head'].append(enData.ENgetnodevalue(nodeindex, pyepanet.EN_HEAD))
                G.node[i]['demand'].append(enData.ENgetnodevalue(nodeindex, pyepanet.EN_DEMAND))
            for u,v,k in G.edges(keys=True):
                linkindex = enData.ENgetlinkindex(k)
                G[u][v][k]['flow'].append(enData.ENgetlinkvalue(linkindex, pyepanet.EN_FLOW))
                G[u][v][k]['velocity'].append(enData.ENgetlinkvalue(linkindex, pyepanet.EN_VELOCITY))
                G[u][v][k]['headloss'].append(enData.ENgetlinkvalue(linkindex, pyepanet.EN_HEADLOSS))
        tstep = enData.ENnextH()
        if tstep <= 0:
            break
    
    return G
