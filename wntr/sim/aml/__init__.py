"""WNTR's algebraic modeling language module (SWIG)."""

from .expr import Var, Param, exp, log, sin, cos, tan, asin, acos, atan, inequality, sign, abs, value, ConditionalExpression
from .aml import Model, ParamDict, VarDict, ConstraintDict, Constraint

