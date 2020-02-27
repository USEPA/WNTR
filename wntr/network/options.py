"""
The wntr.network.options module includes simulation options.

.. note:: 

    This module has been changed in version wntr-2.3 to incorporate the new options 
    that EPANET 2.2 requires. It also reorganizes certain options so that they are 
    more consistent with EPANET's groupings and make more logical sense. Therefore, 
    this change is not necessarily backwards compatible, particularly when trying to
    use pickle files with options generated with wntr <= 2.2.
    For example, the options previously contained in the old SolverOptions class have 
    been moved to the HydraulicOptions class.

    Additionally, this module has been modified to use the "attrs" package,
    which is a better method of creating data structure classes than the manual 
    method used previously. This change will require users to add the attrs 
    package if they do not already have it.

    In cases where the class constructor indicates "NOTHING" is the default argument,
    this should be interpreted that there is a factory function that will generate a 
    new, blank element of the appropriate type.


.. rubric:: Contents

.. autosummary::

    WaterNetworkOptions
    TimeOptions
    GraphicsOptions
    HydraulicOptions
    ResultsOptions
    ReactionOptions
    QualityOptions
    EnergyOptions
    UserOptions

"""
import re
import logging
import attr
from attr.validators import in_

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


def _new_rpt_params():
    ret = dict(elevation=False, demand=True, head=True, pressure=True,
                quality=True, length=False, diameter=False, flow=True,
                velocity=True, headloss=True, position=False, setting=False, reaction=False)
    ret['f-factor'] = False
    return ret


def _new_results_obj():
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


@attr.s
class TimeOptions(object):
    """
    Options related to simulation and model timing.
    
    Attributes
    ----------
    duration : int, default 0
        Simulation duration in seconds
    hydraulic_timestep : int, default 3600
        Hydraulic timestep in seconds
    quality_timestep : int, default 360
        Water quality timestep in seconds 
    rule_timestep : int, default 360
        Rule timestep in seconds
    pattern_timestep : int, default 3600
        Pattern timestep in seconds
    pattern_start : int, default 0
        Time offset (in seconds) to find the starting pattern step; changes 
        where in pattern the pattern starts out, *not* what time the pattern 
        starts
    report_timestep : int, default 3600
        Reporting timestep in seconds
    report_start : int, default 0
        Start time of the report in seconds from the start of the simulation
    start_clocktime : int, default 0
        Time of day in seconds from 12 am at which the simulation begins
    statistic: str, default='NONE' (off)
        Provide statistics rather than time series results in the report file.
        Options are AVERAGED, MINIMUM, MAXIUM, RANGE, and NONE (as defined in the 
        EPANET User Manual)
    
    """
    duration = attr.ib(default=0.0, converter=float)
    hydraulic_timestep = attr.ib(default=3600.0, converter=float)
    quality_timestep = attr.ib(default=360.0, converter=float)
    rule_timestep = attr.ib(default=360.0, converter=float)
    pattern_timestep = attr.ib(default=3600.0, converter=float)
    pattern_start = attr.ib(default=0.0, converter=float)
    report_timestep = attr.ib(default=3600.0, converter=float)
    report_start = attr.ib(default=0.0, converter=float)
    start_clocktime = attr.ib(default=0.0, converter=float)
    statistic = attr.ib(default='NONE', validator=in_(['AVERAGED', 'MINIMUM', 'MAXIMUM', 'RANGE', 'NONE']))
    _pattern1 = re.compile(r'^(\d+):(\d+):(\d+)$')
    _pattern2 = re.compile(r'^(\d+):(\d+)$')
    _pattern3 = re.compile(r'^(\d+)$')

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
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def todict(self):
        """Dictionary representation of the options"""
        return attr.asdict(self)
    asdict = todict

    def tostring(self):
        """String representation of the time options"""
        s = 'Time options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring

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


@attr.s
class GraphicsOptions(object):
    """
    Options related to graphics. 
    
    May be used to contain custom, user defined values. Default attributes 
    comprise the EPANET "backdrop" section options.
    
    Attributes
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
    dimensions = attr.ib(default=None)
    units = attr.ib(default=None)
    offset = attr.ib(default=None)
    image_filename = attr.ib(default=None)
    map_filename = attr.ib(default=None)

    @classmethod
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def todict(self):
        """Dictionary representation of the options"""
        return attr.asdict(self)
    asdict = todict

    def tostring(self):
        """String representation of the graphics options"""
        s = 'Graphics options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring
    

@attr.s
class HydraulicOptions(object): 
    """
    Options related to hydraulic model, including hydraulics. 
    
    Attributes
    ----------
    headloss : str, default 'H-W'
        Formula to use for computing head loss through a pipe. Options are H-W, 
        D-W, and C-M
    hydraulics : str, default None
        Indicates if a hydraulics file should be read in or saved; options are 
        None, USE and SAVE (default None)
    hydraulics_filename : str
        Filename to use if hydraulics = SAVE
    viscosity : float, default 1.0
        Kinematic viscosity of the fluid
    specific_gravity : float, default 1.0
        Specific gravity of the fluid 
    pattern : str, default None
        Name of the default pattern for junction demands. If None, the 
        junctions with demands but without patterns will be held constant
    demand_multiplier : float, default 1.0
        The demand multiplier adjusts the values of baseline demands for all 
        junctions
    emitter_exponent : float, default 0.5
        The exponent used when computing flow from an emitter
    minimum_pressure : float, default 0.0
        The minimum nodal pressure - only valid for EPANET 2.2, this will break EPANET 2.0 if changed from the default
    required_pressure: float, default 0.0
        The required nodal pressure - only valid for EPANET 2.2, this will break EPANET 2.0 if changed from the default
    pressure_exponent: float, default 0.5
        The pressure exponent - only valid for EPANET 2.2, this will break EPANET 2.0 if changed from the default
    trials : int, default 40
        Maximum number of trials used to solve network hydraulics
    accuracy : float, default 0.001
        Convergence criteria for hydraulic solutions (default 0.001)
    unbalanced : str, default 'STOP'
        Indicate what happens if a hydraulic solution cannot be reached.  
        Options are STOP and CONTINUE
    unbalanced_value : int, default None
        Number of additional trials if unbalanced = CONTINUE
    checkfreq : int, default 2
        Number of solution trials that pass between status check 
    maxcheck : int, default 10
        Number of solution trials that pass between status check 
    damplimit : float, default 0.0
        Accuracy value at which solution damping begins
    headerror : float, default None
        The head error convergence limit
    flowchange : float, default None
        The flow change convergence limit
    demand_model : str, default None
        Demand model for EPANET 2.2; acceptable values are DD, PDD, DDA and PDA, though DDA and PDA are the preferred abbreviations.
        Changing this option will break EPANET 2.0 if changed from None. For the WNTR simulator, please set the model when calling run_sim.
    inpfile_units : str, default 'GPM'
        Units for the INP-file; options are CFS, GPM, MGD, IMGD, AFD, LPS, 
        LPM, MLD, CMH, and CMD. This **only** changes the units used in generating
        the INP file -- it has no impact on the units used in WNTR, which are 
        always SI units (m, kg, s).
    
    """
    headloss = attr.ib(default='H-W')  # H-W, D-W, C-M
    hydraulics = attr.ib(default=None)  # USE, SAVE
    hydraulics_filename = attr.ib(default=None)  # string
    viscosity = attr.ib(default=1.0)
    specific_gravity = attr.ib(default=1.0)
    pattern = attr.ib(default='1')  # any pattern string
    demand_multiplier = attr.ib(default=1.0)
    demand_model = attr.ib(default=None)  # DDA, PDA
    minimum_pressure = attr.ib(default=0.0)
    required_pressure = attr.ib(default=0.0)
    pressure_exponent = attr.ib(default=0.5)
    emitter_exponent = attr.ib(default=0.5)
    trials = attr.ib(default=40)
    accuracy = attr.ib(default=0.001)
    unbalanced = attr.ib(default='STOP')  # STOP, CONTINUE
    unbalanced_value = attr.ib(default=None) #int
    checkfreq = attr.ib(default=2)
    maxcheck = attr.ib(default=10)
    damplimit = attr.ib(default=0)
    headerror = attr.ib(default=0)
    flowchange = attr.ib(default=0)
    inpfile_units = attr.ib(default='GPM', repr=False)  # EPANET unit code

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

    @classmethod
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def todict(self):
        """Dictionary representation of the options"""
        return attr.asdict(self)
    asdict = todict

    def tostring(self):
        """String representation of the hydraulic options"""
        s = 'Hydraulic options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    

@attr.s
class ReactionOptions(object):
    """
    Options related to water quality reactions.
    
    Attributes
    ----------
    bulk_rxn_order : float, default 1.0
        Order of reaction occurring in the bulk fluid
    wall_rxn_order : float, default 1.0
        Order of reaction occurring at the pipe wall
    tank_rxn_order : float, default 1.0
        Order of reaction occurring in the tanks
    bulk_rxn_coeff : float, default 0.0
        Reaction coefficient for bulk fluid and tanks
    wall_rxn_coeff : float, default 0.0
        Reaction coefficient for pipe walls
    limiting_potential : float, default None
        Specifies that reaction rates are proportional to the difference 
        between the current concentration and some limiting potential value, 
        off if None
    roughness_correl : float, default None
        Makes all default pipe wall reaction coefficients related to pipe 
        roughness, off if None
        
    """
    bulk_rxn_order = attr.ib(default=1.0, converter=float)
    wall_rxn_order = attr.ib(default=1.0, converter=float)
    tank_rxn_order = attr.ib(default=1.0, converter=float)
    bulk_rxn_coeff = attr.ib(default=0.0, converter=float)
    wall_rxn_coeff = attr.ib(default=0.0, converter=float)
    limiting_potential = attr.ib(default=None, converter=_float_or_None)
    roughness_correl = attr.ib(default=None, converter=_float_or_None)

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

    @classmethod
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def todict(self):
        """Dictionary representation of the options"""
        return attr.asdict(self)
    asdict = todict

    def tostring(self):
        """String representation of the quality options"""
        s = 'Reaction options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring


@attr.s
class QualityOptions(object):
    """
    Options related to water quality modeling.
    
    Attributes
    ----------
    parameter : str, default 'None'
        Type of water quality analysis.  Options are NONE, CHEMICAL, AGE, and 
        TRACE
    trace_node : str, default None
        Trace node name if quality = TRACE
    chemical : str, default None
        Chemical name for 'chemical' analysis
    diffusivity : float, default 1.0
        Molecular diffusivity of the chemical (default 1.0)
    tolerance : float, default 0.01
        Water quality solver tolerance
    _wq_units : str, default None
        Units for quality analysis; concentration for 'chemical', time in seconds for 'age',
        percentage for 'trace'

    """
    parameter = attr.ib(default='NONE', 
                        validator=in_(['NONE', 'CHEMICAL', 'AGE', 'TRACE']), 
                        converter=str.upper)
    trace_node = attr.ib(default=None)
    chemical_name = attr.ib(default='CHEMICAL')
    diffusivity = attr.ib(default=1.0)
    tolerance = attr.ib(default=0.01)
    _wq_units = attr.ib(default='mg/L', repr=False)

    def __setattr__(self, name, value):
        if name in ['diffusivity', 'tolerance']:
            try:
                value = float(value)
            except ValueError:
                raise ValueError('%s must be a number or None', name)
        self.__dict__[name] = value

    @classmethod
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def todict(self):
        """Dictionary representation of the options"""
        return attr.asdict(self)
    asdict = todict

    def tostring(self):
        """String representation of the quality options"""
        s = 'Water quality options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring
    

@attr.s
class EnergyOptions(object):
    """
    Options related to energy calculations.
    
    Attributes
    ----------
    global_price : float, default 0
        Global average cost per Joule
    global_pattern : str, default None
        ID label of time pattern describing how energy price varies with time
    global_efficiency : float, default 75.0
        Global pump efficiency as percent; i.e., 75.0 means 75%
    demand_charge : float, default None
        Added cost per maximum kW usage during the simulation period, or None
        
    """
    global_price = attr.ib(default=0)
    global_pattern = attr.ib(default=None)
    global_efficiency = attr.ib(default=None)
    demand_charge = attr.ib(default=None)

    @classmethod
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def todict(self):
        """Dictionary representation of the options"""
        return attr.asdict(self)
    asdict = todict

    def tostring(self):
        """String representation of the energy options"""
        s = 'Energy options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring


@attr.s
class ResultsOptions(object):
    """
    Options related to results outputs.

    Attributes
    ----------
    rpt_filename : str
        Provides the filename to use for outputting an EPANET report file.
        By default, this will be the prefix plus ".rpt".
    status : str, default 'NO'
        Output solver status ('YES', 'NO', 'FULL'). 'FULL' is only useful for debugging
    summary : str, default 'YES'
        Output summary information ('YES' or 'NO')
    energy : str, default 'NO'
        Output energy information
    nodes : bool, default False
        Output node information in report file
    links : bool, default False
        Output link information in report file
    
    """
    pagesize = attr.ib(default=None)
    rpt_filename = attr.ib(default=None)
    status = attr.ib(default='NO')
    summary = attr.ib(default='YES')
    energy = attr.ib(default='NO')
    nodes = attr.ib(default=False)
    links = attr.ib(default=False)
    rpt_params = attr.ib(factory=_new_rpt_params)
    results_obj = attr.ib(factory=_new_results_obj)
    param_opts = attr.ib(factory=_new_param_opts)

    @classmethod
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def todict(self):
        """Dictionary representation of the options"""
        return attr.asdict(self)
    asdict = todict

    def tostring(self):
        """String representation of the hydraulic options"""
        s = 'Hydraulic options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring


class UserOptions(object):
    """
    Options defined by the user.
    
    Provides an empty class that accepts getattribute and setattribute methods to
    create user-defined options. For example, if using WNTR for uncertainty 
    quantification, certain options could be added here that would never be 
    used directly by WNTR, but which would be saved on pickling and could be
    used by the user-built analysis scripts.
    
    """
    def __init__(self, **params):
        for k, v in params.items():
            self.__dict__[k] = v

    def todict(self):
        """Dictionary representation of the user options"""
        return self.__dict__.copy()
    
    def tostring(self):
        """String representation of the user options"""
        s = 'UserOptions('
        for k,v in self.__dict__.items():
            s += '{0}={1}, '.format(k, str(v))
        if s.endswith(', '):
            s = s[0:-2] + ')'
        return s
    __repr__ = tostring
    

@attr.s
class WaterNetworkOptions(object):
    """
    Water network model options class.
    
    These options mimic options in the EPANET User Manual.
    The class uses the `__slots__` syntax to ensure that older code will raise 
    an appropriate error -- for example, trying to set the options.duration 
    value will result in an error rather than creating a new attribute 
    (which would never be used and cause undiagnosable errors).
    The `user` attribute is a generic python class object that allows for 
    dynamically created attributes that are user specific.

    Attributes
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
    results : ResultsOptions
        Contains options for how for format and save results
    graphics : GraphicsOptions
        Contains EPANET graphics and background options and also the filename
        for external node coordinates, if used
    user : UserOptions
        An empty class object that allows for storage of user-specific options
    

    """
    time = attr.ib(factory=TimeOptions)
    hydraulic = attr.ib(factory=HydraulicOptions)
    results = attr.ib(factory=ResultsOptions, eq=False)
    quality = attr.ib(factory=QualityOptions)
    reaction = attr.ib(factory=ReactionOptions)
    energy = attr.ib(factory=EnergyOptions)
    graphics = attr.ib(factory=GraphicsOptions)
    user = attr.ib(factory=UserOptions, eq=False)

    def __setattr__(self, name, value):
        if name == 'time':
            if not isinstance(value, (TimeOptions, dict, tuple, list)):
                raise ValueError('time must be a TimeOptions or convertable object')
            value = TimeOptions.factory(value)
        elif name == 'hydraulic':
            if not isinstance(value, (HydraulicOptions, dict, tuple, list)):
                raise ValueError('hydraulic must be a HydraulicOptions or convertable object')
            value = HydraulicOptions.factory(value)
        elif name == 'results':
            if not isinstance(value, (ResultsOptions, dict, tuple, list)):
                raise ValueError('results must be a ResultsOptions or convertable object')
            value = ResultsOptions.factory(value)
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
            if not isinstance(value, (UserOptions, dict)):
                raise ValueError('user must be UserOptions or a dictionary')
            if isinstance(value, dict):
                value = UserOptions(**value)
        else:
            raise ValueError('%s is not a valid member of WaterNetworkModel')
        self.__dict__[name] = value

    @classmethod
    def factory(cls, val):
        """Create an options object based on passing in an instance of the object, a dict, or a tuple"""
        if isinstance(val, cls):
            return val
        elif isinstance(val, dict):
            return cls(**val)
        elif isinstance(val, (list, tuple)):
            return cls(*val)
        raise ValueError('Unknown type for %s.factory: %s',
                         cls.__name__, type(val))

    def todict(self):
        """Dictionary representation of the options"""
        return attr.asdict(self)
    asdict = todict

    def tostring(self):
        """String representation of the energy options"""
        s = 'Energy options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring

