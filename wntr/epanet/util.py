"""
The wntr.epanet.util module contains unit conversion utilities based on EPANET units.
"""
from __future__ import annotations

import dataclasses
import enum
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Union, TypedDict
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    "FlowUnits",
    "MassUnits",
    "QualParam",
    "HydParam",
    "to_si",
    "from_si",
    "StatisticsType",
    "QualType",
    "SourceType",
    "PressureUnits",
    "FormulaType",
    "ControlType",
    "LinkTankStatus",
    "MixType",
    "ResultType",
    "EN",
    "SizeLimits",
    "InitHydOption"
]


class SizeLimits(enum.Enum):
    """
    Limits on the size of character arrays used to store ID names
    and text messages.
    """
    # // ! < Max.  # characters in ID name
    EN_MAX_ID = 31
    # //! < Max.  # characters in message text
    EN_MAX_MSG = 255


class InitHydOption(enum.Enum):
    """
    Hydraulic initialization options.
    These options are used to initialize a new hydraulic analysis
    when EN_initH is called.
    """
    # !< Don't save hydraulics; don't re-initialize flows
    EN_NOSAVE = 0
    # !< Save hydraulics to file, don't re-initialize flows
    EN_SAVE = 1
    # !< Don't save hydraulics; re-initialize flows
    EN_INITFLOW = 10
    # !< Save hydraulics; re-initialize flows
    EN_SAVE_AND_INIT = 11


class FlowUnits(enum.Enum):
    r"""Epanet Units Enum class

    EPANET has defined unit codes that are used in its INP input files.
    This enumerated type class provides the appropriate values, rather than
    setting up a large number of constants. Additionally, each Enum value has
    a property that identifies it as either `traditional` or `metric` flow unit.
    EPANET *does not* use fully SI units - these are provided for WNTR compatibility.

    .. rubric:: Enum Members

    ==============  ====================================  ========================
    :attr:`~CFS`    :math:`\rm ft^3\,/\,s`                :attr:`is_traditional`
    :attr:`~GPM`    :math:`\rm gal\,/\,min`               :attr:`is_traditional`
    :attr:`~MGD`    :math:`\rm 10^6\,gal\,/\,day`         :attr:`is_traditional`
    :attr:`~IMGD`   :math:`\rm 10^6\,Imp.\,gal\,/\,day`   :attr:`is_traditional`
    :attr:`~AFD`    :math:`\rm acre\cdot\,ft\,/\,day`     :attr:`is_traditional`
    :attr:`~LPS`    :math:`\rm L\,/\,s`                   :attr:`is_metric`
    :attr:`~LPM`    :math:`\rm L\,/\,min`                 :attr:`is_metric`
    :attr:`~MLD`    :math:`\rm ML\,/\,day`                :attr:`is_metric`
    :attr:`~CMH`    :math:`\rm m^3\,\,hr`                 :attr:`is_metric`
    :attr:`~CMD`    :math:`\rm m^3\,/\,day`               :attr:`is_metric`
    :attr:`~SI`     :math:`\rm m^3\,/\,s`
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
    <FlowUnits.GPM: (1, 6.30901964e-05)>

    Units can be converted to the EPANET integer values by casting as an ``int`` and can be
    converted to a string by accessing the ``name`` property. The factor to convert to SI units
    is accessed using the ``factor`` property.

    >>> FlowUnits.LPS.name
    'LPS'
    >>> int(FlowUnits.LPS)
    5

    The reverse is also true, where an ``int`` from an EPANET run or the string from and input
    file can be used to get a ``FlowUnits`` object.

    >>> FlowUnits(4)
    <FlowUnits.AFD: (4, 0.014276410185185185)>
    >>> FlowUnits['CMD']
    <FlowUnits.CMD: (9, 1.1574074074074073e-05)>

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
    GPM = (1, (0.003785411784 / 60.0))
    MGD = (2, (1e6 * 0.003785411784 / 86400.0))
    IMGD = (3, (1e6 * 0.00454609 / 86400.0))
    AFD = (4, (1233.48184 / 86400.0))
    LPS = (5, 0.001)
    LPM = (6, (0.001 / 60.0))
    MLD = (7, (1e6 * 0.001 / 86400.0))
    CMH = (8, (1.0 / 3600.0))
    CMD = (9, (1.0 / 86400.0))
    SI = (11, 1.0)

    def __init__(self, EN_id, flow_factor=1.0):
        mmap = getattr(self, "_member_map_")
        v2mmap = getattr(self, "_value2member_map_")
        v2mmap[EN_id] = self
        mmap[str(self.name).lower()] = self

    def __int__(self):
        """Convert to an EPANET Toolkit enum number."""
        value = super().value
        return int(value[0])

    def __str__(self):
        """Convert to a string for INP files."""
        return self.name

    @property
    def factor(self):
        r"""float: The conversion factor to convert units into SI units of :math:`m^3\,s^{-1}`.

        Letting values in the original units be :math:`v`, and the resulting values in SI units
        be :math:`s`, the conversion factor, :math:`f`, such that

        .. math::
            v f = s

        """
        value = super().value
        return value[1]

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
        return self in [
            FlowUnits.CFS,
            FlowUnits.GPM,
            FlowUnits.MGD,
            FlowUnits.IMGD,
            FlowUnits.AFD,
        ]

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
        return self in [
            FlowUnits.LPS,
            FlowUnits.LPM,
            FlowUnits.MLD,
            FlowUnits.CMH,
            FlowUnits.CMD,
        ]


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
        value = super().value
        return value[1]


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
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

    def _to_si(self, flow_units, data, mass_units=MassUnits.mg, reaction_order=0):
        """Convert a water quality parameter to SI units from EPANET units.

        By default, the mass units are the EPANET default of mg, and the reaction order is 0.

        Parameters
        ----------
        flow_units : FlowUnits
            The EPANET flow units to use in the conversion
        data : array-like
            The data to be converted (scalar, array or dictionary)
        mass_units : MassUnits
            The EPANET mass units to use in the conversion (mg or ug)
        reaction_order : int
            The reaction order for use converting reaction coefficients

        Returns
        -------
        float
            The data values converted to SI standard units

        """
        original_data_type = None
        if isinstance(data, dict):
            original_data_type = 'dict'
            data_keys = data.keys()
            data = np.array(data.values())
        elif isinstance(data, list):
            original_data_type = 'list'
            data = np.array(data)

        if mass_units is None:
            mass_units = MassUnits.mg

        # Do conversions
        if self in [QualParam.Concentration, QualParam.Quality,
                    QualParam.LinkQuality, QualParam.ReactionRate]:
            data = data * (mass_units.factor / 0.001)  # MASS /L to kg/m3
            if self in [QualParam.ReactionRate]:
                data = data / (24 * 3600)  # 1/day to 1/s

        elif self in [QualParam.SourceMassInject]:
            data = data * (mass_units.factor / 60.0)  # MASS /min to kg/s

        elif self in [QualParam.BulkReactionCoeff] and reaction_order == 1:
            data = data * (1 / 86400.0)  # per day to per second

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 0:
            if flow_units.is_traditional:
                data = data * (mass_units.factor * 0.092903 / 86400.0)  # M/ft2/d to SI
            else:
                data = data * (mass_units.factor / 86400.0)  # M/m2/day to M/m2/s

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 1:
            if flow_units.is_traditional:
                data = data * (0.3048 / 86400.0)  # ft/d to m/s
            else:
                data = data * (1.0 / 86400.0)  # m/day to m/s

        elif self in [QualParam.SourceMassInject]:
            data = data * (mass_units.factor / 60.0)  # per min to per second

        elif self in [QualParam.WaterAge]:
            data = data * 3600.0  # hr to s

        # Convert back to input data type
        if original_data_type == 'dict':
            data = dict(zip(data_keys, data))
        elif original_data_type == 'list': 
            data = list(data)
            
        return data

    def _from_si(self, flow_units, data, mass_units=MassUnits.mg, reaction_order=0):
        """Convert a water quality parameter back to EPANET units from SI units.

        Mass units defaults to :class:`MassUnits.mg`, as this is the EPANET default.

        Parameters
        ----------
        flow_units : FlowUnits
            The EPANET flow units to use in the conversion
        data : array-like
            The SI unit data to be converted (scalar, array or dictionary)
        mass_units : MassUnits
            The EPANET mass units to use in the conversion (mg or ug)
        reaction_order : int
            The reaction order for use converting reaction coefficients

        Returns
        -------
        float
            The data values converted to EPANET appropriate units, based on the flow units.

        """
        original_data_type = None
        if isinstance(data, dict):
            original_data_type = 'dict'
            data_keys = data.keys()
            data = np.array(data.values())
        elif isinstance(data, list):
            original_data_type = 'list'
            data = np.array(data)

        # Do conversions
        if self in [QualParam.Concentration, QualParam.Quality,
                    QualParam.LinkQuality, QualParam.ReactionRate]:
            data = data / (mass_units.factor / 0.001)  # MASS /L fr kg/m3
            if self in [QualParam.ReactionRate]:
                data = data * (24 * 3600)  # 1/day fr 1/s

        elif self in [QualParam.SourceMassInject]:
            data = data / (mass_units.factor / 60.0)  # MASS /min fr kg/s

        elif self in [QualParam.BulkReactionCoeff] and reaction_order == 1:
            data = data / (1 / 86400.0)  # per day fr per second

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 0:
            if flow_units.is_traditional:
                data = data / (mass_units.factor * 0.092903 / 86400.0)  # M/ft2/d fr SI
            else:
                data = data / (mass_units.factor / 86400.0)  # M/m2/day fr M/m2/s

        elif self in [QualParam.WallReactionCoeff] and reaction_order == 1:
            if flow_units.is_traditional:
                data = data / (0.3048 / 86400.0)  # ft/d fr m/s
            else:
                data = data / (1.0 / 86400.0)  # m/day fr m/s

        elif self in [QualParam.SourceMassInject]:
            data = data / (mass_units.factor / 60.0)  # per min fr per second

        elif self in [QualParam.WaterAge]:
            data = data / 3600.0  # hr fr s

        # Convert back to input data type
        if original_data_type == 'dict':
            data = dict(zip(data_keys, data))
        elif original_data_type == 'list':
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
    :attr:`Elevation`           Nodal elevation
    :attr:`Demand`              Nodal demand
    :attr:`HydraulicHead`       Nodal head
    :attr:`Pressure`            Nodal pressure
    :attr:`EmitterCoeff`        Emitter coefficient
    :attr:`TankDiameter`        Tank diameter
    :attr:`Volume`              Tank volume
    :attr:`Length`              Link length
    :attr:`PipeDiameter`        Pipe diameter
    :attr:`Flow`                Link flow
    :attr:`Velocity`            Link velocity
    :attr:`HeadLoss`            Link headloss (from start node to end node)
    :attr:`RoughnessCoeff`      Link roughness (requires `darcy_weisbach` setting for conversion)
    :attr:`Energy`              Pump energy
    :attr:`Power`               Pump power
    ==========================  ===================================================================


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
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

    def _to_si(self, flow_units, data, darcy_weisbach=False):
        """Convert from EPANET units groups to SI units.

        If converting roughness, specify if the Darcy-Weisbach equation is
        used using the darcy_weisbach parameter. Otherwise, that parameter
        can be safely ignored/omitted for any other conversion.

        Parameters
        ----------
        flow_units : FlowUnits
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
        original_data_type = None
        if isinstance(data, pd.core.frame.DataFrame):
            original_data_type = 'dataframe'
            data_index = data.index
            data_columns = data.columns
            data = data.values
        elif isinstance(data, dict):
            original_data_type = 'dict'
            data_keys = data.keys()
            data = np.array(list(data.values()))
        elif isinstance(data, list):
            original_data_type = 'list'
            data = np.array(data)

        # Do conversions
        if self in [HydParam.Demand, HydParam.Flow, HydParam.EmitterCoeff]:
            data = data * flow_units.factor
            if self is HydParam.EmitterCoeff:
                if flow_units.is_traditional:
                    # flowunit/sqrt(psi) to flowunit/sqrt(m), i.e.,
                    # flowunit/sqrt(psi) * sqrt(psi/ft / m/ft ) = flowunit/sqrt(m)
                    data = data * np.sqrt(0.4333 / 0.3048)
        elif self in [HydParam.PipeDiameter]:
            if flow_units.is_traditional:
                data = data * 0.0254  # in to m
            elif flow_units.is_metric:
                data = data * 0.001  # mm to m

        elif self in [HydParam.RoughnessCoeff] and darcy_weisbach:
            if flow_units.is_traditional:
                data = data * (0.001 * 0.3048)  # 1e-3 ft to m
            elif flow_units.is_metric:
                data = data * 0.001  # mm to m

        elif self in [
            HydParam.TankDiameter,
            HydParam.Elevation,
            HydParam.HydraulicHead,
            HydParam.Length]:
            if flow_units.is_traditional:
                data = data * 0.3048  # ft to m

        elif self in [HydParam.HeadLoss]:
            data = data / 1000  # m/1000m or ft/1000ft to unitless

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
                # psi to m, i.e., psi * (m/ft / psi/ft) = m
                data = data * (0.3048 / 0.4333)

        elif self in [HydParam.Volume]:
            if flow_units.is_traditional:
                data = data * np.power(0.3048, 3)  # ft3 to m3

        # Convert back to input data type
        if original_data_type == 'dataframe':
            data = pd.DataFrame(data, columns=data_columns, index=data_index)
        elif original_data_type == 'dict':
            data = dict(zip(data_keys, data))
        elif original_data_type == 'list':
            data = list(data)
        
        return data

    def _from_si(self, flow_units, data, darcy_weisbach=False):
        """Convert from SI units into EPANET specified units.

        If converting roughness, specify if the Darcy-Weisbach equation is
        used using the darcy_weisbach parameter. Otherwise, that parameter
        can be safely ignored/omitted for any other conversion.

        Parameters
        ----------
        flow_units : FlowUnits
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
        original_data_type = None
        if isinstance(data, dict):
            original_data_type = 'dict'
            data_keys = data.keys()
            data = np.array(list(data.values()))
        elif isinstance(data, list):
            original_data_type = 'list'
            data = np.array(data)

        # Do onversions
        if self in [HydParam.Demand, HydParam.Flow, HydParam.EmitterCoeff]:
            data = data / flow_units.factor
            if self is HydParam.EmitterCoeff:
                if flow_units.is_traditional:
                    # flowunit/sqrt(psi) from flowunit/sqrt(m), i.e.,
                    # flowunit/sqrt(m) * sqrt( m/ft / psi/ft ) = flowunit/sqrt(psi), same as
                    # flowunit/sqrt(m) / sqrt( psi/ft / m/ft ) = flowunit/sqrt(psi)
                    data = data / np.sqrt(0.4333 / 0.3048)
        elif self in [HydParam.PipeDiameter]:
            if flow_units.is_traditional:
                data = data / 0.0254  # in from m
            elif flow_units.is_metric:
                data = data / 0.001  # mm from m

        elif self in [HydParam.RoughnessCoeff] and darcy_weisbach:
            if flow_units.is_traditional:
                data = data / (0.001 * 0.3048)  # 1e-3 ft from m
            elif flow_units.is_metric:
                data = data / 0.001  # mm from m

        elif self in [
            HydParam.TankDiameter,
            HydParam.Elevation,
            HydParam.HydraulicHead,
            HydParam.Length]:
            if flow_units.is_traditional:
                data = data / 0.3048  # ft from m

        elif self in [HydParam.HeadLoss]:
            data = data * 1000  # m/1000m or ft/1000ft from unitless

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
                # psi from m, i.e., m * (psi/ft / m/ft) = psi, same as
                # m / ( m/ft / psi/m ) = psi
                data = data / (0.3048 / 0.4333)

        elif self in [HydParam.Volume]:
            if flow_units.is_traditional:
                data = data / np.power(0.3048, 3)  # ft3 from m3

        # Put back into data format passed in
        if original_data_type  == 'dict':
            data = dict(zip(data_keys, data))
        elif original_data_type == 'list':
            data = list(data)
            
        return data


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
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

    def __str__(self):
        return self.name


class QualType(enum.Enum):
    """Provide the EPANET water quality simulation mode.

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
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

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
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

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
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

    def __str__(self):
        return self.name


class FormulaType(enum.Enum):
    """Formula used for determining head loss due to roughness.

    .. rubric:: Enum Members

    ===============  ==================================================================
    :attr:`~HW`      Hazen-Williams headloss formula
    :attr:`~DW`      Darcy-Weisbach formala; requires units conversion
    :attr:`~CM`      Chezy-Manning formula
    ===============  ==================================================================

    """

    HW = (
        0,
        "H-W",
    )
    """Hazen-Williams headloss formula."""
    DW = (
        1,
        "D-W",
    )
    """Darcy-Weisbach formula, requires untis conversion."""
    CM = (
        2,
        "C-M",
    )
    """Chezy-Manning formula."""

    def __init__(self, eid, inpcode):
        v2mm = getattr(self, "_value2member_map_")
        mmap = getattr(self, "_member_map_")
        v2mm[eid] = self
        mmap[inpcode] = self
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

    def __int__(self):
        value = super().value
        return value[0]

    def __str__(self):
        value = super().value
        return value[1]


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
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

    def __str__(self):
        return self.name


class LinkTankStatus(enum.Enum):
    """The link tank status.

    .. rubric:: Enum Members

    ====================  ==================================================================
    :attr:`~XHead`        Pump cannot deliver head (closed)
    :attr:`~TempClosed`   Temporarily closed
    :attr:`~Closed`       Closed
    :attr:`~Open`         Open
    :attr:`~Active`       Valve active (partially open)
    :attr:`~XFlow`        Pump exceeds maximum flow
    :attr:`~XFCV`         FCV cannot supply flow
    :attr:`~XPressure`    Valve cannot supply pressure
    :attr:`~Filling`      Tank filling
    :attr:`~Emptying`     Tank emptying
    ====================  ==================================================================

    """

    XHead = 0
    TempClosed = 1
    Closed = 2
    Open = 3
    Active = 4
    XFlow = 5
    XFCV = 6
    XPressure = 7
    Filling = 8
    Emptying = 9

    def __init__(self, val):
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

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
    Mixed = 0
    TwoComp = 1

    def __init__(self, val):
        mmap = getattr(self, "_member_map_")
        if self.name != str(self.name).upper():
            mmap[str(self.name).upper()] = self
        if self.name != str(self.name).lower():
            mmap[str(self.name).lower()] = self

    def __str__(self):
        return self.name


class ResultType(enum.Enum):
    """Extended period simulation results type"""

    demand = 1
    head = 2
    pressure = 3
    quality = 4
    flowrate = 5
    velocity = 6
    headloss = 7
    linkquality = 8
    status = 9
    setting = 10
    rxnrate = 11
    frictionfact = 12

    @property
    def is_node(self):
        """Is a nodal property result"""
        if abs(self.value) < 5:
            return True
        return False

    @property
    def is_link(self):
        """Is a link property result"""
        if self.value > 4:
            return True
        return False

    @property
    def is_qual(self):
        """Is related to quality"""
        if self.value in [4, 8, 11]:
            return True
        return False

    @property
    def is_hyd(self):
        """Is related to hydraulics"""
        if self.value in [1, 2, 3, 5, 6, 7, 12]:
            return True
        return False


class EN(enum.IntEnum):
    """All the ``EN_`` constants for the EPANET toolkit.

    For example, ``EN_LENGTH`` is accessed as ``EN.LENGTH``, instead.  Please see the EPANET
    toolkit documentation for the description of these enums. Several enums are duplicated
    in separate classes above for clarity during programming.

    The enums can be broken in the following groups.

    - Node parameters: :attr:`~ELEVATION`, :attr:`~BASEDEMAND`, :attr:`~PATTERN`, :attr:`~EMITTER`, :attr:`~INITQUAL`, :attr:`~SOURCEQUAL`, :attr:`~SOURCEPAT`, :attr:`~SOURCETYPE`, :attr:`~TANKLEVEL`, :attr:`~DEMAND`, :attr:`~HEAD`, :attr:`~PRESSURE`, :attr:`~QUALITY`, :attr:`~SOURCEMASS`, :attr:`~INITVOLUME`, :attr:`~MIXMODEL`, :attr:`~MIXZONEVOL`, :attr:`~TANKDIAM`, :attr:`~MINVOLUME`, :attr:`~VOLCURVE`, :attr:`~MINLEVEL,`, :attr:`~MAXLEVEL`, :attr:`~MIXFRACTION`, :attr:`~TANK_KBULK`, :attr:`~TANKVOLUME`, :attr:`~MAXVOLUME`
    - Link parameters: :attr:`~DIAMETER`, :attr:`~LENGTH`, :attr:`~ROUGHNESS`, :attr:`~MINORLOSS`, :attr:`~INITSTATUS`, :attr:`~INITSETTING`, :attr:`~KBULK`, :attr:`~KWALL`, :attr:`~FLOW`, :attr:`~VELOCITY`, :attr:`~HEADLOSS`, :attr:`~STATUS`, :attr:`~SETTING`, :attr:`~ENERGY`, :attr:`~LINKQUAL`, :attr:`~LINKPATTERN`
    - Time parameters: :attr:`~DURATION`, :attr:`~HYDSTEP`, :attr:`~QUALSTEP`, :attr:`~PATTERNSTEP`, :attr:`~PATTERNSTART`, :attr:`~REPORTSTEP`, :attr:`~REPORTSTART`, :attr:`~RULESTEP`, :attr:`~STATISTIC`, :attr:`~PERIODS`, :attr:`~STARTTIME`, :attr:`~HTIME`, :attr:`~HALTFLAG`, :attr:`~NEXTEVENT`
    - Solver parameters: :attr:`~ITERATIONS`, :attr:`~RELATIVEERROR`
    - Component counts: :attr:`~NODECOUNT`, :attr:`~TANKCOUNT`, :attr:`~LINKCOUNT`, :attr:`~PATCOUNT`, :attr:`~CURVECOUNT`, :attr:`~CONTROLCOUNT`
    - Node types: :attr:`~JUNCTION`, :attr:`~RESERVOIR`, :attr:`~TANK`
    - Link types: :attr:`~CVPIPE`, :attr:`~PIPE`, :attr:`~PUMP`, :attr:`~PRV`, :attr:`~PSV`, :attr:`~PBV`, :attr:`~FCV`, :attr:`~TCV`, :attr:`~GPV`
    - Quality analysis types: :attr:`~NONE`, :attr:`~CHEM`, :attr:`~AGE`, :attr:`~TRACE`
    - Source quality types: :attr:`~CONCEN`, :attr:`~MASS`, :attr:`~SETPOINT`, :attr:`~FLOWPACED`
    - Flow unit types: :attr:`~CFS`, :attr:`~GPM`, :attr:`~MGD`, :attr:`~IMGD`, :attr:`~AFD`, :attr:`~LPS`, :attr:`~LPM`, :attr:`~MLD`, :attr:`~CMH`, :attr:`~CMD`
    - Miscelaneous options: :attr:`~TRIALS`, :attr:`~ACCURACY`, :attr:`~TOLERANCE`, :attr:`~EMITEXPON`, :attr:`~DEMANDMULT`
    - Control types: :attr:`~LOWLEVEL`, :attr:`~HILEVEL`, :attr:`~TIMER`, :attr:`~TIMEOFDAY`
    - Time statistic types: :attr:`~NONE`, :attr:`~AVERAGE`, :attr:`~MINIMUM`, :attr:`~MAXIMUM`, :attr:`~RANGE`
    - Tank mixing model types: :attr:`~MIX1`, :attr:`~MIX2`, :attr:`~FIFO`, :attr:`~LIFO`
    - Save results flag: :attr:`~NOSAVE`, :attr:`~SAVE`, :attr:`~INITFLOW`
    - Pump behavior types: :attr:`~CONST_HP`, :attr:`~POWER_FUNC`, :attr:`~CUSTOM`


    """

    # Node parameters
    ELEVATION = 0
    BASEDEMAND = 1
    PATTERN = 2
    EMITTER = 3
    INITQUAL = 4
    SOURCEQUAL = 5
    SOURCEPAT = 6
    SOURCETYPE = 7
    TANKLEVEL = 8
    DEMAND = 9
    HEAD = 10
    PRESSURE = 11
    QUALITY = 12
    SOURCEMASS = 13
    INITVOLUME = 14
    MIXMODEL = 15
    MIXZONEVOL = 16
    TANKDIAM = 17
    MINVOLUME = 18
    VOLCURVE = 19
    MINLEVEL = 20
    MAXLEVEL = 21
    MIXFRACTION = 22
    TANK_KBULK = 23
    TANKVOLUME = 24
    MAXVOLUME = 25

    # Link parameters
    DIAMETER = 0
    LENGTH = 1
    ROUGHNESS = 2
    MINORLOSS = 3
    INITSTATUS = 4
    INITSETTING = 5
    KBULK = 6
    KWALL = 7
    FLOW = 8
    VELOCITY = 9
    HEADLOSS = 10
    STATUS = 11
    SETTING = 12
    ENERGY = 13
    LINKQUAL = 14
    LINKPATTERN = 15

    # Time parameters
    DURATION = 0
    HYDSTEP = 1
    QUALSTEP = 2
    PATTERNSTEP = 3
    PATTERNSTART = 4
    REPORTSTEP = 5
    REPORTSTART = 6
    RULESTEP = 7
    STATISTIC = 8
    PERIODS = 9
    STARTTIME = 10
    HTIME = 11
    HALTFLAG = 12
    NEXTEVENT = 13

    # Solver parameters
    ITERATIONS = 0
    RELATIVEERROR = 1

    # Count parameters
    NODECOUNT = 0
    TANKCOUNT = 1
    LINKCOUNT = 2
    PATCOUNT = 3
    CURVECOUNT = 4
    CONTROLCOUNT = 5

    # Node Types
    JUNCTION = 0
    RESERVOIR = 1
    TANK = 2

    # Link Types
    CVPIPE = 0
    PIPE = 1
    PUMP = 2
    PRV = 3
    PSV = 4
    PBV = 5
    FCV = 6
    TCV = 7
    GPV = 8

    # Quality Types
    NONE = 0
    CHEM = 1
    AGE = 2
    TRACE = 3

    # Source quality types
    CONCEN = 0
    MASS = 1
    SETPOINT = 2
    FLOWPACED = 3

    # Flow units parameter
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

    # Miscelaneous parameters
    TRIALS = 0
    ACCURACY = 1
    TOLERANCE = 2
    EMITEXPON = 3
    DEMANDMULT = 4

    # Control types
    LOWLEVEL = 0
    HILEVEL = 1
    TIMER = 2
    TIMEOFDAY = 3

    # Statistic Types
    AVERAGE = 1
    MINIMUM = 2
    MAXIMUM = 3
    RANGE = 4

    # Tank mixing parameters
    MIX1 = 0
    MIX2 = 1
    FIFO = 2
    LIFO = 3

    # Hydraulic solver / file parameters
    NOSAVE = 0
    SAVE = 1
    INITFLOW = 10

    # Pump behavior Types
    CONST_HP = 0
    POWER_FUNC = 1
    CUSTOM = 2


def to_si(
        from_units: FlowUnits,
        data,
        param,
        mass_units: MassUnits = MassUnits.mg,
        pressure_units: PressureUnits = None,
        darcy_weisbach: bool = False,
        reaction_order: int = 0,
):
    """Convert an EPANET parameter from internal to SI standard units.

    .. note:: 

        See the `Units <../units.html>`__ page for details on the units for each :class:`~HydParam` or :class:`~QualParam`.
        Other than for flows, most parameters only have one US and one metric unit that is used by EPANET.
        For example, even though flow might be specified in gallons, volumes would be specified in cubic feet
        for any US/English flow rates, and in cubic meters for all metric flow units; e.g., never liters 
        for volumes even when flow is declared as LPS.

        Rememeber that internally, WNTR is **always** expecting the values for a parameter to be in true SI
        units -- meters, kilograms, and seconds -- unless explicitly stated otherwise (e.g., hours for control times).


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

    First, we convert an array of flows from GPM to cubic meters per second (the SI units).

    >>> from wntr.epanet.util import *
    >>> flow_si = to_si(FlowUnits.GPM, [0.1, 1.0, 4.3], HydParam.Flow)
    >>> print(flow_si)
    [6.309019640000001e-06, 6.30901964e-05, 0.00027128784452]

    Next, we show how to convert the quality parameter from the EPANET units of mg/L to kg/m3.
    If that is not the mass units you prefer, it is possible to change them to ug/L, g/L, or kg/L,
    as shown in the second example.

    >>> to_si(FlowUnits.GPM, 4.6, QualParam.Quality)
    0.0046
    >>> to_si(FlowUnits.GPM, 4.6, QualParam.Quality, mass_units=MassUnits.ug)
    4.599999999999999e-06

    It is also possible to convert a dictionary of values.

    >>> to_si(FlowUnits.GPM, {'node1': 5.6, 'node2': 1.2}, HydParam.Pressure)
    {'node1': 3.9392568659127623, 'node2': 0.8441264712670206}

    For certain coefficients, there are flags that will change how the conversion occurs. For example,
    reaction coefficients depend on the reaction order.

    >>> to_si(FlowUnits.GPM, 0.45, QualParam.BulkReactionCoeff, reaction_order=0)
    0.45
    >>> to_si(FlowUnits.GPM, 0.45, QualParam.BulkReactionCoeff, reaction_order=1)
    5.208333333333333e-06


    """
    if isinstance(param, HydParam):
        return param._to_si(from_units, data, darcy_weisbach)
    elif isinstance(param, QualParam):
        return param._to_si(from_units, data, mass_units, reaction_order)
    else:
        raise RuntimeError("Invalid parameter: %s" % param)


def from_si(
        to_units: FlowUnits,
        data,
        param,
        mass_units: MassUnits = MassUnits.mg,
        pressure_units: PressureUnits = None,
        darcy_weisbach: bool = False,
        reaction_order: int = 0,
):
    """Convert an EPANET parameter from SI standard units back to internal units.

    .. note:: 

        See the `Units <../units.html>`__ page for details on the units for each :class:`~HydParam` or :class:`~QualParam`.
        Other than for flows, most parameters only have one US and one metric unit that is used by EPANET.
        For example, even though flow might be specified in gallons, volumes would be specified in cubic feet
        for any US/English flow rates, and in cubic meters for all metric flow units; e.g., never liters 
        for volumes even when flow is declared as LPS.

        Rememeber that internally, WNTR is **always** expecting the values for a parameter to be in true SI
        units -- meters, kilograms, and seconds -- unless explicitly stated otherwise (e.g., hours for control times).


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


    Examples
    --------

    First, we convert an array of flows from SI (cubic meters per second) to GPM.

    >>> from wntr.epanet.util import *
    >>> flow_us = from_si(FlowUnits.GPM, [6.309019640000001e-06, 6.30901964e-05, 0.00027128784452], HydParam.Flow)
    >>> print(flow_us)
    [0.1, 1.0, 4.3]

    Next, we show how to convert the quality parameter from kg/m3 to mg/L and then to ug/L.
    
    >>> from_si(FlowUnits.GPM, 0.0046, QualParam.Quality)
    4.6
    >>> from_si(FlowUnits.GPM, 0.0046, QualParam.Quality, mass_units=MassUnits.ug)
    4600.0

    It is also possible to convert a dictionary of values.

    >>> from_si(FlowUnits.GPM, {'node1': 3.9392568659127623, 'node2': 0.8441264712670206}, HydParam.Pressure)
    {'node1': 5.6, 'node2': 1.2}
    
    Finally, an example showing the conversion of 1000 cubic meters per second into the different flow units.

    >>> from_si(FlowUnits.GPM, 1000.0, HydParam.Flow)  # to gallons per minute
    15850323.141488904
    >>> from_si(FlowUnits.LPS, 1000.0, HydParam.Flow)  # to liters per second
    1000000.0
    >>> from_si(FlowUnits.MGD, 1000.0, HydParam.Flow)  # to million gallons per day
    22824.465323744018


    """
    if isinstance(param, HydParam):
        return param._from_si(to_units, data, darcy_weisbach)
    elif isinstance(param, QualParam):
        return param._from_si(to_units, data, mass_units, reaction_order)
    else:
        raise RuntimeError("Invalid parameter: %s" % param)


@dataclass
class ENcomment:
    """A class for storing EPANET configuration file comments with objects.
    
    Attributes
    ----------
    pre : list of str
        a list of comments to put before the output of a configuration line
    post : str
        a single comment that is attached to the end of the line
    """
    pre: List[str] = field(default_factory=list)
    post: str = None

    def wrap_msx_string(self, string) -> str:
        if self.pre is None or len(self.pre) == 0:
            if self.post is None:
                return '  ' + string
            else:
                return '  ' + string + ' ; ' + self.post
        elif self.post is None:
            return '\n; ' + '\n\n; '.join(self.pre) + '\n\n  ' + string
        else:
            return '\n; ' + '\n\n; '.join(self.pre) + '\n\n  ' + string + ' ; ' + self.post

    def to_dict(self):
        return dataclasses.asdict(self)

NoteType = Union[str, dict, ENcomment]
"""An object that stores EPANET compatible annotation data.

A note (or comment) can be a string, a dictionary of the form :code:`{'pre': List[str], 'post': str}`,
or an :class:`wntr.epanet.util.ENcomment` object.
"""
