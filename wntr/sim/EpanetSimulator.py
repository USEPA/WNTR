try:
    from wntr import pyepanet
except ImportError:
    raise ImportError('Error importing pyepanet while running epanet simulator.'
                      'Make sure pyepanet is installed and added to path.')
from WaterNetworkSimulator import *
import pandas as pd
from wntr.utils import convert

class EpanetSimulator(WaterNetworkSimulator):
    """
    Epanet simulator inherited from Water Network Simulator.
    """

    def __init__(self, wn):
        """
        Epanet simulator class.

        Parameters
        ----------
        wn : Water Network Model
            A water network model.
        """
        WaterNetworkSimulator.__init__(self, wn)

        # Timing
        self.prep_time_before_main_loop = 0.0
        self.solve_step = {}

    def run_sim(self, WQ = None, convert_units=True, pandas_result=True):
        """
        Run water network simulation using epanet.

        """

        start_run_sim_time = time.time()
            
        # Create enData
        enData = pyepanet.ENepanet()
        enData.inpfile = self._wn.name
        enData.ENopen(enData.inpfile, 'tmp.rpt')
        flowunits = enData.ENgetflowunits()
        
        enData.ENopenH()
        enData.ENinitH(1)
        
        results = NetResults()
        results.network_name = self._wn.name
        results.simulator_options['type'] = 'EPANET'
        results.time = np.arange(0, self._sim_duration_sec+self._hydraulic_step_sec, self._hydraulic_step_sec)
        
        # Load simulator options
        results.simulator_options['start_time'] = self._sim_start_sec
        results.simulator_options['duration'] = self._sim_duration_sec
        results.simulator_options['pattern_start_time'] = self._pattern_start_sec
        results.simulator_options['hydraulic_time_step'] = self._hydraulic_step_sec
        results.simulator_options['pattern_time_step'] = self._pattern_step_sec
        results.simulator_options['error_code'] = 0
    
        # data for results object
        node_name = []
        node_type = []
        node_times = []
        node_head = []
        node_demand = []
        node_expected_demand = []
        node_pressure = []
        node_quality = []
        link_name = []
        link_type = []
        link_times = []
        link_velocity = []
        link_flowrate = []

        start_main_loop_time = time.time()
        self.prep_time_before_main_loop = start_main_loop_time - start_run_sim_time
        while True:
            start_solve_step = time.time()
            t = enData.ENrunH()
            end_solve_step = time.time()
            self.solve_step[t/self._wn.time_options['HYDRAULIC TIMESTEP']] = end_solve_step - start_solve_step
            if t in results.time:
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
                    node_times.append(t) 
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
                    link_times.append(t) 
                    link_flowrate.append(flow)
                    link_velocity.append(velocity)

            tstep = enData.ENnextH()
            if tstep <= 0:
                break
            # determines if it was successfull
            if enData.Warnflag:
                results.simulator_options['error_code'] = 1
            if enData.Errflag:
                results.simulator_options['error_code'] = 2
        
        enData.ENcloseH()
        if WQ:
            wq_type = WQ[0]
            if wq_type == 'CHEM': 
                wq_node = WQ[1]
                wq_sourceType = WQ[2]
                wq_sourceQual = WQ[3]
                wq_startTime = WQ[4]
                wq_endTime = WQ[5]
                if wq_sourceType == 'CONCEN':
                    wq_sourceType = pyepanet.EN_CONCEN
                elif wq_sourceType == 'MASS':
                    wq_sourceType = pyepanet.EN_MASS
                elif wq_sourceType == 'FLOWPACED':
                    wq_sourceType = pyepanet.EN_FLOWPACED
                elif wq_sourceType == 'SETPOINT':
                    wq_sourceType = pyepanet.EN_SETPOINT
                else:
                    print "Invalid Source Type for CHEM scenario"
                
                if wq_endTime == -1:
                    wq_endTime = enData.ENgettimeparam(pyepanet.EN_DURATION)
                if wq_startTime > wq_endTime:
                    raise RuntimeError('Start time is greater than end time')
                    
                # Set quality type
                enData.ENsetqualtype(pyepanet.EN_CHEM, 'Chemical', 'mg/L', '')
                
                # Set source quality
                wq_sourceQual = convert('Concentration', flowunits, wq_sourceQual, MKS = False) # kg/m3 to mg/L
                nodeid = enData.ENgetnodeindex(wq_node)
                enData.ENsetnodevalue(nodeid, pyepanet.EN_SOURCEQUAL, wq_sourceQual)
                
                # Set source type
                enData.ENsetnodevalue(nodeid, pyepanet.EN_SOURCETYPE, wq_sourceType)
                
                # Set pattern
                patternstep = enData.ENgettimeparam(pyepanet.EN_PATTERNSTEP)
                duration = enData.ENgettimeparam(pyepanet.EN_DURATION)
                patternlen = duration/patternstep
                patternstart = wq_startTime/patternstep
                patternend = wq_endTime/patternstep
                pattern = [0]*patternlen
                pattern[patternstart:patternend] = [1]*(patternend-patternstart)
                enData.ENaddpattern('wq')
                patternid = enData.ENgetpatternindex('wq')
                enData.ENsetpattern(patternid, pattern)  
                enData.ENsetnodevalue(nodeid, pyepanet.EN_SOURCEPAT, patternid)
                
            elif wq_type == 'AGE':
                # Set quality type
                enData.ENsetqualtype(pyepanet.EN_AGE,0,0,0)  
                
            elif wq_type == 'TRACE':
                # Set quality type
                wq_node = WQ[1]
                enData.ENsetqualtype(pyepanet.EN_TRACE,0,0,wq_node)   
                
            else:
                print "Invalid Quality Type"
            enData.ENopenQ()
            enData.ENinitQ(0)

            while True:
                t = enData.ENrunQ()
                if t in results.time:
                    for name, node in self._wn.nodes():
                        nodeindex = enData.ENgetnodeindex(name)
                        quality = enData.ENgetnodevalue(nodeindex, pyepanet.EN_QUALITY)
                    
                        if convert_units:
                            if wq_type == 'CHEM':
                                quality = convert('Concentration', flowunits, quality) # kg/m3
                            elif wq_type == 'AGE':
                                quality = convert('Water Age', flowunits, quality) # s
                        
                        node_quality.append(quality)
                    
                tstep = enData.ENnextQ()
                if tstep <= 0:
                    break
            # determines if it was successfull
            if enData.Warnflag:
                results.simulator_options['error_code'] = 1
            if enData.Errflag:
                results.simulator_options['error_code'] = 2
            enData.ENcloseQ()
        # close epanet 
        enData.ENclose()

        if pandas_result:
            #print len(set(node_times))
            #print len(set(node_name))
            if WQ:
                node_data_frame = pd.DataFrame({'time': node_times,
                                               'node': node_name,
                                               'demand': node_demand,
                                               'expected_demand': node_expected_demand,
                                               'head': node_head,
                                               'pressure': node_pressure,
                                               'quality': node_quality,
                                               'type': node_type})
                node_pivot_table = pd.pivot_table(node_data_frame,
                                              values=['demand', 'expected_demand', 'head', 'pressure', 'quality', 'type'],
                                              index=['node', 'time'],
                                              aggfunc= lambda x: x)
            else:
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
            epanet_sim_results['node_quality'] = node_quality
            epanet_sim_results['link_name'] = link_name
            epanet_sim_results['link_type'] = link_type
            epanet_sim_results['link_times'] = link_times
            epanet_sim_results['link_velocity'] = link_velocity
            epanet_sim_results['link_flowrate'] = link_flowrate


            node_dict = dict()
            node_types = set(epanet_sim_results['node_type'])
            map_properties = dict()
            map_properties['node_demand'] = 'demand'
            map_properties['node_head'] = 'head'
            map_properties['node_pressure'] = 'pressure'
            map_properties['node_quality'] = 'quality'
            map_properties['node_expected_demand'] = 'expected_demand'
            N = len(epanet_sim_results['node_name'])
            n_nodes = len(self._wn._nodes.keys())
            T = N/n_nodes
            #print T
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
                                time_sec = self._hydraulic_step_sec*ts
                                #print i+n_nodes*ts
                                node_dict[node_type][prop_name][node_name][time_sec] = epanet_sim_results[prop][i+n_nodes*ts]

            results.node = node_dict

            link_dict = dict()
            link_types = set(epanet_sim_results['link_type'])
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
                                time_sec = self._hydraulic_step_sec*ts
                                link_dict[link_type][prop_name][link_name][time_sec] = epanet_sim_results[prop][i+n_links*ts]

            results.link = link_dict

        return results

    def _load_general_results(self, results):
        """
        Load general simulation options into the results object.

        Parameters
        ----------
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
