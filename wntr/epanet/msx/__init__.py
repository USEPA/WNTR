# coding: utf-8
"""
The wntr.epanet.msx package provides EPANET-MSX compatibility functions for 
WNTR.

The following environment variable must be set, or the command `set_msx_path` 
must be run prior to trying to instantiate the EPANET-MSX toolkit.

.. envvar:: WNTR_PATH_TO_EPANETMSX

    The full path to the directory where EPANET-MSX has been installed. 
    Specifically, the directory should contain both toolkit files, epanet2.dll 
    and epanetmsx.dll (or the appropriate equivalent files for your system 
    architecture).
"""

import os as _os

def set_msx_path(path):
    if not _os.path.isdir(path):
        raise FileNotFoundError('Directory not found, {}'.format(path))
    _os.environ['WNTR_PATH_TO_EPANETMSX'] = path

from .io import MsxFile, MsxBinFile
from .toolkit import MSXepanet

