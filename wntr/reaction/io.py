# coding: utf-8

import sys
import logging

sys_default_enc = sys.getdefaultencoding()


logger = logging.getLogger(__name__)


class MsxFile(object):
    
    def __init__(self):
        pass

    def read(self, msx_file, rxn_model=None):
        pass

    def write(self, filename, rxn_model):
        pass



class MsxBinFile(object):
    def __init__(self):
        pass

    def read(self, filename):
        pass

