import math
import numpy as np
import logging
from enum import Enum

logger = logging.getLogger('wntr.utils.units')


class FlowUnits(Enum):
    r"""Epanet Units Enum class.

    Attributes
    ----------
    CFS : 0
        cubic feet per second, pyepanet.EN_CFS
    GPM : 1
        gallons per minute, pyepanet.EN_GPM
    MGD : 2
        million gallons per day, pyepanet.EN_MGD
    IMGD : 3
        Imperial mgd, pyepanet.EN_IMGD
    AFD : 4
        acre-feet per day, pyepanet.EN_AFD
    LPS : 5
        liters per second, pyepanet.EN_LPS
    LPM : 6
        liters per minute, pyepanet.EN_LPM
    MLD : 7
        million liters per day, pyepanet.EN_MLD
    CMH : 8
        cubic meters per hour, pyepanet.EN_CMH
    CMD : 9
        cubic meters per day, pyepanet.EN_CMD
    MKS, SI : 11
        SI units; meters cubed per day; no pyepanet.EN... equivalent


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
    SI = 11

    def __int__(self):
        """Convert to an EPANET Toolkit enum number."""
        return int(self.value)

    @property
    def is_traditional(self):
        """True if flow unit is a US Customary (traditional) unit.

        Traditional units include CFS, GPM, MGD, IMGD and AFD.
        """
        return self in [self.CFS, self.GPM, self.MGD, self.IMGD, self.AFD]

    @property
    def is_metric(self):
        """True if flow unit is an SI Derived (metric) unit.

        Metric units include LPS, LPM, MLD, CMH, and CMD.
        This 'does not' include FlowUnits.SI itself, only 'derived' units.
        """
        return self in [self.LPS, self.LPM, self.MLD, self.CMH, self.CMD]


class MassUnits(Enum):
    r"""Mass units used by EPANET, plus SI conversion factor.

    The SI property returns the conversion factor (kg / unit).
    """
    mg = (1, 0.000001)
    ug = (2, 0.000000001)
    g = (3, 0.001)
    kg = (4, 1.0)

    @property
    def SI(self):
        return self.value[1]


class QualParam(Enum):
    r"""EPANET water quality parameters.

    Attributes
    ----------
    Concentration :
        Mass units per volume. However, EPANET always returns units of either
        mg/L or ug/L -- not SI or US Customary units.

    BulkReactionCoeff :
        Unitless for zero-order, or per-day for first-order reactions.

    WallReactionCoeff :
        Units of mass per-square-feet per-day or mass per-square-meter per-day
        for zero-order reactions, or feet per-day or meters per-day for first-
        order reactions.

    SourceMass :
        Source mass based on mass units used; EPANET only accepts mg and ug,
        based on how concetration is specified in the input file. Internally,
        WaterNetworkModel uses SI standard kilograms.

    WaterAge :
        EPANET always reports this in hours.

    Notes
    -----
    Appendix A from EPANET2 user manual

    ======================  ===================================  ========================================
    PARAMETER               US CUSTOMARY                         SI METRIC
    ======================  ===================================  ========================================
    Concentration           mass / L                             mass / L
    Reaction Coeff. (Bulk)  1/day (1st-order)                    1/day (1st-order)
    Reaction Coeff. (Wall)  - mass / sq. ft / day (0-order)      - mass / sq. meter / day (0-order)
                            - ft / day (1st-order)               - meters / day (1st-order)
    Source Mass Injection   mass / minute                        mass / minute
    Water Age               hours                                hours
    ======================  ===================================  ========================================

    Note: US Customary units apply when CFS, GPM, AFD, or MGD is chosen as
    FlowUnits. SI Metric units apply when flow units are LPS, LPM, MLD, CMH,
    CMD, or SI.

    ..note:

        There is an error in the EPANET users manual appendix A that says the
        wall reaction coefficient is in mass / liter / day for both US/SI
        units. Reading page 96, it is clear this is not the case, the revised
        conversions listed above are the ones used internally.


    """
    Concentration = 1
    BulkReactionCoeff = 2
    WallReactionCoeff = 3
    SourceMassInject = 4
    WaterAge = 5

    def to_si(self, flow_units, data, mass_units=MassUnits.mg,
              reaction_order=0):
        data_type = type(data)
        if data_type is dict:
            data_keys = data.keys()
            data = np.array(data.values())
        elif data_type is list:
            data = np.array(data)

        # Do conversions
        if self in [self.Concentration]:
            data = data * (mass_units.SI/0.001)  # MASS /L to kg/m3

        elif self in [self.SourceMassInject]:
            data = data * (mass_units.SI/60.0)  # MASS /min to kg/s

        elif self in [self.BulkReactionCoeff] and reaction_order == 1:
                data = data * (1/86400.0)  # per day to per second

        elif self in [self.WallReactionCoeff] and reaction_order == 0:
            if flow_units.is_traditional:
                data = data * (mass_units.SI*0.092903/86400.0)  # M/ft2/d to SI
            else:
                data = data * (mass_units.SI/86400.0)  # M/m2/day to M/m2/s

        elif self in [self.WallReactionCoeff] and reaction_order == 1:
            if flow_units.is_traditional:
                data = data * (0.3048/86400.0)  # ft/d to m/s
            else:
                data = data * (1.0/86400.0)  # m/day to m/s

        elif self in [self.SourceMassInject]:
            data = data * (mass_units.SI/60.0)  # per min to per second

        elif self in [self.WaterAge]:
            data = data * 3600.0  # hr to s

        # Convert back to input data type
        if data_type is dict:
            data = dict(zip(data_keys, data))
        elif data_type is list:
            data = list(data)
        return data

    def from_si(self, flow_units, data, mass_units=MassUnits.mg,
                reaction_order=0):
        data_type = type(data)
        if data_type is dict:
            data_keys = data.keys()
            data = np.array(data.values())
        elif data_type is list:
            data = np.array(data)

        # Do conversions
        if self in [self.Concentration]:
            data = data / (mass_units.SI/0.001)  # MASS /L fr kg/m3

        elif self in [self.SourceMassInject]:
            data = data / (mass_units.SI/60.0)  # MASS /min fr kg/s

        elif self in [self.BulkReactionCoeff] and reaction_order == 1:
                data = data / (1/86400.0)  # per day fr per second

        elif self in [self.WallReactionCoeff] and reaction_order == 0:
            if flow_units.is_traditional:
                data = data / (mass_units.SI*0.092903/86400.0)  # M/ft2/d fr SI
            else:
                data = data / (mass_units.SI/86400.0)  # M/m2/day fr M/m2/s

        elif self in [self.WallReactionCoeff] and reaction_order == 1:
            if flow_units.is_traditional:
                data = data / (0.3048/86400.0)  # ft/d fr m/s
            else:
                data = data / (1.0/86400.0)  # m/day fr m/s

        elif self in [self.SourceMassInject]:
            data = data / (mass_units.SI/60.0)  # per min fr per second

        elif self in [self.WaterAge]:
            data = data / 3600.0  # hr fr s

        # Convert back to input data type
        if data_type is dict:
            data = dict(zip(data_keys, data))
        elif data_type is list:
            data = list(data)
        return data


class HydParam(Enum):
    r"""EPANET hydraulics and energy parameters.


    Attributes
    ----------
    Demand :

    Flow :

    EmitterCoefficient :

    PipeDiameter :

    RoughnessCoeff :

    TankDiameter :

    Elevation :

    HydraulicHead :

    Length :

    Velocity :

    Energy :

    Power :

    Pressure :

    Volume :


    Notes
    -----
    Appendix A from EPANET2 user manual

    ======================  ============================  ===============================
    PARAMETER               US CUSTOMARY                  SI METRIC
    ======================  ============================  ===============================
    FlowUnits               CFS, GPM, MGD, IMGD, AFD      LPS, LPM, MLD, CMH, CMD
    Concentration           mg/L or ug/L                  mg/L or ug/L
    Demand                  (see Flow units)              (see Flow units)
    Diameter(Pipes)         inches                        millimeters
    Diameter(Tanks)         feet                          meters
    Efficiency              percent                       percent
    Elevation               feet                          meters
    Emitter Coefficient     flow units / (psi)1/2         flow units / (meters)1/2
    Energy                  kilowatt - hours              kilowatt - hours
    Flow                    - CFS (cubic feet / sec)      - LPS (liters / sec)
                            - GPM (gallons / min)         - LPM (liters / min)
                            - MGD (million gal / day)     - MLD (megaliters / day)
                            - IMGD (Imperial MGD)         - CMH (cubic meters / hr)
                            - AFD (acre-feet / day)       - CMD (cubic meters / day)
    Friction Factor         unitless                      unitless
    Hydraulic Head          feet                          meters
    Length                  feet                          meters
    Minor Loss Coeff.       unitless                      unitless
    Power                   horsepower                    kilowatts
    Pressure                psi                           meters
    Reaction Coeff. (Bulk)  1/day (1st-order)             1/day (1st-order)
    Reaction Coeff. (Wall)  - mass / L / day (0-order)    - mass / L / day (0-order)
                            - ft / day (1st-order)        - meters / day (1st-order)
    Roughness Coefficient   - 10-3 feet (Darcy-Weisbach)  - millimeters (Darcy-Weisbach)
                            - unitless otherwise          - unitless otherwise
    Source Mass Injection   mass / minute                 mass / minute
    Velocity                feet / second                 meters / second
    Volume                  cubic feet                    cubic meters
    Water Age               hours                         hours
    ======================  ============================  ===============================

    Note: US Customary units apply when CFS, GPM, AFD, or MGD is chosen as Flow Units. SI Metric units apply when flow units are expressed using either
    liters or cubic meters.

    """
    Demand = 1
    Flow = 2
    EmitterCoeff = 3
    PipeDiameter = 4
    RoughnessCoeff = 14
    TankDiameter = 5
    Elevation = 6
    HydraulicHead = 7
    Length = 8
    Velocity = 9
    Energy = 10
    Power = 11
    Pressure = 12
    Volume = 13

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
            data = np.array(data.values())
        elif data_type is list:
            data = np.array(data)

        # Do conversions
        if self in [self.Demand, self.Flow, self.EmitterCoeff]:
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
            if self is self.EmitterCoeff:
                if flow_units.is_traditional:
                    data = data / 0.7032  # flowunit/psi0.5 to flowunit/m0.5

        elif self in [self.PipeDiameter]:
            if flow_units.is_traditional:
                data = data * 0.0254  # in to m
            elif flow_units.is_metric:
                data = data * 0.001  # mm to m

        elif self in [self.RoughnessCoeff] and darcy_weisbach:
            if flow_units.is_traditional:
                data = data * (1000.0*0.3048)  # 1e-3 ft to m
            elif flow_units.is_metric:
                data = data * 0.001  # mm to m

        elif self in [self.TankDiameter, self.Elevation, self.HydraulicHead,
                      self.Length]:
            if flow_units.is_traditional:
                data = data * 0.3048  # ft to m

        elif self in [self.Velocity]:
            if flow_units.is_traditional:
                data = data * 0.3048  # ft/s to m/s

        elif self in [self.Energy]:
            data = data * 3600000.0  # kW*hr to J

        elif self in [self.Power]:
            if flow_units.is_traditional:
                data = data * 745.699872  # hp to W (Nm/s)
            elif flow_units.is_metric:
                data = data * 1000.0  # kW to W (Nm/s)

        elif self in [self.Pressure]:
            if flow_units.is_traditional:
                data = data * 0.703249614902  # psi to m

        elif self in [self.Volume]:
            if flow_units.is_traditional:
                data = data * math.pow(0.3048, 3)  # ft3 to m3

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
            data = np.array(data.values())
        elif data_type is list:
            data = np.array(data)

        # Do onversions
        if self in [self.Demand, self.Flow, self.EmitterCoeff]:
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
            if self is self.EmitterCoeff:
                if flow_units.is_traditional:
                    data = data / 0.7032  # flowunit/psi0.5 from flowunit/m0.5

        elif self in [self.PipeDiameter]:
            if flow_units.is_traditional:
                data = data / 0.0254  # in from m
            elif flow_units.is_metric:
                data = data / 0.001  # mm from m

        elif self in [self.RoughnessCoeff] and darcy_weisbach:
            if flow_units.is_traditional:
                data = data / (1000.0*0.3048)  # 1e-3 ft from m
            elif flow_units.is_metric:
                data = data / 0.001  # mm from m

        elif self in [self.TankDiameter, self.Elevation, self.HydraulicHead,
                      self.Length]:
            if flow_units.is_traditional:
                data = data / 0.3048  # ft from m

        elif self in [self.Velocity]:
            if flow_units.is_traditional:
                data = data / 0.3048  # ft/s from m/s

        elif self in [self.Energy]:
            data = data / 3600000.0  # kW*hr from J

        elif self in [self.Power]:
            if flow_units.is_traditional:
                data = data / 745.699872  # hp from W (Nm/s)
            elif flow_units.is_metric:
                data = data / 1000.0  # kW from W (Nm/s)

        elif self in [self.Pressure]:
            if flow_units.is_traditional:
                data = data / 0.703249614902  # psi from m

        elif self in [self.Volume]:
            if flow_units.is_traditional:
                data = data / math.pow(0.3048, 3)  # ft3 from m3

        # Put back into data format passed in
        if data_type is dict:
            data = dict(zip(data_keys, data))
        elif data_type is list:
            data = list(data)
        return data


def convert(paramtype, flowunit, data, MKS=True):
    r"""Convert epanet data to SI units (kg, m, sec)

    Parameters
    ----------
    paramtype : string
        Parameter type, options include:

        - Concentration
        - Demand
        - Flow
        - Emitter Coefficient
        - Pipe Diameter
        - Tank Diameter
        - Elevation
        - Hydraulic Head
        - Length
        - Velocity
        - Energy
        - Power
        - Pressure
        - Source Mass Injection
        - Volume
        - Water Age

    flowunit : int
        The flowunit from the inp file, found using enData.ENgetflowunits(),
        options include:

        - 0 = cubic feet per second, pyepanet.EN_CFS
        - 1 = gallons per minute, pyepanet.EN_GPM
        - 2 = million gallons per day, pyepanet.EN_MGD
        - 3 = Imperial mgd, pyepanet.EN_IMGD
        - 4 = acre-feet per day, pyepanet.EN_AFD
        - 5 = liters per second, pyepanet.EN_LPS
        - 6 = liters per minute, pyepanet.EN_LPM
        - 7 = million liters per day, pyepanet.EN_MLD
        - 8 = cubic meters per hour, pyepanet.EN_CMH
        - 9 = cubic meters per day, pyepanet.EN_CMD

    data : list, numpy array, dictonary, or scalar
        Data value(s) to convert

    MKS : bool, default = True
        Convert to meter-kg-seconds (True) or from meter-kg-seconds (False)

    Returns
    -------
    converted_data : list, numpy array, dictonary, or scalar
        Converted data, same size and type as data

    Examples
    --------
    >>> data = np.array([10,20,30])
    >>> convert('Length', 1, data)
    array([ 3.048,  6.096,  9.144])

    >>> convert('Pressure', 2, 30)
    21.096

    >>> convert('Pressure', 2, 21.096, MKS=False)
    29.999

    Notes
    -----
    Appendix A from EPANET2 user manual

    ======================  ============================  ===============================
    PARAMETER               US CUSTOMARY                  SI METRIC
    ======================  ============================  ===============================
    flowunit                0,1,2,3,4                     5,6,7,8,9
    Concentration           mg/L or mg/L                  mg/L or mg/L
    Demand                  (see Flow units)              (see Flow units)
    Diameter(Pipes)         inches                        millimeters
    Diameter(Tanks)         feet                          meters
    Efficiency              percent                       percent
    Elevation               feet                          meters
    Emitter Coefficient     flow units / (psi)1/2         flow units / (meters)1/2
    Energy                  kilowatt - hours              kilowatt - hours
    Flow                    - CFS (cubic feet / sec)      - LPS (liters / sec)
                            - GPM (gallons / min)         - LPM (liters / min)
                            - MGD (million gal / day)     - MLD (megaliters / day)
                            - IMGD (Imperial MGD)         - CMH (cubic meters / hr)
                            - AFD (acre-feet / day)       - CMD (cubic meters / day)
    Friction Factor         unitless                      unitless
    Hydraulic Head          feet                          meters
    Length                  feet                          meters
    Minor Loss Coeff.       unitless                      unitless
    Power                   horsepower                    kilowatts
    Pressure                psi                           meters
    Reaction Coeff. (Bulk)  1/day (1st-order)             1/day (1st-order)
    Reaction Coeff. (Wall)  - mass / L / day (0-order)    - mass / L / day (0-order)
                            - ft / day (1st-order)        - meters / day (1st-order)
    Roughness Coefficient   - 10-3 feet (Darcy-Weisbach)  - millimeters (Darcy-Weisbach)
                            - unitless otherwise          - unitless otherwise
    Source Mass Injection   mass / minute                 mass / minute
    Velocity                feet / second                 meters / second
    Volume                  cubic feet                    cubic meters
    Water Age               hours                         hours
    ======================  ============================  ===============================

    Note: US Customary units apply when CFS, GPM, AFD, or MGD is chosen as flow
    units. SI Metric units apply when flow units are expressed using either
    liters or cubic meters.

    """

    data_type = type(data)
    if data_type is dict:
        data_keys = data.keys()
        data = np.array(data.values())
    elif data_type is list:
        data = np.array(data)

    if paramtype == 'Concentration':
        if MKS: data = data * (1.0e-6/0.001) # mg/L to kg/m3
        else:   data = data / (1.0e-6/0.001) # kg/m3 to mg/L

    elif paramtype in ['Demand', 'Flow', 'Emitter Coefficient']:
        if flowunit == 0:
            if MKS: data = data * 0.0283168466 # ft3/s to m3/s
            else:   data = data / 0.0283168466 # m3/s to ft3/s
        elif flowunit == 1:
            if MKS: data = data * (0.003785411784/60.0) # gall/min to m3/s
            else:   data = data / (0.003785411784/60.0) # m3/s to gall/min
        elif flowunit == 2:
            if MKS: data = data * (1e6*0.003785411784/86400.0) # million gall/d to m3/s
            else:   data = data / (1e6*0.003785411784/86400.0) # m3/s to million gall/d
        elif flowunit == 3:
            if MKS: data = data * (1e6*0.00454609/86400.0) # million imperial gall/d to m3/s
            else:   data = data / (1e6*0.00454609/86400.0) # m3/s to million imperial gall/d
        elif flowunit == 4:
            if MKS: data = data * (1233.48184/86400.0) # acre-feet/day to m3/s
            else:   data = data / (1233.48184/86400.0) # m3/s to acre-feet/day
        elif flowunit == 5:
            if MKS: data = data * 0.001 # L/s to m3/s
            else:   data = data / 0.001 # m3/s to L/s
        elif flowunit == 6:
            if MKS: data = data * (0.001/60.0) # L/min to m3/s
            else:   data = data / (0.001/60.0) # m3/s to L/min
        elif flowunit == 7:
            if MKS: data = data * (1e6*0.001/86400.0) # million L/day to m3/s
            else:   data = data / (1e6*0.001/86400.0) # m3/s to million L/day
        elif flowunit == 8:
            if MKS: data = data / 3600.0 # m3/hour to m3/s
            else:   data = data * 3600.0 # m3/s to m3/hour
        elif flowunit == 9:
            if MKS: data = data / 86400.0 # m3/day to m3/s
            else:   data = data * 86400.0 # m3/s to m3/day

        if paramtype == 'Emitter Coefficient':
            if flowunit in [0,1,2,3,4]:
                if MKS: data = data / 0.7032 # flowunit/psi0.5 to flowunit/m0.5
                else:   data = data * 0.7032 # flowunit/m0.5 to flowunit/psi0.5

    elif paramtype == 'Pipe Diameter':
        if flowunit in [0,1,2,3,4]:
            if MKS: data = data * 0.0254 # in to m
            else:   data = data / 0.0254 # m to in
        else:
            if MKS: data = data * 0.001 # mm to m
            else:   data = data / 0.001 # m to mm

    elif paramtype in ['Tank Diameter', 'Elevation', 'Hydraulic Head', 'Length']:
        if flowunit in [0,1,2,3,4]:
            if MKS: data = data * 0.3048 # ft to m
            else: data = data / 0.3048 # m to ft

    elif paramtype in 'Velocity':
        if flowunit in [0,1,2,3,4]:
            if MKS: data = data * 0.3048 # ft/s to m/s
            else:   data = data / 0.3048 # m/s to ft/s

    elif paramtype == 'Energy':
        if MKS: data = data * 3600000.0 # kW*hr to J
        else:   data = data / 3600000.0 # J to kW*hr

    elif paramtype == 'Power':
        if flowunit in [0,1,2,3,4]:
            if MKS: data = data * 745.699872 # hp to W (Nm/s)
            else:   data = data / 745.699872 # W (Nm/s) to hp
        else:
            if MKS: data = data * 1000 # kW to W (Nm/s)
            else:   data = data / 1000 # W (Nm/s) to kW

    elif paramtype == 'Pressure':
        if flowunit in [0,1,2,3,4]:
            if MKS: data = data * 0.703249614902 # psi to m
            else:   data = data / 0.703249614902 # m to psi
        """
        if flowunit in [0,1,2,3,4]:
            if MKS: data = data * 6894.75729 # psi to Pa
            else: data = data / 6894.75729 # Pa to psi
        else:
            if MKS: data = data * 9806.65 # m to Pa, assumes 1000 kg/m3
               else: data = data / 9806.65 # Pa to m
        """

    elif paramtype == 'Source Mass Injection':
        if MKS: data = data / 60.0 # per min to per second
        else:   data = data * 60.0 # per second ro per min

    elif paramtype == 'Volume':
        if flowunit in [0,1,2,3,4]:
            if MKS: data = data * math.pow(0.3048, 3) # ft3 to m3
            else:   data = data / math.pow(0.3048, 3) # m3 to ft3

    elif paramtype == 'Water Age':
        if MKS: data = data * 3600.0 # hr to s
        else:   data = data / 3600.0 # s to hr

    else:
        logger.warning("Invalid paramtype: " + paramtype + ". No conversion")

    if data_type is dict:
        data = dict(zip(data_keys, data))
    elif data_type is list:
        data = list(data)

    return data
