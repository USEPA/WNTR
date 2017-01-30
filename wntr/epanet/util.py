"""
The wntr.epanet.util module contains unit conversion utilities based on EPANET units.
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

    .. rubric:: Enum Members

    ==============  ====================================  ========================
    :attr:`~CFS`    :math:`ft^3\,/\,s`                    :attr:`is_traditional`
    :attr:`~GPM`    :math:`gal\,/\,min`                   :attr:`is_traditional`
    :attr:`~MGD`    :math:`10^6\,gal\,/\,day`             :attr:`is_traditional`
    :attr:`~IMGD`   :math:`10^6\,Imp.\,gal\,/\,day`       :attr:`is_traditional`
    :attr:`~AFD`    :math:`acre\cdot\,ft\,/\,day`         :attr:`is_traditional`
    :attr:`~LPS`    :math:`L\,/\,s`                       :attr:`is_metric`
    :attr:`~LPM`    :math:`L\,/\,min`                     :attr:`is_metric`
    :attr:`~MLD`    :math:`ML\,/\,day`                    :attr:`is_metric`
    :attr:`~CMH`    :math:`m^3\,\,hr`                     :attr:`is_metric`
    :attr:`~CMD`    :math:`m^3\,/\,day`                   :attr:`is_metric`
    :attr:`~SI`     :math:`m^3\,/\,s`
    ==============  ====================================  ========================

    .. rubric:: Enum Member Attributes

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
        self._member_map_[self.name.lower()] = self

    def __int__(self):
        """Convert to an EPANET Toolkit enum number."""
        return int(self.value[0])

    def __str__(self):
        """Convert to a string for INP files."""
        return self.name

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
    set to a chemical. This is parsed to obtain the mass part of the concentration units,
    and is used to set this enumerated type.

    .. rubric:: Enum Members

    ============  ============================================
    :attr:`~mg`   miligrams; EPANET as "mg/L" or "mg/min"
    :attr:`~ug`   micrograms; EPANET as "ug/L" or "ug/min"
    :attr:`~g`    grams
    :attr:`~kg`   kilograms; WNTR standard
    ============  ============================================

    .. rubric:: Enum Member Attributes

    .. autosummary::
        factor

    """
    mg = (1, 0.000001)
    ug = (2, 0.000000001)
    g = (3, 0.001)
    kg = (4, 1.0)

    @property
    def factor(self):
        """float : The scaling factor to convert to kg."""
        return self.value[1]


class QualParam(enum.Enum):
    u"""EPANET water quality parameters conversion.

    These parameters are separated from the HydParam parameters because they are related to a
    logically separate model in EPANET, but also because conversion to SI units requires additional
    information, namely, the MassUnits that were specified in the EPANET input file. Additionally,
    the reaction coefficient conversions require information about the reaction order that was
    specified. See the `to_si` and `from_si` functions for details.

    .. rubric:: Enum Members

    ==========================  ================================================================
    :attr:`~Concentration`      General concentration parameter
    :attr:`~Quality`            Nodal water quality
    :attr:`~LinkQuality`        Link water quality
    :attr:`~BulkReactionCoeff`  Bulk reaction coefficient (req. `reaction_order` to convert)
    :attr:`~WallReactionCoeff`  Wall reaction coefficient (req. `reaction_order` to convert)
    :attr:`~ReactionRate`       Average reaction rate within a link
    :attr:`~SourceMassInject`   Injection rate for water quality sources
    :attr:`~WaterAge`           Water age at a node
    ==========================  ================================================================

    .. skip::

        .. rubric:: Enum Member Methods

        .. autosummary::
            to_si
            from_si

    """
    Quality = 4
    LinkQuality = 10
    ReactionRate = 13
    Concentration = 35
    BulkReactionCoeff = 36
    WallReactionCoeff = 37
    SourceMassInject = 38
    WaterAge = 39

    def __init__(self, value):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def _to_si(self, flow_units, data, mass_units=MassUnits.mg,
              reaction_order=0):
        """Convert a water quality parameter to SI units from EPANET units.

        By default, the mass units are the EPANET default of mg, and the reaction order is 0.

        Parameters
        ----------
        flow_units : ~FlowUnits
            The EPANET flow units to use in the conversion
        data : array-like
            The data to be converted (scalar, array or dictionary)
        mass_units : ~MassUnits
            The EPANET mass units to use in the conversion (mg or ug)
        reaction_order : int
            The reaction order for use converting reaction coefficients

        Returns
        -------
        float
            The data values converted to SI standard units

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

    def _from_si(self, flow_units, data, mass_units=MassUnits.mg,
                reaction_order=0):
        """Convert a water quality parameter back to EPANET units from SI units.

        Mass units defaults to :class:`MassUnits.mg`, as this is the EPANET default.

        Parameters
        ----------
        flow_units : ~FlowUnits
            The EPANET flow units to use in the conversion
        data : array-like
            The SI unit data to be converted (scalar, array or dictionary)
        mass_units : ~MassUnits
            The EPANET mass units to use in the conversion (mg or ug)
        reaction_order : int
            The reaction order for use converting reaction coefficients

        Returns
        -------
        float
            The data values converted to EPANET appropriate units, based on the flow units.

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
    u"""EPANET hydraulics and energy parameter conversion.

    The hydraulic parameter enumerated type is used to perform unit conversion
    between EPANET internal units and SI units used by WNTR. The units for each
    parameter are determined based on the :class:`FlowUnits` used.

    Parameters that are unitless or otherwise require no conversion are not members of this
    Enum type.

    .. rubric:: Enum Members

    ==========================  ===================================================================
    :attr:`~Elevation`          Nodal elevation
    :attr:`~Demand`             Nodal demand
    :attr:`~HydraulicHead`      Nodal head
    :attr:`~Pressure`           Nodal pressure
    :attr:`~EmitterCoeff`       Emitter coefficient
    :attr:`~TankDiameter`       Tank diameter
    :attr:`~Volume`             Tank volume
    :attr:`~Length`             Link length
    :attr:`~PipeDiameter`       Pipe diameter
    :attr:`~Flow`               Link flow
    :attr:`~Velocity`           Link velocity
    :attr:`~HeadLoss`           Link headloss (from start node to end node)
    :attr:`~RoughnessCoeff`     Link roughness (requires `darcy_weisbach` setting for conversion)
    :attr:`~Energy`             Pump energy
    :attr:`~Power`              Pump power
    ==========================  ===================================================================

    .. skip::

        .. rubric:: Methods

        .. autosummary::
            to_si
            from_si

    """
    Elevation = 0
    Demand = 1
    HydraulicHead = 2
    Pressure = 3

    # Quality = 4

    Length = 5
    PipeDiameter = 6
    Flow = 7
    Velocity = 8
    HeadLoss = 9

    # Link Quality = 10
    # Status = 11
    # Setting = 12
    # Reaction Rate = 13
    # Friction factor = 14

    Power = 15

    # Time = 16

    Volume = 17

    # The following are not "output" network variables, and thus are defined separately

    EmitterCoeff = 31
    RoughnessCoeff = 32
    TankDiameter = 33
    Energy = 34

    def __init__(self, value):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def _to_si(self, flow_units, data, darcy_weisbach=False):
        """Convert from EPANET units groups to SI units.

        If converting roughness, specify if the Darcy-Weisbach equation is
        used using the darcy_weisbach parameter. Otherwise, that parameter
        can be safely ignored/omitted for any other conversion.

        Parameters
        ----------
        flow_units : ~FlowUnits
            The flow units to use in the conversion
        data : array-like
            The EPANET-units data to be converted (scalar, array or dictionary)
        darcy_weisbach : bool, optional
            Set to ``True`` if converting roughness coefficients for use with Darcy-Weisbach
            formula.

        Returns
        -------
        float
            The data values converted to SI standard units.

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

    def _from_si(self, flow_units, data, darcy_weisbach=False):
        """Convert from SI units into EPANET specified units.

        If converting roughness, specify if the Darcy-Weisbach equation is
        used using the darcy_weisbach parameter. Otherwise, that parameter
        can be safely ignored/omitted for any other conversion.

        Parameters
        ----------
        flow_units : :class:`~FlowUnits`
            The flow units to use in the conversion
        data : array-like
            The SI unit data to be converted (scalar, array or dictionary)
        darcy_weisbach : bool, optional
            Set to ``True`` if converting roughness coefficients for use with Darcy-Weisbach
            formula.

        Returns
        -------
        float
            The data values converted to EPANET appropriate units based on the flow units.

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


def to_si(from_units, data, param,
          mass_units=MassUnits.mg, pressure_units=None,
          darcy_weisbach=False, reaction_order=0):
    """Convert an EPANET parameter from internal to SI standard units.

    Parameters
    ----------
    from_units : :class:`~FlowUnits`
        The EPANET flow units (and therefore units system) to use for conversion
    data : float, array-like, dict
        The data to be converted
    param : :class:`~HydParam` or :class:`~QualParam`
        The parameter type for the data
    mass_units : :class:`~MassUnits`, optional
        The EPANET mass units (mg or ug internal to EPANET)
    pressure_units : :class:`~PressureUnits`, optional
        The EPANET pressure units being used (based on `flow_units`, normally)
    darcy_weisbach : bool, optional
        For roughness coefficients, is this used in a Darcy-Weisbach formula?
    reaction_order : int, optional
        For reaction coefficients, what is the reaction order?

    Returns
    -------
    float, array-like, or dict
        The data values convert into SI standard units

    Examples
    --------
    The following examples show conversion from EPANET flow and mass units into SI units.
    Convert concentration of 15.0 mg / L to SI units

    >>> to_si(FlowUnits.MGD, 15.0, QualParam.Concentration)
    0.015

    Convert a bulk reaction coefficient for a first order reaction to SI units.

    >>> to_si(FlowUnits.AFD, 1.0, QualParam.BulkReactionCoeff,
    ... mass_units=MassUnits.ug, reaction_order=1)
    1.1574074074074073e-05


    """
    if isinstance(param, HydParam):
        return param._to_si(from_units, data, darcy_weisbach)
    elif isinstance(param, QualParam):
        return param._to_si(from_units, data, mass_units, reaction_order)
    else:
        raise RuntimeError('Invalid parameter: %s' % param)


def from_si(to_units, data, param,
          mass_units=MassUnits.mg, pressure_units=None,
          darcy_weisbach=False, reaction_order=0):
    """Convert an EPANET parameter from SI standard units back to internal units.

    Parameters
    ----------
    to_units : :class:`~FlowUnits`
        The EPANET flow units (and therefore units system) to use for conversion
    data : float, array-like, dict
        The data to be converted
    param : :class:`~HydParam` or :class:`~QualParam`
        The parameter type for the data
    mass_units : :class:`~MassUnits`, optional
        The EPANET mass units (mg or ug internal to EPANET)
    pressure_units : :class:`~PressureUnits`, optional
        The EPANET pressure units being used (based on `flow_units`, normally)
    darcy_weisbach : bool, optional
        For roughness coefficients, is this used in a Darcy-Weisbach formula?
    reaction_order : int, optional
        For reaction coefficients, what is the reaction order?

    Returns
    -------
    float, array-like, or dict
        The data values converted into EPANET internal units

    """
    if isinstance(param, HydParam):
        return param._from_si(to_units, data, darcy_weisbach)
    elif isinstance(param, QualParam):
        return param._from_si(to_units, data, mass_units, reaction_order)
    else:
        raise RuntimeError('Invalid parameter: %s' % param)


class StatisticsType(enum.Enum):
    """EPANET time series statistics processing.

    .. rubric:: Enum Members

    ================  =========================================================================
    :attr:`~none`     Do no processing, provide instantaneous values on output at time `t`.
    :attr:`~Average`  Average the value across the report period ending at time `t`.
    :attr:`~Minimum`  Provide the minimum value across all complete reporting periods.
    :attr:`~Maximum`  Provide the maximum value across all complete reporting periods.
    :attr:`~Range`    Provide the range (max - min) across all complete reporting periods.
    ================  =========================================================================

    """
    none = 0
    Average = 1
    Minimum = 2
    Maximum = 3
    Range = 4

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class QualType(enum.Enum):
    """Provide the EPANET water quality simulation quality type.

    .. rubric:: Enum Members

    ================  =========================================================================
    :attr:`~none`     Do not perform water quality simulation.
    :attr:`~Chem`     Do chemical transport simulation.
    :attr:`~Age`      Do water age simulation.
    :attr:`~Trace`    Do a tracer test (results in percentage of water is from trace node).
    ================  =========================================================================

    """
    none = 0
    Chem = 1
    Age = 2
    Trace = 3

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class SourceType(enum.Enum):
    """What type of EPANET Chemical source is used.

    .. rubric:: Enum Members

    ==================  =========================================================================
    :attr:`~Concen`     Concentration -- cannot be used at nodes with non-zero demand.
    :attr:`~Mass`       Mass -- mass per minute injection. Can be used at any node.
    :attr:`~Setpoint`   Setpoint -- force node quality to be a certain concentration.
    :attr:`~FlowPaced`  Flow paced -- set variable mass injection based on flow.
    ==================  =========================================================================

    """
    Concen = 0
    Mass = 1
    Setpoint = 2
    FlowPaced = 3

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class PressureUnits(enum.Enum):
    """EPANET output pressure units.

    .. rubric:: Enum Members

    ===============  ====================================================
    :attr:`~psi`     Pounds per square inch (flow units are traditional)
    :attr:`~kPa`     kilopascals (flow units are metric)
    :attr:`~meters`  meters of H2O
    ===============  ====================================================

    """
    psi = 0
    kPa = 1
    Meters = 2

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class FormulaType(enum.Enum):
    """Formula used for determining head loss due to roughness.

    .. rubric:: Enum Members

    ===============  ==================================================================
    :attr:`~HW`      Hazen-Williams headloss formula (:attr:`~str`="H-W")
    :attr:`~DW`      Darcy-Weisbach formala; requires units conversion.
                     (:attr:`~str`='D-W')
    :attr:`~CM`      Chezy-Manning formula (:attr:`~str`="C-M")
    ===============  ==================================================================

    """
    HW = (0, "H-W",)
    DW = (1, "D-W",)
    CM = (2, "C-M",)

    def __init__(self, eid, inpcode):
        self._value2member_map_[eid] = self
        self._member_map_[inpcode] = self
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __int__(self):
        return self.value[0]

    def __str__(self):
        return self.value[1]


class NodeType(enum.Enum):
    """The node type.

    .. rubric:: Enum Members

    ==================  ==================================================================
    :attr:`~Junction`   Node is a :class:`~wntr.network.WaterNetworkModel.Junction`
    :attr:`~Reservoir`  Node is a :class:`~wntr.network.WaterNetworkModel.Reservoir`
    :attr:`~Tank`       Node is a :class:`~wntr.network.WaterNetworkModel.Tank`
    ==================  ==================================================================

    """
    Junction = 0
    Reservoir = 1
    Tank = 2

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class LinkType(enum.Enum):
    """The link type

    .. rubric:: Enum Members

    ===============  ==================================================================
    :attr:`~CV`      Pipe with check valve
    :attr:`~Pipe`    Regular pipe
    :attr:`~Pump`    Pump
    :attr:`~PRV`     Pressure reducing valve
    :attr:`~PSV`     Pressure sustaining valve
    :attr:`~PBV`     Pressure breaker valve
    :attr:`~FCV`     Flow control valve
    :attr:`~TCV`     Throttle control valve
    :attr:`~GPV`     General purpose valve
    ===============  ==================================================================

    """
    CV = 0
    Pipe = 1
    Pump = 2
    PRV = 3
    PSV = 4
    PBV = 5
    FCV = 6
    TCV = 7
    GPV = 8

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class ControlType(enum.Enum):
    """The type of control.

    .. rubric:: Enum Members

    ==================  ==================================================================
    :attr:`~LowLevel`   Act when grade below set level
    :attr:`~HiLevel`    Act when grade above set level
    :attr:`~Timer`      Act when set time reached (from start of simulation)
    :attr:`~TimeOfDay`  Act when time of day occurs (each day)
    ==================  ==================================================================

    """

    LowLevel = 0
    HiLevel = 1
    Timer = 2
    TimeOfDay = 3

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class LinkBaseStatus(enum.Enum):
    """Base status for a link.

    .. rubric:: Enum Members

    ===============  ==================================================================
    :attr:`~Closed`  Pipe/valve/pump is closed.
    :attr:`~Open`    Pipe/valve/pump is open.
    :attr:`~Active`  Valve is partially open.
    ===============  ==================================================================

    """
    Closed = 0
    Open = 1
    Active = 2

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class LinkTankStatus(enum.Enum):
    XHead = 0  #: pump cannot deliver head (closed)
    TempClosed = 1  #: temporarily closed
    Closed = 2 #: closed
    Open = 3  #: open
    Active = 4  #: valve active (partially open)
    XFlow = 5  #: pump exceeds maximum flow
    XFCV = 6  #: FCV cannot supply flow
    XPressure = 7  #: valve cannot supply pressure
    Filling = 8  #: tank filling
    Emptying = 9  #: tank emptying

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class MixType(enum.Enum):
    """Tank mixing model type.

    .. rubric:: Enum Members

    ===============  ==================================================================
    :attr:`~Mix1`    Single compartment mixing model
    :attr:`~Mix2`    Two-compartment mixing model
    :attr:`~FIFO`    First-in/first-out model
    :attr:`~LIFO`    Last-in/first-out model
    ===============  ==================================================================

    """
    Mix1 = 0
    Mix2 = 1
    FIFO = 2
    LIFO = 3

    def __init__(self, val):
        if self.name != self.name.upper():
            self._member_map_[self.name.upper()] = self
        if self.name != self.name.lower():
            self._member_map_[self.name.lower()] = self

    def __str__(self):
        return self.name


class EN(enum.IntEnum):
    """All the ``EN_`` constants for the EPANET toolkit.

    For example, ``EN_LENGTH`` is accessed as ``EN.LENGTH``, instead.  Please see the EPANET
    toolkit documentation for the description of these enums. Several enums are duplicated
    in separaet classes above for clarity during programming.

    """
    ELEVATION    = 0
    BASEDEMAND   = 1
    PATTERN      = 2
    EMITTER      = 3
    INITQUAL     = 4
    SOURCEQUAL   = 5
    SOURCEPAT    = 6
    SOURCETYPE   = 7
    TANKLEVEL    = 8
    DEMAND       = 9
    HEAD         = 10
    PRESSURE     = 11
    QUALITY      = 12
    SOURCEMASS   = 13
    INITVOLUME   = 14
    MIXMODEL     = 15
    MIXZONEVOL   = 16
    TANKDIAM     = 17
    MINVOLUME    = 18
    VOLCURVE     = 19
    MINLEVEL     = 20
    MAXLEVEL     = 21
    MIXFRACTION  = 22
    TANK_KBULK   = 23
    TANKVOLUME   = 24
    MAXVOLUME    = 25
    DIAMETER     = 0
    LENGTH       = 1
    ROUGHNESS    = 2
    MINORLOSS    = 3
    INITSTATUS   = 4
    INITSETTING  = 5
    KBULK        = 6
    KWALL        = 7
    FLOW         = 8
    VELOCITY     = 9
    HEADLOSS     = 10
    STATUS       = 11
    SETTING      = 12
    ENERGY       = 13
    LINKQUAL     = 14
    LINKPATTERN  = 15
    DURATION     = 0
    HYDSTEP      = 1
    QUALSTEP     = 2
    PATTERNSTEP  = 3
    PATTERNSTART = 4
    REPORTSTEP   = 5
    REPORTSTART  = 6
    RULESTEP     = 7
    STATISTIC    = 8
    PERIODS      = 9
    STARTTIME    = 10
    HTIME        = 11
    HALTFLAG     = 12
    NEXTEVENT    = 13
    ITERATIONS   = 0
    RELATIVEERROR= 1
    NODECOUNT    = 0
    TANKCOUNT    = 1
    LINKCOUNT    = 2
    PATCOUNT     = 3
    CURVECOUNT   = 4
    CONTROLCOUNT = 5
    JUNCTION     = 0
    RESERVOIR    = 1
    TANK         = 2
    CVPIPE       = 0
    PIPE         = 1
    PUMP         = 2
    PRV          = 3
    PSV          = 4
    PBV          = 5
    FCV          = 6
    TCV          = 7
    GPV          = 8
    NONE         = 0
    CHEM         = 1
    AGE          = 2
    TRACE        = 3
    CONCEN       = 0
    MASS         = 1
    SETPOINT     = 2
    FLOWPACED    = 3
    CFS          = 0
    GPM          = 1
    MGD          = 2
    IMGD         = 3
    AFD          = 4
    LPS          = 5
    LPM          = 6
    MLD          = 7
    CMH          = 8
    CMD          = 9
    TRIALS       = 0
    ACCURACY     = 1
    TOLERANCE    = 2
    EMITEXPON    = 3
    DEMANDMULT   = 4
    LOWLEVEL     = 0
    HILEVEL      = 1
    TIMER        = 2
    TIMEOFDAY    = 3
    AVERAGE      = 1
    MINIMUM      = 2
    MAXIMUM      = 3
    RANGE        = 4
    MIX1         = 0
    MIX2         = 1
    FIFO         = 2
    LIFO         = 3
    NOSAVE       = 0
    SAVE         = 1
    INITFLOW     = 10
    CONST_HP     = 0
    POWER_FUNC   = 1
    CUSTOM       = 2
