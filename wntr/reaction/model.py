# -*- coding: utf-8 -*-
"""
Water quality reactions base classes

"""

import logging
import warnings
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from enum import Enum, IntFlag
from typing import Any, ClassVar, Dict, Hashable, Iterator, List, Set, Tuple, Union

import sympy
from sympy import Float, Symbol, symbols
from sympy.parsing import parse_expr
from sympy.parsing.sympy_parser import standard_transformations, convert_xor


class VarType(IntFlag):
    """The type of reaction variable"""

    Bulk = 1
    """A species that reacts with other bulk chemicals"""
    Wall = 2
    """A species that reacts with the pipe walls"""
    Constant = 4
    """A constant coefficient for use in a reaction expression"""
    Parameter = 8
    """A coefficient that has a value dependent on the pipe or tank"""
    Term = 16
    """A term that is aliased for ease of writing expressions"""
    # Hydraulic = 32
    # """A hydraulic variable - users should not use this"""

    Species = Bulk | Wall
    """A reaction species"""
    Coeff = Constant | Parameter
    """A reaction coefficient"""

    B = Bulk
    W = Wall
    C = Constant
    P = Parameter
    T = Term
    # H = Hydraulic
    # Hyd = Hydraulic
    Const = Constant
    Param = Parameter


class RxnLocation(Enum):
    """What type of network component does this reaction occur in"""

    Pipes = 1
    """The expression describes a reaction in pipes"""
    Tanks = 2
    """The expression describes a reaction in tanks"""
    P = Pipes
    T = Tanks


class ExprType(Enum):
    """The type of reaction expression"""

    Equil = 1
    """An equilibrium reaction, where expression is RHS of: 0 = f(…,Cᵢ,…), {i | i=1..n}"""
    Rate = 2
    """A decay rate equation, where expression is RHS of: ∂Cᵢ/∂t = f(…,Cᵢ,…), {i | i=1..n}"""
    Formula = 3
    """A formula reaction, where expression is RHS of: Cᵢ = f(…,Cⱼ,…), {j | j=1..n, j≠i}"""
    E = Equil
    R = Rate
    F = Formula


class WaterQualityReactionsModel:
    """A registry of the reaction variables."""

    RESERVED_NAMES = ("D", "Q", "U", "Re", "Us", "Ff", "Av", "E", "I", "pi")
    """These (case sensitive) names are reserved for hydraulic variables and sympy
    physical constants. Note that physical constants E, I, and pi are *not* valid MSX 
    variables - they are reserved symbols in sympy and so they should not be used 
    for variable names."""

    def __init__(self):
        self._variables: Dict[str, RxnVariable] = dict()
        self._usage: Dict[str, Set[str]] = dict()
        self._pipe_reactions: Dict[Hashable, RxnExpression] = dict()
        self._tank_reactions: Dict[Hashable, RxnExpression] = dict()
        for v in self.RESERVED_NAMES:
            self._usage[v] = set()

    @property
    def hydraulic_vars(self) -> Dict[str, str]:
        """The following are the hydraulic variables usable within expressions and terms.

        D : pipe diameter (feet or meters)
        Q : pipe flow rate (flow units)
        U : pipe flow velocity (ft/s or m/s)
        Re : flow Reynolds number
        Us : pipe shear velocity (ft/s or m/s)
        Ff : Darcy-Weisbach friction factor
        Av : Surface area per unit volume (area-units/L)
        """
        return {
            "D": "pipe diameter (feet or meters)",
            "Q": "pipe flow rate (flow units)",
            "U": "pipe flow velocity (ft/s or m/s)",
            "Re": "flow Reynolds number",
            "Us": "pipe shear velocity (ft/s or m/s)",
            "Ff": "Darcy-Weisbach friction factor",
            "Av": "Surface area per unit volume (area-units/L)",
        }

    def variables(self):
        """Generator to iterate over all user defined variables (species, terms, etc).

        Yields
        ------
        str, RxnVariable
            name and object

        Raises
        ------
        StopIteration
        """
        for k, v in self._variables.items():
            yield k, v
        raise StopIteration

    def species(self):
        """Generator to iterate over all species.

        Yields
        ------
        str, RxnSpecies
            name and object

        Raises
        ------
        StopIteration
        """
        for k, v in self._variables.items():
            if isinstance(v, RxnSpecies):
                yield k, v
        raise StopIteration

    def coefficients(self):
        """Generator to iterate over all coefficients.

        Yields
        ------
        str, RxnCoefficient
            name and object

        Raises
        ------
        StopIteration
        """
        for k, v in self._variables.items():
            if isinstance(v, RxnCoefficient):
                yield k, v
        raise StopIteration

    def terms(self):
        """Generator to iterate over all terms.

        Yields
        ------
        str, RxnTerm
            name and object

        Raises
        ------
        StopIteration
        """
        for k, v in self._variables.items():
            if isinstance(v, RxnTerm):
                yield k, v
        raise StopIteration

    def reactions(self):
        """Generator to iterate over all expressions.

        Yields
        ------
        RxnExpression
            reaction expression object

        Raises
        ------
        StopIteration
        """
        for v in self._pipe_reactions.values():
            yield v
        for v in self._tank_reactions.values():
            yield v
        raise StopIteration

    def pipe_reactions(self):
        """Generator to iterate over all expressions.

        Yields
        ------
        RxnExpression
            reaction expression object

        Raises
        ------
        StopIteration
        """
        for v in self._pipe_reactions.values():
            yield v
        raise StopIteration

    def tank_reactions(self):
        """Generator to iterate over all expressions.

        Yields
        ------
        RxnExpression
            reaction expression object

        Raises
        ------
        StopIteration
        """
        for v in self._tank_reactions.values():
            yield v
        raise StopIteration

    @property
    def all_symbols(self) -> Set[sympy.Symbol]:
        """Set of all symbols defined, including hydraulic variables"""
        return set(symbols(" ".join(self._usage.keys())))

    @property
    def variable_names(self) -> Set[str]:
        """Set of all user-defined symbols (excludes hydraulic variables)"""
        return self._variables.keys()

    def add_variable(self, typ: Union[str, VarType], name: str, *args, note: str = None, **kwargs) -> "RxnVariable":
        """Add a new variable to the Reactions object.

        Parameters
        ----------
        typ : str or VarType
            the type of variable
        name : str
            the name (symbol) for the variable
        note : str, optional
            a note or comment describing the variable, by default None

        Returns
        -------
        RxnVariable
            the new variable

        Raises
        ------
        ValueError
            - if name already exists, or
            - missing or invalid value for :param:`typ`
        """
        if name in self._variables.keys():
            raise ValueError("A variable named {} already exists: {}".format(name, self._variables[name]))
        if not typ:
            raise ValueError("Missing/invalid value for typ, got {}".format(typ))
        if isinstance(typ, str) and len(typ) > 0:
            typ = typ[0].upper()
            try:
                typ = VarType[typ]
            except KeyError as k:
                raise ValueError("Missing/invalid value for typ, expected VarType but got {}".format(repr(typ))) from k
        if typ & VarType.Species:
            return self.add_species(typ, name, *args, note=note, **kwargs)
        elif typ & VarType.Coeff:
            return self.add_coefficient(typ, name, *args, note=note, **kwargs)
        elif typ & VarType.Term:
            return self.add_term(name, *args, note=note, **kwargs)
        raise ValueError("Missing/invalid value for typ, got {}".format(typ))

    def add_species(self, typ: Union[str, VarType], name: str, unit: str, Atol: float = None, Rtol: float = None, note: str = None) -> "RxnSpecies":
        """Add a species to the Reactions object

        Parameters
        ----------
        typ : Union[str, VarType]
            _description_
        name : str
            _description_
        unit : str
            _description_
        Atol : float, optional
            _description_, by default None
        Rtol : float, optional
            _description_, by default None
        note : str, optional
            _description_, by default None

        Returns
        -------
        RxnSpecies
            _description_

        Raises
        ------
        ValueError
            - a variable with the :param:`name` already exists
            - an incorrect value for :param:`typ`
        """
        if name in self._variables.keys():
            raise ValueError("A variable named {} already exists: {}".format(name, self._variables[name]))
        if isinstance(typ, str) and len(typ) > 0:
            typ = typ[0].upper()
            try:
                typ = VarType[typ]
            except KeyError as k:
                raise ValueError("Missing/invalid value for typ, expected VarType but got {}".format(repr(typ))) from k
        if typ & VarType.Bulk:
            return self.add_bulk_species(name, unit, Atol, Rtol, note)
        elif typ & VarType.Wall:
            return self.add_wall_species(name, unit, Atol, Rtol, note)
        else:
            raise ValueError("typ must be a valid species type but got {}".format(typ))

    def add_bulk_species(self, name: str, unit: str, Atol: float = None, Rtol: float = None, note: str = None) -> "BulkSpecies":
        """_summary_

        Parameters
        ----------
        name : str
            _description_
        unit : str
            _description_
        Atol : float, optional
            _description_, by default None
        Rtol : float, optional
            _description_, by default None
        note : str, optional
            _description_, by default None

        Returns
        -------
        BulkSpecies
            _description_

        Raises
        ------
        ValueError
            a variable with the :param:`name` already exists
        """
        if name in self._variables.keys():
            raise ValueError("A variable named {} already exists: {}".format(name, self._variables[name]))
        new = BulkSpecies(name=name, unit=unit, Atol=Atol, Rtol=Rtol, note=note)
        self._variables[name] = new
        self._usage[name] = set()
        return new

    def add_wall_species(self, name: str, unit: str, Atol: float = None, Rtol: float = None, note: str = None) -> "WallSpecies":
        """_summary_

        Parameters
        ----------
        name : str
            _description_
        unit : str
            _description_
        Atol : float, optional
            _description_, by default None
        Rtol : float, optional
            _description_, by default None
        note : str, optional
            _description_, by default None

        Returns
        -------
        WallSpecies
            _description_

        Raises
        ------
        ValueError
            a variable with the :param:`name` already exists
        """
        if name in self._variables.keys():
            raise ValueError("A variable named {} already exists: {}".format(name, self._variables[name]))
        new = WallSpecies(name=name, unit=unit, Atol=Atol, Rtol=Rtol, note=note)
        self._variables[name] = new
        self._usage[name] = set()
        return new

    def add_coefficient(
        self, typ: Union[str, VarType], name: str, value: float, note: str = None, pipe_values: Dict[str, float] = None, tank_values: Dict[str, float] = None
    ) -> "RxnCoefficient":
        """_summary_

        Parameters
        ----------
        typ : Union[str, VarType]
            _description_
        name : str
            _description_
        value : float
            _description_
        note : str, optional
            _description_, by default None
        pipe_values : Dict[str, float], optional
            _description_, by default None
        tank_values : Dict[str, float], optional
            _description_, by default None

        Returns
        -------
        RxnCoefficient
            _description_

        Raises
        ------
        ValueError
            - a variable with the :param:`name` already exists
            - an incorrect value for :param:`typ`
        TypeError
            value(s) were passed for :param:`pipe_values` or :param:`tank_values` but the :param:`typ` is ``Constant``
        """
        if name in self._variables.keys():
            raise ValueError("A variable named {} already exists: {}".format(name, self._variables[name]))
        if isinstance(typ, str) and len(typ) > 0:
            typ = typ[0].upper()
            try:
                typ = VarType[typ]
            except KeyError as k:
                raise ValueError("Missing/invalid value for typ, expected VarType but got {}".format(repr(typ))) from k
        if typ & VarType.Const:
            if pipe_values is not None or tank_values is not None:
                raise ValueError(
                    "pipe_values and tank_values must be None for constants but values for {}".format(
                        ("pipe_values" if pipe_values is not None else "")
                        + (" and " if pipe_values is not None and tank_values is not None else "")
                        + ("tank_values" if tank_values is not None else "")
                    )
                )
            return self.add_constant(name, value, note)
        elif typ & VarType.Param:
            return self.add_parameter(name, value, note, pipe_values, tank_values)
        else:
            raise ValueError("typ must be a valid coefficient type but got {}".format(typ))

    def add_constant(self, name: str, value: float, note: str = None) -> "Constant":
        """_summary_

        Parameters
        ----------
        name : str
            _description_
        value : float
            _description_
        note : str, optional
            _description_, by default None

        Returns
        -------
        Constant
            _description_

        Raises
        ------
        ValueError
            a variable with the :param:`name` already exists
        """
        if name in self._variables.keys():
            raise ValueError("A variable named {} already exists: {}".format(name, self._variables[name]))
        new = Constant(name=name, global_value=value, note=note)
        self._variables[name] = new
        self._usage[name] = set()
        return new

    def add_parameter(self, name: str, value: float, note: str = None, pipe_values: Dict[str, float] = None, tank_values: Dict[str, float] = None) -> "Parameter":
        """_summary_

        Parameters
        ----------
        name : str
            _description_
        value : float
            _description_
        note : str, optional
            _description_, by default None
        pipe_values : Dict[str, float], optional
            _description_, by default None
        tank_values : Dict[str, float], optional
            _description_, by default None

        Returns
        -------
        Parameter
            _description_

        Raises
        ------
        ValueError
            a variable with the :param:`name` already exists
        """
        if name in self._variables.keys():
            raise ValueError("A variable named {} already exists: {}".format(name, self._variables[name]))
        new = Parameter(name=name, global_value=value, note=note, pipe_values=pipe_values, tank_values=tank_values)
        self._variables[name] = new
        self._usage[name] = set()
        return new

    def add_term(self, name: str, expr: str, note: str = None) -> "RxnTerm":
        """_summary_

        Parameters
        ----------
        name : str
            _description_
        expr : str
            _description_
        note : str, optional
            _description_, by default None

        Returns
        -------
        RxnTerm
            _description_

        Raises
        ------
        ValueError
            a variable with the :param:`name` already exists
        NameError
            the term uses variable names that are undefined
        """
        if name in self._variables.keys():
            raise ValueError("A variable named {} already exists: {}".format(name, self._variables[name]))
        expr1 = sympy.parse_expr(expr)
        used = expr1.free_symbols
        undefined = used - self.all_symbols
        if len(undefined) > 0:
            raise NameError("Undefined symbol(s) {} in term {}".format(undefined, name))
        new = RxnTerm(name=name, expression=expr, note=note)
        self._variables[name] = new
        self._usage[name] = set()
        for v in used:
            self._usage[v].add(name)
        return new

    def add_reaction(self, loc: Union[str, RxnLocation], typ: Union[str, ExprType], species: Union[str, 'RxnSpecies'], expression: str, note: str = None) -> "RxnExpression":
        """Add a new reaction 

        Parameters
        ----------
        loc : str or RxnLocation
            the location for the reaction: Pipe or Tank
        typ : str or ExprType
            the type of expression: Rate, Equilibrium or Formula
        species : str or RxnSpecies
            the species that is being described
        expression : str
            the actual mathematical expression
        note : str, optional
            any notes or comments, by default None

        Returns
        -------
        RxnExpression
            the new expression object

        Raises
        ------
        ValueError
            an incorrect/invalid value for :param:`loc`
        """
        if not loc:
            raise ValueError("A valid ExprLocationType must be specified for loc, but got {}".format(repr(loc)))
        if isinstance(loc, str) and len(loc) > 0:
            loc = loc[0].upper()
            try:
                loc = RxnLocation[loc]
            except KeyError as k:
                raise ValueError("Missing/unknown value for loc, expected ExprLocationType but got {}".format(loc)) from k
        if loc is RxnLocation.Pipes:
            return self.add_pipe_reaction(typ=typ, species=species, expression=expression, note=note)
        elif loc is RxnLocation.Tanks:
            return self.add_tank_reaction(typ=typ, species=species, expression=expression, note=note)
        else:
            raise ValueError("Missing/unknown value for loc, expected ExprLocationType but got {}".format(loc))

    def add_pipe_reaction(self, typ: Union[str, ExprType], species: Union[str, 'RxnSpecies'], expression: str, note: str = None) -> "RxnExpression":
        """Add a new pipe reaction to the model.

        Parameters
        ----------
        typ : str or ExprType
            the type of expression: Rate, Equilibrium or Formula
        species : str
            the species that is being described
        expression : str
            the actual mathematical expression
        note : str, optional
            any notes or comments, by default None

        Returns
        -------
        RxnExpression
            the new expression object

        Raises
        ------
        ValueError
            an incorrect/invalid value for :param:`typ`
        """
        if species is not None:
            species = str(species)
        if not typ:
            raise ValueError("A valid ExprType must be specified for typ, got {}".format(repr(typ)))
        if isinstance(typ, str) and len(typ) > 0:
            typ = typ[0].upper()
            try:
                typ = ExprType[typ]
            except KeyError as k:
                raise ValueError("Missing/unknown value for typ, expected ExprType but got {}".format(typ)) from k
        if typ is ExprType.Equil:
            new = Equilibrium(species=species, loc=RxnLocation.Pipes, expression=expression, note=note, _variables=self)
        elif typ is ExprType.Rate:
            new = Rate(species=species, loc=RxnLocation.Pipes, expression=expression, note=note, _variables=self)
        elif typ is ExprType.Formula:
            new = Formula(species=species, loc=RxnLocation.Pipes, expression=expression, note=note, _variables=self)
        else:
            raise ValueError("Unknown value for ExprType, got typ={}".format(typ))
        self._pipe_reactions[(typ.name, species)] = new
        return new

    def add_tank_reaction(self, typ: Union[str, ExprType], species: Union[str, 'RxnSpecies'], expression: str, note: str = None) -> "RxnExpression":
        """Add a new tank reaction to the model.

        Parameters
        ----------
        typ : str or ExprType
            the type of expression: Rate, Equilibrium or Formula
        species : str
            the species that is being described
        expression : str
            the actual mathematical expression
        note : str, optional
            any notes or comments, by default None

        Returns
        -------
        RxnExpression
            the new expression object

        Raises
        ------
        ValueError
            an incorrect/invalid value for :param:`typ`
        """
        if species is not None:
            species = str(species)
        if not typ:
            raise ValueError("A valid ExprType must be specified for typ, got {}".format(repr(typ)))
        if isinstance(typ, str) and len(typ) > 0:
            typ = typ[0].upper()
            try:
                typ = ExprType[typ]
            except KeyError as k:
                raise ValueError("Missing/unknown value for typ, expected ExprType but got {}".format(typ)) from k
        if typ is ExprType.Equil:
            new = Equilibrium(species=species, loc=RxnLocation.Tanks, expression=expression, note=note, _variables=self)
        elif typ is ExprType.Rate:
            new = Rate(species=species, loc=RxnLocation.Tanks, expression=expression, note=note, _variables=self)
        elif typ is ExprType.Formula:
            new = Formula(species=species, loc=RxnLocation.Tanks, expression=expression, note=note, _variables=self)
        else:
            raise ValueError("Unknown value for ExprType, got typ={}".format(typ))
        self._tank_reactions[(typ.name, species)] = new
        return new

    def get_variable(self, name) -> "RxnVariable":
        """Get a variable by name.

        Parameters
        ----------
        name : str
            the name of a defined variable

        Returns
        -------
        RxnVariable
            the variable requested

        Raises
        ------
        KeyError
            if a variable with that name does not exist
        TypeError
            if the variable is one of the :attr:`RESERVED_NAMES` that is not
            an object
        """
        if name in self.RESERVED_NAMES:
            raise TypeError("You cannot request one of the hydraulic variables or reserved sympy names")
        try:
            return self._variables[name]
        except KeyError as e:
            raise KeyError("There is no such variable: {}. Remember that variables are case sensitive".format(name)) from e

    def get_reaction(self, loc, typ, species) -> "RxnExpression":
        """_summary_

        Parameters
        ----------
        loc : str or RxnLocation
            the location (pipe or tank) the reaction occurs
        typ : str or ExprType
            the type of reaction to get
        species : str or RxnSpecies
            the species to get the reaction for

        Returns
        -------
        RxnExpression
            the reaction expression object

        Raises
        ------
        TypeError
            :param:`loc`, :param:`typ` or :param:`species` is ``None``
        ValueError
            - :param:`loc` or :param:`typ` is incorrect/invalid
            - :param:`species` is undefined
        KeyError
            - the requested reaction expression is undefined
        """
        if species is not None:
            species = str(species)
        if not species or species not in self._variables.keys():
            raise TypeError("A valid name must be specified for species, but got {}".format(species))
        if not loc:
            raise TypeError("A valid RxnLocation must be specified for loc, but got {}".format(repr(loc)))
        if not typ:
            raise TypeError("A valid ExprType must be specified for typ, got {}".format(repr(typ)))
        if species not in self._variables.keys():
            raise ValueError('Unknown species, {}'.format(species))
        if isinstance(loc, str) and len(loc) > 0:
            loc = loc[0].upper()
            try:
                loc = RxnLocation[loc]
            except KeyError as k:
                raise ValueError("Missing/unknown value for loc, expected RxnLocation but got {}".format(loc)) from k
        if isinstance(typ, str) and len(typ) > 0:
            typ = typ[0].upper()
            try:
                typ = ExprType[typ]
            except KeyError as k:
                raise ValueError("Missing/unknown value for typ, expected ExprType but got {}".format(typ)) from k
        if loc is RxnLocation.Pipes:
            return self._pipe_reactions[(typ.name, species)]
        elif loc is RxnLocation.Tanks:
            return self._tank_reactions[(typ.name, species)]
        else:
            raise ValueError("Invalid RxnLocation specified, got {}".format(loc))

    def get_reactions(self, loc: Union[str, RxnLocation] = None, typ: Union[str, ExprType] = None, species: Union[str, "RxnSpecies"] = None) -> List["RxnExpression"]:
        """Get a subset of all reactions based on the criteria specified in the parameters (ANDed).

        Parameters
        ----------
        loc : str or RxnLocation, optional
            limit to pipe or tank reactions, by default None (both pipes and tanks)
        typ : str or ExprType, optional
            limit to rate, formula, or equilibrium reactions, by default None (all types)
        species : str or RxnSpecies, optional
            limit to a specific species, by default Non (all species)

        Returns
        -------
        list of RxnExpression
            reactions that match all the criteria specified

        Raises
        ------
        ValueError
            - invalid string passed in for :param:`loc`
            - invalid string passed in for :param:`typ`
        """
        if isinstance(loc, str) and len(loc) > 0:
            loc = loc[0].upper()
            try:
                loc = RxnLocation[loc]
            except KeyError as k:
                raise ValueError("Missing/unknown value for loc, expected RxnLocation but got {}".format(loc)) from k
        if isinstance(typ, str) and len(typ) > 0:
            typ = typ[0].upper()
            try:
                typ = ExprType[typ]
            except KeyError as k:
                raise ValueError("Missing/unknown value for typ, expected ExprType but got {}".format(typ)) from k
        if species is not None:
            species = str(species)
        reactions = list()
        if loc is None or loc == RxnLocation.Pipes:
            for k, v in self._pipe_reactions.items():
                if (k[0] == typ or typ is None) and (k[1] == species or species is None):
                    reactions.append(v)
        if loc is None or loc == RxnLocation.Tanks:
            for k, v in self._tank_reactions.items():
                if (k[0] == typ or typ is None) and (k[1] == species or species is None):
                    reactions.append(v)
        return reactions


@dataclass
class RxnVariable:
    """Any variable defined for use in a reaction expression"""

    name: str
    """The name (symbol) of the variable"""
    typ: ClassVar[VarType]
    """The type of variable"""
    value: ClassVar[Union[str, float]]
    """The value of the variable, with type dependent on the type of variable"""
    note = None
    """A comment or note attached to the variable"""

    @property
    def variable_type(self) -> VarType:
        """The type of variable"""
        return self.typ

    def get_symbol(self) -> sympy.Symbol:
        """Get a sympy Symbol from the name"""
        return symbols(self.name)

    def get_value(self, *, pipe=None, tank=None) -> Union[float, str]:
        """Get the unit for a species, the value of a constant or parameter, or an expression for a term.

        Parameters
        ----------
        pipe : str or Pipe, optional
            a pipe or pipe name to use when getting the value, by default None
        tank : str or Tank, optional
            a tank or tank name to use when getting the value, by default None

        Returns
        -------
        float or str
            a float or string, depending on the type

        Raises
        ------
        NotImplementedError
            if a subclass does not implement this function
        """
        raise NotImplementedError

    def __post_init__(self):
        if self.name in WaterQualityReactionsModel.RESERVED_NAMES:
            raise ValueError("the name {} is reserved for a built-in hydraulic variable".format(self.name))
        if not hasattr(self, 'typ'):
            raise NotImplementedError('RxnVariable class cannot be instantiated directly')
        if not isinstance(self.typ, VarType):
            raise ValueError("expected VarType, got {}".format(type(self.typ)))
        if self.typ is VarType.Species or self.typ is VarType.Coeff:
            raise ValueError("generic {} type is inappropriate".format(self.typ))

    def _get_tolerances(self) -> str:
        return ""

    def to_msx_string(self) -> str:
        """Convert to an EPANET-MSX input-file formatted line.

        Returns
        -------
        str
            the EPANET_MSX input-file formatted text

        Raises
        ------
        TypeError
            if the type is improper
        """
        if self.typ & VarType.Species:
            return "{} {} {} {} ;{}".format(self.typ.name.upper(), self.name, self.value, self._get_tolerances(), self.note if self.note else "")
        elif self.typ & VarType.Coeff:
            return "{} {} {} ;{}".format(self.typ.name.upper(), self.name, self.value, self.note if self.note else "")
        elif self.typ & VarType.Term:
            return "{} {} ;{}".format(self.name, self.value, self.note if self.note else "")
        raise TypeError("typ must be a VarType but got {} - how did you do that???".format(type(self.typ)))

    def __str__(self):
        return self.name


@dataclass
class RxnSpecies(RxnVariable):
    """A water quality species, either biologic or chemical."""

    unit: str
    """The unit for this species' concentration"""
    Atol: float = None
    """The absolute tolerance to use when solving equations for this species"""
    Rtol: float = None
    """The relative tolerance to use when solving equations for this species"""
    note: str = None
    """A note regarding the species"""

    @property
    def species_type(self) -> VarType:
        """The type of species"""
        raise NotImplementedError("subclass of RxnSpecies failed to implement species_type property")

    typ = species_type

    def __post_init__(self):
        super().__post_init__()
        if not (self.typ & VarType.Species):
            raise ValueError("species must be Bulk or Wall type")
        if (self.Atol is not None and self.Rtol is None) or (self.Atol is None and self.Rtol is not None):
            raise ValueError("Atol and Rtol must both be None or both be > 0")

    @property
    def _value(self):
        return self.unit

    value = _value

    def get_value(self) -> str:
        """Get the unit of the reaction species."""
        return self.value

    def _get_tolerances(self) -> str:
        if self.Atol is not None:
            return "{} {}".format(self.Atol, self.Rtol)
        return ""

    def get_tolerances(self) -> Union[Tuple[float, float], None]:
        """Get the tolerances for the species equations.

        Returns
        -------
        (float, float) or None
            the absolute and relative tolerance
        """
        if self.Atol is not None:
            return (self.Atol, self.Rtol,)
        return None

    def set_tolerances(self, Atol: float, Rtol: float):
        """Set the absolute and relative tolerances for the solver for this species.

        Parameters
        ----------
        Atol : float
            absolute tolerance for the solver
        Rtol : float
            relative tolerance for the solver

        Raises
        ------
        ValueError
            if either tolerance is less than or equal to zero
        ValueError
            if only one tolerance is set
        """
        try:
            if Atol is None and Rtol is None:
                self.clear_tolerances()
            elif Atol > 0 and Rtol > 0:
                self.Atol = Atol
                self.Rtol = Rtol
            else:
                raise ValueError("both Atol and Rtol must be greater than 0")
        except TypeError as e:
            raise TypeError("Atol and Rtol must both be None or both be positive real numbers") from e

    def clear_tolerances(self):
        """Clear custom tolerances for the species"""
        self.Atol = self.Rtol = None


class BulkSpecies(RxnSpecies):
    """A bulk-reaction species"""

    @property
    def species_type(self):
        return VarType.Bulk

    typ = species_type


class WallSpecies(RxnSpecies):
    """A wall-reaction species"""

    @property
    def species_type(self):
        return VarType.Wall

    typ = species_type


@dataclass
class RxnCoefficient(RxnVariable):
    """A coefficient used in terms or reaction expressions"""

    global_value: float
    """The global (default) value for this coefficient"""
    note: str = None
    """A note regarding this coefficient"""
    pipe_values: Dict[str, float] = field(default_factory=dict, repr=False)
    """Values for specific pipes"""
    tank_values: Dict[str, float] = field(default_factory=dict, repr=False)
    """Values for specific tanks"""

    @property
    def coeff_type(self) -> VarType:
        """The coefficient type, either constant or parameter.

        Returns
        -------
        VarType
            the type of coefficient

        Raises
        ------
        NotImplementedError
            if a subclass failed to overload this property
        """
        raise NotImplementedError("subclass of RxnCoefficient failed to implement coeff_type property")

    typ = coeff_type

    @property
    def _value(self):
        return self.global_value

    value = _value

    def __post_init__(self):
        super().__post_init__()
        if not (self.typ & VarType.Coeff):
            raise ValueError("coefficients must be Constant or Parameter type")
        try:
            self.global_value = float(self.global_value)
        except ValueError as e:
            raise ValueError("coefficients must have a real value but got {}".format(self.global_value)) from e

    def get_value(self, *, pipe=None, tank=None) -> str:
        if pipe is not None and tank is not None:
            raise ValueError("coefficients cannot have both pipe and tank specified")
        if self.typ & VarType.Constant:
            if pipe is not None or tank is not None:
                warnings.warn('constants only have global values, returning the global value', RuntimeWarning)
            return self.global_value
        if pipe is not None:
            return self.pipe_values.get(str(pipe), self.global_value)
        else:
            return self.tank_values.get(str(tank), self.global_value)


class Constant(RxnCoefficient):
    """A constant coefficient"""

    def __post_init__(self):
        if len(self.pipe_values) > 0 or len(self.tank_values) > 0:
            warnings.warn('A Constant cannot have different values for specific pipes or tanks', category=RuntimeWarning)
        self.pipe_values = None
        self.tank_values = None
        super().__post_init__()
        
    @property
    def coeff_type(self):
        return VarType.Constant

    typ = coeff_type


class Parameter(RxnCoefficient):
    """A coefficient that has different values based on a pipe or tank"""

    @property
    def coeff_type(self):
        return VarType.Parameter

    typ = coeff_type


@dataclass
class RxnTerm(RxnVariable):
    """An alias for a subexpression for easier use in a reaction expression"""

    expression: str
    """A subexpression using species and coefficients"""
    note: str = None
    """A note or comment about this term"""

    @property
    def variable_type(self):
        return VarType.Term

    typ = variable_type

    @property
    def _value(self):
        return self.expression

    value = _value


@dataclass
class RxnExpression:
    """A reaction expression"""

    species: str
    """The species the expression applies to"""
    loc: RxnLocation
    """Does this reaction occur in pipes or tanks"""
    typ: ClassVar[ExprType]
    """The left-hand-side of the equation (the type of equation)"""
    expression: str
    """The right-hand-side of the equation (the expression itself)"""
    note: str = None
    """A note or comment regarding this expression"""
    _variables: WaterQualityReactionsModel = None
    """A link to the variable registry for evaluation"""
    _transformations: ClassVar[Tuple] = standard_transformations + (convert_xor,)
    """Expression transformations"""

    def link_variables(self, variables: WaterQualityReactionsModel):
        if variables is not None:
            self._variables = variables
        self.validate()

    def validate(self):
        """Validate the expression by checking variables are defined.

        Returns
        -------
        sympy expression
            _description_

        Raises
        ------
        ValueError
            _description_
        RuntimeError
            _description_
        """
        if self._variables is None:
            raise ValueError("No variables have been linked to this RxnExpression")
        expr = sympy.parse_expr(self.expression, transformations=self._transformations)
        expr_vars = expr.free_symbols
        missing = expr_vars - self._variables.all_symbols
        if len(missing) > 0:
            raise RuntimeError("Validation failed: the following symbols are undefined: {}".format(missing))
        return expr

    @property
    def expression_type(self) -> ExprType:
        """The type of expression"""
        raise NotImplementedError("subclass of RxnExpression does not define the expression type")

    def to_msx_string(self) -> str:
        """Get the expression as an EPANET-MSX input-file style string.

        Returns
        -------
        str
            the expression for use in an EPANET-MSX input file
        """
        return "{} {} {} ;{}".format(self.typ.name.upper(), self.species, self.expression, self.note if self.note else "")


class Equilibrium(RxnExpression):
    """An equilibrium expression, where the evaluated expression should equal 0."""

    @property
    def expression_type(self):
        return ExprType.Equil

    typ = expression_type


class Rate(RxnExpression):
    """A decay rate reaction, where the expression is the change in concentration per time for a specific species."""

    @property
    def expression_type(self):
        return ExprType.Rate

    typ = expression_type


class Formula(RxnExpression):
    """A formula for the concentration of a species based solely on the values of the other species."""

    @property
    def expression_type(self):
        return ExprType.Formula

    typ = expression_type
