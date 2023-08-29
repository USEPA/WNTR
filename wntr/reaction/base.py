# -*- coding: utf-8 -*-

"""
The base classes for the the wntr.reaction module.
Other than the enum classes, the classes in this module are all abstract 
and/or mixin classes, and should not be instantiated directly.
"""

import abc
import enum
import logging
from abc import ABC, abstractmethod, abstractproperty
from collections.abc import MutableMapping
from dataclasses import InitVar, dataclass
from enum import Enum, IntFlag
from typing import (
    Any,
    ClassVar,
    Dict,
    Generator,
    Hashable,
    ItemsView,
    Iterator,
    KeysView,
    List,
    Set,
    Tuple,
    Union,
    ValuesView,
)

has_sympy = False
try:
    from sympy import Float, Symbol, init_printing, symbols
    from sympy.parsing import parse_expr
    from sympy.parsing.sympy_parser import convert_xor, standard_transformations

    has_sympy = True
except ImportError:
    sympy = None
    logging.critical("This python installation does not have SymPy installed. Certain functionality will be disabled.")
    standard_transformations = (None,)
    convert_xor = None
    has_sympy = False

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
"""The hydraulic variables defined in EPANET-MSX"""

RESERVED_NAMES = tuple([v["name"] for v in HYDRAULIC_VARIABLES])
"""The MSX reserved names as a tuple"""

SYMPY_RESERVED = ("E", "I", "pi")
"""Some extra names reserved by sympy"""

EXPR_TRANSFORMS = standard_transformations + (convert_xor,)
"""The sympy transforms to use in expression parsing"""


class KeyInOtherGroupError(KeyError):
    """The key exists but is in a different disjoint group"""

    pass


class VariableNameExistsError(KeyError):
    """The name already exists in the reaction model"""

    pass


class RxnVariableType(Enum):
    """The type of reaction variable.

    The following types are defined, and aliases of just the first character
    are also defined.

    .. rubric:: Valid Values

    .. autosummary::

        BULK
        WALL
        CONSTANT
        PARAMETER
        TERM
        INTERNAL

    .. rubric:: Class methods

    .. autosummary::

        factory

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
    """An internal variable - see :attr:`~wntr.reaction.base.RESERVED_NAMES`"""

    B = BULK
    """Alias for :attr:`BULK`"""
    W = WALL
    """Alias for :attr:`WALL`"""
    C = CONSTANT
    """Alias for :attr:`CONSTANT`"""
    P = PARAMETER
    """Alias for :attr:`PARAMETER`"""
    T = TERM
    """Alias for :attr:`TERM`"""
    I = INTERNAL
    """Alias for :attr:`INTERNAL`"""
    CONST = CONSTANT
    """Alias for :attr:`CONSTANT`"""
    PARAM = PARAMETER
    """Alias for :attr:`PARAMETER`"""

    @classmethod
    def factory(cls, value: Union[str, int, "RxnVariableType"]) -> "RxnVariableType":
        """Convert a value to a valid RxnVariableType.

        Parameters
        ----------
        value : str or int or RxnVariableType
            the value to change

        Returns
        -------
        RxnVariableType
            the equivalent variable type enum

        Raises
        ------
        KeyError
            the value is unknown/undefined
        TypeError
            the type of the value is wrong
        """
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


class RxnLocationType(Enum):
    """What type of network component does this reaction occur in

    The following types are defined, and aliases of just the first character
    are also defined.


    .. rubric:: Valid values

    .. autosummary::

        PIPE
        TANK

    .. rubric:: Class methods

    .. autosummary::

        factory

    """

    PIPE = 1
    """The expression describes a reaction in pipes"""
    TANK = 2
    """The expression describes a reaction in tanks"""
    P = PIPE
    """Alias for :attr:`PIPE`"""
    T = TANK
    """Alias for :attr:`TANK`"""

    @classmethod
    def factory(cls, value: Union[str, int, "RxnLocationType"]) -> "RxnLocationType":
        """Convert a value to a valid RxnLocationType.

        Parameters
        ----------
        value : str or int or RxnLocationType
            the value to process

        Returns
        -------
        RxnLocationType
            the equivalent enum object

        Raises
        ------
        KeyError
            the value is unknown/undefined
        TypeError
            the type of the value is wrong
        """
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


class RxnDynamicsType(Enum):
    """The type of reaction expression.

    The following types are defined, and aliases of just the first character
    are also defined.

    .. rubric:: Valid values

    .. autosummary::

        EQUIL
        RATE
        FORMULA

    .. rubric:: Class methods

    .. autosummary::

        factory

    """

    EQUIL = 1
    """used for equilibrium expressions where it is assumed that the expression supplied is being equated to zero"""
    RATE = 2
    """used to supply the equation that expresses the rate of change of the given species with respect to time as a function of the other species in the model"""
    FORMULA = 3
    """used when the concentration of the named species is a simple function of the remaining species"""
    E = EQUIL
    """Alias for :attr:`EQUIL`"""
    R = RATE
    """Alias for :attr:`RATE`"""
    F = FORMULA
    """Alias for :attr:`FORMULA`"""

    @classmethod
    def factory(cls, value: Union[str, int, "RxnDynamicsType"]) -> "RxnDynamicsType":
        """Convert a value to a RxnDynamicsType.

        Parameters
        ----------
        value : str or int or RxnDynamicsType
            the value to convert

        Returns
        -------
        RxnDynamicsType
            the enum value

        Raises
        ------
        KeyError
            the value is unknown/undefined
        TypeError
            the type of the value is wrong
        """
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
class RxnVariable(ABC):
    """The base for a reaction variable.

    Parameters
    ----------
    name : str
        the name/symbol of the variable
    """

    name: str
    """The name (symbol) for the variable, must be a valid MSX name"""

    def __str__(self) -> str:
        """Returns the name of the variable"""
        return self.name

    def __hash__(self) -> int:
        """Makes the variable hashable by hashing the `str` representation"""
        return hash(str(self))

    @abstractproperty
    def var_type(self) -> RxnVariableType:
        """The variable type."""
        raise NotImplementedError

    def is_species(self) -> bool:
        """Check to see if this variable represents a species (bulk or wall).

        Returns
        -------
        bool
            True if this is a species object, False otherwise
        """
        return self.var_type == RxnVariableType.BULK or self.var_type == RxnVariableType.WALL
    
    def is_coeff(self) -> bool:
        """Check to see if this variable represents a coefficient (constant or parameter).

        Returns
        -------
        bool
            True if this is a coefficient object, False otherwise
        """
        return self.var_type == RxnVariableType.CONST or self.var_type == RxnVariableType.PARAM
    
    def is_term_function(self) -> bool:
        """Check to see if this variable represents a function (MSX term).

        Returns
        -------
        bool
            True if this is a term/function object, False otherwise
        """
        return self.var_type == RxnVariableType.TERM

    @property
    def symbol(self):
        """Representation of the variable's name as a sympy.Symbol"""
        return Symbol(self.name)


@dataclass
class RxnReaction(ABC):
    """The base for a reaction.

    Parameters
    ----------
    species : str
        the name of the species whose reaction dynamics is being described
    location : RxnLocationType or str
        the location the reaction occurs (pipes or tanks)
    expression : str
        the expression for the reaction dynamics (right-hand-side)
    """

    species: str
    """The name of the species that this reaction describes"""
    location: RxnLocationType
    """The location this reaction occurs (pipes vs tanks)"""
    expression: str
    """The expression for the reaction dynamics (or, the right-hand-side of the equation)"""

    def __str__(self) -> str:
        """Names the reaction with the format `species-dot-location` (for example, ``PB2.pipe``)"""
        return self.to_key(self.species, self.location)

    def __hash__(self) -> int:
        """Makes the reaction hashable by hashing the `str` representation"""
        return hash(str(self))

    @abstractproperty
    def expr_type(self) -> RxnDynamicsType:
        """The type of reaction dynamics being described (or, the left-hand-side of the equation)"""
        raise NotImplementedError

    @classmethod
    def to_key(cls, species, location):
        """Generate a dictionary key (equivalent to the ``str`` casting of a reaction)
        without having the object itself.

        Parameters
        ----------
        species : str
            the species for the reaction
        location : RxnLocationType or str
            the location of the reaction

        Returns
        -------
        str
            a species/location unique name
        """
        location = RxnLocationType.factory(location)
        return str(species) + "." + location.name.lower()


class RxnModelRegistry(ABC):
    @abstractmethod
    def variables(self, var_type=None):
        """Generator over all defined variables, optionally limited by variable type"""
        raise NotImplementedError

    @abstractmethod
    def add_variable(self, __variable: RxnVariable):
        """Add a variable *object* to the model"""
        raise NotImplementedError

    @abstractmethod
    def get_variable(self, name: str) -> RxnVariable:
        """Get a specific variable by name"""
        raise NotImplementedError

    @abstractmethod
    def remove_variable(self, name: str):
        """Delete a specified variable from the model"""
        raise NotImplementedError

    @abstractmethod
    def reactions(self, location=None):
        """Generator over all defined reactions, optionally limited by reaction location"""
        raise NotImplementedError

    @abstractmethod
    def add_reaction(self, __reaction: RxnReaction):
        """Add a reaction *object* to the model"""
        raise NotImplementedError

    @abstractmethod
    def get_reaction(self, species, location=None) -> List[RxnReaction]:
        """Get reaction(s) for a species, optionally only for one location"""
        raise NotImplementedError

    @abstractmethod
    def remove_reaction(self, species, location=None):
        """Remove reaction(s) for a species, optionally only for one location"""
        raise NotImplementedError


class LinkedVariablesMixin:

    __variable_registry = None

    @property
    def _variable_registry(self) -> RxnModelRegistry:
        return self.__variable_registry

    @_variable_registry.setter
    def _variable_registry(self, value):
        if value is not None and not isinstance(value, RxnModelRegistry):
            raise TypeError("Linked model must be a RxnModelRegistry, got {}".format(type(value)))
        self.__variable_registry = value

    def validate(self):
        """Validate that this object is a member of the RxnModelRegistry

        Raises
        ------
        TypeError
            if the model registry isn't linked
        """
        if not isinstance(self._variable_registry, RxnModelRegistry):
            raise TypeError("This object is not connected to any RxnModelRegistry")


@dataclass
class ExpressionMixin(ABC):
    """A mixin class for converting an expression to a sympy Expr"""

    @abstractmethod
    def to_symbolic(self, transformations=EXPR_TRANSFORMS):
        """Convert to a symbolic expression.

        Parameters
        ----------
        transformations : tuple of sympy transformations
            transformations to apply to the expression, by default EXPR_TRANSFORMS

        Returns
        -------
        sympy.Expr
            the expression parsed by sympy
        """
        return parse_expr(self.expression, transformations=transformations)


class MSXObject:
    def to_msx_string(self) -> str:
        """Get the expression as an EPANET-MSX input-file style string.

        Returns
        -------
        str
            the expression for use in an EPANET-MSX input file
        """
        raise NotImplementedError
