# -*- coding: utf-8 -*-
"""
Water quality reactions model.

TODO: FIXME: Make sure that we throw the same errors (text/number) as MSX would throw

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

from ..utils.citations import Citation
from .base import (
    HYDRAULIC_VARIABLES,
    SYMPY_RESERVED,
    DisjointMapping,
    LinkedVariablesMixin,
    RxnDynamicsType,
    RxnLocationType,
    RxnModelRegistry,
    RxnReaction,
    RxnVariable,
    RxnVariableType,
    VariableNameExistsError,
)
from .dynamics import EquilibriumDynamics, FormulaDynamics, RateDynamics
from .options import RxnOptions
from .variables import (
    BulkSpecies,
    Coefficient,
    Constant,
    InternalVariable,
    Parameter,
    Species,
    OtherTerm,
    WallSpecies,
)

logger = logging.getLogger(__name__)


@dataclass
class WaterQualityReactionsModel(RxnModelRegistry):
    """Water quality reactions model object.

    Parameters
    ----------
    title : str, optional
        The title of reaction model
    desc : str, optional
        A long description of the model
    filename : str, optional
        The original filename
    citations : list of Citation or str, optional
        It is appropriate to cite sources for water quality models
    allow_sympy_reserved_names : bool, optional
        Should the extra names from sympy be excluded, by default False
    options : RxnOptions, optional
        Reaction MSX options, by default a new object
    _wn : WaterNetworkModel
        The water network model to use, by default None
    """

    # FIXME: Make the __init__ just minimal, with a filename
    # do the rest of stuff directly on the MSX object, make it as
    # close to WNM as possible

    title: str = None
    """A one-line title for the model"""
    
    desc: str = None
    """A multi-line string describing the model"""
    
    filename: str = None
    """The original filename"""

    citations: List[Union[Citation, str]] = "you ought to provide citations for your model"
    """A list of citations for the sources of this model's dynamics"""
    
    allow_sympy_reserved_names: InitVar[bool] = False
    """Allow sympy reserved names (I, E, pi)"""
    
    options: InitVar[RxnOptions] = None
    """A link to the options object"""
    
    _wn: WaterNetworkModel = None
    """A link to a water network model"""

    def __post_init__(self, allow_sympy_reserved_names=False, options=None):
        if self._wn is not None and not isinstance(self._wn, WaterNetworkModel):
            raise TypeError("Did not receive a WaterNetworkModel or None as first argument, got {}".format(self._wn))
        if isinstance(options, property):
            options = RxnOptions()
        elif not isinstance(options, RxnOptions):
            options = RxnOptions.factory(options)
        self._options = options
        if isinstance(self.citations, str):
            self.citations = [self.citations]
        elif isinstance(self.citations, Citation):
            self.citations = [self.citations]

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
        if not allow_sympy_reserved_names:
            for name in SYMPY_RESERVED:
                self._variables[name] = InternalVariable(name, note="sympy reserved name")

    def _is_variable_registered(self, var_or_name: Union[str, RxnVariable]) -> bool:
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
    def function_name_list(self) -> List[str]:
        """A list of all defined function (MSX 'terms') names"""
        return list(self._terms.keys())

    def variables(self, var_type: RxnVariableType = None):
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
        var_type = RxnVariableType.factory(var_type)
        for v in self._variables.values():
            if var_type is not None and v.var_type != var_type:
                continue
            yield v

    def add_variable(self, var_or_type: Union[RxnVariable, RxnVariableType], name: str = None, **kwargs):
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
        if not isinstance(var_or_type, (RxnVariable,)):
            try:
                var_or_type = RxnVariableType.factory(var_or_type)
            except Exception as e:
                raise TypeError("Cannot add an object that is not a RxnVariable subclass or create a new object without a valid var_type") from e
            if name is None:
                raise ValueError("When adding a new variable, a name must be supplied")
            typ = var_or_type
            if typ is RxnVariableType.BULK or typ is RxnVariableType.WALL:
                self.add_species(var_or_type, name, **kwargs)
            elif typ is RxnVariableType.CONST or typ is RxnVariableType.PARAM:
                self.add_coefficient(var_or_type, name, **kwargs)
            elif typ is RxnVariableType.TERM:
                self.add_other_term(var_or_type, name, **kwargs)
            else:
                raise TypeError("Cannot create new objects of the INTERNAL type using this function")
        else:
            if name is None or len(kwargs) > 0:
                raise ValueError("When adding an existing variable object, no other arguments may be supplied")
            __variable = var_or_type
            if self._is_variable_registered(__variable):
                raise VariableNameExistsError("A variable with this name already exists in the model")
            typ = __variable.var_type
            name = __variable.name
            if isinstance(__variable, LinkedVariablesMixin):
                __variable._variable_registry = self
            if typ is RxnVariableType.BULK or typ is RxnVariableType.WALL:
                self._variables.add_item_to_group("species", name, __variable)
                self._inital_quality[name] = dict(global_value=None, nodes=dict(), links=dict())
                self._sources[name] = dict()
            elif typ is RxnVariableType.CONST or typ is RxnVariableType.PARAM:
                self._variables.add_item_to_group("coeffs", name, __variable)
            elif typ is RxnVariableType.TERM:
                self._variables.add_item_to_group("funcs", name, __variable)
            else:
                self._variables.add_item_to_group(None, name, __variable)

    def add_species(
        self,
        species_type: Union[str, Literal[RxnVariableType.BULK], Literal[RxnVariableType.WALL]],
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
        species_type = RxnVariableType.factory(species_type)
        if species_type not in [RxnVariableType.BULK, RxnVariableType.WALL]:
            raise ValueError("Species must be BULK or WALL, got {:s}".format(species_type))
        if self._is_variable_registered(name):
            raise VariableNameExistsError("The variable {} already exists in this model".format(name))
        if (atol is None) ^ (rtol is None):
            raise TypeError("atol and rtol must be the same type, got {} and {}".format(atol, rtol))
        if species_type is RxnVariableType.BULK:
            var = BulkSpecies(name=name, units=units, atol=atol, rtol=rtol, note=note, variable_registry=self)
        elif species_type is RxnVariableType.WALL:
            var = WallSpecies(name=name, units=units, atol=atol, rtol=rtol, note=note, variable_registry=self)
        self._species[name] = var
        self._inital_quality[name] = dict([('global', None), ('nodes', dict()), ('links', dict())])
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
        return self.add_species(RxnVariableType.BULK, name, units, atol, rtol, note)

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
        return self.add_species(RxnVariableType.WALL, name, units, atol, rtol, note)

    def add_coefficient(
        self, coeff_type: Union[str, Literal[RxnVariableType.CONST], Literal[RxnVariableType.PARAM]], name: str, global_value: float, note: str = None, units: str = None, **kwargs
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
        coeff_type = RxnVariableType.factory(coeff_type)
        if coeff_type not in [RxnVariableType.CONST, RxnVariableType.PARAM]:
            raise ValueError("coeff_type must be CONST or PARAM, got {:s}".format(coeff_type))
        if self._is_variable_registered(name):
            raise VariableNameExistsError("The variable {} already exists in this model".format(name))
        if coeff_type is RxnVariableType.CONST:
            var = Constant(name=name, global_value=global_value, note=note, units=units, variable_registry=self)
        elif coeff_type is RxnVariableType.PARAM:
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
        return self.add_coefficient(RxnVariableType.CONST, name=name, global_value=global_value, note=note, units=units)

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
        return self.add_coefficient(RxnVariableType.PARAM, name=name, global_value=global_value, note=note, units=units, _pipe_values=pipe_values, _tank_values=tank_values)

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
            raise VariableNameExistsError("The variable {} already exists in this model".format(name))
        var = OtherTerm(name=name, expression=expression, note=note, variable_registry=self)
        self._terms[name] = var
        return var

    def remove_variable(self, name: str):
        if name in self._inital_quality.keys():
            self._inital_quality.__delitem__(name)
        if name in self._sources.keys():
            self._sources.__delitem__(name)
        return self._variables.__delitem__(name)

    def get_variable(self, name: str) -> RxnVariable:
        return self._variables[name]

    def reactions(self, location: RxnLocationType = None):
        """A generator for iterating through reactions in the model.

        Parameters
        ----------
        location : RxnLocationType, optional
            limit results to reactions within location, by default None

        Yields
        ------
        RxnReaction
            a reaction defined within the model
        """
        location = RxnLocationType.factory(location)
        for v in self._dynamics.values():
            if location is not None and v.location != location:
                continue
            yield v

    def add_reaction(self, location: RxnLocationType, species: Union[str, Species], dynamics: Union[str, int, RxnDynamicsType], expression: str, note: str = None):
        # TODO: accept a "both" or "all" value for location
        location = RxnLocationType.factory(location)
        species = str(species)
        if species not in self._species.keys():
            raise ValueError("The species {} does not exist in the model, failed to add reaction.".format(species))
        _key = RxnReaction.to_key(species, location)
        if _key in self._dynamics.keys():
            raise RuntimeError("The species {} already has a {} reaction defined. Use set_reaction instead.")
        dynamics = RxnDynamicsType.factory(dynamics)
        new = None
        if dynamics is RxnDynamicsType.EQUIL:
            new = EquilibriumDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
        elif dynamics is RxnDynamicsType.RATE:
            new = RateDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
        elif dynamics is RxnDynamicsType.FORMULA:
            new = FormulaDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
        else:
            raise ValueError("Invalid dynamics type, {}".format(dynamics))
        if location is RxnLocationType.PIPE:
            self._pipe_dynamics[str(new)] = new
        elif location is RxnLocationType.TANK:
            self._tank_dynamics[str(new)] = new
        else:
            raise ValueError("Invalid location type, {}".format(location))
        return new

    def add_pipe_reaction(self, species: Union[str, Species], dynamics: Union[str, int, RxnDynamicsType], expression: str, note: str = None) -> RxnReaction:
        return self.add_reaction(RxnLocationType.PIPE, species=species, dynamics=dynamics, expression=expression, note=note)

    def add_tank_reaction(self, species: Union[str, Species], dynamics: Union[str, int, RxnDynamicsType], expression: str, note: str = None) -> RxnReaction:
        return self.add_reaction(RxnLocationType.TANK, species=species, dynamics=dynamics, expression=expression, note=note)

    def remove_reaction(self, species: Union[str, Species], location: Union[str, int, RxnLocationType, Literal["all"]]):
        if location != "all":
            location = RxnLocationType.factory(location)
        species = str(species)
        if location is None:
            raise TypeError('location cannot be None when removing a reaction. Use "all" for all locations.')
        elif location == "all":
            name = RxnReaction.to_key(species, RxnLocationType.PIPE)
            try:
                self._pipe_dynamics.__delitem__(name)
            except KeyError:
                pass
            name = RxnReaction.to_key(species, RxnLocationType.TANK)
            try:
                self._tank_dynamics.__delitem__(name)
            except KeyError:
                pass
        elif location is RxnLocationType.PIPE:
            name = RxnReaction.to_key(species, RxnLocationType.PIPE)
            try:
                self._pipe_dynamics.__delitem__(name)
            except KeyError:
                pass
        elif location is RxnLocationType.TANK:
            name = RxnReaction.to_key(species, RxnLocationType.TANK)
            try:
                self._tank_dynamics.__delitem__(name)
            except KeyError:
                pass
        else:
            raise ValueError("Invalid location, {}".format(location))

    def get_reaction(self, species, location):
        species = str(species)
        location = RxnLocationType.factory(location)
        if location == RxnLocationType.PIPE:
            return self._pipe_dynamics.get(species, None)
        elif location == RxnLocationType.TANK:
            return self._tank_dynamics.get(species, None)

    def init_printing(self, *args, **kwargs):
        """Call sympy.init_printing"""
        init_printing(*args, **kwargs)

    @property
    def options(self) -> RxnOptions:
        """The multispecies reaction model options."""
        return self._options

    @options.setter
    def options(self, value):
        if not isinstance(value, RxnOptions):
            raise TypeError("Expected a RxnOptions object, got {}".format(type(value)))
        self._options = value

    def link_water_network_model(self, wn: WaterNetworkModel):
        self._wn = wn

    def add_pattern(self, name, pat):
        self._patterns[name] = pat

    def to_dict(self) -> dict:
        rep = dict()
        rep["version"] = 'wntr.reactions-0.0.1'
        rep["title"] = self.title
        rep["desc"] = self.desc
        rep["original_filename"] = self.filename
        rep["citations"] = [(c.to_dict() if isinstance(c, Citation) else c) for c in self.citations]
        rep["options"] = self._options.to_dict()
        rep["variables"] = dict()
        rep["variables"]["species"] = [v.to_dict() for v in self._species.values()]
        rep["variables"]["coefficients"] = [v.to_dict() for v in self._coeffs.values()]
        rep["variables"]["other_terms"] = [v.to_dict() for v in self._terms.values()]
        rep["reactions"] = dict()
        rep["reactions"]["pipes"] = [v.to_dict() for v in self._pipe_dynamics.values()]
        rep["reactions"]["tanks"] = [v.to_dict() for v in self._tank_dynamics.values()]
        rep["patterns"] = self._patterns.copy()
        rep["initial_quality"] = self._inital_quality.copy()
        # rep["sources"] = dict()
        # for sp, v in self._sources:
        #     if v is not None and len(v) > 0:
        #         rep["sources"][sp] = dict()
        #         for node, source in v.items():
        #             rep["sources"][sp][node] = source.to_dict()
        return rep
