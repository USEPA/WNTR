# -*- coding: utf-8 -*-

"""Water quality model implementations.
"""


from abc import abstractproperty
import logging

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Tuple,
    Union,
)
import warnings


from wntr.epanet.util import ENcomment
from wntr.network.elements import Source
from wntr.network.model import PatternRegistry, SourceRegistry, WaterNetworkModel
from wntr.utils.disjoint_mapping import DisjointMapping, KeyExistsError

from .base import (
    WaterQualityReaction,
    WaterQualityReactionSystem,
    WaterQualityVariable,
    EXPR_TRANSFORMS,
    HYDRAULIC_VARIABLES,
    EXPR_FUNCTIONS,
    DynamicsType,
    ReactionType,
    QualityVarType,
    SpeciesType,
    AnnotatedFloat,
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
    logging.critical("This python installation does not have SymPy installed. " "Certain functionality will be disabled.")
    standard_transformations = (None,)
    convert_xor = None
    has_sympy = False


logger = logging.getLogger(__name__)

__all__ = [
    "Species",
    "Constant",
    "Parameter",
    "Term",
    "ReservedName",
    "HydraulicVariable",
    "MathFunction",
    "Reaction",
    "MultispeciesReactionSystem",
    "InitialQuality",
    "ParameterValues",
    "NetworkSpecificData",
    "MultispeciesQualityModel",
]


class Species(WaterQualityVariable):
    """A biological or chemical species that impacts water quality.
    
    Attributes
    ----------
    name : str
        The name of the species
    species_type : SpeciesType | str
        The type of species, either "bulk" or "wall"
    units : str
        The units of mass used in expressions of concentration
    diffusivity : float
        The bulk diffusivity in water for bulk species
    """

    def __init__(
        self,
        name: str,
        species_type: Union[SpeciesType, str],
        units: str,
        atol: float = None,
        rtol: float = None,
        *,
        note=None,
        diffusivity: float = None,
        _vars=None,
        _vals=None,
    ) -> None:
        """A biological or chemical species.

        Parameters
        ----------
        name : str
            The species name
        species_type : SpeciesType | str
            The species type
        units : str
            The units of mass for this species, see :attr:`units` property.
        atol : float, optional
            The absolute tolerance when solving this species' equations, by default None [1]_
        rtol : float, optional
            The relative tolerance when solving this species' equations, by default None [1]_

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure)
        diffusivity : float, optional
            Diffusivity of the species in water, by default None
        pipe_reaction : dict | MultispeciesReaction, optional
            Reaction dynamics of the species in pipes, by default None
        tank_reaction : dict | MultispeciesReaction, optional
            Reaction dynamics of the species in tanks, by default None
        _vars : VariableRegistry, optional
            the variables registry object of the model this variable was added to, by default None
        _vals : _type_, optional
            _description_, by default None

        Raises
        ------
        KeyExistsError
            if the name has already been used
        TypeError
            if mandatory arguments are passed as None; if a tank reaction is provided for a
            wall species; if an invalid type is passed for a pipe or tank reaction


        .. [1]
           The `atol` and `rtol` arguments must both be None, or both be a float greater than 0.
        """
        super().__init__(name, note=note)
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
        if _vars is not None and isinstance(_vars, MultispeciesReactionSystem):
            self._vars = _vars
        else:
            self._vars = None
        if _vals is not None and isinstance(_vals, InitialQuality):
            self._vals = _vals
        else:
            self._vals = None

    def set_tolerances(self, atol: float, rtol: float):
        """Set the absolute and relative tolerance for the solvers.

        The user must set both values, or neither value (None). Values must be
        positive.

        Arguments
        ---------
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
    def var_type(self) -> QualityVarType:
        """This is a species"""
        return QualityVarType.SPECIES

    @property
    def species_type(self) -> SpeciesType:
        """The type of species"""
        return self._species_type

    @property
    def initial_quality(self) -> "NetworkSpecificData":
        """If a specific network has been linked, then the initial quality values for the network"""
        if self._vals is not None:
            return self._vals
        else:
            raise TypeError("This species is not linked to a NetworkSpecificValues obejct, please `relink` your model")
        
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


class Constant(WaterQualityVariable):
    """A constant coefficient for use in reaction expressions."""

    def __init__(self, name: str, value: float, *, units: str = None, note=None, _vars=None) -> None:
        """A variable representing a constant value.

        Arguments
        ---------
        name : str
            The name of the variable.
        value : float
            The constant value.

        Keyword Arguments
        -----------------
        units : str, optional
            Units for the variable, by default None
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).

        Other Parameters
        ----------------
        _vars : VariablesRegistry, optional
            the variables registry object of the model this variable was added to, by default None
        """
        super().__init__(name, note=note)
        if _vars is not None and name in _vars:
            raise KeyExistsError("This variable name is already taken")
        self.value = float(value)
        """The value of the constant"""
        self.units = units
        """The units of the constant"""
        if _vars is not None and isinstance(_vars, MultispeciesReactionSystem):
            self._vars = _vars
        elif _vars is None:
            self._vars = None
        else:
            raise TypeError("Invalid type for _vars")

    def __call__(self, *, t=None) -> Any:
        return self.value

    @property
    def var_type(self) -> QualityVarType:
        """This is a constant coefficient."""
        return QualityVarType.CONSTANT

    def to_dict(self) -> Dict[str, Any]:
        ret = dict(name=self.name, value=self.value)
        if self.units:
            ret["units"] = self.units
        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note
        return ret


class Parameter(WaterQualityVariable):
    """A coefficient that is parameterized by pipe/tank."""

    def __init__(self, name: str, global_value: float, *, units: str = None, note=None, _vars=None, _vals=None) -> None:
        """A parameterized variable for use in expressions.

        Arguments
        ---------
        name : str
            The name of this parameter.
        global_value : float
            The global value for the parameter if otherwise unspecified.

        Keyword Arguments
        -----------------
        units : str, optional
            The units for this parameter, by default None
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).

        Other Parameters
        ----------------
        _vars : VariablesRegistry, optional
            the variables registry object of the model this variable was added to, by default None
        _vals : ParameterValues, optional
            Values for specific tanks or pipes, by default None. This argument should
            be passed by the MultispeciesModel during variable creation.
        """
        super().__init__(name, note=note)
        if _vars is not None and name in _vars:
            raise KeyExistsError("This variable name is already taken")
        self.global_value = float(global_value)
        self.units = units
        if _vars is not None and isinstance(_vars, MultispeciesReactionSystem):
            self._vars = _vars
        elif _vars is None:
            self._vars = None
        else:
            raise TypeError("Invalid type for _vars")
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
    def var_type(self) -> QualityVarType:
        """This is a parameterized coefficient."""
        return QualityVarType.PARAMETER

    def link_values(self, values: "ParameterValues"):
        """Link the paraemterized values to a model object.

        Note, this should not be necessary if the user uses the MultispeciesModel
        add_parameter function.

        Arguments
        ---------
        values : ParameterValues
            The parameter values object.
        """
        self._vals = values

    def to_dict(self) -> Dict[str, Any]:
        ret = dict(name=self.name, global_value=self.global_value)
        if self.units:
            ret["units"] = self.units
        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note
        return ret


class Term(WaterQualityVariable):
    def __init__(self, name: str, expression: str, *, note=None, _vars=None) -> None:
        """A named expression that can be used as a term in other expressions.

        Arguments
        ---------
        name : str
            The variable name.
        expression : str
            The mathematical expression to be aliased

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).

        Other Parameters
        ----------------
        _vars : VariablesRegistry, optional
            the variables registry object of the model this variable was added to, by default None
        """
        super().__init__(name, note=note)
        if _vars is not None and name in _vars:
            raise KeyExistsError("This variable name is already taken")
        self.expression = expression
        """The expression that is aliased by this term"""
        if _vars is not None and isinstance(_vars, MultispeciesReactionSystem):
            self._vars = _vars
        elif _vars is None:
            self._vars = None
        else:
            raise TypeError("Invalid type for _vars")

    @property
    def var_type(self) -> QualityVarType:
        """This is a term (named expression)."""
        return QualityVarType.TERM

    def to_dict(self) -> Dict[str, Any]:
        ret = dict(name=self.name, expression=self.expression)
        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note
        return ret


class ReservedName(WaterQualityVariable):
    def __init__(self, name: str, *, note=None) -> None:
        """An object representing a reserved name that should not be used by the user.

        Arguments
        ---------
        name : str
            The reserved name.

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).

        Other Parameters
        ----------------
        _vars : VariablesRegistry, optional
            the variables registry object of the model this variable was added to, by default None

        Raises
        ------
        KeyExistsError
            _description_
        """
        self.name = name
        self.note = note

    @property
    def var_type(self) -> QualityVarType:
        """Variable name is a reserved word in MSX"""
        return QualityVarType.RESERVED

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("You cannot convert a reserved word to a dictionary representation")


class HydraulicVariable(ReservedName):
    """A variable representing instantaneous hydraulics data."""

    def __init__(self, name: str, units: str = None, *, note=None) -> None:
        """A variable representing instantaneous hydraulics data.

        The user should not need to create any variables using this class, they
        are created automatically by the MultispeciesModel object during initialization.

        Arguments
        ---------
        name : str
            The name of the variable (predefined by MSX)
        units : str, optional
            The units for hydraulic variable, by default None

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).
        """
        super().__init__(name, note=note)
        self.units = units
        """The hydraulic variable's units"""


class MathFunction(ReservedName):
    """A variable that is actually a mathematical function defined by MSX."""

    def __init__(self, name: str, func: Callable, *, note=None) -> None:
        """A variable that is actually a mathematical function defined by MSX.

        Arguments
        ---------
        name : str
            The function name
        func : Callable
            The callable function

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).
        """
        super().__init__(name, note=note)
        self.func = func
        """A callable function or SymPy function"""

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.func(*args, **kwds)



class Reaction(WaterQualityReaction):
    """A water quality biochemical reaction dynamics definition for a specific species."""

    def __init__(self, species_name: str, reaction_type: ReactionType, dynamics_type: DynamicsType, expression: str, *, note=None) -> None:
        """A water quality biochemical reaction dynamics definition for a specific species.

        Arguments
        ---------
        species_name : Species | str
            The species (object or name) this reaction is applicable to.
        dynamics_type : DynamicsType
            The type of reaction dynamics being described by the expression: one of RATE, FORMULA, or EQUIL.
        expression : str
            The mathematical expression for the right-hand-side of the reaction equation.

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this reaction, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).
        """
        super().__init__(species_name=species_name, note=note)
        dynamics_type = DynamicsType.get(dynamics_type)
        reaction_type = ReactionType.get(reaction_type)
        if reaction_type is None:
            raise TypeError("Required argument reaction_type cannot be None")
        if dynamics_type is None:
            raise TypeError("Required argument dynamics_type cannot be None")
        self.__reaction_type = reaction_type
        self._dynamics_type = dynamics_type
        if not expression:
            raise TypeError("expression cannot be None")
        self.expression = expression
        """The mathematical expression (right-hand-side)"""

    @property
    def dynamics_type(self) -> DynamicsType:
        """The type of dynamics being described.
        See :class:`DynamicsType` for valid values.
        """
        return self._dynamics_type

    @property
    def reaction_type(self) -> ReactionType:
        """The type of reaction"""
        return self.__reaction_type

    def to_dict(self) -> dict:
        ret = dict(species_name=str(self.species_name), dynamics_type=self.dynamics_type.name.lower(), expression=self.expression)
        if isinstance(self.note, ENcomment):
            ret["note"] = self.note.to_dict()
        elif isinstance(self.note, (str, dict, list)):
            ret["note"] = self.note
        return ret


class MultispeciesReactionSystem(WaterQualityReactionSystem):
    """A registry for all the variables registered in the multispecies reactions model.

    This object can be used like an immutable mapping, with the ``__len__``, ``__getitem__``,
    ``__iter__``, ``__contains__``, ``__eq__`` and ``__ne__`` functions being defined.
    """

    def __init__(self) -> None:
        """Create a new reaction system.
        """
        super().__init__()
        self._vars.add_disjoint_group("reserved")
        self._species = self._vars.add_disjoint_group("species")
        self._const = self._vars.add_disjoint_group("constant")
        self._param = self._vars.add_disjoint_group("parameter")
        self._term = self._vars.add_disjoint_group("term")
        self._rxns = dict(pipe=dict(), tank=dict())
        self._pipes = self._rxns['pipe']
        self._tanks = self._rxns['tank']

    @property
    def species(self) -> Dict[str, Species]:
        """The dictionary view onto only species"""
        return self._species

    @property
    def constants(self) -> Dict[str, Constant]:
        """The dictionary view onto only constants"""
        return self._const

    @property
    def parameters(self) -> Dict[str, Parameter]:
        """The dictionary view onto only parameters"""
        return self._param

    @property
    def terms(self) -> Dict[str, Term]:
        """The dictionary view onto only named terms"""
        return self._term

    @property
    def pipe_reactions(self) -> Dict[str, WaterQualityReaction]:
        """The dictionary view onto pipe reactions"""
        return self._pipes
    
    @property
    def tank_reactions(self) -> Dict[str, WaterQualityReaction]:
        """The dictionary view onto tank reactions"""
        return self._tanks

    def add_variable(self, obj: WaterQualityVariable) -> None:
        """Add a variable object to the registry.

        The appropriate group is determined by querying the object's
        var_type attribute.

        Arguments
        ---------
        obj : WaterQualityVariable
            The variable to add.

        Raises
        ------
        TypeError
            if obj is not a WaterQualityVariable
        KeyExistsError
            if obj has a name that is already used in the registry
        """
        if not isinstance(obj, WaterQualityVariable):
            raise TypeError("Expected WaterQualityVariable object")
        if obj.name in self:
            raise KeyExistsError("Variable name {} already exists in model".format(obj.name))
        obj._vars = self
        self._vars.add_item_to_group(obj.var_type.name.lower(), obj.name, obj)

    def add_reaction(self, obj: WaterQualityReaction) -> None:
        """Add a reaction to the model

        Parameters
        ----------
        obj : WaterQualityReaction
            _description_

        Raises
        ------
        TypeError
            _description_
        KeyError
            _description_
        """
        if not isinstance(obj, WaterQualityReaction):
            raise TypeError("Expected WaterQualityReaction object")
        if obj.species_name not in self:
            raise KeyError("Species {} does not exist in the model".format(obj.species_name))
        self._rxns[obj.reaction_type.name.lower()][obj.species_name] = obj

    def all_variables(self):
        """A generator looping through all variables"""
        for k, v in self._vars.items():
            yield k, v.var_type.name.lower(), v

    def all_reactions(self):
        """A generator looping through all reactions"""
        for k2, v in self._rxns.items():
            for k1, v1 in v.items():
                yield k1, k2, v1

    def to_dict(self):
        return dict(
            species=[v.to_dict() for v in self._species.values()],
            constants=[v.to_dict() for v in self._const.values()],
            parameters=[v.to_dict() for v in self._param.values()],
            terms=[v.to_dict() for v in self._term.values()],
            pipe_reactions=[v.to_dict() for v in self.pipe_reactions.values()],
            tank_reactions=[v.to_dict() for v in self.tank_reactions.values()],
        )


class InitialQuality:
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
        """The global value for this species, if unspecified"""
        self._node_values = node_values if node_values is not None else dict()
        self._link_values = link_values if link_values is not None else dict()

    def __repr__(self) -> str:
        return self.__class__.__name__ + "(global_value={}, node_values=<{} entries>, link_values=<{} entries>)".format(
            self.global_value, len(self._node_values), len(self._link_values)
        )
    
    @property
    def node_values(self) -> Dict[str, float]:
        """A mapping of node names to initial quality values for this species"""
        return self._node_values

    @property
    def link_values(self) -> Dict[str, float]:
        """A mapping of link names to initial quality values for this species"""
        return self._link_values

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return dict(global_value=self.global_value, node_values=self._node_values.copy(), link_values=self._link_values.copy())


class ParameterValues:
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
    def pipe_values(self) -> Dict[str, float]:
        """View onto the pipe values dictionary"""
        return self._pipe_values

    @property
    def tank_values(self) -> Dict[str, float]:
        """View onto the tank values dictionary"""
        return self._tank_values

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return dict(pipe_values=self._pipe_values.copy(), tank_values=self._tank_values.copy())


class NetworkSpecificData:
    """A container for network-specific values associated with a multispecies water quality model."""

    def __init__(self, patterns: dict = None, sources: dict = None, initial_quality: dict = None, parameter_values: dict = None) -> None:
        """A container for network-specific values associated with a multispecies water quality model.

        Data is copied from dictionaries passed in, so once created, the dictionaries passed are not connected
        to this object.

        Parameters
        ----------
        patterns : Dict[str, List[float]]
            patterns to use for sources
        sources : Dict[str, dict]
            sources defined for the model
        initial_quality : Dict[str, dict]
            initial values for different species at different nodes, links, and the global value
        parameter_values : Dict[str, dict]
            parameter values for different pipes and tanks
        """
        if sources is None:
            sources = dict()
        if initial_quality is None:
            initial_quality = dict()
        if patterns is None:
            patterns = dict()
        if parameter_values is None:
            parameter_values = dict()
        self._source_dict = dict()
        self._pattern_dict = dict()
        self._initial_quality_dict: Dict[str, InitialQuality] = dict()
        self._parameter_value_dict: Dict[str, ParameterValues] = dict()
        
        self._source_dict = sources.copy()
        self._pattern_dict = patterns.copy()
        for k, v in initial_quality.items():
            self._initial_quality_dict[k] = InitialQuality(**v)
        for k, v in parameter_values.items():
            self._parameter_value_dict[k] = ParameterValues(**v)

    @property
    def sources(self):
        """A dictionary of sources, keyed by species name"""
        return self._source_dict

    @property
    def initial_quality(self) -> Dict[str, InitialQuality]:
        """A dictionary of initial quality values, keyed by species name"""
        return self._initial_quality_dict

    @property
    def patterns(self):
        """A dictionary of patterns, specific for the water quality model, keyed by pattern name.

        .. note:: the WaterNetworkModel cannot see these patterns, so names can be reused, so be
            careful. Likewise, this model cannot see the WaterNetworkModel patterns, so this could be
            a source of some confusion.
        """
        return self._pattern_dict

    @property
    def parameter_values(self):
        """A dictionary of parameter values, keyed by parameter name"""
        return self._parameter_value_dict

    def add_pattern(self, name: str, multipliers: List[float]):
        """Add a water-quality-model-specific pattern.

        Arguments
        ---------
        name : str
            The pattern name
        multipliers : List[float]
            The pattern multipliers
        """
        self._pattern_dict[name] = multipliers

    def init_new_species(self, species: Species):
        """(Re)set the initial quality values for a species to a new container

        Arguments
        ---------
        species : Species
            The species to (re) initialized.

        Returns
        -------
        InitialQuality
            the new initial quality values container
        """
        self._initial_quality_dict[str(species)] = InitialQuality()
        if isinstance(species, Species):
            species._vals = self._initial_quality_dict[str(species)]
        return self._initial_quality_dict[str(species)]

    def remove_species(self, species: Union[Species, str]):
        """Remove a species from the network specific model.

        Arguments
        ---------
        species : Union[Species, str]
            _description_
        """
        if isinstance(species, Species):
            species._vals = None
        try:
            self._initial_quality_dict.__delitem__(str(species))
        except KeyError:
            pass

    def init_new_parameter(self, param: Parameter):
        """(Re)initialize parameter values for a parameter.

        Arguments
        ---------
        param : Parameter
            _description_

        Returns
        -------
        _type_
            _description_
        """
        self._parameter_value_dict[str(param)] = ParameterValues()
        if isinstance(param, Parameter):
            param._vals = self._parameter_value_dict[str(param)]
        return self._parameter_value_dict[str(param)]

    def remove_parameter(self, param: Union[Parameter, str]):
        """Remove values associated with a specific parameter.

        Arguments
        ---------
        param : Union[Parameter, str]
            _description_
        """
        if isinstance(param, Parameter):
            param._vals = None
        try:
            self._parameter_value_dict.__delitem__(str(param))
        except KeyError:
            pass

    def to_dict(self):
        ret = dict(initial_quality=dict(), parameter_values=dict(), sources=dict(), patterns=dict())
        for k, v in self._initial_quality_dict.items():
            ret["initial_quality"][k] = v.to_dict()
        for k, v in self._parameter_value_dict.items():
            ret["parameter_values"][k] = v.to_dict()
        ret["sources"] = self._source_dict.copy()
        ret["patterns"] = self._pattern_dict.copy()
        return ret
    

class MultispeciesQualityModel:
    """A multispecies water quality model for use with WNTR EPANET-MSX simulator."""

    def __init__(self, msx_file_name=None) -> None:
        """A full, multi-species water quality model.

        Arguments
        ---------
        msx_file_name : str, optional
            an MSX file to read in, by default None
        """
        self.name: str = None
        """A name for the model, or the MSX model filename (no spaces allowed)"""
        self.title: str = None
        """The title line from the MSX file, must be a single line"""
        self.desc: str = None
        """A longer description, note that multi-line descriptions may not be 
        represented well in dictionary form."""
        self._orig_file: str = None
        """The original filename"""
        self._references: List[Union[str, Dict[str, str]]] = list()
        self._options = MultispeciesOptions()
        self._reaction_system = MultispeciesReactionSystem()
        self._network_data = NetworkSpecificData()
        self._wn = None

        for v in HYDRAULIC_VARIABLES:
            self._reaction_system.add_variable(HydraulicVariable(**v))
        for k, v in EXPR_FUNCTIONS.items():
            self._reaction_system.add_variable(MathFunction(name=k.lower(), func=v))
            self._reaction_system.add_variable(MathFunction(name=k.capitalize(), func=v))
            self._reaction_system.add_variable(MathFunction(name=k.upper(), func=v))
        
        if msx_file_name is not None:
            from wntr.epanet.msx.io import MsxFile
            MsxFile.read(msx_file_name, self)

    def __repr__(self) -> str:
        ret = '{}('.format(self.__class__.__name__)
        if self.name:
            ret = ret + 'name={}'.format(repr(self.name))
        elif self.title:
            ret = ret + 'title={}'.format(repr(self.title))
        elif self._orig_file:
            ret = ret + 'msx_file_name={}'.format(repr(self._orig_file))
        ret = ret + ')'
        return ret

    @property
    def references(self) -> List[Union[str, Dict[str, str]]]:
        """A list of strings or mappings that provide references for this model.
        This property should be modified using append/insert/remove. Members of
        the list should be json seriealizable (i.e., strings or dicts of strings).
        """
        return self._references

    @property
    def reaction_system(self) -> MultispeciesReactionSystem:
        """The reaction variables defined for this model."""
        return self._reaction_system
    
    @property
    def rxn_sys(self) -> MultispeciesReactionSystem:
        """Alias for the reaction_system property for ease of programming"""
        return self._reaction_system

    @property
    def network_data(self) -> NetworkSpecificData:
        """The network-specific values added to this model."""
        return self._network_data

    @property
    def net_data(self) -> NetworkSpecificData:
        """Alias for the reaction_system property for ease of programming"""
        return self._network_data

    @property
    def options(self) -> MultispeciesOptions:
        """The MSX model options"""
        return self._options

    @property
    def species_name_list(self) -> List[str]:
        """all defined species names"""
        return list(self.reaction_system.species.keys())

    @property
    def constant_name_list(self) -> List[str]:
        """all defined coefficient names"""
        return list(self.reaction_system.constants.keys())

    @property
    def parameter_name_list(self) -> List[str]:
        """all defined coefficient names"""
        return list(self.reaction_system.parameters.keys())

    @property
    def term_name_list(self) -> List[str]:
        """all defined function (MSX 'terms') names"""
        return list(self.reaction_system.terms.keys())

    @options.setter
    def options(self, value):
        if isinstance(value, dict):
            self._options = MultispeciesOptions.factory(value)
        elif not isinstance(value, MultispeciesOptions):
            raise TypeError("Expected a MultispeciesOptions object, got {}".format(type(value)))
        else:
            self._options = value

    def add_species(
        self,
        name: str,
        species_type: SpeciesType,
        units: str,
        atol: float = None,
        rtol: float = None,
        *,
        note: Any = None,
        diffusivity: float = None,
    ) -> Species:
        """Add a species to the model

        Arguments
        ---------
        name : str
            _description_
        species_type : SpeciesType
            _description_
        units : str
            _description_
        atol : float, optional
            _description_, by default None
        rtol : float, optional
            _description_, by default None

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).
        diffusivity : float, optional
            Diffusivity in water for this species.

        Raises
        ------
        KeyError
            _description_

        Returns
        -------
        Species
            _description_
        """
        if name in self._reaction_system:
            raise KeyError(
                "Variable named {} already exists in model as type {}".format(name, self._reaction_system._vars.get_groupname(name))
            )
        species_type = SpeciesType.get(species_type, allow_none=False)
        iq = self.network_data.init_new_species(name)
        new = Species(
            name=name,
            species_type=species_type,
            units=units,
            atol=atol,
            rtol=rtol,
            note=note,
            _vars=self._reaction_system,
            _vals=iq,
            diffusivity=diffusivity,
        )
        self.reaction_system.add_variable(new)
        return new

    def remove_species(self, species):
        """Remove a species from the model.

        Arguments
        ---------
        species : _type_
            _description_
        """
        name = str(species)
        self.network_data.remove_species(name)
        # FIXME: validate additional items
        self.reaction_system.__delitem__(name)

    def add_constant(self, name: str, value: float, *, units: str = None, note: Any = None) -> Constant:
        """Add a constant coefficient to the model.

        Arguments
        ---------
        name : str
            _description_
        value : float
            _description_

        Keyword Arguments
        -----------------
        units : str, optional
            _description_, by default None
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).

        Raises
        ------
        KeyError
            _description_
        
        Returns
        -------
        Constant
            _description_
        """
        if name in self._reaction_system:
            raise KeyError(
                "Variable named {} already exists in model as type {}".format(name, self._reaction_system._vars.get_groupname(name))
            )
        new = Constant(name=name, value=value, units=units, note=note, _vars=self._reaction_system)
        self.reaction_system.add_variable(new)
        return new

    def remove_constant(self, const):
        """Remove a constant coefficient from the model.

        Arguments
        ---------
        const : _type_
            _description_
        """
        name = str(const)
        # FIXME: validate deletion
        self.reaction_system.__delitem__(name)

    def add_parameter(self, name: str, global_value: float, *, units: str = None, note: Any = None) -> Parameter:
        """Add a parameterized coefficient to the model.

        Arguments
        ---------
        name : str
            _description_
        global_value : float
            _description_

        Keyword Arguments
        -----------------
        units : str, optional
            _description_, by default None
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).

        Raises
        ------
        KeyError
            _description_

        Returns
        -------
        Parameter
            _description_
        """
        if name in self._reaction_system:
            raise KeyError(
                "Variable named {} already exists in model as type {}".format(name, self._reaction_system._vars.get_groupname(name))
            )
        pv = self.network_data.init_new_parameter(name)
        new = Parameter(name=name, global_value=global_value, units=units, note=note, _vars=self._reaction_system, _vals=pv)
        self.reaction_system.add_variable(new)
        return new

    def remove_parameter(self, param):
        """Remove a parameterized coefficient from the model.

        Arguments
        ---------
        param : _type_
            _description_
        """
        name = str(param)
        self.network_data.remove_parameter(name)
        # FIXME: validate additional items
        self.reaction_system.__delitem__(name)

    def add_term(self, name: str, expression: str, *, note: Any = None) -> Term:
        """Add a named expression (term) to the model.

        Arguments
        ---------
        name : str
            _description_
        expression : str
            _description_

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this variable, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).

        Raises
        ------
        KeyError
            _description_

        Returns
        -------
        Term
            _description_
        """
        if name in self._reaction_system:
            raise KeyError(
                "Variable named {} already exists in model as type {}".format(name, self._reaction_system._vars.get_groupname(name))
            )
        new = Term(name=name, expression=expression, note=note, _vars=self._reaction_system)
        self.reaction_system.add_variable(new)
        return new

    def remove_term(self, term):
        """Remove a named expression (term) from the model.

        Arguments
        ---------
        term : _type_
            _description_
        """
        name = str(term)
        # FIXME: validate deletion
        self.reaction_system.__delitem__(name)

    def add_reaction(
        self, species_name: str, reaction_type: ReactionType, dynamics_type: DynamicsType, expression: str, *, note: Any = None
    ) -> WaterQualityReaction:
        """Add a reaction to a species in the model.

        Note that all species need to have both a pipe and tank reaction defined
        unless all species are bulk species and
        the tank reactions are identical to the pipe reactions. However, it is not
        recommended that users take this approach.

        Once added, access the reactions from the species' object.

        Arguments
        ---------
        species_name : str
            _description_
        location_type : LocationType
            _description_
        dynamics_type : DynamicsType
            _description_
        expression : str
            _description_

        Keyword Arguments
        -----------------
        note : str | dict | ENcomment, optional
            Supplementary information regarding this reaction, by default None
            (see :class:`~wntr.epanet.util.ENcomment` for dict structure).

        Raises
        ------
        TypeError
            _description_

        Returns
        -------
        MultispeciesReaction
            _description_
        """
        species_name = str(species_name)
        species = self.reaction_system.species[species_name]
        if species.var_type is not QualityVarType.SPECIES:
            raise TypeError("Variable {} is not a Species, is a {}".format(species.name, species.var_type))
        reaction_type = ReactionType.get(reaction_type, allow_none=False)
        dynamics_type = DynamicsType.get(dynamics_type, allow_none=False)
        new = Reaction(reaction_type=reaction_type, dynamics_type=dynamics_type, species_name=species_name, expression=expression, note=note)
        self.reaction_system.add_reaction(new)
        return new

    def remove_reaction(self, species_name: str, reaction_type: ReactionType) -> None:
        """Remove a reaction at a specified location from a species.

        Parameters
        ----------
        species : str
            the species name to remove the reaction from
        location : LocationType
            the location to remove the reaction from
        """
        reaction_type = ReactionType.get(reaction_type, allow_none=False)
        species_name = str(species_name)
        del self.reaction_system.all_reactions[reaction_type.name.lower()][species_name]

    def to_dict(self):
        from wntr import __version__

        return {
            'wntr-version': "{}".format(__version__),
            'name': self.name,
            'title': self.title,
            'desc': self.desc if self.desc is None or '\n' not in self.desc else self.desc.splitlines(),
            'references': self.references.copy(),
            'reaction_system': self.reaction_system.to_dict(),
            'network_data': self.network_data.to_dict(),
            'options': self.options.to_dict(),
        }

    @classmethod
    def from_dict(cls, data):
        from wntr import __version__
        
        ver = data.get('wntr-version', None)
        if ver > __version__:
            logger.warn('Importing from a file created by a newer version of wntr, compatibility not guaranteed')
            warnings.warn('Importing from a file created by a newer version of wntr, compatibility not guaranteed')
        new = cls()
        new.name = data.get('name', None)
        new.title = data.get('title', None)
        new.desc = data.get('desc', None)
        if isinstance(new.desc, (list, tuple)):
            desc = '\n'.join(new.desc)
            new.desc = desc
        new.references.extend(data.get('references', list()))

        rxn_sys = data.get('reaction_system', dict())
        for var in rxn_sys.get('species', list()):
            new.add_species(**var)
        for var in rxn_sys.get('constants', list()):
            new.add_constant(**var)
        for var in rxn_sys.get('parameters', list()):
            new.add_parameter(**var)
        for var in rxn_sys.get('terms', list()):
            new.add_term(**var)
        for rxn in rxn_sys.get('pipe_reactions', list()):
            rxn['reaction_type'] = 'pipe'
            new.add_reaction(**rxn)
        for rxn in rxn_sys.get('tank_reactions', list()):
            rxn['reaction_type'] = 'tank'
            new.add_reaction(**rxn)
        
        new._network_data = NetworkSpecificData(**data.get('network_data', dict()))
        for species in new.rxn_sys.species:
            if species not in new.net_data.initial_quality:
                new.net_data.init_new_species(species)
        for param in new.rxn_sys.parameters:
            if param not in new.net_data.parameter_values:
                new.net_data.init_new_parameter(param)

        opts = data.get('options', None)
        if opts:
            new.options = opts
        
        return new
