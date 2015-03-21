try:
    from epanetlib import pyepanet
except ImportError:
    raise ImportError('Error importing pyepanet while running epanet simulator.'
                      'Make sure pyepanet is installed and added to path.')
from WaterNetworkSimulator import *
import pandas as pd
from epanetlib.units import convert

class EpanetSimulator(WaterNetworkSimulator):
    """
    Epanet simulator inherited from Water Network Simulator.
    """

    def __init__(self, wn):
        """
        Epanet simulator class.

        Parameters
        ---------
        wn : Water Network Model
            A water network model.
        """
        WaterNetworkSimulator.__init__(self, wn)
        
    def run_sim(self, convert_units=True):
        """
        Run water network simulation using epanet.

        """
        # Create enData
        enData = pyepanet.ENepanet()
        enData.inpfile = self._wn.name
        enData.ENopen(enData.inpfile, 'tmp.rpt')
        
        flowunits = enData.ENgetflowunits()
        
        enData.ENopenH()
        enData.ENinitH(0)
        
        results = NetResults()
        results.network_name = self._wn.name
        results.simulator_options['type'] = 'EPANET'
        results.time = pd.timedelta_range(start='0 minutes',
                                          end=str(self._sim_duration_sec) + ' seconds',
                                          freq=str(self._hydraulic_step_sec/60) + 'min')
    
        # data for results object
        node_name = []
        node_type = []
        node_times = []
        node_head = []
        node_demand = []
        node_pressure = []
        link_name = []
        link_type = []
        link_times = []
        link_velocity = []
        link_flowrate = []

        while True:
            t = enData.ENrunH()
            timedelta = pd.Timedelta(seconds = t)
            if timedelta in results.time:
                for name, node in self._wn.nodes():
                    nodeindex = enData.ENgetnodeindex(name)
                    head = enData.ENgetnodevalue(nodeindex, pyepanet.EN_HEAD)
                    demand = enData.ENgetnodevalue(nodeindex, pyepanet.EN_DEMAND)
                    pressure = enData.ENgetnodevalue(nodeindex, pyepanet.EN_PRESSURE)
                    
                    if convert_units:
                        head = convert('Hydraulic Head', flowunits, head) # m
                        demand = convert('Demand', flowunits, demand) # m3/s
                        pressure = convert('Pressure', flowunits, pressure) # Pa
                    
                    node_name.append(name)
                    node_type.append(self._get_node_type(name))
                    node_times.append(timedelta)
                    node_head.append(head)
                    node_demand.append(demand)
                    node_pressure.append(pressure)

                for name, link in self._wn.links():
                    linkindex = enData.ENgetlinkindex(name)
                    
                    flow = enData.ENgetlinkvalue(linkindex, pyepanet.EN_FLOW)
                    velocity = enData.ENgetlinkvalue(linkindex, pyepanet.EN_VELOCITY)
                    
                    if convert_units:
                        flow = convert('Flow', flowunits, flow) # m3/s
                        velocity = convert('Velocity', flowunits, velocity) # m/s
                    
                    link_name.append(name)
                    link_type.append(self._get_link_type(name))
                    link_times.append(timedelta)
                    link_flowrate.append(flow)
                    link_velocity.append(velocity)

            tstep = enData.ENnextH()
            if tstep <= 0:
                break
        
        node_data_frame = pd.DataFrame({'time': node_times,
                                        'node': node_name,
                                        'demand': node_demand,
                                        'head': node_head,
                                        'pressure': node_pressure,
                                        'type': node_type})

        node_pivot_table = pd.pivot_table(node_data_frame,
                                          values=['demand', 'head', 'pressure', 'type'],
                                          index=['node', 'time'],
                                          aggfunc= lambda x: x)
        results.node = node_pivot_table

        link_data_frame = pd.DataFrame({'time': link_times,
                                        'link': link_name,
                                        'flowrate': link_flowrate,
                                        'velocity': link_velocity,
                                        'type': link_type})

        link_pivot_table = pd.pivot_table(link_data_frame,
                                              values=['flowrate', 'velocity', 'type'],
                                              index=['link', 'time'],
                                              aggfunc= lambda x: x)
        results.link = link_pivot_table

        return results

    def _load_general_results(self, results):
        """
        Load general simulation options into the results object.

        Parameter
        ------
        results : NetworkResults object
        """
        # Load general results
        results.network_name = self._wn.name

        # Load simulator options
        results.simulator_options['type'] = 'EPANET'
        results.simulator_options['start_time'] = self._sim_start_sec
        results.simulator_options['duration'] = self._sim_duration_sec
        results.simulator_options['pattern_start_time'] = self._pattern_start_sec
        results.simulator_options['hydraulic_time_step'] = self._hydraulic_step_sec
        results.simulator_options['pattern_time_step'] = self._pattern_step_sec
