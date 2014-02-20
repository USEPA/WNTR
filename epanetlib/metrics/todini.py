import epanetlib.pyepanet as pyepanet

def todini(enData, P, D, Pstar):
    
    numer = 0
    denom1 = 0
    denom2 = 0
    
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT) 
    
    for i in range(nNodes):
        node = enData.ENgetnodeid(i+1)
        if enData.ENgetnodetype(i+1) == pyepanet.EN_JUNCTION:
            numer = numer + D[node]*(P[node] - Pstar)
            denom2 = denom2 + D[node]*Pstar
        if enData.ENgetnodetype(i+1) == pyepanet.EN_RESERVOIR:
            denom1 = denom1 + -D[node]*P[node]
          
    todini_index = numer/(denom1 - denom2)
    
    return todini_index
    