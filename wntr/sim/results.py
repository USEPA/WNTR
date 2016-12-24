import numpy as np
import datetime

class NetResults(object):
    def __init__(self):
        """
        A class to store water network simulation results.
        """

        # Simulation time series
        self.time = None
        self.generated_datetime = datetime.datetime
        self.network_name = None
        self.solver_statistics = {}
        self.link = None
        self.node = None

    def _adjust_demand(self, Pstar):
        """        
        Correction factor when using demand driven simualtion, see [1]
        
        Parameters
        ----------
        Pstar : scalar
            Pressure threshold
        
        Returns
        -------
        Ad : results object
        
        Examples
        --------
        >>> adjusted_demand = wntr.utils.adjust_demand(20, 30, 40)
        17.32
        >>> adjusted_demand = wntr.utils.adjust_demand(20, 42, 40)
        20
        
        References
        ----------
        Ostfeld A, Kogan D, Shamir U. (2002). Reliability simulation of water
        distribution systems - single and multiquality, Urban Water, 4, 53-61
        """        
        Rd = self.node.loc['demand', :,:]
        P = self.node.loc['pressure',:,:]
        
        Ad = Rd        
        Ad_temp = (Rd/np.sqrt(Pstar))*np.sqrt(P) 
            
        mask = P < Pstar
        Ad[mask] = Ad_temp[mask]
            
        return Ad
