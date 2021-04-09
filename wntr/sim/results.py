import copy
import datetime
import enum

import pandas as pd

import numpy as np
import copy
import numpy as np
from wntr.epanet.util import FlowUnits, MassUnits, HydParam, QualParam
from wntr.epanet.util import from_si
from wntr.network.elements import Pipe, Pump, PRValve, PSValve, PBValve, FCValve

class ResultsStatus(enum.IntEnum):
    converged = 1
    error = 0


class SimulationResults(object):
    """
    Water network simulation results class.
    """

    def __init__(self):

        # Simulation time series
        self.timestamp = str(datetime.datetime.now())
        self.network_name = None
        self.sim_time = 0
        self.link = None
        self.node = None

    def __add__(self, other):
        if not isinstance(other, SimulationResults):
            raise ValueError(
                "operating on a results object requires both be SimulationResults"
            )
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "{}[{}] + {}[{}]".format(
            self.network_name, self.timestamp, other.network_name, other.timestamp
        )
        for key in self.link.keys():
            if key in other.link:
                new.link[key] = self.link[key] + other.link[key]
        for key in self.node.keys():
            if key in other.node:
                new.node[key] = self.node[key] + other.node[key]
        return new

    def __sub__(self, other):
        if not isinstance(other, SimulationResults):
            raise ValueError(
                "operating on a results object requires both be SimulationResults"
            )
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "{}[{}] - {}[{}]".format(
            self.network_name, self.timestamp, other.network_name, other.timestamp
        )
        for key in self.link.keys():
            if key in other.link:
                new.link[key] = self.link[key] - other.link[key]
        for key in self.node.keys():
            if key in other.node:
                new.node[key] = self.node[key] - other.node[key]
        return new

    def convert_units(self, wn, flow_units="GPM",  mass_units="mg", 
                      qual_param=None, return_copy=True):
        """
        Convert simulation results to EPANET unit convensions.
        
        See https://wntr.readthedocs.io/en/stable/units.html#epanet-unit-conventions for more details.
        
        Parameters
        ------------
        wn : WaterNetworkModel object
            Water network model, used to determine link type to convert link setting
        
        flow_units : str (optional)
            Flow unit used for conversion. Must be defined in 
            wntr.epanet.util.FlowUnits.  The default is "GPM"

        mass_units : str (optional)
            Mass unit unsed for conversion.  Must be defined in 
            wntr.epanet.util.MassUnits. The default is "mg".
            
        qual_param : str (optional)
            Quality parameter used for conversion, generally taken from wn.options.quality.parameter,
            Options include CONCENTRATION, AGE, TRACE or None.
            If qual_param is TRACE or None, no conversion is needed (unitless).
            The default is None.
            
        return_copy : bool (optional)
            Return a copy of the results object.  The default is True.
        """
        if return_copy:
            results = copy.deepcopy(self)
        else:
            results = self

        if flow_units is not None and isinstance(flow_units, str):
            flow_units = flow_units.upper()
            flow_units = FlowUnits[flow_units]

        if mass_units is not None and isinstance(mass_units, str):
            mass_units = mass_units.lower()
            mass_units = MassUnits[mass_units]

        if (qual_param is not None
            and isinstance(qual_param, str)
            and qual_param in ["CONCENTRATION", "AGE", "TRACE", "NONE"]):
            qual_param = qual_param.upper()
            # qual_param = QualParam[qual_param]

        ### Nodes 
        for key in results.node.keys():
            results.node[key].index = results.node[key].index / 3600

        results.node["demand"] = from_si(
            flow_units, results.node["demand"], HydParam.Demand)
        
        results.node["head"] = from_si(
            flow_units, results.node["head"], HydParam.HydraulicHead)
        
        results.node["pressure"] = from_si(
            flow_units, results.node["pressure"], HydParam.Pressure)

        if qual_param == "CHEMICAL":
            results.node["quality"] = from_si(
                flow_units, results.node["quality"], QualParam.Concentration, mass_units=mass_units)
        elif qual_param == "AGE":
            results.node["quality"] = from_si(
                flow_units, results.node["quality"], QualParam.WaterAge)
        else:
            pass  # Trace or None, no conversion needed

        ### Links 
        for key in self.link.keys():
            results.link[key].index = results.link[key].index / 3600

        results.link["flowrate"] = from_si(
            flow_units, results.link["flowrate"], HydParam.Flow)
        
        results.link["velocity"] = from_si(
            flow_units, results.link["velocity"], HydParam.Velocity)
        
        results.link["headloss"] = from_si(
            flow_units, results.link["headloss"], HydParam.HeadLoss)
        
        # setting is either roughness coefficient for pipes, pressure or flow
        # for valves, and relative speed for pumps (unitless)
        convert_roughness = [isinstance(link, Pipe) for name, link in wn.links()]
        convert_pressure = [isinstance(link, (PRValve, PSValve, PBValve)) for name, link in wn.links()]
        convert_flow = [isinstance(link, FCValve) for name, link in wn.links()]
        
        setting = np.array(results.link["setting"])
        setting[:, convert_roughness] = from_si(
            flow_units, setting[:, convert_roughness], HydParam.RoughnessCoeff, darcy_weisbach=(wn.options.hydraulic.headloss == 'D-W'))
        setting[:, convert_pressure] = from_si(
            flow_units, setting[:, convert_pressure], HydParam.Pressure)
        setting[:, convert_flow] = from_si(
            flow_units, setting[:, convert_flow], HydParam.Flow)
        results.link["setting"] = setting
        
        try:
            if qual_param == "CHEMICAL":
                results.link["quality"] = from_si(
                    flow_units, results.link["quality"], QualParam.Concentration, mass_units=mass_units)
            elif qual_param == "AGE":
                results.link["quality"] = from_si(
                    flow_units, results.link["quality"], QualParam.WaterAge)
            else:
                pass  # Trace or None, no conversion needed
        except:
            pass

        try:
            results.link["reaction_rate"] = from_si(
                flow_units, results.link["reaction_rate"], QualParam.ReactionRate, mass_units=mass_units)
        except:
            pass
        
        # frictionfact no conversion needed
        # status no conversion needed
        
        return results
