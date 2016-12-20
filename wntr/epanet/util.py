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

    ====================================  =============  ===============================
    Traditional (EPANET: US customary)    SI (WNTR)      Metric (EPANET: metric)
    ====================================  =============  ===============================
    CFS (ft\u00B3 / s)                         SI (m\u00B3 / s)     LPS (L / s)
    GPM (gal / min)                                      LPM (L / min)
    MGD (million gal / day)                              MLD (ML / day)
    IMGD (million Imperial gal / day)                    CMH (m\u00B3 / hr)
    AFD (acre-feet / day)                                CMD (m\u00B3 / day)
    ====================================  =============  ===============================


    .. rubric:: Enum Properties

    .. autosummary::
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


    .. note::
        This Enum uses a value of 0 for one of its members, and therefore
        acts in a non-standard way when evaluating truth values. Use ``None`` / ``is None``
        to check for truth values for variables storing a FlowUnits.

    """
    CFS = 0 #: Cubic feet per second, pyepanet.EN_CFS
    GPM = 1 #: Gallons per minute, pyepanet.EN_GPM
    MGD = 2 #: Million gallons per day, pyepanet.EN_MGD
    IMGD = 3 #: Million Imperial gallons per day, pyepanet.EN_IMGD
    AFD = 4 #: Acre-feet per day, pyepanet.EN_AFD
    LPS = 5 #: Liters per second, pyepanet.EN_LPS
    LPM = 6 #: Liters per minute, pyepanet.EN_LPM
    MLD = 7 #: Million liters per day, pyepanet.EN_MLD
    CMH = 8 #: Cubic meters per hour, pyepanet.EN_CMH
    CMD = 9 #: cubic meters per day, pyepanet.EN_CMD
    SI = 11 #: SI units; meters cubed per day; no pyepanet.EN- equivalent

    def __int__(self):
        """Convert to an EPANET Toolkit enum number."""
        return int(self.value)

    @property
    def is_traditional(self):
        """bool : True if flow unit is a US Customary (traditional) unit.

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
        """bool : True if flow unit is an SI Derived (metric) unit.

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
        scale

    """
    mg = (1, 0.000001) #: milligrams (default EPANET mass unit)
    ug = (2, 0.000000001) #: micrograms (optional EPANET mass unit)
    g = (3, 0.001) #: grams (not used by EPANET, but accepted by WNTR)
    kg = (4, 1.0) #: kilograms (not used by EPANET, used by WNTR internally)

    @property
    def scale(self):
        """float : The scaling factor to convert to kg."""
        return self.value[1]


class QualParam(enum.Enum):
    u"""EPANET water quality parameters.

    .. rubric:: Methods

    .. autosummary::
        to_si
        from_si

    .. rubric:: Enum Members

    ======================  ===================================  ========================================
    Parameter/Enum Member   :class:`FlowUnits` are                :class:`FlowUnits` are
                            US customary (traditional),           SI based (metric),
                            MASS = :class:`MassUnits`             MASS = :class:`MassUnits`
    ======================  ===================================  ========================================
    Concentration           (MASS / L)                           (MASS / L)
    BulkReactionCoeff       - (1/day) [1st-order]                - (1/day) [1st-order]
    WallReactionCoeff       - (MASS / ft\u00B2 / day) [0-order]       - (MASS / m\u00B2 / day) [0-order]
                            - (ft / day) [1st-order]             - (m / day) [1st-order]
    SourceMassInject        (MASS / min)                         (MASS / min)
    WaterAge                (hrs)                                (hrs)
    ======================  ===================================  ========================================

    Note: US Customary units apply when CFS, GPM, AFD, or MGD is chosen as
    FlowUnits. SI Metric units apply when flow units are LPS, LPM, MLD, CMH,
    CMD, or SI.

    """
    Concentration = 1
    BulkReactionCoeff = 2
    WallReactionCoeff = 3
    SourceMassInject = 4
    WaterAge = 5

    def to_si(self, flow_units, data, mass_units=MassUnits.mg,
              reaction_order=0):
        """Convert a water quality parameter to SI units from EPANET units."""
        data_type = type(data)
        if data_type is dict:
            data_keys = data.keys()
            data = np.array(data.values())
        elif data_type is list:
            data = np.array(data)

        # Do conversions
        if self in [QualParam.Concentration]:
            data = data * (mass_units.scale/0.001)  # MASS /L to kg/m3

        elif self in [QualParam.SourceMassInject]:
            data = data * (mass_units.scale/60.0)  # MASS /min to kg/s

        elif self in [QualParam.BulkReactionCoeff] and reaction_order == 1:
                data = data * (1/86400.0)  # per day to per second

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 0:
            if flow_units.is_traditional:
                data = data * (mass_units.scale*0.092903/86400.0)  # M/ft2/d to SI
            else:
                data = data * (mass_units.scale/86400.0)  # M/m2/day to M/m2/s

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 1:
            if flow_units.is_traditional:
                data = data * (0.3048/86400.0)  # ft/d to m/s
            else:
                data = data * (1.0/86400.0)  # m/day to m/s

        elif self in [QualParam.SourceMassInject]:
            data = data * (mass_units.scale/60.0)  # per min to per second

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
        """
        data_type = type(data)
        if data_type is dict:
            data_keys = data.keys()
            data = np.array(data.values())
        elif data_type is list:
            data = np.array(data)

        # Do conversions
        if self in [QualParam.Concentration]:
            data = data / (mass_units.scale/0.001)  # MASS /L fr kg/m3

        elif self in [QualParam.SourceMassInject]:
            data = data / (mass_units.scale/60.0)  # MASS /min fr kg/s

        elif self in [QualParam.BulkReactionCoeff] and reaction_order == 1:
                data = data / (1/86400.0)  # per day fr per second

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 0:
            if flow_units.is_traditional:
                data = data / (mass_units.scale*0.092903/86400.0)  # M/ft2/d fr SI
            else:
                data = data / (mass_units.scale/86400.0)  # M/m2/day fr M/m2/s

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 1:
            if flow_units.is_traditional:
                data = data / (0.3048/86400.0)  # ft/d fr m/s
            else:
                data = data / (1.0/86400.0)  # m/day fr m/s

        elif self in [QualParam.SourceMassInject]:
            data = data / (mass_units.scale/60.0)  # per min fr per second

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
    parameter are determined based on the :class:`FlowUnits` used. The table
    below shows the different units as they are defined by EPANET.

    .. rubric:: Methods

    .. autosummary::
        to_si
        from_si

    .. rubric:: Enum Members

    ======================  ====================================  ===============================
    Parameter/Enum Member   :class:`FlowUnits` are                :class:`FlowUnits` are
                            US customary (traditional)            SI based (metric)
    ======================  ====================================  ===============================
    Flow                    FLOW =                                FLOW =

                            - CFS (ft\u00B3 / s)                       - LPS (L / s)
                            - GPM (gal / min)                     - LPM (L / min)
                            - MGD (million gal / day)             - MLD (ML / day)
                            - IMGD (Imperial MGD)                 - CMH (m\u00B3 / hr)
                            - AFD (acre-feet / day)               - CMD (m\u00B3 / day)
    Demand                  (FLOW)                                (FLOW)
    Diameter (Pipes)        (in)                                  ( mm )
    Diameter (Tanks)        (ft)                                  ( m )
    Efficiency              (\%)                                  (\%)
    Elevation               (ft)                                  ( m )
    Emitter Coefficient     (FLOW / (\u221Apsi))                       (FLOW / (\u221Am))
    Energy                  (kW hrs)                              (kW hrs)
    Friction Factor         unitless                              unitless
    Hydraulic Head          (ft)                                  ( m )
    Length                  (ft)                                  ( m )
    Minor Loss Coeff.       unitless                              unitless
    Power                   (HP)                                  (kW)
    Pressure                (psi)                                 ( m )
    Roughness Coefficient   - Darcy-Weisbach (10\u207B\u00B3 ft)            - Darcy-Weisbach (mm)
                            - otherwise unitless                  - otherwise unitless
    Velocity                (ft / s)                              (m / s)
    Volume                  (ft\u00B3)                                 (m\u00B3)
    ======================  ====================================  ===============================


    """
    Demand = 1 #: Demand is specified in :class:`FlowUnits` units
    Flow = 2 #: Flow is specified in :class:`FlowUnits` units
    EmitterCoeff = 3 #: Emitter Coefficient is defined in :class:`FlowUnits` per :math:`psi^{1/2}`
    PipeDiameter = 4 #: Pipe diameter is specified in either inches or millimeters
    RoughnessCoeff = 14 #: For Darcy-Weisbach loss equations, specified in milli-feet or millimeters; otherwise unitless
    TankDiameter = 5 #: Tank diameters are defined in feet or meters
    Elevation = 6 #: Elevation is defined in feet or meters
    HydraulicHead = 7 #: Hydraulic head is defined in feet or meters
    Length = 8 #: Length is defined in feet or meters
    Velocity = 9 #: Velocity is defined in ft/second or meters/second
    Energy = 10 #: Energy is defined in killowatt-hours, regardless or :class:`FlowUnits`
    Power = 11 #: Power is defined in either horsepower or kilowatts
    Pressure = 12 #: Pressure is defined in psi or meters
    Volume = 13 #: Volume is defined in cubic feet or cubic meters

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
            if flow_units is FlowUnits.CFS:
                data = data * 0.0283168466  # ft3/s to m3/s
            elif flow_units is FlowUnits.GPM:
                data = data * (0.003785411784/60.0)  # gal/min to m3/s
            elif flow_units is FlowUnits.MGD:
                data = data * (1e6*0.003785411784/86400.0)  # MM gal/d to m3/s
            elif flow_units is FlowUnits.IMGD:
                data = data * (1e6*0.00454609/86400.0)  # MM imp gal/d to m3/s
            elif flow_units is FlowUnits.AFD:
                data = data * (1233.48184/86400.0)  # acre-feet/day to m3/s
            elif flow_units is FlowUnits.LPS:
                data = data * 0.001  # L/s to m3/s
            elif flow_units is FlowUnits.LPM:
                data = data * (0.001/60.0)  # L/min to m3/s
            elif flow_units is FlowUnits.MLD:
                data = data * (1e6*0.001/86400.0)  # million L/day to m3/s
            elif flow_units is FlowUnits.CMH:
                data = data * (1.0/3600.0)  # m3/hour to m3/s
            elif flow_units is FlowUnits.CMD:
                data = data * (1.0/86400.0)  # m3/day to m3/s
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
                      self.Length]:
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
            if flow_units is FlowUnits.CFS:
                data = data / 0.0283168466  # ft3/s from m3/s
            elif flow_units is FlowUnits.GPM:
                data = data / (0.003785411784/60.0)  # gal/min from m3/s
            elif flow_units is FlowUnits.MGD:
                data = data / (1e6*0.003785411784/86400.0)  # Mgal/d from m3/s
            elif flow_units is FlowUnits.IMGD:
                data = data / (1e6*0.00454609/86400.0)  # M igal/d from m3/s
            elif flow_units is FlowUnits.AFD:
                data = data / (1233.48184/86400.0)  # acre-feet/day from m3/s
            elif flow_units is FlowUnits.LPS:
                data = data / 0.001  # L/s from m3/s
            elif flow_units is FlowUnits.LPM:
                data = data / (0.001/60.0)  # L/min from m3/s
            elif flow_units is FlowUnits.MLD:
                data = data / (1e6*0.001/86400.0)  # million L/day from m3/s
            elif flow_units is FlowUnits.CMH:
                data = data / (1.0/3600.0)  # m3/hour from m3/s
            elif flow_units is FlowUnits.CMD:
                data = data / (1.0/86400.0)  # m3/day from m3/s
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
                      HydParam.Length]:
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



class _StatisticsType(enum.Enum):
    none = 0
    Averaged = 1
    Minimum = 2
    Maximum = 3
    Range = 4


class _QualityType(enum.Enum):
    none = 0
    Chem = 1
    Age = 2
    Trace = 3


class _PressureUnits(enum.Enum):
    psi = 0
    meters = 1
    kPa = 2


class _LinkType(enum.Enum):
    CV = 0
    Pipe = 1
    Pump = 2
    PRV = 3
    PSV = 4
    PBV = 5
    FCV = 6
    TCV = 7
    GPV = 8


class _LinkStatus(enum.Enum):
    Closed = 0
    Open = 1
    Active = 2
    closed = 0
    open = 1
    active = 2


class _OuputLinkStatus(enum.Enum):
    Closed_MaxHeadExceeded = 0
    Closed_Temporary = 1
    Closed = 2
    Open = 3
    Active = 4
    Open_MaxFlowExceeded = 5
    Open_FlowSettingNotMet = 6
    Open_PressureSettingNotMet = 7

