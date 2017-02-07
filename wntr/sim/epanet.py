from wntr.sim.core import WaterNetworkSimulator
import pandas as pd
import numpy as np
import wntr.epanet.io
from wntr.epanet.util import FlowUnits, MassUnits, HydParam, QualParam, EN, to_si, from_si
import logging
import time
logger = logging.getLogger(__name__)
from wntr.sim.results import NetResults

try:
    import wntr.epanet.pyepanet
except ImportError as e:
    print('{}'.format(e))
    logger.critical('%s',e)
    raise ImportError('Error importing pyepanet while running epanet simulator. '
                      'Make sure pyepanet is installed and added to path.')

from wntr.epanet.pyepanet.epanet2 import EpanetException, ENgetwarning


class FastEpanetSim(WaterNetworkSimulator):
    """
    Fast EPANET simulator class.

    Use the EPANET DLL to run an INP file as-is, and read the results from the
    binary output file. Multiple water quality simulations are still possible
    using the WQ keyword in the run_sim function. Hydraulics will be stored and
    saved to a file. This file will not be deleted by default, nor will any
    binary files be deleted.

    The reason this is considered a "fast" simulator is due to the fact that there
    is no looping within Python. The "ENsolveH" and "ENsolveQ" toolkit
    functions are used instead.

    Parameters
    ----------
    wn : WaterNetworkModel
        Water network model
    reader : wntr.epanet.io.BinFile derived object
        Defaults to None, which will create a new wntr.epanet.io.BinFile object with
        the results_types specified as an init option. Otherwise, a fully
    result_types : dict
        Defaults to None, or all results. Otherwise, is a keyword dictionary to pass to
        the reader to specify what results should be saved.


    .. seealso::

        wntr.epanet.io.BinFile

    """
    def __init__(self, wn, reader=None, result_types=None):
        WaterNetworkSimulator.__init__(self, wn)
        self.reader = reader
        self.prep_time_before_main_loop = 0.0
        if self.reader is None:
            self.reader = BinFile(result_types=result_types)

    def run_sim(self, WQ=None, convert_units=True, file_prefix='temp'):
        EN2 = self._wn._en2data
        inpfile = file_prefix + '.inp'
        EN2.write(inpfile, self._wn, units=EN2.flow_units.name)
        enData = wntr.epanet.pyepanet.ENepanet()
        rptfile = file_prefix + '.rpt'
        outfile = file_prefix + '.bin'
        # hydfile = file_prefix + '.hyd'
        flowunits = FlowUnits(enData.ENgetflowunits())
        if self._wn._inpfile is not None:
            mass_units = self._wn._inpfile.mass_units
        else:
            mass_units = MassUnits.mg
        enData.ENopen(inpfile, rptfile, outfile)
        enData.ENsolveH()
        # enData.ENsavehydfile(hydfile)
        if WQ:
            if not isinstance(WQ,list):
                qlist = [WQ]
            else:
                qlist = WQ
            for WQ in qlist:
                if WQ.quality_type == 'CHEM':

                    # Set quality type and convert source qual
                    if WQ.source_type == 'MASS':
                        enData.ENsetqualtype(EN.CHEM, 'Chemical', 'mg/min', '')
                        wq_sourceQual = from_si(flowunits, WQ.source_quality,
                                                QualParam.SourceMassInject,
                                                mass_units=mass_units)
                        wq_sourceQual = WQ.source_quality*60*1e6 # kg/s to mg/min
                    else:
                        enData.ENsetqualtype(EN.CHEM, 'Chemical', 'mg/L', '')
                        wq_sourceQual = from_si(flowunits, WQ.source_quality,
                                                QualParam.Concentration,
                                                mass_units=mass_units)
                    # Set source quality
                    for node in WQ.nodes:
                        nodeid = enData.ENgetnodeindex(node)
                        enData.ENsetnodevalue(nodeid, EN.SOURCEQUAL, wq_sourceQual)

                    # Set source type
                    if WQ.source_type == 'CONCEN':
                        wq_sourceType = EN.CONCEN
                    elif WQ.source_type == 'MASS':
                        wq_sourceType = EN.MASS
                    elif WQ.source_type == 'FLOWPACED':
                        wq_sourceType = EN.FLOWPACED
                    elif WQ.source_type == 'SETPOINT':
                        wq_sourceType = EN.SETPOINT
                    else:
                        logger.error('Invalid Source Type for CHEM scenario')
                    enData.ENsetnodevalue(nodeid, EN.SOURCETYPE, wq_sourceType)

                    # Set pattern
                    if WQ.end_time == -1:
                        WQ.end_time = enData.ENgettimeparam(EN.DURATION)
                    if WQ.start_time > WQ.end_time:
                        raise RuntimeError('Start time is greater than end time')
                    patternstep = enData.ENgettimeparam(EN.PATTERNSTEP)
                    duration = enData.ENgettimeparam(EN.DURATION)
                    patternlen = int(duration/patternstep)
                    patternstart = int(WQ.start_time/patternstep)
                    patternend = int(WQ.end_time/patternstep)
                    pattern = [0]*patternlen
                    pattern[patternstart:patternend] = [1]*(patternend-patternstart)
                    enData.ENaddpattern('wq')
                    patternid = enData.ENgetpatternindex('wq')
                    enData.ENsetpattern(patternid, pattern)
                    enData.ENsetnodevalue(nodeid, EN.SOURCEPAT, patternid)

                elif WQ.quality_type == 'AGE':
                    # Set quality type
                    enData.ENsetqualtype(EN.AGE,0,0,0)

                elif WQ.quality_type == 'TRACE':
                    # Set quality type
                    for node in WQ.nodes:
                        enData.ENsetqualtype(EN.TRACE,0,0,node.encode('ascii'))
                else:
                    logger.error('Invalid Quality Type')
            enData.ENsolveQ()
        if enData.Errflag:
            enData.ENclose()
            return 1
        elif enData.Warnflag:
            enData.ENclose()
            return 2
        try:
            enData.ENreport()
        except:
            pass
        enData.ENclose()
        return self.reader.read(outfile)


class EpanetSimulator(WaterNetworkSimulator):
    """
    EPANET simulator class.
    The EPANET simulator uses the EPANET toolkit and dll.

    Parameters
    ----------
    wn : WaterNetworkModel object
        Water network model
    """

    def __init__(self, wn):

        WaterNetworkSimulator.__init__(self, wn)

        # Timing
        self.prep_time_before_main_loop = 0.0
        self.solve_step = {}
        self.warning_list = None

    def run_sim(self, WQ=None, convert_units=True, file_prefix='temp', binary_file=False):
        """
        Run an extended period simulation.
        The EpanetSimulator uses an INP file written from the water network model.

        Parameters
        ----------
        WQ : wntr.scenario.Waterquality object (optional)
            Water quality scenario, default = None (hydraulic simulation only)

        convert_units : bool (optional)
            Convert results to SI units, default = True

        file_prefix : string (optional)
            INP and RPT file prefix, default = 'tmp'
        """
        # Write a new inp file from the water network model
        #self._wn.write_inpfile(file_prefix + '.inp')
        #self._wn.name = file_prefix + '.inp'

        start_run_sim_time = time.time()
        logger.debug('Starting run')
        # Create enData
        enData = wntr.epanet.pyepanet.ENepanet()
        enData.inpfile = self._wn.name
        if not binary_file:
            enData.ENopen(enData.inpfile, file_prefix + '.rpt')
        else:
            enData.ENopen(enData.inpfile, file_prefix + '.rpt', file_prefix + '.bin')
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
                    head = enData.ENgetnodevalue(nodeindex, EN.HEAD)
                    demand = enData.ENgetnodevalue(nodeindex, EN.DEMAND)
                    expected_demand = demand
                    pressure = enData.ENgetnodevalue(nodeindex, EN.PRESSURE)

                    if convert_units: # expected demand is already converted
                        head = to_si(flowunits, head, HydParam.HydraulicHead)
                        demand = to_si(flowunits, demand, HydParam.Demand)
                        expected_demand = to_si(flowunits, expected_demand, HydParam.Demand)
                        pressure = to_si(flowunits, pressure, HydParam.Pressure) # Pa

                    node_dictonary['demand'].append(demand)
                    node_dictonary['expected_demand'].append(expected_demand)
                    node_dictonary['head'].append(head)
                    node_dictonary['pressure'].append(pressure)
                    node_dictonary['type'].append(self._get_node_type(name))

                for name in link_names:
                    linkindex = enData.ENgetlinkindex(name)

                    flow = enData.ENgetlinkvalue(linkindex, EN.FLOW)
                    velocity = enData.ENgetlinkvalue(linkindex, EN.VELOCITY)

                    if convert_units:
                        flow = to_si(flowunits, flow, HydParam.Flow)
                        velocity = to_si(flowunits, flow, HydParam.Velocity)

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
                        enData.ENsetqualtype(EN.CHEM, 'Chemical', 'mg/min', '')
                        wq_sourceQual = from_si(flowunits, WQ.source_quality,
                                                QualParam.SourceMassInject,
                                                mass_units=mass_units)
                        wq_sourceQual = WQ.source_quality*60*1e6 # kg/s to mg/min
                    else:
                        enData.ENsetqualtype(EN.CHEM, 'Chemical', 'mg/L', '')
                        wq_sourceQual = from_si(flowunits, WQ.source_quality,
                                                QualParam.Concentration,
                                                mass_units=mass_units)
                    # Set source quality
                    for node in WQ.nodes:
                        nodeid = enData.ENgetnodeindex(node)
                        enData.ENsetnodevalue(nodeid, EN.SOURCEQUAL, wq_sourceQual)

                    # Set source type
                    if WQ.source_type == 'CONCEN':
                        wq_sourceType = EN.CONCEN
                    elif WQ.source_type == 'MASS':
                        wq_sourceType = EN.MASS
                    elif WQ.source_type == 'FLOWPACED':
                        wq_sourceType = EN.FLOWPACED
                    elif WQ.source_type == 'SETPOINT':
                        wq_sourceType = EN.SETPOINT
                    else:
                        logger.error('Invalid Source Type for CHEM scenario')
                    enData.ENsetnodevalue(nodeid, EN.SOURCETYPE, wq_sourceType)

                    # Set pattern
                    if WQ.end_time == -1:
                        WQ.end_time = enData.ENgettimeparam(EN.DURATION)
                    if WQ.start_time > WQ.end_time:
                        raise RuntimeError('Start time is greater than end time')
                    patternstep = enData.ENgettimeparam(EN.PATTERNSTEP)
                    duration = enData.ENgettimeparam(EN.DURATION)
                    patternlen = int(duration/patternstep)
                    patternstart = int(WQ.start_time/patternstep)
                    patternend = int(WQ.end_time/patternstep)
                    pattern = [0]*patternlen
                    pattern[patternstart:patternend] = [1]*(patternend-patternstart)
                    enData.ENaddpattern('wq')
                    patternid = enData.ENgetpatternindex('wq')
                    enData.ENsetpattern(patternid, pattern)
                    enData.ENsetnodevalue(nodeid, EN.SOURCEPAT, patternid)

                elif WQ.quality_type == 'AGE':
                    # Set quality type
                    enData.ENsetqualtype(EN.AGE,0,0,0)

                elif WQ.quality_type == 'TRACE':
                    # Set quality type
                    for node in WQ.nodes:
                        enData.ENsetqualtype(EN.TRACE,0,0,node.encode('ascii'))
                else:
                    logger.error('Invalid Quality Type')
            enData.ENopenQ()
            enData.ENinitQ(int(binary_file))

            while True:
                t = enData.ENrunQ()
                if t in results.time:
                    for name in node_names:
                        nodeindex = enData.ENgetnodeindex(name)
                        quality = enData.ENgetnodevalue(nodeindex, EN.QUALITY)

                        if convert_units:
                            if WQ.quality_type == 'CHEM':
                                quality = to_si(flowunits, quality, QualParam.Concentration,
                                                mass_units=mass_units)
                            elif WQ.quality_type == 'AGE':
                                quality = to_si(flowunits, quality, QualParam.WaterAge)

                        node_dictonary['quality'].append(quality)

                tstep = enData.ENnextQ()
                if tstep <= 0:
                    break

            enData.ENcloseQ()

        try:
            enData.ENreport()
        except:
            pass
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
