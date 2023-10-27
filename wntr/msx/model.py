# -*- coding: utf-8 -*-

"""Water quality model implementations.
"""

import logging

from typing import (
    Any,
    Dict,
    List,
    Union,
)
import warnings


from wntr.msx.elements import Constant, HydraulicVariable, InitialQuality, MathFunction, Parameter, ParameterValues, Reaction, Species, Term
from wntr.utils.disjoint_mapping import KeyExistsError
from .base import (
    NetworkData,
    AbstractModel,
    AbstractReaction,
    ReactionSystem,
    AbstractVariable,
    HYDRAULIC_VARIABLES,
    EXPR_FUNCTIONS,
    ExpressionType,
    ReactionType,
    VariableType,
    SpeciesType,
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
    "MsxNetworkData",
    "MsxReactionSystem",
    "MsxModel",
]


class MsxReactionSystem(ReactionSystem):
    """A registry for all the variables registered in the multispecies reactions model.

    This object can be used like an immutable mapping, with the ``__len__``, ``__getitem__``,
    ``__iter__``, ``__contains__``, ``__eq__`` and ``__ne__`` functions being defined.
    """

    def __init__(self) -> None:
        """Create a new reaction system."""
        super().__init__()
        self._vars.add_disjoint_group("reserved")
        self._species = self._vars.add_disjoint_group("species")
        self._const = self._vars.add_disjoint_group("constant")
        self._param = self._vars.add_disjoint_group("parameter")
        self._term = self._vars.add_disjoint_group("term")
        self._rxns = dict(pipe=dict(), tank=dict())
        self._pipes = self._rxns["pipe"]
        self._tanks = self._rxns["tank"]

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
    def pipe_reactions(self) -> Dict[str, AbstractReaction]:
        """The dictionary view onto pipe reactions"""
        return self._pipes

    @property
    def tank_reactions(self) -> Dict[str, AbstractReaction]:
        """The dictionary view onto tank reactions"""
        return self._tanks

    def add_variable(self, obj: AbstractVariable) -> None:
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
        if not isinstance(obj, AbstractVariable):
            raise TypeError("Expected WaterQualityVariable object")
        if obj.name in self:
            raise KeyExistsError("Variable name {} already exists in model".format(obj.name))
        obj._vars = self
        self._vars.add_item_to_group(obj.var_type.name.lower(), obj.name, obj)

    def add_reaction(self, obj: AbstractReaction) -> None:
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
        if not isinstance(obj, AbstractReaction):
            raise TypeError("Expected WaterQualityReaction object")
        if obj.species_name not in self:
            raise KeyError("Species {} does not exist in the model".format(obj.species_name))
        self._rxns[obj.reaction_type.name.lower()][obj.species_name] = obj

    def variables(self):
        # FIXME: rename without "all_" for this
        """A generator looping through all variables"""
        for k, v in self._vars.items():
            yield k, v.var_type.name.lower(), v

    def reactions(self):
        """A generator looping through all reactions"""
        for k2, v in self._rxns.items():
            for k1, v1 in v.items():
                yield k1, k2, v1

    def to_dict(self) -> dict:
        return dict(
            species=[v.to_dict() for v in self._species.values()],
            constants=[v.to_dict() for v in self._const.values()],
            parameters=[v.to_dict() for v in self._param.values()],
            terms=[v.to_dict() for v in self._term.values()],
            pipe_reactions=[v.to_dict() for v in self.pipe_reactions.values()],
            tank_reactions=[v.to_dict() for v in self.tank_reactions.values()],
        )


class MsxNetworkData(NetworkData):
    """A container for network-specific values associated with a multispecies water quality model."""

    def __init__(
        self, patterns: dict = None, sources: dict = None, initial_quality: dict = None, parameter_values: dict = None
    ) -> None:
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

    def to_dict(self) -> dict:
        ret = dict(initial_quality=dict(), parameter_values=dict(), sources=dict(), patterns=dict())
        for k, v in self._initial_quality_dict.items():
            ret["initial_quality"][k] = v.to_dict()
        for k, v in self._parameter_value_dict.items():
            ret["parameter_values"][k] = v.to_dict()
        ret["sources"] = self._source_dict.copy()
        ret["patterns"] = self._pattern_dict.copy()
        return ret


class MsxModel(AbstractModel):
    """A multispecies water quality model for use with WNTR EPANET-MSX simulator."""

    def __init__(self, msx_file_name=None) -> None:
        """A full, multi-species water quality model.

        Arguments
        ---------
        msx_file_name : str, optional
            an MSX file to read in, by default None
        """
        super().__init__(msx_file_name)
        self._references: List[Union[str, Dict[str, str]]] = list()
        self._options = MultispeciesOptions()
        self._rxn_system = MsxReactionSystem()
        self._net_data = MsxNetworkData()
        self._wn = None

        for v in HYDRAULIC_VARIABLES:
            self._rxn_system.add_variable(HydraulicVariable(**v))
        for k, v in EXPR_FUNCTIONS.items():
            self._rxn_system.add_variable(MathFunction(name=k.lower(), func=v))
            self._rxn_system.add_variable(MathFunction(name=k.capitalize(), func=v))
            self._rxn_system.add_variable(MathFunction(name=k.upper(), func=v))

        if msx_file_name is not None:
            from wntr.epanet.msx.io import MsxFile

            MsxFile.read(msx_file_name, self)

    def __repr__(self) -> str:
        ret = "{}(".format(self.__class__.__name__)
        if self.name:
            ret = ret + "name={}".format(repr(self.name))
        elif self.title:
            ret = ret + "title={}".format(repr(self.title))
        elif self._orig_file:
            ret = ret + "{}".format(repr(self._orig_file))
        ret = ret + ")"
        return ret

    @property
    def references(self) -> List[Union[str, Dict[str, str]]]:
        """A list of strings or mappings that provide references for this model.

        .. note::
            This property is a list, and should be modified using append/insert/remove. 
            Members of the list should be json seriealizable (i.e., strings or dicts of strings).
        """
        return self._references

    @property
    def reaction_system(self) -> MsxReactionSystem:
        """The reaction variables defined for this model."""
        return self._rxn_system

    @property
    def network_data(self) -> MsxNetworkData:
        """The network-specific values added to this model."""
        return self._net_data

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
        if name in self._rxn_system:
            raise KeyError(
                "Variable named {} already exists in model as type {}".format(
                    name, self._rxn_system._vars.get_groupname(name)
                )
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
            _vars=self._rxn_system,
            _vals=iq,
            diffusivity=diffusivity,
        )
        self.reaction_system.add_variable(new)
        return new

    def remove_species(self, species):
        """Remove a species from the model.

        Removes from both the reaction_system and the network_data.

        Arguments
        ---------
        species : _type_
            _description_
        """
        name = str(species)
        self.network_data.remove_species(name)
        # FIXME: validate additional items
        self.reaction_system.__delitem__(name)

    def add_constant(self, name: str, value: float, units: str = None, note: Any = None) -> Constant:
        """Add a constant coefficient to the model.

        Arguments
        ---------
        name : str
            _description_
        value : float
            _description_
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
        if name in self._rxn_system:
            raise KeyError(
                "Variable named {} already exists in model as type {}".format(
                    name, self._rxn_system._vars.get_groupname(name)
                )
            )
        new = Constant(name=name, value=value, units=units, note=note, _vars=self._rxn_system)
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

    def add_parameter(self, name: str, global_value: float, units: str = None, note: Any = None) -> Parameter:
        """Add a parameterized coefficient to the model.

        Arguments
        ---------
        name : str
            _description_
        global_value : float
            _description_
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
        if name in self._rxn_system:
            raise KeyError(
                "Variable named {} already exists in model as type {}".format(
                    name, self._rxn_system._vars.get_groupname(name)
                )
            )
        pv = self.network_data.init_new_parameter(name)
        new = Parameter(name=name, global_value=global_value, units=units, note=note, _vars=self._rxn_system, _vals=pv)
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

    def add_term(self, name: str, expression: str, note: Any = None) -> Term:
        """Add a named expression (term) to the model.

        Arguments
        ---------
        name : str
            _description_
        expression : str
            _description_
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
        if name in self._rxn_system:
            raise KeyError(
                "Variable named {} already exists in model as type {}".format(
                    name, self._rxn_system._vars.get_groupname(name)
                )
            )
        new = Term(name=name, expression=expression, note=note, _vars=self._rxn_system)
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
        self, species_name: str, reaction_type: ReactionType, expression_type: ExpressionType, expression: str, note: Any = None
    ) -> AbstractReaction:
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
        expression_type : ExpressionType
            _description_
        expression : str
            _description_
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
        if species.var_type is not VariableType.SPECIES:
            raise TypeError("Variable {} is not a Species, is a {}".format(species.name, species.var_type))
        reaction_type = ReactionType.get(reaction_type, allow_none=False)
        expression_type = ExpressionType.get(expression_type, allow_none=False)
        new = Reaction(
            reaction_type=reaction_type,
            expression_type=expression_type,
            species_name=species_name,
            expression=expression,
            note=note,
        )
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
        del self.reaction_system.reactions[reaction_type.name.lower()][species_name]

    def to_dict(self) -> dict:
        from wntr import __version__

        return {
            "wntr-version": "{}".format(__version__),
            "name": self.name,
            "title": self.title,
            "description": self.description if self.description is None or "\n" not in self.description else self.description.splitlines(),
            "references": self.references.copy(),
            "reaction_system": self.reaction_system.to_dict(),
            "network_data": self.network_data.to_dict(),
            "options": self.options.to_dict(),
        }

    @classmethod
    def from_dict(cls, data) -> 'MsxModel':
        from wntr import __version__

        ver = data.get("wntr-version", None)
        if ver != __version__:
            logger.warn("Importing from a file created by a different version of wntr, compatibility not guaranteed")
            warnings.warn("Importing from a file created by a different version of wntr, compatibility not guaranteed")
        new = cls()
        new.name = data.get("name", None)
        new.title = data.get("title", None)
        new.description = data.get("description", None)
        if isinstance(new.description, (list, tuple)):
            desc = "\n".join(new.description)
            new.description = desc
        new.references.extend(data.get("references", list()))

        rxn_sys = data.get("reaction_system", dict())
        for var in rxn_sys.get("species", list()):
            new.add_species(**var)
        for var in rxn_sys.get("constants", list()):
            new.add_constant(**var)
        for var in rxn_sys.get("parameters", list()):
            new.add_parameter(**var)
        for var in rxn_sys.get("terms", list()):
            new.add_term(**var)
        for rxn in rxn_sys.get("pipe_reactions", list()):
            rxn["reaction_type"] = "pipe"
            new.add_reaction(**rxn)
        for rxn in rxn_sys.get("tank_reactions", list()):
            rxn["reaction_type"] = "tank"
            new.add_reaction(**rxn)

        new._net_data = MsxNetworkData(**data.get("network_data", dict()))
        for species in new.reaction_system.species:
            if species not in new.network_data.initial_quality:
                new.network_data.init_new_species(species)
        for param in new.reaction_system.parameters:
            if param not in new.network_data.parameter_values:
                new.network_data.init_new_parameter(param)

        opts = data.get("options", None)
        if opts:
            new.options = opts

        return new
