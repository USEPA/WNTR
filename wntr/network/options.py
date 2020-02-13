"""
The wntr.network.options module includes simulation options.

.. rubric:: Contents

.. autosummary::

    WaterNetworkOptions
    TimeOptions
    GraphicsOptions
    HydraulicOptions
    ResultsOptions
    QualityOptions
    EnergyOptions
    SolverOptions
    UserOptions

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

    """
    __slots__ = ['_time','_hydraulic','_results','_quality','_energy','_solver','_graphics','_user']

    def __init__(self):
        self._time = TimeOptions()
        self._hydraulic = HydraulicOptions()
        self._results = ResultsOptions()
        self._quality = QualityOptions()
        self._energy = EnergyOptions()
        self._solver = SolverOptions()
        self._graphics = GraphicsOptions()
        self._user = UserOptions()
        
    def __getstate__(self):
        """Allow pickling with the __slots__ construct"""
        return self._time, self._hydraulic, self._results, self._quality, self._energy, self._solver, self._graphics, self._user
    
    def __setstate__(self, state):
        """Allow pickling with the __slots__ construct"""
        self._time, self._hydraulic, self._results, self._quality, self._energy, self._solver, self._graphics, self._user = state
        
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.time == other.time and \
           self.hydraulic == other.hydraulic and \
           self.quality == other.quality and \
           self.energy == other.energy and \
           self.results.statistic == other.results.statistic and \
           self.solver == other.solver:
               return True
        return False
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    @property
    def time(self):
        """Options related to model timing"""
        return self._time
    
    @time.setter
    def time(self, opts):
        if not isinstance(opts, TimeOptions):
            raise ValueError('time must be a TimeOptions object')
        self._time = opts

    @property
    def hydraulic(self):
        """Options related to the hydraulic model"""
        return self._hydraulic
    
    @hydraulic.setter
    def hydraulic(self, opts):
        if not isinstance(opts, HydraulicOptions):
            raise ValueError('hydraulic must be a HydraulicOptions object')
        self._hydraulic = opts

    @property
    def results(self):
        """Options related to the saving or presentation of results"""
        return self._results
    
    @results.setter
    def results(self, opts):
        if not isinstance(opts, ResultsOptions):
            raise ValueError('results must be a ResultsOptions object')
        self._results = opts

    @property
    def quality(self):
        """Options related to the water quality model"""
        return self._quality
    
    @quality.setter
    def quality(self, opts):
        if not isinstance(opts, QualityOptions):
            raise ValueError('quality must be a QualityOptions object')
        self._quality = opts

    @property
    def energy(self):
        """Options related to energy calculations"""
        return self._energy
    
    @energy.setter
    def energy(self, opts):
        if not isinstance(opts, EnergyOptions):
            raise ValueError('energy must be an EnergyOptions object')
        self._energy = opts

    @property
    def solver(self):
        """Options related to solver configuration"""
        return self._solver
    
    @solver.setter
    def solver(self, opts):
        if not isinstance(opts, SolverOptions):
            raise ValueError('solver must be a SolverOptions object')
        self._solver = opts

    @property
    def graphics(self):
        """Options related to graphics and mapping"""
        return self._graphics
    
    @graphics.setter
    def graphics(self, opts):
        if not isinstance(opts, GraphicsOptions):
            raise ValueError('graphics must be a GraphicsOptions object')
        self._graphics = opts

    @property
    def user(self):
        """User defined options"""
        return self._user
    
    @user.setter
    def user(self, opts):
        if not isinstance(opts, UserOptions):
            raise ValueError('quality must be a UserOptions object')
        self._user = opts

    def todict(self):
        """Dictionary representation of the model options"""
        return dict(time=self._time.todict(),
                    hydraulic=self._hydraulic.todict(),
                    quality=self._quality.todict(),
                    energy=self._energy.todict(),
                    solver=self._solver.todict(),
                    results=self._results.todict(),
                    graphics=self._graphics.todict(),
                    user=self._user.todict())
    
    def tostring(self):
        """String representation of the model options"""
        s = ''
        s += repr(self.time)
        s += repr(self.hydraulic)
        s += repr(self.quality)
        s += repr(self.energy)
        s += repr(self.solver)
        s += repr(self.results)
        s += repr(self.graphics)
        s += repr(self.user)
        return s
    __repr__ = tostring


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
        if abs(self.duration - other.duration)<1e-9 and \
           abs(self.hydraulic_timestep - other.hydraulic_timestep)<1e-9 and \
           abs(self.quality_timestep - other.quality_timestep)<1e-9 and \
           abs(self.rule_timestep - other.rule_timestep)<1e-9 and \
           abs(self.pattern_timestep - other.pattern_timestep)<1e-9 and \
           abs(self.pattern_start - other.pattern_start)<1e-9 and \
           abs(self.report_timestep - other.report_timestep)<1e-9 and \
           abs(self.report_start - other.report_start)<1e-9 and \
           abs(self.start_clocktime - other.start_clocktime)<1e-9:
               return True
        return False

    def __ne__(self, other):
        return not self == other
    
    def todict(self):
        """Dictionary representation of the time options"""
        return self.__dict__.copy()

    def tostring(self):
        """String representation of the time options"""
        s = 'Time options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring
    

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
    def __init__(self):
        self.dimensions = None
        self.units = None
        self.offset = None
        self.image_filename = None
        self.map_filename = None
    
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if abs(self.dimensions[0] - other.dimensions[0])<1e-9 and \
           abs(self.dimensions[1] - other.dimensions[1])<1e-9 and \
           abs(self.dimensions[2] - other.dimensions[2])<1e-9 and \
           abs(self.dimensions[3] - other.dimensions[3])<1e-9 and \
           self.units == other.units and \
           abs(self.offset[0] - other.offset[0])<1e-9 and \
           abs(self.offset[1] - other.offset[1])<1e-9 and \
           self.image_filename == other.image_filename and \
           self.map_filename == other.map_filename:
               return True
        return False

    def __ne__(self, other):
        return not self == other
    
    def todict(self):
        """Dictionary representation of the graphics options"""
        return self.__dict__.copy()
   
    def tostring(self):
        """String representation of the graphics options"""
        s = 'Graphics options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring
    

class HydraulicOptions(object): 
    """
    Options related to hydraulic model, including hydraulics. 
    
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
    minimum_pressure : float, default None
        The minimum nodal pressure - ONLY valid for EPANET 2.2
    required_pressure: float, default None
        The required nodal pressure - ONLY valid for EPANET 2.2
    pressure_exponent: float, default None
        The pressure exponent - ONLY valid for EPANET 2.2
    
    """
    def __init__(self):
        # General options
        self.en2_units = 'GPM'
        self.headloss = 'H-W'
        self.hydraulics = None #string
        self.hydraulics_filename = None #string
        self.viscosity = 1.0
        self.specific_gravity = 1.0
        self.pattern = '1'
        self.demand_multiplier = 1.0
        self.emitter_exponent = 0.5
        self.minimum_pressure = None
        self.required_pressure = None
        self.pressure_exponenet = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.headloss == other.headloss and \
           self.hydraulics == other.hydraulics and \
           self.hydraulics_filename == other.hydraulics_filename and \
           abs(self.viscosity - other.viscosity)<1e-9 and \
           abs(self.specific_gravity - other.specific_gravity)<1e-9 and \
           self.pattern == other.pattern and \
           abs(self.demand_multiplier - other.demand_multiplier)<1e-9 and \
           abs(self.emitter_exponent - other.emitter_exponent)<1e-9:
               return True
        return False

    def __ne__(self, other):
        return not self == other

    def todict(self):
        """Dictionary representation of the hydraulic options"""
        return self.__dict__.copy()
    
    def tostring(self):
        """String representation of the hydraulic options"""
        s = 'Hydraulic options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring
    

class ResultsOptions(object):
    """
    Options related to results outputs.

    Attributes
    ----------
    statistic : str, default 'None'
        Output results as statistical values, rather than time-series; options 
        are AVERAGED, MINIMUM, MAXIUM, RANGE, and NONE (as defined in the 
        EPANET User Manual)
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
    def __init__(self):
        self.statistic = 'NONE'
        self.pagesize = None
        self.rpt_filename = None
        self.status = 'NO'
        self.summary = 'YES'
        self.energy = 'NO'
        self.nodes = False
        self.links = False
        self.rpt_params = { 
                           'elevation': False,
                           'demand': True,
                           'head': True,
                           'pressure': True,
                           'quality': True,
                           'length': False,
                           'diameter': False,
                           'flow': True,
                           'velocity': True,
                           'headloss': True,
                           'position': False,
                           'setting': False,
                           'reaction': False,
                           'f-factor': False,
                           }
        self.results_obj = { # Node extended period results
                           'demand': True,     #node demand (actual)
                           'head': True,       #node head
                           'pressure': True,   #node pressure
                           'quality': True,    #node quality
                           # Link extended period results
                           'flow': True,       #flow in pipes
                           'linkquality': True,#quality in pipes
                           'velocity': True,   #velocity in pipes
                           'headloss': True,   #headloss in pipes
                           'status': True,     #link status
                           'setting': True,    #valve/pump setting
                           'rxnrate': True,    #reaction rate in pipes
                           'frictionfact': True,   #friction factor in pipes
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
           self.rpt_filename == other.rpt_filename and \
           self.status == other.status and \
           self.summary == other.summary and \
           self.energy == other.energy and \
           self.nodes == other.nodes and \
           self.links == other.links:
               return True
        return False

    def __ne__(self, other):
        return not self == other

    def todict(self):
        """Dictionary representation of the results options"""
        return self.__dict__.copy()
   
    def tostring(self):
        """String representation of the results options"""
        s = 'Results options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring
     
        
class QualityOptions(object):
    """
    Options related to water quality modeling.
    
    Attributes
    ----------
    mode : str, default 'None'
        Type of water quality analysis.  Options are NONE, CHEMICAL, AGE, and 
        TRACE
    trace_node : str, default None
        Trace node name if quality = TRACE
    wq_units : str, default None
        Units for quality analysis; concentration for 'chemical', 's' for 'age',
        '%' for 'trace'
    chemical : str, default None
        Chemical name for 'chemical' analysis
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
    roughness_correl : float, default None
        Makes all default pipe wall reaction coefficients related to pipe 
        roughness, off if None
        
    """
    def __init__(self):
        self.mode = 'NONE'
        self.trace_node = None #string 
        self.wq_units = 'mg/L' #string (mg/L or ug/L)
        self.chemical_name = 'CHEMICAL' #string
        self.diffusivity = 1.0
        self.bulk_rxn_order = 1.0
        self.wall_rxn_order = 1.0
        self.tank_rxn_order = 1.0
        self.bulk_rxn_coeff = 0.0
        self.wall_rxn_coeff = 0.0
        self.limiting_potential = None
        self.roughness_correl = None

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        if self.mode != other.mode and \
           self.trace_node != other.trace_node and \
           self.wq_units != other.wq_units and \
           self.chemical_name != other.chemical_name and \
           abs(self.diffusivity - other.diffusivity)>1e-9 and \
           abs(self.bulk_rxn_order - other.bulk_rxn_order)>1e-9 and \
           abs(self.wall_rxn_order - other.wall_rxn_order)>1e-9 and \
           abs(self.tank_rxn_order - other.tank_rxn_order)>1e-9 and \
           abs(self.bulk_rxn_coeff - other.bulk_rxn_coeff)>1e-9 and \
           abs(self.wall_rxn_coeff - other.wall_rxn_coeff)>1e-9:
               return False
        if self.limiting_potential and other.limiting_potential:
            if abs(self.limiting_potential - other.limiting_potential)>1e-9:
                return False
        if self.limiting_potential or other.limiting_potential:
            return False
        if self.roughness_correl and other.roughness_correl:
            if abs(self.roughness_correl - other.roughness_correl)>1e-9:
                return False
        if self.roughness_correl or other.roughness_correl:
            return False
        return True

    def __ne__(self, other):
        return not self == other

    def todict(self):
        """Dictionary representation of the quality options"""
        return self.__dict__.copy()
   
    def tostring(self):
        """String representation of the quality options"""
        s = 'Water quality options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring
    

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
        if abs(self.global_price - other.global_price)>1e-9 and \
           self.global_pattern != other.global_pattern and \
           abs(self.global_efficiency - other.global_efficiency)>1e-9:
               return False
        if self.demand_charge and other.demand_charge:
            if abs(self.demand_charge - other.demand_charge)>1e-9:
               return False
        if self.demand_charge and other.demand_charge:
            return False
        return True

    def __ne__(self, other):
        return not self == other

    def todict(self):
        """Dictionary representation of the energy options"""
        return self.__dict__.copy()
    
    def tostring(self):
        """String representation of the energy options"""
        s = 'Energy options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring


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
    headerror : float, default None
        The head error convergence limit
    flowchange : float, default None
        The flow change convergence limit
        
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
        self.headerror = None
        self.flowchange = None
        self.demand_model = None
        
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if abs(self.trials - other.trials)<1e-9 and \
           abs(self.accuracy - other.accuracy)<1e-9 and \
           self.unbalanced == other.unbalanced and \
           self.demand_model == other.demand_model and \
           abs(self.tolerance - other.tolerance)<1e-9 and \
           abs(self.checkfreq - other.checkfreq)<1e-9 and \
           abs(self.maxcheck - other.maxcheck)<1e-9 and \
           abs(self.damplimit - other.damplimit)<1e-9:
               return True
        return False

    def __ne__(self, other):
        return not self == other

    def todict(self):
        """Dictionary representation of the solver options"""
        return self.__dict__.copy()
    
    def tostring(self):
        """String representation of the solver options"""
        s = 'Solver options:\n'
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
    def __init__(self):
        pass

    def todict(self):
        """Dictionary representation of the user options"""
        return self.__dict__.copy()
    
    def tostring(self):
        """String representation of the user options"""
        s = 'User options:\n'
        for k,v in self.__dict__.items():
            s += '  {0:<20}: {1:<20}\n'.format(k, str(v))
        return s
    __repr__ = tostring
    