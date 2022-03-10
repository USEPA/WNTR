# coding: utf-8
"""
Create an stepwise simulation.

There are several differences between a stepwise simulator, and batch (normal) simulator,
and a real time simulator. In WNTR, a normal water network simulator will run an entire
simulation, from start to finish, and then populate and return the results to the user.
In a real time simulation, the simulator is run in a separate process that is connected
to some other mechanism, such as a SCADA simulator, that performs all controls. A stepwise
simulator serves as a hybrid, or midway point, between the two.

A stepwise simulator retains all user controls and rules of operation internally, just as
the normal simulators do. However, instead of running the entire simulation, it will run 
just a single step of the simulation.

The main difficulty is determining how long that step should be for. There are multiple 
time steps defined in WNTR and EPANET - hydraulic, water quality, rule, report, etc.
Rather than picking one of these, the stepwise simulators simply treat the current duration
as the step size, and simply do not close the internal or EPANET simulator at the end
when the duration has been reached. This means that for each step in an outer, user defined
loop, the user must change the duration by using either "set_new_duration" or "add_more_time"
functions.
"""

import logging
import warnings

import numpy as np
import pandas as pd
import wntr.epanet.io
from wntr.epanet.util import EN
from wntr.network.base import LinkStatus
from wntr.network.controls import StopControl, StopCriteria
from wntr.sim.core import WaterNetworkSimulator
from wntr.sim.results import SimulationResults
from wntr.utils.exceptions import SimulatorError, SimulatorWarning

logger = logging.getLogger(__name__)


class EpanetSimulator_Stepwise(WaterNetworkSimulator):
    """
    _summary_

    Parameters
    ----------
    wn : WaterNetworkModel
        _description_
    """

    def __init__(self, wn):
        WaterNetworkSimulator.__init__(self, wn)
        self._en = None
        self._t = 0
        self._results = None
        self.__initialized = False
        self._node_attributes = [
            (EN.DEMAND, "_demand", "demand"),
            (EN.HEAD, "_head", "head"),
            (EN.PRESSURE, "_pressure", "pressure"),
            (EN.QUALITY, "_quality", "quality"),
        ]
        self._link_attributes = [
            (EN.LINKQUAL, "_quality", "quality"),
            (EN.FLOW, "_flow", "flowrate"),
            (EN.VELOCITY, "_velocity", "velocity"),
            (EN.HEADLOSS, "_headloss", "headloss"),
            (EN.STATUS, "_user_status", "status"),
            (EN.SETTING, "_setting", "setting"),
        ]
        self._link_sensors = dict()
        self._node_sensors = dict()
        self._stop_criteria = StopCriteria()  # node/link, name, attribute, comparison, level
        self._crit_num = 0
        self._temp_link_report_lines = dict()
        self._temp_node_report_lines = dict()
        self._next_stop_time = None

    def add_stop_criterion(self, control: StopControl) -> int:
        raise NotImplementedError()

    def remove_stop_criterion(self, number):
        raise NotImplementedError()

    def clear_stop_criteria(self):
        raise NotImplementedError()

    def query_node_attribute(self, node_name: str, attribute) -> float:
        if self.__initialized:
            node_id = self._en.ENgetnodeindex(node_name)
            if isinstance(attribute, (EN, int)):
                return self._en.ENgetnodevalue(node_id, attribute)
            else:
                return self._en.ENgetnodevalue(node_id, EN[attribute.upper()])
        else:
            msg = 'query_node_attribute cannot be called until the simulator is initialized'
            logger.error(msg)
            raise SimulatorError(msg)

    def query_link_attribute(self, link_name: str, attribute: str) -> float:
        if self.__initialized:
            link_id = self._en.ENgetlinkindex(link_name)
            if isinstance(attribute, (EN,int)):
                return self._en.ENgetlinkvalue(link_id, attribute)
            elif isinstance (attribute, str) and attribute.upper() == 'QUALITY':
                return self._en.ENgetlinkvalue(link_id, EN.LINKQUAL)
            else:
                return self._en.ENgetlinkvalue(link_id, EN[attribute.upper()])
        else:
            msg = 'query_link_attribute cannot be called until the simulator is initialized'
            logger.error(msg)
            raise SimulatorError(msg)

    def add_node_sensor(self, node_name: str):
        """
        Add a sensor that will hold the current value of an attribute at a specific node.

        Parameters
        ----------
        node_name : str
            _description_
        attribute : str
            Must be one of "DEMAND", "HEAD", "PRESSURE", "QUALITY"

        Raises
        ------
        NotImplementedError
            _description_
        """
        node = self._wn.get_node(node_name)
        if self.__initialized:
            node_id = self._en.ENgetnodeindex(node_name)
        else:
            node_id = node_name
        for attr, aname, rname in self._node_attributes:
            self._node_sensors[(node_id, attr)] = (node, aname)

    def add_link_sensor(self, link_name: str):
        """
        Add a sensor that will hold the current value of an attribute on a specific link.

        Parameters
        ----------
        link_name : str
            _description_
        attribute : str
            Must be one of "LINKQUAL", "FLOW", "VELOCITY", "HEADLOSS", "STATUS" or "SETTING"


        Raises
        ------
        NotImplementedError
            _description_
        """
        link = self._wn.get_link(link_name)
        if self.__initialized:
            link_id = self._en.ENgetlinkindex(link_name)
        else:
            link_id = link_name
        for attr, aname, rname in self._link_attributes:
            self._node_sensors[(link_id, attr)] = (link, aname)

    def remove_node_sensor(self, node_name: str):
        """
        _summary_

        Parameters
        ----------
        node_name : str
            _description_

        Raises
        ------
        NotImplementedError
            _description_
        """
        node = self._wn.get_node(node_name)
        if self.__initialized:
            node_id = self._en.ENgetnodeindex(node_name)
        else:
            node_id = node_name
        if node in self._stop_criteria.requires():
            a = SimulatorWarning("You cannot remove a node sensor that is required by stop criteria - action is ignored")
            warnings.warn(a)
        else:
            for attr, name, rname in self._node_attributes:
                self._node_sensors.pop((node_id, attr))
        
    def remove_link_sensor(self, link_name: str):
        """
        _summary_

        Parameters
        ----------
        link_name : str
            _description_
        attribute : str, optional
            _description_, by default None

        Raises
        ------
        NotImplementedError
            _description_
        """
        link = self._wn.get_link(link_name)
        if self.__initialized:
            link_id = self._en.ENgetlinkindex(link_name)
        else:
            link_id = link_name
        if link in self._stop_criteria.requires():
            a = SimulatorWarning("You cannot remove a link sensor that is required by stop criteria - action is ignored")
            warnings.warn(a)
        else:
            for attr, aname, rname in self._link_attributes:
                self._link_sensors.pop((link_id, attr))

    def set_hydraulic_timestep(self, seconds: int) -> int:
        """
        Set the hydraulic timestep to the specified number of seconds.
        The hydraulic timestep must be an integer greater than or equal to 1 second.
        This value is limited on the upper end by the report step size, among others.
        If it is set to be too large, then it will simply be truncated.

        Parameters
        ----------
        seconds : int
            the size of the hydraulic timestep, in integer seconds greater than 0

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        NotImplementedError
            _description_
        """
        if not self.__initialized:
            a = SimulatorWarning("The simulation has not been initialized, please modify wn.options.time.duration instead")
            warnings.warn(a)
            return self._wn.options.time.hydraulic_timestep
        self._en.ENsettimeparam(EN.HYDSTEP, seconds)
        return self._en.ENgettimeparam(EN.HYDSTEP)

    def set_next_stop_time(self, seconds: int) -> int:
        """

        Parameters
        ----------
        seconds : int
            the new total simulation duration, in seconds

        Returns
        -------
        int
            the new total simulation duration, in seconds

        Raises
        ------
        NotImplementedError
            _description_
        ValueError
            if the new duration is less than the current simulation time
        """
        if not self.__initialized:
            w = SimulatorWarning("The simulation has not been initialized, please modify wn.options.time.duration instead") 
            warnings.warn(w)
            return self._wn.options.time.duration
        elif self._t > seconds:
            raise SimulatorError('Current simulation has passed time {} (current is {})'.format(seconds, self._t))
        elif self._t == seconds:
            w = SimulatorWarning("The simulation is already at time {}".format(seconds))
            warnings.warn(w)
        else:
            hstep = self._en.ENgettimeparam(EN.HYDSTEP)
            self._next_stop_time = seconds
            self._en.ENsettimeparam(EN.DURATION, ((seconds// hstep)+1)*hstep)
            # self._en.ENsettimeparam(EN.DURATION, seconds + )
            return self._en.ENgettimeparam(EN.DURATION)

    def set_link_status(self, link_name: str, value: float, override=False):
        """
        _summary_

        Parameters
        ----------
        link_name : str
            _description_
        value : _type_
            _description_

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        NotImplementedError
            _description_
        """
        if not self.__initialized:
            a = SimulatorWarning('You cannot change a link status with set_link_status until the simulation is initialized - action ignored')
            warnings.warn(a)
            return False
        raise NotImplementedError()
        return True

    def set_link_setting(self, link_name: str, value: float, override=False):
        """
        _summary_

        Parameters
        ----------
        link_name : str
            _description_
        value : float
            _description_

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        NotImplementedError
            _description_
        """
        if not self.__initialized:
            a = SimulatorWarning('You cannot change a link status with set_link_status until the simulation is initialized - action ignored')
            warnings.warn(a)
            return False
        raise NotImplementedError()
        return True

    def release_override(self, link_name: str):
        """
        _summary_

        Parameters
        ----------
        link_name : str
            _description_

        Raises
        ------
        NotImplementedError
            _description_
        """
        if not self.__initialized:
            a = SimulatorWarning('You cannot release an override with release_override until the simulation is initialized - action ignored')
            warnings.warn(a)
            return False
        raise NotImplementedError()

    def save_report_step(self):
        t = self._en.ENgettimeparam(EN.HTIME)
        report_line = -1 if t < self._report_start else (t - self._report_start) // self._report_timestep
        if report_line > self._last_line_added:
            time = self._report_start + report_line * self._report_timestep
            self._last_line_added = report_line
            logger.debug('Reporting at time {}'.format(time))

    def initialize(
            self, file_prefix: str = "temp", version=2.2, save_hyd=False, use_hyd=False, hydfile=None,):
        if self.__initialized:
            raise SimulatorError(self.__class__.__name__ +" already initialized")
        self.__initialized = True
        inpfile = file_prefix + ".inp"
        enData = wntr.epanet.toolkit.ENepanet(version=version)
        self._wn.write_inpfile(inpfile, units=self._wn.options.hydraulic.inpfile_units, version=version)
        rptfile = file_prefix + ".rpt"
        outfile = file_prefix + ".bin"
        self.outfile = outfile
        self._results = SimulationResults()
        enData.ENopen(inpfile, rptfile, outfile)
        self._en = enData
        enData.ENsettimeparam(EN.DURATION, int(86400 * 365.25 * 10))
        enData.ENopenH()
        enData.ENinitH(1)
        enData.ENopenQ()
        enData.ENinitQ(1)
        enData.ENrunH()
        enData.ENrunQ()
        self._t = 0
        self._report_timestep = enData.ENgettimeparam(EN.REPORTSTEP)
        self._report_start = enData.ENgettimeparam(EN.REPORTSTART)
        self._last_line_added = -1
        self.save_report_step()            
        logger.debug("Initialized stepwise run")
        # TODO: need to create a list of nodes and links and their attributes for
        # calculating results
        new_link_sensors = dict()
        new_node_sensors = dict()
        for name, vals in self._link_sensors.items():
            wn_name, attr = name
            en_idx = enData.ENgetlinkindex(wn_name)
            new_link_sensors[(en_idx, attr)] = vals
        for name, vals in self._node_sensors.items():
            wn_name, attr = name
            en_idx = enData.ENgetnodeindex(wn_name)
            new_node_sensors[(en_idx, attr)] = vals
        self._link_sensors = new_link_sensors
        self._node_sensors = new_node_sensors

        # Load initial time-0 results into intermediate sensors
        for name, vals in self._node_sensors.items():
            en_idx, at_idx = name
            node, attr = vals
            value = enData.ENgetnodevalue(en_idx, at_idx)
            setattr(node, attr, value)
        for name, vals in self._link_sensors.items():
            en_idx, at_idx = name
            link, attr = vals
            value = enData.ENgetlinkvalue(en_idx, at_idx)
            setattr(link, attr, value)

        tstep = enData.ENnextH()
        qstep = enData.ENnextQ()
        self._t = self._t + tstep

    def run_sim(self):
        enData = self._en
        completed = True
        conditions = list()
        if enData is None:
            raise SimulatorError(self.__class__.__name__ +" not initialized before use")

        while True:
            # Run hydraulic TS and quality TS
            enData.ENrunH()
            enData.ENrunQ()

            # Read all sensors in the _node and _link sensors list
            for name, vals in self._node_sensors.items():
                en_idx, at_idx = name
                node, attr = vals
                value = enData.ENgetnodevalue(en_idx, at_idx)
                setattr(node, attr, value)
            for name, vals in self._link_sensors.items():
                en_idx, at_idx = name
                link, attr = vals
                value = enData.ENgetlinkvalue(en_idx, at_idx)
                setattr(link, attr, value)
            self.save_report_step()
            logger.debug("Ran 1 step")

            # Check on stop criteria
            conditions = self._stop_criteria.check()
            if len(conditions) > 0:
                enData.ENsettimeparam(EN.DURATION, enData.ENgettimeparam(EN.HTIME))
                completed = False

            # Move EPANET forward in time
            tstep = enData.ENnextH()
            qstep = enData.ENnextQ()

            # if tstep < 1, duration has been reached
            if tstep <= 0 or tstep + self._t > self._next_stop_time:
                self.save_report_step()
                break

            # Update time
            self._t = self._t + tstep
        
        return completed, conditions

    def close(self):
        enData = self._en
        if enData is None:
            raise SimulatorError(self.__class__.__name__ +" not initialized before use")
        tstep = 1
        while tstep > 0:
            enData.ENrunH()
            enData.ENrunQ()
            tstep = enData.ENnextH()
            qstep = enData.ENnextQ()
        enData.ENcloseH()
        enData.ENcloseQ()
        logger.debug("Solved quality")
        enData.ENreport()
        logger.debug("Ran quality")
        enData.ENclose()
        logger.debug("Completed step run")
        results = wntr.epanet.io.BinFile().read(self.outfile)
        return results
