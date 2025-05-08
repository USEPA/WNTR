"""
The wntr.library package contains classes to help define water network models
"""
from .demand_library import DemandPatternLibrary
from . import msx
from .model_library import ModelLibrary

model_library = ModelLibrary()