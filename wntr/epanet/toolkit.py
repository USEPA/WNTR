"""
Python extensions for the EPANET Programmers Toolkit DLLs.
EPANET toolkit functions.
"""
from __future__ import print_function
import ctypes, os, sys
from ctypes import byref
from pkg_resources import resource_filename
import platform
epanet_toolkit = 'wntr.epanet.toolkit'

if os.name in ['nt','dos']:
    libepanet = resource_filename(__name__,'Windows/epanet2.dll')
elif sys.platform in ['darwin']:
    libepanet = resource_filename(__name__,'Darwin/libepanet.dylib')
else:
    libepanet = resource_filename(__name__,'Linux/libepanet2.so')

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
                    libepanet = resource_filename(epanet_toolkit,'Windows/%s.dll' % lib)
                    self.ENlib = ctypes.windll.LoadLibrary(libepanet)
                elif sys.platform in ['darwin']:
                    libepanet = resource_filename(epanet_toolkit,'Darwin/lib%s.dylib' % lib)
                    self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                else:
                    libepanet = resource_filename(epanet_toolkit,'Linux/lib%s.so' % lib)
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
            raise EpanetException('EPANET Error {}'.format(self.errcode))
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

    def ENsaveH(self):
        """
        solves for network hydraulics in all time periods

        Must be called before ENreport() if no WQ simulation made.
        Should not be called if ENsolveQ() will be used.

        """
        self.errcode = self.ENlib.ENsaveH()
        self._error()
        return

    def ENopenH(self):
        """sets up data structures for hydraulic analysis"""
        self.errcode = self.ENlib.ENopenH()
        self._error()
        return

    def ENinitH(self, iFlag):
        """
        initializes hydraulic analysis

        Arguments:
         * iFlag   = 2-digit flag where 1st (left) digit indicates
                     if link flows should be re-initialized (1) or
                     not (0) and 2nd digit indicates if hydraulic
                     results should be saved to file (1) or not (0)
        """
        self.errcode = self.ENlib.ENinitH(iFlag)
        self._error()
        return

    def ENrunH(self):
        """
        solves hydraulics for conditions at time t.

        Returns: long
         * current simulation time (seconds)

        This function is used in a loop with ENnextH() to run
        an extended period hydraulic simulation.
        See ENsolveH() for an example.

        """
        lT = ctypes.c_long()
        self.errcode = self.ENlib.ENrunH(byref(lT))
        self._error()
        self.cur_time = lT.value
        return lT.value

    def ENnextH(self):
        """
        determines time until next hydraulic event.

        Returns:
         * time (seconds) until next hydraulic event
           (0 marks end of simulation period)

        This function is used in a loop with ENrunH() to run
        an extended period hydraulic simulation.
        See ENsolveH() for an example.

        """
        lTstep = ctypes.c_long()
        self.errcode = self.ENlib.ENnextH(byref(lTstep))
        self._error()
        return lTstep.value

    def ENcloseH(self):
        """frees data allocated by hydraulics solver"""
        self.errcode = self.ENlib.ENcloseH()
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

    def ENopenQ(self):
        """sets up data structures for WQ analysis"""
        self.errcode = self.ENlib.ENopenQ()
        self._error()
        return

    def ENinitQ(self, iSaveflag):
        """
        initializes WQ analysis

        Arguments:
         * saveflag= EN_SAVE (1) if results saved to file,
                     EN_NOSAVE (0) if not

        """
        self.errcode = self.ENlib.ENinitQ(iSaveflag)
        self._error()
        return

    def ENrunQ(self):
        """
        retrieves hydraulic & WQ results at time t.

        Returns: long
         * current simulation time (seconds)

        This function is used in a loop with ENnextQ() to run
        an extended period WQ simulation. See ENsolveQ() for
        an example.

        """
        lT = ctypes.c_long()
        self.errcode = self.ENlib.ENrunQ(byref(lT))
        self._error()
        return lT.value

    def ENnextQ(self):
        """
        advances WQ simulation to next hydraulic event.

        Returns: long
         * time (seconds) until next hydraulic event
           (0 marks end of simulation period)

        This function is used in a loop with ENrunQ() to run
        an extended period WQ simulation. See ENsolveQ() for
        an example.

        """
        lTstep = ctypes.c_long()
        self.errcode = self.ENlib.ENnextQ(byref(lTstep))
        self._error()
        return lTstep.value

    def ENcloseQ(self):
        """frees data allocated by WQ solver"""
        self.errcode = self.ENlib.ENcloseQ()
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


    def ENgetflowunits(self):
        """
        retrieves flow units code

        Returns: int
         * code of flow units in use (see toolkit.optFlowUnits)

        """
        iCode = ctypes.c_int()
        self.errcode = self.ENlib.ENgetflowunits(byref(iCode))
        self._error()
        return iCode.value



    def ENgetnodeindex(self, sId):
        """
        retrieves index of a node with specific ID

        Arguments:
         * sId     = node ID

        Returns: int
         * index of node in list of nodes

        """
        iIndex = ctypes.c_int()
        self.errcode = self.ENlib.ENgetnodeindex(sId.encode('ascii'), byref(iIndex))
        self._error()
        return iIndex.value


    def ENgetnodevalue(self, iIndex, iCode):
        """
        retrieves parameter value for a node

        Arguments:
         * iIndex  = node index
         * iCode   = node parameter code (see toolkit.optNodeParams)

        Returns: float
         * value of node's parameter

        """
        fValue = ctypes.c_float()
        self.errcode = self.ENlib.ENgetnodevalue(iIndex, iCode, byref(fValue))
        self._error()
        return fValue.value


    def ENgetlinkindex(self, sId):
        """
        retrieves index of a link with specific ID

        Arguments:
         * sId     = link ID

        Returns: int
         * index of link in list of links

        """
        iIndex = ctypes.c_int()
        self.errcode = self.ENlib.ENgetlinkindex(sId.encode('ascii'), byref(iIndex))
        self._error()
        return iIndex.value



    def ENgetlinkvalue(self, iIndex, iCode):
        """
        retrieves parameter value for a link

        Arguments:
         * iIndex  = link index
         * iCode   = link parameter code (see toolkit.optLinkParams)

        Returns:
         * value of link's parameter

        """
        fValue = ctypes.c_float()
        self.errcode = self.ENlib.ENgetlinkvalue(iIndex, iCode, byref(fValue))
        self._error()
        return fValue.value


    def ENsaveinpfile(self, inpfile):
        """
        Saves EPANET input file

        Arguments:
         * inpfile = EPANET .inp output file

        """

        inpfile = inpfile.encode('ascii')
        self.errcode = self.ENlib.ENsaveinpfile(inpfile)
        self._error()

        return


    