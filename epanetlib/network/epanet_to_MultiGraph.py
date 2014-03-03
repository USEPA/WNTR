import epanetlib.pyepanet as pyepanet
import networkx as nx

def epanet_to_MultiGraph(enData):
    r"""Convert ENepanet instance to networkx MultiGraph
    
    Parameters
    ----------
    enData: ENepanet instance
    
    Returns
    -------
    MG: networkx multigraph
    
    Examples
    --------
    >>> enData = en.pyepanet.ENepanet()
    >>> enData.inpfile = 'Net1.inp'
    >>> enData.ENopen(enData.inpfile,'tmp.rpt')
    >>> G = en.network.epanet_to_MultiGraph(enData)
    """
    
    G=nx.MultiGraph(name=enData.inpfile, 
                    flowunits=enData.ENgetflowunits(),
                    time=[])
    
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT) 
    for i in range(nNodes):
        nodeid = enData.ENgetnodeid(i+1)
        nodetype = enData.ENgetnodetype(i+1)
        elevation = enData.ENgetnodevalue(i+1, pyepanet.EN_ELEVATION)
        G.add_node(nodeid, nodetype=nodetype, elevation=elevation)
        
    nLinks = enData.ENgetcount(pyepanet.EN_LINKCOUNT) 
    for i in range(nLinks):
        linkid = enData.ENgetlinkid(i+1)
        linktype = enData.ENgetlinktype(i+1)
        linknodes_index = enData.ENgetlinknodes(i+1)
        node1 = enData.ENgetnodeid(linknodes_index[0])
        node2 = enData.ENgetnodeid(linknodes_index[1])
        length = enData.ENgetlinkvalue(i+1, pyepanet.EN_LENGTH)
        diameter = enData.ENgetlinkvalue(i+1, pyepanet.EN_DIAMETER)
        G.add_edge(node1, node2, key=linkid, linktype=linktype, 
                   startnode=node1, length=length, diameter=diameter)
        
    if enData.inpfile is not '':
        pos = pyepanet.future.ENgetcoordinates(enData.inpfile)
        nx.set_node_attributes(G, 'pos', pos)
    
    return G