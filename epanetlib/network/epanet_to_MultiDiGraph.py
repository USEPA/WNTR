import epanetlib.pyepanet as pyepanet
import networkx as nx
import numpy as np
from epanetlib.units import convert

def epanet_to_MultiDiGraph(enData, convert_units=True, edge_attribute=None):
    r"""Convert ENepanet instance to networkx MultiDiGraph
    
    Parameters
    ----------
    enData : ENepanet instance
        ENepanet instance defined using pyepanet.ENepanet()
        
    convert_units : bool (optional), default = True
        Convert epanet network to MKS units.  This includes converting 
        elevation, tank diameter, and pipe length.  Corrdinates are not converted.
        
    edge_attribute : dict (optional), default = none
        Edge_attribute must be in the format
        {(nodeid1, nodeid2, linkid): x} where nodeid1 is a string, 
        nodeid2 is a string, linkid is a string.  x can be a float or a list, 
        if x is a list, then x[time] is used to populate the multidigraph.
        nodeid1 is the start node and nodeid2 is the end node.
        If x is positive, the link will be set from nodeid1 to nodeid2.  
        If x is negative, the link will be set from nodeid2 to nodeid1.
        In both cases, the link 'weight' is assigned to abs(x)
     
    Returns
    -------
    MG : networkx multidigraph
    
    Examples
    --------
    >>> enData = en.pyepanet.ENepanet()
    >>> enData.inpfile = 'Net1.inp'
    >>> enData.ENopen(enData.inpfile,'tmp.rpt')
    >>> G = en.network.epanet_to_MultiDiGraph(enData)
    
    >>> enData = en.pyepanet.ENepanet()
    >>> enData.inpfile = 'Net1.inp'
    >>> enData.ENopen(enData.inpfile,'tmp.rpt')
    >>> attr = {('10', '11', '10'): -18,
                          ('11', '12', '11'): 14,
                          ('11', '21', '111'): 10}
    >>> G = en.network.epanet_to_MultiDiGraph(enData, edge_attribute=attr)
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
        
        if nodetype == pyepanet.EN_JUNCTION: 
            base_demand = enData.ENgetnodevalue(i+1, pyepanet.EN_BASEDEMAND)
        else:
            base_demand = np.nan
            
        if nodetype == pyepanet.EN_TANK: 
            tank_diameter = enData.ENgetnodevalue(i+1, pyepanet.EN_TANKDIAM)
            tank_minlevel = enData.ENgetnodevalue(i+1, pyepanet.EN_MINLEVEL)
            tank_maxlevel = enData.ENgetnodevalue(i+1, pyepanet.EN_MAXLEVEL)
        else:
            tank_diameter = np.nan
            tank_minlevel = np.nan
            tank_maxlevel = np.nan
            
        if convert_units:
            elevation = convert('Elevation', G.graph['flowunits'], elevation) # m
            base_demand = convert('Demand', G.graph['flowunits'], base_demand) # m
            tank_diameter = convert('Tank Diameter', G.graph['flowunits'], tank_diameter) # m
            tank_minlevel = convert('Elevation', G.graph['flowunits'], tank_minlevel) # m
            tank_maxlevel = convert('Elevation', G.graph['flowunits'], tank_maxlevel) # m
        
        if nodetype == pyepanet.EN_TANK:
            G.add_node(nodeid, nodetype=nodetype, elevation=elevation, 
                   tank_diameter=tank_diameter, tank_minlevel=tank_minlevel,
                   tank_maxlevel=tank_maxlevel, base_demand=base_demand)
        else: G.add_node(nodeid, nodetype=nodetype, elevation=elevation, base_demand=base_demand)
            
        
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