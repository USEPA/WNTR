import epanetlib as en
import numpy as np
import networkx as nx

# Create enData
enData = en.pyepanet.ENepanet()
enData.inpfile = 'networks/Net3.inp'
enData.ENopen(enData.inpfile,'tmp.rpt')

# Create MultiDiGraph and extract some information (like we're doing now)
G = en.network.epanet_to_MultiDiGraph(enData)
nzd = en.metrics.topography.query_node_attribute(G, 'base_demand', np.greater, 0)
diam = en.network.networkx_extensions.get_edge_attributes_MG(G, 'diameter')

# OR create a WDSGraph and extract some information
G0 = en.network.epanet_to_WDSGraph(enData)
nzd0 = G0.query_node_attribute('base_demand', np.greater, 0)
diam0 = G0.get_edge_attributes('diameter')

# Or create a WDSGraph with a Junction Class
G1 = en.network.WDSGraph()
junc = en.network.Junction()
junc.nodeid = '1'
junc.base_demand = 100
junc.elevation = 200
G1.add_node(junc.nodeid, {'attr': junc})

res = en.network.Reservoir()
res.nodeid = '2'
res.base_demand = 5
res.elevation = 3
G1.add_node(res.nodeid, {'attr': res})

tank = en.network.Tank()
tank.nodeid = '3'
tank.base_demand = 1000
tank.elevation = 2000
tank.diameter = 4
tank.minlevel = 2
tank.maxlevel = 6 
G1.add_node(tank.nodeid, {'attr': tank})

print G1.node[junc.nodeid]['attr'].base_demand
print type(junc)
attr = nx.get_node_attributes(G1,'attr')
for k,v in attr.items():
    if type(v) is en.network.Junction:
        print k,v

"""
the next line obviously doesn't work, but could you do something similar to 
pull out nodes of a single class?
"""
#junctions = G1.query_node_attribute('attr', istype, en.classes.Junction)
