import epanetlib.pyepanet as pyepanet
import networkx as nx
import epanetlib.network.networkx_extensions as nx_ext

def entropy(DG, enData):
    
    
    
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT) 
    
    sources = []
    for i in range(nNodes):
        if enData.ENgetnodetype(i+1) == pyepanet.EN_RESERVOIR:
            nodeid = enData.ENgetnodeid(i+1)
            sources.append(nodeid)
        
    for i in range(nNodes):
        sp = []
        if enData.ENgetnodetype(i+1) == pyepanet.EN_JUNCTION:
            nodeid = enData.ENgetnodeid(i+1)
            for j in sources:
                if nx.has_path(DG, j, nodeid):
                    simple_paths = nx_ext.all_simple_paths(DG,source=j,target=nodeid)
                    sp = sp + ([p for p in simple_paths]) 
                    # all_simple_paths was modified to check 'has_path' in the
                    # loop, but this is still slow for large networks
                    # what if the network was skeletonized based on series pipes 
                    # that have the same flow direction?
                    # what about duplicating paths that have pipes in series?
                #print j, nodeid, len(sp)
            
            NDij = len(sp) # number of paths through the link from node i to node j
            MDij = [] # number of links in the NDij path
            for j in sp:
                MDij.append(len(j))
                
            qij = [] # flow in link from node i to node j
            Uj = DG.predecessors(nodeid) # set of nodes on the upstream ends of links incident on node j
            for j in Uj:
                for k in DG[j][nodeid].keys():
                    qij.append(DG[j][nodeid][k]['weight'])
            Qj = sum(qij) # Total flow into node j
                    
    Q0 = sum(nx_ext.get_edge_attributes_MG(DG, 'weight').values())        

    Shat = 0
    
    return Shat
