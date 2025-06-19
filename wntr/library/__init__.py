"""
The wntr.library package contains classes to help define water network models
"""
from .model_library import ModelLibrary
from .demand_library import DemandPatternLibrary
from . import msx

model_library = ModelLibrary()
demand_library = DemandPatternLibrary()
reaction_library = msx.MsxLibrary()
