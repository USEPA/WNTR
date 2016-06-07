try:
    from wntr import pyepanet
except ImportError:
    raise ImportError('Error importing pyepanet while running epanet simulator.'
                      'Make sure pyepanet is installed and added to path.')
from WaterNetworkSimulator import *
import pandas as pd
from wntr.utils import convert
import logging

logger = logging.getLogger(__name__)
from wntr.pyepanet.epanet2 import EpanetException, ENgetwarning

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
        self.warning_list = None
    
    def run_sim(self, WQ=None, convert_units=True):
        """
        Run water network simulation using epanet.

        """

        start_run_sim_time = time.time()
        logger.debug('Starting run')
        # Create enData
        enData = pyepanet.ENepanet()
        enData.inpfile = self._wn.name
        enData.ENopen(enData.inpfile, 'tmp.rpt')
        flowunits = enData.ENgetflowunits()
        
        enData.ENopenH()
        enData.ENinitH(1)
        
        # Create results object and load general simulation options. 
        results = NetResults()
        results.time = np.arange(0, self._wn.options.duration+self._wn.options.hydraulic_timestep, self._wn.options.hydraulic_timestep)
        results.error_code = 0
        
        ntimes = len(results.time)
        nnodes = self._wn.num_nodes()
        nlinks = self._wn.num_links()
        node_names = [name for name, node in self._wn.nodes()]
        link_names = [name for name, link in self._wn.links()]
        
        node_dictonary = {'demand': [],
                          'expected_demand': [],
                          'head': [],
                          'pressure':[],
                          'type': []}
                          
        link_dictonary = {'flowrate': [],
                          'velocity': [],
                          'type': []}

        start_main_loop_time = time.time()
        self.prep_time_before_main_loop = start_main_loop_time - start_run_sim_time
        while True:
            start_solve_step = time.time()
            t = enData.ENrunH()
            end_solve_step = time.time()
            self.solve_step[t/self._wn.options.hydraulic_timestep] = end_solve_step - start_solve_step
            if t in results.time:
                for name in node_names:
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
                    
                    node_dictonary['demand'].append(demand)
                    node_dictonary['expected_demand'].append(expected_demand)
                    node_dictonary['head'].append(head)
                    node_dictonary['pressure'].append(pressure)
                    node_dictonary['type'].append(self._get_node_type(name))
                    
                for name in link_names:
                    linkindex = enData.ENgetlinkindex(name)
                    
                    flow = enData.ENgetlinkvalue(linkindex, pyepanet.EN_FLOW)
                    velocity = enData.ENgetlinkvalue(linkindex, pyepanet.EN_VELOCITY)
                    
                    if convert_units:
                        flow = convert('Flow', flowunits, flow) # m3/s
                        velocity = convert('Velocity', flowunits, velocity) # m/s
                        
                    link_dictonary['flowrate'].append(flow)
                    link_dictonary['velocity'].append(velocity)
                    link_dictonary['type'].append(self._get_link_type(name))

            tstep = enData.ENnextH()
            if tstep <= 0:
                break
            
            if enData.Warnflag:
                results.error_code = 1
            if enData.Errflag:
                results.error_code = 2
        enData.ENcloseH()
        self.warning_list = enData.errcodelist
        
        if WQ:
            if not isinstance(WQ,list):
                qlist = [WQ]
            else:
                qlist = WQ
            for WQ in qlist:
                node_dictonary['quality'] = []
    
                if WQ.quality_type == 'CHEM': 
                    
                    # Set quality type and convert source qual
                    if WQ.source_type == 'MASS':
                        enData.ENsetqualtype(pyepanet.EN_CHEM, 'Chemical', 'mg/min', '')
                        wq_sourceQual = WQ.source_quality*60*1e6 # kg/s to mg/min
                    else:
                        enData.ENsetqualtype(pyepanet.EN_CHEM, 'Chemical', 'mg/L', '')
                        wq_sourceQual = convert('Concentration', flowunits, WQ.source_quality, MKS=False) # kg/m3 to mg/L
                    
                    # Set source quality
                    for node in WQ.nodes:
                        nodeid = enData.ENgetnodeindex(node)
                        enData.ENsetnodevalue(nodeid, pyepanet.EN_SOURCEQUAL, wq_sourceQual)
                    
                    # Set source type
                    if WQ.source_type == 'CONCEN':
                        wq_sourceType = pyepanet.EN_CONCEN
                    elif WQ.source_type == 'MASS':
                        wq_sourceType = pyepanet.EN_MASS
                    elif WQ.source_type == 'FLOWPACED':
                        wq_sourceType = pyepanet.EN_FLOWPACED
                    elif WQ.source_type == 'SETPOINT':
                        wq_sourceType = pyepanet.EN_SETPOINT
                    else:
                        logger.error('Invalid Source Type for CHEM scenario')
                    enData.ENsetnodevalue(nodeid, pyepanet.EN_SOURCETYPE, wq_sourceType)
                    
                    # Set pattern
                    if WQ.end_time == -1:
                        WQ.end_time = enData.ENgettimeparam(pyepanet.EN_DURATION)
                    if WQ.start_time > WQ.end_time:
                        raise RuntimeError('Start time is greater than end time')
                    patternstep = enData.ENgettimeparam(pyepanet.EN_PATTERNSTEP)
                    duration = enData.ENgettimeparam(pyepanet.EN_DURATION)
                    patternlen = duration/patternstep
                    patternstart = WQ.start_time/patternstep
                    patternend = WQ.end_time/patternstep
                    pattern = [0]*patternlen
                    pattern[patternstart:patternend] = [1]*(patternend-patternstart)
                    enData.ENaddpattern('wq')
                    patternid = enData.ENgetpatternindex('wq')
                    enData.ENsetpattern(patternid, pattern)  
                    enData.ENsetnodevalue(nodeid, pyepanet.EN_SOURCEPAT, patternid)
                    
                elif WQ.quality_type == 'AGE':
                    # Set quality type
                    enData.ENsetqualtype(pyepanet.EN_AGE,0,0,0)  
                    
                elif WQ.quality_type == 'TRACE':
                    # Set quality type
                    for node in WQ.nodes:
                        enData.ENsetqualtype(pyepanet.EN_TRACE,0,0,node)   
                    
                else:
                    logger.error('Invalid Quality Type')
            enData.ENopenQ()
            enData.ENinitQ(0)
            
            while True:
                t = enData.ENrunQ()
                if t in results.time:
                    for name in node_names:
                        nodeindex = enData.ENgetnodeindex(name)
                        quality = enData.ENgetnodevalue(nodeindex, pyepanet.EN_QUALITY)
                    
                        if convert_units:
                            if WQ.quality_type == 'CHEM':
                                quality = convert('Concentration', flowunits, quality) # kg/m3
                            elif WQ.quality_type == 'AGE':
                                quality = convert('Water Age', flowunits, quality) # s
                        
                        node_dictonary['quality'].append(quality)
                        
                tstep = enData.ENnextQ()
                if tstep <= 0:
                    break

            enData.ENcloseQ()
            
        # close epanet 
        enData.ENclose()
        
        # Create Panel
        for key, value in node_dictonary.iteritems():
            node_dictonary[key] = np.array(value).reshape((ntimes, nnodes))
        results.node = pd.Panel(node_dictonary, major_axis=results.time, minor_axis=node_names)
        
        for key, value in link_dictonary.iteritems():
            link_dictonary[key] = np.array(value).reshape((ntimes, nlinks))
        results.link = pd.Panel(link_dictonary, major_axis=results.time, minor_axis=link_names)
        
        return results
