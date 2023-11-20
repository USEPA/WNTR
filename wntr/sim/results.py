import datetime
import enum
import numpy as np
import pandas as pd


class ResultsStatus(enum.IntEnum):
    converged = 1
    error = 0

class SimulationResults:
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
    ``C = A.sum()``     Take the sum of each property across time for each node/link
    ==================  ============================================================

    As an example, to calculate the relative difference between the results of two
    simulations, one could do: ``rel_dif = abs(A - B) / A`` (warning - this will operate
    on link statuses as well, which may result in meaningless results for that 
    parameter).

    """
    _data_attributes = ["link", "node"]
    
    def __init__(self):
        # Simulation time series
        self.timestamp = str(datetime.datetime.now())
        self.network_name = None
        for attr in self._data_attributes:
            setattr(self, attr, dict())

    def __add__(self, other):
        if not isinstance(other, SimulationResults):
            raise ValueError(f"operating on a results object requires both be SimulationResults")
        new = SimulationResults()
        new.network_name = "{}[{}] + {}[{}]".format(
            self.network_name, self.timestamp, other.network_name, other.timestamp
        )
        
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                if key in getattr(other, attr).keys():
                    self_dict = getattr(self, attr)
                    other_dict = getattr(other, attr)
                    getattr(new, attr)[key] = self_dict[key] + other_dict[key]
        return new
    
    
    def __sub__(self, other):
        if not isinstance(other, SimulationResults):
            raise ValueError(f"operating on a results object requires both be SimulationResults")
        new = SimulationResults()
        new.network_name = "{}[{}] - {}[{}]".format(
            self.network_name, self.timestamp, other.network_name, other.timestamp
        )
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                if key in getattr(other, attr).keys():
                    self_dict = getattr(self, attr)
                    other_dict = getattr(other, attr)
                    getattr(new, attr)[key] = self_dict[key] - other_dict[key]
        return new

    def __abs__(self):
        new = SimulationResults()
        new.network_name = "|{}[{}]|".format(self.network_name, self.timestamp)
            
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    new_dict = getattr(new, attr)
                    new_dict[key] = abs(self_dict[key])
        return new

    def __neg__(self):
        new = SimulationResults()
        new.network_name = "-{}[{}]".format(self.network_name, self.timestamp)
            
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    new_dict = getattr(new, attr)
                    new_dict[key] = -self_dict[key]
        return new

    def min(self):
        """Min operates on each axis separately, therefore it needs to be a function.
        The built-in ``min`` function will not work."""
        new = SimulationResults()
        new.network_name = "min({}[{}])".format(self.network_name, self.timestamp)
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    new_dict = getattr(new, attr)
                    new_dict[key] = self_dict[key].min(axis=0)
        return new

    def max(self):
        """Max operates on each axis separately, therefore it needs to be a function.
        The built-in ``max`` function will not work."""
        new = SimulationResults()
        new.network_name = "max({}[{}])".format(self.network_name, self.timestamp)
        
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    new_dict = getattr(new, attr)
                    new_dict[key] = self_dict[key].max(axis=0)
        return new

    def sum(self):
        """Sum across time for each node/link for each property."""
        new = SimulationResults()
        new.network_name = "sum({}[{}])".format(self.network_name, self.timestamp)
        
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    new_dict = getattr(new, attr)
                    new_dict[key] = self_dict[key].sum(axis=0)
        return new

    def __pos__(self):
        new = SimulationResults()
        new.network_name = "+{}[{}]".format(self.network_name, self.timestamp)
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    new_dict = getattr(new, attr)
                    new_dict[key] = +self_dict[key]
        return new

    def __truediv__(self, other):
        new = SimulationResults()
        
        if isinstance(other, SimulationResults):
            new.network_name = "{}[{}] / {}[{}]".format(
                self.network_name, self.timestamp, other.network_name, other.timestamp
            )
            for attr in new._data_attributes:
                for key in getattr(self, attr).keys():
                    if key in getattr(other, attr).keys():
                        self_dict = getattr(self, attr)
                        other_dict = getattr(other, attr)
                        getattr(new, attr)[key] = self_dict[key] / other_dict[key]
            return new
                        
        
        elif isinstance(other, int):
            new.network_name = "{}[{}] / {}".format(self.network_name, self.timestamp, other)
            for key in self.link.keys():
                new.link[key] = self.link[key] / other
            for key in self.node.keys():
                new.node[key] = self.node[key] / other
                
            for attr in new._data_attributes:
                for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    getattr(new, attr)[key] = self_dict[key] / other
            return new
        
        else:
            raise ValueError(f"using / on a results object requires the divisor to be SimulationResults or int")

    def __pow__(self, exp, mod=None):
        new = SimulationResults()
        new.network_name = "{}[{}] ** {}".format(self.network_name, self.timestamp, exp)
        for attr in new._data_attributes:
            for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    new_dict = getattr(new, attr)
                    new_dict[key] = pow(self_dict[key], exp, mod)
        return new

    def _adjust_time(self, ts: int):
        """
        Adjust the time index for the results object by `ts`.

        Parameters
        ----------
        ts : int
            The number of seconds by which to adjust the result dataframe index
        
        Returns
        -------
        self: SimulationResults
        """
        ts = int(ts)
            
        for attr in self._data_attributes:
            for key in getattr(self, attr).keys():
                    self_dict = getattr(self, attr)
                    self_dict[key].index += ts
        return self

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
            
        Returns
        -------
        self : SimulationResults

        Raises
        ------
        ValueError
            if `other` is the wrong type
        
        """
        if not isinstance(other, SimulationResults):
            raise ValueError(f"operating on a results object requires both be SimulationResults")
        #NOTE: Below two lines assume that results object has the node attribute and "head" key

        for attr in self._data_attributes:
            self_dict = getattr(self, attr)
            other_dict = getattr(other, attr)
            
            # query for any dataframe to get shape of df in each results object
            self_attr_dataframe = list(self_dict.values())[0]
            other_attr_dataframe = list(other_dict.values())[0]


            all_keys = list(self_dict.keys()) + list(other_dict.keys())
            for key in all_keys:
                self_df = self_dict[key]
                other_df = other_dict[key]
                overlap = self_df.index.intersection(other_df.index)
                if key in self_dict.keys() and key in other_dict.keys():
                    self_dict[key] = pd.concat([self_df[~self_df.index.isin(overlap)], other_df])
                elif key not in other_dict.keys():
                    temp = other_attr_dataframe * np.nan
                    self_dict[key] = pd.concat([self_df[~self_df.index.isin(overlap)], temp])
                elif key not in self_dict.keys():
                    temp = self_attr_dataframe * np.nan
                    self_dict[key] = pd.concat([temp[~temp.index.isin(overlap)], other_df])
        return self
