import networkx as nx

def terminal_nodes(G):
    """ Get all nodes with degree 1
    
    Parameters
    ----------
    G : graph
        A networkx graph
        
    Returns
    -------
    terminal_nodes : list
        list of node indexes
    """
    
    node_degree = G.degree() 
    terminal_nodes = [k for k,v in node_degree.iteritems() if v == 1]
    
    return terminal_nodes

def bridges(G):
    """ Get bridge links"""
    
    n = nx.number_connected_components(G)
    bridges = []
    for (node1, node2, link_name) in G.edges(keys=True):
        # if node1 and node2 have a neighbor in common, no bridge
        if len(set(G.neighbors(node1)) & set(G.neighbors(node2))) == 0: 
            G.remove_edge(node1, node2, key=link_name)
            if nx.number_connected_components(G) > n:
                bridges.append(link_name)
            G.add_edge(node1, node2, key=link_name)
    
    return bridges
    
"""
Extension of networkx functions
"""        
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