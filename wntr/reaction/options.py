import re
import logging
import copy

from wntr.network.options import _float_or_None, _int_or_None, _OptionsBase

logger = logging.getLogger(__name__)


class TimeOptions(_OptionsBase):
    """
    Options related to reaction simulation.

    Parameters
    ----------
    timestep : int >= 1
        Water quality timestep (seconds), by default 60 (one minute).

    """

    _pattern1 = re.compile(r"^(\d+):(\d+):(\d+)$")
    _pattern2 = re.compile(r"^(\d+):(\d+)$")
    _pattern3 = re.compile(r"^(\d+)$")

    def __init__(
        self,
        timestep: int = 60,
    ):
        self.timestep = timestep

    def __setattr__(self, name, value):
        if name in {"timestep"}:
            try:
                value = max(1, int(value))
            except ValueError:
                raise ValueError("%s must be an integer >= 1" % name)
        elif name not in {"timestep"}:
            raise AttributeError("%s is not a valid attribute in TimeOptions" % name)
        self.__dict__[name] = value


class QualityOptions(_OptionsBase):
    """
    Options related to water quality modeling. These options come from
    the "[OPTIONS]" section of an EPANET-MSX input file.

    Parameters
    ----------
    area_units : str, optional
        The units of area to use in surface concentration forms, by default ``M2``. Valid values are ``FT2``, ``M2``, or ``CM2``.

    rate_units : str, optional
        The timee units to use in rate reactions, by default ``MIN``. Valid values are ``SEC``, ``MIN``, ``HR``, or ``DAY``.

    solver : str, optional
        The solver to use, by default ``RK5``. Options are ``RK5`` (5th order Runge-Kutta method), ``ROS2`` (2nd order Rosenbrock method), or ``EUL`` (Euler method).

    coupling : str, optional
        Use coupling method for solution, by default ``NONE``. Valid options are ``FULL`` or ``NONE``.

    rtol : float, optional
        Relative concentration tolerance, by default 1.0e-4.

    atol : float, optional
        Absolute concentration tolerance, by default 1.0e-4.

    compiler : str, optional
        Whether to use a compiler, by default ``NONE``. Valid options are ``VC``, ``GC``, or ``NONE``

    segments : int, optional
        Maximum number of segments per pipe (MSX 2.0 or newer only), by default 5000.

    peclet : int, optional
        Peclet threshold for applying dispersion (MSX 2.0 or newer only), by default 1000.
    """

    def __init__(
        self,
        area_units: str = "M2",
        rate_units: str = "MIN",
        solver: str = "RK5",
        coupling: str = "NONE",
        rtol: float = 1.0e-4,
        atol: float = 1.0e-4,
        compiler: str = "",
        segments: int = 5000,
        peclet: int = 1000,
    ):
        self.area_units = area_units
        self.rate_units = rate_units
        self.solver = solver
        self.coupling = coupling
        self.rtol = rtol
        self.atol = atol
        self.compiler = compiler
        self.segments = segments
        self.peclet = peclet

    def __setattr__(self, name, value):
        if name in ["atol", "rtol"]:
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
            raise AttributeError("%s is not a valid attribute of QualityOptions" % name)
        self.__dict__[name] = value


class ReportOptions(_OptionsBase):
    """
    Options related to EPANET report outputs.
    The values in this options class *do not* affect the behavior of the WNTRSimulator.
    These only affect what is written to an EPANET INP file and the results that are
    in the EPANET-created report file.

    Parameters
    ----------
    report_filename : str
        Provides the filename to use for outputting an EPANET report file,
        by default this will be the prefix plus ".rpt".

    status : str
        Output solver status ("YES", "NO", "FULL"). "FULL" is only useful for debugging

    summary : str
        Output summary information ("YES" or "NO")

    energy : str
        Output energy information

    nodes : None, "ALL", or list
        Output node information in report file. If a list of node names is provided,
        EPANET only provides report information for those nodes.

    links : None, "ALL", or list
        Output link information in report file. If a list of link names is provided,
        EPANET only provides report information for those links.

    pagesize : str
        Page size for EPANET report output


    """

    def __init__(
        self,
        pagesize: list = None,
        report_filename: str = None,
        species: dict = None,
        species_precision: dict = None,
        nodes: bool = False,
        links: bool = False,
    ):
        self.pagesize = pagesize
        self.report_filename = report_filename
        self.species = species if species is not None else dict()
        self.species_precision = species_precision if species_precision is not None else dict()
        self.nodes = nodes
        self.links = links

    def __setattr__(self, name, value):
        if name not in ["pagesize", "report_filename", "species", "nodes", "links", "species_precision"]:
            raise AttributeError("%s is not a valid attribute of ReportOptions" % name)
        self.__dict__[name] = value


class UserOptions(_OptionsBase):
    """
    Options defined by the user.

    Provides an empty class that accepts getattribute and setattribute methods to
    create user-defined options. For example, if using WNTR for uncertainty
    quantification, certain options could be added here that would never be
    used directly by WNTR, but which would be saved on pickling and could be
    used by the user-built analysis scripts.

    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self.__dict__[k] = v


class RxnOptions(_OptionsBase):
    """
    Water network model options class.

    These options mimic options in EPANET.
    The `user` attribute is a generic python class object that allows for
    dynamically created attributes that are user specific.

    Parameters
    ----------
    title : str
        The title to print in the .msx file

    time : TimeOptions
        Contains all timing options for the scenarios

    quality : QualityOptions
        Contains water quality simulation options and source definitions

    report : ReportOptions
        Contains options for how for format and save report

    user : dict
        An empty dictionary that allows for user specified options


    """

    def __init__(self, time: TimeOptions = None, report: ReportOptions = None, quality: QualityOptions = None, user: UserOptions = None):
        self.time = TimeOptions.factory(time)
        self.report = ReportOptions.factory(report)
        self.quality = QualityOptions.factory(quality)
        self.user = UserOptions.factory(user)

    def __setattr__(self, name, value):
        if name == "time":
            if not isinstance(value, (TimeOptions, dict, tuple, list)):
                raise ValueError("time must be a TimeOptions or convertable object")
            value = TimeOptions.factory(value)
        elif name == "report":
            if not isinstance(value, (ReportOptions, dict, tuple, list)):
                raise ValueError("report must be a ReportOptions or convertable object")
            value = ReportOptions.factory(value)
        elif name == "quality":
            if not isinstance(value, (QualityOptions, dict, tuple, list)):
                raise ValueError("quality must be a QualityOptions or convertable object")
            value = QualityOptions.factory(value)
        elif name == "user":
            value = UserOptions.factory(value)
        else:
        # elif name not in ["title"]:
            raise ValueError("%s is not a valid member of WaterNetworkModel")
        self.__dict__[name] = value

    def to_dict(self):
        """Dictionary representation of the options"""
        return dict(self)
