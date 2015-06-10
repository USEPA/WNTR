#import epanetlib.pyepanet as pyepanet
#import numpy as np
#
#def todini(G, Pstar):
#    
#    POut = {}
#    PExp = {}
#    PInRes = {}
#    PInPump = {}
#    
#    for i in G.nodes():
#        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
#            h = np.array(G.node[i]['head']) # m
#            e = G.node[i]['elevation'] # m
#            q = np.array(G.node[i]['demand']) # m3/s
#            POut[i] = q*h
#            PExp[i] = q*(Pstar+e)
#        if G.node[i]['nodetype'] == pyepanet.EN_RESERVOIR:
#            H = np.array(G.node[i]['head']) # m
#            Q = np.array(G.node[i]['demand']) # m3/s
#            PInRes[i] = -Q*H # switch sign on Q.
#    
#    for i,j,k in G.edges(keys=True):
#        if G.edge[i][j][k]['linktype']  == pyepanet.EN_PUMP:
#            h = np.array(G.edge[i][j][k]['headloss'])  # m
#            e = G.node[i]['elevation'] # m
#            q = np.array(G.edge[i][j][k]['flow']) # m3/s
#            PInPump[k] = q*(abs(h))
#    
#    todini_index = (sum(POut.values()) - sum(PExp.values()))/  \
#        (sum(PInRes.values()) + sum(PInPump.values()) - sum(PExp.values()))
#    
#    return todini_index.tolist()
    
    
import epanetlib.pyepanet as pyepanet
import numpy as np

def todini(results, wn, Pstar):
    
    POut = {}
    PExp = {}
    PInRes = {}
    PInPump = {}
    
    for i in results.node.index.levels[0]:
        type_temp = results.node.loc[i,'type'] # create temporary list of node types for each time
        if all(type_temp.str.findall('junction')): # determine if nodes are junctions
            h = np.array(results.node.loc[i,'head']) # m
            p = np.array(results.node.loc[i,'pressure'])
            e = h - p # m
            q = np.array(results.node.loc[i,'demand']) # m3/s
            POut[i] = q*h
            PExp[i] = q*(Pstar+e)
        if all(type_temp.str.findall('reservoir')): # determine if nodes are reservoirs
            H = np.array(results.node.loc[i,'head']) # m
            Q = np.array(results.node.loc[i,'demand']) # m3/s
            PInRes[i] = -Q*H # switch sign on Q.
    
    for i in results.link.index.levels[0]:
        type_temp = results.link.loc[i,'type'] # create temporary list of link types for each time
        if all(type_temp.str.findall('pump')): # determine if nodes are junctions
            start_node = wn.get_link(i)._start_node_name
            end_node = wn.get_link(i)._end_node_name
            h_start = np.array(results.node.loc[start_node,'head']) # (m)
            h_end = np.array(results.node.loc[end_node,'head']) # (m)
            h = h_start - h_end # (m) 
            q = np.array(results.link.loc[i,'flowrate']) # (m^3/s)
            PInPump[i] = q*(abs(h)) # assumes that pumps always add energy to the system
    
    todini_index = (sum(POut.values()) - sum(PExp.values()))/  \
        (sum(PInRes.values()) + sum(PInPump.values()) - sum(PExp.values()))
    
    return todini_index.tolist()