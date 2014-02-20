"""
Extension of networkx functions
"""
import networkx as nx

def set_edge_attributes_MG(MG,name,attributes):
    #Adaptation of nx.set_edge_attributes
    
    for (u,v,k),value in attributes.items():
        MG.edge[u][v][k][name]=value
        
def get_edge_attributes_MG(MG,name):
    #Adaptation of nx.get_edge_attributes

    return dict( ((u,v,k),d[name]) for u,v,k,d in MG.edges(keys=True,data=True) if name in d)
        
def all_simple_paths(G, source, target, cutoff=None):
    # Adaptation of nx.all_simple_paths
    
    if source not in G:
        raise nx.NetworkXError('source node %s not in graph'%source)
    if target not in G:
        raise nx.NetworkXError('target node %s not in graph'%target)
    if cutoff is None:
        cutoff = len(G)-1
    if G.is_multigraph():
        return _all_simple_paths_multigraph(G, source, target, cutoff=cutoff)
    else:
        return 1 #_all_simple_paths_graph(G, source, target, cutoff=cutoff)


def _all_simple_paths_multigraph(G, source, target, cutoff=None):
    if cutoff < 1:
        return
    visited = [source]
    stack = [(v for u,v,k in G.edges(source, keys=True))]
    while stack:
        children = stack[-1]
        child = next(children, None)
        if child is None:
            stack.pop()
            visited.pop()
        elif nx.has_path(G, child, target) == False: # added kaklise
            pass
        elif len(visited) < cutoff:
            if child == target:
                yield visited + [target]
            elif child not in visited:
                visited.append(child)
                stack.append((v for u,v in G.edges(child)))
        else: #len(visited) == cutoff:
            count = ([child]+list(children)).count(target)
            for i in range(count):
                yield visited + [target]
            stack.pop()
            visited.pop()