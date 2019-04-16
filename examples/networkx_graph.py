from __future__ import print_function
import wntr
import networkx as nx

inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Get the WaterNetworkModel graph
G = wn.get_graph()

# Extract node and link properties
node_name = '123'
print(G.node[node_name])
print(G.adj[node_name])

# Compute betweenness centrality
node_degree = G.degree()
bet_cen = nx.betweenness_centrality(G)
wntr.graphics.plot_network(wn, node_attribute=bet_cen, node_size=30, 
                        title='Betweenness Centrality')

# Convert the digraph to an undirected graph
uG = G.to_undirected()

# Check to see if the undirected graph is connected
print(nx.is_connected(uG))

# Create a weighted graph based on length
length = wn.query_link_attribute('length')
G.weight_graph(link_attribute = length)
