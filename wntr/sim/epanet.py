from wntr.sim.core import *
import pandas as pd
import numpy as np
from wntr.epanet.util import FlowUnits, MassUnits, HydParam, QualParam, EN, to_si, from_si
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

    def run_sim(self, convert_units=True, file_prefix='temp'):
        """
        Run an extended period simulation.
        The EpanetSimulator uses an INP file written from the water network model.

        Parameters
        ----------
        convert_units : bool (optional)
            Convert results to SI units, default = True

        file_prefix : string (optional)
            INP and RPT file prefix, default = 'tmp'
        """
        # Write a new inp file from the water network model
        self._wn.name = file_prefix + '.inp'
        self._wn.write_inpfile(file_prefix + '.inp')
        
        start_run_sim_time = time.time()
        logger.debug('Starting run')
        # Create enData
        enData = wntr.epanet.pyepanet.ENepanet()
        enData.inpfile = self._wn.name
        enData.ENopen(enData.inpfile, file_prefix + '.rpt')
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
        nnodes = self._wn.num_nodes
        nlinks = self._wn.num_links
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
        
        if self._wn.options.quality is not 'NONE':
            
            node_dictonary['quality'] = []

            enData.ENopenQ()
            enData.ENinitQ(0)

            while True:
                t = enData.ENrunQ()
                if t in results.time:
                    for name in node_names:
                        nodeindex = enData.ENgetnodeindex(name)
                        quality = enData.ENgetnodevalue(nodeindex, EN.QUALITY)

                        if convert_units:
                            if self._wn.options.quality == 'CHEMICAL':
                                quality = to_si(flowunits, quality, QualParam.Concentration,
                                                mass_units=mass_units)
                            elif self._wn.options.quality == 'AGE':
                                quality = to_si(flowunits, quality, QualParam.WaterAge)

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
