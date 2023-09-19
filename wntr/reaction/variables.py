# -*- coding: utf-8 -*-

"""
Classes for variables used in reaction dynamics definitions.
Defines species (chemical or biological), coefficients for equations,
"term-functions", i.e., named functions that are called "terms" in 
EPANET-MSX, and internal variables, such as hydraulic variables.

The classes in this module can be created directly. However, they are more
powerful when either, a) created using API calls on a :class:`~wntr.reaction.model.WaterNetworkModel`,
or, b) linked to a :class:`~wntr.reaction.model.WaterNetworkModel` model object after creation.
This allows for variables to be validated against other variables in the model, 
avoiding naming conflicts and checking that terms used in a term-function have
been defined.

If :class:`sympy` is installed, then there are functions available
that will convert object instances of these classes into sympy expressions
and symbols. If the instances are linked to a model, then expressions can 
be expanded, validated, and even evaluated or simplified symbolically.

.. rubric:: Contents

.. autosummary::

    Species
    BulkSpecies
    WallSpecies
    Coefficient
    Constant
    Parameter
    OtherTerm
    InternalVariable

"""

import enum
import logging
import warnings
from dataclasses import InitVar, asdict, dataclass, field
from enum import Enum, IntFlag
from typing import Any, ClassVar, Dict, List, Set, Tuple, Union
from .base import MSXComment

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
from wntr.reaction.base import EXPR_TRANSFORMS

from .base import (
    RESERVED_NAMES,
    ExpressionMixin,
    LinkedVariablesMixin,
    MsxObjectMixin,
    AbstractReactionModel,
    ReactionVariable,
    VariableType,
)

logger = logging.getLogger(__name__)


@dataclass(repr=False)
class Species(MsxObjectMixin, LinkedVariablesMixin, ReactionVariable):

    units: str
    """The unit used for this species"""
    atol: InitVar[float] = None
    """The absolute tolerance to use when solving for this species, by default None"""
    rtol: InitVar[float] = None
    """The relative tolerance to use when solving for this species, by default None"""
    note: Union[str, Dict[str, str]] = None
    """A note about this species, by default None"""
    diffusivity: float = None
    """The diffusivity value for this species, by default None"""
    variable_registry: InitVar[AbstractReactionModel] = None

    def __post_init__(self, atol=None, rtol=None, reaction_model=None):
        if isinstance(atol, property):
            atol = None
        elif atol is not None:
            atol = float(atol)
        if isinstance(rtol, property):
            rtol = None
        elif rtol is not None:
            rtol = float(rtol)
        if self.name in RESERVED_NAMES:
            raise ValueError("Name cannot be a reserved name")
        if (atol is None) ^ (rtol is None):
            raise TypeError("atol and rtol must be the same type, got {} and {}".format(atol, rtol))
        self._atol = atol
        self._rtol = rtol
        self._variable_registry = reaction_model

    def __repr__(self):
        return "{}(name={}, unit={}, atol={}, rtol={}, note={})".format(self.__class__.__name__, repr(self.name), repr(self.units), self._atol, self._rtol, repr(self.note))

    def get_tolerances(self) -> Tuple[float, float]:
        """Get the species-specific solver tolerances.

        Returns
        -------
        two-tuple or None
            the absolute and relative tolerances, or None if the global values should be used
        """
        if self._atol is not None and self._rtol is not None:
            return (self._atol, self._rtol)
        return None

    def set_tolerances(self, absolute: float, relative: float):
        """Set the species-specific solver tolerances. Using ``None`` for both will
        clear the tolerances, though using :func:`clear_tolerances` is clearer code.

        Parameters
        ----------
        absolute : float
            the absolute solver tolerance
        relative : float
            the relative solver tolerance

        Raises
        ------
        TypeError
            if both absolute and relative are not the same type
        ValueError
            if either value is less-than-or-equal-to zero
        """
        if absolute is None and relative is None:
            self._atol = self._rtol = None
            return
        try:
            if not isinstance(absolute, float):
                absolute = float(absolute)
            if not isinstance(relative, float):
                relative = float(relative)
        except Exception as e:
            raise TypeError("absolute and relative must be the same type, got {} and {}".format(absolute, relative))
        if absolute <= 0:
            raise ValueError("Absolute tolerance must be greater than 0")
        if relative <= 0:
            raise ValueError("Relative tolerance must be greater than 0")
        self._atol = absolute
        self._rtol = relative

    def clear_tolerances(self):
        """Resets both tolerances to ``None`` to use the global values."""
        self._atol = self._rtol = None

    def to_msx_string(self) -> str:
        tols = self.get_tolerances()
        if tols is None:
            tolstr = ""
        else:
            tolstr = " {:12.6g} {:12.6g}".format(*tols)
        return "{:<12s} {:<8s} {:<8s}{:s}".format(
            self.var_type.name.upper(),
            self.name,
            self.units,
            tolstr,
        )

    def to_dict(self):
        rep = dict(name=self.name, unist=self.units)
        tols = self.get_tolerances()
        if tols is not None:
            rep['atol'] = tols[0]
            rep['rtol'] = tols[1]
        rep['diffusivity'] = self.diffusivity
        if isinstance(self.note, str):
            rep['note'] = self.note
        elif isinstance(self.note, MSXComment):
            rep['note'] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep['note'] = None
        return rep


@dataclass(repr=False)
class BulkSpecies(Species):
    @property
    def var_type(self) -> VariableType:
        return VariableType.BULK


@dataclass(repr=False)
class WallSpecies(Species):
    @property
    def var_type(self) -> VariableType:
        return VariableType.WALL


@dataclass(repr=False)
class Coefficient(MsxObjectMixin, LinkedVariablesMixin, ReactionVariable):

    global_value: float
    note: Union[str, Dict[str, str]] = None
    units: str = None
    variable_registry: InitVar[AbstractReactionModel] = None

    def __post_init__(self, reaction_model):
        if self.name in RESERVED_NAMES:
            raise ValueError("Name cannot be a reserved name")
        self.global_value = float(self.global_value)
        self._variable_registry = reaction_model

    def __repr__(self):
        return "{}(name={}, global_value={}, units={}, note={})".format(self.__class__.__name__, repr(self.name), repr(self.global_value), repr(self.units), repr(self.note))

    def get_value(self) -> float:
        return self.global_value

    def to_msx_string(self) -> str:
        # if self.units is not None:
        #     post = r' ; {"units"="' + str(self.units) + r'"}'
        # else:
        post = ''
        return "{:<12s} {:<8s} {:<16s}{}".format(
            self.var_type.name.upper(),
            self.name,
            str(self.global_value),
            post
        )

    def to_dict(self):
        rep = dict(name=self.name, global_value=self.global_value, units=self.units)
        if isinstance(self.note, str):
            rep['note'] = self.note
        elif isinstance(self.note, MSXComment):
            rep['note'] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep['note'] = None
        return rep


@dataclass(repr=False)
class Constant(Coefficient):
    @property
    def var_type(self) -> VariableType:
        return VariableType.CONST


@dataclass(repr=False)
class Parameter(Coefficient):

    _pipe_values: Dict[str, float] = field(default_factory=dict)
    """A dictionary of parameter values for various pipes"""
    _tank_values: Dict[str, float] = field(default_factory=dict)
    """A dictionary of parameter values for various tanks"""

    def __post_init__(self, reaction_model):
        super().__post_init__(reaction_model)
        if self._pipe_values is None:
            self._pipe_values = dict()
        if self._tank_values is None:
            self._tank_values = dict()

    @property
    def var_type(self) -> VariableType:
        return VariableType.PARAM

    def get_value(self, pipe: str = None, tank: str = None) -> float:
        if pipe is not None and tank is not None:
            raise TypeError("Cannot get a value for a pipe and tank at the same time - one or both must be None")
        if pipe is not None:
            return self._pipe_values.get(pipe, self.global_value)
        if tank is not None:
            return self._tank_values.get(tank, self.global_value)
        return self.global_value

    @property
    def pipe_values(self) -> Dict[str, float]:
        return self._pipe_values

    @property
    def tank_values(self) -> Dict[str, float]:
        return self._tank_values
    
    def to_dict(self):
        rep = super().to_dict()
        rep['pipe_values'] = self._pipe_values.copy()
        rep['tank_values'] = self._tank_values.copy()
        return rep


@dataclass(repr=False)
class OtherTerm(MsxObjectMixin, LinkedVariablesMixin, ExpressionMixin, ReactionVariable):
    """A function definition used as a shortcut in reaction expressions (called a 'term' in EPANET-MSX)

    Parameters
    ----------
    name : str
        the name/symbol of the function (term)
    expression : str
        the mathematical expression described by this function
    note : str, optional
        a note for this function, by default None
    variable_registry : RxnModelRegistry
        the reaction model this function is a part of
    """

    expression: str
    """The expression this named-function is equivalent to"""
    note: Union[str, Dict[str, str]] = None
    """A note about this function/term"""
    variable_registry: InitVar[AbstractReactionModel] = field(default=None, compare=False)

    def __post_init__(self, reaction_model):
        if self.name in RESERVED_NAMES:
            raise ValueError("Name cannot be a reserved name")
        self._variable_registry = reaction_model

    def __repr__(self):
        return "{}(name={}, expression={}, note={})".format(self.__class__.__name__, repr(self.name), repr(self.expression), repr(self.note))

    @property
    def var_type(self) -> VariableType:
        return VariableType.TERM

    def to_msx_string(self) -> str:
        return "{:<8s} {:<64s}".format(self.name, self.expression)

    def to_symbolic(self, transformations=...):
        return super().to_symbolic(transformations)

    def to_dict(self):
        rep = dict(name=self.name, expression=self.expression)
        if isinstance(self.note, str):
            rep['note'] = self.note
        elif isinstance(self.note, MSXComment):
            rep['note'] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep['note'] = None
        return rep


@dataclass(repr=False)
class InternalVariable(ReactionVariable):
    """A hydraulic variable or a placeholder for a built-in reserved word.

    For example, "Len" is the EPANET-MSX name for the length of a pipe, and "I" is a sympy
    reserved symbol for the imaginary number."""

    note: str = "internal variable - not output to MSX"
    units: str = None

    def __repr__(self):
        return "{}(name={}, note={}, units={})".format(self.__class__.__name__, repr(self.name), repr(self.note), repr(self.units))

    @property
    def var_type(self) -> VariableType:
        return VariableType.INTERNAL
