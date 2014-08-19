import epanetlib.pyepanet as pyepanet
from epanetlib.network import epanet_to_MultiDiGraph
import numpy as np
from epanetlib.units import convert

def eps_waterqual(enData, G=None, convert_units=True):
    
    if G == None:
        G = epanet_to_MultiDiGraph(enData)
    
    if G.graph['time'] == []:
        duration = enData.ENgettimeparam(pyepanet.EN_DURATION)
        timestep = enData.ENgettimeparam(pyepanet.EN_REPORTSTEP)
        G.graph['time'] = range(0,duration+1,timestep) 
        
    enData.ENsolveH()
    enData.ENopenQ()
    enData.ENinitQ(1)
    
    for i in G.nodes():
        G.node[i]['quality'] = []
        
    for u,v,k in G.edges(keys=True):
        G[u][v][k]['quality'] = []
    
    while True:
        t = enData.ENrunQ()
        if t in G.graph['time']:
            for i in G.nodes():
                nodeindex = enData.ENgetnodeindex(i)
                
                quality = enData.ENgetnodevalue(nodeindex, pyepanet.EN_QUALITY)
                
                if convert_units:
                    if enData.ENgetqualtype()[0] == pyepanet.EN_CHEM:
                        quality = convert('Concentration', G.graph['flowunits'], quality) # kg/m3
                    elif enData.ENgetqualtype()[0] == pyepanet.EN_AGE:
                        quality = convert('Water Age', G.graph['flowunits'], quality) # s
                
                G.node[i]['quality'].append(quality)
                
            """
            EN_LINKQUAL is TNT in the toolkit
            for u,v,k in G.edges(keys=True):
                linkindex = enData.ENgetlinkindex(k)
                
                quality = enData.ENgetlinkvalue(linkindex, pyepanet.EN_LINKQUAL)
                
                if convert_units:
                    if enData.ENgetqualtype() == pyepanet.EN_CHEM:
                        quality = convert('Concentration', G.graph['flowunits'], quality) # kg/m3
                    elif enData.ENgetqualtype() == pyepanet.EN_AGE:
                        quality = convert('Water Age', G.graph['flowunits'], quality) # s
                
                G[u][v][k]['conc'].append(quality)
            """
                
        tstep = enData.ENnextQ()
        if tstep <= 0:
            break
    
    return G
