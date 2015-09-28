from wntr import *
import pandas as pd
import math
import numpy as np
import networkx

# probably a better way - google enumerations in python
class SimulationEventStatus(object):
    def __init__(self):
        self.NoChangesRequired = 0
        self.ChangesRequired = 1
        self.ChangesRequired_PleaseBackup = 2



class SimulationEvent(object):
    def __init__(self, wn):
        pass

    # override this method to return a value from the 
    # SimulationEventStatus enumeration
    def EventNeedsToMakeChanges(self, wn, current_timestep_soln):
        assert False && 'This should never get called'

    def MakeEventChanges(self, wn, current_timestep_sol):
        assert False && 'This should never get called'


class ControllerEvent(SimulationEvent):
    def __init__(self, control_str):
        # do parsing magic to produce 
        self._event_time = 1.65 # actually get this from control_str
        self._event_action = 'close_pipe'
        self._event_object = 'pipe65'

    def EventNeedsToMakeChanges(self, wn, current_time_soln):
        ct = current_timestep_soln.current_time
        if ct > self._event_time:
            if (ct - self._event_time) > 1e-1:
                return SimulationEventStatus.ChangesRequired_PleaseBackup
            else:
                return SimulationEventStatus.ChangesRequired
        return SimulationEventStatus.NoChangesRequired

    def MakeEventChanges(self, wn, current_timestep_sol):
        # do the magic to close the pipe
        # generate a log string
        self._fired = True

class ManageTimedLeakEvent(SimulationEvent):
    def __init__(self, leak_loc_str, time_leak_start, time_leak_end):
        self._leak_loc_str = leak_loc_str
        self._leak_time = leak_time

    # ...

class ManagePressureInducedLeakEvent(SimulationEvent):
    def __init__(self, leak_loc_str, pressure_bound):


# inside run sim, we would have something like...

# with the solution from the latest step in sol_t,
need_to_backup = False
need_to_make_changes = False
for event in eventList:
    status = event.EventNeedsToMakeChanges() 
    if status == SimulationEventStatus.RequiresChanges:
        # so some stuff here
        need_to_make_changes  = True
    elif status == SimulationEventStatus.RequiresChanges_PleaseBackup:
        need_to_backup = True
        need_to_make_changes = True

# more to do, but you get the idea...




# in a different method - maybe __main__ for your particular script
# you might have...
eventList = []
eventList.append(ManagePressureInducedLeakEvent('pipe97', 14.7*4.0))
for str in EpanetControlStrings:
    eventList.append(ControlEvent(str)

wnm.AddEventList(eventList)
sim = PyomoSimulator(wnm)
sim.run_sim()


sim = PyomoSimulator(wnm)
sim.run_sim(eventList)









wnm.AddEvents(eventList)





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
