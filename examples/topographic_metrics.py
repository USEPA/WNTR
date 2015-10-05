import wntr
import numpy as np 
import networkx as nx
import matplotlib.pyplot as plt
import os

plt.close('all')

# Create a water network model
my_path = os.path.abspath(os.path.dirname(__file__))
inp_file = os.path.join(my_path,'networks','Net3.inp')
wn = wntr.network.WaterNetworkModel(inp_file)

# Get a copy of the graph and convert the MultiDiGraph to a MultiGraph
G = wn.get_graph_deep_copy().to_undirected()

# Graph the network
wntr.network.draw_graph(wn, title= wn.name)
            
# Print general topographic information (type, number of nodes, 
# number of edges, average degree)
print nx.info(G)

# Set node and edge attribute and plot the graph. 
junction_attr = wn.query_node_attribute('elevation', 
                                      node_type=wntr.network.Junction)
pipe_attr = wn.query_link_attribute('length', link_type=wntr.network.Pipe)
wntr.network.draw_graph(wn, node_attribute=junction_attr, 
                           link_attribute=pipe_attr, 
                           title='Node elevation and pipe length', 
                           node_size=40, link_width=2)

# Compute link density (2m/n(n-1) where n is the number of nodes and m is the 
# number of edges in G. The density is 0 for a graph without edges and 1 for 
# a dense graph (a graph with the maximum number of edges). The density of 
# multigraphs can be higher than 1)
print "Link density: " + str(nx.density(G))

# Compute number of self loops (a link that connects a node to itself)
print "Number of self loops: " + str(G.number_of_selfloops())

# Compute node degree (number of links per node)
node_degree = G.degree()
wntr.network.draw_graph(wn, node_attribute=node_degree,
                      title='Node Degree', node_size=40, node_range=[1,5])

# Compute number of terminal nodes (degree = 1)
terminal_nodes = wntr.network.terminal_nodes(G)
wntr.network.draw_graph(wn, node_attribute=terminal_nodes,
                      title='Terminal nodes', node_size=40, node_range=[0,1])
print "Number of terminal nodes: " + str(len(terminal_nodes))
print "   " + str(terminal_nodes)

# Compute number of NZD nodes (base demand > 0)
nzd_nodes = wn.query_node_attribute('base_demand', np.greater, 0.0)
wntr.network.draw_graph(wn, node_attribute=nzd_nodes.keys(),
                      title='NZD nodes', node_size=40, node_range=[0,1])
print "Number of NZD nodes: " + str(len(nzd_nodes))
print "   " + str(nzd_nodes.keys())

# Compute pipes with diameter > threshold
diameter = 0.508 # m (20 inches)
pipes = wn.query_link_attribute('diameter', np.greater, diameter)
wntr.network.draw_graph(wn, link_attribute=pipes.keys(), 
                      title='Pipes > 20 inches', link_width=2, 
                      link_range=[0,1])
print "Number of pipes > 20 inches: " + str(len(pipes))
print "   " + str(pipes)

# Compute nodes with elevation <= treshold
elevation = 1.524 # m (5 feet)
nodes = wn.query_node_attribute('elevation', np.less_equal, elevation)
wntr.network.draw_graph(wn, node_attribute=nodes.keys(), 
                      title='Nodes <= 5 ft elevation', node_size=40, 
                      node_range=[0,1])
print "Number of nodes <= 5 ft elevation: " + str(len(nodes))
print "   " + str(nodes)

if nx.is_connected(G):
    # Compute eccentricity (maximum distance from node to all other nodes in G)
    ecc = nx.eccentricity(G)
    wntr.network.draw_graph(wn, node_attribute=ecc, title='Eccentricity', 
                          node_size=40, node_range=[15, 30])

    # Compute diameter (maximum eccentricity. The eccentricity of a node v is 
    # the maximum)
    # distance from v to all other nodes in G.
    print "Diameter: " + str(nx.diameter(G))

    # Compute shortest path length and average shortest path length
    #nx.shortest_path_length(G)
    ASPL = nx.average_shortest_path_length(G)
    print "Average shortest path length: " + str(ASPL)
else:
    print "Diameter: NaN, network is not connected"
    print "Average shortest path length: NaN, network is not connected"

# Compute cluster coefficient (function of the number of triangles through 
# a node)
clust_coefficients = nx.clustering(nx.Graph(G))
wntr.network.draw_graph(wn, node_attribute=clust_coefficients,
                      title='Clustering Coefficient', node_size=40)

# Compute meshedness coefficient
meshedness = float(G.number_of_edges() - G.number_of_nodes() + 1)/(2*G.number_of_nodes()-5)
print "Meshedness coefficient: " + str(meshedness)

# Compute betweenness centrality (number of times a node acts as a bridge 
# along the shortest path between two other nodes.)
bet_cen = nx.betweenness_centrality(G)
bet_cen_trim = dict([(k,v) for k,v in bet_cen.iteritems() if v > 0.1])
wntr.network.draw_graph(wn, node_attribute=bet_cen_trim, 
                      title='Betweenness Centrality', node_size=40, 
                      node_range=[0.1, 0.4])
central_pt_dom = sum(max(bet_cen.values()) - np.array(bet_cen.values()))/G.number_of_nodes()
print "Central point dominance: " + str(central_pt_dom)


# Compute articulation point (any node whose removal (along with all its 
# incident edges) increases the number of connected components of a graph)
Nap = list(nx.articulation_points(G))
Nap = list(set(Nap)) # get the unique nodes in Nap
Nap_density = float(len(Nap))/G.number_of_nodes()
print "Density of articulation points: " + str(Nap_density)
wntr.network.draw_graph(wn, node_attribute=Nap, title='Articulation Point', 
                      node_size=40, node_range=[0,1])

# Compute bridges (a link is considered a bridge if the removal of that link 
# increases the number of connected components in the network.)
bridges = wntr.network.bridges(G)
wntr.network.draw_graph(wn, link_attribute=bridges, title='Bridges', 
                      link_width=2, link_range=[0,1])
Nbr_density = float(len(bridges))/G.number_of_edges()
print "Density of bridges: " + str(Nbr_density)

# Compute spectal gap (difference in the first and second eigenvalue of 
# the adj matrix)
eig = nx.adjacency_spectrum(G)
spectral_gap = eig[0] - eig[1]
print "Spectal gap: " + str(spectral_gap.real)

# Compute algebraic connectivity (second smallest eigenvalue of the normalized
# Laplacian matrix of a network.)
eig = nx.laplacian_spectrum(G)
alg_con = eig[-2]
print "Algebraic connectivity: " + str(alg_con)

# Critical ratio of defragmentation
tmp = np.mean(pow(np.array(node_degree.values()),2))
fc = 1-(1/((tmp/np.mean(node_degree.values()))-1))
print "Critical ratio of defragmentation: " + str(fc)

# Compute closeness centrality (inverse of the sum of shortest path from one
# node to all other nodes)
clo_cen = nx.closeness_centrality(G)
wntr.network.draw_graph(wn, node_attribute=clo_cen,
                      title='Closeness Centrality', node_size=40)
