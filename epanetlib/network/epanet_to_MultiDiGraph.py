import epanetlib.pyepanet as pyepanet
import networkx as nx

def epanet_to_MultiDiGraph(enData, edge_attribute, pos=None):
    r"""Convert ENepanet instance to networkx MultiDiGraph
    
    Parameters
    ----------
    enData: ENepanet instance
    
    edge_attribute: dict
        An edge_attribute dictonary has the format
        {(nodeid1, nodeid2, linkid): x} where nodeid1 is a string, 
        nodeid2 is a string, linkid is a string, and x is a float.  
        nodeid1 is the start node and nodeid2 is the end node.
        If x is positive, the link will be set from nodeid1 to nodeid2.  
        If x is negative, the link will be set from nodeid2 to nodeid1.
        In both cases, the link 'weight' is assigned to abs(x)
    
    pos: dict, optional
        A node_attribute dictionary for position has the format
        {nodeid: (x,y)} where nodeid is a string, x and y are floats
        
    Returns
    -------
    MG: networkx digraph
    
    Examples
    --------
    >>> enData = en.pyepanet.ENepanet()
    >>> enData.ENopen('Net1.inp','tmp.rpt')
    >>> pos = en.pyepanet.future.ENgetcoordinates('Net1.inp')
    >>> edge_attribute = {('10', '11', '10'): -18,
                          ('11', '12', '11'): 14,
                          ('11', '21', '111'): 10}
    >>> DG = en.network.epanet_to_MultiDiGraph(enData, edge_attribute, pos=pos)
    """
                            
    mDG=nx.MultiDiGraph() 
    
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT) 
    for i in range(nNodes):
        nodeid = enData.ENgetnodeid(i+1)
        elevation = enData.ENgetnodevalue(i+1, pyepanet.EN_ELEVATION)
        mDG.add_node(nodeid, elevation=elevation)
        
    nLinks = enData.ENgetcount(pyepanet.EN_LINKCOUNT) 
    for i in range(nLinks):
        linkid = enData.ENgetlinkid(i+1)
        linknodes_index = enData.ENgetlinknodes(i+1)
        node1 = enData.ENgetnodeid(linknodes_index[0])
        node2 = enData.ENgetnodeid(linknodes_index[1])
        length = enData.ENgetlinkvalue(i+1, pyepanet.EN_LENGTH)
        diameter = enData.ENgetlinkvalue(i+1, pyepanet.EN_DIAMETER)
        try:
            data = edge_attribute[(node1, node2, linkid)]
        except:
            data = 0
        if data > 0:
            mDG.add_edge(node1, node2, key=linkid, length=length, diameter=diameter, weight=abs(data))
        elif data < 0:
            mDG.add_edge(node2, node1, key=linkid, length=length, diameter=diameter, weight=abs(data))
        else:
            pass
    
    if pos is not None:
        nx.set_node_attributes(mDG, 'pos', pos)
    
    return mDG
