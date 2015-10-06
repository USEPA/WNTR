#import wntr.pyepanet as pyepanet
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
    
import wntr.network
import wntr.pyepanet as pyepanet
import numpy as np

def todini(results, wn, Pstar):
    
    POut = {}
    PExp = {}
    PInRes = {}
    PInPump = {}
    
    for name, node in wn.nodes(wntr.network.Junction):
        h = np.array(results.node.loc['head',:,name]) # m
        p = np.array(results.node.loc['pressure',:,name])
        e = h - p # m
        q = np.array(results.node.loc['demand',:,name]) # m3/s
        POut[name] = q*h
        PExp[name] = q*(Pstar+e)
    
    for name, node in wn.nodes(wntr.network.Reservoir):
        H = np.array(results.node.loc['head',:,name]) # m
        Q = np.array(results.node.loc['demand',:,name]) # m3/s
        PInRes[name] = -Q*H # switch sign on Q.
    
    for name, link in wn.links(wntr.network.Pump):
        start_node = link._start_node_name
        end_node = link._end_node_name
        h_start = np.array(results.node.loc['head',:,start_node]) # (m)
        h_end = np.array(results.node.loc['head',:,end_node]) # (m)
        h = h_start - h_end # (m) 
        q = np.array(results.link.loc['flowrate',:,name]) # (m^3/s)
        PInPump[name] = q*(abs(h)) # assumes that pumps always add energy to the system
    
    todini_index = (sum(POut.values()) - sum(PExp.values()))/  \
        (sum(PInRes.values()) + sum(PInPump.values()) - sum(PExp.values()))
    
    return todini_index.tolist()