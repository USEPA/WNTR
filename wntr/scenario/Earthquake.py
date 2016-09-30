import wntr
import numpy as np
import networkx as nx
import pandas as pd
from scipy.spatial import distance

class Earthquake(object):
    """
    Earthquake scenario class.
    """

    def __init__(self, epicenter, magnitude, depth):
        self.epicenter = epicenter
        """ Earthquake epicenter, (x,y) tuple in meters"""
        self.magnitude = magnitude
        """Earthquake magnitude, Richter scale"""
        self.depth = depth
        """Earthquake depth, m"""

    def distance_to_epicenter(self, wn, element_type=wntr.network.Node):
        """
        Distance to the epicenter
        
        Parameters
        -----------
        wn : WaterNetworkModel
        
        element_type: optional (default = wntr.network.Node)
        
        Returns
        ---------
        R : pd.Series
            Distance to epicenter (m)
        """
        G = wn.get_graph_deep_copy()
        pos = nx.get_node_attributes(G,'pos') 
        R = pd.Series()
        
        if element_type in [wntr.network.Link, wntr.network.Pipe, wntr.network.Pump, wntr.network.Valve]:
            # Compute pipe center position
            link_pos = {}
            for name, link in wn.links(element_type):
                start_point = pos[link.start_node()]
                end_point = pos[link.end_node()]
                link_pos[name] = ((end_point[0] + start_point[0])/2, 
                                  (end_point[1] + start_point[1])/2)
                          
            for name, link in wn.links(element_type):       
                R[name] = distance.euclidean(self.epicenter, link_pos[name]) # m
        
        elif element_type in [wntr.network.Node, wntr.network.Junction, wntr.network.Tank, wntr.network.Reservoir]:
            for name, node in wn.nodes(element_type):       
                R[name] = distance.euclidean(self.epicenter, pos[name]) # m
                
        return R
        
    def pga_attenuation_model(self,R,method=None):
        """
        Peak ground acceleration attenuation models
        
        Parameters
        -----------
        R : pd.Series
            Distance to epicenter (m)
        
        method : int (optional, default = None, average)
            1 = Kawashima et al. (1984)
            2 = Baag et al. (1998)
            3 = Lee and Cho (2002)
        
        Returns
        --------
        PGA : pd.Series
            Peak ground acceleration (g)
        """
        R = R/1000 # convert m to km
        D = self.depth/1000 # convert m to km
        delta = np.sqrt(np.power(R,2) + np.power(D,2))
         
        if method == 1:
            # Kawashima et al. (1984)
            PGA = 403.8*np.power(10, 0.265*self.magnitude)*np.power(R+30, -1.218)
        elif method == 2:
            # Baag et al. (1998)
            PGA = np.exp(0.4 + 1.2*self.magnitude - 0.76*np.log(delta) - 0.0094*delta)
        elif method == 3:
            # Lee and Cho (2002)
            PGA = np.power(10, -1.83 + 0.386*self.magnitude - np.log10(R) - 0.0015*R)
        else:
            # Average of the three methods
            PGA = ((403.8*np.power(10, 0.265*self.magnitude)*np.power(R+30, -1.218)) + \
                  np.exp(0.4 + 1.2*self.magnitude - 0.76*np.log(delta) - 0.0094*delta) + \
                  np.power(10, -1.83 + 0.386*self.magnitude - np.log10(R) - 0.0015*R))/3
        
        PGA = PGA/100 # convert cm/s2 to m/s2
        
        PGA = PGA/9.81 # convert m/s2 to g
        
        return PGA
    
    def pgv_attenuation_model(self, R, method=None):
        """
        Peak ground velocity attenuation models
        
        Parameters
        -----------
        R : pd.Series
            Distance to epicenter (m)
        
        method : int (optional, default = None, average)
            1 = Yu and Jin (2008) - Rock
            2 = Yu and Jin (2008) - Soil
            
        Returns
        --------
        PGV : pd.Series
            Peak ground velocity (m/s)
        """
        R = R/1000 # convert m to km
        
        if method == 1:
            # Yu and Jin (2008) - Rock
            PGV = np.power(10, -0.848 + 0.775*self.magnitude + -1.834*np.log10(R+17))
        elif method == 2:
            # Yu and Jin (2008) - Soil
            PGV = np.power(10, -0.285 + 0.711*self.magnitude + -1.851*np.log10(R+17))
        else:
            # Average
            PGV = (np.power(10, -0.848 + 0.775*self.magnitude + -1.834*np.log10(R+17)) + \
                  np.power(10, -0.285 + 0.711*self.magnitude + -1.851*np.log10(R+17)))/2
 
        PGV = PGV/100 # convert cm/s to m/s
        
        return PGV
        
    def correction_factor(self, pipe_characteristics, diameter_weight=None, material_weight=None, 
                          topography_weight=None, liquifaction_weight=None):
        """
        Correction factor
        Defaults based on Isoyama et al., 2000
        """
        
        # Make sure the values are strings
        pipe_characteristics = pd.DataFrame(data = pipe_characteristics.values, columns =pipe_characteristics.columns, index = pipe_characteristics.index.astype('str'))
        
        if diameter_weight is None:
            diameter_weight = {'Very small': 1.6, 'Small': 1.0, 'Medium': 0.8, 'Large': 0.5}
            
        if material_weight is None:
            material_weight = {'ACP': 1.2, 'PV': 1.0, 'PVC': 1.0, 'CIP': 1.0, 
                  'PE': 0.8, 'HI-3P': 0.8, 'SP': 0.3, 'DCIP': 0.3}
                  
        if topography_weight is None:
            topography_weight = {'Narrow valley': 3.2, 'Terrace': 1.5, 
                'Disturbed hill': 1.1, 'Alluvial': 1.0, 'Stiff alluvial': 0.4}
                   
        if liquifaction_weight is None:
            liquifaction_weight = {'Total': 2.4, 'Partial': 2.0, 'None': 1.0}  
           
        C0 = pipe_characteristics['Diameter'].map(diameter_weight)
        C1 = pipe_characteristics['Material'].map(material_weight)
        C2 = pipe_characteristics['Topography'].map(topography_weight)
        C3 = pipe_characteristics['Liquifaction'].map(liquifaction_weight) 
        C = C0*C1*C2*C3

        return C
        
    def repair_rate_model(self, PGV, C=1, method=1):
        """
        Calculate repair rate
        
        Parameters
        ------------
        PGV : pd.Series
            Peak ground velocity (m/s)

        K : pd.Series
            Correction factor
            
        method : int (default = 1)
            1 = Linear
            2 = Power
        
        Returns
        -------        
        Repair rate : pd.Series
            Number of repairs per m
        """
        PGV = (100*PGV)/2.54 # in/s
        
        if method == 1:
            # linear model
            RR = C*0.00187*PGV 
        elif method == 2:
            # Power model
            RR = C*0.00108*np.power(PGV, 1.173)
        else:
            print "invalid method"
            
        RR = RR*(3.28/1000) # convert 1/1000ft to 1/m

        return RR
        
    def DTGR(self,M,M_min,M_max,b):
        """
        Returns the the Doubly Truncated Gutenberg Richter cumulative probability 
        for the specified magnitude, magnitude range, and coefficient.
        """    
        B = b*np.log(10)
        P = 1 - (np.exp(-B*M) - np.exp(-B*M_max))/(np.exp(-B*M_min) - np.exp(-B*M_max))
        
        return P
        
    def DTGR_inv(self, P,M_min,M_max,b):
        """
        Returns the inverse of the Doubly Truncated Gutenberg Richter distribution 
        for the specified probability, magnitude range, and coefficient.
        """
        B = b*np.log(10)
        M = np.log(np.exp(-B*M_min) - P*(np.exp(-B*M_min)-np.exp(-B*M_max)))/(-B)
        
        return M
