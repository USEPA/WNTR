# -*- coding: utf-8 -*-

"""Water quality model implementations.
"""


import logging

from typing import (
    Any,
    Callable,
    Dict,
    Literal,
    Tuple,
    Union,
)

from wntr.epanet.util import ENcomment
from wntr.utils.disjoint_mapping import KeyExistsError

from .base import (
    VariableValues,
    AbstractReaction,
    ReactionSystem,
    AbstractVariable,
    ExpressionType,
    ReactionType,
    VariableType,
    SpeciesType,
)

has_sympy = False
try:
    from sympy import Float, Symbol, init_printing, symbols
    from sympy.parsing import parse_expr
    from sympy.parsing.sympy_parser import convert_xor, standard_transformations

    has_sympy = True
except ImportError:
    sympy = None
    logging.critical("This python installation does not have SymPy installed. " "Certain functionality will be disabled.")
    standard_transformations = (None,)
    convert_xor = None
    has_sympy = False


logger = logging.getLogger(__name__)

__all__ = [
    'Species',
    'Constant',
    'Parameter',
    'Term',
    'ReservedName',
    'HydraulicVariable',
    'MathFunction',
    'Reaction'
]


class Species(AbstractVariable):
    """A biological or chemical species that impacts water quality.

    .. rubric:: Attributes

    .. autosummary::

        ~Species.name
        ~Species.species_type
        ~Species.units
        ~Species.note
        ~Species.diffusivity

    .. rubric:: Methods

    .. autosummary::

        ~Species.set_tolerances
        ~Species.get_tolerances
        ~Species.clear_tolerances
        ~Species.to_dict

    .. rubric:: Read-only Attributes

    .. autosummary::

        ~Species.atol
        ~Species.rtol
        ~Species.initial_quality
        ~Species.pipe_reaction
        ~Species.tank_reaction

    """

    def __init__(
        self,
        name: str,
        species_type: Union[SpeciesType, str],
        units: str,
        atol: float = None,
        rtol: float = None,
        *,
        note: Union[str, dict, ENcomment]=None,
        diffusivity: float = None,
        _vars: ReactionSystem = None,
        _vals: VariableValues = None,
    ) -> None:
        """A biological or chemical species.

        Parameters
        ----------
        name : str
            The species name
        species_type : SpeciesType or str
            The species type
        units : str
            The units of mass for this species, see :attr:`units` property.
        atol : float, optional, requires rtol
            The absolute tolerance when solving this species' equations, by default None
        rtol : float, optional, requires atol
            The relative tolerance when solving this species' equations, by default None
        note : str or dict or ENcomment, optional
            Supplementary information regarding this variable, by default None
        diffusivity : float, optional
            Diffusivity of the species in water, by default None

        Other Parameters
        ----------------
        _vars : MsxReactionSystem, optional
            the reaction system this species is a part of, by default None
        _vals : InitialQuality, optional
            the initial quality values for this species, by default None

        Raises
        ------
        KeyExistsError
            if the name has already been used
        TypeError
            if a tank reaction is provided for a wall species
        """
        super().__init__(name, note=note)
        if _vars is not None and not isinstance(_vars, ReactionSystem):
            raise TypeError("Invalid type for _vars, {}".format(type(_vars)))
        if _vals is not None and not isinstance(_vals, InitialQuality):
            raise TypeError("Invalid type for _vals, {}".format(type(_vals)))
        if _vars is not None and name in _vars:
            raise KeyExistsError("This variable name is already taken")
        species_type = SpeciesType.get(species_type)
        if species_type is None:
            raise TypeError("species_type cannot be None")
        self._species_type = species_type
        self._tolerances = None
        self.set_tolerances(atol, rtol)
        self.units: str = units
        """The units of mass for this species. 
        For bulk species, concentration is this unit divided by liters, for wall species, concentration is this unit
        divided by the model's area-unit (see options).
        """
        self.diffusivity: float = diffusivity
        """The diffusivity of this species in water, if being used, by default None"""
        self._vars = _vars
        self._vals = _vals

    def set_tolerances(self, atol: float, rtol: float):
        """Set the absolute and relative tolerance for the solvers.

        The user must set both values, or neither value (None). Values must be
        positive.

        Parameters
        ----------
        atol : float
            The absolute tolerance to use
        rtol : float
            The relative tolerance to use

        Raises
        ------
        TypeError
            if only one of `atol` or `rtol` is a float
        ValueError
            if either value is less-than-or-equal-to zero
        """
        if (self.atol is None) ^ (self.rtol is None):
            raise TypeError("atol and rtol must both be float or both be None")
        if self.atol is None:
            self._tolerances = None
        elif atol <= 0 or rtol <= 0:
            raise ValueError("atol and rtol must both be positive, got atol={}, rtol={}".format(atol, rtol))
        else:
            self._tolerances = (atol, rtol)

    def get_tolerances(self) -> Union[Tuple[float, float], None]:
        """Get the custom solver tolerances for this species.

        Returns
        -------
        Union[Tuple[float, float], None]
            absolute and relative tolerances, respectively, if they are set
        """
        return self._tolerances

    def clear_tolerances(self):
        """Set both tolerances to None, reverting to the global options value."""
        self._tolerances = None

    @property
    def atol(self) -> float:
        """The absolute tolerance. Must be set using :meth:`set_tolerances`"""
        if self._tolerances is not None:
            return self._tolerances[0]
        return None

    @property
    def rtol(self) -> float:
        """The relative tolerance. Must be set using :meth:`set_tolerances`"""
        if self._tolerances is not None:
            return self._tolerances[1]
        return None

    @property
    def var_type(self) -> VariableType:
        """This is a species"""
        return VariableType.SPECIES

    @property
    def species_type(self) -> SpeciesType:
        """The type of species"""
        return self._species_type

    @property
    def initial_quality(self):
        """If a specific network has been linked, then the initial quality values for the network"""
        if self._vals is not None:
            return self._vals
        else:
            raise TypeError("This species is not linked to a NetworkData obejct, please `relink` your model")

    @property
    def pipe_reaction(self):
        if self._vars is not None:
            return self._vars.pipe_reactions[self.name]
        else:
            raise AttributeError('This species is not connected to a ReactionSystem')

    @property
    def tank_reaction(self):
        if self._vars is not None:
            return self._vars.tank_reactions[self.name]
        else:
            raise AttributeError('This species is not connected to a ReactionSystem')

    def to_dict(self) -> Dict[str, Any]:
        """Create a dictionary representation of the object

        The species dictionary has the following format, as described using a json schema.

        .. code:: json

            {
                "title": "Species",
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "species_type": {
                        "enum": ["bulk", "wall"]
                    },
                    "units": {
                        "type": "string"
                    },
                    "atol": {
                        "type": "number",
                        "exclusiveMinimum": 0
                    },
                    "rtol": {
                        "type": "number",
                        "exclusiveMinimum": 0
                    },
                    "note": {
                        "type": "string"
                    },
                    "diffusivity": {
                        "type": "number",
                        "minimum": 0
                    }
                },
                "required": ["name", "species_type", "units", "pipe_reaction", "tank_reaction"],
                "dependentRequired": {"atol": ["rtol"], "rtol":["atol"]}
            }

        """
        ret = dict(
            name=self.name, species_type=self.species_type.name.lower(), units=self.units, atol=self.atol, rtol=self.rtol
        )

        if self.diffusivity:
            ret["diffusivity"] = self.diffusivity

        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note

        return ret


class Constant(AbstractVariable):
    """A constant coefficient for use in reaction expressions."""

    def __init__(self, name: str, value: float, *, units: str = None, note: Union[str, dict, ENcomment]=None, _vars: ReactionSystem = None) -> None:
        """A variable representing a constant value.

        Parameters
        ----------
        name : str
            The name of the variable.
        value : float
            The constant value.
        units : str, optional
            Units for the variable, by default None
        note : str or dict or ENcomment, optional
            Supplementary information regarding this variable, by default None

        Other Parameters
        ----------------
        _vars : MsxReactionSystem, optional
            the reaction system this constant is a part of, by default None
        """
        super().__init__(name, note=note)
        if _vars is not None and not isinstance(_vars, ReactionSystem):
            raise TypeError("Invalid type for _vars, {}".format(type(_vars)))
        if _vars is not None and name in _vars:
            raise KeyExistsError("This variable name is already taken")
        self.value = float(value)
        """The value of the constant"""
        self.units = units
        """The units of the constant"""
        self._vars = _vars

    def __call__(self, *, t=None) -> Any:
        return self.value

    @property
    def var_type(self) -> VariableType:
        """This is a constant coefficient."""
        return VariableType.CONSTANT

    def to_dict(self) -> Dict[str, Any]:
        ret = dict(name=self.name, value=self.value)
        if self.units:
            ret["units"] = self.units
        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note
        return ret


class Parameter(AbstractVariable):
    """A coefficient that is parameterized by pipe/tank."""

    def __init__(self, name: str, global_value: float, *, units: str = None, note: Union[str, dict, ENcomment]=None, _vars: ReactionSystem = None, _vals: VariableValues=None) -> None:
        """A parameterized variable for use in expressions.

        Parameters
        ----------
        name : str
            The name of this parameter.
        global_value : float
            The global value for the parameter if otherwise unspecified.
        units : str, optional
            The units for this parameter, by default None
        note : str or dict or ENcomment, optional
            Supplementary information regarding this variable, by default None

        Other Parameters
        ----------------
        _vars : MsxReactionSystem, optional
            the reaction system this parameter is a part of, by default None
        _vals : ParameterValues, optional
            the netork-specific values for this parameter, by default None
        """
        super().__init__(name, note=note)
        if _vars is not None and not isinstance(_vars, ReactionSystem):
            raise TypeError("Invalid type for _vars, {}".format(type(_vars)))
        if _vals is not None and not isinstance(_vals, ParameterValues):
            raise TypeError("Invalid type for _vals, {}".format(type(_vals)))
        if _vars is not None and name in _vars:
            raise KeyExistsError("This variable name is already taken")
        self.global_value = float(global_value)
        self.units = units
        self._vars = _vars
        self._vals = _vals

    def __call__(self, *, t=None, pipe: float = None, tank: float = None) -> Any:
        if pipe is not None and tank is not None:
            raise TypeError("Both pipe and tank cannot be specified at the same time")
        elif self._vals is None and (pipe is not None or tank is not None):
            raise ValueError("No link provided to network-specific parameter values")
        if pipe:
            return self._vals.pipe_values.get(pipe, self.global_value)
        elif tank:
            return self._vals.tank_values.get(pipe, self.global_value)
        return self.global_value

    @property
    def var_type(self) -> VariableType:
        """This is a parameterized coefficient."""
        return VariableType.PARAMETER

    def to_dict(self) -> Dict[str, Any]:
        ret = dict(name=self.name, global_value=self.global_value)
        if self.units:
            ret["units"] = self.units
        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note
        return ret


class Term(AbstractVariable):
    def __init__(self, name: str, expression: str, *, note: Union[str, dict, ENcomment]=None, _vars: ReactionSystem = None) -> None:
        """A named expression that can be used as a term in other expressions.

        Parameters
        ----------
        name : str
            The variable name.
        expression : str
            The mathematical expression to be aliased
        note : str or dict or ENcomment, optional
            Supplementary information regarding this variable, by default None

        Other Parameters
        ----------------
        _vars : MsxReactionSystem, optional
            the reaction system this species is a part of, by default None
        """
        super().__init__(name, note=note)
        if _vars is not None and not isinstance(_vars, ReactionSystem):
            raise TypeError("Invalid type for _vars, {}".format(type(_vars)))
        if _vars is not None and name in _vars:
            raise KeyExistsError("This variable name is already taken")
        self.expression = expression
        """The expression that is aliased by this term"""
        self._vars = _vars

    @property
    def var_type(self) -> VariableType:
        """This is a term (named expression)."""
        return VariableType.TERM

    def to_dict(self) -> Dict[str, Any]:
        ret = dict(name=self.name, expression=self.expression)
        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note
        return ret


class ReservedName(AbstractVariable):
    def __init__(self, name: str, *, note: Union[str, dict, ENcomment]=None) -> None:
        """An object representing a reserved name that should not be used by the user.

        Parameters
        ----------
        name : str
            The reserved name.
        note : str or dict or ENcomment, optional
            Supplementary information regarding this variable, by default None

        Other Parameters
        ----------------
        _vars : MsxReactionSystem, optional
            the reaction system this species is a part of, by default None

        Raises
        ------
        KeyExistsError
            _description_
        """
        self.name = name
        self.note = note

    @property
    def var_type(self) -> VariableType:
        """Variable name is a reserved word in MSX"""
        return VariableType.RESERVED

    def to_dict(self) -> Dict[str, Any]:
        return '{}({})'.format(self.__class__.__name__, ', '.join(['name={}'.format(repr(self.name)), 'note={}'.format(repr(self.note))]))


class HydraulicVariable(ReservedName):
    """A variable representing instantaneous hydraulics data."""

    def __init__(self, name: str, units: str = None, *, note: Union[str, dict, ENcomment]=None) -> None:
        """A variable representing instantaneous hydraulics data.

        The user should not need to create any variables using this class, they
        are created automatically by the MultispeciesModel object during initialization.

        Parameters
        ----------
        name : str
            The name of the variable (predefined by MSX)
        units : str, optional
            The units for hydraulic variable, by default None
        note : str or dict or ENcomment, optional
            Supplementary information regarding this variable, by default None
        """
        super().__init__(name, note=note)
        self.units = units
        """The hydraulic variable's units"""


class MathFunction(ReservedName):
    """A variable that is actually a mathematical function defined by MSX."""

    def __init__(self, name: str, func: Callable, *, note: Union[str, dict, ENcomment]=None) -> None:
        """A variable that is actually a mathematical function defined by MSX.

        Parameters
        ----------
        name : str
            The function name
        func : Callable
            The callable function
        note : str or dict or ENcomment, optional
            Supplementary information regarding this variable, by default None
        """
        super().__init__(name, note=note)
        self.func = func
        """A callable function or SymPy function"""

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.func(*args, **kwds)


class Reaction(AbstractReaction):
    """A water quality biochemical reaction dynamics definition for a specific species."""

    def __init__(
        self, species_name: str, reaction_type: ReactionType, expression_type: ExpressionType, expression: str, *, note: Union[str, dict, ENcomment]=None, _vars: ReactionSystem = None
    ) -> None:
        """A water quality biochemical reaction dynamics definition for a specific species.

        Parameters
        ----------
        species_name : str
            The species (object or name) this reaction is applicable to.
        reaction_type : ReactionType
            The type of reaction, either PIPE or TANK
        expression_type : ExpressionType
            The type of reaction dynamics being described by the expression: one of RATE, FORMULA, or EQUIL.
        expression : str
            The mathematical expression for the right-hand-side of the reaction equation.
        note : str or dict or ENcomment, optional
            Supplementary information regarding this variable, by default None
        
        Other Parameters
        ----------------
        _vars : MsxReactionSystem, optional
            the reaction system this species is a part of, by default None
        """
        super().__init__(species_name=species_name, note=note)
        if _vars is not None and not isinstance(_vars, ReactionSystem):
            raise TypeError("Invalid type for _vars, {}".format(type(_vars)))
        expression_type = ExpressionType.get(expression_type)
        reaction_type = ReactionType.get(reaction_type)
        if reaction_type is None:
            raise TypeError("Required argument reaction_type cannot be None")
        if expression_type is None:
            raise TypeError("Required argument expression_type cannot be None")
        self.__rxn_type = reaction_type
        self._expr_type = expression_type
        if not expression:
            raise TypeError("expression cannot be None")
        self.expression = expression
        """The mathematical expression (right-hand-side)"""
        self._vars = _vars

    @property
    def expression_type(self) -> ExpressionType:
        """The type of dynamics being described: RATE, EQUIL or FORMULA"""
        return self._expr_type

    @property
    def reaction_type(self) -> ReactionType:
        """The type (i.e., location) of reaction: will be PIPE or TANK"""
        return self.__rxn_type

    def to_dict(self) -> dict:
        ret = dict(
            species_name=str(self.species_name), expression_type=self.expression_type.name.lower(), expression=self.expression
        )
        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note
        return ret


class InitialQuality(VariableValues):
    """A container for initial quality values for a species in a specific network."""

    def __init__(self, global_value: float = 0.0, node_values: dict = None, link_values: dict = None):
        """The initial quality values for a species.

        Arguments
        ---------
        global_value : float, optional
            _description_, by default 0.0
        node_values : dict[str, float], optional
            _description_, by default None
        link_values : dict[str, float], optional
            _description_, by default None
        """
        self.global_value = global_value
        """The global initial quality for this species. 
        
        Will be set to 0.0 when not explicitly specified, and can be overridden for
        specific nodes and links using the other members of this class."""
        self._node_values = node_values if node_values is not None else dict()
        self._link_values = link_values if link_values is not None else dict()

    def __repr__(self) -> str:
        return self.__class__.__name__ + "(global_value={}, node_values=<{} entries>, link_values=<{} entries>)".format(
            self.global_value, len(self._node_values), len(self._link_values)
        )

    @property
    def var_type(self) -> VariableType:
        """This is data for a species"""
        return VariableType.SPECIES

    @property
    def node_values(self) -> Dict[str, float]:
        """A mapping that overrides the global_value of the initial quality at specific nodes"""
        return self._node_values

    @property
    def link_values(self) -> Dict[str, float]:
        """A mapping that overrides the global_value of the initial quality in specific links"""
        return self._link_values

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return dict(global_value=self.global_value, node_values=self._node_values.copy(), link_values=self._link_values.copy())


class ParameterValues(VariableValues):
    """A container for pipe and tank specific values of a parameter for a specific network."""

    def __init__(self, *, pipe_values: dict = None, tank_values: dict = None) -> None:
        """The non-global values for a parameter.

        Arguments
        ---------
        pipe_values : dict, optional
            _description_, by default None
        tank_values : dict, optional
            _description_, by default None
        """
        self._pipe_values = pipe_values if pipe_values is not None else dict()
        self._tank_values = tank_values if tank_values is not None else dict()

    def __repr__(self) -> str:
        return self.__class__.__name__ + "(pipe_values=<{} entries>, tank_values=<{} entries>)".format(
            len(self._pipe_values), len(self._tank_values)
        )

    @property
    def var_type(self) -> VariableType:
        """This is data for a parameter"""
        return VariableType.PARAMETER

    @property
    def pipe_values(self) -> Dict[str, float]:
        """A mapping that overrides the global_value of a parameter for a specific pipe"""
        return self._pipe_values

    @property
    def tank_values(self) -> Dict[str, float]:
        """A mapping that overrides the global_value of a parameter for a specific tank"""
        return self._tank_values

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return dict(pipe_values=self._pipe_values.copy(), tank_values=self._tank_values.copy())

