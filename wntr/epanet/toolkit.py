"""
Python extensions for the EPANET Programmers Toolkit DLLs.
EPANET toolkit functions.
"""
from __future__ import print_function
import ctypes, os, sys
from ctypes import byref
from pkg_resources import resource_filename
import platform
pyepanet_package = 'wntr.epanet.toolkit'

if os.name in ['nt','dos']:
    libepanet = resource_filename(__name__,'pyepanet/data/Windows/epanet2.dll')
elif sys.platform in ['darwin']:
    libepanet = resource_filename(__name__,'pyepanet/data/Darwin/libepanet.dylib')
else:
    libepanet = resource_filename(__name__,'pyepanet/data/Linux/libepanet2.so')

import logging
logger = logging.getLogger(__name__)

# import warnings

class EpanetException(Exception):
    pass


def ENgetwarning(code, sec=-1):
    if sec >= 0:
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        header = 'At %3d:%.2d:%.2d, '%(hours,mm,sec)
    else:
        header = ''
    if code == 1:
        return header+'System hydraulically unbalanced - convergence to a hydraulic solution was not achieved in the allowed number of trials'
    elif code == 2:
        return header+'System may be hydraulically unstable - hydraulic convergence was only achieved after the status of all links was held fixed'
    elif code == 3:
        return header+'System disconnected - one or more nodes with positive demands were disconnected for all supply sources'
    elif code == 4:
        return header+'Pumps cannot deliver enough flow or head - one or more pumps were forced to either shut down (due to insufficient head) or operate beyond the maximum rated flow'
    elif code == 5:
        return header+'Vavles cannot deliver enough flow - one or more flow control valves could not deliver the required flow even when fully open'
    elif code == 6:
        return header+'System has negative pressures - negative pressures occurred at one or more junctions with positive demand'
    else:
        return header+'Unknown warning: %d'%code



class ENepanet():
    """Wrapper class to load the EPANET DLL object, then perform operations on
    the EPANET object that is created when a file is loaded.
    """

    ENlib = None
    """The variable that holds the ctypes Library object"""

    errcode = 0
    """Return code from the EPANET library functions"""

    errcodelist = []
    cur_time = 0

    Warnflag = False
    """A warning ocurred at some point during EPANET execution"""

    Errflag = False
    """A fatal error ocurred at some point during EPANET execution"""

    inpfile = 'temp.inp'
    """The name of the EPANET input file"""

    rptfile = 'temp.rpt'
    """The report file to generate"""

    binfile = 'temp.bin'
    """The optional binary output file"""

    fileLoaded = False

    def __init__(self, inpfile='', rptfile='', binfile=''):

        self.inpfile = inpfile
        self.rptfile = rptfile
        self.binfile = binfile

        libnames = ['epanet2_x86','epanet2','epanet']
        if '64' in platform.machine():
            libnames.insert(0, 'epanet2_amd64')
        for lib in libnames:
            try:
                if os.name in ['nt','dos']:
                    libepanet = resource_filename(pyepanet_package,'pyepanet/data/Windows/%s.dll' % lib)
                    self.ENlib = ctypes.windll.LoadLibrary(libepanet)
                elif sys.platform in ['darwin']:
                    libepanet = resource_filename(pyepanet_package,'pyepanet/data/Darwin/lib%s.dylib' % lib)
                    self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                else:
                    libepanet = resource_filename(pyepanet_package,'pyepanet/data/Linux/lib%s.so' % lib)
                    self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                return # OK!
            except Exception as E1:
                if lib == libnames[-1]:
                    raise E1
                pass
        return

    def isOpen(self):
        return self.fileLoaded

    def _error(self):
        """Print the error text the corresponds to the error code returned"""
        if not self.errcode: return
        #errtxt = self.ENlib.ENgeterror(self.errcode)
        logger.error("EPANET error: %d",self.errcode)
        if self.errcode >= 100:
            self.Errflag = True
            self.errcodelist.append(self.errcode)
            raise EpanetException(self.ENgeterror(self.errcode))
        else:
            self.Warnflag = True
            # warnings.warn(ENgetwarning(self.errcode))
            self.errcodelist.append(ENgetwarning(self.errcode,self.cur_time))
        return


    def ENopen(self, inpfile=None, rptfile=None, binfile=None):
        """
        Opens EPANET input file & reads in network data

        Arguments:
         * inpfile = EPANET .inp input file (default to constructor value)
         * rptfile = Output file to create (default to constructor value)
         * binfile = Binary output file to create (default to constructor value)

        """
        if self.fileLoaded: self.ENclose()
        if self.fileLoaded:
            raise RuntimeError("File is loaded and cannot be closed")
        if inpfile is None: inpfile = self.inpfile
        if rptfile is None: rptfile = self.rptfile
        if binfile is None: binfile = self.binfile
        inpfile = inpfile.encode('ascii')
        rptfile = rptfile.encode('ascii')
        binfile = binfile.encode('ascii')
        self.errcode = self.ENlib.ENopen(inpfile, rptfile, binfile)
        self._error()
        if self.errcode < 100:
            self.fileLoaded = True
        return

    def ENclose(self):
        """frees all memory & files used by EPANET"""
        self.errcode = self.ENlib.ENclose()
        self._error()
        if self.errcode < 100:
            self.fileLoaded = False
        return

    def ENsolveH(self):
        """solves for network hydraulics in all time periods"""
        self.errcode = self.ENlib.ENsolveH()
        self._error()
        return

    def ENsavehydfile(self, filename):
        """
        copies binary hydraulics file to disk

        Arguments:
         * filename= name of file

        """
        self.errcode = self.ENlib.ENsavehydfile(filename.encode('ascii'))
        self._error()
        return

    def ENusehydfile(self, filename):
        """
        opens previously saved binary hydraulics file

        Arguments:
         * filename= name of file

        """
        self.errcode = self.ENlib.ENusehydfile(filename.encode('ascii'))
        self._error()
        return

    def ENsolveQ(self):
        """solves for network water quality in all time periods"""
        self.errcode = self.ENlib.ENsolveQ()
        self._error()
        return

    def ENreport(self):
        """writes report to report file"""
        self.errcode = self.ENlib.ENreport()
        self._error()
        return

    def ENgetcount(self, iCode):
        """
        retrieves the number of components of a given type in the network

        Arguments:
         * iCode   = component code (see toolkit.optComponentCounts)

        Returns:
         * number of components in network

        """
        iCount = ctypes.c_int()
        self.errcode = self.ENlib.ENgetcount(iCode, byref(iCount))
        self._error()
        return iCount.value
