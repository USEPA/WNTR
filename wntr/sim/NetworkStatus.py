from wntr import *
import pandas as pd
import math
import numpy as np
import networkx


class NetworkStatus(object):
    """
    The purpose of the NetworkStatus object is to track the status of
    a network throughout the simulation. If the simulator is passed a
    WaterNetworkModel object and a NetworkStatus object, it should be
    able to solve the set of hydraulic equations for the given
    timestep.

    """


    def __init__(self, wn):

        self._wn = wn

        #The time of the simulation in seconds
        self.time_sec = 0,0 

        # links closed by time controls and conditional controls
        self.links_closed_by_controls = set([]) 

        # links closed for tanks with too low of a level
        self.links_closed_by_tank_controls = set([]) 

        # Closed check valves
        self.closed_check_valves = set([]) 

        # set of all closed links
        self.links_closed = set([]) 

        # pump speed settings
        # format: {pump_name: speed_setting_value}
        self.pump_speeds = {} 

        # valve settings
        # format: {valve_name: valve_setting_value}
        self.valve_settings = {} 

        # demands for junction for current timestep
        # format: {junction_name: expected_demand}
        self.demands = {} 

        # Value of tank heads at self.time_sec
        # format: {tank_name: head}
        self.tank_heads = {}

        # Reservoir head at self.time_sec
        # format: {reservoir_name: head}
        self.reservoir_heads = {}

        # Set of active leaks
        self.active_leaks = set([])


    def update_network_status(self, results):
        """
        Method to update the NetworkStatus object based on the results
        of the previous timestep.
        
        Parameters
        ----------
        results: TBD
           Add description here

        """



    def save_network_status(self, file_name='tmp_network_status.pickle'):
        """
        Method to save a NetworkStatus object using pickle.

        Parameters
        ----------
        file_name: string
           Name of the file to save the NetworkStatus object to.

        """

    def load_network_status(self, file_name = 'tmp_network_status.pickle'):
        """
        Method to load a NetworkStatus object using pickle.

        Parameters
        ----------
        file_name: string
           Name of the file to save the NetworkStatus object to.

        """
