import wntr.pyepanet as pyepanet
import numpy as np

def average_water_consumed_perday(enData):
    qbar = {}
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT) 
    for nodeindex in range(1,nNodes+1):
        nodeid = enData.ENgetnodeid(nodeindex)
        
        numdemands = enData.ENgetnumdemands(nodeindex)
        L = {}
        pattID = {}
        for k in range(numdemands):
            pattID[k] = enData.ENgetdemandpattern(nodeindex, k)
            L[k] = enData.ENgetpatternlen(pattID)
        lcm_n = lcml(L.values())
        
        qbar_n = 0
        for k in range(numdemands):    
            qbase = enData.ENgetbasedemand(nodeindex, k)
            for t in range(lcm_n):
                m = enData.ENgetpatternvalue(pattID[k], np.mod(t,L[k]))
                qbar_n = qbar_n + qbase*m/lcm_n
        qbar[nodeid] = qbar_n    
        
    return qbar
    
def average_demand_perday(results):
    # qbar = average demand per day
    
    qbar = dict.fromkeys(results.node.index.levels[0])
    for i in results.node.index.levels[0]:
        type_temp = results.node.loc[i,'type'] # create temporary list of node types for each time
        if all(type_temp.str.findall('junction')): # determine if nodes are junctions
            qbar[i] = np.mean(results.node.loc[i,'demand'])*3600*24 # m3/day
        else:
            qbar[i] = 0
            
    return qbar

def population(qbar, R):
    # pop = population per node
    pop = np.array(qbar.values())/R
    pop.astype(int)
    pop = dict(zip(qbar.keys(), pop.astype(int)))
    return pop


def ingestion_timing_D24(G):
    pass

def ingestion_timing_F5():
    pass

def ingestion_timing_P5():
    pass

def ingestion_volume_M():
    per_capita_ingestion_volume = 0
    return per_capita_ingestion_volume
    
def ingestion_volumne_P():
    per_capita_ingestion_volume = 0
    return per_capita_ingestion_volume


def gcd(x,y):
  while y:
    if y<0:
      x,y=-x,-y
    x,y=y,x % y
    return x

def gcdl(*list):
  return reduce(gcd, *list)

def lcm(x,y):
  return x*y / gcd(x,y)

def lcml(*list):
  return reduce(lcm, *list)
  
  

def VC(G):
    # VC = volume of water consumed
    VC = dict.fromkeys(G.nodes())
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            VC[i] = np.sum(G.node[i]['demand'])
        else:
            VC[i] = 0
    return VC
    
def MC(G):
    # MC = mass of water consumed
    MC = dict.fromkeys(G.nodes())
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            MC[i] = np.sum(np.array(G.node[i]['demand'])*np.array(G.node[i]['quality']))
        else:
            MC[i] = 0
    return MC
    

    
    