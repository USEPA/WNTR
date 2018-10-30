"""
The wntr.network.graph module includes methods to represent a water network 
model as a NetworkX MultiDiGraph, and compute topographic metrics on the graph.

"""
import networkx as nx
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class WntrMultiDiGraph(nx.MultiDiGraph):
    """
    Extension of networkx MultiDiGraph
    """

    def weight_graph(self, node_attribute={}, link_attribute={}):
        """
        Return a weighted graph based on node and link attributes.
        The weighted graph changes the direction of the original link if the weight is negative.

        Parameters
        ----------
        G : graph
            Networkx graph
        node_attribute :  dict or pandas Series
            Node attributes
        link_attribues : dict or pandas Series
            Link attributes

        Returns
        -------
        Networkx weighted graph
        
        """

        for node_name in self.nodes():
            try:
                value = node_attribute[node_name]

                nx.set_node_attributes(self, name='weight', values={node_name: value})
            except:
                pass

        for (node1, node2, link_name) in list(self.edges(keys=True)):
            try:
                value = link_attribute[link_name]

                if value < 0: # change the direction of the link and value
                    link_type = self[node1][node2][link_name]['type'] # 'type' should be the only other attribute on G.edge
                    self.remove_edge(node1, node2, link_name)
                    self.add_edge(node2, node1, link_name)
                    nx.set_edge_attributes(self, name='type', values={(node2, node1, link_name): link_type})
                    nx.set_edge_attributes(self, name='weight', values={(node2, node1, link_name): -value})
                else:
                    nx.set_edge_attributes(self, name='weight', values={(node1, node2, link_name): value})
            except:
                    pass

    def terminal_nodes(self):
        """
        Get all nodes with degree 1

        Parameters
        ----------
        G : graph
            A networkx graph

        Returns
        -------
        List of terminal node names
        
        """

        node_degree = dict(self.degree())
        terminal_nodes = [k for k,v in node_degree.items() if v == 1]

        return terminal_nodes

    def bridges(self):
        """
        Get bridge links (uses an undirected graph)

        Parameters
        ----------
        G : graph
            A networkx graph

        Returns
        -------
        List of links that are bridges
        
        """
        n = nx.number_connected_components(self.to_undirected())
        bridges = []
        for (node1, node2, link_name) in list(self.edges(keys=True)):
            # if node1 and node2 have a neighbor in common, no bridge
            if len(set(self.neighbors(node1)) & set(self.neighbors(node2))) == 0:
                self.remove_edge(node1, node2, key=link_name)
                if nx.number_connected_components(self.to_undirected()) > n:
                    bridges.append(link_name)
                self.add_edge(node1, node2, key=link_name)

        return bridges

    def central_point_dominance(self):
        """
        Compute central point dominance

        Returns
        -------
        Central point dominance (float)
        
        """
        bet_cen = nx.betweenness_centrality(self.to_undirected())
        bet_cen = list(bet_cen.values())
        cpd = sum(max(bet_cen) - np.array(bet_cen))/(len(bet_cen)-1)

        return cpd

    def spectral_gap(self):
        """
        Spectral gap. Difference in the first and second eigenvalue of
        the adjacency matrix

        Returns
        -------
        Spectral gap (float)
        
        """

        eig = nx.adjacency_spectrum(self.to_undirected())
        spectral_gap = abs(eig[0] - eig[1])

        return spectral_gap.real

    def algebraic_connectivity(self):
        """
        Algebraic connectivity. Second smallest eigenvalue of the normalized
        Laplacian matrix of a network. Uses an undirected graph.

        Returns
        -------
        Algebraic connectivity (float)
        
        """
        eig = nx.laplacian_spectrum(self.to_undirected())
        eig = np.sort(eig)
        alg_con = eig[1]

        return alg_con

    def critical_ratio_defrag(self):
        """
        Critical ratio of defragmentation.

        Returns
        -------
        Critical ratio of defragmentation (float)
        
        """
        node_degree = dict(self.degree())
        tmp = np.mean(pow(np.array(list(node_degree.values())),2))
        fc = 1-(1/((tmp/np.mean(list(node_degree.values())))-1))

        return fc

    def links_in_simple_paths(self, sources, sinks):
        """
        Count all links in a simple path between sources and sinks

        Parameters
        -----------
        sources : list
            List of source nodes
        sinks : list
            List of sink nodes
        sinks : list
            List of sink nodes

        Returns
        -------
        Dictionary with the number of times each link is involved in a path
        
        """
        link_names = [name for (node1, node2, name) in list(self.edges(keys=True))]
        link_count = pd.Series(data = 0, index=link_names)

        for sink in sinks:
            for source in sources:
                if nx.has_path(self, source, sink):
                    paths = _all_simple_paths(self,source,target=sink)
                    for path in paths:
                        for i in range(len(path)-1):
                            links = list(self[path[i]][path[i+1]].keys())
                            for link in links:
                                link_count[link] = link_count[link]+1

        return link_count


def _all_simple_paths(G, source, target, cutoff=None):
    """
    Adaptation of nx.all_simple_paths for multigraphs
    """

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
    stack = [(v for u,v,k in list(G.edges(source, keys=True)))]
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
                stack.append((v for u,v in list(G.edges(child))))
        else: #len(visited) == cutoff:
            count = ([child]+list(children)).count(target)
            for i in range(count):
                yield visited + [target]
            stack.pop()
            visited.pop()

