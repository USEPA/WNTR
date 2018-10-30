import numpy as np
import datetime

class SimulationResults(object):
    """
    Water network simulation results class.
    """

    def __init__(self):

        # Simulation time series
        self.timestamp = str(datetime.datetime.now())
        self.network_name = None
        self.link = None
        self.node = None
        """
        self.time = None
        self.meta = {'quality_mode':None,
                     'quality_chem':None,
                     'quality_units':None,
                     'quality_trace':None,
                     'node_names':None,
                     'node_type':None,
                     'node_elevation':None,
                     'link_names':None,
                     'link_type':None,
                     'link_subtype':None,
                     'link_length':None,
                     'link_diameter':None,
                     'report_times':None,
                     'stats_mode':None,
                     'stats_N':None}
        """

#    def _adjust_demand(self, Pstar):
#        """
#        Correction factor when using demand-driven simulation from 
#        Ostfeld A, Kogan D, Shamir U. (2002). Reliability simulation of water
#        distribution systems - single and multiquality, Urban Water, 4, 53-61
#
#
#        Parameters
#        ----------
#        Pstar : scalar
#            Pressure threshold
#
#        Returns
#        -------
#        Ad : results object
#
#        """
#        Rd = self.node.loc['demand', :,:]
#        P = self.node.loc['pressure',:,:]
#
#        Ad = Rd
#        Ad_temp = (Rd/np.sqrt(Pstar))*np.sqrt(P)
#
#        mask = P < Pstar
#        Ad[mask] = Ad_temp[mask]
#
#        return Ad
