"""
The wntr.epanet.toolkit module is a Python extensions for the EPANET 
Programmers Toolkit DLLs.

.. rubric:: Contents

.. autosummary::

    runepanet
    ENepanet
    EpanetException
    ENgetwarning

"""
import ctypes
import os
import os.path
import platform
import sys
from ctypes import byref
from .util import SizeLimits
from pkg_resources import resource_filename

epanet_toolkit = "wntr.epanet.toolkit"

if os.name in ["nt", "dos"]:
    libepanet = resource_filename(__name__, "Windows/epanet2.dll")
elif sys.platform in ["darwin"]:
    libepanet = resource_filename(__name__, "Darwin/libepanet.dylib")
else:
    libepanet = resource_filename(__name__, "Linux/libepanet2.so")

import logging

logger = logging.getLogger(__name__)


# import warnings


class EpanetException(Exception):
    pass


def ENgetwarning(code, sec=-1):
    if sec >= 0:
        hours = int(sec / 3600.0)
        sec -= hours * 3600
        mm = int(sec / 60.0)
        sec -= mm * 60
        header = "At %3d:%.2d:%.2d, " % (hours, mm, sec)
    else:
        header = ""
    if code == 1:
        return (
                header
                + "System hydraulically unbalanced - convergence to a hydraulic solution was not achieved in the allowed number of trials"
        )
    elif code == 2:
        return (
                header
                + "System may be hydraulically unstable - hydraulic convergence was only achieved after the status of all links was held fixed"
        )
    elif code == 3:
        return (
                header
                + "System disconnected - one or more nodes with positive demands were disconnected for all supply sources"
        )
    elif code == 4:
        return (
                header
                + "Pumps cannot deliver enough flow or head - one or more pumps were forced to either shut down (due to insufficient head) or operate beyond the maximum rated flow"
        )
    elif code == 5:
        return (
                header
                + "Vavles cannot deliver enough flow - one or more flow control valves could not deliver the required flow even when fully open"
        )
    elif code == 6:
        return (
                header
                + "System has negative pressures - negative pressures occurred at one or more junctions with positive demand"
        )
    else:
        return header + "Unknown warning: %d" % code

def runepanet(inpfile, rptfile=None, binfile=None):
    """Run an EPANET command-line simulation
    
    Parameters
    ----------
    inpfile : str
        The input file name

    """
    file_prefix, file_ext = os.path.splitext(inpfile)
    if rptfile is None:
        rptfile = file_prefix + ".rpt"
    if binfile is None:
        binfile = file_prefix + ".bin"

    enData = ENepanet()
    enData.ENopen(inpfile, rptfile, binfile)
    enData.ENsolveH()
    enData.ENsolveQ()
    try:
        enData.ENreport()
    except:
        pass
    enData.ENclose()


class ENepanet:
    """Wrapper class to load the EPANET DLL object, then perform operations on
    the EPANET object that is created when a file is loaded.

    This simulator is thread safe **only** for EPANET `version=2.2`.

    Parameters
    ----------
    inpfile : str
        Input file to use
    rptfile : str
        Output file to report to
    binfile : str
        Results file to generate
    version : float
        EPANET version to use (either 2.0 or 2.2)
    
    """

    def __init__(self, inpfile="", rptfile="", binfile="", version=2.2):

        self.ENlib = None
        self.errcode = 0
        self.errcodelist = []
        self.cur_time = 0

        self.Warnflag = False
        self.Errflag = False
        self.fileLoaded = False

        self.inpfile = inpfile
        self.rptfile = rptfile
        self.binfile = binfile

        if float(version) == 2.0:
            libnames = ["epanet2_x86", "epanet2", "epanet"]
            if "64" in platform.machine():
                libnames.insert(0, "epanet2_amd64")
        elif float(version) == 2.2:
            libnames = ["epanet22", "epanet22_win32"]
            if "64" in platform.machine():
                libnames.insert(0, "epanet22_amd64")
        for lib in libnames:
            try:
                if os.name in ["nt", "dos"]:
                    libepanet = resource_filename(
                        epanet_toolkit, "Windows/%s.dll" % lib
                    )
                    self.ENlib = ctypes.windll.LoadLibrary(libepanet)
                elif sys.platform in ["darwin"]:
                    libepanet = resource_filename(
                        epanet_toolkit, "Darwin/lib%s.dylib" % lib
                    )
                    self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                else:
                    libepanet = resource_filename(
                        epanet_toolkit, "Linux/lib%s.so" % lib
                    )
                    self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                return
            except Exception as E1:
                if lib == libnames[-1]:
                    raise E1
                pass
            finally:
                if version >= 2.2 and '32' not in lib:
                    self._project = ctypes.c_uint64()
                elif version >= 2.2:
                    self._project = ctypes.c_uint32()
                else:
                    self._project = None
        return

    def isOpen(self):
        """Checks to see if the file is open"""
        return self.fileLoaded

    def _error(self):
        """Print the error text the corresponds to the error code returned"""
        if not self.errcode:
            return
        # errtxt = self.ENlib.ENgeterror(self.errcode)
        logger.error("EPANET error: %d", self.errcode)
        if self.errcode >= 100:
            self.Errflag = True
            self.errcodelist.append(self.errcode)
            raise EpanetException("EPANET Error {}".format(self.errcode))
        else:
            self.Warnflag = True
            # warnings.warn(ENgetwarning(self.errcode))
            self.errcodelist.append(ENgetwarning(self.errcode, self.cur_time))
        return

    def ENopen(self, inpfile=None, rptfile=None, binfile=None):
        """
        Opens an EPANET input file and reads in network data

        Parameters
        ----------
        inpfile : str
            EPANET INP file (default to constructor value)
        rptfile : str
            Output file to create (default to constructor value)
        binfile : str
            Binary output file to create (default to constructor value)
            
        """
        if self._project is not None:
            if self.fileLoaded:
                self.EN_close(self._project)
            if self.fileLoaded:
                raise RuntimeError("File is loaded and cannot be closed")
            if inpfile is None:
                inpfile = self.inpfile
            if rptfile is None:
                rptfile = self.rptfile
            if binfile is None:
                binfile = self.binfile
            inpfile = inpfile.encode("latin-1")
            rptfile = rptfile.encode("latin-1")
            binfile = binfile.encode("latin-1")
            self.ENlib.EN_createproject(ctypes.byref(self._project))
            self.errcode = self.ENlib.EN_open(self._project, inpfile, rptfile, binfile)
            self._error()
            if self.errcode < 100:
                self.fileLoaded = True
            return
        else:
            if self.fileLoaded:
                self.ENclose()
            if self.fileLoaded:
                raise RuntimeError("File is loaded and cannot be closed")
            if inpfile is None:
                inpfile = self.inpfile
            if rptfile is None:
                rptfile = self.rptfile
            if binfile is None:
                binfile = self.binfile
            inpfile = inpfile.encode("latin-1")
            rptfile = rptfile.encode("latin-1")
            binfile = binfile.encode("latin-1")
            self.errcode = self.ENlib.ENopen(inpfile, rptfile, binfile)
            self._error()
            if self.errcode < 100:
                self.fileLoaded = True
            return

    def ENclose(self):
        """Frees all memory and files used by EPANET"""
        if self._project is not None:
            self.errcode = self.ENlib.EN_close(self._project)
            self.ENlib.EN_deleteproject(self._project)
            self._project = None
            self._project = ctypes.c_uint64()
        else:
            self.errcode = self.ENlib.ENclose()
        self._error()
        if self.errcode < 100:
            self.fileLoaded = False
        return

    def ENsolveH(self):
        """Solves for network hydraulics in all time periods"""
        if self._project is not None:
            self.errcode = self.ENlib.EN_solveH(self._project)
        else:
            self.errcode = self.ENlib.ENsolveH()
        self._error()
        return

    def ENsaveH(self):
        """Solves for network hydraulics in all time periods

        Must be called before ENreport() if no water quality simulation made.
        Should not be called if ENsolveQ() will be used.

        """
        if self._project is not None:
            self.errcode = self.ENlib.EN_saveH(self._project)
        else:
            self.errcode = self.ENlib.ENsaveH()
        self._error()
        return

    def ENopenH(self):
        """Sets up data structures for hydraulic analysis"""
        if self._project is not None:
            self.errcode = self.ENlib.EN_openH(self._project)
        else:
            self.errcode = self.ENlib.ENopenH()
        self._error()
        return

    def ENinitH(self, iFlag):
        """Initializes hydraulic analysis

        Parameters
        -----------
        iFlag : 2-digit flag
            2-digit flag where 1st (left) digit indicates
            if link flows should be re-initialized (1) or
            not (0) and 2nd digit indicates if hydraulic
            results should be saved to file (1) or not (0)
            
        """
        if self._project is not None:
            self.errcode = self.ENlib.EN_initH(self._project, iFlag)
        else:
            self.errcode = self.ENlib.ENinitH(iFlag)
        self._error()
        return

    def ENrunH(self):
        """Solves hydraulics for conditions at time t
        
        This function is used in a loop with ENnextH() to run
        an extended period hydraulic simulation.
        See ENsolveH() for an example.
        
        Returns
        --------
        int
            Current simulation time (seconds)
        
        """
        lT = ctypes.c_long()
        if self._project is not None:
            self.errcode = self.ENlib.EN_runH(self._project, byref(lT))
        else:
            self.errcode = self.ENlib.ENrunH(byref(lT))
        self._error()
        self.cur_time = lT.value
        return lT.value

    def ENnextH(self):
        """Determines time until next hydraulic event
        
        This function is used in a loop with ENrunH() to run
        an extended period hydraulic simulation.
        See ENsolveH() for an example.
        
        Returns
        ---------
        int
            Time (seconds) until next hydraulic event (0 marks end of simulation period)
         
        """
        lTstep = ctypes.c_long()
        if self._project is not None:
            self.errcode = self.ENlib.EN_nextH(self._project, byref(lTstep))
        else:
            self.errcode = self.ENlib.ENnextH(byref(lTstep))
        self._error()
        return lTstep.value

    def ENcloseH(self):
        """Frees data allocated by hydraulics solver"""
        if self._project is not None:
            self.errcode = self.ENlib.EN_closeH(self._project)
        else:
            self.errcode = self.ENlib.ENcloseH()
        self._error()
        return

    def ENsavehydfile(self, filename):
        """Copies binary hydraulics file to disk

        Parameters
        -------------
        filename : str
            Name of hydraulics file to output
            
        """
        if self._project is not None:
            self.errcode = self.ENlib.EN_savehydfile(self._project, filename.encode("latin-1"))
        else:
            self.errcode = self.ENlib.ENsavehydfile(filename.encode("latin-1"))
        self._error()
        return

    def ENusehydfile(self, filename):
        """Opens previously saved binary hydraulics file

        Parameters
        -------------
        filename : str
            Name of hydraulics file to use
            
        """
        if self._project is not None:
            self.errcode = self.ENlib.EN_usehydfile(self._project, filename.encode("latin-1"))
        else:
            self.errcode = self.ENlib.ENusehydfile(filename.encode("latin-1"))
        self._error()
        return

    def ENsolveQ(self):
        """Solves for network water quality in all time periods"""
        if self._project is not None:
            self.errcode = self.ENlib.EN_solveQ(self._project)
        else:
            self.errcode = self.ENlib.ENsolveQ()
        self._error()
        return

    def ENopenQ(self):
        """Sets up data structures for water quality analysis"""
        if self._project is not None:
            self.errcode = self.ENlib.EN_openQ(self._project)
        else:
            self.errcode = self.ENlib.ENopenQ()
        self._error()
        return

    def ENinitQ(self, iSaveflag):
        """Initializes water quality analysis

        Parameters
        -------------
        iSaveflag : int
             EN_SAVE (1) if results saved to file, EN_NOSAVE (0) if not
             
        """
        if self._project is not None:
            self.errcode = self.ENlib.EN_initQ(self._project, iSaveflag)
        else:
            self.errcode = self.ENlib.ENinitQ(iSaveflag)
        self._error()
        return

    def ENrunQ(self):
        """Retrieves hydraulic and water quality results at time t
        
        This function is used in a loop with ENnextQ() to run
        an extended period water quality simulation. See ENsolveQ() for
        an example.
        
        Returns
        -------
        int
            Current simulation time (seconds)
         
        """
        lT = ctypes.c_long()
        if self._project is not None:
            self.errcode = self.ENlib.EN_runQ(self._project, byref(lT))
        else:
            self.errcode = self.ENlib.ENrunQ(byref(lT))
        self._error()
        return lT.value

    def ENnextQ(self):
        """Advances water quality simulation to next hydraulic event

        This function is used in a loop with ENrunQ() to run
        an extended period water quality simulation. See ENsolveQ() for
        an example.
        
        Returns
        --------
        int
            Time (seconds) until next hydraulic event (0 marks end of simulation period)
         
        """
        lTstep = ctypes.c_long()
        if self._project is not None:
            self.errcode = self.ENlib.EN_nextQ(self._project, byref(lTstep))
        else:
            self.errcode = self.ENlib.ENnextQ(byref(lTstep))
        self._error()
        return lTstep.value

    def ENcloseQ(self):
        """Frees data allocated by water quality solver"""
        if self._project is not None:
            self.errcode = self.ENlib.EN_closeQ(self._project)
        else:
            self.errcode = self.ENlib.ENcloseQ()
        self._error()
        return

    def ENreport(self):
        """Writes report to report file"""
        if self._project is not None:
            self.errcode = self.ENlib.EN_report(self._project)
        else:
            self.errcode = self.ENlib.ENreport()
        self._error()
        return

    def ENgetcount(self, iCode):
        """Retrieves the number of components of a given type in the network

        Parameters
        -------------
        iCode : int
            Component code (see toolkit.optComponentCounts)

        Returns
        ---------
        int
            Number of components in network
        
        """
        iCount = ctypes.c_int()
        if self._project is not None:
            self.errcode = self.ENlib.EN_getcount(self._project, iCode, byref(iCount))
        else:
            self.errcode = self.ENlib.ENgetcount(iCode, byref(iCount))
        self._error()
        return iCount.value

    def ENgetflowunits(self):
        """Retrieves flow units code

        Returns
        -----------
        Code of flow units in use (see toolkit.optFlowUnits)
        
        """
        iCode = ctypes.c_int()
        if self._project is not None:
            self.errcode = self.ENlib.EN_getflowunits(self._project, byref(iCode))
        else:
            self.errcode = self.ENlib.ENgetflowunits(byref(iCode))
        self._error()
        return iCode.value

    def ENgetnodeid(self, iIndex):
        """
        desc: Gets the ID name of a node given its index.

        :param a node's index (starting from 1).
        :return the node's ID name.
        """
        fValue = ctypes.create_string_buffer(SizeLimits.EN_MAX_ID.value)
        if self._project is not None:
            self.errcode = self.ENlib.EN_getnodeid(self._project, iIndex, byref(fValue))
        else:
            self.errcode = self.ENlib.ENgetnodeid(iIndex, byref(fValue))
        self._error()
        return str(fValue.value, 'UTF-8')

    def ENgetnodeindex(self, sId):
        """Retrieves index of a node with specific ID

        Parameters
        -------------
        sId : int
            Node ID

        Returns
        ---------
        Index of node in list of nodes
        
        """
        iIndex = ctypes.c_int()
        if self._project is not None:
            self.errcode = self.ENlib.EN_getnodeindex(self._project, sId.encode("latin-1"), byref(iIndex))
        else:
            self.errcode = self.ENlib.ENgetnodeindex(sId.encode("latin-1"), byref(iIndex))
        self._error()
        return iIndex.value

    def ENgetnodetype(self, iIndex):
        """
        desc: Retrieves a node's type given its index.

        :param iIndex: idx
        :param nodeType: the node's type (see EN_NodeType).
        :return int node type
        """
        fValue = ctypes.c_int()
        if self._project is not None:
            self.errcode = self.ENlib.EN_getnodetype(self._project, iIndex, byref(fValue))
        else:
            self.errcode = self.ENlib.ENgetnodetype(iIndex, byref(fValue))
        self._error()
        return fValue.value

    def ENgetnodevalue(self, iIndex, iCode):
        """
        Retrieves parameter value for a node

        Parameters
        -------------
        iIndex: int
            Node index
        iCode : int
            Node parameter code (see toolkit.optNodeParams)

        Returns
        ---------
        Value of node's parameter

        """
        fValue = ctypes.c_float()
        if self._project is not None:
            fValue = ctypes.c_double()
            self.errcode = self.ENlib.EN_getnodevalue(self._project, iIndex, iCode, byref(fValue))
        else:
            self.errcode = self.ENlib.ENgetnodevalue(iIndex, iCode, byref(fValue))
        self._error()
        return fValue.value

    def ENgetlinkindex(self, sId):
        """Retrieves index of a link with specific ID

        Parameters
        -------------
        sId : int
            Link ID

        Returns
        ---------
        Index of link in list of links

        """
        iIndex = ctypes.c_int()
        if self._project is not None:
            self.errcode = self.ENlib.EN_getlinkindex(self._project, sId.encode("latin-1"), byref(iIndex))
        else:
            self.errcode = self.ENlib.ENgetlinkindex(sId.encode("latin-1"), byref(iIndex))
        self._error()
        return iIndex.value

    def ENgetlinktype(self, iIndex):
        """
        Retrieves a link's type.

        :param iIndex: index
        :return:linkType
        """
        fValue = ctypes.c_int()
        if self._project is not None:
            self.errcode = self.ENlib.EN_getlinktype(self._project, iIndex, byref(fValue))
        else:
            self.errcode = self.ENlib.EN_getlinktype(iIndex, byref(fValue))
        self._error()
        return fValue.value

    def ENgetlinkvalue(self, iIndex, iCode):
        """Retrieves parameter value for a link

        Parameters
        -------------
        iIndex : int
            Link index
        iCode : int
            Link parameter code (see toolkit.optLinkParams)

        Returns
        ---------
        Value of link's parameter

        """
        fValue = ctypes.c_float()
        if self._project is not None:
            fValue = ctypes.c_double()
            self.errcode = self.ENlib.EN_getlinkvalue(self._project, iIndex, iCode, byref(fValue))
        else:
            self.errcode = self.ENlib.ENgetlinkvalue(iIndex, iCode, byref(fValue))
        self._error()
        return fValue.value

    def ENsetlinkvalue(self, iIndex, iCode, fValue):
        """
        Set the value on a link

        Parameters
        ----------
        iIndex : int
            the link index
        iCode : int
            the parameter enum integer
        fValue : float
            the value to set on the link
        """
        if self._project is not None:
            self.errcode = self.ENlib.EN_setlinkvalue(self._project,
                                                      ctypes.c_int(iIndex), ctypes.c_int(iCode), ctypes.c_double(fValue)
                                                      )
        else:
            self.errcode = self.ENlib.ENsetlinkvalue(
                ctypes.c_int(iIndex), ctypes.c_int(iCode), ctypes.c_float(fValue)
            )
        self._error()

    def ENsetnodevalue(self, iIndex, iCode, fValue):
        """
        Set the value on a node

        Parameters
        ----------
        iIndex : int
            the node index
        iCode : int
            the parameter enum integer
        fValue : float
            the value to set on the node
        """
        if self._project is not None:
            self.errcode = self.ENlib.EN_setnodevalue(self._project,
                                                      ctypes.c_int(iIndex), ctypes.c_int(iCode), ctypes.c_double(fValue)
                                                      )
        else:
            self.errcode = self.ENlib.ENsetnodevalue(
                ctypes.c_int(iIndex), ctypes.c_int(iCode), ctypes.c_float(fValue)
            )
        self._error()

    def ENsettimeparam(self, eParam, lValue):
        """
        Set a time parameter value

        Parameters
        ----------
        eParam : int
            the time parameter to set
        lValue : long
            the value to set, in seconds
        """
        if self._project is not None:
            self.errcode = self.ENlib.EN_settimeparam(
                self._project, ctypes.c_int(eParam), ctypes.c_long(lValue)
            )
        else:
            self.errcode = self.ENlib.ENsettimeparam(
                ctypes.c_int(eParam), ctypes.c_long(lValue)
            )
        self._error()

    def ENgettimeparam(self, eParam):
        """
        Get a time parameter value

        Parameters
        ----------
        eParam : int
            the time parameter to get

        Returns
        -------
        long
            the value of the time parameter, in seconds
        """
        lValue = ctypes.c_long()
        if self._project is not None:
            self.errcode = self.ENlib.EN_gettimeparam(
                self._project, ctypes.c_int(eParam), byref(lValue)
            )
        else:
            self.errcode = self.ENlib.ENgettimeparam(
                ctypes.c_int(eParam), byref(lValue)
            )
        self._error()
        return lValue.value

    def ENsaveinpfile(self, inpfile):
        """Saves EPANET input file

        Parameters
        -------------
        inpfile : str
		    EPANET INP output file

        """

        inpfile = inpfile.encode("latin-1")
        if self._project is not None:
            self.errcode = self.ENlib.EN_saveinpfile(self._project, inpfile)
        else:
            self.errcode = self.ENlib.ENsaveinpfile(inpfile)
        self._error()

        return
