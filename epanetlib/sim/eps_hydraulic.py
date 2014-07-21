import epanetlib.pyepanet as pyepanet
from epanetlib.network import epanet_to_MultiDiGraph
import numpy as np
from epanetlib.units import convert

def eps_hydraulic(enData, G=None, convert_units=True):
    
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
                
                head = enData.ENgetnodevalue(nodeindex, pyepanet.EN_HEAD)
                demand = enData.ENgetnodevalue(nodeindex, pyepanet.EN_DEMAND)
                
                if convert_units:
                    head = convert('Hydraulic Head', G.graph['flowunits'], head) # m
                    demand = convert('Demand', G.graph['flowunits'], demand) # m3/s
                
                G.node[i]['head'].append(head)
                G.node[i]['demand'].append(demand)
                
            for u,v,k in G.edges(keys=True):
                linkindex = enData.ENgetlinkindex(k)
                
                flow = enData.ENgetlinkvalue(linkindex, pyepanet.EN_FLOW)
                velocity = enData.ENgetlinkvalue(linkindex, pyepanet.EN_VELOCITY)
                headloss = enData.ENgetlinkvalue(linkindex, pyepanet.EN_HEADLOSS)
                
                if convert_units:
                    flow = convert('Flow', G.graph['flowunits'], flow) # m3/s
                    velocity = convert('Velocity', G.graph['flowunits'], velocity) # m/s
                    headloss = convert('Hydraulic Head', G.graph['flowunits'], headloss) # m
                
                G[u][v][k]['flow'].append(flow)
                G[u][v][k]['velocity'].append(velocity)
                G[u][v][k]['headloss'].append(headloss)
                
        tstep = enData.ENnextH()
        if tstep <= 0:
            break
    
    return G
