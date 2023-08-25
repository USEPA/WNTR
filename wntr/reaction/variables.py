import enum
import logging
from dataclasses import InitVar, asdict, dataclass, field
from enum import Enum, IntFlag
from typing import Any, ClassVar, Dict, List, Set, Tuple, Union

import sympy
from sympy import Float, Function, Symbol, init_printing, symbols
from sympy.parsing import parse_expr
from sympy.parsing.sympy_parser import convert_xor, standard_transformations

from wntr.network.model import WaterNetworkModel

from .base import ExpressionMixin, LinkedVariablesMixin, VariableRegistry, ReactionVariable, RxnVarType, RESERVED_NAMES

logger = logging.getLogger(__name__)


@dataclass(repr=False)
class Species(LinkedVariablesMixin, ReactionVariable):

    unit: str
    atol: InitVar[float] = None
    rtol: InitVar[float] = None
    note: str = None
    variable_registry: InitVar[VariableRegistry] = None

    def __post_init__(self, atol=None, rtol=None, reaction_model=None):
        if isinstance(atol, property): atol=None
        if isinstance(rtol, property): rtol=None
        if self.name in RESERVED_NAMES:
            raise ValueError('Name cannot be a reserved name')
        if (atol is None) ^ (rtol is None):
            raise TypeError('atol and rtol must be the same type, got {} and {}'.format(atol, rtol))
        self._atol = atol
        self._rtol = rtol
        self._variable_registry = reaction_model

    @property
    def atol(self) -> float:
        return self._atol
    
    @property
    def rtol(self) -> float:
        return self._rtol

    def get_tolerances(self) -> Union[Tuple[float, float], None]:
        if self._atol is not None and self._rtol is not None:
            return (self._atol, self._rtol)
        return None

    def set_tolerances(self, atol: float, rtol: float):
        if atol is None and rtol is None:
            self._atol = self._rtol = None
            return
        try:
            if not isinstance(atol, float):
                atol = float(atol)
            if not isinstance(rtol, float):
                rtol = float(rtol)
        except Exception as e:
            raise TypeError('atol and rtol must be the same type, got {} and {}'.format(atol, rtol))
        if atol <= 0:
            raise ValueError("Absolute tolerance atol must be greater than 0")
        if rtol <= 0:
            raise ValueError("Relative tolerance rtol must be greater than 0")
        self._atol = atol
        self._rtol = rtol

    def clear_tolerances(self):
        self._atol = self._rtol = None

    def to_msx_string(self) -> str:
        tols = self.get_tolerances()
        if tols is None:
            # tolstr = "{:<12s} {:<12s}".format("", "")
            tolstr = ''
        else:
            #tolstr = "{:12.6g} {:12.6g}".format(*tols)
            tolstr = "{} {}".format(*tols)
        # return "{:<4s} {:<32s} {:s} {:s} ;{:s}".format(
        return "{:s} {:s} {:s} {:s} ;{:s}".format(
            self.var_type.name.upper(),
            self.name,
            self.unit,
            tolstr,
            self.note if self.note is not None else "",
        )

    def __repr__(self):
        return "{}(name={}, unit={}, atol={}, rtol={}, note={})".format(
            self.__class__.__name__, repr(self.name), repr(self.unit), self.atol, self.rtol, repr(self.note)
        )


@dataclass(repr=False)
class BulkSpecies(Species):
    @property
    def var_type(self) -> RxnVarType:
        return RxnVarType.BULK


@dataclass(repr=False)
class WallSpecies(Species):
    @property
    def var_type(self) -> RxnVarType:
        return RxnVarType.WALL


@dataclass(repr=False)
class Coefficient(LinkedVariablesMixin, ReactionVariable):

    global_value: float
    note: str = None
    unit: str = None
    variable_registry: InitVar[VariableRegistry] = None

    def __post_init__(self, reaction_model):
        if self.name in RESERVED_NAMES:
            raise ValueError('Name cannot be a reserved name')
        self._variable_registry = reaction_model

    def get_value(self) -> float:
        return self.global_value

    def to_msx_string(self) -> str:
        # return "{:<6s} {:<32s} {:g};{:s}".format(
        return "{:s} {:s} {} ;{:s}".format(
            self.var_type.name.upper(),
            self.name,
            self.global_value,
            self.note if self.note is not None else "",
        )

    def __repr__(self):
        return "{}(name={}, global_value={}, unit={}, note={})".format(self.__class__.__name__, repr(self.name), repr(self.global_value), repr(self.unit), repr(self.note))


@dataclass(repr=False)
class Constant(Coefficient):
    @property
    def var_type(self) -> RxnVarType:
        return RxnVarType.CONST


@dataclass(repr=False)
class Parameter(Coefficient):

    _pipe_values: Dict[str, float] = field(default_factory=dict)
    _tank_values: Dict[str, float] = field(default_factory=dict)

    @property
    def var_type(self) -> RxnVarType:
        return RxnVarType.PARAM

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


@dataclass(repr=False)
class NamedExpression(LinkedVariablesMixin, ExpressionMixin, ReactionVariable):

    note: str = None
    variable_registry: InitVar[VariableRegistry] = field(default=None, compare=False)

    def __post_init__(self, reaction_model):
        if self.name in RESERVED_NAMES:
            raise ValueError('Name cannot be a reserved name')
        self._variable_registry = reaction_model

    @property
    def var_type(self) -> RxnVarType:
        return RxnVarType.TERM

    def sympify(self):
        raise NotImplementedError

    def to_msx_string(self) -> str:
        return "{:s} {:s} ;{:s}".format(self.name, self.expression, self.note if self.note is not None else "")

    def __repr__(self):
        return "{}(name={}, expression={}, note={})".format(self.__class__.__name__, repr(self.name), repr(self.expression), repr(self.note))


Term = NamedExpression


class InternalVariable(ReactionVariable):

    @property
    def var_type(self) -> RxnVarType:
        return RxnVarType.INTERNAL

    def to_msx_string(self) -> str:
        raise TypeError("InternalVariable is not output to an MSX input file")

    def __repr__(self):
        return "{}(name={})".format(self.__class__.__name__, repr(self.name))
