import wntr
import networkx as nx

inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

G = wn.get_graph_deep_copy()

node_name = '123'
print G.node[node_name]
print G.edge[node_name]

node_degree = G.degree()
bet_cen = nx.betweenness_centrality(G)
wntr.network.draw_graph(wn, node_attribute=bet_cen, node_size=30, 
                        title='Betweenness Centrality')
