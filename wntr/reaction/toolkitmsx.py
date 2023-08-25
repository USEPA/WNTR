"""
The wntr.reaction.toolkit module is a Python extension for the EPANET MSX
Programmers Toolkit DLLs.

.. note::
    
    Code in this section taken from code originally written by Junli Hao 07/29/2018, 
    "EPANET-MSX-Python-wrapper" on GitHub, licensed under the BSD license. See LICENSE.txt for more 
    details.


"""
import ctypes
import os
import os.path
import platform
import sys
from ctypes import byref
from ..epanet.toolkit import EpanetException, ENepanet
from ..epanet.util import SizeLimits
from pkg_resources import resource_filename

epanet_toolkit = "wntr.epanet.toolkit"

if os.name in ["nt", "dos"]:
    libepanet = resource_filename(__name__, "Windows/epanet2.dll")
    libmsx = resource_filename(__name__, "Windows/epanetmsx.dll")
elif sys.platform in ["darwin"]:
    libepanet = resource_filename(__name__, "Darwin/libepanet.dylib")
    libmsx = resource_filename(__name__, "Darwin/libepanetmsx.dylib")
else:
    libepanet = resource_filename(__name__, "Linux/libepanet2.so")
    libmsx = resource_filename(__name__, "Linux/libepanetmsx.so")

import logging

logger = logging.getLogger(__name__)


class EpanetMsxToolkitError(Exception):
    ERROR_CODES = {
        101: "insufficient memory available.",
        102: "no network data available.",
        103: "hydraulics not initialized.",
        104: "no hydraulics for water quality analysis.",
        105: "water quality not initialized.",
        106: "no results saved to report on.",
        107: "hydraulics supplied from external file.",
        108: "cannot use external file while hydraulics solver is active.",
        109: "cannot change time parameter when solver is active.",
        110: "cannot solve network hydraulic equations.",
        120: "cannot solve water quality transport equations.",
        200: "Cannot read EPANET-MSX file.",
        201: "Syntax error",
        202: "Function call contains an illegal numeric value",
        203: "Function call refers to an undefined node",
        204: "Function call refers to an undefined link",
        205: "Function call refers to an undefined time pattern",
        206: "Function call refers to an undefined curve",
        207: "Function call attempts to control a check valve pipe or a GPV valve",
        208: "Function call contains illegal PDA pressure limits",
        209: "Function call contains an illegal node property value",
        211: "Function call contains an illegal link property value",
        212: "Function call refers to an undefined Trace Node",
        213: "Function call contains an invalid option value",
        214: "Too many characters in a line of an input file",
        215: "Function call contains a duplicate ID label",
        216: "Function call refers to an undefined pump",
        217: "Invalid pump energy data",
        219: "Illegal valve connection to tank node",
        220: "Illegal valve connection to another valve",
        221: "Mis-placed clause in rule-based control",
        222: "Link assigned same start and end nodes",
        223: "Not enough nodes in network",
        224: "No tanks or reservoirs in network",
        225: "Invalid lower/upper levels for tank",
        226: "No head curve or power rating for pump",
        227: "Invalid head curve for pump",
        230: "Nonincreasing x-values for curve",
        233: "Network has unconnected node",
        240: "Function call refers to nonexistent water quality source",
        241: "Function call refers to nonexistent control",
        250: "Function call contains invalid format (e.g. too long an ID name)",
        251: "Function call contains invalid parameter code",
        253: "Function call refers to nonexistent demand category",
        254: "Function call refers to node with no coordinates",
        257: "Function call refers to nonexistent rule",
        258: "Function call refers to nonexistent rule clause",
        259: "Function call attempts to delete a node that still has links connected to it",
        260: "Function call attempts to delete node assigned as a Trace Node",
        261: "Function call attempts to delete a node or link contained in a control",
        262: "Function call attempts to modify network structure while a solver is open",
        301: "Identical file names used for different types of files",
        302: "Cannot open input file",
        303: "Cannot open report file",
        304: "Cannot open output file",
        305: "Cannot open hydraulics file",
        306: "Hydraulics file does not match network data",
        307: "Cannot read hydraulics file",
        308: "Cannot save results to binary file",
        309: "Cannot save results to report file",
        501: "insufficient memory available.",
        502: "no EPANET data file supplied.",
        503: "could not open MSX input file.",
        504: "could not open hydraulic results file.",
        505: "could not read hydraulic results file.",
        506: "could not read MSX input file.",
        507: "too few pipe reaction expressions.",
        508: "too few tank reaction expressions.",
        509: "could not open differential equation solver.",
        510: "could not open algebraic equation solver.",
        511: "could not open binary results file.",
        512: "read/write  on binary results file.",
        513: "could not integrate reaction rate expressions.",
        514: "could not solve reaction equilibrium expressions.",
        515: "reference made to an unknown type of object.",
        516: "reference made to an illegal object index.",
        517: "reference made to an undefined object ID.",
        518: "invalid property values were specified.",
        519: "an MSX project was not opened.",
        520: "an MSX project is already opened.",
        521: "could not open MSX report file.",
        522: "could not compile chemistry functions.",
        523: "could not load functions from compiled chemistry file.",
        524: "illegal math operation.",
    }

    def __init__(self, code, *args: object) -> None:
        msg = self.ERROR_CODES.get(code, "EPANET MSX error: {}".format(code))
        super().__init__(msg, *args)


class MSXepanet(ENepanet):
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
            libnames = ["epanetmsx"]
            if "64" in platform.machine():
                libnames.insert(0, "epanetmsx_amd64")
        elif float(version) == 2.2:
            libnames = ["epanetmsx", "epanetmsx_win32"]
            if "64" in platform.machine():
                libnames.insert(0, "epanetmsx_amd64")
        for lib in libnames:
            try:
                if os.name in ["nt", "dos"]:
                    libepanet = resource_filename(epanet_toolkit, "Windows/%s.dll" % lib)
                    self.ENlib = ctypes.windll.LoadLibrary(libepanet)
                elif sys.platform in ["darwin"]:
                    libepanet = resource_filename(epanet_toolkit, "Darwin/lib%s.dylib" % lib)
                    self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                else:
                    libepanet = resource_filename(epanet_toolkit, "Linux/lib%s.so" % lib)
                    self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                return
            except Exception as E1:
                if lib == libnames[-1]:
                    raise E1
                pass
            finally:
                self._project = None

        return

    # ----------running the simulation-----------------------------------------------------
    def MSXopen(self, nomeinp):
        """Opens the MSX Toolkit to analyze a particular distribution system
        Arguments:
        nomeinp: name of the msx input file
        """
        ierr = self.ENlib.MSXopen(ctypes.c_char_p(nomeinp.encode()))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXclose(
        self,
    ):
        """Closes down the Toolkit system (including all files being processed)"""
        ierr = self.ENlib.MSXclose()
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXusehydfile(self, fname):
        """Uses the contents of the specified file as the current binary hydraulics file"""
        ierr = self.ENlib.MSXusehydfile(ctypes.c_char_p(fname.encode()))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXsolveH(
        self,
    ):
        """Runs a complete hydraulic simulation with results
        for all time periods written to the binary Hydraulics file."""
        ierr = self.ENlib.MSXsolveH()
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXinit(self, saveFlag=0):
        """Initializes the MSX system before solving for water quality results in step-wise fashion
        set saveFlag to 1 if water quality results should be saved to a scratch binary file, or to 0 is not saved to file"""
        ierr = self.ENlib.MSXinit(saveFlag)
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXsolveQ(
        self,
    ):
        """solves for water quality over the entire simulation period and saves the results to an internal scratch file"""
        ierr = self.ENlib.MSXsolveQ()
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXstep(
        self,
    ):
        """Advances the water quality simulation one water quality time step.
        The time remaining in the overall simulation is returned as tleft, the current time as t."""
        t = ctypes.c_long()
        tleft = ctypes.c_long()
        ierr = self.ENlib.MSXstep(ctypes.byref(t), ctypes.byref(tleft))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        out = [t.value, tleft.value]
        return out

    def MSXsaveoutfile(self, fname):
        """saves water quality results computed for each node, link and reporting time period to a named binary file"""
        ierr = self.ENlib.MSXsaveoutfile(ctypes.c_char_p(fname.encode()))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXsavemsxfile(self, fname):
        """saves the data associated with the current MSX project into a new MSX input file"""
        ierr = self.ENlib.MSXsavemsxfile(ctypes.c_char_p(fname.encode()))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXreport(
        self,
    ):
        """Writes water quality simulations results as instructed by the MSX input file to a text file"""
        ierr = self.ENlib.MSXreport()
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    # ---------get parameters---------------------------------------------------------------
    def MSXgetindex(self, type, name):
        """Retrieves the internal index of an MSX object given its name.
        Arguments:
        type (int)
        MSX_SPECIES - 3 (for a chemical species)
        MSX_CONSTANT - 6 (for a reaction constant
        MSX_PARAMETER - 5 (for a reaction parameter)
        MSX_PATTERN - 7 (for a time pattern)"""
        type_ind = 100  # in case the type input is in text
        if type == "MSX_SPECIES" or type == 3:
            type_ind = 3
        if type == "MSX_CONSTANT" or type == 6:
            type_ind = 6
        if type == "MSX_PARAMETER" or type == 5:
            type_ind = 5
        if type == "MSX_PATTERN" or type == 7:
            type_ind = 7
        if type_ind == 100:
            raise Exception("unrecognized type")
        ind = ctypes.c_int()
        ierr = self.ENlib.MSXgetindex(type_ind, ctypes.c_char_p(name.encode()), ctypes.byref(ind))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return ind.value

    def MSXgetIDlen(self, type, index):
        """Retrieves the number of characters in the ID name of an MSX object given its internal index number.
        Arguments:
        type - int:
        MSX_SPECIES - 3 (for a chemical species)
        MSX_CONSTANT - 6 (for a reaction constant
        MSX_PARAMETER - 5 (for a reaction parameter)
        MSX_PATTERN - 7 (for a time pattern)"""
        type_ind = 100  # in case the type input is in text
        if type == "MSX_SPECIES" or type == 3:
            type_ind = 3
        if type == "MSX_CONSTANT" or type == 6:
            type_ind = 6
        if type == "MSX_PARAMETER" or type == 5:
            type_ind = 5
        if type == "MSX_PATTERN" or type == 7:
            type_ind = 7
        if type_ind == 100:
            raise Exception("unrecognized type")
        len = ctypes.c_int()
        ierr = self.ENlib.MSXgetIDlen(type_ind, ctypes.c_int(index), ctypes.byref(len))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return len.value

    def MSXgetID(self, type, index):
        """Retrieves the ID name of an object given its internal index number
        Arguments:
        type:
        MSX_SPECIES - 3 (for a chemical species)
        MSX_CONSTANT - 6 (for a reaction constant
        MSX_PARAMETER - 5 (for a reaction parameter)
        MSX_PATTERN - 7 (for a time pattern)
        maxlen: maxi number of characters that id can hold not counting null termination character"""
        type_ind = 100  # in case the type input is in text
        if type == "MSX_SPECIES" or type == 3:
            type_ind = 3
        if type == "MSX_CONSTANT" or type == 6:
            type_ind = 6
        if type == "MSX_PARAMETER" or type == 5:
            type_ind = 5
        if type == "MSX_PATTERN" or type == 7:
            type_ind = 7
        if type_ind == 100:
            raise Exception("unrecognized type")
        maxlen = 32
        id = ctypes.create_string_buffer(maxlen)
        ierr = self.ENlib.MSXgetID(type_ind, ctypes.c_int(index), ctypes.byref(id), ctypes.c_int(maxlen - 1))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        # the .decode() added my MF 6/3/21
        return id.value.decode()

    def MSXgetinitqual(self, type, ind, spe):
        """Retrieves the initial concentration of a particular chemical species assigned to a specific node
        or link of the pipe network.
        Arguments:
        type is type of object: MSX_NODE (0), MSX_LINK (1)
        ind is the internal sequence number (starting from 1) assigned to the node or link
        speicies is the sequence number of teh species (starting  from 1)"""
        type_ind = 100
        if type == "MSX_NODE" or type == 0:
            type_ind = 0
        if type == "MSX_LINK" or type == 1:
            type_ind = 1
        if type_ind == 100:
            raise Exception("unrecognized type")
        iniqual = ctypes.c_double()
        ierr = self.ENlib.MSXgetinitqual(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(spe), ctypes.byref(iniqual))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return iniqual.value

    def MSXgetqual(self, type, ind, spe):
        """Retrieves a chemical species concentration at a given node or the average concentration along a link at the current simulation time step
        Arguments:
        type is type of object: MSX_NODE (0), MSX_LINK (1)
        ind is the internal sequence number (starting from 1) assigned to the node or link
        speicies is the sequence number of teh species (starting  from 1)
        concentrations expressed as: mass units per liter for bulk species and mass per unit area for surface species"""
        type_ind = 100
        if type == "MSX_NODE" or type == 0:
            type_ind = 0
        if type == "MSX_LINK" or type == 1:
            type_ind = 1
        if type_ind == 100:
            raise Exception("unrecognized type")
        qual = ctypes.c_double()
        ierr = self.ENlib.MSXgetqual(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(spe), ctypes.byref(qual))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return qual.value

    def MSXgetconstant(self, ind):
        """Retrieves the value of a particular reaction constant
        Arguments:
        ind is the sequence number of the reaction constant (starting from 1) as it appeared in the MSX input file"""
        const = ctypes.c_double()
        ierr = self.ENlib.MSXgetconstant(ind, ctypes.byref(const))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return const.value

    def MSXgetparameter(self, type, ind, param_ind):
        """Retrieves the value of a particular reaction parameter for a give TANK or PIPE
        Arguments:
        type is the type of object: MSX_NODE (0) or MSX_LINK (1)
        ind is the internal sequence number(starting from 1) assigned to the node or link
        param is the sequence number of the parameter (starting from 1 as listed in the MSX input file)"""
        type_ind = 100  # in case type input is in text
        if type == "MSX_NODE" or type == 0:
            type_ind = 0
        if type == "MSX_LINK" or type == 1:
            type_ind = 1
        if type_ind == 100:
            raise Exception("unrecognized type")
        param = ctypes.c_double()
        ierr = self.ENlib.MSXgetparameter(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(param_ind), ctypes.byref(param))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return param.value

    def MSXgetsource(self, node, spe):
        """Retrieves information on any external source of a particular chemical species assigned to a specific node of the pipe network
        Arguments:
        node is the internal sequence number (starting from 1) assigned to the node of interest
        species is the sequence number of the species of interest (starting from 1 as listed in the MSX input file)
        type is returned with the type of external source and will be one of the following pre-defined constants
        MSX_NOSOURCE (-1) no source; MSX_CONCEN (0) a concentration source; MSX_MASS (1) mass booster source;
        MSX_SETPOINT (2) setpoint source; MSX_FLOWPACED (3) flow paced source
        level is returned with the baseline concentration (or mass flow rate) of the source
        pat is returned with the index of the time pattern used to add variability to the source's baseline level (0 if no pattern defined for the source)"""
        level = ctypes.c_double()
        type = ctypes.c_int()
        pat = ctypes.c_int()
        ierr = self.ENlib.MSXgetsource(ctypes.c_int(node), ctypes.c_int(spe), ctypes.byref(type), ctypes.byref(level), ctypes.byref(pat))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        src_out = [type.value, level.value, pat.value]
        return src_out

    def MSXgetpatternlen(self, pat):
        """Retrieves the number of time periods within a SOURCE time pattern
        Arguments:
        pat is the internal sequence number (starting from 1) of the pattern as appears in the MSX input file"""
        len = ctypes.c_int()
        ierr = self.ENlib.MSXgetpatternlen(pat, ctypes.byref(len))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return len.value

    def MSXgetpatternvalue(self, pat, period):
        """Retrieves the multiplier at a specific time period for a given SOURCE time pattern
        Arguments:
        pat is the internal sequence number (starting from 1) of the pattern as appears in the MSX input file
        period is the index of the time period (starting from 1) whose multiplier is being sought
        value is the vlaue of teh pattern's multiplier in teh desired period"""
        val = ctypes.c_double()
        ierr = self.ENlib.MSXgetpatternvalue(pat, period, ctypes.byref(val))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return val.value

    def MSXgetcount(self, type):
        """Retrieves the number of objects of a specified type.
        Arguments:
        MSX_SPECIES - 3 (for a chemical species)
        MSX_CONSTANT - 6 (for a reaction constant
        MSX_PARAMETER - 5 (for a reaction parameter)
        MSX_PATTERN - 7 (for a time pattern)
        maxlen: maxi number of characters that id can hold not counting null termination character"""
        type_ind = 100  # in case the type input is in text
        if type == "MSX_SPECIES" or type == 3:
            type_ind = 3
        if type == "MSX_CONSTANT" or type == 6:
            type_ind = 6
        if type == "MSX_PARAMETER" or type == 5:
            type_ind = 5
        if type == "MSX_PATTERN" or type == 7:
            type_ind = 7
        if type_ind == 100:
            raise Exception("unrecognized type")
        count = ctypes.c_int()
        ierr = self.ENlib.MSXgetcount(type_ind, ctypes.byref(count))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        return count.value

    def MSXgetspecies(self, spe):
        """Retrieves the attributes of a chemical species given its internal index number.
        species is the sequence number of the species (starting from 1 as listed in teh MSX input file_
        type: MSX_BULK (defined as 0) and MSX_WALL (defined as 1)
        units: C_style character string array that is returned with the mass units that were defined for the species in question(hold max 15 characters)
        aTol returned with absolute concentration tolerance defined for the species
        rTol returned with the relative concentration tolerance defined for the species"""
        type_ind = ctypes.c_int()
        units = ctypes.create_string_buffer(15)
        aTol = ctypes.c_double()
        rTol = ctypes.c_double()
        ierr = self.ENlib.MSXgetspecies(spe, ctypes.byref(type_ind), ctypes.byref(units), ctypes.byref(aTol), ctypes.byref(rTol))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
        spe_out = [type_ind.value, units.value, aTol.value, rTol.value]
        return spe_out

    def MSXgeterror(self, errcode, len=100):
        """returns the text for an error message given its error code
        arguments:
        code is the code number of an error condition generated by EPANET-MSX
        msg is a C-style string containing text of error message corresponding to error code
        len is the max number of charaters that msg can contain (at least 80)"""
        errmsg = ctypes.create_string_buffer(len)
        self.ENlib.MSXgeterror(errcode, ctypes.byref(errmsg), len)
        return errmsg.value.decode()

    # --------------set parameters-----------------------------------

    def MSXsetconstant(self, ind, value):
        """assigns a new value to a specific reaction constant
        Arguments:
        ind is the sequence number of the reaction constant (starting from 1) as it appreaed in the MSX input file
        value is the new value to be assigned to the constant"""
        ierr = self.ENlib.MSXsetconstant(ctypes.c_int(ind), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXsetparameter(self, type, ind, param, value):
        """assigns a value to a particular reaction parameter for a given TANK or PIPE
        Arguments:
        type is the type of object: MSX_NODE (0) or MSX_LINK (1)
        ind is the internal sequence number(starting from 1) assigned to the node or link
        param is the sequence number of the parameter (starting from 1 as listed in the MSX input file"""
        type_ind = 100
        if type == "MSX_NODE" or type == 0:
            type_ind = 0
        if type == "MSX_LINK" or type == 1:
            type_ind = 1
        if type_ind == 100:
            raise Exception("unrecognized type")
        ierr = self.ENlib.MSXsetparameter(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(param), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXsetinitqual(self, type, ind, spe, value):
        """Retrieves the initial concentration of a particular chemical species assigned to a specific node
        or link of the pipe network.
        Arguments:
        type is type of object: MSX_NODE (0), MSX_LINK (1)
        ind is the internal sequence number (starting from 1) assigned to the node or link
        speicies is the sequence number of teh species (starting  from 1)"""
        type_ind = 100
        if type == "MSX_NODE" or type == 0:
            type_ind = 0
        if type == "MSX_LINK" or type == 1:
            type_ind = 1
        if type_ind == 100:
            raise Exception("unrecognized type")
        ierr = self.ENlib.MSXsetinitqual(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(spe), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXsetsource(self, node, spe, type_n, level, pat):
        """sets the attributes of an external source of a particular chemical species in a specific node of the pipe network
        Arguments:
        node is the internal sequence number (starting from 1) assigned to the node of interest
        species is the sequence number of the species of interest (starting from 1 as listed in the MSX input file)
        type is returned with the type of exteernal source and will be one of the following pre-defined constants
        MSX_NOSOURCE (-1) no source; MSX_CONCEN (0) a concentration source; MSX_MASS (1) mass booster source;
        MSX_SETPOINT (2) setpoint source; MSX_FLOWPACED (3) flow paced source
        level is the baseline concentration (or mass flow rate) of the source
        pat is the index of the time pattern used to add variability to the source's baseline level (0 if no pattern defined for the source)"""
        type_ind = 100
        if type_n == "MSX_NOSOURCE" or type_n == -1:
            type_ind = -1
        if type_n == "MSX_CONCEN" or type_n == 0:
            type_ind = 0
        if type_n == "MSX_MASS" or type_n == 1:
            type_ind = 1
        if type_n == "MSX_SETPOINT" or type_n == 2:
            type_ind = 2
        if type_n == "MSX_FLOWPACED" or type_n == 3:
            type_ind = 3
        if type_ind == 100:
            raise Exception("unrecognized type")
        ierr = self.ENlib.MSXsetsource(ctypes.c_int(node), ctypes.c_int(spe), ctypes.c_int(type_ind), ctypes.c_double(level), ctypes.c_int(pat))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXsetpattern(self, pat, mult):
        """assigns a new set of multipliers to a given MSX SOURCE time pattern
        Arguments:
        pat is the internal sequence number (starting from 1) of the pattern as appears in the MSX input file
        mult is an array of multiplier values to replace those preciously used by the pattern
        len is the number of entries in mult"""
        length = len(mult)
        cfactors_type = ctypes.c_double * length
        cfactors = cfactors_type()
        for i in range(length):
            cfactors[i] = float(mult[i])
        ierr = self.ENlib.MSXsetpattern(ctypes.c_int(pat), cfactors, ctypes.c_int(length))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXsetpatternvalue(self, pat, period, value):
        """Sets the multiplier factor for a specific period within a SOURCE time pattern.
        Arguments:
        index: time pattern index
        period: period within time pattern
        value:  multiplier factor for the period"""
        ierr = self.ENlib.MSXsetpatternvalue(ctypes.c_int(pat), ctypes.c_int(period), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)

    def MSXaddpattern(self, patternid):
        """Adds a new, empty MSX source time pattern to an MSX project.
        Arguments:
        pattern id: c-string name of pattern"""
        ierr = self.ENlib.MSXaddpattern(ctypes.c_char_p(patternid.encode()))
        if ierr != 0:
            raise EpanetMsxToolkitError(ierr)
