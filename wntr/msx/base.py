# coding: utf-8
"""
The wntr.msx.base module includes base classes for the multi-species water
quality model

Other than the enum classes, the classes in this module are all abstract
and/or mixin classes, and should not be instantiated directly.
"""

import logging
import os
from abc import ABC, abstractclassmethod, abstractmethod, abstractproperty
from enum import Enum
from typing import Any, Dict, Iterator, Generator
from wntr.epanet.util import NoteType

from wntr.utils.disjoint_mapping import DisjointMapping
from wntr.utils.enumtools import add_get

from numpy import (
    abs,
    arccos,
    arcsin,
    arctan,
    cos,
    cosh,
    exp,
    heaviside,
    log,
    log10,
    sign,
    sin,
    sinh,
    sqrt,
    tan,
    tanh,
)

def cot(x):
    return 1 / tan(x)

def arccot(x):
    return 1 / arctan(1 / x)

def coth(x):
    return 1 / tanh(x)

logger = logging.getLogger(__name__)

HYDRAULIC_VARIABLES = [
    {"name": "D", "note": "pipe diameter (feet or meters) "},
    {
        "name": "Kc",
        "note": "pipe roughness coefficient (unitless for Hazen-Williams or Chezy-Manning head loss formulas, millifeet or millimeters for Darcy-Weisbach head loss formula)",
    },
    {"name": "Q", "note": "pipe flow rate (flow units) "},
    {"name": "U", "note": "pipe flow velocity (ft/sec or m/sec) "},
    {"name": "Re", "note": "flow Reynolds number "},
    {"name": "Us", "note": "pipe shear velocity (ft/sec or m/sec) "},
    {"name": "Ff", "note": "Darcy-Weisbach friction factor "},
    {"name": "Av", "note": "Surface area per unit volume (area units/L) "},
    {"name": "Len", "note": "Pipe length (feet or meters)"},
]
"""Hydraulic variables defined in EPANET-MSX.
For reference, the valid values are provided in :numref:`table-msx-hyd-vars`.

.. _table-msx-hyd-vars:
.. table:: Valid hydraulic variables in multi-species quality model expressions.

    ============== ================================================
    **Name**       **Description**
    -------------- ------------------------------------------------
    ``D``          pipe diameter
    ``Kc``         pipe roughness coefficient
    ``Q``          pipe flow rate
    ``U``          pipe flow velocity
    ``Re``         flow Reynolds number
    ``Us``         pipe shear velocity
    ``Ff``         Darcy-Weisbach friction factor
    ``Av``         pipe surface area per unit volume
    ``Len``        pipe length
    ============== ================================================

:meta hide-value:
"""

EXPR_FUNCTIONS = dict(
    abs=abs,
    sgn=sign,
    sqrt=sqrt,
    step=heaviside,
    log=log,
    exp=exp,
    sin=sin,
    cos=cos,
    tan=tan,
    cot=cot,
    asin=arcsin,
    acos=arccos,
    atan=arctan,
    acot=arccot,
    sinh=sinh,
    cosh=cosh,
    tanh=tanh,
    coth=coth,
    log10=log10,
)
"""Mathematical functions available for use in expressions. See 
:numref:`table-msx-funcs` for a list and description of the 
different functions recognized. These names, case insensitive, are 
considered invalid when naming variables.

.. _table-msx-funcs:
.. table:: Functions defined for use in EPANET-MSX expressions.

    ============== ================================================================
    **Name**       **Description**
    -------------- ----------------------------------------------------------------
    ``abs``        absolute value
    ``sgn``        sign
    ``sqrt``       square-root
    ``step``       step function
    ``exp``        natural number, `e`, raised to a power
    ``log``        natural logarithm
    ``log10``      base-10 logarithm
    ``sin``        sine
    ``cos``        cosine
    ``tan``        tangent
    ``cot``        cotangent
    ``asin``       arcsine
    ``acos``       arccosine
    ``atan``       arctangent
    ``acot``       arccotangent
    ``sinh``       hyperbolic sine
    ``cosh``       hyperbolic cosine
    ``tanh``       hyperbolic tangent
    ``coth``       hyperbolic cotangent
    ``*``          multiplication
    ``/``          division
    ``+``          addition
    ``-``          negation and subtraction
    ``^``          power/exponents
    ``(``, ``)``   groupings and function parameters
    ============== ================================================================

:meta hide-value:
"""

RESERVED_NAMES = (
    tuple([v["name"] for v in HYDRAULIC_VARIABLES])
    + tuple([k.lower() for k in EXPR_FUNCTIONS.keys()])
    + tuple([k.upper() for k in EXPR_FUNCTIONS.keys()])
    + tuple([k.capitalize() for k in EXPR_FUNCTIONS.keys()])
)
"""WNTR reserved names. This includes the MSX hydraulic variables
(see :numref:`table-msx-hyd-vars`) and the MSX defined functions 
(see :numref:`table-msx-funcs`).

:meta hide-value:
"""

_global_dict = dict()
for k, v in EXPR_FUNCTIONS.items():
    _global_dict[k.lower()] = v
    _global_dict[k.capitalize()] = v
    _global_dict[k.upper()] = v
for v in HYDRAULIC_VARIABLES:
    _global_dict[v["name"]] = v["name"]


@add_get(abbrev=True)
class VariableType(Enum):
    """Type of reaction variable.

    The following types are defined, and aliases of just the first character
    are also defined.

    .. rubric:: Enum Members
    .. autosummary::

        SPECIES
        CONSTANT
        PARAMETER
        TERM
        RESERVED

    .. rubric:: Class Methods
    .. autosummary::
        :nosignatures:

        get

    """

    SPECIES = 3
    """Chemical or biological water quality species"""
    TERM = 4
    """Functional term, or named expression, for use in reaction expressions"""
    PARAMETER = 5
    """Reaction expression coefficient that is parameterized by tank or pipe"""
    CONSTANT = 6
    """Constant coefficient for use in reaction expressions"""
    RESERVED = 9
    """Variable that is either a hydraulic variable or other reserved word"""

    S = SPEC = SPECIES
    T = TERM
    P = PARAM = PARAMETER
    C = CONST = CONSTANT
    R = RES = RESERVED

    def __repr__(self):
        return repr(self.name)


@add_get(abbrev=True)
class SpeciesType(Enum):
    """Enumeration for species type

    .. warning:: These enum values are not the same as the MSX SpeciesType.

    .. rubric:: Enum Members

    .. autosummary::
        BULK
        WALL

    .. rubric:: Class Methods
    .. autosummary::
        :nosignatures:

        get

    """

    BULK = 1
    """Bulk species"""
    WALL = 2
    """Wall species"""

    B = BULK
    W = WALL

    def __repr__(self):
        return repr(self.name)
    

@add_get(abbrev=True)
class ReactionType(Enum):
    """Reaction type which specifies the location where the reaction occurs

    The following types are defined, and aliases of just the first character
    are also defined.

    .. rubric:: Enum Members
    .. autosummary::
        PIPE
        TANK

    .. rubric:: Class Methods
    .. autosummary::
        :nosignatures:

        get
    """

    PIPE = 1
    """Expression describes a reaction in pipes"""
    TANK = 2
    """Expression describes a reaction in tanks"""

    P = PIPE
    T = TANK

    def __repr__(self):
        return repr(self.name)
    

@add_get(abbrev=True)
class ExpressionType(Enum):
    """Type of reaction expression

    The following types are defined, and aliases of just the first character
    are also defined.

    .. rubric:: Enum Members
    .. autosummary::

        EQUIL
        RATE
        FORMULA

    .. rubric:: Class Methods
    .. autosummary::
        :nosignatures:

        get

    """

    EQUIL = 1
    """Equilibrium expressions where equation is being equated to zero"""
    RATE = 2
    """Rate expression where the equation expresses the rate of change of
    the given species with respect to time as a function of the other species
    in the model"""
    FORMULA = 3
    """Formula expression where the concentration of the named species is a
    simple function of the remaining species"""

    E = EQUIL
    R = RATE
    F = FORMULA

    def __repr__(self):
        return repr(self.name)


class ReactionBase(ABC):
    """Water quality reaction class.

    This is an abstract class for water quality reactions with partial concrete
    attribute and method definitions. All parameters and methods documented
    here must be defined by a subclass except for the following:

    .. rubric:: Concrete attributes

    The :meth:`__init__` method defines the following attributes concretely.
    Thus, a subclass should call :code:`super().__init__(species_name, note=note)`
    at the beginning of its own initialization.

    .. autosummary::

        ~ReactionBase._species_name
        ~ReactionBase.note

    .. rubric:: Concrete properties

    The species name is protected, and a reaction cannot be manually assigned
    a new species. Therefore, the following property is defined concretely.

    .. autosummary::

        species_name

    .. rubric:: Concrete methods

    The following methods are concretely defined, but can be overridden.

    .. autosummary::
        :nosignatures:

        __str__
        __repr__
    """

    def __init__(self, species_name: str, *, note: NoteType = None) -> None:
        """Reaction ABC init method.

        Make sure you call this method from your concrete subclass ``__init__`` method:
        
        .. code::
            
            super().__init__(species_name, note=note)

        Parameters
        ----------
        species_name : str
            Name of the chemical or biological species being modeled using this
            reaction
        note : (str | dict | ENcomment), optional keyword
            Supplementary information regarding this reaction, by default None
            (see-also :class:`~wntr.epanet.util.NoteType`)

        Raises
        ------
        TypeError
            If expression_type is invalid
        """
        if species_name is None:
            raise TypeError("The species_name cannot be None")
        self._species_name: str = str(species_name)
        """Protected name of the species"""
        self.note: NoteType = note
        """Optional note regarding the reaction (see :class:`~wntr.epanet.util.NoteType`)
        """

    @property
    def species_name(self) -> str:
        """Name of the species that has a reaction being defined."""
        return self._species_name

    @property
    @abstractmethod
    def reaction_type(self) -> Enum:
        """Reaction type (reaction location)."""
        raise NotImplementedError

    def __str__(self) -> str:
        """Return the name of the species and the reaction type, indicated by
        an arrow. E.g., 'HOCL->PIPE for chlorine reaction in pipes."""
        return "{}->{}".format(self.species_name, self.reaction_type.name)

    def __repr__(self) -> str:
        """Return a representation of the reaction from the dictionary
        representation - see :meth:`to_dict`"""
        return "{}(".format(self.__class__.__name__) + ", ".join(["{}={}".format(k, repr(getattr(self, k))) for k, v in self.to_dict().items()]) + ")"

    @abstractmethod
    def to_dict(self) -> dict:
        """Represent the object as a dictionary"""
        raise NotImplementedError


class VariableBase(ABC):
    """Multi-species water quality model variable

    This is an abstract class for water quality model variables with partial
    definition of concrete attributes and methods. Parameters and methods
    documented here must be defined by a subclass except for the following:

    .. rubric:: Concrete attributes

    The :meth:`__init__` method defines the following attributes concretely.
    Thus, a subclass should call :code:`super().__init__()` at the beginning
    of its own initialization.

    .. autosummary::

        ~VariableBase.name
        ~VariableBase.note

    .. rubric:: Concrete methods

    The following methods are concretely defined, but can be overridden.

    .. autosummary::
        :nosignatures:

        __str__
        __repr__
    """

    def __init__(self, name: str, *, note: NoteType = None) -> None:
        """Variable ABC init method.

        Make sure you call this method from your concrete subclass ``__init__`` method:
        
        .. code::
            
            super().__init__(name, note=note)

        Parameters
        ----------
        name : str
            Name/symbol for the variable. Must be a valid MSX variable name
        note : (str | dict | ENcomment), optional keyword
            Supplementary information regarding this variable, by default None
            (see-also :class:`~wntr.epanet.util.NoteType`)

        Raises
        ------
        KeyExistsError
            Name is already taken
        ValueError
            Name is a reserved word
        """
        if name in RESERVED_NAMES:
            raise ValueError("Name cannot be a reserved name")
        self.name: str = name
        """Name/ID of this variable, must be a valid EPANET/MSX ID"""
        self.note: NoteType = note
        """Optional note regarding the variable (see :class:`~wntr.epanet.util.NoteType`)
        """

    @property
    @abstractmethod
    def var_type(self) -> Enum:
        """Type of reaction variable"""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Represent the object as a dictionary"""
        return dict(name=self.name)

    def __str__(self) -> str:
        """Return the name of the variable"""
        return self.name

    def __repr__(self) -> str:
        """Return a representation of the variable from the dictionary
        representation - see :meth:`to_dict`"""
        return "{}(".format(self.__class__.__name__) + ", ".join(["{}={}".format(k, repr(getattr(self, k))) for k, v in self.to_dict().items()]) + ")"


class ReactionSystemBase(ABC):
    """Abstract class for reaction systems, which contains variables and
    reaction expressions.

    This class contains the functions necessary to perform dictionary-style
    addressing of *variables* by their name. It does not allow dictionary-style
    addressing of reactions.

    This is an abstract class with some concrete attributes and methods.
    Parameters and methods documented here must be defined by a subclass
    except for the following:

    .. rubric:: Concrete attributes

    The :meth:`__init__` method defines the following attributes concretely.
    Thus, a subclass should call :code:`super().__init__()` or :code:`super().__init__(filename)`.

    .. autosummary::

        ~ReactionSystemBase._vars
        ~ReactionSystemBase._rxns

    .. rubric:: Concrete methods

    The following special methods are concretely provided to directly access
    items in the :attr:`_vars` attribute.

    .. autosummary::
        :nosignatures:

        __contains__
        __eq__
        __ne__
        __getitem__
        __iter__
        __len__
    """

    def __init__(self) -> None:
        """Constructor for the reaction system.
        
        Make sure you call this method from your concrete subclass ``__init__`` method:
        
        .. code::
            
            super().__init__()

        """
        self._vars: DisjointMapping = DisjointMapping()
        """Variables registry, which is mapped to dictionary functions on the
        reaction system object"""
        self._rxns: Dict[str, Any] = dict()
        """Reactions dictionary"""

    @abstractmethod
    def add_variable(self, obj: VariableBase) -> None:
        """Add a variable to the system"""
        raise NotImplementedError

    @abstractmethod
    def add_reaction(self, obj: ReactionBase) -> None:
        """Add a reaction to the system"""
        raise NotImplementedError

    @abstractmethod
    def variables(self) -> Generator[Any, Any, Any]:
        """Generator looping through all variables"""
        raise NotImplementedError

    @abstractmethod
    def reactions(self) -> Generator[Any, Any, Any]:
        """Generator looping through all reactions"""
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict:
        """Represent the reaction system as a dictionary"""
        raise NotImplementedError

    def __contains__(self, __key: object) -> bool:
        return self._vars.__contains__(__key)

    def __eq__(self, __value: object) -> bool:
        return self._vars.__eq__(__value)

    def __ne__(self, __value: object) -> bool:
        return self._vars.__ne__(__value)

    def __getitem__(self, __key: str) -> VariableBase:
        return self._vars.__getitem__(__key)

    def __iter__(self) -> Iterator:
        return self._vars.__iter__()

    def __len__(self) -> int:
        return self._vars.__len__()


class VariableValuesBase(ABC):
    """Abstract class for a variable's network-specific values

    This class should contain values for different pipes, tanks,
    etc., that correspond to a specific network for the reaction
    system. It can be used for initial concentration values, or
    for initial settings on parameters, but should be information
    that is clearly tied to a specific type of variable.

    This is a pure abstract class. All parameters
    and methods documented here must be defined by a subclass.
    """

    @property
    @abstractmethod
    def var_type(self) -> Enum:
        """Type of variable this object holds data for."""
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict:
        """Represent the object as a dictionary"""
        raise NotImplementedError


class NetworkDataBase(ABC):
    """Abstract class containing network specific data

    This class should be populated with things like initial quality,
    sources, parameterized values, etc.

    This is a pure abstract class. All parameters
    and methods documented here must be defined by a subclass.
    """

    @abstractmethod
    def to_dict(self) -> dict:
        """Represent the object as a dictionary"""
        raise NotImplementedError


class QualityModelBase(ABC):
    """Abstract multi-species water quality model

    This is an abstract class for a water quality model. All parameters and
    methods documented here must be defined by a subclass except for the
    following:

    .. rubric:: Concrete attributes

    The :meth:`__init__` method defines the following attributes concretely.
    Thus, a subclass should call :code:`super().__init__()` or :code:`super().__init__(filename)`.

    .. autosummary::

        ~QualityModelBase.name
        ~QualityModelBase.title
        ~QualityModelBase.description
        ~QualityModelBase._orig_file
        ~QualityModelBase._options
        ~QualityModelBase._rxn_system
        ~QualityModelBase._net_data
        ~QualityModelBase._wn
    """

    def __init__(self, filename=None):
        """QualityModel ABC init method.

        Make sure you call this method from your concrete subclass ``__init__`` method:
        
        .. code::
            
            super().__init__(filename=filename)

        Parameters
        ----------
        filename : str, optional
            File to use to populate the initial data
        """
        self.name: str = None if filename is None else os.path.splitext(os.path.split(filename)[1])[0]
        """Name for the model, or the MSX model filename (no spaces allowed)"""
        self.title: str = None
        """Title line from the MSX file, must be a single line"""
        self.description: str = None
        """Longer description; note that multi-line descriptions may not be 
        represented well in dictionary form"""
        self._orig_file: str = filename
        """Protected original filename, if provided in the constructor"""
        self._options = None
        """Protected options data object"""
        self._rxn_system: ReactionSystemBase = None
        """Protected reaction system object"""
        self._net_data: NetworkDataBase = None
        """Protected network data object"""
        self._wn = None
        """Protected water network object"""

    @property
    @abstractmethod
    def options(self):
        """Model options structure

        Concrete classes should implement this with the appropriate typing and
        also implement a setter method.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def reaction_system(self) -> ReactionSystemBase:
        """Reaction variables defined for this model

        Concrete classes should implement this with the appropriate typing.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def network_data(self) -> NetworkDataBase:
        """Network-specific values added to this model

        Concrete classes should implement this with the appropriate typing.
        """
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict:
        """Represent the object as a dictionary"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_dict(self, data: dict) -> "QualityModelBase":
        """Create a new model from a dictionary

        Parameters
        ----------
        data : dict
            Dictionary representation of the model

        Returns
        -------
        QualityModelBase
            New concrete model
        """
        raise NotImplementedError
