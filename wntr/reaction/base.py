import abc
from abc import ABC, abstractmethod, abstractproperty
from collections.abc import MutableMapping
import enum
import logging
from dataclasses import InitVar, asdict, dataclass, field
from enum import Enum, IntFlag
from typing import Any, ClassVar, Dict, Generator, ItemsView, Iterator, KeysView, List, Set, Tuple, Union, ValuesView, Hashable
import datetime

import sympy
from sympy import Float, Symbol, init_printing, symbols, Function
from sympy.parsing import parse_expr
from sympy.parsing.sympy_parser import convert_xor, standard_transformations

from wntr.network.model import WaterNetworkModel

from .options import RxnOptions

logger = logging.getLogger(__name__)

HYDRAULIC_VARIABLES = [
    {"name": "D", "note": "pipe diameter (feet or meters) "},
    {
        "name": "Kc",
        "note": "pipe roughness coefcient (unitless for Hazen-Williams or Chezy-Manning head loss formulas, millifeet or millimeters for Darcy-Weisbach head loss formula)",
    },
    {"name": "Q", "note": "pipe flow rate (flow units) "},
    {"name": "U", "note": "pipe flow velocity (ft/sec or m/sec) "},
    {"name": "Re", "note": "flow Reynolds number "},
    {"name": "Us", "note": "pipe shear velocity (ft/sec or m/sec) "},
    {"name": "Ff", "note": "Darcy-Weisbach friction factor "},
    {"name": "Av", "note": "Surface area per unit volume (area units/L) "},
    {"name": "Len", "note": "Pipe length (feet or meters)"},
]
RESERVED_NAMES = tuple([v['name'] for v in HYDRAULIC_VARIABLES])
SYMPY_RESERVED = ("E", "I", "pi")
EXPR_TRANSFORMS = standard_transformations + (convert_xor,)

@dataclass
class Citation:
    title: str
    year: int
    author: str = None

    # citation type/subtype (e.g., "report"/"tech. rep.")
    citationtype: str = 'misc'
    citationsubtype: str = None

    # document identifiers
    doi: str = None
    url: str = None
    isrn: str = None
    isbn: str = None
    issn: str = None
    eprint: str = None

    # container titles
    journaltitle: str = None
    maintitle: str = None
    booktitle: str = None
    issuetitle: str = None

    # conference/proceedings info
    eventtitle: str = None
    eventdate: datetime.date = None
    venue: str = None

    # publishing info
    institution: str = None
    organization: str = None
    publisher: str = None
    location: str = None
    howpublished: str = None
    language: str = None
    origlanguage: str = None

    # additional people
    editor: str = None
    bookauthor: str = None
    translator: str = None
    annotator: str = None
    commentator: str = None
    introduction: str = None
    foreword: str = None
    afterword: str = None

    # identifying info
    issue: str = None
    series: str = None
    volume: str = None
    number: str = None
    part: str = None
    edition: str = None
    version: str = None
    chapter: str = None
    pages: str = None
    volumes: str = None
    pagetotal: str = None

    # dates
    month: str = None
    fulldate: datetime.date = None
    urldate: datetime.date = None

    # extra
    note: str = None
    addendum: str = None
    abstract: str = None
    annotation: str = None


class KeyInOtherGroupError(KeyError):
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
    def make(cls, value: Union[str, int, "RxnVarType"]):
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
    def make(cls, value: Union[str, int, "RxnLocType"]):
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
    def make(cls, value: Union[str, int, "RxnExprType"]):
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

    __data: Dict[Hashable, Hashable] = None
    __key_groupnames: Dict[Hashable, str] = None
    __groups: Dict[str, "DisjointMappingGroup"] = None
    __usage: Dict[Hashable, Set[Any]] = None

    def __init__(self, *args, **kwargs):
        self.__data: Dict[Hashable, Any] = dict(*args, **kwargs)
        self.__key_groupnames: Dict[Hashable, str] = dict()
        self.__groups: Dict[str, "DisjointMappingGroup"] = dict()
        self.__usage: Dict[Hashable, Set[Any]] = dict()
        for k, v in self.__data.items():
            self.__key_groupnames[k] = None
            self.__usage[k] = set()

    def add_disjoint_group(self, name):
        if name in self.__groups.keys():
            raise KeyError("Disjoint group already exists within registry")
        new = DisjointMappingGroup(name, self)
        self.__groups.__setitem__(name, new)
        return new

    def get_disjoint_group(self, name: str):
        return self.__groups[name]

    def get_groupname(self, __key: Hashable):
        return self.__key_groupnames[__key]

    def add_item_to_group(self, groupname, key, value):
        current = self.__key_groupnames.get(key, None)
        if current is not None and groupname != current:
            raise KeyInOtherGroupError("The key '{}' is already used in a different group '{}'".format(key, groupname))
        if groupname is not None:
            group = self.__groups[groupname]
            group._data.__setitem__(key, value)
        self.__key_groupnames[key] = groupname
        return self.__data.__setitem__(key, value)

    def move_item_to_group(self, new_group_name, key):
        value = self.__data[key]
        current = self.get_groupname(key)
        if new_group_name is not None:
            new_group = self.__groups[new_group_name]
            new_group._data[key] = value
        if current is not None:
            old_group = self.__groups[current]
            old_group._data.__delitem__(key)
        self.__key_groupnames[key] = new_group_name

    def remove_item_from_group(self, groupname, key):
        current = self.__key_groupnames.get(key, None)
        if groupname != current:
            raise KeyInOtherGroupError("The key '{}' is in a different group '{}'".format(key, groupname))
        if groupname is not None:
            self.__groups[groupname]._data.__delitem__(key)

    def __getitem__(self, __key: Any) -> Any:
        return self.__data.__getitem__(__key)

    def __setitem__(self, __key: Any, __value: Any) -> None:
        current = self.__key_groupnames.get(__key, None)
        if current is not None:
            self.__groups[current]._data[__key] = __value
        return self.__data.__setitem__(__key, __value)

    def __delitem__(self, __key: Any) -> None:
        current = self.__key_groupnames.get(__key, None)
        if current is not None:
            self.__groups[current]._data.__delitem__(__key)
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
        raise RuntimeError("You cannot clear this")

    def popitem(self) -> tuple:
        raise RuntimeError("You cannot pop this")


class DisjointMappingGroup(MutableMapping):
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

    __name: str = None
    __keyspace: DisjointMapping = None
    _data: dict = None

    def __new__(cls, name: str, __keyspace: DisjointMapping):
        if name is None:
            raise TypeError("A name must be specified")
        if __keyspace is None:
            raise TypeError("A registry must be specified")
        newobj = super().__new__(cls)
        return newobj

    def __init__(self, name: str, __keyspace: DisjointMapping):
        if name is None:
            raise TypeError("A name must be specified")
        if __keyspace is None:
            raise TypeError("A registry must be specified")
        self.__name: str = name
        self.__keyspace: DisjointMapping = __keyspace
        self._data = dict()

    def __getitem__(self, __key: Any) -> Any:
        return self._data[__key]

    def __setitem__(self, __key: Any, __value: Any) -> None:
        return self.__keyspace.add_item_to_group(self.__name, __key, __value)

    def __delitem__(self, __key: Any) -> None:
        return self.__keyspace.remove_item_from_group(self.__name, __key)

    def __contains__(self, __key: object) -> bool:
        return self._data.__contains__(__key)

    def __iter__(self) -> Iterator:
        return self._data.__iter__()

    def __len__(self) -> int:
        return self._data.__len__()

    def keys(self) -> KeysView:
        return self._data.keys()

    def items(self) -> ItemsView:
        return self._data.items()

    def values(self) -> ValuesView:
        return self._data.values()

    def clear(self) -> None:
        raise RuntimeError("Cannot clear a group")

    def popitem(self) -> tuple:
        raise RuntimeError("Cannot pop from a group")

    def __repr__(self) -> str:
        return "{}(name={}, data={})".format(self.__class__.__name__, repr(self.__name), self._data)


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

    def __hash__(self) -> int:
        return hash(str(self))


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

    def __hash__(self) -> int:
        return hash(str(self))


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
