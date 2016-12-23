"""
The wntr.network.graph module includes methods to represent a water network 
model as a MultiDiGraph, compute topographic metrics on the graph, and plot the 
water network model. 
"""
import networkx as nx
import numpy as np
import pandas as pd
try:
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
except:
    pass
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
            A networkx graph
        node_attribute :  dict or pandas Series
            node attributes
        link_attribues : dict or pandas Series
            link attributes


        Returns
        -------
        G : weighted graph
            A networkx weighted graph
        """
        
        for node_name in self.nodes():
            try:
                value = node_attribute[node_name]

                nx.set_node_attributes(self, 'weight', {node_name: value})
            except:
                pass

        for (node1, node2, link_name) in self.edges(keys=True):
            try:
                value = link_attribute[link_name]

                if value < 0: # change the direction of the link and value
                    link_type = self[node1][node2][link_name]['type'] # 'type' should be the only other attribute on G.edge
                    self.remove_edge(node1, node2, link_name)
                    self.add_edge(node2, node1, link_name)
                    nx.set_edge_attributes(self, 'type', {(node2, node1, link_name): link_type})
                    nx.set_edge_attributes(self, 'weight', {(node2, node1, link_name): -value})
                else:
                    nx.set_edge_attributes(self, 'weight', {(node1, node2, link_name): value})
            except:
                    pass

    def terminal_nodes(self):
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

        node_degree = self.degree()
        terminal_nodes = [k for k,v in node_degree.items() if v == 1]

        return terminal_nodes

    def bridges(self):
        """ Get bridge links. Uses an undirected graph.
        Parameters
        ----------
        G : graph
            A networkx graph


        Returns
        -------
        bridges : list
            list of link indexes
        """
        n = nx.number_connected_components(self.to_undirected())
        bridges = []
        for (node1, node2, link_name) in self.edges(keys=True):
            # if node1 and node2 have a neighbor in common, no bridge
            if len(set(self.neighbors(node1)) & set(self.neighbors(node2))) == 0:
                self.remove_edge(node1, node2, key=link_name)
                if nx.number_connected_components(self.to_undirected()) > n:
                    bridges.append(link_name)
                self.add_edge(node1, node2, key=link_name)

        return bridges

    def central_point_dominance(self):
        """ Compute central point dominance.
            
        Returns
        -------
        cpd : float
            Central point dominance
        """
        bet_cen = nx.betweenness_centrality(self.to_undirected())
        bet_cen = list(bet_cen.values())
        cpd = sum(max(bet_cen) - np.array(bet_cen))/(len(bet_cen)-1)

        return cpd

    def spectral_gap(self):
        """ Spectral gap. Difference in the first and second eigenvalue of
        the adj matrix

        Returns
        -------
        spectral_gap : float
            Spectral gap
        """

        eig = nx.adjacency_spectrum(self)
        spectral_gap = eig[0] - eig[1]

        return spectral_gap.real

    def algebraic_connectivity(self):
        """ Algebraic connectivity. Second smallest eigenvalue of the normalized
        Laplacian matrix of a network. Uses an undirected graph.

        Returns
        -------
        alg_con : float
            Algebraic connectivity
        """
        eig = nx.laplacian_spectrum(self.to_undirected())
        eig = np.sort(eig)
        alg_con = eig[1]

        return alg_con

    def critical_ratio_defrag(self):
        """ Critical ratio of defragmentation.

        Returns
        -------
        fd : float
            Critical ratio of defragmentation
        """
        node_degree = self.degree()
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
        link_count : dict
            A dictonary with the number of times each link is involved in a path
        """
        link_names = [name for (node1, node2, name) in self.edges(keys=True)]
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
    """Adaptation of nx.all_simple_paths for mutligraphs"""

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

def draw_graph(wn, node_attribute=None, link_attribute=None, title=None,
               node_size=10, node_range = [None,None], node_cmap=None,
               link_width=1, link_range = [None,None], link_cmap=None,
               add_colorbar=True, figsize=None, dpi=None, directed=False, node_labels=False,plt_fig=None):

    """
    Draw a WaterNetworkModel networkx graph

    Parameters
    ----------
    wn : WaterNetworkModel
        A WaterNetworkModel object

    node_attribute : str, list, pd.Series, or dict, optional
        (default = None)

        - If node_attribute is a string, then the node_attribute dictonary is
          populated using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node is given a value of 1.
        - If node_attribute is a pd.Series, then it shoud be in the format
          {(nodeid,time): x} or {nodeid: x} where nodeid is a string and x is a float.
          The time index is not used in the plot.
        - If node_attribute is a dict, then it shoud be in the format
          {nodeid: x} where nodeid is a string and x is a float

    link_attribute : str, list, pd.Series, or dict, optional
        (default = None)

        - If link_attribute is a string, then the link_attribute dictonary is
          populated using edge_attribute = wn.query_link_attribute(str)
        - If link_attribute is a list, then each link is given a value of 1.
        - If link_attribute is a pd.Series, then it shoud be in the format
          {(linkid,time): x} or {linkid: x} where linkid is a string and x is a float.
          The time index is not used in the plot.
        - If link_attribute is a dict, then it shoud be in the format
          {linkid: x} where linkid is a string and x is a float.

    title : str, optional
        (default = None)

    node_size : int, optional
        (default = 10)

    node_range : list, optional
        (default = [None,None])

    node_cmap : matplotlib.pyplot.cm colormap, optional
        (default = jet)

    link_width : int, optional
        (default = 1)

    link_range : list, optional
        (default = [None,None])

    link_cmap : matplotlib.pyplot.cm colormap, optional
        (default = jet)

    add_colorbar : bool, optional
        (default = True)

    directed : bool, optional
        (default = False)

    node_labels: bool, optional
        If True, the graph will have each node labeled with its name.
        (default = False)

    Returns
    -------
    Figure

    Examples
    --------
    >>> wn = en.network.WaterNetworkModel('Net1.inp')
    >>> en.network.draw_graph(wn)

    Notes
    -----
    For more network draw options, see nx.draw_networkx
    """
    
    if plt_fig is None:
        plt.figure(facecolor='w', edgecolor='k')

    # Graph
    G = wn.get_graph_deep_copy()
    if not directed:
        G = G.to_undirected()

    # Position
    pos = nx.get_node_attributes(G,'pos')
    if len(pos) == 0:
        pos = None

    # Node attribute
    if isinstance(node_attribute, str):
        node_attribute = wn.query_node_attribute(node_attribute)
    if isinstance(node_attribute, list):
        node_attribute = dict(zip(node_attribute,[1]*len(node_attribute)))
    if isinstance(node_attribute, pd.Series):
        if node_attribute.index.nlevels == 2: # (nodeid, time) index
            node_attribute.reset_index(level=1, drop=True, inplace=True) # drop time
        node_attribute = dict(node_attribute)

    # Define node list, color, and colormap
    if node_attribute is None:
        nodelist = None
        nodecolor = 'k'
    else:
        nodelist,nodecolor = zip(*node_attribute.items())
    if node_cmap is None:
        node_cmap=plt.cm.jet

    # Link attribute
    if isinstance(link_attribute, str):
        link_attribute = wn.query_link_attribute(link_attribute)
    if isinstance(link_attribute, list):
        link_attribute = dict(zip(link_attribute,[1]*len(link_attribute)))
    if isinstance(link_attribute, pd.Series):
        if link_attribute.index.nlevels == 2: # (linkid, time) index
            link_attribute.reset_index(level=1, drop=True, inplace=True) # drop time
        link_attribute = dict(link_attribute)

    # Replace link_attribute dictonary defined as
    # {link_name: attr} with {(start_node, end_node, link_name): attr}
    if link_attribute is not None:
        attr = {}
        for link_name, value in link_attribute.items():
            link = wn.get_link(link_name)
            attr[(link.start_node(), link.end_node(), link_name)] = value
        link_attribute = attr
    if type(link_width) is dict:
        attr = {}
        for link_name, value in link_width.items():
            link = wn.get_link(link_name)
            attr[(link.start_node(), link.end_node(), link_name)] = value
        link_width = attr

    # Define link list, color, and colormap
    if link_attribute is None:
        linklist = None
        linkcolor = 'k'
    else:
        linklist,linkcolor = zip(*link_attribute.items())
    if type(link_width) is dict:
        linklist2,link_width = zip(*link_width.items())
        if not linklist == linklist2:
            logger.warning('Link color and width do not share the same indexes, link width changed to 1.')
            link_width = 1
    if link_cmap is None:
        link_cmap=plt.cm.jet

    # Plot
    #plt.figure(facecolor='w', edgecolor='k', figsize=figsize, dpi=dpi)

    if title is not None:
        plt.title(title)

    if node_labels:
        nodes = nx.draw_networkx_labels(G, pos,
                                       nodelist=nodelist, node_color=nodecolor, node_size=node_size, cmap=node_cmap, vmin = node_range[0], vmax = node_range[1],linewidths=0)
    else:
        nodes = nx.draw_networkx_nodes(G, pos, with_labels=False,
                                       nodelist=nodelist, node_color=nodecolor, node_size=node_size, cmap=node_cmap, vmin = node_range[0], vmax = node_range[1],linewidths=0)
    edges = nx.draw_networkx_edges(G, pos,
                                   edgelist=linklist, edge_color=linkcolor, width=link_width, edge_cmap=link_cmap, edge_vmin = link_range[0], edge_vmax = link_range[1])
    if add_colorbar and node_attribute:
        plt.colorbar(nodes, shrink=0.5, pad = 0)
    if add_colorbar and link_attribute:
        plt.colorbar(edges, shrink=0.5, pad = 0.05)
    plt.axis('off')

    return nodes, edges
