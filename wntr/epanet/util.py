"""
Provides parameter units conversion utilities through Enum classes based on EPANET units.
"""

import numpy as np
import enum
import logging

logger = logging.getLogger(__name__)

class FlowUnits(enum.Enum):
    u"""Epanet Units Enum class.

    EPANET has defined unit codes that are used in its INP input files.
    This enumerated type class provides the appropriate values, rather than
    setting up a large number of constants. Additionally, each Enum value has
    a property that identifies it as either `traditional` or `metric` flow unit.
    EPANET *does not* use fully SI units - these are provided for WNTR compatibilty.

    * Traditional (US customary, ``EN_US``)
        * ``FlowUnits.CFS`` [ :math:`ft^3\,/\,s` ]
        * ``FlowUnits.GPM`` [ :math:`gal\,/\,min` ]
        * ``FlowUnits.MGD`` [ :math:`10^6\,gal\,/\,day` ]
        * ``FlowUnits.IMGD`` [ :math:`10^6\,Imp.\,gal\,/\,day` ]
        * ``FlowUnits.AFD`` [ :math:`acre\cdot\,ft\,/\,day` ]
    * Metric (SI related, ``EN_SI``)
        * ``FlowUnits.LPS`` [ :math:`L\,/\,s` ]
        * ``FlowUnits.LPM`` [ :math:`L\,/\,min` ]
        * ``FlowUnits.MLD`` [ :math:`ML\,/\,day` ]
        * ``FlowUnits.CMH`` [ :math:`m^3\,\,hr` ]
        * ``FlowUnits.CMD`` [ :math:`m^3\,/\,day` ]
    * SI (WNTR internal units)
        * ``FlowUnits.SI`` [ :math:`m^3\,/\,s` ]

    .. rubric:: Enum Properties

    .. autosummary::
        factor
        is_traditional
        is_metric


    Examples
    --------
    >>> from wntr.epanet import FlowUnits
    >>> FlowUnits.GPM
    <FlowUnits.GPM: 1>

    Units can be converted to the EPANET integer values by casting as an ``int`` and can be
    converted to a string by accessing the ``name`` property.

    >>> FlowUnits.LPS.name
    'LPS'
    >>> int(FlowUnits.LPS)
    5

    The reverse is also true, where an ``int`` from an EPANET run or the string from and input
    file can be used to get a ``FlowUnits`` object.

    >>> FlowUnits(4)
    <FlowUnits.AFD: 4>
    >>> FlowUnits['CMD']
    <FlowUnits.CMD: 9>

    Units can be checked for metric or US customary status using the ``is_traditional`` or
    ``is_metric`` options.

    >>> FlowUnits.GPM.is_traditional
    True
    >>> FlowUnits.GPM.is_metric
    False

    Conversion can be done using the `factor` attribute. For example, to convert 10 AFD to SI units,
    and to convert 10 MGD to MLD,

    >>> 10 * FlowUnits.AFD.factor
    0.14276410185185184
    >>> 10 * FlowUnits.MGD.factor / FlowUnits.MLD.factor
    37.85411784000001


    .. note::
        This Enum uses a value of 0 for one of its members, and therefore
        acts in a non-standard way when evaluating truth values. Use ``None`` / ``is None``
        to check for truth values for variables storing a FlowUnits.

    """
    CFS = (0, 0.0283168466)
    GPM = (1, (0.003785411784/60.0))
    MGD = (2, (1e6*0.003785411784/86400.0))
    IMGD = (3, (1e6*0.00454609/86400.0))
    AFD = (4, (1233.48184/86400.0))
    LPS = (5, 0.001)
    LPM = (6, (0.001/60.0))
    MLD = (7, (1e6*0.001/86400.0))
    CMH = (8, (1.0/3600.0))
    CMD = (9, (1.0/86400.0))
    SI = (11, 1.0)

    def __init__(self, EN_id, flow_factor):
        self._value2member_map_[EN_id] = self

    def __int__(self):
        """Convert to an EPANET Toolkit enum number."""
        return int(self.value[0])

    @property
    def factor(self):
        """float: The conversion factor to convert units into SI units of :math:`m^3\,s^{-1}`.

        Letting values in the original units be :math:`v`, and the resulting values in SI units
        be :math:`s`, the conversion factor, :math:`f`, such that

        .. math::
            v f = s

        """
        return self.value[1]

    @property
    def is_traditional(self):
        """bool: True if flow unit is a US Customary (traditional) unit.

        Traditional units include CFS, GPM, MGD, IMGD and AFD.

        Examples
        --------
        >>> FlowUnits.MGD.is_traditional
        True
        >>> FlowUnits.MLD.is_traditional
        False
        >>> FlowUnits.SI.is_traditional
        False

        """
        return self in [FlowUnits.CFS, FlowUnits.GPM, FlowUnits.MGD, FlowUnits.IMGD, FlowUnits.AFD]

    @property
    def is_metric(self):
        """bool: True if flow unit is an SI Derived (metric) unit.

        Metric units include LPS, LPM, MLD, CMH, and CMD.
        This 'does not' include FlowUnits.SI itself, only 'derived' units.

        Examples
        --------
        >>> FlowUnits.MGD.is_metric
        False
        >>> FlowUnits.MLD.is_metric
        True
        >>> FlowUnits.SI.is_metric
        False

        """
        return self in [FlowUnits.LPS, FlowUnits.LPM, FlowUnits.MLD, FlowUnits.CMH, FlowUnits.CMD]


class MassUnits(enum.Enum):
    r"""Mass units used by EPANET, plus SI conversion factor.

    Mass units are defined in the EPANET INP file when the QUALITY option is
    set to a chemical. The line is formatted as follows

    .. code::

            [OPTIONS]
            QUALITY Chemical mg/L


    This is parsed to obtain the mass part of the concentration units, and
    is used to set this enumerated type.

    .. rubric:: Attribute (Enum value) Properties

    .. autosummary::
        factor

    """
    mg = (1, 0.000001) #: milligrams (default EPANET mass unit)
    ug = (2, 0.000000001) #: micrograms (optional EPANET mass unit)
    g = (3, 0.001) #: grams (not used by EPANET, but accepted by WNTR)
    kg = (4, 1.0) #: kilograms (not used by EPANET, used by WNTR internally)

    @property
    def factor(self):
        """float : The scaling factor to convert to kg."""
        return self.value[1]


class QualParam(enum.Enum):
    u"""EPANET water quality parameters.

    These parameters are separated from the HydParam parameters because they are related to a
    logically separate model in EPANET, but also because conversion to SI units requires additional
    information, namely, the MassUnits that were specified in the EPANET input file. Additionally,
    the reaction coefficient conversions require information about the reaction order that was
    specified. See the `to_si` and `from_si` functions for details.

    * ``QualParam.Concentration``, ``QualParam.Quality``, and ``QualParam.LinkQuality`` are
      the EPANET "quality" reported.
      simulations.
    * ``QualParam.BulkReactionCoeff`` provides the decay or growth factor for chemicals/biologics within
      the bulk water in pipes or tanks.
    * ``QualParam.WallReactionCoeff`` provides the decay or growth factor for chemical/biologic reactions
      with materials or biofilms on pipe walls. Converting to SI units requires knowing the
      reaction order.
    * ``QualParam.ReactionRate`` is the average reaction rate, in mass per time.
    * ``QualParam.SourceMassInject`` provides the injection rate, in mass per time, of an EPANET MASS
      type water quality source.
    * ``QualParam.WaterAge`` is the time the water has been residing in the system.

    .. rubric:: Methods

    .. autosummary::
        to_si
        from_si



    """
    Quality = 4  #: water quality at node
    LinkQuality = 10  #: average water quality in link
    ReactionRate = 13  #: average reaction rate within pipe
    Concentration = 35  #: alias for quality
    BulkReactionCoeff = 36  #: Bulk reaction coefficient (depends on reaction_order)
    WallReactionCoeff = 37  #: wall reaction coefficient (depends on reaction_order)
    SourceMassInject = 38  #: mass injection rate
    WaterAge = 39  #: water age

    def to_si(self, flow_units, data, mass_units=MassUnits.mg,
              reaction_order=0):
        """Convert a water quality parameter to SI units from EPANET units.

        By default, the mass units are the EPANET default of mg, and the reaction order is 0.

        Examples
        --------
        The following examples show conversion from EPANET flow and mass units into SI units.
        Convert concentration of 15.0 mg / L to SI units

        >>> QualParam.Concentration.to_si(FlowUnits.MGD, 15.0, MassUnits.mg)
        0.015

        Convert a bulk reaction coefficient for a first order reaction to SI units.

        >>> QualParam.BulkReactionCoeff.to_si(FlowUnits.AFD, 1.0, MassUnits.ug, reaction_order=1)
        1.1574074074074073e-05

        """
        data_type = type(data)
        if data_type is dict:
            data_keys = data.keys()
            data = np.array(data.values())
        elif data_type is list:
            data = np.array(data)

        # Do conversions
        if self in [QualParam.Concentration, QualParam.Quality, QualParam.LinkQuality]:
            data = data * (mass_units.factor/0.001)  # MASS /L to kg/m3

        elif self in [QualParam.SourceMassInject]:
            data = data * (mass_units.factor/60.0)  # MASS /min to kg/s

        elif self in [QualParam.BulkReactionCoeff] and reaction_order == 1:
                data = data * (1/86400.0)  # per day to per second

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 0:
            if flow_units.is_traditional:
                data = data * (mass_units.factor*0.092903/86400.0)  # M/ft2/d to SI
            else:
                data = data * (mass_units.factor/86400.0)  # M/m2/day to M/m2/s

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 1:
            if flow_units.is_traditional:
                data = data * (0.3048/86400.0)  # ft/d to m/s
            else:
                data = data * (1.0/86400.0)  # m/day to m/s

        elif self in [QualParam.SourceMassInject]:
            data = data * (mass_units.factor/60.0)  # per min to per second

        elif self in [QualParam.WaterAge]:
            data = data * 3600.0  # hr to s

        # Convert back to input data type
        if data_type is dict:
            data = dict(zip(data_keys, data))
        elif data_type is list:
            data = list(data)
        return data

    def from_si(self, flow_units, data, mass_units=MassUnits.mg,
                reaction_order=0):
        """Convert a water quality parameter back to EPANET units from SI units.

        Mass units defaults to :class:`MassUnits.mg`, as this is the EPANET default.

        Examples
        --------
        The following examples show conversion from EPANET flow and mass units from SI units.
        Convert concentration of 0.015 kg / cubic meter back to EPANET units (mg/L)

        >>> QualParam.Concentration.from_si(FlowUnits.MGD, 0.015)
        15.0

        Convert a bulk reaction coefficient for a first order reaction back into per-day.

        >>> QualParam.BulkReactionCoeff.from_si(FlowUnits.AFD, 1.1574e-05, MassUnits.ug, reaction_order=1)
        0.9999936


        """
        data_type = type(data)
        if data_type is dict:
            data_keys = data.keys()
            data = np.array(data.values())
        elif data_type is list:
            data = np.array(data)

        # Do conversions
        if self in [QualParam.Concentration, QualParam.Quality, QualParam.LinkQuality]:
            data = data / (mass_units.factor/0.001)  # MASS /L fr kg/m3

        elif self in [QualParam.SourceMassInject]:
            data = data / (mass_units.factor/60.0)  # MASS /min fr kg/s

        elif self in [QualParam.BulkReactionCoeff] and reaction_order == 1:
                data = data / (1/86400.0)  # per day fr per second

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 0:
            if flow_units.is_traditional:
                data = data / (mass_units.factor*0.092903/86400.0)  # M/ft2/d fr SI
            else:
                data = data / (mass_units.factor/86400.0)  # M/m2/day fr M/m2/s

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 1:
            if flow_units.is_traditional:
                data = data / (0.3048/86400.0)  # ft/d fr m/s
            else:
                data = data / (1.0/86400.0)  # m/day fr m/s

        elif self in [QualParam.SourceMassInject]:
            data = data / (mass_units.factor/60.0)  # per min fr per second

        elif self in [QualParam.WaterAge]:
            data = data / 3600.0  # hr fr s

        # Convert back to input data type
        if data_type is dict:
            data = dict(zip(data_keys, data))
        elif data_type is list:
            data = list(data)
        return data


class HydParam(enum.Enum):
    u"""EPANET hydraulics and energy parameters.

    The hydraulic parameter enumerated type is used to perform unit conversion
    between EPANET internal units and SI units used by WNTR. The units for each
    parameter are determined based on the :class:`FlowUnits` used.

    * Node parameters
        * ``HydParam.Elevation``
        * ``HydParam.Demand``
        * ``HydParam.HydraulicHead``
        * ``HydParam.Pressure``
    * Emitter parameters
        * ``HydParam.EmitterCoeff``
    * Tank parameters
        * ``HydParam.TankDiameter``
        * ``HydParam.Volume``
    * Link parameters
        * ``HydParam.Length``
        * ``HydParam.PipeDiameter``
        * ``HydParam.Flow``
        * ``HydParam.Velocity``
        * ``HydParam.HeadLoss``
    * Pipe parameters
        * ``HydParam.RoughnessCoeff`` requires knowing the method. For Darcy-Weisbach, this parameter needs
          conversion to milli-feet and millimeters, otherwise it is unitless.
    * Pump parameters
        * ``HydParam.Energy``
        * ``HydParam.Power``

    .. rubric:: Methods

    .. autosummary::
        to_si
        from_si

    """
    Elevation = 0 #: Elevation is defined in feet or meters
    Demand = 1 #: Demand is specified in :class:`FlowUnits` units
    HydraulicHead = 2 #: Hydraulic head is defined in feet or meters
    Pressure = 3 #: Pressure is defined in psi, kPa, or meters
    # Quality = 4
    Length = 5 #: Length is defined in feet or meters
    PipeDiameter = 6 #: Pipe diameter is specified in either inches or millimeters
    Flow = 7 #: Flow is specified in :class:`FlowUnits` units
    Velocity = 8 #: Velocity is defined in ft/second or meters/second
    HeadLoss = 9 #: Head loss is defined in feet or meters
    # Link Quality = 10
    # Status = 11
    # Setting = 12
    # Reaction Rate = 13
    # Friction factor = 14
    Power = 15 #: Power is defined in either horsepower or kilowatts
    # Time = 16
    Volume = 17 #: Volume is defined in cubic feet or cubic meters
    # The following are not "output" network variables, and thus are defined separately
    EmitterCoeff = 31 #: Emitter Coefficient is defined in :class:`FlowUnits` per :math:`psi^{1/2}`
    RoughnessCoeff = 32 #: For Darcy-Weisbach loss equations, specified in milli-feet or millimeters; otherwise unitless
    TankDiameter = 33 #: Tank diameters are defined in feet or meters
    Energy = 34 #: Energy is defined in killowatt-hours, regardless or :class:`FlowUnits`

    def to_si(self, flow_units, data, darcy_weisbach=False):
        """Convert from EPANET units groups to SI units.

        If converting roughness, specify if the Darcy-Weisbach equation is
        used using the darcy_weisbach parameter. Otherwise, that parameter
        can be safely ignored/omitted for any other conversion.
        """
        # Convert to array for unit conversion
        data_type = type(data)
        if data_type is dict:
            data_keys = data.keys()
            data = np.array(list(data.values()))
        elif data_type is list:
            data = np.array(data)

        # Do conversions
        if self in [HydParam.Demand, HydParam.Flow, HydParam.EmitterCoeff]:
            data = data * flow_units.factor
            if self is HydParam.EmitterCoeff:
                if flow_units.is_traditional:
                    data = data / 0.7032  # flowunit/psi0.5 to flowunit/m0.5

        elif self in [HydParam.PipeDiameter]:
            if flow_units.is_traditional:
                data = data * 0.0254  # in to m
            elif flow_units.is_metric:
                data = data * 0.001  # mm to m

        elif self in [HydParam.RoughnessCoeff] and darcy_weisbach:
            if flow_units.is_traditional:
                data = data * (1000.0*0.3048)  # 1e-3 ft to m
            elif flow_units.is_metric:
                data = data * 0.001  # mm to m

        elif self in [HydParam.TankDiameter, HydParam.Elevation, HydParam.HydraulicHead,
                      HydParam.Length, HydParam.HeadLoss]:
            if flow_units.is_traditional:
                data = data * 0.3048  # ft to m

        elif self in [HydParam.Velocity]:
            if flow_units.is_traditional:
                data = data * 0.3048  # ft/s to m/s

        elif self in [HydParam.Energy]:
            data = data * 3600000.0  # kW*hr to J

        elif self in [HydParam.Power]:
            if flow_units.is_traditional:
                data = data * 745.699872  # hp to W (Nm/s)
            elif flow_units.is_metric:
                data = data * 1000.0  # kW to W (Nm/s)

        elif self in [HydParam.Pressure]:
            if flow_units.is_traditional:
                data = data * 0.703249614902  # psi to m

        elif self in [HydParam.Volume]:
            if flow_units.is_traditional:
                data = data * np.power(0.3048, 3)  # ft3 to m3

        # Convert back to input data type
        if data_type is dict:
            data = dict(zip(data_keys, data))
        elif data_type is list:
            data = list(data)
        return data

    def from_si(self, flow_units, data, darcy_weisbach=False):
        """Convert from SI units into EPANET specified units.

        If converting roughness, specify if the Darcy-Weisbach equation is
        used using the darcy_weisbach parameter. Otherwise, that parameter
        can be safely ignored/omitted for any other conversion.
        """
        # Convert to array for conversion
        data_type = type(data)
        if data_type is dict:
            data_keys = data.keys()
            data = np.array(list(data.values()))
        elif data_type is list:
            data = np.array(data)

        # Do onversions
        if self in [HydParam.Demand, HydParam.Flow, HydParam.EmitterCoeff]:
            data = data / flow_units.factor
            if self is HydParam.EmitterCoeff:
                if flow_units.is_traditional:
                    data = data / 0.7032  # flowunit/psi0.5 from flowunit/m0.5

        elif self in [HydParam.PipeDiameter]:
            if flow_units.is_traditional:
                data = data / 0.0254  # in from m
            elif flow_units.is_metric:
                data = data / 0.001  # mm from m

        elif self in [HydParam.RoughnessCoeff] and darcy_weisbach:
            if flow_units.is_traditional:
                data = data / (1000.0*0.3048)  # 1e-3 ft from m
            elif flow_units.is_metric:
                data = data / 0.001  # mm from m

        elif self in [HydParam.TankDiameter, HydParam.Elevation, HydParam.HydraulicHead,
                      HydParam.Length, HydParam.HeadLoss]:
            if flow_units.is_traditional:
                data = data / 0.3048  # ft from m

        elif self in [HydParam.Velocity]:
            if flow_units.is_traditional:
                data = data / 0.3048  # ft/s from m/s

        elif self in [HydParam.Energy]:
            data = data / 3600000.0  # kW*hr from J

        elif self in [HydParam.Power]:
            if flow_units.is_traditional:
                data = data / 745.699872  # hp from W (Nm/s)
            elif flow_units.is_metric:
                data = data / 1000.0  # kW from W (Nm/s)

        elif self in [HydParam.Pressure]:
            if flow_units.is_traditional:
                data = data / 0.703249614902  # psi from m

        elif self in [HydParam.Volume]:
            if flow_units.is_traditional:
                data = data / np.power(0.3048, 3)  # ft3 from m3

        # Put back into data format passed in
        if data_type is dict:
            data = dict(zip(data_keys, data))
        elif data_type is list:
            data = list(data)
        return data



class StatisticsType(enum.Enum):
    """EPANET time series statistics processing."""
    NONE = 0  #: Do no processing, provide instantaneous values on output at time `t`.
    AVERAGE = 1  #: Average the value across the report period ending at time `t`.
    MINIMUM = 2  #: Provide the minimum value across all complete reporting periods.
    MAXIMUM = 3  #: Provide the maximum value across all complete reporting periods.
    RANGE = 4  #: Provide the range (max - min) across all complete reporting periods.


class QualType(enum.Enum):
    """Provide the EPANET water quality simulation quality type."""
    NONE = 0  #: Do not perform water quality simulation.
    CHEM = 1  #: Do chemical transport simulation.
    AGE = 2  #: Do water age simulation.
    TRACE = 3  #: Do a tracer test (results in percentage of water is from trace node).


class SourceType(enum.Enum):
    """What type of EPANET Chemical source is used."""
    CONCEN = 0  #: Concentration -- cannot be used at nodes with non-zero demand.
    MASS = 1  #: Mass -- mass per minute injection. Can be used at any node.
    SETPOINT = 2  #: Setpoint -- force node quality to be a certain concentration.
    FLOWPACED = 3  #: Flow paced -- set variable mass injection based on flow.


class PressureUnits(enum.Enum):
    PSI = 0
    KPA = 1
    METERS = 2


class FormulaType(enum.Enum):
    """Formula used for determining head loss due to roughness."""
    HW = (0, "H-W",) #: Hazen-Williams
    DW = (1, "D-W",) #: Darcy-Weisbach; requires units conversion.
    CM = (2, "C-M",) #: Chezy-Manning

    def __init__(self, eid, inpcode):
        self._value2member_map_[eid] = self
        self._member_map_[inpcode] = self

    def __int__(self):
        return self.value[0]

    @property
    def inpcode(self):
        """Return the INP file text needed for the OPTIONS section."""
        return self.value[1]


class NodeType(enum.Enum):
    JUNCTION = 0
    RESERVOIR = 1
    TANK = 2


class LinkType(enum.Enum):
    CV = 0  #: pipe with check valve
    PIPE = 1  #: regular pipe
    PUMP = 2  #: pump
    PRV = 3  #: pressure reducing valve
    PSV = 4  #: pressure sustaining valve
    PBV = 5  #: pressure breaker valve
    FCV = 6  #: flow control valve
    TCV = 7  #: throttle control valve
    GPV = 8  #: general purpose valve


class ControlType(enum.Enum):
    LOWLEVEL = 0  #: act when grade below set level
    HILEVEL = 1  #: act when grade above set lavel
    TIMER = 2  #: act when set time reached (from start of simulation)
    TIMEOFDAY = 3  #: act when time of day occurs


class LinkBaseStatus(enum.Enum):
    CLOSED = 0  #: pipe/valve/pump is closed
    OPEN = 1  #: pipe/valve/pump is open
    ACTIVE = 2  #: valve is partially open
    closed = 0
    opened = 1
    active = 2


class LinkTankStatus(enum.Enum):
    XHEAD = 0  #: pump cannot deliver head (closed)
    TEMPCLOSED = 1  #: temporarily closed
    CLOSED = 2 #: closed
    OPEN = 3  #: open
    ACTIVE = 4  #: valve active (partially open)
    XFLOW = 5  #: pump exceeds maximum flow
    XFCV = 6  #: FCV cannot supply flow
    XPRESSURE = 7  #: valve cannot supply pressure
    FILLING = 8  #: tank filling
    EMPTYING = 9  #: tank emptying


class MixType(enum.Enum):
    MIX1 = 0  #: 1-compartment model
    MIX2 = 1  #: 2-compartment model
    FIFO = 2  #: first-in, first-out model
    LIFO = 3  #: last-in, first-out model
