# -*- coding: utf-8 -*-
"""
Water quality reactions base classes

"""

import logging
import warnings
from collections.abc import MutableMapping
from dataclasses import InitVar, dataclass, field, asdict
from enum import Enum, IntFlag
from typing import Any, ClassVar, Dict, Generator, Hashable, Iterator, List, Set, Tuple, Union

import sympy
from sympy import Float, Symbol, symbols, init_printing
from sympy.parsing import parse_expr
from sympy.parsing.sympy_parser import standard_transformations, convert_xor

from wntr.network.model import WaterNetworkModel
from .base import ReactionDynamics, ReactionVariable
from .variables import InternalVariable
from .options import RxnOptions
from .base import DynamicsRegistry, VariableRegistry, RxnExprType, RxnLocType, RxnVarType, DisjointMapping, RESERVED_NAMES, SYMPY_RESERVED

class MultispeciesWaterQualityModel(DynamicsRegistry, VariableRegistry):

    def __init__(self, title: str = None, desc: str = None, allow_sympy_reserved=False):
        self.title: str = title
        self.desc: str = desc
        self.options = RxnOptions()
        self._wn: WaterNetworkModel = None

        self._variables: Dict[str, ReactionVariable] = dict()
        self._species = DisjointMapping(self._variables)
        self._coeff = DisjointMapping(self._variables)
        self._terms = DisjointMapping(self._variables)

        self._dynamics: Dict[str, ReactionDynamics] = dict()
        self._pipe_dynamics = DisjointMapping(self._dynamics)
        self._tank_dynamics = DisjointMapping(self._dynamics)

        for name in RESERVED_NAMES:
            self._variables[name] = InternalVariable(name)
        if not allow_sympy_reserved:
            for name in SYMPY_RESERVED:
                self._variables[name] = InternalVariable(name)

    def link_water_network_model(self, wn: WaterNetworkModel):
        self._wn = wn

    def variables(self, var_type=None):
        var_type = RxnVarType.make(var_type)
        for k, v in self._variables.items():
            if var_type is not None and v.var_type != var_type:
                continue
            yield k, v

    def dynamics(self, location=None):
        location = RxnLocType.make(location)
        for k, v in self._dynamics.items():
            if location is not None and v.location != location:
                continue
            yield k, v
        
    def add_dynamics(self, dyn: ReactionDynamics):
        return super().add_dynamics(dyn)
    
    def add_variable(self, var: ReactionVariable):
        return super().add_variable(var)
    
    def del_dynamics(self, species, location):
        return super().del_dynamics(species, location)
    
    def del_variable(self, name: str):
        return super().del_variable(name)
    
    def get_dynamics(self, species, location):
        species = str(species)
        location = RxnLocType.make(location)
        if location == RxnLocType.PIPE:
            return self._pipe_dynamics.get(species, None)
        elif location == RxnLocType.TANK:
            return self._tank_dynamics.get(species, None)
        
    def get_variable(self, name: str) -> ReactionVariable:
        return self._variables[name]
