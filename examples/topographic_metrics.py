import epanetlib as en
import numpy as np 
import networkx as nx
from sympy.physics import units
import matplotlib.pyplot as plt

plt.close('all')

# Create a WaterNetworkModel
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, 'networks/Net3.inp')

# Get a copy of the graph and convert the MultiDiGraph to a MultiGraph
G = wn.get_graph_copy().to_undirected()

# Basic plot
en.network.draw_graph(wn, title= wn.name)
            
# General topographic information = type, number of nodes, number of edges, 
# average degree
print nx.info(G)

# Example of setting node and edge attribute from the network class and 
# plotting the graph. NX graph requires a dictionary indexed by 
# (start_node, end_node, link_name) to set edge attribute
junction_attr = wn.get_node_attribute('elevation', node_type=en.network.Junction)
pipe_attr = wn.get_link_attribute('length', link_type=en.network.Pipe)
en.network.draw_graph(wn, node_attribute=junction_attr, 
                           link_attribute=pipe_attr, title='Node elevation and pipe length', 
                           node_size=40, link_width=2)

# Link density = 2m/n(n-1) where n is the number of nodes and m is the number
# of edges in G. The density is 0 for a graph without edges and 1 for a dense
# graph (a graph with the maximum number of edges). The density of multigraphs
# can be higher than 1.
print "Link density: " + str(nx.density(G))

# Self loop = a link that connects a node to itself
print "Number of self loops: " + str(G.number_of_selfloops())

# Node degree = number of links per node
node_degree = G.degree()
en.network.draw_graph(wn, node_attribute=node_degree,
                      title='Node Degree', node_size=40, node_range=[1,5])

# Terminal nodes (degree = 1)
terminal_nodes = en.network.terminal_nodes(G)
en.network.draw_graph(wn, node_attribute=terminal_nodes,
                      title='Terminal nodes', node_size=40, node_range=[0,1])
print "Number of terminal nodes: " + str(len(terminal_nodes))
print "   " + str(terminal_nodes)

# NZD nodes
nzd_nodes = wn.query_node_attribute('base_demand', np.greater, 0.0)
en.network.draw_graph(wn, node_attribute=nzd_nodes.keys(),
                      title='NZD nodes', node_size=40, node_range=[0,1])
print "Number of NZD nodes: " + str(len(nzd_nodes))
print "   " + str(nzd_nodes.keys())

# Pipes with diameter > threshold
diameter = 20*float((units.inches/units.m)) # in to m
pipes = wn.query_link_attribute('diameter', np.greater, diameter)
en.network.draw_graph(wn, link_attribute=pipes.keys(), 
                           title='Pipes > 20 inches', link_width=2, link_range=[0,1])
print "Number of pipes > 20 inches: " + str(len(pipes))
print "   " + str(pipes)

# Nodes with elevation <= treshold
elevation = 5*float((units.ft/units.m)) # ft to m
nodes = wn.query_node_attribute('elevation', np.less_equal, elevation)
en.network.draw_graph(wn, node_attribute=nodes.keys(), 
                           title='Nodes <= 5 ft elevation', node_size=40, node_range=[0,1])
print "Number of nodes <= 5 ft elevation: " + str(len(nodes))
print "   " + str(nodes)

if nx.is_connected(G):
    # Eccentricity = maximum distance from node to all other nodes in G
    ecc = nx.eccentricity(G)
    en.network.draw_graph(wn, node_attribute=ecc,
                          title='Eccentricity', node_size=40, node_range=[15, 30])

    # Diameter = maximum eccentricity. The eccentricity of a node v is the maximum
    # distance from v to all other nodes in G.
    print "Diameter: " + str(nx.diameter(G))

    # Shortest path length and average shortest path length
    #nx.shortest_path_length(G)
    print "Average shortest path length: " + str(nx.average_shortest_path_length(G))
else:
    print "Diameter: NaN, network is not connected"
    print "Average shortest path length: NaN, network is not connected"

# Cluster coefficient = function of the number of triangles through a node
clust_coefficients = nx.clustering(nx.Graph(G))
en.network.draw_graph(wn, node_attribute=clust_coefficients,
                      title='Clustering Coefficient', node_size=40)

# Meshedness coefficient
meshedness = float(G.number_of_edges() - G.number_of_nodes() + 1)/(2*G.number_of_nodes()-5)
print "Meshedness coefficient: " + str(meshedness)

# Betweenness centrality = number of times a node acts as a bridge along the
# shortest path between two other nodes.
bet_cen = nx.betweenness_centrality(G)
bet_cen_trim = dict([(k,v) for k,v in bet_cen.iteritems() if v > 0.1])
en.network.draw_graph(wn, node_attribute=bet_cen_trim,
                      title='Betweenness Centrality', node_size=40, node_range=[0.1, 0.4])
central_pt_dom = sum(max(bet_cen.values()) - np.array(bet_cen.values()))/G.number_of_nodes()
print "Central point dominance: " + str(central_pt_dom)


# Articulation point = any node whose removal (along with all its incident
# edges) increases the number of connected components of a graph
Nap = list(nx.articulation_points(G))
Nap = list(set(Nap)) # get the unique nodes in Nap
Nap_density = float(len(Nap))/G.number_of_nodes()
print "Density of articulation points: " + str(Nap_density)
en.network.draw_graph(wn, node_attribute=Nap,
                      title='Articulation Point', node_size=40, node_range=[0,1])

# Bridge = a link is considered a bridge if the removal of that link increases 
# the number of connected components in the network.
bridges = en.network.bridges(G)
en.network.draw_graph(wn, link_attribute=bridges, title='Bridges', link_width=2, link_range=[0,1])
Nbr_density = float(len(bridges))/G.number_of_edges()
print "Density of bridges: " + str(Nbr_density)

# Spectal gap = difference in the first and second eigenvalue of the adj matrix
eig = nx.adjacency_spectrum(G)
spectral_gap = eig[0] - eig[1]
print "Spectal gap: " + str(spectral_gap.real)

# Algebraic connectivity =  second smallest eigenvalue of the normalized
# Laplacian matrix of a network.
eig = nx.laplacian_spectrum(G)
alg_con = eig[-2]
print "Algebraic connectivity: " + str(alg_con)

# Critical ratio of defragmentation
tmp = np.mean(pow(np.array(node_degree.values()),2))
fc = 1-(1/((tmp/np.mean(node_degree.values()))-1))
print "Critical ratio of defragmentation: " + str(fc)

# Closeness centrality = inverse of the sum of shortest path from one node to
# all other nodes
clo_cen = nx.closeness_centrality(G)
en.network.draw_graph(wn, node_attribute=clo_cen,
                      title='Closeness Centrality', node_size=40)
