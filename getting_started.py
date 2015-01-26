import epanetlib as en

# Create enData
enData = en.pyepanet.ENepanet()
enData.inpfile = 'networks/Net3.inp'
enData.ENopen(enData.inpfile,'tmp.rpt')

# Create MultiDiGraph
G = en.network.epanet_to_MultiDiGraph(enData)
en.network.draw_graph(G, title=enData.inpfile)


