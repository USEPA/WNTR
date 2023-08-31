# coding: utf-8
"""
A stepwise simulator using EPANET 2.2 as the execcution engine.
"""

import logging
from re import S
from typing import Union
import warnings

import numpy as np
import pandas as pd
import wntr.epanet.io
from wntr.epanet.toolkit import ENepanet
from wntr.epanet.util import EN, FlowUnits, HydParam, LinkTankStatus, MassUnits, QualParam, to_si
from wntr.network.base import Link, LinkStatus, Node
from wntr.network.controls import StopControl, StopCriteria, Control
from wntr.network.model import WaterNetworkModel
from wntr.sim.core import WaterNetworkSimulator
from wntr.sim.results import SimulationResults
from wntr.utils.exceptions import SimulatorError, SimulatorWarning

logger = logging.getLogger(__name__)


class EpanetSimulator_Stepwise(WaterNetworkSimulator):
    def __init__(
        self,
        wn: WaterNetworkModel,
        file_prefix: str = "temp",
        version=2.2,
        save_hyd=False,
        use_hyd=False,
        hydfile=None,
        maximum_duration=None,
    ):
        """Stepwise EPANET simulator class.

        Uses the EPANET DLL to run in a step-by-step manner, either through a loop
        or a generator. The next step size can be set manually each call, or the
        defined step from the WaterNetworkModel options will be used by default.
        A maximum duration can be set, otherwise the stop time can be arbitrarily
        set, and even changed mid simulation, by the user.

        Parameters
        ----------
        wn : WaterNetworkModel
            the water network model
        file_prefix : str, optional
            prefix to use for the temporary file, by default "temp"
        version : float, optional
            EPANET DLL version, by default 2.2 (strongly recommended)
        save_hyd : bool, optional
            save a hydraulics file for use later, by default False
        use_hyd : bool, optional
            load a previously saved hydraulics file, by default False
        hydfile : str, optional
            name of the hydraulics file to use, by default None
        maximum_duration : int, optional
            a maximum duration this run could go, by default None (the wn duration);
            use a value of -1 to set to the maximum possible run length (2**31 seconds)


        Examples
        --------
        There are two methods to use the stepwise simulator. The first mode is useful
        for loops where interaction will occur at regular time steps. The second mode
        is more useful when the simulation may be called at irregular steps, from 
        another function e.g.

        Both the two examples below show a simple 1-day simulation

        Method one

        .. code::

            with EpanetSimulator_Stepwise(wn, file_prefix="temp1") as sim:
                sim.step_size = 3600
                sim.duration = 86400
                for success, stop_conditions in sim:
                    step_results = sim.get_results()
                    # do something
            results = wntr.epanet.io.BinFile().read("temp1.bin")

        Method two

        .. code::

            sim = EpanetSimulator_Stepwise(wn, file_prefix="temp2")
            sim.initialize()
            for i in range(24):
                sim.set_next_stop_time(3600*(i+1))
                success = True
                while not success:
                    success, stop_conditions = sim.run_sim()
                    # do something
            sim.close()
            results = wntr.epanet.io.BinFile().read("temp2.bin")
        

        Because of the way EPANET binary files are written, a warning will be issued
        when reading in the results - this is normal and is not a problem.

        """
        super().__init__(wn)
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
        self.logger = logger
        self._link_sensors = dict()
        self._node_sensors = dict()
        self._stop_criteria = StopCriteria()  # node/link, name, attribute, comparison, level
        self._temp_index = list()
        self._temp_link_report_lines = dict()
        self._temp_node_report_lines = dict()
        self._next_stop_time: int = None
        self._overrides = dict()
        self._file_prefix = file_prefix
        self._version = version
        self._save_hyd = save_hyd
        self._use_hyd = use_hyd
        self._hydfile = hydfile
        self._duration = wn.options.time.duration
        self._max_duration = maximum_duration

    @property
    def current_time(self) -> int:
        """the last time solved, in seconds (read-only)"""
        return self._t

    @property
    def next_time(self) -> int:
        """the next time to be solved, in seconds (read-only)"""
        return self._en.ENgettimeparam(EN.HTIME)

    @property
    def duration(self) -> int:
        """Time when a generator loop will stop simulation"""
        return self._duration

    @duration.setter
    def duration(self, seconds: int) -> None:
        self._duration = seconds

    @property
    def step_size(self) -> int:
        """Length of each simulation step within a generator loop, in seconds"""
        return self._delta_t

    @step_size.setter
    def step_size(self, seconds: int) -> None:
        self._delta_t = seconds

    def get_results(self) -> list:
        """Get results that have been collated since the last run_sim or step call.

        Returns
        -------
        list
            dataframes of results for each attribute
        """
        return self._results

    def add_stop_criterion(self, control: StopControl):
        """Add a stop criterion for this simulator.

        A stop control will stop the simulator before a step has completed if the
        criterion has been met. The criteria

        Parameters
        ----------
        control : StopControl
            a stop criteria to check for
        """
        self._stop_criteria.register_criterion(control)
        for obj in self._stop_criteria.requires():
            if isinstance(obj, Node):
                self.add_node_sensor(obj.name)
            elif isinstance(obj, Link):
                self.add_link_sensor(obj.name)

    def remove_stop_criterion(self, control: Union[StopControl, str]):
        """Unregister a stop criteria control

        Parameters
        ----------
        control : StopControl or str
            the stop criteria name or object
        """
        self._stop_criteria.deregister(control)

    def clear_stop_criteria(self):
        """Remove all stop criteria from the simulator"""
        self._stop_criteria._controls.clear()

    def query_node_attribute(self, node_name: str, attribute) -> float:
        """Get the current, instantaneous value of a node's attribute

        Of particular note, this method does not require the simulator to
        be stopped at a report step, it queries the value at the current
        calculation step.

        Parameters
        ----------
        node_name : str
            name of the node to query
        attribute : str, int, or EN enum
            attribute to query (must be a valid EPANET toolkit attribute name or integer)

        Returns
        -------
        float
            value of node/attribute

        Raises
        ------
        SimulatorError
            if the simulation has not been initialized
        """
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
        """Get the current, instantaneous value of a link's attribute

        Of particular note, this method does not require the simulator to
        be stopped at a report step, it queries the value at the current
        calculation step.

        Parameters
        ----------
        link_name : str
            name of the link to query
        attribute : str, int, or EN enum
            attribute to query (must be a valid EPANET toolkit attribute name or integer)

        Returns
        -------
        float
            value of link/attribute

        Raises
        ------
        SimulatorError
            if the simulation has not been initialized
        """
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

        Similar to querying a specific node, adding a node as a sensor means that the
        values of all attributes are automatically set on the network model at each
        hydraulic time step. This is required when using StopControl criteria.
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

        Similar to querying a specific link, adding a link as a sensor means that the
        values of all attributes are automatically set on the network model at each
        hydraulic time step. This is required when using StopControl criteria.
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
        Remove a node from the list of sensors

        Parameters
        ----------
        node_name : str
            The name of the sensor to remove

        Raises
        ------
        SimulatorWarning
            if the sensor cannot be removed because it is required by a stop criterion.
            The stop criterion must be removed first.
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
        Remove a link from the list of sensors

        Parameters
        ----------
        link_name : str
            The name of the sensor to remove

        Raises
        ------
        SimulatorWarning
            if the sensor cannot be removed because it is required by a stop criterion.
            The stop criterion must be removed first.
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
        Set the next time when the :method:`run_sim` call will stop.

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
            return self._t  # self._en.ENgettimeparam(EN.DURATION)
        elif self._t == seconds:
            w = SimulatorWarning("The simulation is already at time {}".format(seconds))
            warnings.warn(w)
            return self._t  # self._en.ENgettimeparam(EN.DURATION)
        else:
            self._next_stop_time = seconds
            # self._en.ENsettimeparam(EN.DURATION, seconds)
            return self._next_stop_time  # self._en.ENgettimeparam(EN.DURATION)

    def set_link_status(self, link_name: str, value: float, override=True):
        """
        Set the status of a link and optionally override any other controls

        Parameters
        ----------
        link_name : str
            the name of the link to change
        value : float
            the status value to assign to the link
        override : bool
            whether controls or rules which change the link should be disabled, be default ``True``

        Raises
        ------
        SimulatorError
            if the simulation has not been initialized
        """
        if self._en is None:
            w = SimulatorError("The simulation has not been initialized")
            logger.error(w)
            raise w
        link_num = self._en.ENgetlinkindex(link_name)
        self._en.ENsetlinkvalue(link_num, EN.STATUS, value)
        if link_name in self._overrides and override:
            # FIXME: handle overrides
            controls = self._overrides[link_name]
            for ctrl_data in controls:
                self._en.ENsetcontrol(
                    ctrl_data["index"],
                    EN.LOWLEVEL,
                    ctrl_data["linkindex"],
                    value,
                    ctrl_data["nodeindex"],
                    0.0,
                )
        # else:
        #     w = SimulatorWarning("No override set on the specified link")
        #     warnings.warn(w)

    def set_link_setting(self, link_name: str, value: float, override=True):
        """
        Change the setting of a link (pump power or valve setting).

        Parameters
        ----------
        link_name : str
            the name of the link to set
        value : float
            the setting value
        override : bool
            whether controls or rules which change the link should be disabled, be default ``True``

        Raises
        ------
        SimulationError
            if the simulation has not been initialized
        """
        if self._en is None:
            w = SimulatorError("The simulation has not been initialized")
            logger.error(w)
            raise w
        link_num = self._en.ENgetlinkindex(link_name)
        self._en.ENsetlinkvalue(link_num, EN.SETTING, value)
        if link_name in self._overrides and override:
            # FIXME: handle overrides
            controls = self._overrides[link_name]
            for ctrl_data in controls:
                self._en.ENsetcontrol(
                    ctrl_data["index"],
                    EN.LOWLEVEL,
                    ctrl_data["linkindex"],
                    value,
                    ctrl_data["nodeindex"],
                    0.0,
                )
        # else:
        #     w = SimulatorWarning("No override set on the specified link")
        #     warnings.warn(w)

    def release_override(self, link_name: str):
        """
        Release a link override and reenable appropriate controls

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
        link_num = self._en.ENgetlinkindex(link_name)
        if link_name in self._overrides.keys():
            # FIXME: handle overrides
            controls = self._overrides[link_name]
            for ctrl_data in controls:
                index = self._en.ENaddcontrol(
                    ctrl_data["type"],
                    ctrl_data["linkindex"],
                    ctrl_data["setting"],
                    ctrl_data["nodeindex"],
                    ctrl_data["level"],
                )
                ctrl_data["index"] = index
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
        # while (max(self._temp_index) > self._results.node['head'].index.max()):
        #     # add more chunks if max index exceeded
        #     last_index = self._results.node['head'].index.max()
        #     next_start = last_index + self._report_timestep
        #     next_end = next_start + self._chunk_size * self._report_timestep + 1
        #     nnodes = self._wn.num_nodes
        #     nlinks = self._wn.num_links
        #     index = np.arange(next_start, next_end, self._report_timestep)
        #     dfna = pd.DataFrame(np.nan * np.zeros([len(index), nnodes]), index=index, columns=self._results.node['head'].columns)
        #     for _, _, name, _ in self._node_attributes:
        #         df2 = pd.concat([self._results.node[name], dfna])
        #         self._results.node[name] = df2
        #     dfla = pd.DataFrame(np.nan * np.zeros([len(index), nlinks]), index=index, columns=self._results.link['flowrate'].columns)
        #     for _, _, name, _ in self._link_attributes:
        #         df2 = pd.concat([self._results.link[name], dfla])
        #         self._results.link[name] = df2
        # if len(self._temp_index) == 1:
        #     self._temp_index = self._temp_index[0]
        for _, _, name, f in self._node_attributes:
            df2 = np.array(self._temp_node_report_lines[name])
            # logger.info('Size of df2: {}'.format(df2.shape))
            if f is not None:
                df2 = f(self._flow_units, df2, mass_units=self._mass_units)
            self._results.node[name] = pd.DataFrame(
                df2, index=self._temp_index, columns=self._wn.node_name_list
            )  # .loc[self._temp_index, :] = df2
            self._temp_node_report_lines[name] = list()
        for _, _, name, f in self._link_attributes:
            df2 = np.array(self._temp_link_report_lines[name])
            if f is not None:
                df2 = f(self._flow_units, df2, mass_units=self._mass_units)
            self._results.link[name] = pd.DataFrame(
                df2, index=self._temp_index, columns=self._wn.link_name_list
            )  # .loc[self._temp_index, :] = df2
            self._temp_link_report_lines[name] = list()
        self._temp_index = list()

    def _setup_results_object(self, results_size):
        results_size = 1
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
                self._report_start + 1 + (results_size) * self._report_timestep,
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

    def _setup_overrides(self):
        require_override = set()
        for key, ctrl in self._wn.controls():
            for obj in ctrl.requires():
                if isinstance(obj, Link):
                    require_override.add(obj)
        numctrls = self._en.ENgetcount(EN.CONTROLCOUNT)
        link_indexes = dict()
        for link in require_override:
            link_name = link.name
            link_num = self._en.ENgetlinkindex(link_name)
            link_indexes[link_num] = link_name
            self._overrides[link_name] = list()
        for i in range(1, numctrls + 1):
            self.logger.info("Control {}".format(i))
            ctrl_data = self._en.ENgetcontrol(i)
            self.logger.info("Control data {}".format(ctrl_data))
            # print('Control data {} = {}'.format(i, ctrl_data))
            if ctrl_data["linkindex"] not in link_indexes:
                warnings.warn("Found a control that isn' in the water network model!")
            link_name = link_indexes[ctrl_data["linkindex"]]
            self._overrides[link_name].append(ctrl_data)

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

    def __enter__(self):
        self.initialize(self._file_prefix, self._version, self._save_hyd, self._use_hyd, self._hydfile)
        return self

    def initialize(
        self,
        file_prefix: str = "temp",
        version=2.2,
        save_hyd=False,
        use_hyd=False,
        hydfile=None,
        estimated_results_size=None,
    ):
        # TODO: change chunk size to 1 day in report steps, only input is estimated number of days in simulation.
        # TODO: initial chunks based on wn.options.time.duration (in days), change the name to "estimated_days_in_simulation"
        """
        _summary_

        Parameters
        ----------
        file_prefix : str, optional
            _description_, by default "temp"
        version : float, optional
            _description_, by default 2.2
        estimated_results_size : int, optional
            initial days of results to create in memory, by default None, which will set it to
            the number of days in the WaterNetworkModel's options.time.duration value.

        .. warning::

            **Adding chunks is slow,** if you know the number of results rows you will need, it is far better to start
            with that many rows: initial_rows = chunk_size * initial_chunks. Additional results by appending chunk_size rows at a time.


        Raises
        ------
        SimulatorError
            _description_
        """
        if self._en is not None:
            raise SimulatorError(self.__class__.__name__ + " already initialized")
        inpfile = file_prefix + ".inp"
        enData = wntr.epanet.toolkit.ENepanet(version=version)
        orig_duration = self._wn.options.time.duration
        if self._max_duration is None:
            self._max_duration = int(2**30)
        self._wn.options.time.duration = self._max_duration
        self._wn.write_inpfile(inpfile, units=self._wn.options.hydraulic.inpfile_units, version=version)
        rptfile = file_prefix + ".rpt"
        outfile = file_prefix + ".bin"
        self.outfile = outfile
        enData.ENopen(inpfile, rptfile, outfile)
        self._wn.options.time.duration = orig_duration
        self._en = enData
        self._flow_units = FlowUnits(self._en.ENgetflowunits())
        self._mass_units = MassUnits.mg
        self._chunk_size = int(np.ceil(86400 / self._wn.options.time.report_timestep))
        initial_chunks = estimated_results_size if estimated_results_size is not None else orig_duration // 86400 + 1

        if self._max_duration is None:
            enData.ENsettimeparam(EN.DURATION, self._max_duration)
        self._t = 0
        self._report_timestep = enData.ENgettimeparam(EN.REPORTSTEP)
        self._report_start = enData.ENgettimeparam(EN.REPORTSTART)
        self._last_line_added = -1
        self._setup_overrides()
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

        self._setup_results_object(initial_chunks * self._chunk_size)
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
        self._duration = orig_duration
        self._delta_t = enData.ENgettimeparam(EN.REPORTSTEP)
        # Load initial time-0 results into results (if reporting)
        self._save_report_step()  # saves on internal temp results lists
        # Load initial time-0 results into intermediate sensors
        self._save_intermediate_values()  # stores on WaterNetworkModel
        self._t = enData.ENgettimeparam(EN.HTIME)
        tstep = enData.ENnextH()
        self._tstep = tstep
        qstep = enData.ENnextQ()
        self._nt = self._t + tstep
        self._copy_results_object()
        logger.debug("Initialized stepwise run")

    def __iter__(self):
        return self

    def __next__(self):
        # self.logger.debug("Next time {}, next stop {}, duration {}", self.next_time, self._next_stop_time, self._duration)
        if (self.next_time > self._duration) or self.next_time <= 0 or self._tstep <= 0:
            raise StopIteration
        self._tstep, conditions = self._step()
        self._copy_results_object()
        return len(conditions) > 0, conditions

    def _step(self):
        enData = self._en
        completed = True
        conditions = list()
        if enData is None:
            raise SimulatorError(self.__class__.__name__ + " not initialized before use")
        self._wn._prev_sim_time = self._t
        enData.ENrunH()
        enData.ENrunQ()
        self._wn.sim_time = enData.ENgettimeparam(EN.HTIME)

        # Read all sensors in the _node and _link sensors list
        self._save_intermediate_values()
        self._save_report_step()
        logger.debug("Ran 1 step")

        # Check on stop criteria
        conditions = self._stop_criteria.check()
        # if len(conditions) > 0:
        #     # enData.ENsettimeparam(EN.DURATION, enData.ENgettimeparam(EN.HTIME))
        #     completed = False

        self._t = enData.ENgettimeparam(EN.HTIME)
        # Move EPANET forward in time
        tstep = enData.ENnextH()
        qstep = enData.ENnextQ()

        self._nt = self._t + tstep

        # if tstep < 1, duration has been reached
        return tstep, conditions

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
            tstep, conditions = self._step()
            if len(conditions) > 0:
                completetd = False

            # if tstep < 1, duration has been reached
            if tstep <= 0 or self._t > self._next_stop_time:
                self._save_report_step()
                break

            if len(conditions) > 0:
                break

            # Update time

        self._copy_results_object()
        return completed, conditions

    def __exit__(self, type, value, traceback):
        res = self.close()

    def close(self):
        enData = self._en
        if enData is None:
            raise SimulatorError(self.__class__.__name__ + " not initialized before use")
        tstep = 1
        self.set_next_stop_time(self.next_time)
        self._en.ENsettimeparam(EN.DURATION, self.next_time)
        while tstep > 0:
            enData.ENrunH()
            enData.ENrunQ()
            tstep = enData.ENnextH()
            qstep = enData.ENnextQ()
            self._save_report_step()
            self._nt = self._t + tstep
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
        for _, _, name, _ in self._node_attributes:
            df2 = self._results.node[name]
            mask = df2.index <= self._nt
            df2 = df2.loc[mask, :]
            self._results.node[name] = df2
        for _, _, name, _ in self._link_attributes:
            df2 = self._results.link[name]
            mask = df2.index <= self._nt
            df2 = df2.loc[mask, :]
            self._results.link[name] = df2
        return self._results
