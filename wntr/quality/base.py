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
from typing import ClassVar, Generator, List, Union

import numpy as np

from wntr.network.base import AbstractModel
from wntr.network.model import WaterNetworkModel
from wntr.network.elements import Pattern
from wntr.quality.options import MultispeciesOptions
from wntr.utils.enumtools import add_get
from wntr.utils.ordered_set import OrderedSet

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
"""The hydraulic variables defined in EPANET-MSX.

:meta hide-value:
"""

RESERVED_NAMES = tuple([v["name"] for v in HYDRAULIC_VARIABLES])
"""The MSX reserved names."""

SYMPY_RESERVED = ("E", "I", "pi")
"""Some extra names reserved by sympy"""

EXPR_TRANSFORMS = standard_transformations + (convert_xor,)
"""The sympy transforms to use in expression parsing.

:meta hide-value:
"""


@add_get(abbrev=True)
class VariableType(Enum):
    """The type of reaction variable.

    The following types are defined, and aliases of just the first character
    are also defined.

    .. rubric:: Enum Members
    .. autosummary::
        BULK
        WALL
        CONSTANT
        PARAMETER
        TERM
        INTERNAL

    .. rubric:: Class Methods
    .. autosummary::
        :nosignatures:

        get

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
    W = WALL
    C = CONSTANT
    P = PARAMETER
    T = TERM
    I = INTERNAL

    CONST = CONSTANT
    PARAM = PARAMETER
    

@add_get(abbrev=True)
class LocationType(Enum):
    """What type of network component does this reaction occur in

    The following types are defined, and aliases of just the first character
    are also defined.

    .. rubric:: Enum Members
    .. autosummary::
        PIPE
        TANK

    .. rubric:: Class Methods
    .. autosummary::
        :nosignatures:
    
        get
    """

    PIPE = 1
    """The expression describes a reaction in pipes"""
    TANK = 2
    """The expression describes a reaction in tanks"""

    P = PIPE
    T = TANK


@add_get(abbrev=True)
class DynamicsType(Enum):
    """The type of reaction expression.

    The following types are defined, and aliases of just the first character
    are also defined.

    .. rubric:: Enum Members
    .. autosummary::
        EQUIL
        RATE
        FORMULA

    .. rubric:: Class Methods
    .. autosummary::
        :nosignatures:
        
        get

    """

    EQUIL = 1
    """used for equilibrium expressions where it is assumed that the expression supplied is being equated to zero"""
    RATE = 2
    """used to supply the equation that expresses the rate of change of the given species with respect to time as a function of the other species in the model"""
    FORMULA = 3
    """used when the concentration of the named species is a simple function of the remaining species"""

    E = EQUIL
    R = RATE
    F = FORMULA


class ReactionVariable(ABC):
    """The base for a reaction variable.

    Attributes
    ----------
    name : str
        The name (symbol) for the variable, must be a valid MSX name
    """

    def __str__(self) -> str:
        """Returns the name of the variable"""
        return self.name

    def __hash__(self) -> int:
        return hash(str(self))

    __variable_registry = None

    @property
    def _variable_registry(self) -> "AbstractQualityModel":
        return self.__variable_registry

    @_variable_registry.setter
    def _variable_registry(self, value):
        if value is not None and not isinstance(value, AbstractQualityModel):
            raise TypeError("Linked model must be a RxnModelRegistry, got {}".format(type(value)))
        self.__variable_registry = value

    def validate(self):
        """Validate that this object is a member of the RxnModelRegistry

        Raises
        ------
        TypeError
            if the model registry isn't linked
        """
        if not isinstance(self._variable_registry, AbstractQualityModel):
            raise TypeError("This object is not connected to any RxnModelRegistry")

    @abstractproperty
    def var_type(self) -> VariableType:
        """The variable type."""
        raise NotImplementedError

    def is_species(self) -> bool:
        """Check to see if this variable represents a species (bulk or wall).

        Returns
        -------
        bool
            True if this is a species object, False otherwise
        """
        return self.var_type == VariableType.BULK or self.var_type == VariableType.WALL

    def is_coeff(self) -> bool:
        """Check to see if this variable represents a coefficient (constant or parameter).

        Returns
        -------
        bool
            True if this is a coefficient object, False otherwise
        """
        return self.var_type == VariableType.CONST or self.var_type == VariableType.PARAM

    def is_other_term(self) -> bool:
        """Check to see if this variable represents a function (MSX term).

        Returns
        -------
        bool
            True if this is a term/function object, False otherwise
        """
        return self.var_type == VariableType.TERM

    @property
    def symbol(self):
        """Representation of the variable's name as a sympy.Symbol"""
        return Symbol(self.name)

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
        return self.symbol


class ReactionDynamics(ABC):
    """The base for a reaction.

    Attributes
    ----------
    species : str
        the name of the species whose reaction dynamics is being described
    location : RxnLocationType or str
        the location the reaction occurs (pipes or tanks)
    expression : str
        the expression for the reaction dynamics (right-hand-side)
    """

    def __str__(self) -> str:
        """Names the reaction with the format `species-dot-location` (for example, ``PB2.pipe``)"""
        return self.to_key(self.species, self.location)

    def __hash__(self) -> int:
        """Makes the reaction hashable by hashing the `str` representation"""
        return hash(str(self))

    __variable_registry = None

    @property
    def _variable_registry(self) -> "AbstractQualityModel":
        return self.__variable_registry

    @_variable_registry.setter
    def _variable_registry(self, value):
        if value is not None and not isinstance(value, AbstractQualityModel):
            raise TypeError("Linked model must be a RxnModelRegistry, got {}".format(type(value)))
        self.__variable_registry = value

    def validate(self):
        """Validate that this object is a member of the RxnModelRegistry

        Raises
        ------
        TypeError
            if the model registry isn't linked
        """
        if not isinstance(self._variable_registry, AbstractQualityModel):
            raise TypeError("This object is not connected to any RxnModelRegistry")

    @abstractproperty
    def expr_type(self) -> DynamicsType:
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
        location = LocationType.get(location)
        return str(species) + "." + location.name.lower()

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


class AbstractQualityModel(ABC):
    """Abstract methods any water quality model should include."""

    @abstractmethod
    def variables(self, var_type=None):
        """Generator over all defined variables, optionally limited by variable type"""
        raise NotImplementedError

    @abstractmethod
    def add_variable(self, __variable: ReactionVariable):
        """Add a variable *object* to the model"""
        raise NotImplementedError

    @abstractmethod
    def get_variable(self, name: str) -> ReactionVariable:
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
    def add_reaction(self, __reaction: ReactionDynamics):
        """Add a reaction *object* to the model"""
        raise NotImplementedError

    @abstractmethod
    def get_reaction(self, species, location=None) -> List[ReactionDynamics]:
        """Get reaction(s) for a species, optionally only for one location"""
        raise NotImplementedError

    @abstractmethod
    def remove_reaction(self, species, location=None):
        """Remove reaction(s) for a species, optionally only for one location"""
        raise NotImplementedError
