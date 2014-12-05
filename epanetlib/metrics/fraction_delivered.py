import epanetlib.pyepanet as pyepanet
import numpy as np

def fraction_delivered_volume(G, Pstar):
    """Fraction of delivered volume, at consumer (NZD) nodes
    
    Parameters
    ----------
    G : graph
        A networkx graph
    
    Pstar : scalar
        pressure threshold
        
    Returns
    -------
    fdv : dict
        fraction of delivered volume per node
    
    Notes
    -----
    Equation 2 in Ostfeld et al, Urban Water, 4, 2002
    """
    
    fdv = dict()
    T = len(G.graph['time'])
    
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            if sum(G.node[i]['demand'])  > 0: # demand > 0
                P = np.array(G.node[i]['head']) # m
                Rd = np.array(G.node[i]['demand']) # m3/s
                Ad = adjust_demand(Rd, P, Pstar)
                
                # Vj = volume of delivered demand
                # VT = volume of requested demand
                Vj = sum(Ad*T)
                VT = sum(Rd*T)
                
                if VT > 0:
                    fdv[i] = float(Vj)/VT
                else:
                    fdv[i] = 1
    
    return fdv

def fraction_delivered_demand(G, Pstar, Dstar):
    """Fraction of delivered demand, at consumer (NZD) nodes
    
    Parameters
    ----------
    G : graph
        A networkx graph
    
    Pstar : scalar
        pressure threshold
    
    Dstar : scalar
        demand factor
        
    Returns
    -------
    fdd : dict
        fraction of delivered demand per node
    
    Notes
    -----
    Equation 3 in Ostfeld et al, Urban Water, 4, 2002
    
    """
    
    fdd = dict()
    T = len(G.graph['time'])
    
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            if sum(G.node[i]['demand'])  > 0: # demand > 0
                P = np.array(G.node[i]['head']) # m
                Rd = np.array(G.node[i]['demand']) # m3/s
                Ad = adjust_demand(Rd, P, Pstar)
               
               # t = number of time steps when the delivered demand is greater than
               # Dstar * the requiested demand
                # the quality threshold
                t = sum(Ad > Rd*Dstar)
                
                fdd[i] = float(t)/T
            
    return fdd
    
def fraction_delivered_quality(G, Qstar):
    """Fraction of delivered quality, at consumer (NZD) nodes
    
    Parameters
    ----------
    G : graph
        A networkx graph
    
    Qstar : scalar
        water quality threshold
    
    Returns
    -------
    fdq : dict
        fraction of delivered quality per node
    
    Notes
    -----
    Equation 4 in Ostfeld et al, Urban Water, 4, 2002
    
    """
    
    fdq = dict()
    T = len(G.graph['time']) # total number of timesteps
    
    for i in G.nodes():
        if G.node[i]['nodetype']  == pyepanet.EN_JUNCTION:
            if sum(G.node[i]['demand'])  > 0: # demand > 0
                q = np.array(G.node[i]['quality']) # kg/m3
                
                # t = number of time steps when concentration is below 
                # the quality threshold
                t = sum(q < Qstar) 
                
                fdq[i] = float(t)/T
            
    return fdq
    
def adjust_demand(Rd, P, Pstar):
    """Adjust simulated demands based on node pressure
    
    Parameters
    ----------
    Rd : numpy array or scalar
        Requested demand
    
    P : numpy array or scalar
        Pressure

    Pstar : scalar
        Pressure threshold
    
    Returns
    -------
    Ad : numpy array or scalar
        Adjusted demand
    
    Notes
    -----
    Equation 1 in Ostfeld et al, Urban Water, 4, 2002
    
    """
    
    Ad_temp = (Rd/np.sqrt(Pstar))*np.sqrt(P)
    Ad = np.array(Rd,copy=True)
    Ad[P < Pstar] = Ad_temp[P < Pstar]
    
    return Ad