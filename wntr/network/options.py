"""
The wntr.network.options module includes simulation options.

.. note:: 

    This module has been changed in version 0.2.3 to incorporate the new options 
    that EPANET 2.2 requires. It also reorganizes certain options to better align 
    with EPANET nomenclature. This change is not backwards compatible, particularly 
    when trying to use pickle files with older options.

.. rubric:: Classes

.. autosummary::
    :nosignatures:

    Options
    TimeOptions
    GraphicsOptions
    HydraulicOptions
    ReportOptions
    ReactionOptions
    QualityOptions
    EnergyOptions
    UserOptions

"""
import re
import logging
import copy

logger = logging.getLogger(__name__)

def _float_or_None(value):
    """Converts a value to a float, but doesn't crash for values of None"""
    if value is not None:
        return float(value)
    return None


def _int_or_None(value):
    """Converts a value to an int, but doesn't crash for values of None"""
    if value is not None:
        return int(value)
    return None


def _new_report_params():
    ret = dict(elevation=False, demand=True, head=True, pressure=True,
                quality=True, length=False, diameter=False, flow=True,
                velocity=True, headloss=True, position=False, setting=False, reaction=False)
    ret['f-factor'] = False
    return ret


def _new_report_obj():
    ret = dict(demand=True, head=True, pressure=True, quality=True,
                flow=True, linkquality=True, velocity=True, headloss=True, status=True,
                setting=True, rxnrate=True, frictionfact=True)
    return ret


def _new_param_opts():
    ret = dict(elevation=dict(), demand=dict(), head=dict(), pressure=dict(),
                quality=dict(), length=dict(), diameter=dict(), flow=dict(), 
                velocity=dict(), headloss=dict(), position=dict(), setting=dict(),
                reaction=dict())
    ret['f-factor'] = dict()
    return ret


class _OptionsBase(object):
    @classmethod
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        elif val is None:
            return cls()
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, ", ".join(["{}={}".format(k, repr(v)) for k, v in self.__dict__.items()]))
    __repr__ = __str__

    def __iter__(self):
        for k, v in self.__dict__.items():
            try: 
                vv = dict(v)
            except:
                vv = v
            yield k, vv

    def __getitem__(self, index):
        return self.__dict__[index]
    
    def __eq__(self, other):
        if other is None: return False
        if not hasattr(other, '__dict__'): return False
        for k in self.__dict__.keys():
            if not self.__dict__[k] == other.__dict__[k]: return False
        return True


class TimeOptions(_OptionsBase):
    """
    Options related to simulation and model timing.
    These options are named according to the EPANET 2.2 "Times" settings.
    
    Parameters
    ----------
    duration : int
        Simulation duration (seconds), by default 0.

    hydraulic_timestep : int >= 1
        Hydraulic timestep (seconds), by default 3600 (one hour).

    quality_timestep : int >= 1
        Water quality timestep (seconds), by default 360 (five minutes).

    rule_timestep : int >= 1
        Rule timestep (seconds), by default 360 (five minutes).

    pattern_timestep : int >= 1
        Pattern timestep (seconds), by default 3600 (one hour).

    pattern_start : int
        Time offset (in seconds) to find the starting pattern step; changes 
        where in pattern the pattern starts out, *not* what time the pattern 
        starts, by default 0.

    report_timestep : int >= 1
        Reporting timestep (seconds), by default 3600 (one hour).

    report_start : int
        Start time of the report (in seconds) from the start of the simulation, by default 0.

    start_clocktime : int
        Time of day (in seconds from midnight) at which the simulation begins, by default 0 (midnight).

    statistic: str
        Provide statistics rather than time series report in the report file.
        Options are "AVERAGED", "MINIMUM", "MAXIUM", "RANGE", and "NONE" (as defined in the 
        EPANET User Manual). Defaults to "NONE".

    pattern_interpolation: bool 
        **Only used by the WNTRSimulator**. Defaults to False. If True, interpolation will
        be used determine pattern values between pattern timesteps. If
        False, patterns cause step-like behavior where the pattern
        value corresponding to the most recent pattern timestep is
        used until the next pattern timestep. For example, given the
        pattern [1, 1.2, 1.6], a pattern timestep of 1 hour, and a
        pattern_interpolation value of False, a value of 1 is used at
        0 hours and every time strictly less than 1 hour. A value of
        1.2 is used at hour 1 and every time strictly less than 2
        hours. With a pattern_interpolation value of True, a value of
        1 is used at 0 hours and a value of 1.2 is used at 1
        hour. However, at an intermediat time such as 0.5 hours,
        interpolation is used, resulting in a value of 1.1. Using
        interpolation with a shorter hydraulic_timestep can make
        problems with large changes in patterns (e.g., large changes
        in demand) easier to solve.

    """
    _pattern1 = re.compile(r'^(\d+):(\d+):(\d+)$')
    _pattern2 = re.compile(r'^(\d+):(\d+)$')
    _pattern3 = re.compile(r'^(\d+)$')
    def __init__(self,
                duration: int = 0,
                hydraulic_timestep: int=3600,
                quality_timestep: int=360,
                rule_timestep: int=360,
                pattern_timestep: int=3600,
                pattern_start: int=0,
                report_timestep: int=3600,
                report_start: int=0,
                start_clocktime: int=0,
                statistic: str='NONE',
                pattern_interpolation: bool = False):
        self.duration = duration
        self.hydraulic_timestep = hydraulic_timestep
        self.quality_timestep = quality_timestep
        self.rule_timestep = rule_timestep
        self.pattern_timestep = pattern_timestep
        self.pattern_start = pattern_start
        self.report_timestep = report_timestep
        self.report_start = report_start
        self.start_clocktime = start_clocktime
        self.statistic = statistic
        self.pattern_interpolation = pattern_interpolation

    def __setattr__(self, name, value):
        if name == 'statistic':
            value = str.upper(value)
            if value not in ['AVERAGED', 'MINIMUM', 'MAXIMUM', 'RANGE', 'NONE']:
                raise ValueError('Statistic must be one of AVERAGED, MINIMUM, MAXIMUM, RANGE or NONE')
        elif name in {'hydraulic_timestep', 'quality_timestep', 'rule_timestep', 
                        'pattern_timestep'}:
            try:
                value = max(1, int(value))
            except ValueError:
                raise ValueError('%s must be an integer >= 1'%name)
        elif name not in {'duration', 'pattern_start', 'report_start', 'report_timestep',
                            'start_clocktime', 'pattern_interpolation'}:
            raise AttributeError('%s is not a valid attribute in TimeOptions'%name)
        elif name not in {'report_timestep', 'pattern_interpolation'}:
            try:
                value = float(value)
            except ValueError:
                raise ValueError('%s must be a number'%name)
        self.__dict__[name] = value


class GraphicsOptions(_OptionsBase):
    """
    Options related to graphics. 
    
    May be used to contain custom, user defined values. 
    These options are taken from the EPANET "[BACKDROP]" section. 
    Additionally, the "MAP" option (`map_filename`), which identifies a file containing 
    node coordinates in the EPANET "[OPTIONS]" section, is also included here.
    
    Parameters
    ----------
    dimensions : 4-tuple or list
        Dimensions for backdrop image in the order (LLx, LLy, URx, URy). By default, 
        EPANET will make the image match the full extent of node coordinates (set to `None`).

    units : str
        Units for backdrop image dimensions. Must be one of FEET, METERS, DEGREES or NONE, by default "NONE".

    offset : 2-tuple or list
        Offset for the network in order (X, Y), by default ``None`` (no offset).

    image_filename : string
        Filename where image is located, by default ``None``.

    map_filename : string
        Filename used to store node coordinates in (node, x, y) format. This option is
        from the EPANET "[OPTIONS]" section. See note below.
    
    
    .. note::

        Because the format of the MAP file is uncertain, file will need to be processed
        by the user to assign coordinates to nodes, if desired. Remember that node 
        coordinates have impact *only* on graphics and *do not* impact simulation results.
        If the `map_filename` is not ``None``, then no [COORDINATES] will be written out
        to INP files (to save space, since the simulator does not use that section).
        This can be overwritten in the `write_inpfile` commands.
    

    """
    def __init__(self,
                 dimensions: list = None,
                 units: str = None,
                 offset: list = None,
                 image_filename: str = None,
                 map_filename: str = None):
        self.dimensions = dimensions
        self.units = units
        self.offset = offset
        self.image_filename = image_filename
        self.map_filename = map_filename

    def __setattr__(self, name, value):
        if name == 'units':
            value = str(value).upper()
            if value not in ['FEET','METERS','DEGREES','NONE']:
                raise ValueError('Backdrop units must be one of FEET, METERS, DEGREES, or NONE')
        elif name not in ['dimensions', 'units', 'offset', 'image_filename', 'map_filename']:
            raise AttributeError('%s is not a valid attribute of GraphicsOptions'%name)
        self.__dict__[name] = value


class HydraulicOptions(_OptionsBase): 
    """
    Options related to hydraulic model.
    These options are named according to the settings in the EPANET "[OPTIONS]"
    section. Unless specified, these options are valid for both EPANET 2.0 and 2.2.
    
    Parameters
    ----------
    headloss : str
        Formula to use for computing head loss through a pipe. Options are "H-W", 
        "D-W", and "C-M", by default "H-W".

    hydraulics : str
        Indicates if a hydraulics file should be read in or saved; options are 
        ``None``, "USE" and "SAVE", by default ``None``.

    hydraulics_filename : str
        Filename to use if ``hydraulics is not None``, by default ``None``.

    viscosity : float
        Kinematic viscosity of the fluid, by default 1.0.

    specific_gravity : float
        Specific gravity of the fluid, by default 1.0.

    pattern : str
        Name of the default pattern for junction demands. By default,
        the default pattern is the pattern named "1". If this is set 
        to None (or if pattern "1" does not exist), then
        junctions with demands but without patterns will be held constant.

    demand_multiplier : float
        The demand multiplier adjusts the values of baseline demands for all 
        junctions, by default 1.0.

    emitter_exponent : float
        The exponent used when computing flow from an emitter, by default 0.5.

    minimum_pressure : float
        (EPANET 2.2 only) The global minimum nodal pressure, by default 0.0.

    required_pressure: float
        (EPANET 2.2 only) The required nodal pressure, by default 0.07 (m H2O)

    pressure_exponent: float
        (EPANET 2.2 only) The pressure exponent, by default 0.5.

    trials : int
        Maximum number of trials used to solve network hydraulics, by default 200.

    accuracy : float
        Convergence criteria for hydraulic solutions, by default 0.001.

    headerror : float
        (EPANET 2.2 only) Augments the `accuracy` option by adjusting the head 
        error convergence limit, by default 0 (off).

    flowchange : float
        (EPANET 2.2 only) Augments the `accuracy` option by adjusting the flow 
        change convergence limit, by default 0 (off).

    unbalanced : str
        Indicate what happens if a hydraulic solution cannot be reached.  
        Options are "STOP" and "CONTINUE", by default "STOP".

    unbalanced_value : int
        Number of additional trials if ``unbalanced == "CONTINUE"``, by default ``None``.

    checkfreq : int
        Number of solution trials that pass between status checks, by default 2.

    maxcheck : int
        Number of solution trials that pass between status check, by default 10.

    damplimit : float
        Accuracy value at which solution damping begins, by default 0 (no damping).

    demand_model : str
        Demand model for EPANET 2.2; acceptable values are "DD" and "PDD", by default "DD".
        EPANET 2.0 only contains demand driven analysis, and will issue a warning 
        if this option is not set to DD.

    inpfile_units : str
        Units for the INP file; options are "CFS", "GPM", "MGD", "IMGD", "AFD", "LPS", 
        "LPM", "MLD", "CMH", and "CMD". This **only** changes the units used in generating
        the INP file -- it has **no impact** on the units used in WNTR, which are 
        **always** SI units (m, kg, s).
    
    inpfile_pressure_units: str
        Pressure units for the INP file, by default None (uses pressure units from inpfile_units)

    """
    def __init__(self,
                 headloss: str = 'H-W',
                 hydraulics: str = None,
                 hydraulics_filename: str = None,
                 viscosity: float = 1.0,
                 specific_gravity: float = 1.0,
                 pattern: str = '1',
                 demand_multiplier: float = 1.0,
                 demand_model: str = 'DD',
                 minimum_pressure: float = 0.0,
                 required_pressure: float = 0.07,  # EPANET 2.2 default
                 pressure_exponent: float = 0.5,
                 emitter_exponent: float = 0.5,
                 trials: int = 200,  # EPANET 2.2 increased the default from 40 to 200
                 accuracy: float = 0.001,
                 unbalanced: str = 'STOP',
                 unbalanced_value: int = None,
                 checkfreq: int = 2,
                 maxcheck: int = 10,
                 damplimit: int = 0,
                 headerror: float = 0,
                 flowchange: float = 0,
                 inpfile_units: str = 'GPM',
                 inpfile_pressure_units: str = None):
        self.headloss = headloss
        self.hydraulics = hydraulics
        self.hydraulics_filename = hydraulics_filename
        self.viscosity = viscosity
        self.specific_gravity = specific_gravity
        self.pattern = pattern
        self.demand_multiplier = demand_multiplier
        self.demand_model = demand_model
        self.minimum_pressure = minimum_pressure
        self.required_pressure = required_pressure
        self.pressure_exponent = pressure_exponent
        self.emitter_exponent = emitter_exponent
        self.trials = trials
        self.accuracy = accuracy
        self.unbalanced = unbalanced
        self.unbalanced_value = unbalanced_value
        self.checkfreq = checkfreq
        self.maxcheck = maxcheck
        self.damplimit = damplimit
        self.headerror = headerror
        self.flowchange = flowchange
        self.inpfile_units = inpfile_units
        self.inpfile_pressure_units = inpfile_pressure_units

    def __setattr__(self, name, value):
        if name == 'headloss':
            value = str.upper(value)
            if value not in ['H-W', 'D-W', 'C-M']:
                raise ValueError('headloss must be one of "H-W", "D-W", or "C-M"')
        elif name == 'hydraulics':
            if value is not None:
                value = str.upper(value)
                if value not in ['USE', 'SAVE']:
                    raise ValueError('hydraulics must be None (off) or one of "USE" or "SAVE"')
        elif name == 'demand_model':
            if value is not None:
                value = str.upper(value)
                if value not in ['DDA', 'DD', 'PDD', 'PDA']:
                    raise ValueError('demand_model must be None (off) or one of "DD", "DDA", "PDD", or "PDA"')
                if value == 'DD': value = 'DDA'
                if value == 'PDD': value = 'PDA'
        elif name == 'unbalanced':
            value = str.upper(value)
            if value not in ['STOP', 'CONTINUE']:
                raise ValueError('headloss must be either "STOP" or "CONTINUE"')
        elif name == 'inpfile_units' and isinstance(value, str):
            value = str.upper(value)
            if value not in ['CFS', 'GPM', 'MGD', 'IMGD', 'AFD', 'LPS', 'LPM', 'MLD', 'CMH', 'CMD']:
                raise ValueError('inpfile_units = "%s" is not a valid EPANET unit code', value)
        elif name == 'inpfile_pressure_units' and isinstance(value, str):
            value = str.upper(value)
        elif name == 'unbalanced_value':
            try:
                value = _int_or_None(value)
            except ValueError:
                raise ValueError('%s must be an int or None', name)
        elif name in ['trials', 'checkfreq', 'maxcheck']:
            try:
                value = int(value)
            except ValueError:
                raise ValueError('%s must be an integer', name)
        elif name not in ['pattern', 'hydraulics_filename', 'inpfile_units', 'inpfile_pressure_units']:
            try:
                value = float(value)
            except ValueError:
                raise ValueError('%s must be a number', name)
        if name not in ['headloss', 'hydraulics', 'hydraulics_filename', 'viscosity', 'specific_gravity',
                        'pattern', 'demand_multiplier', 'demand_model', 'minimum_pressure', 'required_pressure',
                        'pressure_exponent', 'emitter_exponent', 'trials', 'accuracy', 'unbalanced', 
                        'unbalanced_value', 'checkfreq', 'maxcheck', 'damplimit', 'headerror',
                        'flowchange', 'inpfile_units', 'inpfile_pressure_units']:
            raise AttributeError('%s is not a valid attribute of HydraulicOptions'%name)
        self.__dict__[name] = value


class ReactionOptions(_OptionsBase):
    """
    Options related to water quality reactions.
    From the EPANET "[REACTIONS]" options.
    
    Parameters
    ----------
    bulk_order : float
        Order of reaction occurring in the bulk fluid, by default 1.0.

    wall_order : float
        Order of reaction occurring at the pipe wall; must be either 0 or 1, by default 1.0.

    tank_order : float
        Order of reaction occurring in the tanks, by default 1.0.

    bulk_coeff : float
        Global reaction coefficient for bulk fluid and tanks, by default 0.0.

    wall_coeff : float
        Global reaction coefficient for pipe walls, by default 0.0.

    limiting_potential : float
        Specifies that reaction rates are proportional to the difference 
        between the current concentration and some limiting potential value, 
        by default ``None`` (off).

    roughness_correl : float
        Makes all default pipe wall reaction coefficients related to pipe 
        roughness, according to functions as defined in EPANET, by default 
        ``None`` (off).
        

    .. note::

        Remember to use positive numbers for growth reaction coefficients and 
        negative numbers for decay coefficients. The time units for all reaction
        coefficients are in "per-second" and converted to/from EPANET units during I/O.

    """
    def __init__(self,
                 bulk_order: float = 1.0,
                 wall_order: float = 1.0,
                 tank_order: float = 1.0,
                 bulk_coeff: float = 0.0,
                 wall_coeff: float = 0.0,
                 limiting_potential: float = None,
                 roughness_correl: float = None):
        self.bulk_order = bulk_order
        self.wall_order = wall_order
        self.tank_order = tank_order
        self.bulk_coeff = bulk_coeff
        self.wall_coeff = wall_coeff
        self.limiting_potential = limiting_potential
        self.roughness_correl = roughness_correl

    def __setattr__(self, name, value):
        if name not in ['limiting_potential', 'roughness_correl']:
            try:
                value = float(value)
            except ValueError:
                raise ValueError('%s must be a number', name)
        else:
            try:
                value = _float_or_None(value)
            except ValueError:
                raise ValueError('%s must be a number or None', name)
        if name not in ['bulk_order', 'wall_order', 'tank_order', 'bulk_coeff',
                        'wall_coeff', 'limiting_potential', 'roughness_correl']:
            raise AttributeError('%s is not a valid attribute of ReactionOptions'%name)
        self.__dict__[name] = value


class QualityOptions(_OptionsBase):
    """
    Options related to water quality modeling. These options come from
    the "[OPTIONS]" section of an EPANET INP file.
    
    Parameters
    ----------
    parameter : str
        Type of water quality analysis.  Options are "NONE", "CHEMICAL", "AGE", and 
        "TRACE", by default ``None``.

    trace_node : str
        Trace node name if ``quality == "TRACE"``, by default ``None``.

    chemical : str
        Chemical name for "CHEMICAL" analysis, by default "CHEMICAL" if appropriate.

    diffusivity : float
        Molecular diffusivity of the chemical, by default 1.0.

    tolerance : float
        Water quality solver tolerance, by default 0.01.

    inpfile_units : str
        Units for quality analysis if the parameter is set to CHEMICAL. 
        This is **only** relevant for the INP file. This value **must** be either
        "mg/L" (default) or "ug/L" (miligrams or micrograms per liter). 
        Internal WNTR units are always SI units (kg/m3).


    """
    def __init__(self,
                 parameter: str = 'NONE',
                 trace_node: str = None,
                 chemical_name: str = 'CHEMICAL',
                 diffusivity: float = 1.0,
                 tolerance: float = 0.01,
                 inpfile_units: str = 'mg/L'):
        self.parameter = parameter
        self.trace_node = trace_node
        self.chemical_name = chemical_name
        self.diffusivity = diffusivity
        self.tolerance = tolerance
        self.inpfile_units = inpfile_units

    def __setattr__(self, name, value):
        if name in ['diffusivity', 'tolerance']:
            try:
                value = float(value)
            except ValueError:
                raise ValueError('%s must be a number or None', name)
        if name not in ['parameter', 'trace_node', 'chemical_name', 'diffusivity',
                        'tolerance', 'inpfile_units']:
            raise AttributeError('%s is not a valid attribute of QualityOptions'%name)
        self.__dict__[name] = value


class EnergyOptions(_OptionsBase):
    """
    Options related to energy calculations.
    From the EPANET "[ENERGY]" settings.
    
    Parameters
    ----------
    global_price : float
        Global average cost per Joule, by default 0.

    global_pattern : str
        ID label of time pattern describing how energy price varies with
        time, by default ``None``.

    global_efficiency : float
        Global pump efficiency as percent; i.e., 75.0 means 75%,
        by default ``None``.

    demand_charge : float
        Added cost per maximum kW usage during the simulation period,
        by default ``None``.

    
    """
    def __init__(self,
                global_price: float=0,
                global_pattern: str=None,
                global_efficiency: float=None,
                demand_charge: float=None):
        self.global_price = global_price
        self.global_pattern = global_pattern
        self.global_efficiency = global_efficiency
        self.demand_charge = demand_charge

    def __setattr__(self, name, value):
        if name not in ['global_price', 'global_pattern', 'global_efficiency', 'demand_charge']:
            raise AttributeError('%s is not a valid attribute of EnergyOptions'%name)
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
    def __init__(self,
                pagesize: list=None,
                report_filename: str=None,
                status: str='NO',
                summary: str='YES',
                energy: str='NO',
                nodes: bool=False,
                links: bool=False,
                report_params: dict=None,
                param_opts: dict=None):
        self.pagesize = pagesize
        self.report_filename = report_filename
        self.status = status
        self.summary = summary
        self.energy = energy
        self.nodes = nodes
        self.links = links
        self.report_params = report_params if report_params is not None else _new_report_params()
        self.param_opts = param_opts if param_opts is not None else _new_param_opts()
    
    def __setattr__(self, name, value):
        if name not in ['pagesize', 'report_filename', 'status', 'summary', 'energy', 'nodes',
                        'links', 'report_params', 'param_opts']:
            raise AttributeError('%s is not a valid attribute of ReportOptions'%name)
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


class Options(_OptionsBase):
    """
    Water network model options class.
    
    These options mimic options in EPANET.
    The `user` attribute is a generic python class object that allows for 
    dynamically created attributes that are user specific.

    Parameters
    ----------
    time : TimeOptions
        Contains all timing options for the scenarios

    hydraulic : HydraulicOptions
        Contains hydraulic solver parameters

    reaction : ReactionOptions
        Contains chemical reaction parameters

    quality : QualityOptions
        Contains water quality simulation options and source definitions

    energy : EnergyOptions
        Contains parameters for energy calculations

    report : ReportOptions
        Contains options for how for format and save report

    graphics : GraphicsOptions
        Contains EPANET graphics and background options and also the filename
        for external node coordinates, if used

    user : dict
        An empty dictionary that allows for user specified options
    
    
    """
    def __init__(self,
                 time: TimeOptions = None,
                 hydraulic: HydraulicOptions = None,
                 report: ReportOptions = None,
                 quality: QualityOptions = None,
                 reaction: ReactionOptions = None,
                 energy: EnergyOptions = None,
                 graphics: GraphicsOptions = None,
                 user: UserOptions = None):
        self.time = TimeOptions.factory(time)
        self.hydraulic = HydraulicOptions.factory(hydraulic)
        self.report = ReportOptions.factory(report)
        self.quality = QualityOptions.factory(quality)
        self.reaction = ReactionOptions.factory(reaction)
        self.energy = EnergyOptions.factory(energy)
        self.graphics = GraphicsOptions.factory(graphics)
        self.user = UserOptions.factory(user)

    def __setattr__(self, name, value):
        if name == 'time':
            if not isinstance(value, (TimeOptions, dict, tuple, list)):
                raise ValueError('time must be a TimeOptions or convertable object')
            value = TimeOptions.factory(value)
        elif name == 'hydraulic':
            if not isinstance(value, (HydraulicOptions, dict, tuple, list)):
                raise ValueError('hydraulic must be a HydraulicOptions or convertable object')
            value = HydraulicOptions.factory(value)
        elif name == 'report':
            if not isinstance(value, (ReportOptions, dict, tuple, list)):
                raise ValueError('report must be a ReportOptions or convertable object')
            value = ReportOptions.factory(value)
        elif name == 'quality':
            if not isinstance(value, (QualityOptions, dict, tuple, list)):
                raise ValueError('quality must be a QualityOptions or convertable object')
            value = QualityOptions.factory(value)
        elif name == 'reaction':
            if not isinstance(value, (ReactionOptions, dict, tuple, list)):
                raise ValueError('reaction must be a ReactionOptions or convertable object')
            value = ReactionOptions.factory(value)
        elif name == 'energy':
            if not isinstance(value, (EnergyOptions, dict, tuple, list)):
                raise ValueError('energy must be a EnergyOptions or convertable object')
            value = EnergyOptions.factory(value)
        elif name == 'graphics':
            if not isinstance(value, (GraphicsOptions, dict, tuple, list)):
                raise ValueError('graphics must be a GraphicsOptions or convertable object')
            value = GraphicsOptions.factory(value)
        elif name == 'user':
            value = UserOptions.factory(value)
        else:
            raise ValueError('%s is not a valid member of WaterNetworkModel')
        self.__dict__[name] = value


    def to_dict(self):
        """Dictionary representation of the options"""
        return dict(self)
