import datetime
import enum
import numpy as np
import pandas as pd


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

    ==================  ============================================================
    Example function    Description
    ------------------  ------------------------------------------------------------
    ``C = A + B``       Add the values from A and B for each property
    ``C = A - B``       Subtract the property values in B from A
    ``C = A / B``       Divide the property values in A by the values in B
    ``C = A / n``       Divide the property values in A by n [int];
                        note that this only makes sense if calculating an average
    ``C = pow(A, p)``   Raise the property values in A to the p-th power;
                        note the syntax ``C = pow(A, p, mod)`` can also be used
    ``C = abs(A)``      Take the absolute value of the property values in A
    ``C = -A``          Take the negative of all property values in A
    ``C = +A``          Take the positive of all property values in A
    ``C = A.max()``     Get the maximum value for each property for node/link
    ``C = A.min()``     Get the minimum value for each property for node/link
    ``n = A.len()``     Get the number of timesteps within A
    ``C = A.sqrt()``    Take the element-wise square root for all properties
    ``C = A.sum()``     Take the sum of each property across time for each node/link
    ==================  ============================================================

    As an example, to calculate the relative difference between the results of two
    simulations, one could do: ``rel_dif = abs(A - B) / A`` (warning - this will operate
    on link statuses as well, which may result in meaningless results for that 
    parameter).

    """

    def __init__(self):

        # Simulation time series
        self.timestamp = str(datetime.datetime.now())
        self.network_name = None
        self.link = None
        self.node = None

    def __add__(self, other):
        if not isinstance(other, SimulationResults):
            raise ValueError("operating on a results object requires both be SimulationResults")
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
            raise ValueError("operating on a results object requires both be SimulationResults")
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
        new.network_name = "|{}[{}]|".format(self.network_name, self.timestamp)
        for key in self.link.keys():
            new.link[key] = abs(self.link[key])
        for key in self.node.keys():
            new.node[key] = abs(self.node[key])
        return new

    def __neg__(self):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "-{}[{}]".format(self.network_name, self.timestamp)
        for key in self.link.keys():
            new.link[key] = -self.link[key]
        for key in self.node.keys():
            new.node[key] = -self.node[key]
        return new

    def min(self):
        """Min operates on each axis separately, therefore it needs to be a function.
        The built-in ``min`` function will not work."""
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "min({}[{}])".format(self.network_name, self.timestamp)
        for key in self.link.keys():
            new.link[key] = self.link[key].min(axis=0)
        for key in self.node.keys():
            new.node[key] = self.node[key].min(axis=0)
        return new

    def max(self):
        """Max operates on each axis separately, therefore it needs to be a function.
        The built-in ``max`` function will not work."""
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "max({}[{}])".format(self.network_name, self.timestamp)
        for key in self.link.keys():
            new.link[key] = self.link[key].max(axis=0)
        for key in self.node.keys():
            new.node[key] = self.node[key].max(axis=0)
        return new

    def len(self):
        """This is not an iterator, but there is still a meaning to calling its length.
        However, this means that ``len`` must be a function called from the object, not
        the builtin function."""
        for key in self.link.keys():
            return len(self.link[key])

    def sqrt(self):
        """Element-wise square root of all values."""
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "sqrt({}[{}])".format(self.network_name, self.timestamp)
        for key in self.link.keys():
            new.link[key] = np.sqrt(self.link[key])
        for key in self.node.keys():
            new.node[key] = np.sqrt(self.node[key])
        return new

    def sum(self):
        """Sum across time for each node/link for each property."""
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "sum({}[{}])".format(self.network_name, self.timestamp)
        for key in self.link.keys():
            new.link[key] = self.link[key].sum(axis=0)
        for key in self.node.keys():
            new.node[key] = self.node[key].sum(axis=0)
        return new

    def __pos__(self):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "+{}[{}]".format(self.network_name, self.timestamp)
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
            new.network_name = "{}[{}] / {}".format(self.network_name, self.timestamp, other)
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
        new.network_name = "{}[{}] ** {}".format(self.network_name, self.timestamp, exp)
        for key in self.link.keys():
            new.link[key] = pow(self.link[key], exp, mod)
        for key in self.node.keys():
            new.node[key] = pow(self.node[key], exp, mod)
        return new

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

    def append(self, other):
        """
        Combine two results objects into a single, new result object.
        If the times overlap, then the results from the `other` object will take precedence 
        over the values in the calling object. I.e., given ``A.append(B)``, 
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
            raise ValueError("operating on a results object requires both to be SimulationResults")
        start_time = other.node["head"].index.values[0]
        keep = self.node["head"].index.values < start_time
        for key in self.link.keys():
            if key in other.link:
                t2 = pd.concat([self.link[key].loc[keep], other.link[key]])
                self.link[key] = t2
            else:
                temp = other.link["flowrate"] * np.nan
                t2 = pd.concat([self.link[key].loc[keep], temp])
                self.link[key] = t2
        for key in other.link.keys():
            if key not in self.link.keys():
                temp = self.link["flowrate"] * np.nan
                t2 = pd.concat([temp.loc[keep], other.link[key]])
                self.link[key] = t2
        for key in self.node.keys():
            if key in other.node:
                t2 = pd.concat([self.node[key].loc[keep], other.node[key]])
                self.node[key] = t2
            else:
                temp = other.node["head"] * np.nan
                t2 = pd.concat([self.node[key].loc[keep], temp])
                self.node[key] = t2
        for key in other.node.keys():
            if key not in self.node.keys():
                temp = self.node["head"] * np.nan
                t2 = pd.concat([temp.loc[keep],other.node[key]])
                self.node[key] = t2

