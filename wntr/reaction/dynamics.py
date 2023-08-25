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
from wntr.reaction.base import RxnVarType

from .base import ExpressionMixin, LinkedVariablesMixin, RxnExprType, RxnLocType, VariableRegistry, ReactionDynamics, RxnVarType
from .variables import Coefficient, NamedExpression, Species

logger = logging.getLogger(__name__)


class MSXDefinedDynamicsMixin:
    def to_msx_string(self) -> str:
        """Get the expression as an EPANET-MSX input-file style string.

        Returns
        -------
        str
            the expression for use in an EPANET-MSX input file
        """
        return "{} {} {} ;{}".format(self.expr_type.name.upper(), str(self.species), self.expression, self.note if self.note else "")


@dataclass(repr=False)
class RateDynamics(MSXDefinedDynamicsMixin, LinkedVariablesMixin, ExpressionMixin, ReactionDynamics):
    note: str = None
    variable_registry: InitVar[VariableRegistry] = field(default=None, compare=False)

    def __post_init__(self, variable_registry):
        self._variable_registry = variable_registry

    @property
    def expr_type(self) -> RxnExprType:
        return RxnExprType.RATE

    def sympify(self):
        raise NotImplementedError


@dataclass(repr=False)
class EquilibriumDynamics(MSXDefinedDynamicsMixin, LinkedVariablesMixin, ExpressionMixin, ReactionDynamics):
    note: str = None
    variable_registry: InitVar[VariableRegistry] = field(default=None, compare=False)

    def __post_init__(self, variable_registry):
        self._variable_registry = variable_registry

    @property
    def expr_type(self) -> RxnExprType:
        return RxnExprType.EQUIL

    def sympify(self):
        raise NotImplementedError


@dataclass(repr=False)
class FormulaDynamics(MSXDefinedDynamicsMixin, LinkedVariablesMixin, ExpressionMixin, ReactionDynamics):
    note: str = None
    variable_registry: InitVar[VariableRegistry] = field(default=None, compare=False)

    def __post_init__(self, variable_registry):
        self._variable_registry = variable_registry

    @property
    def expr_type(self) -> RxnExprType:
        return RxnExprType.FORMULA

    def sympify(self):
        raise NotImplementedError
