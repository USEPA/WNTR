"""EPANET-MSX enum types, for use in toolkit API calls."""

from enum import IntEnum
from wntr.utils.enumtools import add_get

@add_get(prefix='MSX_')
class ObjectType(IntEnum):
    """The enumeration for object type used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    NODE = 0
    LINK = 1
    PIPE = 1
    TANK = 2
    SPECIES = 3
    TERM = 4
    PARAMETER = 5
    CONSTANT = 6
    PATTERN = 7
    MAX_OBJECTS = 8


@add_get(prefix='MSX_')
class SourceType(IntEnum):
    """The enumeration for source type used in EPANET-MSX.
    
    .. warning:: These enum values start with -1.
    """
    NOSOURCE = -1
    CONCEN = 0
    MASS = 1
    SETPOINT = 2
    FLOWPACED = 3


@add_get(prefix='MSX_')
class UnitSystemType(IntEnum):
    """The enumeration for the units system used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    US = 0
    SI = 1


@add_get(prefix='MSX_')
class FlowUnitsType(IntEnum):
    """The enumeration for the flow units used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    CFS = 0
    GPM = 1
    MGD = 2
    IMGD = 3
    AFD = 4
    LPS = 5
    LPM = 6
    MLD = 7
    CMH = 8
    CMD = 9


@add_get(prefix='MSX_')
class MixType(IntEnum):
    """The enumeration for the mixing model used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    MIX1 = 0
    MIX2 = 1
    FIFO = 2
    LIFO = 3


@add_get(prefix='MSX_')
class SpeciesType(IntEnum):
    """The enumeration for species type used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    BULK = 0
    WALL = 1


@add_get(prefix='MSX_')
class ExpressionType(IntEnum):
    """The enumeration for the expression type used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    NO_EXPR = 0
    RATE = 1
    FORMULA = 2
    EQUIL = 3


@add_get(prefix='MSX_')
class SolverType(IntEnum):
    """The enumeration for the solver type used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    EUL = 0
    RK5 = 1
    ROS2 = 2


@add_get(prefix='MSX_')
class CouplingType(IntEnum):
    """The enumeration for the coupling type option used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    NO_COUPLING = 0
    FULL_COUPLING = 1


@add_get(prefix='MSX_')
class MassUnitsType(IntEnum):
    """The enumeration for mass units used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    MG = 0
    UG = 1
    MOLE = 2
    MMOLE = 3


@add_get(prefix='MSX_')
class AreaUnitsType(IntEnum):
    """The enumeration for area units used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    FT2 = 0
    M2 = 1
    CM2 = 2


@add_get(prefix='MSX_')
class RateUnitsType(IntEnum):
    """The enumeration for rate units used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    SECONDS = 0
    MINUTES = 1
    HOURS = 2
    DAYS = 3


@add_get(prefix='MSX_')
class UnitsType(IntEnum):
    """The enumerations for units used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    LENGTH_UNITS = 0
    DIAM_UNITS = 1
    AREA_UNITS = 2
    VOL_UNITS = 3
    FLOW_UNITS = 4
    CONC_UNITS = 5
    RATE_UNITS = 6
    MAX_UNIT_TYPES = 7


@add_get(prefix='MSX_')
class HydVarType(IntEnum):
    """The enumeration for hydraulic variable used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    DIAMETER = 1
    FLOW = 2
    VELOCITY = 3
    REYNOLDS = 4
    SHEAR = 5
    FRICTION = 6
    AREAVOL = 7
    ROUGHNESS = 8
    LENGTH = 9
    MAX_HYD_VARS = 10


@add_get(prefix='MSX_')
class TstatType(IntEnum):
    """The enumeration used for time statistic in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    SERIES = 0
    AVERAGE = 1
    MINIMUM = 2
    MAXIMUM = 3
    RANGE = 4


@add_get(prefix='MSX_')
class OptionType(IntEnum):
    """The enumeration used for option in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    AREA_UNITS_OPTION = 0
    RATE_UNITS_OPTION = 1
    SOLVER_OPTION = 2
    COUPLING_OPTION = 3
    TIMESTEP_OPTION = 4
    RTOL_OPTION = 5
    ATOL_OPTION = 6
    COMPILER_OPTION =7
    MAXSEGMENT_OPTION = 8
    PECLETNUMBER_OPTION = 9


@add_get(prefix='MSX_')
class CompilerType(IntEnum):
    """The enumeration used for specifying compiler options in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    NO_COMPILER = 0
    VC = 1
    GC = 2


@add_get(prefix='MSX_')
class FileModeType(IntEnum):
    """The enumeration for file model used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.
    """
    SCRATCH_FILE = 0
    SAVED_FILE = 1
    USED_FILE = 2
