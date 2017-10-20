"""
Water Network Model Options Classes
"""

## Start with the component classes

class TimeOptions(object):
    def __init__(self):
        # Time related options
        self.duration = 0
        "Simulation duration in seconds"

        self.hydraulic_timestep = 3600
        "Hydraulic timestep in seconds."

        self.quality_timestep = 360.0
        "Water quality timestep in seconds"

        self.rule_timestep = 360.0
        "Rule timestep in seconds"

        self.pattern_timestep = 3600.0
        "Pattern timestep in seconds"

        self.pattern_start = 0.0
        "Time offset in seconds at which all patterns will start. E.g., a value of 7200 would start the simulation with each pattern in the time period that corresponds to hour 2."

        self.report_timestep = 3600.0
        "Reporting timestep in seconds"

        self.report_start = 0.0
        "Start time of the report in seconds from the start of the simulation."

        self.start_clocktime = 0.0
        "Time of day in seconds from 12 am at which the simulation begins."

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
    """An epanet backdrop object."""
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
    def __init__(self):
        # General options
        self.units = 'GPM'
        "EPANET INP File units of measurement.  Options are CFS, GPM, MGD, IMGD, AFD, LPS, LPM, MLD, CMH, and CMD (as defined in the EPANET User Manual)."

        self.headloss = 'H-W'
        "Formula to use for computing head loss through a pipe. Options are H-W, D-W, and C-M (as defined in the EPANET User Manual)."

        self.hydraulics = None #string
        "Indicates if a hydraulics file should be used or saved.  Options are USE and SAVE (as defined in the EPANET User Manual)."

        self.hydraulics_filename = None #string
        "Filename to use if hydraulics = SAVE"

        self.viscosity = 1.0
        "Kinematic viscosity of the fluid"

        self.diffusivity = 1.0
        "Molecular diffusivity of the chemical"

        self.specific_gravity = 1.0
        "Specific gravity of the fluid"
        

        self.pattern = None
        "Name of the default pattern for junction demands. If None, the junctions without patterns will be held constant."

        self.demand_multiplier = 1.0
        "The demand multiplier adjusts the values of baseline demands for all junctions"

        self.emitter_exponent = 0.5
        "The exponent used when computing flow from an emitter"

        self.map = None
        "Filename used to store node coordinates"
        
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.headloss == other.headloss and \
           self.hydraulics == other.hydraulics and \
           self.hydraulics_filename == other.hydraulics_filename and \
           abs(self.viscosity - other.viscosity)<1e-10 and \
           abs(self.diffusivity - other.diffusivity)<1e-10 and \
           abs(self.specific_gravity - other.specific_gravity)<1e-10 and \
           self.pattern == other.pattern and \
           abs(self.demand_multiplier - other.demand_multiplier)<1e-10 and \
           abs(self.emitter_exponent - other.emitter_exponent)<1e-10 and \
           self.map == other.map:
               return True
        return False


class ResultsOptions(object):
    def __init__(self):
        self.statistic = 'NONE'
        "Post processing statistic.  Options are AVERAGED, MINIMUM, MAXIUM, RANGE, and NONE (as defined in the EPANET User Manual)."
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
    def __init__(self):
        self.type = 'NONE'
        "Type of water quality analysis.  Options are NONE, CHEMICAL, AGE, and TRACE (as defined in the EPANET User Manual)."

        self.value = None #string
        "Trace node name if quality = TRACE, Chemical units if quality = CHEMICAL"

        # Reaction options
        self.bulk_rxn_order = 1.0
        "Order of reaction occurring in the bulk fluid"

        self.wall_rxn_order = 1.0
        "Order of reaction occurring at the pipe wall"

        self.tank_rxn_order = 1.0
        "Order of reaction occurring in the tanks"

        self.bulk_rxn_coeff = 0.0
        "Reaction coefficient for bulk fluid and tanks"

        self.wall_rxn_coeff = 0.0
        "Reaction coefficient for pipe walls"

        self.limiting_potential = None
        "Specifies that reaction rates are proportional to the difference between the current concentration and some limiting potential value"

        self.roughness_correlation = None
        "Makes all default pipe wall reaction coefficients related to pipe roughness"

    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.type == other.type and \
           self.value == other.value and \
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
    """An epanet energy definitions object."""
    def __init__(self):
        self.global_price = 0
        """Global average cost per Joule (default 0)"""
        self.global_pattern = None
        """ID label of time pattern describing how energy price varies with time"""
        self.global_efficiency = 75.0
        """Global pump efficiency as percent; i.e., 75.0 means 75% (default 75%)"""
        self.demand_charge = None
        """Added cost per maximum kW usage during the simulation period"""
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
    def __init__(self):
        self.trials = 40
        "Maximum number of trials used to solve network hydraulics"
        self.accuracy = 0.001
        "Convergence criteria for hydraulic solutions"
        self.unbalanced = 'STOP'
        "Indicate what happens if a hydraulic solution cannot be reached.  Options are STOP and CONTINUE  (as defined in the EPANET User Manual)."
        self.unbalanced_value = None #int
        "Number of additional trials if unbalanced = CONTINUE"
        self.tolerance = 0.01
        "Convergence criteria for water quality solutions"
        self.checkfreq = 2
        "Number of solution trials that pass between status check"
        self.maxcheck = 10
        "Number of solution trials that pass between status check"
        self.damplimit = 0
        "Accuracy value at which solution damping begins"

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


class WaterNetworkOptions(object):
    """
    A class to manage options.  These options mimic options in the EPANET User Manual.
    """

    def __init__(self):
        self.time = TimeOptions()
        self.general = GeneralOptions()
        self.results = ResultsOptions()
        self.quality = QualityOptions()
        self.energy = EnergyOptions()
        self.solver = SolverOptions()
        self.graphics = GraphicsOptions()
        
    def __eq__(self, other):
        if not type(self) == type(other):
            return False
        ###  self.units == other.units and \
        if self.time == other.time and \
           self.general == other.general and \
           self.results == other.results and \
           self.quality == other.quality and \
           self.energy == other.energy and \
           self.solver == other.solver and \
           self.graphics == other.graphics:
               return True
        return False
