# shapely and geopandas are optional dependencies of WNTR. If shapely 
# version is >= 2.0, the environment variable USE_PYGEOS is set to '0' to 
# ensure geopandas uses shapely over pygeos. Future versions of 
# geopandas will use shapely by default.
try:
    import shapely
    if int(shapely.__version__.split('.')[0]) >= 2:
        import os
        os.environ['USE_PYGEOS'] = '0'
except ModuleNotFoundError:
    pass

from wntr import epanet
from wntr import network
from wntr import morph
from wntr import metrics
from wntr import sim
from wntr import scenario
from wntr import graphics
from wntr import gis
from wntr import utils

__version__ = '0.6.0dev'

__copyright__ = """Copyright 2019 National Technology & Engineering 
Solutions of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 
with NTESS, the U.S. Government retains certain rights in this software."""

__license__ = "Revised BSD License"

from wntr.utils.logger import start_logging


    
