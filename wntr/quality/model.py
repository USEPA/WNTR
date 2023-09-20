# -*- coding: utf-8 -*-
"""
Water quality reactions model.

.. rubric:: Contents

.. autosummary::

    MultispeciesReactionModel

"""

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

from wntr.network.elements import Source
from wntr.utils.disjoint_mapping import DisjointMapping, KeyExistsError

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

import wntr.quality.io
from wntr.network.model import WaterNetworkModel
from wntr.utils.citations import Citation

from .base import (
    HYDRAULIC_VARIABLES,
    SYMPY_RESERVED,
    DynamicsType,
    LinkedVariablesMixin,
    LocationType,
    ReactionDynamics,
    AbstractReactionModel,
    ReactionVariable,
    VariableType,
)
from .dynamics import EquilibriumDynamics, FormulaDynamics, RateDynamics
from .options import MultispeciesOptions
from .variables import (
    BulkSpecies,
    Coefficient,
    Constant,
    InternalVariable,
    OtherTerm,
    Parameter,
    Species,
    WallSpecies,
)

logger = logging.getLogger(__name__)

__all__ = ["MultispeciesReactionModel"]


class MultispeciesReactionModel(AbstractReactionModel):
    """Water quality reactions model object.

    Parameters
    ----------
    msx_file_name : str, optional
        The name of the MSX input file to read

    """

    def __init__(self, msx_file_name=None):
        self.name: str = None
        """A one-line title for the model"""

        self.title: str = None
        """The title line from the MSX file"""

        self._msxfile: str = msx_file_name
        """The original filename"""

        self._citations: List[Union[Citation, str]] = list()
        """A list of citations for the sources of this model's dynamics"""

        self._allow_sympy_reserved_names: InitVar[bool] = True
        """Allow sympy reserved names (I, E, pi)"""

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

        self._sources: Dict[str, Dict[str, Source]] = dict()
        self._inital_quality: Dict[str, Dict[str, Dict[str, float]]] = dict()
        self._patterns: Dict[str, Any] = dict()
        self._report = list()

        for v in HYDRAULIC_VARIABLES:
            self._variables[v["name"]] = InternalVariable(v["name"], note=v["note"])
        if not self._allow_sympy_reserved_names:
            for name in SYMPY_RESERVED:
                self._variables[name] = InternalVariable(name, note="sympy reserved name")
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

    @property
    def variable_name_list(self) -> List[str]:
        """A list of all defined variable names"""
        return list(self._variables.keys())

    @property
    def species_name_list(self) -> List[str]:
        """A list of all defined species names"""
        return list(self._species.keys())

    @property
    def coefficient_name_list(self) -> List[str]:
        """A list of all defined coefficient names"""
        return list(self._coeffs.keys())

    @property
    def other_term_name_list(self) -> List[str]:
        """A list of all defined function (MSX 'terms') names"""
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
        var_or_type : RxnVariable or RxnVariableType
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
            if isinstance(__variable, LinkedVariablesMixin):
                __variable._variable_registry = self
            if typ is VariableType.BULK or typ is VariableType.WALL:
                self._variables.add_item_to_group("species", name, __variable)
                self._inital_quality[name] = dict(global_value=None, nodes=dict(), links=dict())
                self._sources[name] = dict()
            elif typ is VariableType.CONST or typ is VariableType.PARAM:
                self._variables.add_item_to_group("coeffs", name, __variable)
            elif typ is VariableType.TERM:
                self._variables.add_item_to_group("funcs", name, __variable)
            else:
                self._variables.add_item_to_group(None, name, __variable)

    def add_species(
        self,
        species_type: Union[str, Literal[VariableType.BULK], Literal[VariableType.WALL]],
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
        species_type : BULK or WALL
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
            var = BulkSpecies(name=name, units=units, atol=atol, rtol=rtol, note=note, variable_registry=self)
        elif species_type is VariableType.WALL:
            var = WallSpecies(name=name, units=units, atol=atol, rtol=rtol, note=note, variable_registry=self)
        self._species[name] = var
        self._inital_quality[name] = dict([("global", None), ("nodes", dict()), ("links", dict())])
        self._sources[name] = dict()
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

    def add_coefficient(
        self, coeff_type: Union[str, Literal[VariableType.CONST], Literal[VariableType.PARAM]], name: str, global_value: float, note: str = None, units: str = None, **kwargs
    ) -> Coefficient:
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
            var = Constant(name=name, global_value=global_value, note=note, units=units, variable_registry=self)
        elif coeff_type is VariableType.PARAM:
            var = Parameter(name=name, global_value=global_value, note=note, units=units, variable_registry=self, **kwargs)
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
        return self.add_coefficient(VariableType.PARAM, name=name, global_value=global_value, note=note, units=units, _pipe_values=pipe_values, _tank_values=tank_values)

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
        var = OtherTerm(name=name, expression=expression, note=note, variable_registry=self)
        self._terms[name] = var
        return var

    def remove_variable(self, name: str):
        """Remove a variable from the model.

        Parameters
        ----------
        name : str
            variable name
        """
        if name in self._inital_quality.keys():
            self._inital_quality.__delitem__(name)
        if name in self._sources.keys():
            self._sources.__delitem__(name)
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
            new = EquilibriumDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
        elif dynamics is DynamicsType.RATE:
            new = RateDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
        elif dynamics is DynamicsType.FORMULA:
            new = FormulaDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
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
        species = str(species)
        location = LocationType.get(location)
        if location == LocationType.PIPE:
            return self._pipe_dynamics.get(species, None)
        elif location == LocationType.TANK:
            return self._tank_dynamics.get(species, None)

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

    def add_pattern(self, name, pat):
        self._patterns[name] = pat

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
