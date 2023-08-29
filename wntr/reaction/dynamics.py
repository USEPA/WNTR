# -*- coding: utf-8 -*-

r"""
Classes for the species reactions used in reaction models.
Defines a reaction based on the type of reaction dynamics, e.g., equilibrium 
or rate-of-change. The dynamics, or ``expr_type`` determine the left-hand-side of a reaction
equation, while the ``expression`` provides the right-hand-side.

In other words, the ``expr_type``, ``species`` and ``expression`` attributes of all
reaction class objects can be read as:

.. math::

    expr\_type(species) = expression(vars,...).


For a ``RATE`` reaction, this equates to:

.. math::

    \frac{d}{dt}C(species) = f(vars,...)


The classes in this module can be created directly. However, they are more
powerful when either, a) created using API calls on a :class:`~wntr.reaction.model.WaterNetworkModel`,
or, b) linked to a :class:`~wntr.reaction.model.WaterNetworkModel` model object after creation.
This allows for expressions to be validated against the variables defined in the model.

If :class:`sympy` is installed, then there are functions available
that will convert object instances of these classes into sympy expressions
and symbols. If the instances are linked to a model, then expressions can 
be expanded, validated, and even evaluated or simplified symbolically.
"""
import enum
import logging
from dataclasses import InitVar, asdict, dataclass, field
from enum import Enum, IntFlag
from typing import Any, ClassVar, Dict, List, Set, Tuple, Union

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
from wntr.reaction.base import EXPR_TRANSFORMS, MSXObject, RxnVariableType

from .base import (
    ExpressionMixin,
    LinkedVariablesMixin,
    RxnDynamicsType,
    RxnLocationType,
    RxnModelRegistry,
    RxnReaction,
    RxnVariableType,
)
from .variables import Coefficient, Species, OtherTerm

logger = logging.getLogger(__name__)


@dataclass(repr=False)
class RateDynamics(MSXObject, LinkedVariablesMixin, ExpressionMixin, RxnReaction):
    r"""Used to supply the equation that expresses the rate of change of the given species
    with respect to time as a function of the other species in the model.

    .. math::

        \frac{d}{dt} C(species) = expression


    Parameters
    ----------
    species : str
        the name of the species whose reaction dynamics is being described
    location : RxnLocationType or str
        the location the reaction occurs (pipes or tanks)
    expression : str
        the expression for the reaction dynamics, which is the rate-of-change of the species concentration
    note : str, optional
        a note about this reaction
    variable_registry : RxnModelRegistry, optional
        a link to the remainder of the larger model
    """
    note: str = None
    """A note or comment about this species reaction dynamics"""
    variable_registry: InitVar[RxnModelRegistry] = field(default=None, compare=False)
    """A link to the reaction model with variables"""

    def __post_init__(self, variable_registry):
        self._variable_registry = variable_registry

    @property
    def expr_type(self) -> RxnDynamicsType:
        return RxnDynamicsType.RATE

    def to_symbolic(self, transformations=...):
        return super().to_symbolic(transformations)

    def to_msx_string(self) -> str:
        return "{} {} {} ;{}".format(self.expr_type.name.upper(), str(self.species), self.expression, self.note if self.note else "")

    def to_dict(self) -> dict:
        rep = dict(species=self.species, expr_type=self.expr_type.name.lower(), expression=self.expression)
        if self.note is not None:
            rep['note'] = self.note
        return rep



@dataclass(repr=False)
class EquilibriumDynamics(MSXObject, LinkedVariablesMixin, ExpressionMixin, RxnReaction):
    """Used for equilibrium expressions where it is assumed that the expression supplied is being equated to zero.

    .. math::

        0 = expression


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
    variable_registry : RxnModelRegistry, optional
        a link to the remainder of the larger model
    """

    note: str = None
    """A note or comment about this species reaction dynamics"""
    variable_registry: InitVar[RxnModelRegistry] = field(default=None, compare=False)
    """A link to the reaction model with variables"""

    def __post_init__(self, variable_registry):
        self._variable_registry = variable_registry

    @property
    def expr_type(self) -> RxnDynamicsType:
        return RxnDynamicsType.EQUIL

    def to_symbolic(self, transformations=...):
        return super().to_symbolic(transformations)

    def to_msx_string(self) -> str:
        return "{} {} {} ;{}".format(self.expr_type.name.upper(), str(self.species), self.expression, self.note if self.note else "")

    def to_dict(self) -> dict:
        rep = dict(species=self.species, expr_type=self.expr_type.name.lower(), expression=self.expression)
        if self.note is not None:
            rep['note'] = self.note
        return rep


@dataclass(repr=False)
class FormulaDynamics(MSXObject, LinkedVariablesMixin, ExpressionMixin, RxnReaction):
    """Used when the concentration of the named species is a simple function of the remaining species.

    .. math::

        C(species) = expression


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
    variable_registry : RxnModelRegistry, optional
        a link to the remainder of the larger model
    """

    note: str = None
    """A note or comment about this species reaction dynamics"""
    variable_registry: InitVar[RxnModelRegistry] = field(default=None, compare=False)
    """A link to the reaction model with variables"""

    def __post_init__(self, variable_registry):
        self._variable_registry = variable_registry

    @property
    def expr_type(self) -> RxnDynamicsType:
        return RxnDynamicsType.FORMULA

    def to_symbolic(self, transformations=...):
        return super().to_symbolic(transformations)

    def to_msx_string(self) -> str:
        return "{} {} {} ;{}".format(self.expr_type.name.upper(), str(self.species), self.expression, self.note if self.note else "")

    def to_dict(self) -> dict:
        rep = dict(species=self.species, expr_type=self.expr_type.name.lower(), expression=self.expression)
        if self.note is not None:
            rep['note'] = self.note
        return rep
