# -*- coding: utf-8 -*-
"""
Multispecies water quality model and elements.

This module contains concrete instantiations of the abstract classes described in :class:`wntr.quality.base`.
"""

import enum
import logging
import warnings
from collections.abc import MutableMapping
from dataclasses import InitVar, asdict, dataclass, field
from enum import Enum, IntFlag
from typing import (
    Any,
    ClassVar,
    Dict,
    Generator,
    Hashable,
    Iterator,
    List,
    Literal,
    Set,
    Tuple,
    Union,
)

import wntr.quality.io
from wntr.epanet.util import ENcomment
from wntr.network.elements import Source
from wntr.network.model import PatternRegistry, SourceRegistry, WaterNetworkModel
from wntr.utils.citations import Citation
from wntr.utils.disjoint_mapping import DisjointMapping, KeyExistsError

from .base import (
    EXPR_TRANSFORMS,
    HYDRAULIC_VARIABLES,
    RESERVED_NAMES,
    EXPR_FUNCTIONS,
    AbstractQualityModel,
    DynamicsType,
    LocationType,
    ReactionDynamics,
    ReactionVariable,
    VariableType,
)
from .options import MultispeciesOptions

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


class Species(ReactionVariable):
    """A species in a multispecies water quality model.

    .. rubric:: Constructor

    The preferred way to create a new species is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_bulk_species()`,
    :meth:`~MultispeciesQualityModel.add_wall_species()`,
    :meth:`~MultispeciesQualityModel.add_species()`, or
    :meth:`~MultispeciesQualityModel.add_variable()`.
    """

    name: str = None
    """The name (symbol) for the variable, must be a valid MSX name"""
    units: str = None
    """The units used for concentration of this species"""
    note: Union[str, Dict[str, str]] = None
    """A note to go with this species"""
    diffusivity: float = None
    """A value for diffusivity for this species"""
    initial_quality: float = None
    """Global initial quality for this species"""

    def __init__(
        self,
        name: str,
        units: str,
        atol: float = None,
        rtol: float = None,
        note: Union[str, Dict[str, str]] = None,
        diffusivity: float = None,
        initial_quality: float = None,
        *,
        _qm: AbstractQualityModel = None,
    ):
        """
        Parameters
        ----------
        name : str
            The name (symbol) for the variable, must be a valid MSX name
        units : str
            The units used for this species
        atol : float, optional
            The absolute tolerance to use when solving for this species, by default None
        rtol : float, optional
            The relative tolerance to use when solving for this species, by default None
        note : str or dict, optional
            A note about this species, by default None
        diffusivity : float, optional
            The diffusivity value for this species, by default None
        initial_quality: float, optional
            The global initial quality for this species, by default None

        Other Parameters
        ----------------
        _qm : MultispeciesQualityModel
            the model to link with, populated automatically if the :class:`MultispeciesQualityModel` API is used, by default None
        """
        if name in RESERVED_NAMES:
            raise ValueError("Name cannot be a reserved name")
        self.name: str = name
        """The name of the variable"""
        self.units: str = units
        """The units used for this species"""
        self.note = note
        """A note about this species, by default None"""
        self.diffusivity: float = diffusivity
        """The diffusivity value for this species, by default None"""
        self.initial_quality: float = initial_quality
        """The global initial quality for this species, by default None (C=0.0)"""
        if atol is not None:
            atol = float(atol)
        if rtol is not None:
            rtol = float(rtol)
        if (atol is None) ^ (rtol is None):
            raise TypeError("atol and rtol must be the same type, got {} and {}".format(atol, rtol))
        self._atol = atol
        self._rtol = rtol
        self._variable_registry = _qm

    def __repr__(self):
        return "{}(name={}, unit={}, atol={}, rtol={}, note={})".format(self.__class__.__name__, repr(self.name), repr(self.units), self._atol, self._rtol, repr(self.note))

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.name == other.name
            and self.units == other.units
            and self.diffusivity == other.diffusivity
            and self._atol == other._atol
            and self._rtol == other._rtol
        )

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

    def to_dict(self):
        rep = dict(name=self.name, unist=self.units)
        tols = self.get_tolerances()
        if tols is not None:
            rep["atol"] = tols[0]
            rep["rtol"] = tols[1]
        rep["diffusivity"] = self.diffusivity
        if isinstance(self.note, str):
            rep["note"] = self.note
        elif isinstance(self.note, ENcomment):
            rep["note"] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep["note"] = None
        return rep


class BulkSpecies(Species):
    """A bulk species.

    .. rubric:: Constructor

    The preferred way to create a new bulk species is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_bulk_species()`, 
    :meth:`~MultispeciesQualityModel.add_species()`, or 
    :meth:`~MultispeciesQualityModel.add_variable()`.
    """

    @property
    def var_type(self):
        return VariableType.BULK


class WallSpecies(Species):
    """A wall species.

    .. rubric:: Constructor

    The preferred way to create a new wall species is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_wall_species()`,
    :meth:`~MultispeciesQualityModel.add_species()`, or
    :meth:`~MultispeciesQualityModel.add_variable()`.
    """

    @property
    def var_type(self):
        return VariableType.WALL


class Coefficient(ReactionVariable):
    """A coefficient, either constant or parameterized by pipe or tank, that is used in reaction expressions.

    .. rubric:: Constructor

    The preferred way to create a new coefficient is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_constant_coeff()`,
    :meth:`~MultispeciesQualityModel.add_parameterized_coeff()`,
    :meth:`~MultispeciesQualityModel.add_coefficient()`, or
    :meth:`~MultispeciesQualityModel.add_variable()`.
    """

    name: str = None
    """The name (symbol) for the variable, must be a valid MSX name"""
    units: str = None
    """The units used for this variable"""
    note: Union[str, Dict[str, str]] = None
    """A note to go with this varibale"""
    global_value: float = None
    """The global value for the coefficient"""

    def __init__(self, name: str, global_value: float, note: Union[str, Dict[str, str]] = None, units: str = None, *, _qm: AbstractQualityModel = None):
        """
        Parameters
        ----------
        name : str
            the name/symbol of the coefficient
        global_value : float
            the global value for the coefficient
        note : Union[str, Dict[str, str]], optional
            a note for this variable, by default None
        units : str, optional
            units for this coefficient, by default None

        Other Parameters
        ----------------
        _qm : MultispeciesQualityModel
            the model to link with, populated automatically if the :class:`MultispeciesQualityModel` API is used, by default None
        """
        if name in RESERVED_NAMES:
            raise ValueError("Name cannot be a reserved name")
        self.name = name
        """The name of the variable"""
        self.global_value = float(global_value)
        """The global value for the coefficient"""
        self.note = note
        """A note about this species, by default None"""
        self.units = units
        """The units used for this species"""
        self._variable_registry = _qm

    def __repr__(self):
        return "{}(name={}, global_value={}, units={}, note={})".format(self.__class__.__name__, repr(self.name), repr(self.global_value), repr(self.units), repr(self.note))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name and self.global_value == other.global_value and self.units == other.units

    def get_value(self) -> float:
        """Get the value of the coefficient

        Returns
        -------
        float
            the global value
        """
        return self.global_value

    def to_dict(self):
        rep = dict(name=self.name, global_value=self.global_value, units=self.units)
        if isinstance(self.note, str):
            rep["note"] = self.note
        elif isinstance(self.note, ENcomment):
            rep["note"] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep["note"] = None
        return rep


class Constant(Coefficient):
    """A constant coefficient for reaction expressions.

    .. rubric:: Constructor

    The preferred way to create a new constant coefficient is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_constant_coeff()`,
    :meth:`~MultispeciesQualityModel.add_coefficient()`, or
    :meth:`~MultispeciesQualityModel.add_variable()`.
    """

    @property
    def var_type(self):
        return VariableType.CONST


class Parameter(Coefficient):
    """A variable parameter for reaction expressions.

    .. rubric:: Constructor

    The preferred way to create a new parameterized coefficient is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_parameterized_coeff()`,
    :meth:`~MultispeciesQualityModel.add_coefficient()`, or
    :meth:`~MultispeciesQualityModel.add_variable()`.
    """

    def __init__(
        self,
        name: str,
        global_value: float,
        note: Union[str, Dict[str, str]] = None,
        units: str = None,
        pipe_values: Dict[str, float] = None,
        tank_values: Dict[str, float] = None,
        *,
        _qm: AbstractQualityModel = None,
    ):
        """
        Parameters
        ----------
        name : str
            the name/symbol of the coefficient
        global_value : float
            the global value for the coefficient
        note : Union[str, Dict[str, str]], optional
            a note for this variable, by default None
        units : str, optional
            units for this coefficient, by default None
        pipe_values : dict, optional
            the values of the parameter at specific pipes, by default None
        tank_values : dict, optional
            the values of the parameter at specific tanks, by default None

        Other Parameters
        ----------------
        _qm : MultispeciesQualityModel
            the model to link with, populated automatically if the :class:`MultispeciesQualityModel` API is used, by default None
        """
        super().__init__(name, global_value=global_value, note=note, units=units, _qm=_qm)
        self._pipe_values = pipe_values if pipe_values is not None else dict()
        """A dictionary of parameter values for various pipes"""
        self._tank_values = tank_values if tank_values is not None else dict()
        """A dictionary of parameter values for various tanks"""

    def __eq__(self, other):
        basic = isinstance(other, self.__class__) and self.name == other.name and self.global_value == other.global_value and self.units == other.units
        if not basic:
            return False
        for k, v in self._pipe_values:
            if other._pipe_values[k] != v:
                return False
        for k, v in self._tank_values:
            if other._tank_values[k] != v:
                return False
        return True

    @property
    def var_type(self):
        return VariableType.PARAM

    def get_value(self, pipe: str = None, tank: str = None) -> float:
        """Get the value of the parameter, either globally or for a specific pipe or tank.

        Parameters
        ----------
        pipe : str, optional
            a pipe to get the value for, by default None
        tank : str, optional
            a tank to get the value for, by default None

        Returns
        -------
        float
            either a specific parameter value for the specified pipe or tank, or the global value
            if nothing is specified OR if the pipe or tank requested does not have a special value.

        Raises
        ------
        TypeError
            if both pipe and tank are specified
        """
        if pipe is not None and tank is not None:
            raise TypeError("Cannot get a value for a pipe and tank at the same time - one or both must be None")
        if pipe is not None:
            return self._pipe_values.get(pipe, self.global_value)
        if tank is not None:
            return self._tank_values.get(tank, self.global_value)
        return self.global_value

    @property
    def pipe_values(self) -> Dict[str, float]:
        """A dictionary of values, iff different from the global value, for specific pipes"""
        return self._pipe_values

    @property
    def tank_values(self) -> Dict[str, float]:
        """A dictionary of values, iff different from the global value, for specific tanks"""
        return self._tank_values

    def to_dict(self):
        rep = super().to_dict()
        rep["pipe_values"] = self._pipe_values.copy()
        rep["tank_values"] = self._tank_values.copy()
        return rep


@dataclass(repr=False)
class OtherTerm(ReactionVariable):
    """An expression term defined as a function of species, coefficients, or other terms.

    .. rubric:: Constructor

    The preferred way to create a new functional term is to use one of the following
    functions from the :class:`MultispeciesQualityModel`:
    :meth:`~MultispeciesQualityModel.add_other_term()` or
    :meth:`~MultispeciesQualityModel.add_variable()`.
    """

    name: str = None
    """The name (symbol) for the variable, must be a valid MSX name"""
    expression: str = None
    """The mathematical expression this term represents"""
    note: Union[str, Dict[str, str]] = None
    """A note to go with this term"""

    def __init__(
        self,
        name: str,
        expression: str,
        note: Union[str, Dict[str, str]] = None,
        *,
        _qm: AbstractQualityModel = None,
    ):
        """
        Parameters
        ----------
        name : str
            the name/symbol of the function (term)
        expression : str
            the mathematical expression described by this function
        note : str, optional
            a note for this function, by default None

        Other Parameters
        ----------------
        _qm : MultispeciesQualityModel
            the model to link with, populated automatically if the :class:`MultispeciesQualityModel` API is used, by default None
        """
        if name in RESERVED_NAMES:
            raise ValueError("Name cannot be a reserved name")
        self.name = name
        """The name of the variable"""
        self.expression = expression
        """The expression this named-function is equivalent to"""
        self.note = note
        """A note about this function/term"""
        self._variable_registry = _qm

    def __repr__(self):
        return "{}(name={}, expression={}, note={})".format(self.__class__.__name__, repr(self.name), repr(self.expression), repr(self.note))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name and self.expression == other.expression

    @property
    def var_type(self):
        return VariableType.TERM

    def to_symbolic(self):
        return super().to_symbolic()

    def to_dict(self):
        rep = dict(name=self.name, expression=self.expression)
        if isinstance(self.note, str):
            rep["note"] = self.note
        elif isinstance(self.note, ENcomment):
            rep["note"] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep["note"] = None
        return rep


@dataclass(repr=False)
class InternalVariable(ReactionVariable):
    """A hydraulic variable or a placeholder for a built-in reserved word.

    For example, "Len" is the EPANET-MSX name for the length of a pipe, and "I" is a sympy
    reserved symbol for the imaginary number.
    
    .. rubric:: Constructor

    Objects of this type are instantiated when creating a new :class:`MultispeciesQualityModel`,
    and should not need to be created by hand.
    """

    name: str = None
    """The name (symbol) for the variable, must be a valid MSX name"""
    units: str = None
    """The units used for this variable"""
    note: Union[str, Dict[str, str]] = None
    """A note to go with this variable"""

    def __init__(
        self,
        name: str,
        note: Union[str, Dict[str, str]] = "internal variable - not output to MSX",
        units: str = None,
    ):
        """
        Parameters
        ----------
        name : str
            The name and symbol for the new variable
        note : str or dict, optional
            A note to go on the object, by default "internal variable - not output to MSX"
        units : str, optional
            Units used by values stored in this variable, by default None
        """
        self.name = name
        """The name of the variable"""
        self.note = note
        """A note about this function/term"""
        self.units = units
        """The units used for this species"""

    def __repr__(self):
        return "{}(name={}, note={}, units={})".format(self.__class__.__name__, repr(self.name), repr(self.note), repr(self.units))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name

    @property
    def var_type(self):
        return VariableType.INTERNAL


@dataclass(repr=False)
class RateDynamics(ReactionDynamics):
    r"""A rate-of-change reaction dynamics expression.

    Used to supply the equation that expresses the rate of change of the given species
    with respect to time as a function of the other species in the model.

    .. math::

        \frac{d}{dt} C(species) = expression

    .. rubric:: Constructor

    The preferred way to create a new rate reaction expression is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_pipe_reaction()`,
    :meth:`~MultispeciesQualityModel.add_tank_reaction()`, or
    :meth:`~MultispeciesQualityModel.add_reaction()`.
    """

    def __init__(self, species: str, location: LocationType, expression: str, note: Union[str, Dict[str, str]] = None, *, _qm: AbstractQualityModel = None):
        """
        Parameters
        ----------
        species : str
            the name of the species whose reaction dynamics is being described
        location : RxnLocationType or str
            the location the reaction occurs (pipes or tanks)
        expression : str
            the expression for the reaction dynamics, which should equal to zero
        note : str, optional
            a note about this reaction

        Other Parameters
        ----------------
        _qm : MultispeciesQualityModel
            the model to link with, populated automatically if the :class:`MultispeciesQualityModel` API is used, by default None
        """
        self.species = species
        """Name of the species being described"""
        self.location = location
        """Location this reaction occurs"""
        self.expression = expression
        """The expression"""
        self.note = note
        """A note or comment about this species reaction dynamics"""
        self._variable_registry = _qm

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name and self.location == other.location and self.expression == other.expression

    @property
    def expr_type(self) -> DynamicsType:
        return DynamicsType.RATE

    def to_symbolic(self):
        return super().to_symbolic()

    def to_dict(self) -> dict:
        rep = dict(species=self.species, expr_type=self.expr_type.name.lower(), expression=self.expression)
        if isinstance(self.note, str):
            rep["note"] = self.note
        elif isinstance(self.note, ENcomment):
            rep["note"] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep["note"] = None
        return rep


@dataclass(repr=False)
class EquilibriumDynamics(ReactionDynamics):
    """An equilibrium reaction expression.

    Used for equilibrium expressions where it is assumed that the expression supplied is being equated to zero.

    .. math::

        0 = expression

    .. rubric:: Constructor

    The preferred way to create a new rate reaction expression is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_pipe_reaction()`,
    :meth:`~MultispeciesQualityModel.add_tank_reaction()`, or
    :meth:`~MultispeciesQualityModel.add_reaction()`.
    """

    def __init__(self, species: str, location: LocationType, expression: str, note: Union[str, Dict[str, str]] = None, *, _qm: AbstractQualityModel = None):
        """
        Parameters
        ----------
        species : str
            the name of the species whose reaction dynamics is being described
        location : RxnLocationType or str
            the location the reaction occurs (pipes or tanks)
        expression : str
            the expression for the reaction dynamics, which should equal to zero
        note : str, optional
            a note about this reaction

        Other Parameters
        ----------------
        _qm : MultispeciesQualityModel
            the model to link with, populated automatically if the :class:`MultispeciesQualityModel` API is used, by default None
        """
        self.species = species
        """Name of the species being described"""
        self.location = location
        """Location this reaction occurs"""
        self.expression = expression
        """The expression"""
        self.note = note
        """A note or comment about this species reaction dynamics"""
        self._variable_registry = _qm

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name and self.location == other.location and self.expression == other.expression

    @property
    def expr_type(self) -> DynamicsType:
        return DynamicsType.EQUIL

    def to_symbolic(self):
        return super().to_symbolic()

    def to_dict(self) -> dict:
        rep = dict(species=self.species, expr_type=self.expr_type.name.lower(), expression=self.expression)
        if isinstance(self.note, str):
            rep["note"] = self.note
        elif isinstance(self.note, ENcomment):
            rep["note"] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep["note"] = None
        return rep


@dataclass(repr=False)
class FormulaDynamics(ReactionDynamics):
    """A formula-based reaction dynamics expression.

    Used when the concentration of the named species is a simple function of the remaining species.

    .. math::

        C(species) = expression

    .. rubric:: Constructor

    The preferred way to create a new rate reaction expression is to use one of the following
    functions from the :class:`MultispeciesQualityModel`: 
    :meth:`~MultispeciesQualityModel.add_pipe_reaction()`,
    :meth:`~MultispeciesQualityModel.add_tank_reaction()`, or
    :meth:`~MultispeciesQualityModel.add_reaction()`.
    """

    def __init__(self, species: str, location: LocationType, expression: str, note: Union[str, Dict[str, str]] = None, *, _qm: AbstractQualityModel = None):
        """
        Parameters
        ----------
        species : str
            the name of the species whose reaction dynamics is being described
        location : RxnLocationType or str
            the location the reaction occurs (pipes or tanks)
        expression : str
            the expression for the reaction formula, which is used to calculate the concentration of the species
        note : str, optional
            a note about this reaction

        Other Parameters
        ----------------
        _qm : MultispeciesQualityModel
            the model to link with, populated automatically if the :class:`MultispeciesQualityModel` API is used, by default None
        """
        self.species = species
        """Name of the species being described"""
        self.location = location
        """Location this reaction occurs"""
        self.expression = expression
        """The expression"""
        self.note = note
        """A note or comment about this species reaction dynamics"""
        self._variable_registry = _qm

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name and self.location == other.location and self.expression == other.expression

    @property
    def expr_type(self) -> DynamicsType:
        return DynamicsType.FORMULA

    def to_symbolic(self):
        return super().to_symbolic()

    def to_dict(self) -> dict:
        rep = dict(species=self.species, expr_type=self.expr_type.name.lower(), expression=self.expression)
        if isinstance(self.note, str):
            rep["note"] = self.note
        elif isinstance(self.note, ENcomment):
            rep["note"] = asdict(self.note) if self.note.pre else self.note.post
        else:
            rep["note"] = None
        return rep


class MultispeciesQualityModel(AbstractQualityModel):
    """A multispecies water quality reactions model, for use with EPANET-MSX.
    """

    def __init__(self, msx_file_name=None):
        """Create a new multispecies water quality reaction model.

        Parameters
        ----------
        msx_file_name : str, optional
            The name of the MSX input file to read
        """
        self.name: str = None
        """A one-line title for the model"""

        self.title: str = None
        """The title line from the MSX file"""

        self._msxfile: str = msx_file_name
        """The original filename"""

        self._citations: List[Union[Citation, str]] = list()
        """A list of citations for the sources of this model's dynamics"""

        self._options: InitVar[MultispeciesOptions] = None
        """A link to the options object"""

        self._wn: WaterNetworkModel = None
        """A link to a water network model"""

        self._options = MultispeciesOptions()

        self._variables: DisjointMapping = DisjointMapping()
        self._species = self._variables.add_disjoint_group("species")
        self._coeffs = self._variables.add_disjoint_group("coeffs")
        self._terms = self._variables.add_disjoint_group("funcs")

        self._dynamics: DisjointMapping = DisjointMapping()
        self._pipe_dynamics = self._dynamics.add_disjoint_group("pipe")
        self._tank_dynamics = self._dynamics.add_disjoint_group("tank")

        self._usage: Dict[str, Set[str]] = dict()  # FIXME: currently no usage tracking

        self._source_dict: Dict[str, Dict[str, Source]] = dict()
        self._inital_qual_dict: Dict[str, Dict[str, Dict[str, float]]] = dict()
        self._pattern_dict: Dict[str, List[float]] = dict()

        self._report = list()

        for v in HYDRAULIC_VARIABLES:
            self._variables[v["name"]] = InternalVariable(v["name"], note=v["note"])
        for name in EXPR_FUNCTIONS.keys():
            self._variables[name.lower()] = InternalVariable(name, note="MSX function")
            self._variables[name.upper()] = InternalVariable(name, note="MSX function")
            self._variables[name.capitalize()] = InternalVariable(name, note="MSX function")
        if msx_file_name is not None:
            from wntr.epanet.msx.io import MsxFile

            inp = MsxFile()
            inp.read(msx_file_name, self)

    def _is_variable_registered(self, var_or_name: Union[str, ReactionVariable]) -> bool:
        name = str(var_or_name)
        if name in self._variables.keys():
            return True
        return False

    def has_variable(self, name: str) -> bool:
        """Check to see if there is a variable by this name.

        Parameters
        ----------
        name : str
            a variable name to check

        Returns
        -------
        bool
            ``True`` if there is a variable by this name, ``False`` otherwise
        """
        return name in self._variables.keys()

    def variable_dict(self) -> Dict[str, Any]:
        vars = dict()
        for symb, spec in self._species.items():
            vars[symb] = symbols(symb)
        for symb, coeff in self._coeffs.items():
            vars[symb] = symbols(symb)
        for symb, term in self._terms.items():
            vars[symb] = symbols(symb)
        return vars

    @property
    def variable_name_list(self) -> List[str]:
        """all defined variable names"""
        return list(self._variables.keys())

    @property
    def species_name_list(self) -> List[str]:
        """all defined species names"""
        return list(self._species.keys())

    @property
    def coefficient_name_list(self) -> List[str]:
        """all defined coefficient names"""
        return list(self._coeffs.keys())

    @property
    def other_term_name_list(self) -> List[str]:
        """all defined function (MSX 'terms') names"""
        return list(self._terms.keys())

    def variables(self, var_type: VariableType = None):
        """A generator to loop over the variables.

        Parameters
        ----------
        var_type : RxnVariableType, optional
            limit results to a specific type, by default None

        Yields
        ------
        RxnVariable
            a variable defined within the model
        """
        var_type = VariableType.get(var_type)
        for v in self._variables.values():
            if var_type is not None and v.var_type != var_type:
                continue
            yield v

    def add_variable(self, var_or_type: Union[ReactionVariable, VariableType], name: str = None, **kwargs):
        """Add an new variable to the model, or add an existing, unlinked variable object to the model.

        Parameters
        ----------
        var_or_type : RxnVariable | RxnVariableType
            the variable object to add to the model, or the type if creating a new variable object
        name : str or None
            the name of a new variable, must be None if adding an existing object, by default None
        kwargs
            any keyword arguments to pass to a new object constructor

        Raises
        ------
        TypeError
            if var_or_type is not a valid object, or if trying to create a new internal/hydraulic variable
        ValueError
            if var_or_type is an object, but name is supplied, or if var_or_type is a type, but no name is supplied
        VariableNameExistsError
            if the variable or name uses the same name an existing variable already uses
        """
        if not isinstance(var_or_type, (ReactionVariable,)):
            try:
                var_or_type = VariableType.get(var_or_type)
            except Exception as e:
                raise TypeError("Cannot add an object that is not a RxnVariable subclass or create a new object without a valid var_type") from e
            if name is None:
                raise ValueError("When adding a new variable, a name must be supplied")
            typ = var_or_type
            if typ is VariableType.BULK or typ is VariableType.WALL:
                self.add_species(var_or_type, name, **kwargs)
            elif typ is VariableType.CONST or typ is VariableType.PARAM:
                self.add_coefficient(var_or_type, name, **kwargs)
            elif typ is VariableType.TERM:
                self.add_other_term(var_or_type, name, **kwargs)
            else:
                raise TypeError("Cannot create new objects of the INTERNAL type using this function")
        else:
            if name is None or len(kwargs) > 0:
                raise ValueError("When adding an existing variable object, no other arguments may be supplied")
            __variable = var_or_type
            if self._is_variable_registered(__variable):
                raise KeyExistsError("A variable with this name already exists in the model")
            typ = __variable.var_type
            name = __variable.name
            if hasattr(__variable, "_variable_registry"):
                __variable._variable_registry = self
            if typ is VariableType.BULK or typ is VariableType.WALL:
                self._variables.add_item_to_group("species", name, __variable)
                self._inital_qual_dict[name] = dict(global_value=None, nodes=dict(), links=dict())
                self._source_dict[name] = dict()
            elif typ is VariableType.CONST or typ is VariableType.PARAM:
                self._variables.add_item_to_group("coeffs", name, __variable)
            elif typ is VariableType.TERM:
                self._variables.add_item_to_group("funcs", name, __variable)
            else:
                self._variables.add_item_to_group(None, name, __variable)

    def add_species(
        self,
        species_type: Union[str, int, VariableType],
        name: str,
        units: str,
        atol: float = None,
        rtol: float = None,
        note: str = None,
    ) -> Species:
        """Add a new species to the model.
        The atol and rtol parameters must either both be omitted or both be provided.

        Parameters
        ----------
        species_type : ~VariableType.BULK | ~VariableType.WALL
            the type of species
        name : str
            the name/symbol of the species
        units : str
            the unit of concentration used
        atol : float, optional
            the absolute tolerance for the solver for this species, by default None (global value)
        rtol : float, optional
            the relative tolerance fot the solver for this species, by default None (global value)
        note : str, optional
            a note or comment about this species, by default None

        Returns
        -------
        Species
            the new species object

        Raises
        ------
        ValueError
            if species_type is invalid
        VariableNameExistsError
            if a variable with this name already exists in the model
        TypeError
            if atol and rtol are not both None or both a float
        """
        species_type = VariableType.get(species_type)
        if species_type not in [VariableType.BULK, VariableType.WALL]:
            raise ValueError("Species must be BULK or WALL, got {:s}".format(species_type))
        if self._is_variable_registered(name):
            raise KeyExistsError("The variable {} already exists in this model".format(name))
        if (atol is None) ^ (rtol is None):
            raise TypeError("atol and rtol must be the same type, got {} and {}".format(atol, rtol))
        if species_type is VariableType.BULK:
            var = BulkSpecies(name=name, units=units, atol=atol, rtol=rtol, note=note, _qm=self)
        elif species_type is VariableType.WALL:
            var = WallSpecies(name=name, units=units, atol=atol, rtol=rtol, note=note, _qm=self)
        self._species[name] = var
        self._inital_qual_dict[name] = dict([("global", None), ("nodes", dict()), ("links", dict())])
        self._source_dict[name] = dict()
        return var

    def add_bulk_species(self, name: str, units: str, atol: float = None, rtol: float = None, note: str = None) -> BulkSpecies:
        """Add a new bulk species to the model.
        The atol and rtol parameters must either both be omitted or both be provided.

        Parameters
        ----------
        name : str
            the name/symbol of the species
        units : str
            the unit of concentration used
        atol : float, optional
            the absolute tolerance for the solver for this species, by default None (global value)
        rtol : float, optional
            the relative tolerance fot the solver for this species, by default None (global value)
        note : str, optional
            a note or comment about this species, by default None

        Returns
        -------
        Species
            the new species object

        Raises
        ------
        VariableNameExistsError
            if a variable with this name already exists in the model
        TypeError
            if atol and rtol are not both None or both a float
        """
        return self.add_species(VariableType.BULK, name, units, atol, rtol, note)

    def add_wall_species(self, name: str, units: str, atol: float = None, rtol: float = None, note: str = None) -> WallSpecies:
        """Add a new wall species to the model.
        The atol and rtol parameters must either both be omitted or both be provided.

        Parameters
        ----------
        name : str
            the name/symbol of the species
        units : str
            the unit of concentration used
        atol : float, optional
            the absolute tolerance for the solver for this species, by default None (global value)
        rtol : float, optional
            the relative tolerance fot the solver for this species, by default None (global value)
        note : str, optional
            a note or comment about this species, by default None

        Returns
        -------
        Species
            the new species object

        Raises
        ------
        VariableNameExistsError
            if a variable with this name already exists in the model
        TypeError
            if atol and rtol are not both None or both a float
        """
        return self.add_species(VariableType.WALL, name, units, atol, rtol, note)

    def add_coefficient(self, coeff_type: Union[str, int, VariableType], name: str, global_value: float, note: str = None, units: str = None, **kwargs) -> Coefficient:
        """Add a new coefficient to the model.

        Parameters
        ----------
        coeff_type : CONST or PARAM
            the type of coefficient to add
        name : str
            the name/symbol of the coefficient
        global_value : float
            the global value for the coefficient
        note : str, optional
            a note or comment about this coefficient, by default None
        units : str, optional
            a unit for this coefficient, by default None
        kwargs : other keyword arguments
            certain coefficient classes have additional arguments. If specified,
            these will be passed to the constructor for the relevant class.

        Returns
        -------
        Coefficient
            the new coefficient object

        Raises
        ------
        ValueError
            if the coeff_type is invalid
        VariableNameExistsError
            if a variable with this name already exists in the model
        """
        coeff_type = VariableType.get(coeff_type)
        if coeff_type not in [VariableType.CONST, VariableType.PARAM]:
            raise ValueError("coeff_type must be CONST or PARAM, got {:s}".format(coeff_type))
        if self._is_variable_registered(name):
            raise KeyExistsError("The variable {} already exists in this model".format(name))
        if coeff_type is VariableType.CONST:
            var = Constant(name=name, global_value=global_value, note=note, units=units, _qm=self)
        elif coeff_type is VariableType.PARAM:
            var = Parameter(name=name, global_value=global_value, note=note, units=units, _qm=self, **kwargs)
        self._coeffs[name] = var
        return var

    def add_constant_coeff(self, name: str, global_value: float, note: str = None, units: str = None) -> Constant:
        """Add a new constant coefficient to the model.

        Parameters
        ----------
        coeff_type : CONST or PARAM
            the type of coefficient to add
        name : str
            the name/symbol of the coefficient
        global_value : float
            the global value for the coefficient
        note : str, optional
            a note or comment about this coefficient, by default None
        units : str, optional
            units for this coefficient, by default None

        Returns
        -------
        Coefficient
            the new coefficient object

        Raises
        ------
        ValueError
            if the coeff_type is invalid
        VariableNameExistsError
            if a variable with this name already exists in the model
        """
        return self.add_coefficient(VariableType.CONST, name=name, global_value=global_value, note=note, units=units)

    def add_parameterized_coeff(
        self, name: str, global_value: float, note: str = None, units: str = None, pipe_values: Dict[str, float] = None, tank_values: Dict[str, float] = None
    ) -> Parameter:
        """Add a new parameterized coefficient (based on pipe/tank name) to the model.

        Parameters
        ----------
        coeff_type : CONST or PARAM
            the type of coefficient to add
        name : str
            the name/symbol of the coefficient
        global_value : float
            the global value for the coefficient
        note : str, optional
            a note or comment about this coefficient, by default None
        units: str, optional
            a unit for this coefficient, by default None
        pipe_values : dict, optional
            values for this coefficient in specifically named pipes
        tank_values : dict, optional
            values for this coefficient in specifically named tanks

        Returns
        -------
        Coefficient
            the new coefficient object

        Raises
        ------
        ValueError
            if the coeff_type is invalid
        VariableNameExistsError
            if a variable with this name already exists in the model
        """
        return self.add_coefficient(VariableType.PARAM, name=name, global_value=global_value, note=note, units=units, pipe_values=pipe_values, tank_values=tank_values)

    def add_other_term(self, name: str, expression: str, note: str = None) -> OtherTerm:
        """Add a new user-defined function to the model.
        In EPANET-MSX, these variables are called 'TERMS', and serve as shortcut aliases
        to simplify reaction expressions that would otherwise become very hard to read/write
        on a single line (a requirement in EPANET-MSX input files). Because 'term' is
        ambiguous, this will be referred to as a 'other term' or 'simplifying term'.

        Parameters
        ----------
        name : str
            the name/symbol for this function (an MSX 'term')
        expression : str
            the symbolic expression for this function
        note : str, optional
            a note or comment about this function, by default None

        Returns
        -------
        UserFunction
            the new function or simplyifying term object

        Raises
        ------
        VariableNameExistsError
            if a variable with this name already exists in the model
        """
        if self._is_variable_registered(name):
            raise KeyExistsError("The variable {} already exists in this model".format(name))
        var = OtherTerm(name=name, expression=expression, note=note, _qm=self)
        self._terms[name] = var
        return var

    def remove_variable(self, name: str):
        """Remove a variable from the model.

        Parameters
        ----------
        name : str
            variable name
        """
        if name in self._inital_qual_dict.keys():
            self._inital_qual_dict.__delitem__(name)
        if name in self._source_dict.keys():
            self._source_dict.__delitem__(name)
        return self._variables.__delitem__(name)

    def get_variable(self, name: str) -> ReactionVariable:
        """Get a variable based on its name (symbol).

        Parameters
        ----------
        name : str
            The variable name

        Returns
        -------
        ReactionVariable
            the variable with the name in question

        Raises
        ------
        KeyError
            a variable with that name does not exist
        """
        return self._variables[name]

    def reactions(self, location: LocationType = None):
        """A generator for iterating through reactions in the model.

        Parameters
        ----------
        location : RxnLocationType, optional
            limit results to reactions within location, by default None

        Yields
        ------
        ReactionDynamics
            a reaction defined within the model
        """
        location = LocationType.get(location)
        for v in self._dynamics.values():
            if location is not None and v.location != location:
                continue
            yield v

    def add_reaction(self, location: LocationType, species: Union[str, Species], dynamics: Union[str, int, DynamicsType], expression: str, note: str = None):
        """Add a multispecies water quality reaction to the model.

        Parameters
        ----------
        location : LocationType
            where the reaction is taking place
        species : Union[str, Species]
            the species with the dynamics that are being described
        dynamics : Union[str, int, DynamicsType]
            the type of reaction dynamics used to describe this species changes through time
        expression : str
            the right-hand-side of the reaction dynamics equation
        note : str, optional
            a note about this reaction, by default None

        Returns
        -------
        ReactionDynamics
            the resulting reaction object

        Raises
        ------
        ValueError
            species does not exist
        RuntimeError
            species already has reaction defined FIXME: this should be an MSX error
        ValueError
            invalid dynamics type
        ValueError
            invalid location type
        """
        # TODO: accept a "both" or "all" value for location
        location = LocationType.get(location)
        species = str(species)
        if species not in self._species.keys():
            raise ValueError("The species {} does not exist in the model, failed to add reaction.".format(species))
        _key = ReactionDynamics.to_key(species, location)
        if _key in self._dynamics.keys():
            raise RuntimeError("The species {} already has a {} reaction defined. Use set_reaction instead.")
        dynamics = DynamicsType.get(dynamics)
        new = None
        if dynamics is DynamicsType.EQUIL:
            new = EquilibriumDynamics(species=species, location=location, expression=expression, note=note, _qm=self)
        elif dynamics is DynamicsType.RATE:
            new = RateDynamics(species=species, location=location, expression=expression, note=note, _qm=self)
        elif dynamics is DynamicsType.FORMULA:
            new = FormulaDynamics(species=species, location=location, expression=expression, note=note, _qm=self)
        else:
            raise ValueError("Invalid dynamics type, {}".format(dynamics))
        if location is LocationType.PIPE:
            self._pipe_dynamics[str(new)] = new
        elif location is LocationType.TANK:
            self._tank_dynamics[str(new)] = new
        else:
            raise ValueError("Invalid location type, {}".format(location))
        return new

    def add_pipe_reaction(self, species: Union[str, Species], dynamics: Union[str, int, DynamicsType], expression: str, note: str = None) -> ReactionDynamics:
        """Add a pipe reaction. See also :meth:`add_reaction`.

        Parameters
        ----------
        species : Union[str, Species]
            the species with the dynamics that are being described
        dynamics : Union[str, int, DynamicsType]
            the type of reaction dynamics used to describe this species changes through time
        expression : str
            the right-hand-side of the reaction dynamics equation
        note : str, optional
            a note about this reaction, by default None

        Returns
        -------
        ReactionDynamics
            the reaction object
        """
        return self.add_reaction(LocationType.PIPE, species=species, dynamics=dynamics, expression=expression, note=note)

    def add_tank_reaction(self, species: Union[str, Species], dynamics: Union[str, int, DynamicsType], expression: str, note: str = None) -> ReactionDynamics:
        """Add a pipe reaction. See also :meth:`add_reaction`.

        Parameters
        ----------
        species : Union[str, Species]
            the species with the dynamics that are being described
        dynamics : Union[str, int, DynamicsType]
            the type of reaction dynamics used to describe this species changes through time
        expression : str
            the right-hand-side of the reaction dynamics equation
        note : str, optional
            a note about this reaction, by default None

        Returns
        -------
        ReactionDynamics
            the reaction object
        """
        return self.add_reaction(LocationType.TANK, species=species, dynamics=dynamics, expression=expression, note=note)

    def remove_reaction(self, species: Union[str, Species], location: Union[str, int, LocationType, Literal["all"]]):
        """Remove a reaction for a species from the model

        Parameters
        ----------
        species : str or Species
            the species to remove a reaction for
        location : str, int, LocationType or 'all'
            the location of the reaction to delete, with 'all' meaning both wall and pipe reactions

        Raises
        ------
        ValueError
            if the value for `location` is invalid
        """
        if location != "all":
            location = LocationType.get(location)
        species = str(species)
        if location is None:
            raise TypeError('location cannot be None when removing a reaction. Use "all" for all locations.')
        elif location == "all":
            name = ReactionDynamics.to_key(species, LocationType.PIPE)
            try:
                self._pipe_dynamics.__delitem__(name)
            except KeyError:
                pass
            name = ReactionDynamics.to_key(species, LocationType.TANK)
            try:
                self._tank_dynamics.__delitem__(name)
            except KeyError:
                pass
        elif location is LocationType.PIPE:
            name = ReactionDynamics.to_key(species, LocationType.PIPE)
            try:
                self._pipe_dynamics.__delitem__(name)
            except KeyError:
                pass
        elif location is LocationType.TANK:
            name = ReactionDynamics.to_key(species, LocationType.TANK)
            try:
                self._tank_dynamics.__delitem__(name)
            except KeyError:
                pass
        else:
            raise ValueError("Invalid location, {}".format(location))

    def get_reaction(self, species, location):
        """Get a reaction for a species at either a pipe or tank.

        Parameters
        ----------
        species : str or Species
            the species to get a reaction for
        location : str, int, or LocationType
            the location of the reaction

        Returns
        -------
        ReactionDynamics
            the requested reaction object
        """
        if species is None:
            raise TypeError("species must be a string or Species")
        if location is None:
            raise TypeError("location must be a string, int, or LocationType")
        species = str(species)
        location = LocationType.get(location)
        loc = location.name.lower()
        if location == LocationType.PIPE:
            return self._pipe_dynamics.get(species + "." + loc)
        elif location == LocationType.TANK:
            return self._tank_dynamics.get(species + "." + loc)

    def init_printing(self, *args, **kwargs):
        """Call sympy.init_printing"""
        init_printing(*args, **kwargs)

    @property
    def citations(self) -> List[Union[str, Citation]]:
        """A list of citation strings or Citation objects.
        The Citation object from wntr.utils does not have to be used, but an object of
        a different type should have a "to_dict" method to ensure that dictionary and
        json conversions work as intended.
        """
        return self._citations

    @property
    def options(self) -> MultispeciesOptions:
        """The multispecies reaction model options."""
        return self._options

    @options.setter
    def options(self, value):
        if isinstance(value, dict):
            self._options = MultispeciesOptions.factory(value)
        elif not isinstance(value, MultispeciesOptions):
            raise TypeError("Expected a RxnOptions object, got {}".format(type(value)))
        else:
            self._options = value

    def link_water_network_model(self, wn: WaterNetworkModel):
        self._wn = wn

    def to_dict(self) -> dict:
        """Convert this water quality model to a dictionary"""
        wntr.quality.io.to_dict()

    def from_dict(self, d) -> dict:
        """Append to this water quality model from a dictionary"""
        wntr.quality.io.from_dict(d, append=self)

    def __repr__(self):
        if self._msxfile or self.name:
            return "{}({})".format(self.__class__.__name__, repr(self._msxfile) if self._msxfile else repr(self.name))
        return super().__repr__()
