"""The EPANET simulator."""

import enum
from typing import Literal
import numpy as np
import pandas as pd
from wntr.network.base import Link, Node
from wntr.network.controls import StopControl, StopCriteria
from wntr.network.model import WaterNetworkModel
from wntr.sim.core import WaterNetworkSimulator
from wntr.network.io import write_inpfile
from wntr.epanet.util import EN, HydParam, MassUnits, FlowUnits, QualParam, to_si
import wntr.epanet.toolkit as _tk
import wntr.epanet
import warnings
import logging

from wntr.sim.results import SimulationResults

logger = logging.getLogger(__name__)

try:
    import wntr.epanet.toolkit
except ImportError as e:
    print("{}".format(e))
    logger.critical("%s", e)
    raise ImportError(
        "Error importing epanet toolkit while running epanet simulator. "
        "Make sure libepanet is installed and added to path."
    )


class EpanetSimulator(WaterNetworkSimulator):
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


    .. note::

        WNTR now includes access to both the EPANET 2.0.12 and EPANET 2.2 toolkit libraries.
        By default, version 2.2 will be used.


    Parameters
    ----------
    wn : WaterNetworkModel
        Water network model
    reader : wntr.epanet.io.BinFile (derived object)
        Defaults to None, which will create a new wntr.epanet.io.BinFile object with
        the results_types specified as an init option. Otherwise, a fully
    result_types : dict
        Defaults to None, or all results. Otherwise, is a keyword dictionary to pass to
        the reader to specify what results should be saved.


    .. seealso::

        :class:`~wntr.epanet.io.BinFile`

    """

    def __init__(self, wn, reader=None, result_types=None):
        WaterNetworkSimulator.__init__(self, wn)
        self._wn: WaterNetworkModel = wn
        self.reader = reader
        self.prep_time_before_main_loop = 0.0
        if self.reader is None:
            self.reader = wntr.epanet.io.BinFile(result_types=result_types)
        # options requirements for __enter__, __next__, __exit__ methods
        self._file_prefix = None
        self._version = None
        self._save_hyd = None
        self._use_hyd = None
        self._hydfile = None
        self._maximum_duration = None
        self._convergence_error = None
        self._estimated_results_size = None
        self._tk: wntr.epanet.toolkit.ENepanet = None
        self._t: int = 0
        self._t_next: int = 0
        self._results: SimulationResults = None
        self._link_sensors = dict()
        self._node_sensors = dict()
        self._temp_index = list()
        self._temp_link_report_lines = dict()
        self._temp_node_report_lines = dict()
        self._next_stop_time: int = None
        self._overrides = dict()
        self._duration = None
        self._stop_criteria = None

    def run_sim(
        self,
        file_prefix="temp",
        save_hyd=False,
        use_hyd=False,
        hydfile=None,
        version=2.2,
        convergence_error=False,
    ):
        """
        Run the EPANET simulator.

        Runs the EPANET simulator through the compiled toolkit DLL. Can use/save hydraulics
        to allow for separate WQ runs.

        .. note::

            By default, WNTR now uses the EPANET 2.2 toolkit as the engine for the EpanetSimulator.
            To force usage of the older EPANET 2.0 toolkit, use the ``version`` command line option.
            Note that if the demand_model option is set to PDD, then a warning will be issued, as
            EPANET 2.0 does not support such analysis.


        Parameters
        ----------
        file_prefix : str
            Default prefix is "temp". All files (.inp, .bin/.out, .hyd, .rpt) use this prefix
        use_hyd : bool
            Will load hydraulics from ``file_prefix + '.hyd'`` or from file specified in `hydfile_name`
        save_hyd : bool
            Will save hydraulics to ``file_prefix + '.hyd'`` or to file specified in `hydfile_name`
        hydfile : str
            Optionally specify a filename for the hydraulics file other than the `file_prefix`
        version : float
            {2.0, **2.2**} Optionally change the version of the EPANET toolkit libraries. Valid choices are
            either 2.2 (the default if no argument provided) or 2.0.
        convergence_error: bool (optional)
            If convergence_error is True, an error will be raised if the
            simulation does not converge. If convergence_error is False, partial results are returned,
            a warning will be issued, and results.error_code will be set to 0
            if the simulation does not converge.  Default = False.
        """
        if isinstance(version, str):
            version = float(version)
        inpfile = file_prefix + ".inp"
        if version == 2.2 and self._version is not None:
            version = float(self._version)
        if file_prefix == "temp" and self._file_prefix is not None:
            file_prefix = self._file_prefix
        if not save_hyd and self._save_hyd is not None:
            save_hyd = self._save_hyd
        if not use_hyd and self._save_hyd is not None:
            use_hyd = self._use_hyd
        if hydfile is None and self._save_hyd is not None:
            hydfile = self._hydfile
        if not convergence_error and self._convergence_error is not None:
            convergence_error = self._convergence_error

        write_inpfile(
            self._wn,
            inpfile,
            units=self._wn.options.hydraulic.inpfile_units,
            version=version,
        )
        epanet = wntr.epanet.toolkit.ENepanet(version=version)
        rptfile = file_prefix + ".rpt"
        outfile = file_prefix + ".bin"
        if self._wn._msx is not None:
            save_hyd = True
        if hydfile is None:
            hydfile = file_prefix + ".hyd"
        epanet.ENopen(inpfile, rptfile, outfile)
        if use_hyd:
            epanet.ENusehydfile(hydfile)
            logger.debug("Loaded hydraulics")
        else:
            epanet.ENsolveH()
            logger.debug("Solved hydraulics")
        if save_hyd:
            epanet.ENsavehydfile(hydfile)
            logger.debug("Saved hydraulics")
        epanet.ENsolveQ()
        logger.debug("Solved quality")
        epanet.ENreport()
        logger.debug("Ran quality")
        epanet.ENclose()
        logger.debug("Completed run")
        # os.sys.stderr.write('Finished Closing\n')

        results = self.reader.read(
            outfile, convergence_error, self._wn.options.hydraulic.headloss == "D-W"
        )

        if self._wn._msx is not None:
            # Attributed to Matthew's package
            msxfile = file_prefix + ".msx"
            rptfile = file_prefix + ".msx-rpt"
            binfile = file_prefix + ".msx-bin"
            msxfile2 = file_prefix + ".check.msx"
            wntr.epanet.msx.io.MsxFile.write(msxfile, self._wn._msx)
            msx = wntr.epanet.msx.MSXepanet(inpfile, rptfile, outfile, msxfile)
            msx.ENopen(inpfile, rptfile, outfile)
            msx.MSXopen(msxfile)
            msx.MSXusehydfile(hydfile)
            msx.MSXinit()
            msx.MSXsolveH()
            msx.MSXsolveQ()
            msx.MSXreport()
            msx.MSXsaveoutfile(binfile)
            msx.MSXsavemsxfile(msxfile2)
            msx.MSXclose()
            msx.ENclose()
            results = wntr.epanet.msx.io.MsxBinFile(binfile, self._wn, results)

        return results


class StepwiseEpanetSimulator(WaterNetworkSimulator):

    def __init__(self):
        self._wn: WaterNetworkModel = None
        self.mode = None
        self.reader = None
        self.prep_time_before_main_loop = 0.0
        if self.reader is None:
            self.reader = wntr.epanet.io.BinFile(result_types=None)
        self._epanet: wntr.epanet.toolkit.ENepanet = None
        self._dt: int = 1
        self._t: int = 0
        self._t_next: int = 0
        self._T_break: int = None
        self._T_duration = None
        self._T_maximum = None
        self._results: SimulationResults = None
        self._file_prefix = None
        self._version = None
        self._save_hyd = None
        self._use_hyd = None
        self._hydfile = None
        self._convergence_error = None
        self._estimated_results_size = None
        self._link_sensors = dict()
        self._node_sensors = dict()
        self._temp_index = list()
        self._temp_link_report_lines = dict()
        self._temp_node_report_lines = dict()
        self._overrides = dict()
        self._stop_criteria = None
        self._version = 2.2
        self._node_attributes = [
            (_tk.NodeParam.QUALITY, "_quality", "quality", QualParam.Quality),
            (_tk.NodeParam.DEMAND, "_demand", "demand", HydParam.Demand),
            (_tk.NodeParam.HEAD, "_head", "head", HydParam.HydraulicHead),
            (_tk.NodeParam.PRESSURE, "_pressure", "pressure", HydParam.Pressure),
        ]
        self._link_attributes = [
            (
                _tk.LinkParam.LINKQUAL,
                "_quality",
                "quality",
                QualParam.LinkQuality,
            ),
            (_tk.LinkParam.FLOW, "_flow", "flowrate", HydParam.Flow),
            (_tk.LinkParam.VELOCITY, "_velocity", "velocity", HydParam.Velocity),
            (_tk.LinkParam.HEADLOSS, "_headloss", "headloss", HydParam.HeadLoss),
            (_tk.LinkParam.STATUS, "_user_status", "status", None),
            (_tk.LinkParam.SETTING, "_setting", "setting", None),
        ]
        self.logger = logger

    def toolkit(self) -> wntr.epanet.toolkit.ENepanet:
        """Get direct access to the toolkit object; use with care."""
        return self._epanet

    def run_sim(self):
        raise RuntimeWarning(
            "Please use the `with ... as ...:` syntax with the context managed simulator."
        )

    def open(
        self,
        wn,
        file_prefix: str = "temp",
        save_hyd=False,
        use_hyd=False,
        hydfile=None,
        convergence_error=False,
        maximum_duration=None,
        estimated_results_size=None,
        stop_criteria: StopCriteria = None,
    ) -> "StepwiseEpanetSimulator":
        """
        Create a new context-managed EPANET v2.2 simulator. This simulator must be used
        with the `with ... as ...` context-management paradigm.

        Parameters
        ----------
        wn : WaterNetworkModel
            The water network model to use.
        file_prefix : str
            The prefix for output files, by default 'temp'.
        save_hyd : bool
            Set to True to save the hydraulics, by default False.
        use_hyd : bool
            Set to True to use previous hydraulics, by default False.
        hydfile : str
            Set the name of the hydraulics file to save or use, by default None.
        convergence_error : bool
            Set to True to ***** convergence errors, by default False.
        maximum_duration : int
            To continue "forever", use a value of -1, otherwise, give a maximum duration
            (in seconds) for the simulation; by default None which uses ``wn.options.time.duration``.
        estimated_results_size : int
            An estimated number of results lines to capture, by default None which means to
            estimate from the duration and report step.
        stop_criteria : StopCriteria
            Simulation termination criteria that are not EPANET standard, by default None.


        Returns
        -------
        ContextManagedEpanetSimulator
            a new context managed EPANET simulator


        Examples
        --------
        .. code::

            wn = wntr.network.io.read_inpfile('somefile.inp')
            with wntr.sim.epanet.simulate(wn) as sim:
                for step in sim:
                    pass
                res = sim.get_results()

        """
        if self._epanet is not None:
            raise RuntimeError(self.__class__.__name__ + " already initialized")
        self._wn = wn
        self._file_prefix = file_prefix
        self._save_hyd = save_hyd
        self._use_hyd = use_hyd
        self._hydfile = hydfile
        self._version = 2.2
        self._T_maximum = maximum_duration
        self._convergence_error = convergence_error
        self._estimated_results_size = estimated_results_size
        self._stop_criteria = (
            stop_criteria if stop_criteria is not None else StopCriteria()
        )
        return self

    def __enter__(self):
        if self._epanet is not None:
            raise RuntimeError(self.__class__.__name__ + " already initialized")
        self._T_duration = self._wn.options.time.duration
        version = 2.2
        file_prefix = self._file_prefix if self._file_prefix is not None else "temp"
        estimated_results_size = self._estimated_results_size
        inpfile = file_prefix + ".inp"
        epanet = wntr.epanet.toolkit.ENepanet(version=version)
        orig_duration = self._wn.options.time.duration
        if self._T_maximum is None:
            self._T_maximum = orig_duration
        if self._T_maximum < 1:
            self._T_maximum = int(2**30)
        self._wn.options.time.duration = self._T_maximum
        wntr.network.io.write_inpfile(
            self._wn,
            inpfile,
            units=self._wn.options.hydraulic.inpfile_units,
            version=version,
        )
        rptfile = file_prefix + ".rpt"
        outfile = file_prefix + ".bin"
        self.outfile = outfile
        epanet.ENopen(inpfile, rptfile, outfile)
        self._wn.options.time.duration = orig_duration
        self._epanet = epanet
        self._flow_units = FlowUnits(self._epanet.ENgetflowunits())
        self._mass_units = MassUnits.mg
        self._chunk_size = int(np.ceil(86400 / self._wn.options.time.report_timestep))
        initial_chunks = (
            estimated_results_size
            if estimated_results_size is not None
            else orig_duration // 86400 + 1
        )

        if self._T_maximum is None:
            epanet.ENsettimeparam(_tk.TimeParam.DURATION, self._T_maximum)
        self._t = 0
        self._report_timestep = epanet.ENgettimeparam(_tk.TimeParam.REPORTSTEP)
        self._report_start = epanet.ENgettimeparam(_tk.TimeParam.REPORTSTART)
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
                    QualParam.Concentration,
                )
                self._link_attributes[0] = (
                    self._link_attributes[0][0],
                    self._link_attributes[0][1],
                    self._link_attributes[0][2],
                    QualParam.Concentration,
                )
            elif self._wn.options.quality.parameter.upper() == "AGE":
                self._node_attributes[0] = (
                    self._node_attributes[0][0],
                    self._node_attributes[0][1],
                    self._node_attributes[0][2],
                    QualParam.WaterAge,
                )
                self._link_attributes[0] = (
                    self._link_attributes[0][0],
                    self._link_attributes[0][1],
                    self._link_attributes[0][2],
                    QualParam.WaterAge,
                )

        self._setup_results_object(initial_chunks * self._chunk_size)
        # setup intermediate sensors indices from names to internal EPANET numbers
        new_link_sensors = dict()
        new_node_sensors = dict()
        for name, vals in self._link_sensors.items():
            wn_name, attr = name
            en_idx = epanet.ENgetlinkindex(wn_name)
            if attr == _tk.LinkParam.LINKQUAL:
                vals = (vals[0], vals[1], self._link_sensors[0][-1])
            new_link_sensors[(en_idx, attr)] = vals
        for name, vals in self._node_sensors.items():
            wn_name, attr = name
            en_idx = epanet.ENgetnodeindex(wn_name)
            if attr == _tk.NodeParam.QUALITY:
                vals = (vals[0], vals[1], self._node_sensors[0][-1])
            new_node_sensors[(en_idx, attr)] = vals
        self._link_sensors = new_link_sensors
        self._node_sensors = new_node_sensors
        if self._T_break is None:
            self._T_break = self._T_maximum
        epanet.ENopenH()
        epanet.ENinitH(1)
        epanet.ENopenQ()
        epanet.ENinitQ(1)
        epanet.ENrunH()
        epanet.ENrunQ()
        self._T_duration = orig_duration
        self._dt = epanet.ENgettimeparam(_tk.TimeParam.REPORTSTEP)
        # # Load initial time-0 results into results (if reporting)
        self._save_report_step()  # saves on internal temp results lists
        # # Load initial time-0 results into intermediate sensors
        self._save_intermediate_values()  # stores on WaterNetworkModel
        self._t = epanet.ENgettimeparam(_tk.TimeParam.HTIME)
        tstep = epanet.ENnextH()
        self._tstep = tstep
        qstep = epanet.ENnextQ()
        self._t_next = self._t + tstep
        self._copy_results_object()
        logger.debug("Initialized stepwise run")
        return self

    def __iter__(self):
        return self

    def __next__(self):
        # self.logger.debug("Next time {}, next stop {}, duration {}", self.next_time, self._next_stop_time, self._duration)
        if (self.next_time > self._T_duration) or self.next_time <= 0 or self._tstep <= 0:
            raise StopIteration
        return self.step()

    def step(self):
        epanet = self._epanet
        completed = True
        conditions = []
        if epanet is None:
            raise RuntimeError(self.__class__.__name__ + " not initialized before use")
        self._wn._prev_sim_time = self._t
        epanet.ENrunH()
        epanet.ENrunQ()
        self._wn.sim_time = epanet.ENgettimeparam(_tk.TimeParam.HTIME)

        # Read all sensors in the _node and _link sensors list
        self._save_intermediate_values()
        self._save_report_step()
        logger.debug("Ran 1 step")

        # Check on stop criteria
        conditions = self._stop_criteria.check()
        # if len(conditions) > 0:
        #     # enData.ENsettimeparam(_tk.TimeParam.DURATION, enData.ENgettimeparam(_tk.TimeParam.HTIME))
        #     completed = False

        self._t = epanet.ENgettimeparam(_tk.TimeParam.HTIME)
        # Move EPANET forward in time
        t_hyd = epanet.ENnextH()
        t_qual = epanet.ENnextQ()
        while (t_hyd < 1 and t_qual >= 1) or t_qual < t_hyd:
            epanet.ENrunQ()
            t_qual = epanet.ENnextQ()

        self._t_next = self._t + t_hyd
        self._copy_results_object()
        return len(conditions) > 0, conditions

    def continue_run(self):
        stop, cond = self.step()
        while len(cond) < 1 and self._T_break > self.current_time:
            stop, cond = self.step()
        if self._T_break <= self.current_time:
            self.set_breakpoint(self._T_maximum)
        return len(cond)>0, cond

    def __exit__(self, type, value, traceback):
        epanet = self._epanet
        if epanet is None:
            raise RuntimeError(self.__class__.__name__ + " not initialized before use")
        if self.current_time < self._T_maximum:
            self.set_breakpoint(self.current_time)
            self._epanet.ENsettimeparam(_tk.TimeParam.DURATION, self.current_time)
        epanet.ENcloseH()
        epanet.ENcloseQ()
        epanet.ENreport()
        epanet.ENclose()
        logger.debug("Completed step run")
        self._epanet = None
        # results = wntr.epanet.io.BinFile().read(self.outfile)
        return self.get_results()

    @property
    def current_time(self):
        """int: the last time solved (read-only, in seconds)"""
        return self._t

    @property
    def next_time(self):
        """int: the next time to be solved (read-only, in secconds)"""
        return self._epanet.ENgettimeparam(_tk.TimeParam.HTIME)

    @property
    def duration(self):
        """int: the duration of the simulation, i.e. when to stop taking steps"""
        return self._T_duration

    @duration.setter
    def duration(self, seconds):
        self._T_duration = seconds

    @property
    def step_size(self):
        """int: the duration of the next step, which may be several hydraulic, waterquality or report steps"""
        return self._dt

    @step_size.setter
    def step_size(self, seconds):
        self._dt = seconds

    def get_results(self):
        """list: get any results (at report steps) that have been collected since the last step"""
        results = wntr.sim.SimulationResults()
        results.node = dict()
        results.link = dict()
        for _, _, name, _ in self._node_attributes:
            df2 = self._results.node[name]
            index = np.reshape(df2['index'], -1)
            results.node[name] = pd.DataFrame(data=np.reshape(df2['data'],(len(index),-1)), columns=df2['columns'], index=index)
        for _, _, name, _ in self._link_attributes:
            df2 = self._results.link[name]
            index = np.reshape(df2['index'], -1)
            results.link[name] = pd.DataFrame(data=np.reshape(df2['data'],(len(index),-1)), columns=df2['columns'], index=index)
        return results

    def add_stop_criterion(self, control: StopControl):
        """Add a stop criterion for this simulator

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

    def remove_stop_criterion(self, control):
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

    def get_node_value(self, node_name: str, attribute) -> float:
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
            value

        Raises
        ------
        RuntimeError
            if the simulation has not been initialized
        """
        if self._epanet is not None:
            node_id = self._epanet.ENgetnodeindex(node_name)
            if isinstance(attribute, (EN, int)):
                return self._epanet.ENgetnodevalue(node_id, attribute)
            else:
                return self._epanet.ENgetnodevalue(node_id, EN[attribute.upper()])
        else:
            msg = "The simulator has not been initialized"
            logger.error(msg)
            raise RuntimeError(msg)

    def get_link_value(self, link_name: str, attribute: str) -> float:
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
            value

        Raises
        ------
        RuntimeError
            if the simulation has not been initialized
        """
        if self._epanet is not None:
            link_id = self._epanet.ENgetlinkindex(link_name)
            if isinstance(attribute, (EN, int)):
                return self._epanet.ENgetlinkvalue(link_id, attribute)
            elif isinstance(attribute, str) and attribute.upper() == "QUALITY":
                return self._epanet.ENgetlinkvalue(link_id, _tk.LinkParam.LINKQUAL)
            else:
                return self._epanet.ENgetlinkvalue(
                    link_id, _tk.LinkParam[attribute.upper()]
                )
        else:
            msg = "The simulator has not been initialized"
            logger.error(msg)
            raise RuntimeError(msg)

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
        if self._epanet is not None:
            node_id = self._epanet.ENgetnodeindex(node_name)
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
        if self._epanet is not None:
            link_id = self._epanet.ENgetlinkindex(link_name)
        else:
            link_id = link_name
        for attr, aname, _, f in self._link_attributes:
            if attr == _tk.LinkParam.SETTING:
                if link.link_type == "Pipe":
                    f = HydParam.RoughnessCoeff
                elif link.link_type == "Valve":
                    if link.valve_type in ["PRV", "PSV", "PBV"]:
                        f = HydParam.Pressure
                    elif link.valve_type == "FCV":
                        f = HydParam.Flow
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
        RuntimeWarning
            if the sensor cannot be removed because it is required by a stop criterion.
            The stop criterion must be removed first.
        """
        node = self._wn.get_node(node_name)
        if self._epanet is not None:
            node_id = self._epanet.ENgetnodeindex(node_name)
        else:
            node_id = node_name
        if node in self._stop_criteria.requires():
            a = RuntimeWarning(
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
        RuntimeWarning
            if the sensor cannot be removed because it is required by a stop criterion.
            The stop criterion must be removed first.
        """
        link = self._wn.get_link(link_name)
        if self._epanet is not None:
            link_id = self._epanet.ENgetlinkindex(link_name)
        else:
            link_id = link_name
        if link in self._stop_criteria.requires():
            a = RuntimeWarning(
                "You cannot remove a link sensor that is required by stop criteria - action is ignored"
            )
            warnings.warn(a)
        else:
            for attr, _, _, _ in self._link_attributes:
                self._link_sensors.pop((link_id, attr))

    def set_hydraulic_timestep(self, dt_hyd: int) -> int:
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
        RuntimeError
            if the simulation has not been initialized
        """
        if self._epanet is None:
            a = RuntimeError("The simulation has not been initialized")
            logger.error(a)
            raise a
        self._epanet.ENsettimeparam(_tk.TimeParam.HYDSTEP, dt_hyd)
        return self._epanet.ENgettimeparam(_tk.TimeParam.HYDSTEP)

    def set_breakpoint(self, sim_time: int) -> int:
        """
        Set the next time when the :func:`continue` call will stop

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
        if sim_time is None:
            self._T_break = None
            return
        if self._epanet is None:
            w = RuntimeError("The simulation has not been initialized")
            logger.error(w)
            raise w
        elif self._t > sim_time:
            w = RuntimeWarning(
                "Current simulation has passed time {} (current is {})".format(
                    sim_time, self._t
                )
            )
            warnings.warn(w)
            return self._t  # self._en.ENgettimeparam(_tk.TimeParam.DURATION)
        elif self._t == sim_time:
            w = RuntimeWarning("The simulation is already at time {}".format(sim_time))
            warnings.warn(w)
            return self._t  # self._en.ENgettimeparam(_tk.TimeParam.DURATION)
        else:
            self._T_break = sim_time
            # self._en.ENsettimeparam(_tk.TimeParam.DURATION, seconds)
            return (
                self._T_break
            )  # self._en.ENgettimeparam(_tk.TimeParam.DURATION)

    def set_link_status(self, link_name: str, value: float, override=True):
        if self._epanet is None:
            w = RuntimeError("The simulation has not been initialized")
            logger.error(w)
            raise w
        link_num = self._epanet.ENgetlinkindex(link_name)
        self._epanet.ENsetlinkvalue(link_num, _tk.LinkParam.STATUS, value)
        if link_name in self._overrides and override:
            # FIXME: handle overrides
            controls = self._overrides[link_name]
            for ctrl_data in controls:
                self._epanet.ENsetcontrol(
                    ctrl_data["index"],
                    ctrl_data["type"],
                    ctrl_data["linkindex"],
                    ctrl_data["setting"],
                    ctrl_data["nodeindex"],
                    (
                        1e30
                        if ctrl_data["type"] == _tk.CtrlType.HILEVEL
                        else -1e30
                    ),
                )
        else:
            w = RuntimeWarning("No override set on the specified link")
            warnings.warn(w)

    def set_link_setting(self, link_name: str, value: float, override=True):
        if self._epanet is None:
            w = RuntimeError("The simulation has not been initialized")
            logger.error(w)
            raise w
        link_num = self._epanet.ENgetlinkindex(link_name)
        self._epanet.ENsetlinkvalue(link_num, _tk.LinkParam.SETTING, value)
        if link_name in self._overrides and override:
            # FIXME: handle overrides
            controls = self._overrides[link_name]
            for ctrl_data in controls:
                self._epanet.ENsetcontrol(
                    ctrl_data["index"],
                    ctrl_data["type"],
                    ctrl_data["linkindex"],
                    ctrl_data["setting"],
                    ctrl_data["nodeindex"],
                    (
                        1e30
                        if ctrl_data["type"] == _tk.CtrlType.HILEVEL
                        else -1e30
                    ),
                )
        else:
            w = RuntimeWarning("No override set on the specified link")
            warnings.warn(w)

    def release_override(self, link_name: str):
        if self._epanet is None:
            w = RuntimeError("The simulation has not been initialized")
            logger.error(w)
            raise w
        link_num = self._epanet.ENgetlinkindex(link_name)
        if link_name in self._overrides.keys():
            # FIXME: handle overrides
            controls = self._overrides[link_name]
            for ctrl_data in controls:
                self._epanet.ENsetcontrol(
                    ctrl_data["index"],
                    ctrl_data["type"],
                    ctrl_data["linkindex"],
                    ctrl_data["setting"],
                    ctrl_data["nodeindex"],
                    ctrl_data["level"],
                )
        else:
            w = RuntimeWarning("No override set on the specified link")
            warnings.warn(w)

    def _save_report_step(self):
        t = self._epanet.ENgettimeparam(_tk.TimeParam.HTIME)
        # this is checking to make sure we are at a report step, or if past the step, but it didn't get reported, then report out.
        report_line = (
            -1
            if t < self._report_start
            else (t - self._report_start) // self._report_timestep
        )
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
                demand.append(self._epanet.ENgetnodevalue(idx, _tk.NodeParam.DEMAND))
                head.append(self._epanet.ENgetnodevalue(idx, _tk.NodeParam.HEAD))
                pressure.append(
                    self._epanet.ENgetnodevalue(idx, _tk.NodeParam.PRESSURE)
                )
                quality.append(
                    self._epanet.ENgetnodevalue(idx, _tk.NodeParam.QUALITY)
                )
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
                linkqual.append(
                    self._epanet.ENgetlinkvalue(idx, _tk.LinkParam.LINKQUAL)
                )
                flow.append(self._epanet.ENgetlinkvalue(idx, _tk.LinkParam.FLOW))
                velocity.append(
                    self._epanet.ENgetlinkvalue(idx, _tk.LinkParam.VELOCITY)
                )
                headloss.append(
                    self._epanet.ENgetlinkvalue(idx, _tk.LinkParam.HEADLOSS)
                )
                status.append(self._epanet.ENgetlinkvalue(idx, _tk.LinkParam.STATUS))
                setting.append(
                    self._epanet.ENgetlinkvalue(idx, _tk.LinkParam.SETTING)
                )
            self._temp_link_report_lines["quality"].append(linkqual)
            self._temp_link_report_lines["flowrate"].append(flow)
            self._temp_link_report_lines["velocity"].append(velocity)
            self._temp_link_report_lines["headloss"].append(headloss)
            self._temp_link_report_lines["status"].append(status)
            self._temp_link_report_lines["setting"].append(setting)

    def _copy_results_object(self):
        if len(self._temp_index) == 0:
            return
        for _, _, name, param in self._node_attributes:
            df2 = np.array(self._temp_node_report_lines[name])
            if param is not None:
                df2 = to_si(self._flow_units, df2, param, self._mass_units)
            self._results.node[name]['data'].append(df2)
            self._results.node[name]['index'].append(self._temp_index)
            self._temp_node_report_lines[name] = list()
        for _, _, name, param in self._link_attributes:
            df2 = np.array(self._temp_link_report_lines[name])
            if param is not None:
                df2 = to_si(self._flow_units, df2, param, self._mass_units)
            self._results.link[name]['data'].append(df2)
            self._results.link[name]['index'].append(self._temp_index)
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
            self._node_name_idx.append(self._epanet.ENgetnodeindex(node_name))
        for link_name in self._link_name_str:
            self._link_name_idx.append(self._epanet.ENgetlinkindex(link_name))
        for _, _, name, _ in self._node_attributes:
            self._results.node[name] = dict(
                data=list(), columns=self._node_name_str, index=list()
            )
            self._temp_node_report_lines[name] = list()
        for _, _, name, _ in self._link_attributes:
            self._results.link[name] = dict(
                data=list(), columns=self._link_name_str, index=list()
            )
            self._temp_link_report_lines[name] = list()

    def _setup_overrides(self):
        require_override = set()
        for key, ctrl in self._wn.controls():
            for obj in ctrl.requires():
                if isinstance(obj, Link):
                    require_override.add(obj)
        numctrls = self._epanet.ENgetcount(_tk.CountType.CONTROLCOUNT)
        link_indexes = dict()
        for link in require_override:
            link_name = link.name
            link_num = self._epanet.ENgetlinkindex(link_name)
            link_indexes[link_num] = link_name
            self._overrides[link_name] = list()
        for i in range(1, numctrls + 1):
            self.logger.info("Control {}".format(i))
            ctrl_data = self._epanet.ENgetcontrol(i)
            self.logger.info("Control data {}".format(ctrl_data))
            # print('Control data {} = {}'.format(i, ctrl_data))
            if ctrl_data["linkindex"] not in link_indexes:
                warnings.warn("Found a control that isn' in the water network model!")
            link_name = link_indexes[ctrl_data["linkindex"]]
            self._overrides[link_name].append(ctrl_data)

    def _save_intermediate_values(self):
        for name, vals in self._node_sensors.items():
            en_idx, at_idx = name  # (where, what) you are measuring
            node, attr, param = (
                vals  # WNTR node object, attribute name, and conversion function
            )
            value = self._epanet.ENgetnodevalue(en_idx, at_idx)
            if param is not None:
                value = to_si(
                    self._flow_units, value, param, mass_units=self._mass_units
                )
            setattr(node, attr, value)  # set the simulation value on the node object
        for name, vals in self._link_sensors.items():
            en_idx, at_idx = name
            link, attr, param = vals
            value = self._epanet.ENgetlinkvalue(en_idx, at_idx)
            if param is not None:
                value = to_si(
                    self._flow_units, value, param, mass_units=self._mass_units
                )
            setattr(link, attr, value)
