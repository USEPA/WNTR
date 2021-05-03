import copy
import datetime
import enum

import pandas as pd

import numpy as np
import copy
import numpy as np
from wntr.epanet.util import FlowUnits, MassUnits, HydParam, QualParam
from wntr.epanet.util import from_si
from wntr.network.elements import Pipe, Pump, Valve, PRValve, PSValve, PBValve, FCValve

class ResultsStatus(enum.IntEnum):
    converged = 1
    error = 0


class SimulationResults(object):
    """
    Water network simulation results class.

    A small number of mathematical and statistical functions are also provided.
    These functions are applied to all dataframes within the results object (or
    between two results objects) by name, elementwise.

    Assuming ``A`` and ``B`` are both results objects that have the same time
    indices for the results and which describe the same water network physical
    model (i.e., have the same nodes and links), then the following functions 
    are defined:

    ==================  ===========================================================
    Example function    Description
    ------------------  -----------------------------------------------------------
    ``C = A + B``       Add the values from A and B for each property
    ``C = A - B``       Subtract the property values in B from A
    ``C = A / B``       Divide the property values in A by the values in B
    ``C = A / n``       Divide the property values in A by n [int];
                        note that this only makes sense if calculating an average
    ``C = A ** p``      Raise the property values in A to the p-th power;
                        note the syntax ``C = pow(A, p, mod)`` can also be used
    ``C = abs(A)``      Take the absolute value of the property values in A
    ``C = -A``          Take the negative of all property values in A
    ``C = +A``          Take the positive of all property values in A
    ==================  ===========================================================

    As an example, to calculate the relative difference between the results of two
    simulations, one could do: ``rel_dif = abs(A - B) / A`` (warning - this will operate
    on link statuses as well, which may result in meaningless results for that 
    parameter).

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

    def __abs__(self):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "|{}[{}]|".format(
            self.network_name, self.timestamp
        )
        for key in self.link.keys():
            new.link[key] = abs(self.link[key])
        for key in self.node.keys():
            new.node[key] = abs(self.node[key])
        return new

    def __neg__(self):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "-{}[{}]".format(
            self.network_name, self.timestamp
        )
        for key in self.link.keys():
            new.link[key] = -self.link[key]
        for key in self.node.keys():
            new.node[key] = -self.node[key]
        return new

    def __pos__(self):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "+{}[{}]".format(
            self.network_name, self.timestamp
        )
        for key in self.link.keys():
            new.link[key] = +self.link[key]
        for key in self.node.keys():
            new.node[key] = +self.node[key]
        return new

    def __truediv__(self, other):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        if isinstance(other, SimulationResults):
            new.network_name = "{}[{}] / {}[{}]".format(
                self.network_name, self.timestamp, other.network_name, other.timestamp
            )
            for key in self.link.keys():
                if key in other.link:
                    new.link[key] = self.link[key] / other.link[key]
            for key in self.node.keys():
                if key in other.node:
                    new.node[key] = self.node[key] / other.node[key]
            return new
        elif isinstance(other, int):
            new.network_name = "{}[{}] / {}".format(
                self.network_name, self.timestamp, other
            )
            for key in self.link.keys():
                new.link[key] = self.link[key] / other
            for key in self.node.keys():
                new.node[key] = self.node[key] / other
            return new
        else:
            raise ValueError(
                "operating on a results object requires divisor be a SimulationResults or a float"
            )
        

    def __pow__(self, exp, mod=None):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "{}[{}] ** {}".format(
            self.network_name, self.timestamp, exp
        )
        for key in self.link.keys():
            new.link[key] = pow(self.link[key], exp, mod)
        for key in self.node.keys():
            new.node[key] = pow(self.node[key], exp, mod)
        return new

    def _adjust_time(self, ts: int):
        """
        Adjust the time index for the results object by `ts`.

        Parameters
        ----------
        ts : int
            The number of seconds by which to adjust the result dataframe index
        """
        ts = int(ts)
        for key in self.link.keys():
            self.link[key].index += ts
        for key in self.node.keys():
            self.node[key].index += ts

    def append_results_from(self, other):
        """
        Combine two results objects into a single, new result object.
        If the times overlap, then the results from the `other` object will take precedence 
        over the values in the calling object. I.e., given ``A.append_results_from(B)``, 
        where ``A`` and ``B``
        are both `SimluationResults`, any results from ``A`` that relate to times equal to or
        greater than the starting time of results in ``B`` will be dropped.

        .. warning::
        
            This operations will be performed "in-place" and will change ``A``


        Parameters
        ----------
        other : SimulationResults
            Results objects from a different, and subsequent, simulation.

        Raises
        ------
        ValueError
            if `other` is the wrong type
        
        """
        if not isinstance(other, SimulationResults):
            raise ValueError(
                "operating on a results object requires both be SimulationResults"
            )
        start_time = other.node['head'].index.values[0]
        keep = self.node['head'].index.values < start_time
        for key in self.link.keys():
            if key in other.link:
                t2 = self.link[key].loc[keep].append(other.link[key])
                self.link[key] = t2
            else:
                temp = other.link['flowrate'] * pd.nan
                t2 = self.link[key].loc[keep].append(temp)
                self.link[key] = t2
        for key in other.link.keys():
            if key not in self.link.keys():
                temp = self.link['flowrate'] * pd.nan
                t2 = temp.loc[keep].append(other.link[key])
                self.link[key] = t2
        for key in self.node.keys():
            if key in other.node:
                t2 = self.node[key].loc[keep].append(other.node[key])
                self.node[key] = t2
            else:
                temp = other.node['head'] * pd.nan
                t2 = self.node[key].loc[keep].append(temp)
                self.node[key] = t2
        for key in other.node.keys():
            if key not in self.node.keys():
                temp = self.node['head'] * pd.nan
                t2 = temp.loc[keep].append(other.node[key])
                self.node[key] = t2

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
        
        try:
            columns = results.link["headloss"].columns
            index = results.link["headloss"].index
            headloss = np.array(results.link["headloss"])
            convert_headloss = [isinstance(link, Pipe) for name, link in wn.links()]
            convert_length = [isinstance(link, (Pump, Valve)) for name, link in wn.links()]
            headloss[:, convert_headloss] = from_si(flow_units, headloss[:, convert_headloss], HydParam.HeadLoss)
            headloss[:, convert_length] = from_si(flow_units, headloss[:, convert_length], HydParam.Length)
            results.link["headloss"] = pd.DataFrame(headloss, index=index, columns=columns)
            #results.link["headloss"] = from_si(
            #    flow_units, results.link["headloss"], HydParam.HeadLoss)
        except:
            pass # right now, the WNTRSimulator does not save headloss
            
        # setting is either roughness coefficient for pipes, pressure or flow
        # for valves, and relative speed for pumps (unitless)
        convert_roughness = [isinstance(link, Pipe) for name, link in wn.links()]
        convert_pressure = [isinstance(link, (PRValve, PSValve, PBValve)) for name, link in wn.links()]
        convert_flow = [isinstance(link, FCValve) for name, link in wn.links()]
        
        columns = results.link["setting"].columns
        index = results.link["setting"].index
        setting = np.array(results.link["setting"])
        setting[:, convert_roughness] = from_si(
            flow_units, setting[:, convert_roughness], HydParam.RoughnessCoeff, darcy_weisbach=(wn.options.hydraulic.headloss == 'D-W'))
        setting[:, convert_pressure] = from_si(
            flow_units, setting[:, convert_pressure], HydParam.Pressure)
        setting[:, convert_flow] = from_si(
            flow_units, setting[:, convert_flow], HydParam.Flow)
        results.link["setting"] = pd.DataFrame(setting, index=index, columns=columns)
        
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
