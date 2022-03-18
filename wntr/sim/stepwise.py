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
from wntr.epanet.toolkit import ENepanet
from wntr.epanet.util import EN, FlowUnits, HydParam, LinkTankStatus, MassUnits, QualParam, to_si
from wntr.network.base import Link, LinkStatus
from wntr.network.controls import StopControl, StopCriteria
from wntr.network.model import WaterNetworkModel
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

    def __init__(self, wn: WaterNetworkModel):
        WaterNetworkSimulator.__init__(self, wn)
        self._en: ENepanet = None
        self._t: int = 0
        self._tn: int = 0
        self._results: SimulationResults = None
        self._node_attributes = [
            (EN.QUALITY, "_quality", "quality", None),
            (EN.DEMAND, "_demand", "demand", HydParam.Demand._to_si),
            (EN.HEAD, "_head", "head", HydParam.HydraulicHead._to_si),
            (EN.PRESSURE, "_pressure", "pressure", HydParam.Pressure._to_si),
        ]
        self._link_attributes = [
            (EN.LINKQUAL, "_quality", "quality", None),
            (EN.FLOW, "_flow", "flowrate", HydParam.Flow._to_si),
            (EN.VELOCITY, "_velocity", "velocity", HydParam.Velocity._to_si),
            (EN.HEADLOSS, "_headloss", "headloss", HydParam.HeadLoss._to_si),
            (EN.STATUS, "_user_status", "status", None),
            (EN.SETTING, "_setting", "setting", None),
        ]
        self._link_sensors = dict()
        self._node_sensors = dict()
        self._stop_criteria = StopCriteria()  # node/link, name, attribute, comparison, level
        self._temp_index = list()
        self._temp_link_report_lines = dict()
        self._temp_node_report_lines = dict()
        self._next_stop_time: int = None
        self._overrides = dict()

    @property
    def current_time(self):
        return self._t

    @property
    def next_time(self):
        return self._en.ENgettimeparam(EN.HTIME)

    def get_results(self):
        return self._results

    def add_stop_criterion(self, control: StopControl) -> int:
        self._stop_criteria.register_criterion(control)

    def remove_stop_criterion(self, control):
        self._stop_criteria.deregister(control)

    def clear_stop_criteria(self):
        self._stop_criteria._controls.clear()

    def query_node_attribute(self, node_name: str, attribute) -> float:
        if self._en is not None:
            node_id = self._en.ENgetnodeindex(node_name)
            if isinstance(attribute, (EN, int)):
                return self._en.ENgetnodevalue(node_id, attribute)
            else:
                return self._en.ENgetnodevalue(node_id, EN[attribute.upper()])
        else:
            msg = "The simulator has not been initialized"
            logger.error(msg)
            raise SimulatorError(msg)

    def query_link_attribute(self, link_name: str, attribute: str) -> float:
        if self._en is not None:
            link_id = self._en.ENgetlinkindex(link_name)
            if isinstance(attribute, (EN, int)):
                return self._en.ENgetlinkvalue(link_id, attribute)
            elif isinstance(attribute, str) and attribute.upper() == "QUALITY":
                return self._en.ENgetlinkvalue(link_id, EN.LINKQUAL)
            else:
                return self._en.ENgetlinkvalue(link_id, EN[attribute.upper()])
        else:
            msg = "The simulator has not been initialized"
            logger.error(msg)
            raise SimulatorError(msg)

    def add_node_sensor(self, node_name: str):
        """
        Add a sensor that keeps the current values of all output parameters for a node.
        These values are accessible by looking at the read-only parameters on the node
        in the water network model.

        Parameters
        ----------
        node_name : str
            the name of the node to track
        """
        node = self._wn.get_node(node_name)
        if self._en is not None:
            node_id = self._en.ENgetnodeindex(node_name)
        else:
            node_id = node_name
        for attr, aname, _, f in self._node_attributes:
            self._node_sensors[(node_id, attr)] = (node, aname, f)

    def add_link_sensor(self, link_name: str):
        """
        Add a sensor that keeps the current values of all output parameters for a link.
        These values are accessible by looking at the read-only parameters on the link
        in the water network model.

        Parameters
        ----------
        link_name : str
            the name of the link to track
        """
        link = self._wn.get_link(link_name)
        if self._en is not None:
            link_id = self._en.ENgetlinkindex(link_name)
        else:
            link_id = link_name
        for attr, aname, _, f in self._link_attributes:
            if attr == EN.SETTING:
                if link.link_type == "Pipe":
                    f = HydParam.RoughnessCoeff._to_si
                elif link.link_type == "Valve":
                    if link.valve_type in ["PRV", "PSV", "PBV"]:
                        f = HydParam.Pressure._to_si
                    elif link.valve_type == "FCV":
                        f = HydParam.Flow._to_si
            self._link_sensors[(link_id, attr)] = (link, aname, f)

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
        if self._en is not None:
            node_id = self._en.ENgetnodeindex(node_name)
        else:
            node_id = node_name
        if node in self._stop_criteria.requires():
            a = SimulatorWarning(
                "You cannot remove a node sensor that is required by stop criteria - action is ignored"
            )
            warnings.warn(a)
        else:
            for attr, _, _, _ in self._node_attributes:
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
        if self._en is not None:
            link_id = self._en.ENgetlinkindex(link_name)
        else:
            link_id = link_name
        if link in self._stop_criteria.requires():
            a = SimulatorWarning(
                "You cannot remove a link sensor that is required by stop criteria - action is ignored"
            )
            warnings.warn(a)
        else:
            for attr, _, _, _ in self._link_attributes:
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
        int
            the size of the timestep that was actually set, in seconds

        Raises
        ------
        SimulatorError
            if the simulation has not been initialized
        """
        if self._en is None:
            a = SimulatorError("The simulation has not been initialized")
            logger.error(a)
            raise a
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
        SimulationError
            if the new duration is less than the current simulation time or
            if the simulation is at the duration or has not been initialized
        """
        if self._en is None:
            w = SimulatorError("The simulation has not been initialized")
            logger.error(w)
            raise w
        elif self._t > seconds:
            w = SimulatorWarning("Current simulation has passed time {} (current is {})".format(seconds, self._t))
            warnings.warn(w)
            return self._en.ENgettimeparam(EN.DURATION)
        elif self._t == seconds:
            w = SimulatorWarning("The simulation is already at time {}".format(seconds))
            warnings.warn(w)
            return self._en.ENgettimeparam(EN.DURATION)
        else:
            self._next_stop_time = seconds
            self._en.ENsettimeparam(EN.DURATION, seconds)
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
        if self._en is None:
            w = SimulatorError("The simulation has not been initialized")
            logger.error(w)
            raise w
        link_num = self._en.ENgetlinkindex(link_name)
        if not override:
            self._en.ENsetlinkvalue(link_num, EN.STATUS, value)
        elif link_name in self._overrides:
            control_number = self._overrides[link_name]
            self._en.ENsetcontrol(control_number, EN.LOWLEVEL, link_num, value, 1, 1e30)
        else:
            control_number = self._en.ENaddcontrol(EN.LOWLEVEL, link_num, value, 1, 1e30)
            self._overrides[link_name] = control_number

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
        if self._en is None:
            w = SimulatorError("The simulation has not been initialized")
            logger.error(w)
            raise w
        link_num = self._en.ENgetlinkindex(link_name)
        if not override:
            self._en.ENsetlinkvalue(link_num, EN.SETTING, value)
        elif link_name in self._overrides:
            control_number = self._overrides[link_name]
            self._en.ENsetcontrol(control_number, EN.LOWLEVEL, link_num, value, 1, 1e30)
        else:
            control_number = self._en.ENaddcontrol(EN.LOWLEVEL, link_num, value, 1, 1e30)
            self._overrides[link_name] = control_number

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
        if self._en is None:
            w = SimulatorError("The simulation has not been initialized")
            logger.error(w)
            raise w
        if link_name in self._overrides.keys():
            control_number = self._overrides[link_name]
            self._en.ENdeletecontrol(control_number)
            for k, v in self._overrides.items():
                if v > control_number:
                    self._overrides[k] = v - 1
        else:
            w = SimulatorWarning("No override set on the specified link")
            warnings.warn(w)

    def _save_report_step(self):
        t = self._en.ENgettimeparam(EN.HTIME)
        # this is checking to make sure we are at a report step, or if past the step, but it didn't get reported, then report out.
        report_line = -1 if t < self._report_start else (t - self._report_start) // self._report_timestep
        if report_line > self._last_line_added:
            time = self._report_start + report_line * self._report_timestep
            self._last_line_added = report_line
            logger.debug("Reporting at time {}".format(time))
            self._temp_index.append(time)
            demand = list()
            head = list()
            pressure = list()
            quality = list()
            for idx in self._node_name_idx:
                demand.append(self._en.ENgetnodevalue(idx, EN.DEMAND))
                head.append(self._en.ENgetnodevalue(idx, EN.HEAD))
                pressure.append(self._en.ENgetnodevalue(idx, EN.PRESSURE))
                quality.append(self._en.ENgetnodevalue(idx, EN.QUALITY))
            self._temp_node_report_lines["demand"].append(demand)
            self._temp_node_report_lines["head"].append(head)
            self._temp_node_report_lines["pressure"].append(pressure)
            self._temp_node_report_lines["quality"].append(quality)
            linkqual = list()
            flow = list()
            velocity = list()
            headloss = list()
            status = list()
            setting = list()
            for idx in self._link_name_idx:
                linkqual.append(self._en.ENgetlinkvalue(idx, EN.LINKQUAL))
                flow.append(self._en.ENgetlinkvalue(idx, EN.FLOW))
                velocity.append(self._en.ENgetlinkvalue(idx, EN.VELOCITY))
                headloss.append(self._en.ENgetlinkvalue(idx, EN.HEADLOSS))
                status.append(self._en.ENgetlinkvalue(idx, EN.STATUS))
                setting.append(self._en.ENgetlinkvalue(idx, EN.SETTING))
            self._temp_link_report_lines["quality"].append(linkqual)
            self._temp_link_report_lines["flowrate"].append(flow)
            self._temp_link_report_lines["velocity"].append(velocity)
            self._temp_link_report_lines["headloss"].append(headloss)
            self._temp_link_report_lines["status"].append(status)
            self._temp_link_report_lines["setting"].append(setting)

    def _copy_results_object(self):
        if len(self._temp_index) == 0:
            return
        for _, _, name, f in self._node_attributes:
            df2 = np.array(self._temp_node_report_lines[name])
            if f is not None:
                df2 = f(self._flow_units, df2, mass_units=self._mass_units)
            self._results.node[name].loc[self._temp_index, :] = df2
            self._temp_node_report_lines[name] = list()
        for _, _, name, f in self._link_attributes:
            df2 = np.array(self._temp_link_report_lines[name])
            if f is not None:
                df2 = f(self._flow_units, df2, mass_units=self._mass_units)
            self._results.link[name].loc[self._temp_index, :] = df2
            self._temp_link_report_lines[name] = list()
        self._temp_index = list()

    def _setup_results_object(self, results_size):
        self._results = SimulationResults()
        self._results.node = dict()
        self._results.link = dict()
        self._node_name_idx = list()
        self._link_name_idx = list()
        self._node_name_str = self._wn.node_name_list
        self._link_name_str = self._wn.link_name_list
        index = [self._report_start]
        if results_size > 0:
            index = np.arange(
                self._report_start,
                self._report_start + (results_size + 1) * self._report_timestep,
                self._report_timestep,
            )
        for node_name in self._node_name_str:
            self._node_name_idx.append(self._en.ENgetnodeindex(node_name))
        for link_name in self._link_name_str:
            self._link_name_idx.append(self._en.ENgetlinkindex(link_name))
        for _, _, name, _ in self._node_attributes:
            self._results.node[name] = pd.DataFrame([], columns=self._node_name_str, index=index)
            self._temp_node_report_lines[name] = list()
        for _, _, name, _ in self._link_attributes:
            self._results.link[name] = pd.DataFrame([], columns=self._link_name_str, index=index)
            self._temp_link_report_lines[name] = list()

    def _save_intermediate_values(self):
        for name, vals in self._node_sensors.items():
            en_idx, at_idx = name  # (where, what) you are measuring
            node, attr, f = vals  # WNTR node object, attribute name, and conversion function
            value = self._en.ENgetnodevalue(en_idx, at_idx)
            if f is not None:
                value = f(self._flow_units, value, mass_units=self._mass_units)
            setattr(node, attr, value)  # set the simulation value on the node object
        for name, vals in self._link_sensors.items():
            en_idx, at_idx = name
            link, attr, f = vals
            value = self._en.ENgetlinkvalue(en_idx, at_idx)
            if f is not None:
                value = f(self._flow_units, value, mass_units=self._mass_units)
            setattr(link, attr, value)

    def initialize(
        self, file_prefix: str = "temp", version=2.2, save_hyd=False, use_hyd=False, hydfile=None, result_size=0
    ):
        if self._en is not None:
            raise SimulatorError(self.__class__.__name__ + " already initialized")
        inpfile = file_prefix + ".inp"
        enData = wntr.epanet.toolkit.ENepanet(version=version)
        self._wn.write_inpfile(inpfile, units=self._wn.options.hydraulic.inpfile_units, version=version)
        rptfile = file_prefix + ".rpt"
        outfile = file_prefix + ".bin"
        self.outfile = outfile
        enData.ENopen(inpfile, rptfile, outfile)
        self._en = enData
        self._flow_units = FlowUnits(self._en.ENgetflowunits())
        self._mass_units = MassUnits.mg

        enData.ENsettimeparam(EN.DURATION, int(86400 * 365.25 * 10))
        self._t = 0
        self._report_timestep = enData.ENgettimeparam(EN.REPORTSTEP)
        self._report_start = enData.ENgettimeparam(EN.REPORTSTART)
        self._last_line_added = -1

        if self._wn.options.quality.parameter is not None:
            if self._wn.options.quality.parameter.upper() == "CHEMICAL":
                if self._wn.options.quality.inpfile_units.lower().startswith("ug"):
                    self._mass_units = MassUnits.ug
                self._node_attributes[0] = (
                    self._node_attributes[0][0],
                    self._node_attributes[0][1],
                    self._node_attributes[0][2],
                    QualParam.Concentration._to_si,
                )
                self._link_attributes[0] = (
                    self._link_attributes[0][0],
                    self._link_attributes[0][1],
                    self._link_attributes[0][2],
                    QualParam.Concentration._to_si,
                )
            elif self._wn.options.quality.parameter.upper() == "AGE":
                self._node_attributes[0] = (
                    self._node_attributes[0][0],
                    self._node_attributes[0][1],
                    self._node_attributes[0][2],
                    QualParam.WaterAge._to_si,
                )
                self._link_attributes[0] = (
                    self._link_attributes[0][0],
                    self._link_attributes[0][1],
                    self._link_attributes[0][2],
                    QualParam.WaterAge._to_si,
                )

        self._setup_results_object(result_size)
        # setup intermediate sensors indices from names to internal EPANET numbers
        new_link_sensors = dict()
        new_node_sensors = dict()
        for name, vals in self._link_sensors.items():
            wn_name, attr = name
            en_idx = enData.ENgetlinkindex(wn_name)
            if attr == EN.LINKQUAL:
                vals = (vals[0], vals[1], self._link_sensors[0][-1])
            new_link_sensors[(en_idx, attr)] = vals
        for name, vals in self._node_sensors.items():
            wn_name, attr = name
            en_idx = enData.ENgetnodeindex(wn_name)
            if attr == EN.QUALITY:
                vals = (vals[0], vals[1], self._node_sensors[0][-1])
            new_node_sensors[(en_idx, attr)] = vals
        self._link_sensors = new_link_sensors
        self._node_sensors = new_node_sensors

        enData.ENopenH()
        enData.ENinitH(1)
        enData.ENopenQ()
        enData.ENinitQ(1)
        enData.ENrunH()
        enData.ENrunQ()

        # Load initial time-0 results into results (if reporting)
        self._save_report_step()  # saves on internal temp results lists
        # Load initial time-0 results into intermediate sensors
        self._save_intermediate_values()  # stores on WaterNetworkModel
        self._t = enData.ENgettimeparam(EN.HTIME)
        tstep = enData.ENnextH()
        qstep = enData.ENnextQ()
        self._nt = self._t + tstep
        self._copy_results_object()
        logger.debug("Initialized stepwise run")

    def run_sim(self):
        enData = self._en
        completed = True
        conditions = list()
        if enData is None:
            raise SimulatorError(self.__class__.__name__ + " not initialized before use")
        if self._t > self._next_stop_time:
            return True, []
        while True:
            # Run hydraulic TS and quality TS
            enData.ENrunH()
            enData.ENrunQ()

            # Read all sensors in the _node and _link sensors list
            self._save_intermediate_values()
            self._save_report_step()
            logger.debug("Ran 1 step")

            # Check on stop criteria
            conditions = self._stop_criteria.check()
            if len(conditions) > 0:
                enData.ENsettimeparam(EN.DURATION, enData.ENgettimeparam(EN.HTIME))
                completed = False

            self._t = enData.ENgettimeparam(EN.HTIME)

            # Move EPANET forward in time
            tstep = enData.ENnextH()
            qstep = enData.ENnextQ()

            self._nt = self._t + tstep

            # if tstep < 1, duration has been reached
            if tstep <= 0 or self._t > self._next_stop_time:
                self._save_report_step()
                break

            # Update time

        self._copy_results_object()
        return completed, conditions

    def close(self):
        enData = self._en
        if enData is None:
            raise SimulatorError(self.__class__.__name__ + " not initialized before use")
        tstep = 1
        while tstep > 0:
            enData.ENrunH()
            enData.ENrunQ()
            tstep = enData.ENnextH()
            qstep = enData.ENnextQ()
            self._save_report_step()
        enData.ENcloseH()
        enData.ENcloseQ()
        logger.debug("Solved quality")
        enData.ENreport()
        logger.debug("Ran quality")
        enData.ENclose()
        logger.debug("Completed step run")
        self._en = None
        # results = wntr.epanet.io.BinFile().read(self.outfile)
        self._copy_results_object()
        return self._results
