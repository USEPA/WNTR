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

# Example plots
en.network.draw_graph(G)
en.network.draw_graph(G, node_attribute='elevation', edge_attribute='length', 
                      title='Multi-graph, inp layout', node_size=40, edge_width=2)

degree = G.degree()


# General topographic information = type, number of nodes, number of edges, average degree
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
                      title='Node Degree', node_size=40, node_range=[1,5])
terminal_nodes = [k for k,v in node_degree.iteritems() if v == 1]
attr = dict(zip(terminal_nodes,[1]*len(terminal_nodes)))
en.network.draw_graph(G, node_attribute=attr, 
                      title='Terminal nodes', node_size=40, node_range=[0,1])
                      
if nx.is_connected(G):
    # Eccentricity = maximum distance from node to all other nodes in G
    ecc = nx.eccentricity(G)
    en.network.draw_graph(G, node_attribute=ecc, 
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
en.network.draw_graph(G, node_attribute=clust_coefficients, 
                      title='Clustering Coefficient', node_size=40)
                      
# Meshedness coefficient
meshedness = float(G.number_of_edges() - G.number_of_nodes() + 1)/(2*G.number_of_nodes()-5)
print "Meshedness coefficient: " + str(meshedness)        
     
# Betweenness centrality = number of times a node acts as a bridge along the 
# shortest path between two other nodes.
bet_cen = nx.betweenness_centrality(G)
bet_cen2 = dict([(k,v) for k,v in bet_cen.iteritems() if v > 0.1])
en.network.draw_graph(G, node_attribute=bet_cen2, 
                      title='Betweenness Centrality', node_size=40, node_range=[0.1, 0.4])
central_pt_dom = sum(max(bet_cen.values()) - np.array(bet_cen.values()))/G.number_of_nodes()
print "Central point dominance: " + str(central_pt_dom)


# Articulation point = any node whose removal (along with all its incident 
# edges) increases the number of connected components of a graph
Nap = list(nx.articulation_points(G))
Nap = list(set(Nap)) # get the unique nodes in Nap
Nap_density = float(len(Nap))/G.number_of_nodes()
print "Density of articulation points: " + str(Nap_density)
art_points = dict(zip(Nap,[1]*len(Nap)))
en.network.draw_graph(G, node_attribute=art_points, 
                      title='Articulation Point', node_size=40, node_range=[0,1])
    
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
                      







