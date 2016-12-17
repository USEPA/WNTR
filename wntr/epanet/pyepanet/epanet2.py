"""
Python extensions for the EPANET Programmers Toolkit DLLs.
EPANET toolkit functions.
"""
from toolkit import *
import ctypes, os, sys
from ctypes import byref
from pkg_resources import resource_filename
import platform
pyepanet_package = 'wntr.pyepanet'

import logging
logger = logging.getLogger(__name__)

import warnings

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
    
    inpfile = ''
    rptfile = ''
    binfile = ''
    
    fileLoaded = False
    
    def __init__(self, inpfile='', rptfile='', binfile=''):
        """Initialize the ENepanet class

        Keyword arguments:
         * inpfile = the name of the EPANET input file (default '')
         * rptfile = the report file to generate (default '')
         * binfile = the optional binary output file (default '')

        """
        self.inpfile = inpfile
        self.rptfile = rptfile
        self.binfile = binfile

        libnames = ['epanet2_x86','epanet2','epanet']
        if '64' in platform.machine():
            libnames.insert(0, 'epanet2_amd64')
        for lib in libnames:
            try:
                if os.name in ['nt','dos']:
                    libepanet = resource_filename(pyepanet_package,'data/Windows/%s.dll' % lib)
                    self.ENlib = ctypes.windll.LoadLibrary(libepanet)
                elif sys.platform in ['darwin']:
                    libepanet = resource_filename(pyepanet_package,'data/Darwin/lib%s.dylib' % lib)
                    self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                else:
                    libepanet = resource_filename(pyepanet_package,'data/Linux/lib%s.so' % lib)
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
            raise(EpanetException(self.ENgeterror(self.errcode)))
        else:
            self.Warnflag = True
            warnings.warn(ENgetwarning(self.errcode))
            self.errcodelist.append(ENgetwarning(self.errcode,self.cur_time))
        return

    def epanetExec(self, inpfile=None, rptfile=None, binfile=None):
        """
        Open an input file, run EPANET, then close the file.
        
        Arguments:
         * inpfile = EPANET input file
         * rptfile = output file to create
         * binfile = optional binary file to create
        
        """
        if inpfile is None: inpfile = self.inpfile
        if rptfile is None: rptfile = self.rptfile
        if binfile is None: binfile = self.binfile
        logger.info("EPANET Version 2.0")
        try:
            self.ENopen(inpfile, rptfile, binfile)
            self.ENsolveH()
            self.ENsolveQ()
            self.ENreport()
        except:
            pass
        try:
            self.ENclose()
        except:
            pass
        if self.Errflag: 
            logger.error("EPANET completed. There are errors.")
        elif self.Warnflag:
            logger.warning("EPANET completed. There are warnings.")
        else:
            logger.info("EPANET completed.")
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
            raise(EPANETException('Fatal error closing previously opened file'))
        if inpfile is None: inpfile = self.inpfile
        if rptfile is None: rptfile = self.rptfile
        if binfile is None: binfile = self.binfile
        self.errcode = self.ENlib.ENopen(inpfile, rptfile, binfile)
        self._error()
        if self.errcode < 100:
            self.fileLoaded = True
        return
        
    def ENsaveinpfile(self, filename):
        """saves current data base to file"""
        self.errcode = self.ENlib.ENsaveinpfile(filename)
        self._error()
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
        self.errcode = self.ENlib.ENsavehydfile(filename)
        self._error()
        return
        
    def ENusehydfile(self, filename):
        """
        opens previously saved binary hydraulics file
        
        Arguments:
         * filename= name of file
        
        """
        self.errcode = self.ENlib.ENusehydfile(filename)
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
        
    def ENstepQ(self):
        """
        advances WQ simulation by a single WQ time step
        
        Returns: long
         * time left in overall simulation (seconds)
        
        This function is used in a loop with ENrunQ() to run
        an extended period WQ simulation.
        
        """
        lTLeft = ctypes.c_long()
        self.errcode = self.ENlib.ENstepQ(byref(lTLeft))
        self._error()
        return lTLeft.value
        
    def ENcloseQ(self):
        """frees data allocated by WQ solver"""
        self.errcode = self.ENlib.ENcloseQ()
        self._error()
        return
        
    def ENwriteline(self, line):
        """
        writes line of text to report file
        
        Arguments:
         * line    = text string
        
        """
        self.errcode = self.ENlib.ENwriteline(line)
        self._error()
        return
        
    def ENreport(self):
        """writes report to report file"""
        self.errcode = self.ENlib.ENreport()
        self._error()
        return
        
    def ENresetreport(self):
        """resets report options to default values"""
        self.errcode = self.ENlib.ENresetreport()
        self._error()
        return
        
    def ENsetreport(self, sFmt):
        """
        processes a reporting format command
        
        Arguments:
         * sFmt    = report format command
        
        """
        self.errcode = self.ENlib.ENsetreport(sFmt)
        self._error()
        return
        
    def ENgetcontrol(self, iCindex):
        """
        retrieves parameters that define a simple control
        
        Arguments:
         * iCindex = control index (position of control statement
                     in the input file, starting from 1)
        
        Returns: tuple( int, int, float, int, float )
         * control type code (see toolkit.optControlTypes)
         * index of controlled link
         * control setting on link
         * index of controlling node (0 for TIMER
           or TIMEOFDAY control)
         * control level (tank level, junction
           pressure, or time (seconds)
        
        """
        iCtype = ctypes.c_int()
        iLindex = ctypes.c_int()
        fSetting = ctypes.c_float()
        iNindex = ctypes.c_int()
        fLevel = ctypes.c_float()
        self.errcode = self.ENlib.ENgetcontrol(iCindex, byref(iCtype),
                                               byref(iLindex), byref(fSetting),
                                               byref(iNindex), byref(fLevel))
        self._error()
        return (iCtype.value, iLindex.value, fSetting.value, iNindex.value, 
                        fLevel.value)
    
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
        
    def ENgetoption(self, iCode):
        """
        gets value for an analysis option
        
        Arguments:
         * iCode   = option code (toolkit.optMiscOptions)
        
        Returns:
         * option value
        
        """
        fValue = ctypes.c_float()
        self.errcode = self.ENlib.ENgetoption(iCode, byref(fValue))
        self._error()
        return fValue.value
        
    def ENgettimeparam(self, iCode):
        """
        retrieves value of specific time parameter
        
        Arguments:
         * iCode   = time parameter code (see toolkit.optTimeParams)
        
        """
        lValue = ctypes.c_long()
        self.errcode = self.ENlib.ENgettimeparam(iCode, byref(lValue))
        self._error()
        return lValue.value
        
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
        
    def ENgetpatternindex(self, sId):
        """
        retrieves index of time pattern with specific ID
        
        Arguments:
         * sId     = time pattern ID
        
        Returns: int
         * index of time pattern in list of patterns
        
        """
        iIndex = ctypes.c_int()
        self.errcode = self.ENlib.ENgetpatternindex(sId, byref(iIndex))
        self._error()
        return iIndex.value
        
    def ENgetpatternid(self, iIndex):
        """
        retrieves ID of a time pattern with specific index
        
        Arguments:
         * iIndex  = index of time pattern
        
        Returns: string
         * pattern ID
        
        """
        sId = ctypes.create_string_buffer(256)
        self.errcode = self.ENlib.ENgetpatternid(iIndex, byref(sId))
        self._error()
        return sId.value
        
    def ENgetpatternlen(self, iIndex):
        """
        retrieves number of multipliers in a time pattern
        
        Arguments:
         * iIndex  = index of time pattern
        
        Returns: int
         * pattern length (number of multipliers)
        
        """
        iLen = ctypes.c_int()
        self.errcode = self.ENlib.ENgetpatternlen(iIndex, byref(iLen))
        self._error()
        return iLen.value
        
    def ENgetpatternvalue(self, iIndex, iPeriod):
        """
        retrieves multiplier for a specific time period and pattern
        
        Arguments:
         * iIndex  = index of time pattern
         * iPeriod = pattern time period
        
        Returns: float
         * pattern multiplier
        
        """
        fValue = ctypes.c_float()
        self.errcode = self.ENlib.ENgetpatternvalue(iIndex, iPeriod, 
                                                    byref(fValue))
        self._error()
        return fValue.value
        
    def ENgetqualtype(self):
        """
        retrieves type of quality analysis called for
        
        Returns: tuple( int, int )
         * WQ analysis code number (see toolkit.optQualTypes)
         * index of node being traced (if iQualcode = WQ tracing (EN_TRACE))
        
        """
        iQualcode = ctypes.c_int()
        iTracenode = ctypes.c_int()
        self.errcode = self.ENlib.ENgetqualtype(byref(iQualcode), 
                                                byref(iTracenode))
        self._error()
        return (iQualcode.value, iTracenode.value)
        
    def ENgeterror(self, iErrcode):
        """
        retrieves text of error/warning message
        
        Arguments:
         * errcode = error/warning code number
        
        Returns: string
         * text of error/warning message
        
        """
        sErrmsg = ctypes.create_string_buffer(256)
        self.errcode = self.ENlib.ENgeterror(iErrcode, byref(sErrmsg), 256)
        self._error()
        return sErrmsg.value
        
    def ENgetnodeindex(self, sId):
        """
        retrieves index of a node with specific ID
        
        Arguments:
         * sId     = node ID
        
        Returns: int
         * index of node in list of nodes
        
        """
        iIndex = ctypes.c_int()
        self.errcode = self.ENlib.ENgetnodeindex(sId, byref(iIndex))
        self._error()
        return iIndex.value
        
    def ENgetnodeid(self, iIndex):
        """
        retrieves ID of a node with specific index
        
        Arguments:
         * iIndex  = index of node in list of nodes
        
        Returns: string
         * node ID
        
        """
        sId = ctypes.create_string_buffer(256)
        self.errcode = self.ENlib.ENgetnodeid(iIndex, byref(sId))
        self._error()
        return sId.value
    
    def ENgetnodetype(self, iIndex):
        """
        retrieves node type of specific node
        
        Arguments:
         * iIndex  = node index
        
        Returns: int
         * node type code number (see toolkit.optNodeTypes)
        
        """
        iCode = ctypes.c_int()
        self.errcode = self.ENlib.ENgetnodetype(iIndex, byref(iCode))
        self._error()
        return iCode.value
        
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
        
    def ENgetnumdemands(self, iIndex):
        """
        get the number of demand multiplers at a given node
        
        Arguments:
         * iIndex  = node index
        
        Returns: int
         * number of demands
        
        NOTE: TEVAepanet DLL's only
        
        """
        iNumDemands = ctypes.c_int()
        self.errcode = self.ENlib.ENgetnumdemands(iIndex, 
                                                  byref(iNumDemands))
        self._error()
        return iNumDemands.value
        
    def ENgetbasedemand(self, iIndex, iDemIdx):
        """
        get the based demand at a node and demand index
        
        Arguments:
         * iIndex  = node index
         * iDemIdx = demand index
        
        Returns: float
         * value of the base demand
        
        NOTE: TEVAepanet DLL's only
                
        """
        fBaseDemand = ctypes.c_float()
        self.errcode = self.ENlib.ENgetbasedemand(iIndex, iDemIdx,
                                                  byref(fBaseDemand))
        self._error()
        return fBaseDemand.value
        
    def ENgetdemandpattern(self, iNodeIndex, iDemandIdx):
        """
        get the demand pattern associated with a node and demand index
        
        Arguments:
         * iIndex  = 
         * iDemIdx = 
        
        Returns:
         * index of the demand pattern
        
        NOTE: TEVAepanet DLL's only
        
        """
        iPattIdx = ctypes.c_int()
        self.errcode = self.ENlib.ENgetdemandpattern(iNodeIndex, iDemandIdx, 
                                                     byref(iPattIdx))
        self._error()
        return iPattIdx.value
        
    def ENgetlinkindex(self, sId):
        """
        retrieves index of a link with specific ID
        
        Arguments:
         * sId     = link ID
        
        Returns: int
         * index of link in list of links
        
        """
        iIndex = ctypes.c_int()
        self.errcode = self.ENlib.ENgetlinkindex(sId, byref(iIndex))
        self._error()
        return iIndex.value
        
    def ENgetlinkid(self, iIndex):
        """
        retrieves ID of a link with specific index
        
        Arguments:
         * iIndex  = index of link in list of links
        
        Returns: string
         * retrieves ID of a link with specific index
        
        """
        sId = ctypes.create_string_buffer(256)
        self.errcode = self.ENlib.ENgetlinkid(iIndex, byref(sId))
        self._error()
        return sId.value
        
    def ENgetlinktype(self, iIndex):
        """
        retrieves link type of specific link
        
        Arguments:
         * iIndex  = link index
        
        Returns: int
         * link type code number (see toolkit.optLinkTypes)
        
        """
        iCode = ctypes.c_int()
        self.errcode = self.ENlib.ENgetlinktype(iIndex, byref(iCode))
        self._error()
        return iCode.value
        
    def ENgetlinknodes(self, iIndex):
        """
        retrieves end nodes of a specific link
        
        Arguments:
         * iIndex: =link index
        
        Returns: tuple
         * index of link's starting node
         * index of link's ending node
        
        """
        iNode1 = ctypes.c_int()
        iNode2 = ctypes.c_int()
        self.errcode = self.ENlib.ENgetlinknodes(iIndex, byref(iNode1), 
                                                 byref(iNode2))
        self._error()
        return (iNode1.value, iNode2.value)
        
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
        
    def ENgetversion(self):
        """
        retrieves a number assigned to the most recent
        update of the source code. This number, set by the
        constant CODEVERSION found in TYPES.H,  began with
        20001 and increases by 1 with each new update.
        
        Returns: int
         * version number of the DLL source code
        
        """
        v = ctypes.c_int()
        self.errcode = self.ENlib.ENgetversion(byref(v))
        self._error()
        return v.value
        
    def ENsetcontrol(self, iCindex, iCtype, iLindex, fSetting, iNindex, fLevel):
        """
        specifies parameters that define a simple control
        
        Arguments:
         * cindex  = control index (position of control statement
                     in the input file, starting from 1)
         * ctype   = control type code (see TOOLKIT.H)
         * lindex  = index of controlled link
         * setting = control setting applied to link
         * nindex  = index of controlling node (0 for TIMER
                     or TIMEOFDAY control)
         * level   = control level (tank level, junction pressure,
                     or time (seconds))
        
        """
        self.errcode = self.ENlib.ENsetcontrol(iCindex, iCtype, iLindex, 
                                               ctypes.c_float(fSetting), iNindex, ctypes.c_float(fLevel))
        self._error()
        return
        
    def ENsetnodevalue(self, iIndex, iCode, fValue):
        """
        sets input parameter value for a node
        
        Arguments:
         * iIndex  = node index
         * iCode   = node parameter code (see toolkit.optNodeParams)
         * fValue  = parameter value
        
        """
        self.errcode = self.ENlib.ENsetnodevalue(iIndex, iCode, ctypes.c_float(fValue))
        self._error()
        return
        
    def ENsetlinkvalue(self, iIndex, iCode, fValue):
        """
        sets input parameter value for a link
        
        Arguments:
         * iIndex  = link index
         * iCode   = link parameter code (see toolkit.optLinkParams)
         * fValue  = parameter value
        
        """
        self.errcode = self.ENlib.ENsetlinkvalue(iIndex, iCode, ctypes.c_float(fValue))
        self._error()
        return
        
    def ENaddpattern(self, sId):
        """
        adds a new time pattern appended to the end of the existing patterns
        
        Arguments:
         * sId     = ID name of the new pattern
        
        """
        self.errcode = self.ENlib.ENaddpattern(sId)
        self._error()
        return
        
    def ENsetpattern(self, iIndex, afMult):
        """
        sets multipliers for a specific time pattern
        
        Arguments:
         * iIndex  = time pattern index
         * afMult  = array of pattern multipliers
        
        """
        afMult = (ctypes.c_float * len(afMult))(*afMult)
        self.errcode = self.ENlib.ENsetpattern(iIndex, afMult, len(afMult))
        self._error()
        return
        
    def ENsetpatternvalue(self, iIndex, iPeriod, fValue):
        """
        sets multiplier for a specific time period and pattern
        
        Arguments:
         * iIndex  = time pattern index
         * iPeriod = time pattern period
         * fValue  = pattern multiplier
        
        """
        self.errcode = self.ENlib.ENsetpatternvalue(iIndex, iPeriod, ctypes.c_float(fValue))
        self._error()
        return
        
    def ENsettimeparam(self, iCode, lValue):
        """
        sets value for time parameter
        
        Arguments:
         * iCode   = time parameter code (see toolkit.optTimeParams)
         * lValue  = time parameter value
        
        """
        self.errcode = self.ENlib.ENsettimeparam(iCode, lValue)
        self._error()
        return
        
    def ENsetoption(self, iCode, fValue):
        """
        sets value for an analysis option
        
        Arguments:
         * iCode   = option code (see toolkit.optMiscOptions)
         * fValue  = option value
        
        """
        self.errcode = self.ENlib.ENsetoption(iCode, ctypes.c_float(fValue))
        self._error()
        return
        
    def ENsetstatusreport(self, iCode):
        """
        sets level of hydraulic status reporting
        
        Arguments:
         * iCode   = status reporting code (0, 1, or 2)
        
        """
        self.errcode = self.ENlib.ENsetstatusreport(iCode)
        self._error()
        return
        
    def ENsetqualtype(self, iQualcode, sChemname, sChemunits, sTracenode):
        """
        sets type of quality analysis called for
        
        Arguments:
         * iQualcode  = WQ parameter code (see toolkit.optQualTypes)
         * sChemname  = name of WQ constituent
         * sChemunits = concentration units of WQ constituent
         * sTracenode = ID of node being traced
        
        NOTE: chemname and chemunits only apply when WQ analysis
              is for chemical. tracenode only applies when WQ
              analysis is source tracing.
        
        """
        self.errcode = self.ENlib.ENsetqualtype(iQualcode, sChemname, 
                                                sChemunits, sTracenode)
        self._error()
        return
    

def main(argv=sys.argv):
    argc = len(argv)
    errcode = 0
    if argc < 3:
        # output format 3
        pass
    f1 = argv[1]
    f2 = argv[2]
    if argc > 3: f3 = argv[3]
    else: f3 = ''
    try:
        A = ENepanet(inpfile=f1, rptfile=f2, binfile=f3)
        A.epanetExec()
        return A.errcode
    except Exception as E:
        print "EPANET Failed to launch"
        print E
        return 1
