# coding: utf-8
"""
The wntr.msx.options module includes options for multi-species water quality
models
"""

import logging
from typing import Dict, List, Literal, Union

from wntr.network.options import _OptionsBase

logger = logging.getLogger(__name__)


class MsxReportOptions(_OptionsBase):
    """
    Report options

    Parameters
    ----------
    report_filename : str
        Filename for the EPANET-MSX report file, by default this will be
        the prefix plus ".rpt".
    species : dict[str, bool]
        Output species concentrations
    species_precision : dict[str, float]
        Output species concentrations with the specified precision
    nodes : None, "ALL", or list
        Output node information. If a list of node names is provided,
        EPANET-MSX only provides report information for those nodes.
    links : None, "ALL", or list
        Output link information. If a list of link names is provided,
        EPANET-MSX only provides report information for those links.
    pagesize : str
        Page size for EPANET-MSX report output

    """

    def __init__(
        self,
        pagesize: list = None,
        report_filename: str = None,
        species: Dict[str, bool] = None,
        species_precision: Dict[str, float] = None,
        nodes: Union[Literal["ALL"], List[str]] = None,
        links: Union[Literal["ALL"], List[str]] = None,
    ):
        self.pagesize = pagesize
        """Pagesize for the report"""
        self.report_filename = report_filename
        """Prefix of the report filename (will add .rpt)"""
        self.species = species if species is not None else dict()
        """Turn individual species outputs on and off, by default no species are output"""
        self.species_precision = species_precision if species_precision is not None else dict()
        """Output precision for the concentration of a specific species"""
        self.nodes = nodes
        """List of nodes to print output for, or 'ALL' for all nodes, by default None"""
        self.links = links
        """List of links to print output for, or 'ALL' for all links, by default None"""

    def __setattr__(self, name, value):
        if name not in ["pagesize", "report_filename", "species", "nodes", "links", "species_precision"]:
            raise AttributeError("%s is not a valid attribute of ReportOptions" % name)
        self.__dict__[name] = value


class MsxSolverOptions(_OptionsBase):
    """
    Solver options

    Parameters
    ----------
    timestep : int >= 1
        Water quality timestep (seconds), by default 60 (one minute).
    area_units : str, optional
        Units of area to use in surface concentration forms, by default
        ``M2``. Valid values are ``FT2``, ``M2``, or ``CM2``.
    rate_units : str, optional
        Time units to use in all rate reactions, by default ``MIN``. Valid
        values are ``SEC``, ``MIN``, ``HR``, or ``DAY``.
    solver : str, optional
        Solver to use, by default ``RK5``. Options are ``RK5`` (5th order
        Runge-Kutta method), ``ROS2`` (2nd order Rosenbrock method), or
        ``EUL`` (Euler method).
    coupling : str, optional
        Use coupling method for solution, by default ``NONE``. Valid
        options are ``FULL`` or ``NONE``.
    atol : float, optional
        Absolute concentration tolerance, by default 0.01 (regardless of
        species concentration units).
    rtol : float, optional
        Relative concentration tolerance, by default 0.001 (±0.1%).
    compiler : str, optional
        Whether to use a compiler, by default ``NONE``. Valid options are
        ``VC``, ``GC``, or ``NONE``
    segments : int, optional
        Maximum number of segments per pipe (MSX 2.0 or newer only), by
        default 5000.
    peclet : int, optional
        Peclet threshold for applying dispersion (MSX 2.0 or newer only),
        by default 1000.
    report : MsxReportOptions or dict
        Options on how to report out results.

    """

    def __init__(
        self,
        timestep: int = 360,
        area_units: str = "M2",
        rate_units: str = "MIN",
        solver: str = "RK5",
        coupling: str = "NONE",
        atol: float = 1.0e-4,
        rtol: float = 1.0e-4,
        compiler: str = "NONE",
        segments: int = 5000,
        peclet: int = 1000,
        # global_initial_quality: Dict[str, float] = None,
        report: MsxReportOptions = None,
    ):
        self.timestep: int = timestep
        """Timestep, in seconds, by default 360"""
        self.area_units: str = area_units
        """Units used to express pipe wall surface area where, by default FT2.
        Valid values are FT2, M2, and CM2."""
        self.rate_units: str = rate_units
        """Units in which all reaction rate terms are expressed, by default HR.
        Valid values are HR, MIN, SEC, and DAY."""
        self.solver: str = solver
        """Solver to use, by default EUL. Valid values are EUL, RK5, and
        ROS2."""
        self.coupling: str = coupling
        """Whether coupling should occur during solving, by default NONE. Valid
        values are NONE and FULL."""
        self.rtol: float = rtol
        """Relative tolerance used during solvers ROS2 and RK5, by default
        0.001 for all species. Can be overridden on a per-species basis."""
        self.atol: float = atol
        """Absolute tolerance used by the solvers, by default 0.01 for all
        species regardless of concentration units. Can be overridden on a
        per-species basis."""
        self.compiler: str = compiler
        """Compiler to use if the equations should be compiled by EPANET-MSX,
        by default NONE. Valid options are VC, GC and NONE."""
        self.segments: int = segments
        """Number of segments per-pipe to use, by default 5000."""
        self.peclet: int = peclet
        """Threshold for applying dispersion, by default 1000."""
        self.report: MsxReportOptions = MsxReportOptions.factory(report)
        """Reporting output options."""

    def __setattr__(self, name, value):
        if name == "report":
            if not isinstance(value, (MsxReportOptions, dict, tuple, list)):
                raise ValueError("report must be a ReportOptions or convertable object")
            value = MsxReportOptions.factory(value)
        elif name in {"timestep"}:
            try:
                value = max(1, int(value))
            except ValueError:
                raise ValueError("%s must be an integer >= 1" % name)
        elif name in ["atol", "rtol"]:
            try:
                value = float(value)
            except ValueError:
                raise ValueError("%s must be a number", name)
        elif name in ["segments", "peclet"]:
            try:
                value = int(value)
            except ValueError:
                raise ValueError("%s must be a number", name)
        elif name not in ["area_units", "rate_units", "solver", "coupling", "compiler"]:
            raise ValueError("%s is not a valid member of MsxSolverOptions")
        self.__dict__[name] = value

    def to_dict(self):
        """Dictionary representation of the options"""
        return dict(self)
