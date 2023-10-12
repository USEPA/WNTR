# -*- coding: utf-8 -*-

"""The base classes for the the WNTR quality extensions module.
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
from typing import Any, ClassVar, Dict, Generator, List, Union

import numpy as np

from wntr.network.base import AbstractModel
from wntr.network.model import WaterNetworkModel
from wntr.network.elements import Pattern
from wntr.quality.options import MultispeciesOptions
from wntr.utils.enumtools import add_get
from wntr.utils.ordered_set import OrderedSet

has_sympy = False
try:
    from sympy import Float, Symbol, init_printing, symbols, Function, Mul, Add, Pow, Integer
    from sympy.functions import cos, sin, tan, cot, Abs, sign, sqrt, log, exp, asin, acos, atan, acot, sinh, cosh, tanh, coth, Heaviside
    from sympy.parsing import parse_expr
    from sympy.parsing.sympy_parser import convert_xor, standard_transformations, auto_number, auto_symbol
    class _log10(Function):
        @classmethod
        def eval(cls, x):
            return log(x, 10)
    has_sympy = True
except ImportError:
    sympy = None
    has_sympy = False
    logging.critical("This python installation does not have SymPy installed. Certain functionality will be disabled.")
    standard_transformations = (None,)
    convert_xor = None
    if not has_sympy:
        from numpy import cos, sin, tan, abs, sign, sqrt, log, exp, arcsin, arccos, arctan, sinh, cosh, tanh, heaviside, log10
        cot = lambda x : 1 / tan(x)
        Abs = abs
        asin = arcsin
        acos = arccos
        atan = arctan
        acot = lambda x : 1 / arctan(1 / x)
        coth = lambda x : 1 / tanh(x)
        Heaviside = heaviside
        _log10 = log10

logger = logging.getLogger(__name__)

HYDRAULIC_VARIABLES = [
    {"name": "D", "note": "pipe diameter (feet or meters) "},
    {
        "name": "Kc",
        "note": "pipe roughness coefficient (unitless for Hazen-Williams or Chezy-Manning head loss formulas, millifeet or millimeters for Darcy-Weisbach head loss formula)",
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
For reference, the valid values are provided in :numref:`table-msx-hyd-vars`.

.. _table-msx-hyd-vars:
.. table:: Valid hydraulic variables in multispecies quality model expressions.

    ============== ================================================
    **Name**       **Description**
    -------------- ------------------------------------------------
    ``D``          pipe diameter
    ``Kc``         pipe roughness coefficient
    ``Q``          pipe flow rate
    ``Re``         flow Reynolds number
    ``Us``         pipe shear velocity
    ``Ff``         Darcy-Weisbach friction factor
    ``Av``         pipe surface area per unit volume
    ``Len``        pipe length
    ============== ================================================

:meta hide-value:
"""

EXPR_FUNCTIONS = dict(
    abs=abs,
    sgn=sign,
    sqrt=sqrt,
    step=Heaviside,
    log=log,
    exp=exp,
    sin=sin,
    cos=cos,
    tan=tan,
    cot=cot,
    asin=asin,
    acos=acos,
    atan=atan,
    acot=acot,
    sinh=sinh,
    cosh=cosh,
    tanh=tanh,
    coth=coth,
    log10=_log10,
)
"""Mathematical functions available for use in expressions. See 
:numref:`table-msx-funcs` for a list and description of the 
different functions recognized. These names, case insensitive, are 
considered invalid when naming variables.

Additionally, the following SymPy names - ``Mul``, ``Add``, ``Pow``, 
``Integer``, ``Float`` - are used to convert numbers and symbolic 
functions; therefore, these five words, case sensitive, are also invalid
for use as variable names.

.. _table-msx-funcs:
.. table:: Functions defined for use in EPANET-MSX expressions.

    ============== ================================================================
    **Name**       **Description**
    -------------- ----------------------------------------------------------------
    ``abs``        absolute value (:func:`~sympy.functions.Abs`)
    ``sgn``        sign (:func:`~sympy.functions.sign`)
    ``sqrt``       square-root
    ``step``       step function (:func:`~sympy.functions.Heaviside`)
    ``exp``        natural number, `e`, raised to a power
    ``log``        natural logarithm
    ``log10``      base-10 logarithm (defined as internal function)
    ``sin``        sine
    ``cos``        cosine
    ``tan``        tangent
    ``cot``        cotangent
    ``asin``       arcsine
    ``acos``       arccosine
    ``atan``       arctangent
    ``acot``       arccotangent
    ``sinh``       hyperbolic sine
    ``cosh``       hyperbolic cosine
    ``tanh``       hyperbolic tangent
    ``coth``       hyperbolic cotangent
    ``*``          multiplication (:func:`~sympy.Mul`)
    ``/``          division (:func:`~sympy.Mul`)
    ``+``          addition (:func:`~sympy.Add`)
    ``-``          negation and subtraction (:func:`~sympy.Add`)
    ``^``          power/exponents (:func:`~sympy.Pow`)
    ``(``, ``)``   groupings and function parameters
    `numbers`      literal values (:func:`~sympy.Float` and :func:`~sympy.Integer`)
    ============== ================================================================

:meta hide-value:
"""

RESERVED_NAMES = (
    tuple([v["name"] for v in HYDRAULIC_VARIABLES])
    + tuple([k for k, v in EXPR_FUNCTIONS.items()])
    + tuple([k.upper() for k, v in EXPR_FUNCTIONS.items()])
    + tuple([k.capitalize() for k, v in EXPR_FUNCTIONS.items()])
    + ('Mul', 'Add', 'Pow', 'Integer', 'Float')
)
"""The WNTR reserved names. This includes the MSX hydraulic variables
(see :numref:`table-msx-hyd-vars`) and the MSX defined functions 
(see :numref:`table-msx-funcs`).

:meta hide-value:
"""

_global_dict = dict()
for k, v in EXPR_FUNCTIONS.items():
    _global_dict[k] = v
    _global_dict[k.lower()] = v
    _global_dict[k.capitalize()] = v
    _global_dict[k.upper()] = v
for v in HYDRAULIC_VARIABLES:
    _global_dict[v["name"]] = symbols(v["name"])
_global_dict['Mul'] = Mul
_global_dict['Add'] = Add
_global_dict['Pow'] = Pow
_global_dict['Integer'] = Integer
_global_dict['Float'] = Float

EXPR_TRANSFORMS = (
    auto_symbol,
    auto_number,
    convert_xor,
)
"""The sympy transforms to use in expression parsing. See 
:numref:`table-sympy-transformations` for the list of transformations.

.. _table-sympy-transformations:
.. table:: Transformations used by WNTR when parsing expressions using SymPy.

    ========================================== ==================
    **Transformation**                         **Is used?**
    ------------------------------------------ ------------------
    ``lambda_notation``                        No
    ``auto_symbol``                            Yes
    ``repeated_decimals``                      No
    ``auto_number``                            Yes
    ``factorial_notation``                     No
    ``implicit_multiplication_application``    No
    ``convert_xor``                            Yes
    ``implicit_application``                   No
    ``implicit_multiplication``                No
    ``convert_equals_signs``                   No
    ``function_exponentiation``                No
    ``rationalize``                            No
    ========================================== ==================

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
    EXTERNAL = 32
    """An internal variable - see :attr:`~wntr.reaction.base.RESERVED_NAMES`"""

    B = BULK
    W = WALL
    C = CONSTANT
    P = PARAMETER
    T = TERM
    E = EXTERNAL

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


class AbstractVariable(ABC):
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


class AbstractReaction(ABC):
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
    def to_symbolic(self, transformations: tuple = EXPR_TRANSFORMS):
        """Convert to a symbolic expression.

        Parameters
        ----------
        transformations : tuple of sympy transformations
            transformations to apply to the expression, by default :data:`EXPR_TRANSFORMS`

        Returns
        -------
        sympy.Expr or sympy.Symbol
            the expression parsed by sympy
        """
        if not has_sympy:
            return self.expression
        return parse_expr(self.expression, local_dict=self._variable_registry.variable_dict() if self._variable_registry is not None else None, transformations=transformations, global_dict=_global_dict, evaluate=False)


class AbstractQualityModel(ABC):
    """Abstract methods any water quality model should include."""

    @abstractmethod
    def variables(self, var_type=None):
        """Generator over all defined variables, optionally limited by variable type"""
        raise NotImplementedError

    @abstractmethod
    def variable_dict(self) -> Dict[str, Any]:
        """Create a dictionary of variable names and their sympy represenations"""
        raise NotImplementedError

    @abstractmethod
    def add_variable(self, __variable: AbstractVariable):
        """Add a variable *object* to the model"""
        raise NotImplementedError

    @abstractmethod
    def get_variable(self, name: str) -> AbstractVariable:
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
    def add_reaction(self, __reaction: AbstractReaction):
        """Add a reaction *object* to the model"""
        raise NotImplementedError

    @abstractmethod
    def get_reaction(self, species, location=None) -> List[AbstractReaction]:
        """Get reaction(s) for a species, optionally only for one location"""
        raise NotImplementedError

    @abstractmethod
    def remove_reaction(self, species, location=None):
        """Remove reaction(s) for a species, optionally only for one location"""
        raise NotImplementedError
