"""
Water Network Model Options Classes

Provides the classes that make up the WNTR options for a model and to pass to solvers.

"""


class WaterNetworkOptions(object):
    """
    A class to manage options.  These options mimic options in the EPANET User Manual.

    This class now uses the `__slots__` syntax to ensure that older code will raise an appropriate
    error -- for example, trying to set the options.duration value will result in an error 
    rather than creating a new attribute (which would never be used and cause undiagnosable errors).
    
    The `user` attribute is a generic python class object that allows for dynamically created 
    attributes that are user specific; core WNTR functionality will never use options in the `user`
    section, but 3-rd party libraries or add-ons may.
        
    Attributes
    ----------
    time : :class:`~TimeOptions`
        All options related to model timing
    general : :class:`~GeneralOptions`
        General WNTR model options
    results : :class:`~ResultsOptions`
        Options related to the saving or presentaion of results
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


## Start with the component classes

class TimeOptions(object):
    """All options relating to simulation and model timing.
    
    Attributes
    ----------
    duration
        Simulation duration in seconds (default 0)
    hydraulic_timestep
        Hydraulic timestep in seconds (default 3600)
    quality_timestep
        Water quality timestep in seconds (default 360)
    rule_timestep
        Rule timestep in seconds (default 360)
    pattern_timestep
        Pattern timestep in seconds (default 3600)
    pattern_start
        Time offset (in seconds) to find the starting pattern step; changes where in pattern
        the pattern starts out, *not* what time the pattern starts (default 0)
    report_timestep
        Reporting timestep in seconds (default 3600)
    report_start
        Start time of the report in seconds from the start of the simulation (default 0)
    start_clocktime
        Time of day in seconds from 12 am at which the simulation begins (default 0)
    
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


class GraphicsOptions(object):
    """All options relating to graphics. 
    
    May be used to contain custom, user defined values. Default attributes comprise the
    EPANET "backdrop" section options.
    
    Attributes
    ----------
    dimensions
        (x, y, dx, dy) Dimensions for backdrop image 
    units
        Units for backdrop image
    filename
        Filename where image is located
    offset
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


class GeneralOptions(object):
    """All options relating to general model, including hydraulics.
    
    Attributes
    ----------
    units
        Input/output units (EPANET); options are CFS, GPM, MGD, IMGD, AFD, LPS, LPM, MLD, CMH, and CMD (default is GPM)
    headloss
        Formula to use for computing head loss through a pipe. Options are H-W, D-W, and C-M (default is H-W)
    hydraulics
        Indicates if a hydraulics file should be read in or saved; options are None, USE and SAVE (as defined in the EPANET User Manual).
    hydraulics_filename
        Filename to use if hydraulics = SAVE
    viscosity
        Kinematic viscosity of the fluid
    specific_gravity
        Specific gravity of the fluid
    pattern
        Name of the default pattern for junction demands. If None, the junctions with demands but without patterns will be held constant
    demand_multiplier
        The demand multiplier adjusts the values of baseline demands for all junctions
    emitter_exponent
        The exponent used when computing flow from an emitter
    map
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


class ResultsOptions(object):
    """All options relating to results outputs.

    Attributes
    ----------
    statistic
        Output results as statistical values, rather than time-series; options are AVERAGED, MINIMUM, MAXIUM, RANGE, and NONE (as defined in the EPANET User Manual).

        
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
        
        
class QualityOptions(object):
    """All options relating to water quality modeling.
    
    Attributes
    ----------
    analysis_type
        Type of water quality analysis.  Options are NONE, CHEMICAL, AGE, and TRACE (as defined in the EPANET User Manual)
    trace_node
        Trace node name if quality = TRACE
    concentration_units
        Chemical units if quality = CHEMICAL
    diffusivity
        Molecular diffusivity of the chemical
    bulk_rxn_order
        Order of reaction occurring in the bulk fluid
    wall_rxn_order
        Order of reaction occurring at the pipe wall
    tank_rxn_order
        Order of reaction occurring in the tanks
    bulk_rxn_coeff        
        Reaction coefficient for bulk fluid and tanks
    wall_rxn_coeff
        Reaction coefficient for pipe walls
    limiting_potential
        Specifies that reaction rates are proportional to the difference between the current concentration and some limiting potential value
    roughness_correlation
        Makes all default pipe wall reaction coefficients related to pipe roughness
        
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


class EnergyOptions(object):
    """All options relating to energy calculations.
    
    Attributes
    ----------
    global_price
        Global average cost per Joule (default 0)
    global_pattern
        ID label of time pattern describing how energy price varies with time
    global_efficiency
        Global pump efficiency as percent; i.e., 75.0 means 75% (default 75%)
    demand_charge
        Added cost per maximum kW usage during the simulation period
    
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


class SolverOptions(object):
    """All options relating to solver options (for any solver).

    Attributes
    ----------
    trials
        Maximum number of trials used to solve network hydraulics
    accuracy
        Convergence criteria for hydraulic solutions
    unbalanced
        Indicate what happens if a hydraulic solution cannot be reached.  Options are STOP and CONTINUE  (as defined in the EPANET User Manual).
    unbalanced_value
        Number of additional trials if unbalanced = CONTINUE
    tolerance
        Convergence criteria for water quality solutions
    checkfreq
        Number of solution trials that pass between status check
    maxcheck
        Number of solution trials that pass between status check
    damplimit
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


class UserOptions(object):
    """This is a generic user options dictionary to allow for private extensions
    
    Allows users to add attributes for their own personal use under options.user.*
    
    """
    def __init__(self):
        pass

