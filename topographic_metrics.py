import epanetlib as en
import networkx as nx
import matplotlib.pyplot as plt

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

# Diameter = maximum eccentricity. The eccentricity of a node v is the maximum 
# distance from v to all other nodes in MG.
print "Diameter: " + str(nx.diameter(G))
        
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
    
# Node degree = number of links per node
node_degree = G.degree() 
en.network.draw_graph(G, node_attribute=node_degree, 
                      title='Node Degree', node_size=40)
    
# Betweenness centrality = number of times a node acts as a bridge along the 
# shortest path between two other nodes.
bet_cen = nx.betweenness_centrality(G)
en.network.draw_graph(G, node_attribute=bet_cen, 
                      title='Betweenness Centrality', node_size=40)

# Closeness centrality = inverse of the sum of shortest path from one node to 
# all other nodes
clo_cen = nx.closeness_centrality(G)
en.network.draw_graph(G, node_attribute=clo_cen, 
                      title='Closeness Centrality', node_size=40)

# Cluster coefficient = function of the number of triangles through a node
clust_coefficients = nx.clustering(nx.Graph(G))
en.network.draw_graph(G, node_attribute=clust_coefficients, 
                      title='Clustering Coefficient', node_size=40)
    