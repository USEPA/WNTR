import epanetlib as en
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

plt.close('all')

# Create enData
enData = en.pyepanet.ENepanet()
enData.inpfile = 'networks/Net3.inp'
enData.ENopen(enData.inpfile,'tmp.rpt')

# Create MultiDiGraph and convert it to a MultiGraph
G = en.network.epanet_to_MultiDiGraph(enData)
G = G.to_undirected()

# Plot
en.network.draw_graph(G)
en.network.draw_graph(G, node_attribute='elevation', edge_attribute='length', 
                      title='Multi-graph, inp layout', node_size=40, edge_width=2)

# Topographic metrics
# General information = type, number of nodes, number of edges, average degree
print nx.info(G) 

# Link density = 2m/n(n-1) where n is the number of nodes and m is the number 
# of edges in G. The density is 0 for a graph without edges and 1 for a dense 
# graph (a graph with the maximum number of edges). The density of multigraphs 
# can be higher than 1.  
print "Link density: " + str(nx.density(G))

# Self loop = a link that connects a node to itself
print "Number of self loops: " + str(G.number_of_selfloops())

# Node degree = number of links per node
node_degree = G.degree() 
en.network.draw_graph(G, node_attribute=node_degree, 
                      title='Node Degree', node_size=40)
ave_node_degree = np.mean(node_degree.values())
#print "Average node degree: " + str(ave_node_degree)
    
# Eccentricity = maximum distance from node to all other nodes in G
ecc = nx.eccentricity(G)
en.network.draw_graph(G, node_attribute=ecc, 
                      title='Eccentricity', node_size=40)
                      
# Diameter = maximum eccentricity. The eccentricity of a node v is the maximum 
# distance from v to all other nodes in MG.
print "Diameter: " + str(nx.diameter(G))
        
# Shortest path length and average shortest path length
#nx.shortest_path_length(G)
print "Average shortest path length: " + str(nx.average_shortest_path_length(G))

# Cluster coefficient = function of the number of triangles through a node
clust_coefficients = nx.clustering(nx.Graph(G))
en.network.draw_graph(G, node_attribute=clust_coefficients, 
                      title='Clustering Coefficient', node_size=40)
                      
# Meshedness coefficient
meshedness = float(G.number_of_edges() - G.number_of_nodes() + 1)/(2*G.number_of_nodes()-5)
print "Meshedness coefficient: " + str(meshedness)        
     
# Betweenness centrality = number of times a node acts as a bridge along the 
# shortest path between two other nodes.
bet_cen = nx.betweenness_centrality(G)
en.network.draw_graph(G, node_attribute=bet_cen, 
                      title='Betweenness Centrality', node_size=40)
central_pt_dom = sum(max(bet_cen.values()) - np.array(bet_cen.values()))/G.number_of_nodes()
print "Central point dominance: " + str(central_pt_dom)


# Articulation point = any node whose removal (along with all its incident 
# edges) increases the number of connected components of a graph
Nap = list(nx.articulation_points(G))
Nap_density = float(len(Nap))/G.number_of_nodes()
print "Density of articulation points: " + str(Nap_density)
NapFreq = []
for i in G.nodes():
    NapFreq.append(Nap.count(i))
art_points = dict(zip(G.nodes(), NapFreq))
en.network.draw_graph(G, node_attribute=art_points, 
                      title='Articulation Points', node_size=40)
    
# Bridges, Nbr is not correct
"""
tmp= dict([(k,v) for k, v in art_points.iteritems() if v > 0])
Nbr = nx.edges(G,tmp.keys())
Nbr_density = float(len(Nbr))/G.number_of_nodes()
print "Density of bridges: " + str(Nbr_density)
"""

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
fc = 1-(1/((tmp/ave_node_degree)-1))
print "Critical ratio of defragmentation: " + str(fc)


# Other...

# Closeness centrality = inverse of the sum of shortest path from one node to 
# all other nodes
clo_cen = nx.closeness_centrality(G)
en.network.draw_graph(G, node_attribute=clo_cen, 
                      title='Closeness Centrality', node_size=40)
                      







