# coding: utf-8
"""
The wntr.epanet.msx.enums module contains EPANET-MSX enum types, for use in
toolkit API calls.
"""

from enum import IntEnum
from wntr.utils.enumtools import add_get

@add_get(prefix='MSX_')
class TkObjectType(IntEnum):
    r"""Enumeration for object type used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        NODE
        LINK
        PIPE
        TANK
        SPECIES
        TERM
        PARAMETER
        CONSTANT
        PATTERN
    """
    NODE = 0
    """EPANET node"""
    LINK = 1
    """EPANET link"""
    PIPE = 1
    """EPANET pipe"""
    TANK = 2
    """EPANET tank"""
    SPECIES = 3
    """MSX species"""
    TERM = 4
    """MSX term"""
    PARAMETER = 5
    """MSX parameter"""
    CONSTANT = 6
    """MSX constant"""
    PATTERN = 7
    """**MSX** pattern"""
    MAX_OBJECTS = 8


@add_get(prefix='MSX_')
class TkSourceType(IntEnum):
    r"""Enumeration for source type used in EPANET-MSX.

    .. warning:: These enum values start with -1.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        NOSOURCE
        CONCEN
        MASS
        SETPOINT
        FLOWPACED
    """
    NOSOURCE = -1
    """No source"""
    CONCEN = 0
    """Concentration based source"""
    MASS = 1
    """Constant mass source"""
    SETPOINT = 2
    """Setpoint source"""
    FLOWPACED = 3
    """Flow-paced source"""


@add_get(prefix='MSX_')
class TkUnitSystem(IntEnum):
    r"""Enumeration for the units system used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        US
        SI
    """
    US = 0
    """US units (ft, ft2, gal)"""
    SI = 1
    """SI units (m, m2, m3)"""


@add_get(prefix='MSX_')
class TkFlowUnits(IntEnum):
    r"""Enumeration for the flow units used in EPANET-MSX (determined from
    EPANET INP file read in with the toolkit).

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        CFS
        GPM
        MGD
        IMGD
        AFD
        LPS
        LPM
        MLD
        CMH
        CMD
    """
    CFS = 0
    """cubic feet per second"""
    GPM = 1
    """gallons (US) per minute"""
    MGD = 2
    """million gallons (US) per day"""
    IMGD = 3
    """million Imperial gallons per day"""
    AFD = 4
    """acre-feet (US) per day"""
    LPS = 5
    """liters per second"""
    LPM = 6
    """liters per minute"""
    MLD = 7
    """million liters per day"""
    CMH = 8
    """cubic meters per hour"""
    CMD = 9
    """cubic meters per day"""


@add_get(prefix='MSX_')
class TkMixType(IntEnum):
    r"""Enumeration for the mixing model used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        MIX1
        MIX2
        FIFO
        LIFO
    """
    MIX1 = 0
    """full mixing, 1 compartment"""
    MIX2 = 1
    """full mixing, 2 comparments"""
    FIFO = 2
    """first in, first out"""
    LIFO = 3
    """last in, first out"""


@add_get(prefix='MSX_')
class TkSpeciesType(IntEnum):
    r"""Enumeration for species type used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        BULK
        WALL
    """
    BULK = 0
    """bulk species"""
    WALL = 1
    """wall species"""


@add_get(prefix='MSX_')
class TkExpressionType(IntEnum):
    r"""Enumeration for the expression type used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        NO_EXPR
        RATE
        FORMULA
        EQUIL
    """
    NO_EXPR = 0
    """no expression defined"""
    RATE = 1
    """expression is a rate expression"""
    FORMULA = 2
    """expression is a formula expression"""
    EQUIL = 3
    """expression is an equilibrium expression"""


@add_get(prefix='MSX_')
class TkSolverType(IntEnum):
    r"""Enumeration for the solver type used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        EUL
        RK5
        ROS2
    """
    EUL = 0
    """Euler solver"""
    RK5 = 1
    """Runga-Kutta 5th order solver"""
    ROS2 = 2
    """Ros 2nd order solver"""


@add_get(prefix='MSX_')
class TkCouplingType(IntEnum):
    r"""Enumeration for the coupling type option used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        NO_COUPLING
        FULL_COUPLING
    """
    NO_COUPLING = 0
    """no coupling"""
    FULL_COUPLING = 1
    """full coupling"""


@add_get(prefix='MSX_')
class TkMassUnits(IntEnum):
    r"""Enumeration for mass units used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        MG
        UG
        MOLE
        MMOLE
    """
    MG = 0
    """milligrams"""
    UG = 1
    """micrograms"""
    MOLE = 2
    """mole"""
    MMOLE = 3
    """millimole"""


@add_get(prefix='MSX_')
class TkAreaUnits(IntEnum):
    r"""Enumeration for area units used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        FT2
        M2
        CM2
    """
    FT2 = 0
    """square feet"""
    M2 = 1
    """square meters"""
    CM2 = 2
    """square centimeters"""


@add_get(prefix='MSX_')
class TkRateUnits(IntEnum):
    r"""Enumeration for rate units used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        SECONDS
        MINUTES
        HOURS
        DAYS
    """
    SECONDS = 0
    """per second"""
    MINUTES = 1
    """per minute"""
    HOURS = 2
    """per hour"""
    DAYS = 3
    """per day"""


@add_get(prefix='MSX_')
class TkUnits(IntEnum):
    r"""Position for units used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        LENGTH_UNITS
        DIAM_UNITS
        AREA_UNITS
        VOL_UNITS
        FLOW_UNITS
        CONC_UNITS
        RATE_UNITS
    """
    LENGTH_UNITS = 0
    """the length unit index"""
    DIAM_UNITS = 1
    """the diameter unit index"""
    AREA_UNITS = 2
    """the area unit index"""
    VOL_UNITS = 3
    """the volume unit index"""
    FLOW_UNITS = 4
    """the flow unit index"""
    CONC_UNITS = 5
    """the concentration unit index"""
    RATE_UNITS = 6
    """the rate unit index"""
    MAX_UNIT_TYPES = 7


@add_get(prefix='MSX_')
class TkHydVar(IntEnum):
    r"""Enumeration for hydraulic variable used in EPANET-MSX.
    
    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        DIAMETER
        FLOW
        VELOCITY
        REYNOLDS
        SHEAR
        FRICTION
        AREAVOL
        ROUGHNESS
        LENGTH
    """
    DIAMETER = 1
    """pipe diameter"""
    FLOW = 2
    """pipe flow rate"""
    VELOCITY = 3
    """segment velocity"""
    REYNOLDS = 4
    """Reynolds number"""
    SHEAR = 5
    """shear velocity"""
    FRICTION = 6
    """friction factor"""
    AREAVOL = 7
    """area / volume ratio"""
    ROUGHNESS = 8
    """roughness number"""
    LENGTH = 9
    """pipe or segment length"""
    MAX_HYD_VARS = 10


@add_get(prefix='MSX_')
class TkTstat(IntEnum):
    r"""Enumeration used for time statistic in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        SERIES
        AVERAGE
        MINIMUM
        MAXIMUM
        RANGE
    """
    SERIES = 0
    """output a time series"""
    AVERAGE = 1
    """output the average"""
    MINIMUM = 2
    """output the minimum"""
    MAXIMUM = 3
    """output the maximum"""
    RANGE = 4
    """output the range (max - min)"""


@add_get(prefix='MSX_')
class TkOption(IntEnum):
    r"""Enumeration used for choosing an option in EPANET-MSX toolkit.
    
    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        AREA_UNITS_OPTION
        RATE_UNITS_OPTION
        SOLVER_OPTION
        COUPLING_OPTION
        TIMESTEP_OPTION
        RTOL_OPTION
        ATOL_OPTION
        COMPILER_OPTION
        MAXSEGMENT_OPTION
        PECLETNUMBER_OPTION
    """
    AREA_UNITS_OPTION = 0
    """area units"""
    RATE_UNITS_OPTION = 1
    """rate units"""
    SOLVER_OPTION = 2
    """solver"""
    COUPLING_OPTION = 3
    """coupling"""
    TIMESTEP_OPTION = 4
    """timestep size"""
    RTOL_OPTION = 5
    """relative tolerance (global)"""
    ATOL_OPTION = 6
    """absolute tolerance (global)"""
    COMPILER_OPTION =7
    """compiler option"""
    MAXSEGMENT_OPTION = 8
    """max segments"""
    PECLETNUMBER_OPTION = 9
    """peclet number"""


@add_get(prefix='MSX_')
class TkCompiler(IntEnum):
    r"""Enumeration used for specifying compiler options in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        NO_COMPILER
        VC
        GC
    """
    NO_COMPILER = 0
    """do not compile reaction dynamics"""
    VC = 1
    """use Visual C to compile reaction dynamics"""
    GC = 2
    """use Gnu C to compile reaction dynamics"""


@add_get(prefix='MSX_')
class TkFileMode(IntEnum):
    r"""Enumeration for file model used in EPANET-MSX.

    .. warning:: These enum values start with 0.

    .. rubric:: Enum Members

    The following enum names are defined, and, if using the :meth:`get` method,
    then they are case insensitive and can be optionally prefixed with "MSX\_".

    .. autosummary::
        SCRATCH_FILE
        SAVED_FILE
        USED_FILE
    """
    SCRATCH_FILE = 0
    """use a scratch file"""
    SAVED_FILE = 1
    """save the file"""
    USED_FILE = 2
    """use a saved file"""
