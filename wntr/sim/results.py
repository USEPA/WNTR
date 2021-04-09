import copy
import datetime
import enum

import pandas as pd
from wntr.epanet.util import FlowUnits, HydParam, MassUnits, QualParam, from_si


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
        if not isinstance(other, SimulationResults):
            raise ValueError(
                "operating on a results object requires both be SimulationResults"
            )
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
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

    def _adjust_time(self, ts):
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

        Returns
        -------
        SimulationResults
            New object containing the combined results

        Raises
        ------
        ValueError
            [description]
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

    def convert_units(
        self, flow_units="GPM", mass_units="mg", qual_param=None, return_copy=True
    ):
        """
        Convert simulation results to EPANET unit convensions.
        
        See https://wntr.readthedocs.io/en/stable/units.html#epanet-unit-conventions for more details.
        
        Parameters
        ------------
        flow_units : str
            Flow unit used for conversion.  For example, GPM or LPS.
            flow_unit must be defined in wntr.epanet.util.FlowUnits
            
        mass_units : str
            Mass unit unsed for conversion.  For example, mg or g.
            mass_unit must be defined in wntr.epanet.util.MassUnits
            
        qual_param : str
            Quality parameter used for conversion, generally taken from wn.options.quality.parameter,
            Options include CONCENTRATION, AGE, TRACE or None.
            If qual_param is TRACE or None, no conversion is needed (unitless).
            
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

        if (
            qual_param is not None
            and isinstance(qual_param, str)
            and qual_param in ["CONCENTRATION", "AGE", "TRACE", "NONE"]
        ):
            qual_param = qual_param.upper()
            # qual_param = QualParam[qual_param]

        ## Nodes ##
        for key in results.node.keys():
            results.node[key].index = results.node[key].index / 3600

        results.node["demand"] = from_si(
            flow_units, results.node["demand"], HydParam.Demand
        )
        results.node["head"] = from_si(
            flow_units, results.node["head"], HydParam.HydraulicHead
        )
        results.node["pressure"] = from_si(
            flow_units, results.node["pressure"], HydParam.Pressure
        )

        if qual_param == "CHEMICAL":
            results.node["quality"] = from_si(
                flow_units,
                results.node["quality"],
                QualParam.Concentration,
                mass_units=mass_units,
            )
        elif qual_param == "AGE":
            results.node["quality"] = from_si(
                flow_units, results.node["quality"], QualParam.WaterAge
            )
        else:
            pass  # Trace or None, no conversion needed

        ## Links ##
        for key in self.link.keys():
            results.link[key].index = results.link[key].index / 3600

        results.link["flowrate"] = from_si(
            flow_units, results.link["flowrate"], HydParam.Flow
        )
        results.link["headloss"] = from_si(
            flow_units, results.link["headloss"], HydParam.HeadLoss
        )
        results.link["velocity"] = from_si(
            flow_units, results.link["velocity"], HydParam.Velocity
        )

        if qual_param == "CHEMICAL":
            results.link["quality"] = from_si(
                flow_units,
                results.link["quality"],
                QualParam.Concentration,
                mass_units=mass_units,
            )
        elif qual_param == "AGE":
            results.link["quality"] = from_si(
                flow_units, results.link["quality"], QualParam.WaterAge
            )
        else:
            pass  # Trace or None, no conversion needed

        # frictionfact no conversion needed
        # status no conversion needed
        # setting requires valve type, convert with pressure or flow type, or change setting to pressure_setting and flow_setting.
        # rxnrate, convert with BulkReactionCoeff? or WallReactionCoeff?

        return results
