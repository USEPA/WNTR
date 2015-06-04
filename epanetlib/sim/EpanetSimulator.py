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
        
    def run_sim(self, convert_units=True, pandas_result=True):
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
        node_expected_demand = []
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
                    expected_demand = demand
                    pressure = enData.ENgetnodevalue(nodeindex, pyepanet.EN_PRESSURE)
                    
                    if convert_units: # expected demand is already converted
                        head = convert('Hydraulic Head', flowunits, head) # m
                        demand = convert('Demand', flowunits, demand) # m3/s
                        expected_demand = convert('Demand', flowunits, expected_demand) # m3/s
                        pressure = convert('Pressure', flowunits, pressure) # Pa
                    
                    node_name.append(name)
                    node_type.append(self._get_node_type(name))
                    node_times.append(timedelta)
                    node_head.append(head)
                    node_demand.append(demand)
                    node_expected_demand.append(expected_demand)
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
        
        if pandas_result:
            node_data_frame = pd.DataFrame({'time': node_times,
                                            'node': node_name,
                                            'demand': node_demand,
                                            'expected_demand': node_expected_demand,
                                            'head': node_head,
                                            'pressure': node_pressure,
                                            'type': node_type})

            node_pivot_table = pd.pivot_table(node_data_frame,
                                              values=['demand', 'expected_demand', 'head', 'pressure', 'type'],
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
        else:
            epanet_sim_results = {}
            epanet_sim_results['node_name'] = node_name
            epanet_sim_results['node_type'] = node_type
            epanet_sim_results['node_times'] = node_times
            epanet_sim_results['node_head'] = node_head
            epanet_sim_results['node_demand'] = node_demand
            epanet_sim_results['node_expected_demand'] = node_expected_demand
            epanet_sim_results['node_pressure'] = node_pressure
            epanet_sim_results['link_name'] = link_name
            epanet_sim_results['link_type'] = link_type
            epanet_sim_results['link_times'] = link_times
            epanet_sim_results['link_velocity'] = link_velocity
            epanet_sim_results['link_flowrate'] = link_flowrate

            hydraulic_time_step = float(copy.deepcopy(self._hydraulic_step_sec))
            node_dict = dict()
            node_types = set(self._pyomo_sim_results['node_type'])
            map_properties = dict()
            map_properties['node_demand'] = 'demand'
            map_properties['node_head'] = 'head'
            map_properties['node_pressure'] = 'pressure'
            map_properties['node_expected_demand'] = 'expected_demand'
            N = len(epanet_sim_results['node_name'])
            n_nodes = len(self._wn._nodes.keys())
            T = N/n_nodes
            for node_type in node_types:
                node_dict[node_type] = dict()
                for prop, prop_name in map_properties.iteritems():
                    node_dict[node_type][prop_name] = dict()
                    for i in xrange(n_nodes):
                        node_name = epanet_sim_results['node_name'][i]
                        n_type = self._get_node_type(node_name)
                        if n_type == node_type:
                            node_dict[node_type][prop_name][node_name] = dict()
                            for ts in xrange(T):
                                time_sec = hydraulic_time_step*ts
                                #print i+n_nodes*ts
                                node_dict[node_type][prop_name][node_name][time_sec] = epanet_sim_results[prop][i+n_nodes*ts]

            results.node = node_dict

            link_dict = dict()
            link_types = set(self._pyomo_sim_results['link_type'])
            map_properties = dict()
            map_properties['link_flowrate'] = 'flowrate'
            map_properties['link_velocity'] = 'velocity'
            N = len(epanet_sim_results['link_name'])
            n_links = len(self._wn._links.keys())
            T = N/n_links
            for link_type in link_types:
                link_dict[link_type] = dict()
                for prop, prop_name in map_properties.iteritems():
                    link_dict[link_type][prop_name] = dict()
                    for i in xrange(n_links):
                        link_name = epanet_sim_results['link_name'][i]
                        l_type = self._get_link_type(link_name)
                        if l_type == link_type:
                            link_dict[link_type][prop_name][link_name] = dict()
                            for ts in xrange(T):
                                time_sec = hydraulic_time_step*ts
                                link_dict[link_type][prop_name][link_name][time_sec] = epanet_sim_results[prop][i+n_links*ts]

            results.link = link_dict

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
