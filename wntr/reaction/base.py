import abc
from abc import ABC, abstractmethod, abstractproperty
from collections.abc import MutableMapping
import enum
import logging
from dataclasses import InitVar, asdict, dataclass, field
from enum import Enum, IntFlag
from typing import Any, ClassVar, Dict, Generator, ItemsView, Iterator, KeysView, List, Set, Tuple, Union, ValuesView

import sympy
from sympy import Float, Symbol, init_printing, symbols, Function
from sympy.parsing import parse_expr
from sympy.parsing.sympy_parser import convert_xor, standard_transformations

from wntr.network.model import WaterNetworkModel

from .options import RxnOptions

logger = logging.getLogger(__name__)

RESERVED_NAMES = ("D", "Q", "U", "Re", "Us", "Ff", "Av")
SYMPY_RESERVED = ("E", "I", "pi")
EXPR_TRANSFORMS = standard_transformations + (convert_xor,)

class KeyInOtherDictError(KeyError):
    pass

class VariableNameExistsError(KeyError):
    pass

class RxnVarType(Enum):
    """The type of reaction variable.

    .. rubric:: Valid Values

    The following types are defined, and aliases of the first character
    are also defined.

    .. autosummary::

        Bulk
        Wall
        Constant
        Parameter
        Term

        Species
        Coeff

    """

    BULK = 1
    """A species that reacts with other bulk chemicals"""
    WALL = 2
    """A species that reacts with the pipe walls"""
    CONSTANT = 4
    """A constant coefficient for use in a reaction expression"""
    PARAMETER = 8
    """A coefficient that has a value dependent on the pipe or tank"""
    TERM = 16
    """A term that is aliased for ease of writing expressions"""
    INTERNAL = 32
    """An internal variable - see RESERVED_NAMES"""

    B = BULK
    """Alias for :attr:`Bulk`"""
    W = WALL
    """Alias for :attr:`Wall`"""
    C = CONSTANT
    """Alias for :attr:`Constant`"""
    P = PARAMETER
    """Alias for :attr:`Parameter`"""
    T = TERM
    """Alias for :attr:`Term`"""
    I = INTERNAL
    """Alias for :attr:`Internal`"""
    CONST = CONSTANT
    """Alias for :attr:`Constant`"""
    PARAM = PARAMETER
    """Alias for :attr:`Parameter`"""

    @classmethod
    def make(cls, value: Union[str, int, 'RxnVarType']):
        if value is None: 
            return
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        if isinstance(value, str):
            try:
                return cls[value[0].upper()]
            except KeyError:
                raise KeyError(value)
        raise TypeError("Invalid type '{}'".format(type(value)))


class RxnLocType(Enum):
    """What type of network component does this reaction occur in

    .. rubric:: Valid values

    The following types are defined, and aliases of the first character
    are also defined.

    .. autosummary::

        Pipes
        Tanks
    """

    PIPE = 1
    """The expression describes a reaction in pipes"""
    TANK = 2
    """The expression describes a reaction in tanks"""
    P = PIPE
    """Alias for :attr:`Pipes`"""
    T = TANK
    """Alias for :attr:`Tanks`"""

    @classmethod
    def make(cls, value: Union[str, int, 'RxnLocType']):
        if value is None: 
            return
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        if isinstance(value, str):
            try:
                return cls[value[0].upper()]
            except KeyError:
                raise KeyError(value)
        raise TypeError("Invalid type '{}'".format(type(value)))


class RxnExprType(Enum):
    """The type of reaction expression.

    .. rubric:: Valid values

    The following types are defined, and aliases of the first character
    are also defined.

    .. autosummary::

        Equil
        Rate
        Formula
    """

    EQUIL = 1
    """used for equilibrium expressions where it is assumed that the expression supplied is being equated to zero"""
    RATE = 2
    """used to supply the equation that expresses the rate of change of the given species with respect to time as a function of the other species in the model"""
    FORMULA = 3
    """used when the concentration of the named species is a simple function of the remaining species"""
    E = EQUIL
    """Alias for :attr:`Equil`"""
    R = RATE
    """Alias for :attr:`Rate`"""
    F = FORMULA
    """Alias for :attr:`Formula`"""

    @classmethod
    def make(cls, value: Union[str, int, 'RxnExprType']):
        if value is None: 
            return
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        if isinstance(value, str):
            try:
                return cls[value[0].upper()]
            except KeyError:
                raise KeyError(value)
        raise TypeError("Invalid type '{}'".format(type(value)))


class DisjointMapping(MutableMapping):
    """A dictionary that checks a namespace for existing entries.

    To create a new instance, pass a set to act as a namespace. If the namespace does not
    exist, a new namespace will be instantiated. If it does exist, then a new, disjoint
    dictionary will be created that checks the namespace keys before it will allow a new
    item to be added to the dictionary. An item can only belong to one of the disjoint dictionaries
    associated with the namespace.

    Examples
    --------
    Assume there is a namespace `nodes` that has two distinct subsets of objects, `tanks`
    and `reservoirs`. A name for a tank cannot also be used for a reservoir, and a node
    cannot be both a `tank` and a `reservoir`. A DisjointNamespaceDict allows two separate
    dictionaries to be kept, one for each subtype, but the keys within the two dictionaries
    will be ensured to not overlap.

    Parameters
    ----------
    __keyspace : set
        the name of the namespace for consistency checking
    *args, **kwargs : Any
        regular arguments and keyword arguments passed to the underlying dictionary

    """

    __keyspace: dict = None
    __data: dict = None

    def __new__(cls, __keyspace: dict, *args, **kwargs):
        if __keyspace is None:
            __keyspace = dict()
        newobj = super().__new__(cls)
        return newobj

    def __init__(self, __keyspace, *args, **kwargs):
        self.__keyspace = __keyspace
        temp = dict(*args, **kwargs)
        overlap = set(self.__keyspace.keys()).intersection(temp.keys())
        if overlap:
            raise KeyInOtherDictError(overlap)
        self.__keyspace.update(temp)
        self.__data = temp

    def __getitem__(self, __key: Any) -> Any:
        try:
            return self.__data.__getitem__(__key)
        except KeyError as e:
            if __key in self.__keyspace.keys():
                raise KeyInOtherDictError(__key)
            raise

    def __setitem__(self, __key: Any, __value: Any) -> None:
        if __key not in self.__data.keys() and __key in self.__keyspace.keys():
            raise KeyInOtherDictError(__key)
        return self.__data.__setitem__(__key, __value)

    def __delitem__(self, __key: Any) -> None:
        if __key not in self.__data.keys() and __key in self.__keyspace.keys():
            raise KeyInOtherDictError(__key)
        self.__keyspace.__delitem__(__key)
        return self.__data.__delitem__(__key)

    def __contains__(self, __key: object) -> bool:
        return self.__data.__contains__(__key)

    def __iter__(self) -> Iterator:
        return self.__data.__iter__()

    def __len__(self) -> int:
        return self.__data.__len__()

    def keys(self) -> KeysView:
        return self.__data.keys()

    def items(self) -> ItemsView:
        return self.__data.items()

    def values(self) -> ValuesView:
        return self.__data.values()

    def clear(self) -> None:
        for k in self.__data.keys():
            self.__keyspace.__delitem__(k)
        return self.__data.clear()

    def popitem(self) -> tuple:
        (k, v) = self.__data.popitem()
        self.__keyspace.__delitem__(k)
        return (k, v)

    def new_disjoint_mapping(self):
        return DisjointMapping(self.__keyspace)


@dataclass
class ReactionVariable(ABC):

    name: str

    @abstractproperty
    def var_type(self) -> RxnVarType:
        raise NotImplementedError

    @abstractmethod
    def to_msx_string(self) -> str:
        raise NotImplementedError

    @property
    def symbol(self):
        return sympy.Symbol(self.name)

    def __str__(self) -> str:
        return self.name


@dataclass
class ReactionDynamics(ABC):

    species: str
    location: RxnLocType

    @abstractproperty
    def expr_type(self) -> RxnExprType:
        raise NotImplementedError

    @abstractmethod
    def to_msx_string(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.to_key(self.species, self.location)

    @classmethod
    def to_key(cls, species, location):
        location = RxnLocType.make(location)
        return species + "." + location.name.lower()


class VariableRegistry(ABC):

    @abstractmethod
    def variables(self, var_type=None):
        raise NotImplementedError

    @abstractmethod
    def get_variable(self, name: str) -> ReactionVariable:
        raise NotImplementedError

    @abstractmethod
    def del_variable(self, name: str):
        raise NotImplementedError


class ReactionRegistry(ABC):

    @abstractmethod
    def reactions(self, location=None):
        raise NotImplementedError

    @abstractmethod
    def get_reaction(self, species, location=None) -> List[ReactionDynamics]:
        raise NotImplementedError
    
    @abstractmethod
    def del_reaction(self, species, location=None):
        raise NotImplementedError


class LinkedVariablesMixin:

    __variable_registry = None

    @property
    def _variable_registry(self) -> VariableRegistry:
        return self.__variable_registry

    @_variable_registry.setter
    def _variable_registry(self, value):
        if value is not None and not isinstance(value, VariableRegistry):
            raise TypeError("Linked model must be a RxnModel, got {}".format(type(value)))
        self.__variable_registry = value

@dataclass
class ExpressionMixin(ABC):

    expression: str

    @abstractmethod
    def sympify(self):
        raise NotImplementedError


