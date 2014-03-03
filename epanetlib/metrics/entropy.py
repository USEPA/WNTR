import epanetlib.pyepanet as pyepanet
import networkx as nx
import epanetlib.network.networkx_extensions as nx_ext

def entropy(G):

    if G.is_directed() == False:
        return
        
    sources = []
    for i in G.nodes():
        if G.node[i]['nodetype'] == pyepanet.EN_RESERVOIR:
            sources.append(i)
        
    for i in G.nodes():
        sp = []
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            for j in sources:
                if nx.has_path(G, j, i):
                    simple_paths = nx_ext.all_simple_paths(G,source=j,target=i)
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
            Uj = G.predecessors(i) # set of nodes on the upstream ends of links incident on node j
            for j in Uj:
                for k in G[j][i].keys():
                    qij.append(G[j][i][k]['weight'])
            Qj = sum(qij) # Total flow into node j
                    
    Q0 = sum(nx_ext.get_edge_attributes_MG(G, 'weight').values())        

    Shat = 0
    
    return Shat
