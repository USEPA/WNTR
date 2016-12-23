from wntr.sim.core import *
import pandas as pd
import numpy as np
from wntr.epanet.util import FlowUnits, MassUnits, HydParam, QualParam
import logging

logger = logging.getLogger(__name__)

try:
    import wntr.epanet.pyepanet
except ImportError as e:
    print('{}'.format(e))
    logger.critical('%s',e)
    raise ImportError('Error importing pyepanet while running epanet simulator. '
                      'Make sure pyepanet is installed and added to path.')

from wntr.epanet.pyepanet.epanet2 import EpanetException, ENgetwarning

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

    def run_sim(self, WQ=None, convert_units=True, inp_file_prefix='temp'):
        """
        Run water network simulation using EPANET.  
        The EpanetSimulator uses an INP file written from the water network model.
        
        Parameters
        ----------
        WQ : wntr.scenario.Waterquality object (optional)
            Water quality scenario object, default = None (hydraulic simulation only)

        convert_units : bool (optional)
            Convert results to SI units, default = True
            
        inp_file_prefix : string (optional)
            INP file prefix, default = 'tmp'
        """
        # Write a new inp file from the water network model
        #self._wn.write_inpfile(inp_file_prefix + '.inp')
        #self._wn.name = inp_file_prefix + '.inp'
        
        start_run_sim_time = time.time()
        logger.debug('Starting run')
        # Create enData
        enData = wntr.epanet.pyepanet.ENepanet()
        enData.inpfile = self._wn.name
        enData.ENopen(enData.inpfile, inp_file_prefix + '.rpt')
        flowunits = FlowUnits(enData.ENgetflowunits())
        if self._wn._inpfile is not None:
            mass_units = self._wn._inpfile.mass_units
        else:
            mass_units = MassUnits.mg

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
                    head = enData.ENgetnodevalue(nodeindex, wntr.epanet.pyepanet.EN_HEAD)
                    demand = enData.ENgetnodevalue(nodeindex, wntr.epanet.pyepanet.EN_DEMAND)
                    expected_demand = demand
                    pressure = enData.ENgetnodevalue(nodeindex, wntr.epanet.pyepanet.EN_PRESSURE)

                    if convert_units: # expected demand is already converted
                        head = HydParam.HydraulicHead.to_si(flowunits, head)
                        demand = HydParam.Demand.to_si(flowunits, demand)
                        expected_demand = HydParam.Demand.to_si(flowunits, expected_demand)
                        pressure = HydParam.Pressure.to_si(flowunits, pressure) # Pa

                    node_dictonary['demand'].append(demand)
                    node_dictonary['expected_demand'].append(expected_demand)
                    node_dictonary['head'].append(head)
                    node_dictonary['pressure'].append(pressure)
                    node_dictonary['type'].append(self._get_node_type(name))

                for name in link_names:
                    linkindex = enData.ENgetlinkindex(name)

                    flow = enData.ENgetlinkvalue(linkindex, wntr.epanet.pyepanet.EN_FLOW)
                    velocity = enData.ENgetlinkvalue(linkindex, wntr.epanet.pyepanet.EN_VELOCITY)

                    if convert_units:
                        flow = HydParam.Flow.to_si(flowunits, flow)
                        velocity = HydParam.Velocity.to_si(flowunits, flow)

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
                        enData.ENsetqualtype(wntr.epanet.pyepanet.EN_CHEM, 'Chemical', 'mg/min', '')
                        wq_sourceQual = QualParam.SourceMassInject.from_si(flowunits, WQ.source_quality, mass_units)
                        wq_sourceQual = WQ.source_quality*60*1e6 # kg/s to mg/min
                    else:
                        enData.ENsetqualtype(wntr.epanet.pyepanet.EN_CHEM, 'Chemical', 'mg/L', '')
                        wq_sourceQual = QualParam.Concentration.from_si(flowunits, WQ.source_quality, mass_units)
                    # Set source quality
                    for node in WQ.nodes:
                        nodeid = enData.ENgetnodeindex(node)
                        enData.ENsetnodevalue(nodeid, wntr.epanet.pyepanet.EN_SOURCEQUAL, wq_sourceQual)

                    # Set source type
                    if WQ.source_type == 'CONCEN':
                        wq_sourceType = wntr.epanet.pyepanet.EN_CONCEN
                    elif WQ.source_type == 'MASS':
                        wq_sourceType = wntr.epanet.pyepanet.EN_MASS
                    elif WQ.source_type == 'FLOWPACED':
                        wq_sourceType = wntr.epanet.pyepanet.EN_FLOWPACED
                    elif WQ.source_type == 'SETPOINT':
                        wq_sourceType = wntr.epanet.pyepanet.EN_SETPOINT
                    else:
                        logger.error('Invalid Source Type for CHEM scenario')
                    enData.ENsetnodevalue(nodeid, wntr.epanet.pyepanet.EN_SOURCETYPE, wq_sourceType)

                    # Set pattern
                    if WQ.end_time == -1:
                        WQ.end_time = enData.ENgettimeparam(wntr.epanet.pyepanet.EN_DURATION)
                    if WQ.start_time > WQ.end_time:
                        raise RuntimeError('Start time is greater than end time')
                    patternstep = enData.ENgettimeparam(wntr.epanet.pyepanet.EN_PATTERNSTEP)
                    duration = enData.ENgettimeparam(wntr.epanet.pyepanet.EN_DURATION)
                    patternlen = int(duration/patternstep)
                    patternstart = int(WQ.start_time/patternstep)
                    patternend = int(WQ.end_time/patternstep)
                    pattern = [0]*patternlen
                    pattern[patternstart:patternend] = [1]*(patternend-patternstart)
                    enData.ENaddpattern('wq')
                    patternid = enData.ENgetpatternindex('wq')
                    enData.ENsetpattern(patternid, pattern)
                    enData.ENsetnodevalue(nodeid, wntr.epanet.pyepanet.EN_SOURCEPAT, patternid)

                elif WQ.quality_type == 'AGE':
                    # Set quality type
                    enData.ENsetqualtype(wntr.epanet.pyepanet.EN_AGE,0,0,0)

                elif WQ.quality_type == 'TRACE':
                    # Set quality type
                    for node in WQ.nodes:
                        enData.ENsetqualtype(wntr.epanet.pyepanet.EN_TRACE,0,0,node.encode('ascii'))

                else:
                    logger.error('Invalid Quality Type')
            enData.ENopenQ()
            enData.ENinitQ(0)

            while True:
                t = enData.ENrunQ()
                if t in results.time:
                    for name in node_names:
                        nodeindex = enData.ENgetnodeindex(name)
                        quality = enData.ENgetnodevalue(nodeindex, wntr.epanet.pyepanet.EN_QUALITY)

                        if convert_units:
                            if WQ.quality_type == 'CHEM':
                                quality = QualParam.Concentration.to_si(flowunits, quality, mass_units)
                            elif WQ.quality_type == 'AGE':
                                quality = QualParam.WaterAge.to_si(flowunits, quality)

                        node_dictonary['quality'].append(quality)

                tstep = enData.ENnextQ()
                if tstep <= 0:
                    break

            enData.ENcloseQ()

        # close epanet
        enData.ENclose()

        # Create Panel
        for key, value in node_dictonary.items():
            node_dictonary[key] = np.array(value).reshape((ntimes, nnodes))
        results.node = pd.Panel(node_dictonary, major_axis=results.time, minor_axis=node_names)
        for key, value in link_dictonary.items():
            link_dictonary[key] = np.array(value).reshape((ntimes, nlinks))
        results.link = pd.Panel(link_dictonary, major_axis=results.time, minor_axis=link_names)

        return results
