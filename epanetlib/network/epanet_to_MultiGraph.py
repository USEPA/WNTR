import epanetlib.pyepanet as pyepanet
import networkx as nx

def epanet_to_MultiGraph(enData, pos=None):
    r"""Convert ENepanet instance to networkx MultiGraph
    
    Parameters
    ----------
    enData: ENepanet instance
    
    pos: dict, optional
        A node_attribute dictionary for position has the format
        {nodeid: (x,y)} where nodeid is a string, x and y are floats
        
    Returns
    -------
    MG: networkx multigraph
    
    Examples
    --------
    >>> enData = en.pyepanet.ENepanet()
    >>> enData.ENopen('Net1.inp','tmp.rpt')
    >>> MG = en.network.epanet_to_MultiGraph(enData)
    """
    
    MG=nx.MultiGraph() 
    
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT) 
    for i in range(nNodes):
        nodeid = enData.ENgetnodeid(i+1)
        elevation = enData.ENgetnodevalue(i+1, pyepanet.EN_ELEVATION)
        MG.add_node(nodeid, elevation=elevation)
        
    nLinks = enData.ENgetcount(pyepanet.EN_LINKCOUNT) 
    for i in range(nLinks):
        linkid = enData.ENgetlinkid(i+1)
        linknodes_index = enData.ENgetlinknodes(i+1)
        node1 = enData.ENgetnodeid(linknodes_index[0])
        node2 = enData.ENgetnodeid(linknodes_index[1])
        length = enData.ENgetlinkvalue(i+1, pyepanet.EN_LENGTH)
        diameter = enData.ENgetlinkvalue(i+1, pyepanet.EN_DIAMETER)
        MG.add_edge(node1, node2, key=linkid, length=length, diameter=diameter)

    if pos is not None:
        nx.set_node_attributes(MG, 'pos', pos)

    return MG