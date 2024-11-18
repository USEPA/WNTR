# coding: utf-8
"""
The wntr.msx.model module includes methods to build a multi-species water
quality model.
"""

from __future__ import annotations

import logging
import warnings
from typing import Dict, Generator, List, Union
from wntr.epanet.util import NoteType

from wntr.utils.disjoint_mapping import KeyExistsError

from .base import (
    EXPR_FUNCTIONS,
    HYDRAULIC_VARIABLES,
    QualityModelBase,
    ReactionBase,
    NetworkDataBase,
    ReactionSystemBase,
    ExpressionType,
    ReactionType,
    SpeciesType,
    VariableType,
)
from .elements import Constant, HydraulicVariable, InitialQuality, MathFunction, Parameter, ParameterValues, Reaction, Species, Term
from .options import MsxSolverOptions

logger = logging.getLogger(__name__)

MsxVariable = Union[Constant, HydraulicVariable, MathFunction, Parameter, Species, Term]
"""A class that is a valid MSX variable class"""


class MsxReactionSystem(ReactionSystemBase):
    """Registry for all the variables registered in the multi-species reactions
    model.

    This object can be used like a mapping.
    """

    def __init__(self) -> None:
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
        """Dictionary view onto only species"""
        return self._species

    @property
    def constants(self) -> Dict[str, Constant]:
        """Dictionary view onto only constants"""
        return self._const

    @property
    def parameters(self) -> Dict[str, Parameter]:
        """Dictionary view onto only parameters"""
        return self._param

    @property
    def terms(self) -> Dict[str, Term]:
        """Dictionary view onto only named terms"""
        return self._term

    @property
    def pipe_reactions(self) -> Dict[str, Reaction]:
        """Dictionary view onto pipe reactions"""
        return self._pipes

    @property
    def tank_reactions(self) -> Dict[str, Reaction]:
        """Dictionary view onto tank reactions"""
        return self._tanks

    def add_variable(self, variable: MsxVariable) -> None:
        """Add a variable object to the registry.

        The appropriate group is determined by querying the object's
        var_type attribute.

        Parameters
        ----------
        variable
            Variable to add.

        Raises
        ------
        TypeError
            If `variable` is not an MsxVariable
        KeyExistsError
            If `variable` has a name that is already used in the registry
        """
        if not isinstance(variable, (Species, Constant, Parameter, Term, MathFunction, HydraulicVariable)):
            raise TypeError("Expected AVariable object")
        if variable.name in self:
            raise KeyExistsError("Variable name {} already exists in model".format(variable.name))
        variable._vars = self
        self._vars.add_item_to_group(variable.var_type.name.lower(), variable.name, variable)

    def add_reaction(self, reaction: Reaction) -> None:
        """Add a reaction to the model

        Parameters
        ----------
        reaction : Reaction
            Water quality reaction definition

        Raises
        ------
        TypeError
            If `reaction` is not a Reaction
        KeyError
            If the `species_name` in the `reaction` does not exist in the model
        """
        if not isinstance(reaction, Reaction):
            raise TypeError("Expected a Reaction object")
        if reaction.species_name not in self:
            raise KeyError("Species {} does not exist in the model".format(reaction.species_name))
        self._rxns[reaction.reaction_type.name.lower()][reaction.species_name] = reaction

    def variables(self) -> Generator[tuple, None, None]:
        """Generator looping through all variables"""
        for k, v in self._vars.items():
            if v.var_type.name.lower() not in ['reserved']:
                yield k, v

    def reactions(self) -> Generator[tuple, None, None]:
        """Generator looping through all reactions"""
        for k2, v in self._rxns.items():
            for k1, v1 in v.items():
                yield k1, v1

    def to_dict(self) -> dict:
        """Dictionary representation of the MsxModel."""
        return dict(
            species=[v.to_dict() for v in self._species.values()],
            constants=[v.to_dict() for v in self._const.values()],
            parameters=[v.to_dict() for v in self._param.values()],
            terms=[v.to_dict() for v in self._term.values()],
            pipe_reactions=[v.to_dict() for v in self.pipe_reactions.values()],
            tank_reactions=[v.to_dict() for v in self.tank_reactions.values()],
        )


class MsxNetworkData(NetworkDataBase):
    """Network-specific values associated with a multi-species water 
    quality model

    Data is copied from dictionaries passed in, so once created, the
    dictionaries passed are not connected to this object.

    Parameters
    ----------
    patterns : dict, optional
        Patterns to use for sources
    sources : dict, optional
        Sources defined for the model
    initial_quality : dict, optional
        Initial values for different species at different nodes, links, and
        the global value
    parameter_values : dict, optional
        Parameter values for different pipes and tanks

    Notes
    -----
    ``patterns``
        Dictionary keyed by pattern name (str) with values being the
        multipliers (list of float)
    ``sources``
        Dictionary keyed by species name (str) with values being
        dictionaries keyed by junction name (str) with values being the
        dictionary of settings for the source
    ``initial_quality``
        Dictionary keyed by species name (str) with values being either an
        :class:`~wntr.msx.elements.InitialQuality` object or the
        appropriate dictionary representation thereof.
    ``parameter_values``
        Dictionary keyed by parameter name (str) with values being either
        a :class:`~wntr.msx.elements.ParameterValues` object or the
        appropriate dictionary representation thereof.
    """

    def __init__(self, patterns: Dict[str, List[float]] = None,
                 sources: Dict[str, Dict[str, dict]] = None,
                 initial_quality: Dict[str, Union[dict, InitialQuality]] = None,
                 parameter_values: Dict[str, Union[dict, ParameterValues]] = None) -> None:
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
        """Dictionary of sources, keyed by species name"""
        return self._source_dict

    @property
    def initial_quality(self) -> Dict[str, InitialQuality]:
        """Dictionary of initial quality values, keyed by species name"""
        return self._initial_quality_dict

    @property
    def patterns(self):
        """Dictionary of patterns, specific for the water quality model, keyed
        by pattern name.

        .. note:: the WaterNetworkModel cannot see these patterns, so names can
           be reused, so be careful. Likewise, this model cannot see the
           WaterNetworkModel patterns, so this could be a source of some
           confusion.
        """
        return self._pattern_dict

    @property
    def parameter_values(self) -> Dict[str, ParameterValues]:
        """Dictionary of parameter values, keyed by parameter name"""
        return self._parameter_value_dict

    def add_pattern(self, name: str, multipliers: List[float]):
        """Add a water quality model specific pattern.

        Arguments
        ---------
        name : str
            Pattern name
        multipliers : list of float
            Pattern multipliers
        """
        self._pattern_dict[name] = multipliers

    def init_new_species(self, species: Species):
        """(Re)set the initial quality values for a species

        Arguments
        ---------
        species : Species
            Species to (re)initialized.

        Returns
        -------
        InitialQuality
            New initial quality values
        """
        self._initial_quality_dict[str(species)] = InitialQuality()
        if isinstance(species, Species):
            species._vals = self._initial_quality_dict[str(species)]
        return self._initial_quality_dict[str(species)]

    def remove_species(self, species: Union[Species, str]):
        """Remove a species from the network specific model

        Arguments
        ---------
        species : Species or str
            Species to be removed from the network data
        """
        if isinstance(species, Species):
            species._vals = None
        try:
            self._initial_quality_dict.__delitem__(str(species))
        except KeyError:
            pass

    def init_new_parameter(self, param: Parameter):
        """(Re)initialize parameter values for a parameter

        Arguments
        ---------
        param : Parameter
            Parameter to be (re)initialized with network data

        Returns
        -------
        ParameterValues
            New network data for the specific parameter
        """
        self._parameter_value_dict[str(param)] = ParameterValues()
        if isinstance(param, Parameter):
            param._vals = self._parameter_value_dict[str(param)]
        return self._parameter_value_dict[str(param)]

    def remove_parameter(self, param: Union[Parameter, str]):
        """Remove values associated with a specific parameter

        Ignores non-parameters.

        Arguments
        ---------
        param : Parameter or str
            Parameter or parameter name to be removed from the network data
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


class MsxModel(QualityModelBase):
    """Multi-species water quality model

    Arguments
    ---------
    msx_file_name : str, optional
        MSX file to to load into the MsxModel object, by default None
    """

    def __init__(self, msx_file_name=None) -> None:
        super().__init__(msx_file_name)
        self._references: List[Union[str, Dict[str, str]]] = list()
        self._options: MsxSolverOptions = MsxSolverOptions()
        self._rxn_system: MsxReactionSystem = MsxReactionSystem()
        self._net_data: MsxNetworkData = MsxNetworkData()
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
        """List of strings or mappings that provide references for this model

        .. note::
            This property is a list, and should be modified using
            append/insert/remove. Members of the list should be json
            serializable (i.e., strings or dicts of strings).
        """
        return self._references

    @property
    def reaction_system(self) -> MsxReactionSystem:
        """Reaction variables defined for this model"""
        return self._rxn_system

    @property
    def network_data(self) -> MsxNetworkData:
        """Network-specific values added to this model"""
        return self._net_data

    @property
    def options(self) -> MsxSolverOptions:
        """MSX model options"""
        return self._options

    @property
    def species_name_list(self) -> List[str]:
        """Get a list of species names"""
        return list(self.reaction_system.species.keys())

    @property
    def constant_name_list(self) -> List[str]:
        """Get a list of coefficient names"""
        return list(self.reaction_system.constants.keys())

    @property
    def parameter_name_list(self) -> List[str]:
        """Get a list of coefficient names"""
        return list(self.reaction_system.parameters.keys())

    @property
    def term_name_list(self) -> List[str]:
        """Get a list of function (MSX 'terms') names"""
        return list(self.reaction_system.terms.keys())

    @options.setter
    def options(self, value: Union[dict, MsxSolverOptions]):
        if isinstance(value, dict):
            self._options = MsxSolverOptions.factory(value)
        elif not isinstance(value, MsxSolverOptions):
            raise TypeError("Expected a MsxSolverOptions object, got {}".format(type(value)))
        else:
            self._options = value

    def add_species(
        self,
        name: str,
        species_type: SpeciesType,
        units: str,
        atol: float = None,
        rtol: float = None,
        note: NoteType = None,
        diffusivity: float = None,
    ) -> Species:
        """Add a species to the model

        Arguments
        ---------
        name : str
            Species name
        species_type : SpeciesType
            Type of species, either BULK or WALL
        units : str
            Mass units for  this species
        atol : float, optional unless rtol is not None
            Absolute solver tolerance for this species, by default None
        rtol : float, optional unless atol is not None
            Relative solver tolerance for this species, by default None
        note : NoteType, optional keyword
            Supplementary information regarding this variable, by default None
            (see also :class:`~wntr.epanet.util.ENcomment`)
        diffusivity : float, optional
            Diffusivity of this species in water

        Raises
        ------
        KeyExistsError
            If a variable with this name already exists
        ValueError
            If `atol` or `rtol` ≤ 0

        Returns
        -------
        Species
            New species
        """
        if name in self._rxn_system:
            raise KeyExistsError("Variable named {} already exists in model as type {}".format(name, self._rxn_system._vars.get_groupname(name)))
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

    def remove_species(self, variable_or_name):
        """Remove a species from the model

        Removes from both the reaction_system and the network_data.

        Parameters
        ----------
        variable_or_name : Species or str
            Species (or name of the species) to be removed

        Raises
        ------
        KeyError
            If `variable_or_name` is not a species in the model
        """
        name = str(variable_or_name)
        if name not in self.reaction_system.species:
            raise KeyError('The specified variable is not a registered species in the reaction system')
        self.network_data.remove_species(name)
        self.reaction_system.__delitem__(name)

    def add_constant(self, name: str, value: float, units: str = None, note: NoteType = None) -> Constant:
        """Add a constant coefficient to the model

        Arguments
        ---------
        name : str
            Name of the coefficient
        value : float
            Constant value of the coefficient
        units : str, optional
            Units for this coefficient, by default None
        note : NoteType, optional
            Supplementary information regarding this variable, by default None

        Raises
        ------
        KeyExistsError
            Variable with this name already exists

        Returns
        -------
        Constant
            New constant coefficient
        """
        if name in self._rxn_system:
            raise KeyExistsError("Variable named {} already exists in model as type {}".format(name, self._rxn_system._vars.get_groupname(name)))
        new = Constant(name=name, value=value, units=units, note=note, _vars=self._rxn_system)
        self.reaction_system.add_variable(new)
        return new

    def remove_constant(self, variable_or_name):
        """Remove a constant coefficient from the model

        Parameters
        ----------
        variable_or_name : Constant or str
            Constant (or name of the constant) to be removed

        Raises
        ------
        KeyError
            If `variable_or_name` is not a constant coefficient in the model
        """
        name = str(variable_or_name)
        if name not in self.reaction_system.constants:
            raise KeyError('The specified variable is not a registered constant in the reaction system')
        self.reaction_system.__delitem__(name)

    def add_parameter(self, name: str, global_value: float, units: str = None, note: NoteType = None) -> Parameter:
        """Add a parameterized coefficient to the model

        Arguments
        ---------
        name : str
            Name of the parameter
        global_value : float
            Global value of the coefficient (can be overridden for specific
            pipes/tanks)
        units : str, optional
            Units for the coefficient, by default None
        note : NoteType, optional keyword
            Supplementary information regarding this variable, by default None
            (see also :class:`~wntr.epanet.util.ENcomment`).

        Raises
        ------
        KeyExistsError
            If a variable with this name already exists

        Returns
        -------
        Parameter
            New parameterized coefficient
        """
        if name in self._rxn_system:
            raise KeyExistsError("Variable named {} already exists in model as type {}".format(name, self._rxn_system._vars.get_groupname(name)))
        pv = self.network_data.init_new_parameter(name)
        new = Parameter(name=name, global_value=global_value, units=units, note=note, _vars=self._rxn_system, _vals=pv)
        self.reaction_system.add_variable(new)
        return new

    def remove_parameter(self, variable_or_name):
        """Remove a parameterized coefficient from the model

        Parameters
        ----------
        variable_or_name : Parameter or str
            Parameter (or name of the parameter) to be removed

        Raises
        ------
        KeyError
            If `variable_or_name` is not a parameter in the model
        """
        name = str(variable_or_name)
        if name not in self.reaction_system.parameters:
            raise KeyError('The specified variable is not a registered parameter in the reaction system')
        self.network_data.remove_parameter(name)
        self.reaction_system.__delitem__(name)

    def add_term(self, name: str, expression: str, note: NoteType = None) -> Term:
        """Add a named expression (term) to the model

        Parameters
        ----------
        name : str
            Name of the functional term to be added
        expression : str
            Expression that the term defines
        note : NoteType, optional keyword
            Supplementary information regarding this variable, by default None
            (see also :class:`~wntr.epanet.util.ENcomment`)

        Raises
        ------
        KeyExistsError
            if a variable with this name already exists

        Returns
        -------
        Term
            New term
        """
        if name in self._rxn_system:
            raise KeyError("Variable named {} already exists in model as type {}".format(name, self._rxn_system._vars.get_groupname(name)))
        new = Term(name=name, expression=expression, note=note, _vars=self._rxn_system)
        self.reaction_system.add_variable(new)
        return new

    def remove_term(self, variable_or_name):
        """Remove a named expression (term) from the model

        Parameters
        ----------
        variable_or_name : Term or str
            Term (or name of the term) to be deleted

        Raises
        ------
        KeyError
            If `variable_or_name` is not a term in the model
        """
        name = str(variable_or_name)
        if name not in self.reaction_system.terms:
            raise KeyError('The specified variable is not a registered term in the reaction system')
        self.reaction_system.__delitem__(name)

    def add_reaction(self, species_name: Union[Species, str], reaction_type: ReactionType, expression_type: ExpressionType, expression: str, note: NoteType = None) -> ReactionBase:
        """Add a reaction to a species in the model

        Note that all species need to have both a pipe and tank reaction
        defined unless all species are bulk species and the tank reactions are
        identical to the pipe reactions. However, it is not recommended that
        users take this approach.

        Once added, access the reactions from the species' object.

        Arguments
        ---------
        species_name : Species or str
            Species (or name of species) the reaction is being defined for
        reaction_type: ReactionType
            Reaction type (location), from {PIPE, TANK}
        expression_type : ExpressionType
            Expression type (left-hand-side) of the equation, from {RATE,
            EQUIL, FORMULA}
        expression : str
            Expression defining the reaction
        note : NoteType, optional keyword
            Supplementary information regarding this reaction, by default None
            (see also :class:`~wntr.epanet.util.ENcomment`)

        Raises
        ------
        TypeError
            If a variable that is not species is passed

        Returns
        -------
        MsxReactionSystem
            New reaction object
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
        """Remove a reaction at a specified location from a species

        Parameters
        ----------
        species : Species or str
            Species (or name of the species) of the reaction to remove
        reaction_type : ReactionType
            Reaction type (location) of the reaction to remove
        """
        reaction_type = ReactionType.get(reaction_type, allow_none=False)
        species_name = str(species_name)
        del self.reaction_system._rxns[reaction_type.name.lower()][species_name]

    def to_dict(self) -> dict:
        """Dictionary representation of the MsxModel"""
        from wntr import __version__

        return {
            "version": "wntr-{}".format(__version__),
            "name": self.name,
            "title": self.title,
            "description": self.description if self.description is None or "\n" not in self.description else self.description.splitlines(),
            "references": self.references.copy(),
            "reaction_system": self.reaction_system.to_dict(),
            "network_data": self.network_data.to_dict(),
            "options": self.options.to_dict(),
        }

    @classmethod
    def from_dict(cls, data) -> "MsxModel":
        """Create a new multi-species water quality model from a dictionary
        
        Parameters
        ----------
        data : dict
            Model data
        """
        from wntr import __version__

        ver = data.get("version", None)
        if ver != 'wntr-{}'.format(__version__):
            logger.warn("Importing from a file created by a different version of wntr, compatibility not guaranteed")
            # warnings.warn("Importing from a file created by a different version of wntr, compatibility not guaranteed")
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
