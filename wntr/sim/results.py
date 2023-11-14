import datetime
import enum
import numpy as np
import pandas as pd


class ResultsStatus(enum.IntEnum):
    converged = 1
    error = 0


class ResultsBase:
    """Base class for results of various simulations carried out by WNTR.
    The basic structure of a subclass is an object with one or more attributes
    containing dictionaries of dataframes.
    Subclasses are differentiated by defining the class attribute `data_attributes`
    which determines the names of the attributes which will hold dictionaries of 
    DataFrames.

    A small number of mathematical and statistical functions are also provided.
    These functions are applied to all dataframes within the results object (or
    between two results objects) by name, elementwise.

    Assuming ``A`` and ``B`` are both results objects that have the same time
    indices for the results and which describe the same water network physical
    model (i.e., have the same nodes and links), then the following functions 
    are defined:
    """
    def __init__(self):
        # Simulation time series
        self.timestamp = str(datetime.datetime.now())
        self.network_name = None
        for attr in self.data_attributes:
            self.__setattr__(attr, dict())

    def __add__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError(f"operating on a results object requires both be {type(self)}")
        new = type(self.res)()
        new.network_name = "{}[{}] + {}[{}]".format(
            self.network_name, self.timestamp, other.network_name, other.timestamp
        )
        
        for attr in new.data_attributes:
            for key in self.__getattr__(attr).keys():
                if key in other.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    other_dict = other.__getattr__(attr)
                    new.__getattr__(attr)[key] = self_dict[key] + other_dict[key]
        return new
    
    
    def __sub__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError(f"operating on a results object requires both be {type(self)}")
        new = type(self)()
        new.network_name = "{}[{}] - {}[{}]".format(
            self.network_name, self.timestamp, other.network_name, other.timestamp
        )
        for attr in new.data_attributes:
            for key in self.__getattr__(attr).keys():
                if key in other.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    other_dict = other.__getattr__(attr)
                    new.__getattr__(attr)[key] = self_dict[key] - other_dict[key]
        return new

    def __abs__(self):
        new = type(self)()
        new.network_name = "|{}[{}]|".format(self.network_name, self.timestamp)
            
        for attr in new.data_attributes:
            for key in self.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    self_dict[key] = abs(self_dict[key])
        return new

    def __neg__(self):
        new = type(self)()
        new.network_name = "-{}[{}]".format(self.network_name, self.timestamp)
            
        for attr in new.data_attributes:
            for key in self.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    self_dict[key] = -self_dict[key]
        return new

    def min(self):
        """Min operates on each axis separately, therefore it needs to be a function.
        The built-in ``min`` function will not work."""
        new = type(self)()
        new.network_name = "min({}[{}])".format(self.network_name, self.timestamp)

        for attr in new.data_attributes:
            for key in self.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    self_dict[key] = self_dict[key].min(axis=0)
        return new

    def max(self):
        """Max operates on each axis separately, therefore it needs to be a function.
        The built-in ``max`` function will not work."""
        new = type(self)()
        new.network_name = "max({}[{}])".format(self.network_name, self.timestamp)
        
        for attr in new.data_attributes:
            for key in self.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    self_dict[key] = self_dict[key].max(axis=0)
        return new

    # def len(self):
    #     """This is not an iterator, but there is still a meaning to calling its length.
    #     However, this means that ``len`` must be a function called from the object, not
    #     the builtin function."""
    #     for key in self.link.keys():
    #         return len(self.link[key])

    # def sqrt(self):
    #     """Element-wise square root of all values."""
    #     new = type(self)()
    #     new.link = dict()
    #     new.node = dict()
    #     new.network_name = "sqrt({}[{}])".format(self.network_name, self.timestamp)
    #     for key in self.link.keys():
    #         new.link[key] = np.sqrt(self.link[key])
    #     for key in self.node.keys():
    #         new.node[key] = np.sqrt(self.node[key])
    #     return new

    def sum(self):
        """Sum across time for each node/link for each property."""
        new = type(self)()
        new.network_name = "sum({}[{}])".format(self.network_name, self.timestamp)
        
        for attr in new.data_attributes:
            for key in self.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    self_dict[key] = self_dict[key].sum(axis=0)
        return new

    def __pos__(self):
        new = type(self)()
        new.network_name = "+{}[{}]".format(self.network_name, self.timestamp)
        for attr in new.data_attributes:
            for key in self.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    self_dict[key] = +self_dict[key]
        return new

    # def __truediv__(self, other):
    #     new = type(self)()
    #     new.link = dict()
    #     new.node = dict()
    #     if isinstance(other, type(self)):
    #         new.network_name = "{}[{}] / {}[{}]".format(
    #             self.network_name, self.timestamp, other.network_name, other.timestamp
    #         )
    #         for key in self.link.keys():
    #             if key in other.link:
    #                 new.link[key] = self.link[key] / other.link[key]
    #         for key in self.node.keys():
    #             if key in other.node:
    #                 new.node[key] = self.node[key] / other.node[key]
    #         return new
    #     elif isinstance(other, int):
    #         new.network_name = "{}[{}] / {}".format(self.network_name, self.timestamp, other)
    #         for key in self.link.keys():
    #             new.link[key] = self.link[key] / other
    #         for key in self.node.keys():
    #             new.node[key] = self.node[key] / other
    #         return new
    #     else:
    #         raise ValueError(f"operating on a results object requires both be {type(self)}")

    # def __pow__(self, exp, mod=None):
    #     new = type(self)()
    #     new.link = dict()
    #     new.node = dict()
    #     new.network_name = "{}[{}] ** {}".format(self.network_name, self.timestamp, exp)
    #     for key in self.link.keys():
    #         new.link[key] = pow(self.link[key], exp, mod)
    #     for key in self.node.keys():
    #         new.node[key] = pow(self.node[key], exp, mod)
    #     return new

    def _adjust_time(self, ts: int):
        """
        Adjust the time index for the results object by `ts`.

        Parameters
        ----------
        ts : int
            The number of seconds by which to adjust the result dataframe index
        """
        ts = int(ts)
            
        for attr in self.data_attributes:
            for key in self.__getattr__(attr).keys():
                    self_dict = self.__getattr__(attr)
                    self_dict[key].index += ts

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
        if not isinstance(other, type(self)):
            raise ValueError(f"operating on a results object requires both be {type(self)}")
        start_time = other.node["head"].index.values[0]
        keep = self.node["head"].index.values < start_time
        for attr in self.data_attributes:
            self_dict = self.__getattr__(attr)
            other_dict = other.__getattr__(attr)
            for key in self_dict.keys()+other_dict.keys():
                if key in self_dict.keys() and key in other_dict.keys():
                    t2 = pd.concat([self_dict[key].loc[keep], other_dict[key]])
                    self_dict[key] = t2
                elif key not in other_dict.keys():
                    temp = other_dict[list(other_dict.keys())[0]] * np.nan
                    t2 = pd.concat([self_dict[key].loc[keep], temp])
                    self_dict[key] = t2
                elif key not in self_dict.keys():
                    temp = self_dict[list(self_dict.keys())[0]] * np.nan
                    t2 = pd.concat([temp.loc[keep], other_dict[key]])
                    self_dict[key] = t2
    
class WasteWaterResults(ResultsBase):
    data_attributes = ["attr1", "attr2"]
    def __init__(self):
        super(WasteWaterResults, self).__init__()
        
class MSXResults(ResultsBase):
    data_attributes = ["attr3", "attr4"]
    def __init__(self):
        super(WasteWaterResults, self).__init__()

class HydraulicResults(ResultsBase):
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
    data_attributes = ["link", "node"]
    def __init__(self):
        super(HydraulicResults, self).__init__()
