"""
The wntr.network.options module includes simulation options.

.. note:: 

    This module has been changed in version 0.2.3 to incorporate the new options 
    that EPANET 2.2 requires. It also reorganizes certain options to better align 
    with EPANET nomenclature. This change is not backwards compatible, particularly 
    when trying to use pickle files with older options.

.. rubric:: Contents

.. autosummary::

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
    
    Parameters
    ----------
    duration : int
        Simulation duration in seconds
    hydraulic_timestep : int
        Hydraulic timestep in seconds
    quality_timestep : int
        Water quality timestep in seconds 
    rule_timestep : int
        Rule timestep in seconds
    pattern_timestep : int
        Pattern timestep in seconds
    pattern_start : int
        Time offset (in seconds) to find the starting pattern step; changes 
        where in pattern the pattern starts out, *not* what time the pattern 
        starts
    report_timestep : int
        Reporting timestep in seconds
    report_start : int
        Start time of the report in seconds from the start of the simulation
    start_clocktime : int, default 0
        Time of day in seconds from 12 am at which the simulation begins
    statistic: str
        Provide statistics rather than time series report in the report file.
        Options are AVERAGED, MINIMUM, MAXIUM, RANGE, and NONE (as defined in the 
        EPANET User Manual)
    
    """
    _pattern1 = re.compile(r'^(\d+):(\d+):(\d+)$')
    _pattern2 = re.compile(r'^(\d+):(\d+)$')
    _pattern3 = re.compile(r'^(\d+)$')
    def __init__(self,
                duration: float = 0.0,
                hydraulic_timestep: float=3600.0,
                quality_timestep: float=360.0,
                rule_timestep: float=360.0,
                pattern_timestep: float=3600.0,
                pattern_start: float=0.0,
                report_timestep: float=3600.0,
                report_start: float=0.0,
                start_clocktime: float=0.0,
                statistic: str='NONE'):
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

    def __setattr__(self, name, value):
        if name == 'statistic':
            value = str.upper(value)
            if value not in ['AVERAGED', 'MINIMUM', 'MAXIMUM', 'RANGE', 'NONE']:
                raise ValueError('headloss must be one of "H-W", "D-W", or "C-M"')
        elif name not in ['report_timestep']:
            try:
                value = float(value)
            except ValueError:
                raise ValueError('%s must be a number', name)
        self.__dict__[name] = value

    @classmethod
    def seconds_to_tuple(cls, sec):
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        return (hours, mm, int(sec))

    @classmethod
    def time_str_to_seconds(cls, s):
        """
        Converts time format to seconds.

        Parameters
        ----------
        s : string
            Time string. Options are 'HH:MM:SS', 'HH:MM', 'HH'


        Returns
        -------
        Integer value of time in seconds.
        """
        time_tuple = cls._pattern1.search(s)
        if bool(time_tuple):
            return (int(time_tuple.groups()[0])*60*60 +
                    int(time_tuple.groups()[1])*60 +
                    int(round(float(time_tuple.groups()[2]))))
        else:
            time_tuple = cls._pattern2.search(s)
            if bool(time_tuple):
                return (int(time_tuple.groups()[0])*60*60 +
                        int(time_tuple.groups()[1])*60)
            else:
                time_tuple = cls._pattern3.search(s)
                if bool(time_tuple):
                    return int(time_tuple.groups()[0])*60*60
                else:
                    raise RuntimeError("Time format not recognized. ")

    @classmethod
    def clock_str_to_seconds(cls, s, am_pm):
        """
        Converts clocktime format to seconds.


        Parameters
        ----------
        s : string
            Time string. Options are 'HH:MM:SS', 'HH:MM', HH'

        am : string
            options are AM or PM


        Returns
        -------
        Integer value of time in seconds

        """
        if am_pm.upper() == 'AM':
            am = True
        elif am_pm.upper() == 'PM':
            am = False
        else:
            raise RuntimeError('am_pm option not recognized; options are AM or PM')

        time_tuple = cls._pattern1.search(s)
        if bool(time_tuple):
            time_sec = (int(time_tuple.groups()[0])*60*60 +
                        int(time_tuple.groups()[1])*60 +
                        int(round(float(time_tuple.groups()[2]))))
            if s.startswith('12'):
                time_sec -= 3600*12
            if not am:
                if time_sec >= 3600*12:
                    raise RuntimeError('Cannot specify am/pm for times greater than 12:00:00')
                time_sec += 3600*12
            return time_sec
        else:
            time_tuple = cls._pattern2.search(s)
            if bool(time_tuple):
                time_sec = (int(time_tuple.groups()[0])*60*60 +
                            int(time_tuple.groups()[1])*60)
                if s.startswith('12'):
                    time_sec -= 3600*12
                if not am:
                    if time_sec >= 3600 * 12:
                        raise RuntimeError('Cannot specify am/pm for times greater than 12:00:00')
                    time_sec += 3600*12
                return time_sec
            else:
                time_tuple = cls._pattern3.search(s)
                if bool(time_tuple):
                    time_sec = int(time_tuple.groups()[0])*60*60
                    if s.startswith('12'):
                        time_sec -= 3600*12
                    if not am:
                        if time_sec >= 3600 * 12:
                            raise RuntimeError('Cannot specify am/pm for times greater than 12:00:00')
                        time_sec += 3600*12
                    return time_sec
                else:
                    raise RuntimeError("Time format not recognized. ")


class GraphicsOptions(_OptionsBase):
    """
    Options related to graphics. 
    
    May be used to contain custom, user defined values. Default attributes 
    comprise the EPANET "backdrop" section options.
    
    Parameters
    ----------
    dimensions : 4-tuple or list
        (x, y, dx, dy) Dimensions for backdrop image 
    units : str
        Units for backdrop image
    offset : 2-tuple or list
        (x,y) offset for the network
    image_filename : string
        Filename where image is located
    map_filename : string
        Filename used to store node coordinates in (node, x, y) format
    
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


class HydraulicOptions(_OptionsBase): 
    """
    Options related to hydraulic model, including hydraulics. 
    
    Parameters
    ----------
    headloss : str
        Formula to use for computing head loss through a pipe. Options are H-W, 
        D-W, and C-M
    hydraulics : str
        Indicates if a hydraulics file should be read in or saved; options are 
        None, USE and SAVE (default None)
    hydraulics_filename : str
        Filename to use if hydraulics = SAVE
    viscosity : float
        Kinematic viscosity of the fluid
    specific_gravity : float
        Specific gravity of the fluid 
    pattern : str
        Name of the default pattern for junction demands. If None, the 
        junctions with demands but without patterns will be held constant
    demand_multiplier : float
        The demand multiplier adjusts the values of baseline demands for all 
        junctions
    emitter_exponent : float
        The exponent used when computing flow from an emitter
    minimum_pressure : float
        The minimum nodal pressure - only valid for EPANET 2.2
    required_pressure: float
        The required nodal pressure - only valid for EPANET 2.2
    pressure_exponent: float
        The pressure exponent - only valid for EPANET 2.2
    trials : int
        Maximum number of trials used to solve network hydraulics
    accuracy : float
        Convergence criteria for hydraulic solutions (default 0.001)
    unbalanced : str
        Indicate what happens if a hydraulic solution cannot be reached.  
        Options are STOP and CONTINUE
    unbalanced_value : int
        Number of additional trials if unbalanced = CONTINUE
    checkfreq : int
        Number of solution trials that pass between status check 
    maxcheck : int
        Number of solution trials that pass between status check 
    damplimit : float
        Accuracy value at which solution damping begins
    headerror : float
        The head error convergence limit
    flowchange : float
        The flow change convergence limit
    demand_model : str
        Demand model for EPANET 2.2; acceptable values are DD, PDD, DDA and PDA, though DDA and PDA are the preferred abbreviations.
        EPANET 2.0 only contains demand driven analysis, and will issue a warning if this option is not DD or DDA.
    inpfile_units : str
        Units for the INP-file; options are CFS, GPM, MGD, IMGD, AFD, LPS, 
        LPM, MLD, CMH, and CMD. This **only** changes the units used in generating
        the INP file -- it has **no impact** on the units used in WNTR, which are 
        always SI units (m, kg, s).
    
    """
    def __init__(self,
                 headloss: str = 'H-W',
                 hydraulics: str = None,
                 hydraulics_filename: str = None,
                 viscosity: float = 1.0,
                 specific_gravity: float = 1.0,
                 pattern: str = '1',
                 demand_multiplier: float = 1.0,
                 demand_model: str = 'DDA',
                 minimum_pressure: float = 0.0,
                 required_pressure: float = 0.07,
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
                 inpfile_units: str = 'GPM'):
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
                    raise ValueError('demand_model must be None (off) or one of "DDA" or "PDA"')
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
        elif name not in ['pattern', 'hydraulics_filename', 'inpfile_units']:
            try:
                value = float(value)
            except ValueError:
                raise ValueError('%s must be a number', name)
        self.__dict__[name] = value


class ReactionOptions(_OptionsBase):
    """
    Options related to water quality reactions.
    
    Parameters
    ----------
    bulk_order : float
        Order of reaction occurring in the bulk fluid
    wall_order : float
        Order of reaction occurring at the pipe wall
    tank_order : float
        Order of reaction occurring in the tanks
    bulk_coeff : float
        Reaction coefficient for bulk fluid and tanks
    wall_coeff : float
        Reaction coefficient for pipe walls
    limiting_potential : float
        Specifies that reaction rates are proportional to the difference 
        between the current concentration and some limiting potential value, 
        off if None
    roughness_correl : float
        Makes all default pipe wall reaction coefficients related to pipe 
        roughness, off if None
        
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
        self.__dict__[name] = value


class QualityOptions(_OptionsBase):
    """
    Options related to water quality modeling.
    
    Parameters
    ----------
    parameter : str
        Type of water quality analysis.  Options are NONE, CHEMICAL, AGE, and 
        TRACE
    trace_node : str
        Trace node name if quality = TRACE
    chemical : str
        Chemical name for 'chemical' analysis
    diffusivity : float
        Molecular diffusivity of the chemical (default 1.0)
    tolerance : float
        Water quality solver tolerance
    inpfile_units : str
        Units for quality analysis; concentration for 'chemical', time in seconds for 'age',
        percentage for 'trace'

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
        self.__dict__[name] = value


class EnergyOptions(_OptionsBase):
    """
    Options related to energy calculations.
    
    Parameters
    ----------
    global_price : float
        Global average cost per Joule
    global_pattern : str
        ID label of time pattern describing how energy price varies with time
    global_efficiency : float
        Global pump efficiency as percent; i.e., 75.0 means 75%
    demand_charge : float
        Added cost per maximum kW usage during the simulation period, or None
        
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


class ReportOptions(_OptionsBase):
    """
    Options related to report outputs.

    Parameters
    ----------
    report_filename : str
        Provides the filename to use for outputting an EPANET report file.
        By default, this will be the prefix plus ".rpt".
    status : str
        Output solver status ('YES', 'NO', 'FULL'). 'FULL' is only useful for debugging
    summary : str
        Output summary information ('YES' or 'NO')
    energy : str
        Output energy information
    nodes : None, "ALL", or list
        Output node information in report file. If a list of node names is provided, 
        EPANET only provides report information for those nodes.
    links : None, "ALL", or list
        Output link information in report file. If a list of link names is provided, 
        EPANET only provides report information for those links.
    
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


    def todict(self):
        """Dictionary representation of the options"""
        return dict(self)
