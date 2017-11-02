"""
The wntr.network.options module includes simulation options.
"""
import logging

logger = logging.getLogger(__name__)

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
    time : :class:`~TimeOptions`
        All options related to model timing
    general : :class:`~GeneralOptions`
        General WNTR model options
    results : :class:`~ResultsOptions`
        Options related to the saving or presentation of results
    quality : :class:`~QualityOptions`
        Water quality model options
    energy : :class:`~EnergyOptions`
        Energy calculation options
    solver : :class:`~SolverOptions`
        Solver configuration options
    graphics : :class:`~GraphicsOptions`
        Graphics and mapping options
    user : :class:`~UserOptions`
        Space for end-user defined options
    """
    __slots__ = ['time','general','results','quality','energy','solver','graphics','user']

    def __init__(self):
        self.time = TimeOptions()
        self.general = GeneralOptions()
        self.results = ResultsOptions()
        self.quality = QualityOptions()
        self.energy = EnergyOptions()
        self.solver = SolverOptions()
        self.graphics = GraphicsOptions()
        self.user = UserOptions()
        
    def __getstate__(self):
        """Allow pickling with the __slots__ construct"""
        return self.time, self.general, self.results, self.quality, self.energy, self.solver, self.graphics, self.user
    
    def __setstate__(self, state):
        """Allow pickling with the __slots__ construct"""
        self.time, self.general, self.results, self.quality, self.energy, self.solver, self.graphics, self.user = state
        
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.time == other.time and \
           self.general == other.general and \
           self.quality == other.quality and \
           self.energy == other.energy and \
           self.results.statistic == other.results.statistic and \
           self.solver == other.solver:
               return True
        return False
    
    def __ne__(self, other):
        return not self.__eq__(other)

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
    """
    def __init__(self):
        # Time related options
        self.duration = 0
        self.hydraulic_timestep = 3600
        self.quality_timestep = 360.0
        self.rule_timestep = 360.0
        self.pattern_timestep = 3600.0
        self.pattern_start = 0.0
        self.report_timestep = 3600.0
        self.report_start = 0.0
        self.start_clocktime = 0.0

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if abs(self.duration - other.duration)<1e-10 and \
           abs(self.hydraulic_timestep - other.hydraulic_timestep)<1e-10 and \
           abs(self.quality_timestep - other.quality_timestep)<1e-10 and \
           abs(self.rule_timestep - other.rule_timestep)<1e-10 and \
           abs(self.pattern_timestep - other.pattern_timestep)<1e-10 and \
           abs(self.pattern_start - other.pattern_start)<1e-10 and \
           abs(self.report_timestep - other.report_timestep)<1e-10 and \
           abs(self.report_start - other.report_start)<1e-10 and \
           abs(self.start_clocktime - other.start_clocktime)<1e-10:
               return True
        return False

    def __repr__(self):
        s = 'Time options:\n'
        s += '\t{0:<20}: {1:<20}\n'.format('duration', self.duration)
        s += '\t{0:<20}: {1:<20}\n'.format('hydraulic_timestep', self.hydraulic_timestep)
        s += '\t{0:<20}: {1:<20}\n'.format('quality_timestep', self.quality_timestep)
        s += '\t{0:<20}: {1:<20}\n'.format('rule_timestep', self.rule_timestep)
        s += '\t{0:<20}: {1:<20}\n'.format('pattern_timestep', self.pattern_timestep)
        s += '\t{0:<20}: {1:<20}\n'.format('pattern_start', self.pattern_start)
        s += '\t{0:<20}: {1:<20}\n'.format('report_timestep', self.report_timestep)
        s += '\t{0:<20}: {1:<20}\n'.format('report_start', self.report_start)
        s += '\t{0:<20}: {1:<20}\n'.format('start_clocktime', self.start_clocktime)
        return s

    def __str__(self):
        return self.__repr__()

    def __ne__(self, other):
        return not self == other


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
    filename : str
        Filename where image is located
    offset : 2-tuple or list
        (x,y) offset for the network
    """
    def __init__(self, filename=None, dim=None, units=None, offset=None):
        self.dimensions = dim
        self.units = units
        self.filename = filename
        self.offset = offset

    def __str__(self):
        text = ""
        if self.dimensions is not None:
            text += "DIMENSIONS {} {} {} {}\n".format(self.dimensions[0],
                                                      self.dimensions[1],
                                                      self.dimensions[2],
                                                      self.dimensions[3])
        if self.units is not None:
            text += "UNITS {}\n".format(self.units)
        if self.filename is not None:
            text += "FILE {}\n".format(self.filename)
        if self.offset is not None:
            text += "OFFSET {} {}\n".format(self.offset[0], self.offset[1])
        return text

class GeneralOptions(object): # KAK, HydraulicOptions?
    """
    Options related to general model, including hydraulics. 
    
    Attributes
    ----------
    units : str, default 'GPM'
        Input/output units (EPANET); options are CFS, GPM, MGD, IMGD, AFD, LPS, 
        LPM, MLD, CMH, and CMD
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
    map : str
        Filename used to store node coordinates in (node, x, y) format
    """
    def __init__(self):
        # General options
        self.units = 'GPM'
        self.headloss = 'H-W'
        self.hydraulics = None #string
        self.hydraulics_filename = None #string
        self.viscosity = 1.0
        self.specific_gravity = 1.0
        self.pattern = None
        self.demand_multiplier = 1.0
        self.emitter_exponent = 0.5
        self.map = None
        
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.headloss == other.headloss and \
           self.hydraulics == other.hydraulics and \
           self.hydraulics_filename == other.hydraulics_filename and \
           abs(self.viscosity - other.viscosity)<1e-10 and \
           abs(self.specific_gravity - other.specific_gravity)<1e-10 and \
           self.pattern == other.pattern and \
           abs(self.demand_multiplier - other.demand_multiplier)<1e-10 and \
           abs(self.emitter_exponent - other.emitter_exponent)<1e-10 and \
           self.map == other.map:
               return True
        return False

    def __ne__(self, other):
        return not self == other



class ResultsOptions(object):
    """
    Options related to results outputs.

    Attributes
    ----------
    statistic : str, default 'None'
        Output results as statistical values, rather than time-series; options 
        are AVERAGED, MINIMUM, MAXIUM, RANGE, and NONE (as defined in the 
        EPANET User Manual)
    """
    def __init__(self):
        self.statistic = 'NONE'
        self.pagesize = 0
        self.file = None
        self.status = 'NO'
        self.summary = 'YES'
        self.energy = 'NO'
        self.nodes = False
        self.links = False
        self.rpt_params = { # param name: [Default, Setting]
                           'elevation': [False, False],
                           'demand': [True, True],
                           'head': [True, True],
                           'pressure': [True, True],
                           'quality': [True, True],
                           'length': [False, False],
                           'diameter': [False, False],
                           'flow': [True, True],
                           'velocity': [True, True],
                           'headloss': [True, True],
                           'position': [False, False],
                           'setting': [False, False],
                           'reaction': [False, False],
                           'f-factor': [False, False],
                           }
        self.param_opts = { # param name: [Default, Setting]
                           'elevation': {},
                           'demand': {},
                           'head': {},
                           'pressure': {},
                           'quality': {},
                           'length': {},
                           'diameter': {},
                           'flow': {},
                           'velocity': {},
                           'headloss': {},
                           'position': {},
                           'setting': {},
                           'reaction': {},
                           'f-factor': {},
                           }        
        
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.statistic == other.statistic and \
           self.pagesize == other.pagesize and \
           self.file == other.file and \
           self.status == other.status and \
           self.summary == other.summary and \
           self.energy == other.energy and \
           self.nodes == other.nodes and \
           self.links == other.links:
               return True
        return False

    def __ne__(self, other):
        return not self == other

        
        
class QualityOptions(object):
    """
    Options related to water quality modeling.
    
    Attributes
    ----------
    analysis_type : str, default 'None'
        Type of water quality analysis.  Options are NONE, CHEMICAL, AGE, and 
        TRACE
    trace_node : str
        Trace node name if quality = TRACE
    concentration_units : str, default = 'mg/L'
        Units for chemical analysis
    diffusivity : float, default 1.0
        Molecular diffusivity of the chemical (default 1.0)
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
    roughness_correlation : float, default None
        Makes all default pipe wall reaction coefficients related to pipe 
        roughness, off if None
    """
    def __init__(self):
        self.type = 'NONE'
        self.value = None #string
        self.diffusivity = 1.0
        self.bulk_rxn_order = 1.0
        self.wall_rxn_order = 1.0
        self.tank_rxn_order = 1.0
        self.bulk_rxn_coeff = 0.0
        self.wall_rxn_coeff = 0.0
        self.limiting_potential = None
        self.roughness_correlation = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.type == other.type and \
           self.value == other.value and \
           abs(self.diffusivity - other.diffusivity)<1e-10 and \
           abs(self.bulk_rxn_order - other.bulk_rxn_order)<1e-10 and \
           abs(self.wall_rxn_order - other.wall_rxn_order)<1e-10 and \
           abs(self.tank_rxn_order - other.tank_rxn_order)<1e-10 and \
           abs(self.bulk_rxn_coeff - other.bulk_rxn_coeff)<1e-10 and \
           abs(self.wall_rxn_coeff - other.wall_rxn_coeff)<1e-10 and \
           abs(self.limiting_potential - other.limiting_potential)<1e-10 and \
           abs(self.roughness_correlation - other.roughness_correlation)<1e-10:
               return True
        return False

    def __ne__(self, other):
        return not self == other


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
    def __init__(self):
        self.global_price = 0
        self.global_pattern = None
        self.global_efficiency = 75.0
        self.demand_charge = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if abs(self.global_price - other.global_price)<1e-10 and \
           self.global_pattern == other.global_pattern and \
           abs(self.global_efficiency - other.global_efficiency)<1e-10 and \
           abs(self.demand_charge - other.demand_charge)<1e-10:
               return True
        return False

    def __ne__(self, other):
        return not self == other


class SolverOptions(object):
    """
    Options related to solver options (for any solver).

    Attributes
    ----------
    trials : int, default 40
        Maximum number of trials used to solve network hydraulics
    accuracy : float, default 0.001
        Convergence criteria for hydraulic solutions (default 0.001)
    unbalanced : str, default 'STOP'
        Indicate what happens if a hydraulic solution cannot be reached.  
        Options are STOP and CONTINUE
    unbalanced_value : int, default None
        Number of additional trials if unbalanced = CONTINUE
    tolerance : float, default 0.01
        Convergence criteria for water quality solutions
    checkfreq : int, default 2
        Number of solution trials that pass between status check 
    maxcheck : int, default 10
        Number of solution trials that pass between status check 
    damplimit : float, default 0.0
        Accuracy value at which solution damping begins
    """
    def __init__(self):
        self.trials = 40
        self.accuracy = 0.001
        self.unbalanced = 'STOP'
        self.unbalanced_value = None #int
        self.tolerance = 0.01
        self.checkfreq = 2
        self.maxcheck = 10
        self.damplimit = 0

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if abs(self.trials - other.trials)<1e-10 and \
           abs(self.accuracy - other.accuracy)<1e-10 and \
           self.unbalanced == other.unbalanced and \
           abs(self.tolerance - other.tolerance)<1e-10 and \
           abs(self.checkfreq - other.checkfreq)<1e-10 and \
           abs(self.maxcheck - other.maxcheck)<1e-10 and \
           abs(self.damplimit - other.damplimit)<1e-10:
               return True
        return False

    def __ne__(self, other):
        return not self == other


class UserOptions(object):
    """
    Options defined by the user.
    """
    def __init__(self):
        pass
