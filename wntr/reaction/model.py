# -*- coding: utf-8 -*-
"""
Water quality reactions base classes

"""

import logging
import warnings
from collections.abc import MutableMapping
from dataclasses import InitVar, asdict, dataclass, field
from enum import Enum, IntFlag
from typing import Any, ClassVar, Dict, Generator, Hashable, Iterator, List, Literal, Set, Tuple, Union

import sympy
from sympy import Float, Symbol, init_printing, symbols
from sympy.parsing import parse_expr
from sympy.parsing.sympy_parser import convert_xor, standard_transformations

from wntr.network.model import WaterNetworkModel
from wntr.reaction.dynamics import EquilibriumDynamics, FormulaDynamics, RateDynamics

from .base import (
    HYDRAULIC_VARIABLES,
    RESERVED_NAMES,
    SYMPY_RESERVED,
    DisjointMapping,
    DisjointMappingGroup,
    ReactionDynamics,
    ReactionRegistry,
    ReactionVariable,
    RxnExprType,
    RxnLocType,
    RxnVarType,
    VariableNameExistsError,
    VariableRegistry,
)
from .options import RxnOptions
from .variables import BulkSpecies, Coefficient, Constant, InternalVariable, OtherTerm, Parameter, Species, WallSpecies


@dataclass
class WaterQualityReactionsModel(ReactionRegistry, VariableRegistry):
    """Water quality reactions model object.

    Parameters
    ----------
    title : str
        The title of reaction model
    desc : str
        A long description of the model
    citations : 
    """
    filename: str = None
    title: str = None
    desc: str = None
    citations: Union[List[str], str] = "you ought to provide citations for this model"
    allow_sympy_reserved_names: InitVar[bool] = False
    options: InitVar[RxnOptions] = None
    _wn: WaterNetworkModel = None

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
        self._variables: DisjointMapping = DisjointMapping()
        self._species = self._variables.add_disjoint_group('species')
        self._coeff = self._variables.add_disjoint_group('coeff')
        self._terms = self._variables.add_disjoint_group('terms')

        self._dynamics: DisjointMapping = DisjointMapping()
        self._pipe_dynamics = self._dynamics.add_disjoint_group('pipe')
        self._tank_dynamics = self._dynamics.add_disjoint_group('tank')

        self._usage: Dict[str, Set[str]] = dict()

        self._sources: Dict[str, float] = dict()
        self._inital_quality = list()
        self._wn: WaterNetworkModel = None
        self._patterns: Dict[str, Any] = dict()
        self._report = list()

        for v in HYDRAULIC_VARIABLES:
            self._variables[v['name']] = InternalVariable(v['name'], note=v['note'])
        if not allow_sympy_reserved_names:
            for name in SYMPY_RESERVED:
                self._variables[name] = InternalVariable(name, note="sympy reserved name")

    def _is_variable_registered(self, var_or_name: Union[str, ReactionVariable]) -> bool:
        name = str(var_or_name)
        if name in self._variables:
            return True
        return False

    @property
    def variable_name_list(self) -> List[str]:
        return list(self._variables.keys())

    @property
    def species_name_list(self) -> List[str]:
        return list(self._species.keys())

    @property
    def coefficient_name_list(self) -> List[str]:
        return list(self._coeff.keys())

    @property
    def other_term_name_list(self) -> List[str]:
        return list(self._terms.keys())

    def variables(self, var_type=None):
        var_type = RxnVarType.make(var_type)
        for k, v in self._variables.items():
            if var_type is not None and v.var_type != var_type:
                continue
            yield k, v

    def add_species(
        self, species_type: Union[str, Literal[RxnVarType.BULK], Literal[RxnVarType.WALL]], name: str, unit: str, atol: float = None, rtol: float = None, note: str = None
    ) -> Species:
        species_type = RxnVarType.make(species_type)
        if species_type not in [RxnVarType.BULK, RxnVarType.WALL]:
            raise ValueError("Species must be BULK or WALL, got {:s}".format(species_type))
        if self._is_variable_registered(name):
            raise VariableNameExistsError("The variable {} already exists in this model".format(name))
        if (atol is None) ^ (rtol is None):
            raise TypeError("atol and rtol must be the same type, got {} and {}".format(atol, rtol))
        if species_type is RxnVarType.BULK:
            var = BulkSpecies(name, unit, atol, rtol, note, self)
        elif species_type is RxnVarType.WALL:
            var = WallSpecies(name, unit, atol, rtol, note, self)
        self._species[name] = var
        return var

    def add_bulk_species(self, name: str, unit: str, atol: float = None, rtol: float = None, note: str = None) -> BulkSpecies:
        return self.add_species(RxnVarType.BULK, name, unit, atol, rtol, note)

    def add_wall_species(self, name: str, unit: str, atol: float = None, rtol: float = None, note: str = None) -> WallSpecies:
        return self.add_species(RxnVarType.WALL, name, unit, atol, rtol, note)

    def add_coefficient(
        self, coeff_type: Union[str, Literal[RxnVarType.CONST], Literal[RxnVarType.PARAM]], name: str, global_value: float, note: str = None, unit: str = None, **kwargs
    ) -> Coefficient:
        coeff_type = RxnVarType.make(coeff_type)
        if coeff_type not in [RxnVarType.CONST, RxnVarType.PARAM]:
            raise ValueError("Species must be CONST or PARAM, got {:s}".format(coeff_type))
        if self._is_variable_registered(name):
            raise VariableNameExistsError("The variable {} already exists in this model".format(name))
        if coeff_type is RxnVarType.CONST:
            var = Constant(name=name, global_value=global_value, note=note, unit=unit, variable_registry=self)
        elif coeff_type is RxnVarType.PARAM:
            var = Parameter(name=name, global_value=global_value, note=note, unit=unit, variable_registry=self, **kwargs)
        self._coeff[name] = var
        return var

    def add_constant_coeff(self, name: str, global_value: float, note: str = None, unit: str = None) -> Constant:
        return self.add_coefficient(RxnVarType.CONST, name=name, global_value=global_value, note=note, unit=unit)

    def add_parameterized_coeff(
        self, name: str, global_value: float, note: str = None, unit: str = None, pipe_values: Dict[str, float] = None, tank_values: Dict[str, float] = None
    ) -> Parameter:
        return self.add_coefficient(RxnVarType.PARAM, name=name, global_value=global_value, note=note, unit=unit, _pipe_values=pipe_values, _tank_values=tank_values)

    def add_other_term(self, name: str, expression: str, note: str = None) -> OtherTerm:
        if self._is_variable_registered(name):
            raise VariableNameExistsError("The variable {} already exists in this model".format(name))
        var = OtherTerm(name=name, expression=expression, note=note, variable_registry=self)
        self._terms[name] = var
        return var

    def del_variable(self, name: str):
        return self._variables.__delitem__(name)

    def get_variable(self, name: str) -> ReactionVariable:
        return self._variables[name]

    def reactions(self, location=None):
        location = RxnLocType.make(location)
        for k, v in self._dynamics.items():
            if location is not None and v.location != location:
                continue
            yield k, v

    def add_reaction(self, location: RxnLocType, species: Union[str, Species], dynamics: Union[str, int, RxnExprType], expression: str, note: str = None):
        location = RxnLocType.make(location)
        species = str(species)
        _key = ReactionDynamics.to_key(species, location)
        if _key in self._dynamics.keys():
            raise RuntimeError("The species {} already has a {} reaction defined. Use set_reaction instead.")
        dynamics = RxnExprType.make(dynamics)
        new = None
        if dynamics is RxnExprType.EQUIL:
            new = EquilibriumDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
        elif dynamics is RxnExprType.RATE:
            new = RateDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
        elif dynamics is RxnExprType.FORMULA:
            new = FormulaDynamics(species=species, location=location, expression=expression, note=note, variable_registry=self)
        else:
            raise ValueError("Invalid dynamics type, {}".format(dynamics))
        if location is RxnLocType.PIPE:
            self._pipe_dynamics[str(new)] = new
        elif location is RxnLocType.TANK:
            self._tank_dynamics[str(new)] = new
        else:
            raise ValueError("Invalid location type, {}".format(location))
        return new

    def add_pipe_reaction(self, species: Union[str, Species], dynamics: Union[str, int, RxnExprType], expression: str, note: str = None) -> ReactionDynamics:
        return self.add_reaction(RxnLocType.PIPE, species=species, dynamics=dynamics, expression=expression, note=note)

    def add_tank_reaction(self, species: Union[str, Species], dynamics: Union[str, int, RxnExprType], expression: str, note: str = None) -> ReactionDynamics:
        return self.add_reaction(RxnLocType.TANK, species=species, dynamics=dynamics, expression=expression, note=note)

    def del_reaction(self, species: Union[str, Species], location: Union[str, int, RxnLocType, Literal["all"]]):
        if location != "all":
            location = RxnLocType.make(location)
        species = str(species)
        if location is None:
            raise TypeError('location cannot be None when removing a reaction. Use "all" for all locations.')
        elif location == "all":
            name = ReactionDynamics.to_key(species, RxnLocType.PIPE)
            try:
                self._pipe_dynamics.__delitem__(name)
            except KeyError:
                pass
            name = ReactionDynamics.to_key(species, RxnLocType.TANK)
            try:
                self._tank_dynamics.__delitem__(name)
            except KeyError:
                pass
        elif location is RxnLocType.PIPE:
            name = ReactionDynamics.to_key(species, RxnLocType.PIPE)
            try:
                self._pipe_dynamics.__delitem__(name)
            except KeyError:
                pass
        elif location is RxnLocType.TANK:
            name = ReactionDynamics.to_key(species, RxnLocType.TANK)
            try:
                self._tank_dynamics.__delitem__(name)
            except KeyError:
                pass
        else:
            raise ValueError("Invalid location, {}".format(location))

    def get_reaction(self, species, location):
        species = str(species)
        location = RxnLocType.make(location)
        if location == RxnLocType.PIPE:
            return self._pipe_dynamics.get(species, None)
        elif location == RxnLocType.TANK:
            return self._tank_dynamics.get(species, None)

    def init_printing(self, *args, **kwargs):
        """Call sympy.init_printing(*args, **kwargs)"""
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