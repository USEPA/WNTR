import epanetlib.pyepanet as pyepanet
import networkx as nx
from epanetlib.units import convert

def epanet_to_MultiDiGraph(enData, convert_units=True, edge_attribute=None):
    r"""Convert ENepanet instance to networkx MultiDiGraph
    
    Parameters
    ----------
    enData: ENepanet instance
    
    edge_attribute: dict (optional)
        Edge_attribute shoud be in the format
        {(nodeid1, nodeid2, linkid): x} where nodeid1 is a string, 
        nodeid2 is a string, linkid is a string.  x can be a float or a list, 
        if x is a list, then x[time] is used to populate the digraph.
        nodeid1 is the start node and nodeid2 is the end node.
        If x is positive, the link will be set from nodeid1 to nodeid2.  
        If x is negative, the link will be set from nodeid2 to nodeid1.
        In both cases, the link 'weight' is assigned to abs(x)
     
    Returns
    -------
    MG: networkx digraph
    
    Examples
    --------
    >>> enData = en.pyepanet.ENepanet()
    >>> enData.inpfile = 'Net1.inp'
    >>> enData.ENopen(enData.inpfile,'tmp.rpt')
    >>> G0 = en.network.epanet_to_MultiDiGraph(enData)
    >>> attr = {('10', '11', '10'): -18,
                          ('11', '12', '11'): 14,
                          ('11', '21', '111'): 10}
    >>> G1 = en.network.epanet_to_MultiDiGraph(enData, edge_attribute=attr)
    """
                            
    G=nx.MultiDiGraph(name=enData.inpfile, 
                      flowunits=enData.ENgetflowunits(), 
                      time=[],
                      timestep=enData.ENgettimeparam(pyepanet.EN_REPORTSTEP))
    
    nNodes = enData.ENgetcount(pyepanet.EN_NODECOUNT) 
    for i in range(nNodes):
        nodeid = enData.ENgetnodeid(i+1)
        nodetype = enData.ENgetnodetype(i+1)
        elevation = enData.ENgetnodevalue(i+1, pyepanet.EN_ELEVATION)
        
        if convert_units:
            elevation = convert('Elevation', G.graph['flowunits'], elevation) # m
        
        # Average volume of water consumed per day
        #VC = average_volume_water_consumed_per_day(enData,i)
        
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
        
        if convert_units:
            length = convert('Length', G.graph['flowunits'], length) # m
            diameter = convert('Pipe Diameter', G.graph['flowunits'], diameter) # m
        
        if edge_attribute == None:
            G.add_edge(node1, node2, key=linkid, linktype=linktype, 
                       length=length, diameter=diameter)
        else:
            try:
                data = edge_attribute[(node1, node2, linkid)]
            except:
                data = 0
                
            if data > 0:
                G.add_edge(node1, node2, key=linkid, linktype=linktype, 
                           length=length, diameter=diameter, weight=abs(data))
            elif data < 0:
                G.add_edge(node2, node1, key=linkid, linktype=linktype, 
                           length=length, diameter=diameter, weight=abs(data))

    if enData.inpfile is not '':
        pos = pyepanet.future.ENgetcoordinates(enData.inpfile)
        nx.set_node_attributes(G, 'pos', pos)
    
    return G
"""
def average_volume_water_consumed_per_day(enData,i):
    pattern = enData.ENgetnodevalue(i+1, pyepanet.EN_PATTERN)
    patlen = enData.ENgetpatternlen(pattern)
    basedemand = enData.ENgetnodevalue(i+1, pyepanet.EN_BASEDEMAND)
    hyd_timestep = enData.ENgettimeparam(pyepanet.EN_PATTERNSTEP)
    start_time = enData.ENgettimeparam(pyepanet.EN_PATTERNSTART)
    for t in range(patlen):
        val = enData.ENgetpatternvalue(pattern,t)
"""