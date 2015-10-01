import wntr

import math
import numpy as np
import matplotlib.pylab as plt
import pickle 
import networkx as nx
from scipy.spatial import distance

def _pipe_center_position(wn, coordinate_scale = 1, correct_length = False):
    """
    Define positions of pipes
    """
    G = wn._graph
    pos = nx.get_node_attributes(G,'pos') ##
    
    link_pos = {}
    for name, link in wn.links():
        start_point = pos[link.start_node()]
        end_point = pos[link.end_node()]
        link_pos[name] = ((end_point[0] + start_point[0])/2, 
                          (end_point[1] + start_point[1])/2)
        
        if correct_length == True:                  
            pipe_length = distance.euclidean(start_point, end_point)
            link.length = pipe_length*coordinate_scale
    
    return link_pos
        

class Earthquake(object):
    """
    Earthquake scenario class.
    """

    def __init__(self, epicenter, magnitude, depth, correction_factor = [1,1,1,1]):
        self.epicenter = epicenter
        self.magnitude = magnitude
        self.depth = depth
        self.correction_factor = correction_factor
        
        self.pga = {}
        self.correction_factor = {}
        self.repair_rate = {}
        self.probability_of_break = {}
        self.probability_of_leak = {}
        self.pipe_status = {}  
        self.pipes_to_leak = []

    
    def pga_attenuation_model(self,R,method):
        """
        Peak ground acceleration attenuation models
        
        PGA = 0.001 g (~0.01 m/s2): perceptible by people
        PGA = 0.02  g (~0.2  m/s2): people lose their balance
        PGA = 0.50  g (~5 m/s2): very high; well-designed buildings can survive if the duration is short
        https://en.wikipedia.org/wiki/Peak_ground_acceleration
        
        Shallow earthquakes are between 0 and 70 km deep, 
        intermediate earthquakes, 70 - 300 km deep, 
        and deep earthquakes, 300 - 700 km deep
        http://earthquake.usgs.gov/learn/topics/seismology/determining_depth.php
        """
        # PGA = peak ground acceleration (m/s2)
        # M = earthquake magnitude,
        # R = epicenter distance (m)
        # delta = distance (m) from focus assuming a focal depth of 10 km
        
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
        elif method == 4:
            # Average of the three methods
            PGA = ((403.8*np.power(10, 0.265*self.magnitude)*np.power(R+30, -1.218)) + \
                  np.exp(0.4 + 1.2*self.magnitude - 0.76*np.log(delta) - 0.0094*delta) + \
                  np.power(10, -1.83 + 0.386*self.magnitude - np.log10(R) - 0.0015*R))/3
        
        PGA = PGA/100 # convert cm/s2 to m/s2
        
        return PGA
    
    def correction_factor_lookup_table(self, link, material='SP', topography='Stiff alluvial', 
                      liquifaction='None'):
        """
        Isoyama et al., 2000 correction factor lookup table
        
        DCIP (ductile cast-iron pipe)
        CIP (cast-iron pipe)
        VP. PVC (polyvinyl chloride pipe)
        SP (steel pipe with welded joints)
        SGP (steel pipe with screwed joints)
        ACP (asbestos cement pipe).

        """
        
        C = [1,1,1,1]
        
        C2 = {'ACP': 1.2, 'VP': 1.0, 'PVC': 1.0, 'CIP': 1.0, 'PE': 0.8, 
              'HI-3P': 0.8, 'SP': 0.3, 'DCIP': 0.3}
        C3 = {'Narrow valley': 3.2, 'Terrace': 1.5, 'Disturbed hill': 1.1, 
              'Alluvial': 1.0, 'Stiff alluvial': 0.4}
        C4 = {'Total': 2.4, 'Partial': 2.0, 'None': 1.0}
        
        if link.diameter < 0.1: #  < 3.9 inches
            C[0] = 1.6
        elif link.diameter < 0.2: # < 7.8 inches
            C[0] = 1.0
        elif link.diameter < 0.5: # < 19.6 inches
            C[0] = 0.8
        else:
            C[0] = 0.5
        
        try:
            C[1] = C2[material]
        except:
            print material  + "not in lookup table"
        
        try:
            C[2] = C3[topography]
        except:
            print topography  + "not in lookup table"
        try:
            C[3] = C4[liquifaction]
        except:
            print liquifaction  + "not in lookup table"
            
        return C
        
    def repair_rate_model(self, PGA, C=[1,1,1,1]):
        """
        Repair rate (#/m)
        PGA (m/s2)
        """
        
        PGA = PGA*100 # convert m/s2 to cm/s2
        
        #RR = C[0]*C[1]*C[2]*C[3]*0.00187*PGA # 1/ft
        #RR = RR/1000 # convert 1/km to 1/m
        
        PGV = PGA*10 # cm/s
        PGV = PGV/2.54 # in/s
        RR = C[0]*C[1]*C[2]*C[3]*0.00187*PGV # 1/1000ft
        RR = RR*(3.28/1000) # convert 1/1000ft to 1/m
        
        #RR = 1.698*np.power(10, -16)*np.power(PGA, 6.06) # 1/km
        #RR = RR/1000 # convert 1/km to 1/m
        
        return RR
    
    def probability_model(self, RR,L):
        """
        Probability of a pipe break and leak
        RR (# per m)
        L (m)
        """
        Pbr = 1-np.exp(-RR*L)
        Pl = Pbr*5
        
        Psum = Pbr + Pl
        if Psum > 1:
            Pl = Pl/Psum
            Pbr = Pbr/Psum
        
        return (Pbr,Pl)
    
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

    def generate(self, wn, coordinate_scale = 1, correct_length = False):
        """
        Compute distance, PGA, repair rate, probabiltiy of break and leak,
        and pipe status
        """        
        link_pos = _pipe_center_position(wn, coordinate_scale, correct_length)
        
        dist_to_epicenter = {}

        for name, link in wn.links(wntr.network.Pipe):

            dist_to_epicenter[name] = distance.euclidean(self.epicenter, link_pos[name])*coordinate_scale # m
                
            self.pga[name] = self.pga_attenuation_model(dist_to_epicenter[name],4) # m/s2
            
            #pipe_materials = ['PVC', 'SP']
            #material = np.random.choice(pipe_materials, p=[0.7, 0.3])
            
            self.correction_factor[name] = self.correction_factor_lookup_table(link)
            
            self.repair_rate[name] = self.repair_rate_model(self.pga[name], self.correction_factor[name]) # per m
            
            (self.probability_of_break[name], self.probability_of_leak[name]) = \
                self.probability_model(self.repair_rate[name],link.length)
            
            p = np.random.uniform()  
            if p < self.probability_of_leak[name]:
                self.pipe_status[name] = 1 # leak
            elif p < self.probability_of_leak[name]+self.probability_of_break[name]:
                self.pipe_status[name] = 2 # break
            else:
                self.pipe_status[name] = 0 # normal
            
        self.pipes_to_leak = [pipe_name for pipe_name, status in self.pipe_status.iteritems() if status == 1]
            
        #plt.figure()
        #plt.hist(dist_to_epicenter.values())
