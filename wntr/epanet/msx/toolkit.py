# coding: utf-8
"""
The wntr.epanet.msx.toolkit module is a Python extension for the EPANET-MSX
Programmers Toolkit DLLs.

.. note::
    
    Code in this section is based on code from "EPANET-MSX-Python-wrapper",
    licensed under the BSD license. See LICENSE.md for details.
"""
import ctypes
import os
import os.path
import platform
import sys
from typing import Union

from pkg_resources import resource_filename

from wntr.epanet.msx.enums import TkObjectType, TkSourceType

from ..toolkit import ENepanet
from .exceptions import MSX_ERROR_CODES, EpanetMsxException, MSXKeyError, MSXValueError

epanet_toolkit = "wntr.epanet.toolkit"

if os.name in ["nt", "dos"]:
    libepanet = resource_filename(__name__, "../Windows/epanet2.lib")
    libmsx = resource_filename(__name__, "../Windows/epanetmsx.lib")
elif sys.platform in ["darwin"]:
    libepanet = resource_filename(__name__, "../Darwin/libepanet2.dylib")
    libmsx = resource_filename(__name__, "../Darwin/libepanetmsx.dylib")
else:
    libepanet = resource_filename(__name__, "../Linux/libepanet2.so")
    libmsx = resource_filename(__name__, "../Linux/libepanetmsx.so")

dylib_dir = os.environ.get('DYLD_FALLBACK_LIBRARY_PATH','')
if dylib_dir != '':
    dylib_dir = dylib_dir + ':' + resource_filename(__name__, "../Darwin")
    os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = dylib_dir

import logging

logger = logging.getLogger(__name__)


class MSXepanet(ENepanet):
    def __init__(self, inpfile="", rptfile="", binfile="", msxfile=""):

        if 'WNTR_PATH_TO_EPANETMSX' in os.environ:
            msx_toolkit = os.environ['WNTR_PATH_TO_EPANETMSX']
        else:
            msx_toolkit = None

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
        self.msxfile = msxfile

        libnames = ["epanetmsx"]
        if "64" in platform.machine():
            libnames.insert(0, "epanetmsx")
        if msx_toolkit:
            for lib in libnames:
                try:
                    if os.name in ["nt", "dos"]:
                        libepanet = os.path.join(msx_toolkit, "%s.dll" % lib)
                        self.ENlib = ctypes.windll.LoadLibrary(libepanet)
                    elif sys.platform in ["darwin"]:
                        libepanet = os.path.join(msx_toolkit, "lib%s.dylib" % lib)
                        self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                    else:
                        libepanet = os.path.join(msx_toolkit, "lib%s.so" % lib)
                        self.ENlib = ctypes.cdll.LoadLibrary(libepanet)
                    return
                except Exception as E1:
                    if lib == libnames[-1]:
                        raise E1
                    pass
                finally:
                    self._project = None
        else:
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

    def _error(self, *args):
        """Print the error text the corresponds to the error code returned"""
        if not self.errcode:
            return
        # errtxt = self.ENlib.ENgeterror(self.errcode)
        errtext =  MSX_ERROR_CODES.get(self.errcode, 'unknown error')
        if '%' in errtext and len(args) == 1:
            errtext % args
        if self.errcode >= 100:
            self.Errflag = True
            logger.error("EPANET error {} - {}".format(self.errcode, errtext))
            raise EpanetMsxException(self.errcode)
        return

    # ----------running the simulation-----------------------------------------
    def MSXopen(self, msxfile):
        """Opens the MSX Toolkit to analyze a particular distribution system.

        Parameters
        ----------
        msxfile : str
            Name of the MSX input file
        """
        if msxfile is not None:
            msxfile = ctypes.c_char_p(msxfile.encode())
        ierr = self.ENlib.MSXopen(msxfile)
        if ierr != 0:
            raise EpanetMsxException(ierr, msxfile)

    def MSXclose(self):
        """Closes down the Toolkit system (including all files being processed)"""
        ierr = self.ENlib.MSXclose()
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXusehydfile(self, filename):
        """Uses the contents of the specified file as the current binary
        hydraulics file

        Parameters
        ----------
        filename : str
            Name of the hydraulics file to use
        """
        ierr = self.ENlib.MSXusehydfile(ctypes.c_char_p(filename.encode()))
        if ierr != 0:
            raise EpanetMsxException(ierr, filename)

    def MSXsolveH(self):
        """Runs a complete hydraulic simulation with results
        for all time periods written to the binary Hydraulics file."""
        ierr = self.ENlib.MSXsolveH()
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXinit(self, saveFlag=0):
        """Initializes the MSX system before solving for water quality results
        in step-wise fashion set saveFlag to 1 if water quality results should
        be saved to a scratch binary file, or to 0 is not saved to file"""
        saveFlag = int(saveFlag)
        ierr = self.ENlib.MSXinit(saveFlag)
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsolveQ(self):
        """Solves for water quality over the entire simulation period and saves
        the results to an internal scratch file"""
        ierr = self.ENlib.MSXsolveQ()
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXstep(self):
        """Advances the water quality simulation one water quality time step.
        The time remaining in the overall simulation is returned as tleft, the
        current time as t."""
        t = ctypes.c_long()
        tleft = ctypes.c_long()
        ierr = self.ENlib.MSXstep(ctypes.byref(t), ctypes.byref(tleft))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        out = [t.value, tleft.value]
        return out

    def MSXsaveoutfile(self, filename):
        """Saves water quality results computed for each node, link and
        reporting time period to a named binary file

        Parameters
        ----------
        filename : str
            Save a binary results file
        """
        ierr = self.ENlib.MSXsaveoutfile(ctypes.c_char_p(filename.encode()))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsavemsxfile(self, filename):
        """Saves the data associated with the current MSX project into a new
        MSX input file

        Parameters
        ----------
        filename : str
            Name of the MSX input file to create
        """
        ierr = self.ENlib.MSXsavemsxfile(ctypes.c_char_p(filename.encode()))
        if ierr != 0:
            raise EpanetMsxException(ierr, filename)

    def MSXreport(self):
        """Writes water quality simulations results as instructed by the MSX
        input file to a text file"""
        ierr = self.ENlib.MSXreport()
        if ierr != 0:
            raise EpanetMsxException(ierr)

    # ---------get parameters--------------------------------------------------
    def MSXgetindex(self, _type: Union[int, TkObjectType], name):
        """Gets the internal index of an MSX object given its name.

        Parameters
        ----------
        _type : int, str or ObjectType
            Type of object to get an index for
        name : str 
            Name of the object to get an index for

        Returns
        -------
        int
            Internal index
        
        Raises
        ------
        MSXKeyError
            If an invalid str is passed for _type
        MSXValueError
            If _type is not a valid MSX object type
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        ind = ctypes.c_int()
        ierr = self.ENlib.MSXgetindex(type_ind, ctypes.c_char_p(name.encode()), ctypes.byref(ind))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, name=name)))
        return ind.value

    def MSXgetIDlen(self, _type, index):
        """Get the number of characters in the ID name of an MSX object
        given its internal index number.

        Parameters
        ----------
        _type : int, str or ObjectType
            Type of object to get an index for
        index : int
            Index of the object to get the ID length for

        Returns
        -------
        int
            Length of the object ID
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        len = ctypes.c_int()
        ierr = self.ENlib.MSXgetIDlen(type_ind, ctypes.c_int(index), ctypes.byref(len))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, index=index)))
        return len.value

    def MSXgetID(self, _type, index):
        """Get the ID name of an object given its internal index number

        Parameters
        ----------
        _type : int, str or ObjectType
            Type of object to get an index for
        index : int
            Index of the object to get the ID for

        Returns
        -------
        str
            Object ID
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        maxlen = 32
        id = ctypes.create_string_buffer(maxlen)
        ierr = self.ENlib.MSXgetID(type_ind, ctypes.c_int(index), ctypes.byref(id), ctypes.c_int(maxlen - 1))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, index=index)))
        # the .decode() added my MF 6/3/21
        return id.value.decode()

    def MSXgetinitqual(self, _type, node_link_index, species_index):
        """Get the initial concentration of a particular chemical species
        assigned to a specific node or link of the pipe network

        Parameters
        ----------
        _type : str, int or ObjectType
            Type of object
        node_link_index : int
            Object index
        species_index : int
            Species index

        Returns
        -------
        float
            Initial quality value for that node or link

        Raises
        ------
        MSXKeyError
            Type passed in for ``_type`` is not valid
        MSXValueError
            Value for ``_type`` is not valid
        EpanetMsxException
            Any other error from the C-API
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [TkObjectType.NODE, TkObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        iniqual = ctypes.c_double()
        ierr = self.ENlib.MSXgetinitqual(ctypes.c_int(type_ind), ctypes.c_int(node_link_index), ctypes.c_int(species_index), ctypes.byref(iniqual))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, node_link_index=node_link_index, species_index=species_index)))
        return iniqual.value

    def MSXgetqual(self, _type, node_link_index, species_index):
        """Get a chemical species concentration at a given node or the
        average concentration along a link at the current simulation time step

        Parameters
        ----------
        _type : str, int or ObjectType
            Type of object
        node_link_index : int
            Object index
        species_index : int
            Species index

        Returns
        -------
        float
            Current quality value for that node or link

        Raises
        ------
        MSXKeyError
            Type passed in for ``_type`` is not valid
        MSXValueError
            Value for ``_type`` is not valid
        EpanetMsxException
            Any other error from the C-API
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [TkObjectType.NODE, TkObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        qual = ctypes.c_double()
        ierr = self.ENlib.MSXgetqual(ctypes.c_int(type_ind), ctypes.c_int(node_link_index), ctypes.c_int(species_index), ctypes.byref(qual))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, node_link_index=node_link_index, species_index=species_index)))
        return qual.value

    def MSXgetconstant(self, constant_index):
        """Get the value of a particular reaction constant

        Parameters
        ----------
        constant_index : int
            Index to the constant

        Returns
        -------
        float
            Value of the constant

        Raises
        ------
        EpanetMsxException
            Toolkit error occurred
        """
        const = ctypes.c_double()
        ierr = self.ENlib.MSXgetconstant(constant_index, ctypes.byref(const))
        if ierr != 0:
            raise EpanetMsxException(ierr, constant_index)
        return const.value

    def MSXgetparameter(self, _type, node_link_index, param_index):
        """Get the value of a particular reaction parameter for a given
        TANK or PIPE.

        Parameters
        ----------
        _type : int or str or Enum
            Get the type of the parameter
        node_link_index : int
            Link index
        param_index : int
            Parameter variable index

        Returns
        -------
        float
            Parameter value

        Raises
        ------
        MSXKeyError
            If there is no such _type
        MSXValueError
            If the _type is improper
        EpanetMsxException
            Any other error
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [TkObjectType.NODE, TkObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        param = ctypes.c_double()
        ierr = self.ENlib.MSXgetparameter(ctypes.c_int(type_ind), ctypes.c_int(node_link_index), ctypes.c_int(param_index), ctypes.byref(param))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, node_link_index=node_link_index, param_index=param_index)))
        return param.value

    def MSXgetsource(self, node_index, species_index):
        """Get information on any external source of a particular
        chemical species assigned to a specific node of the pipe network
        
        Parameters
        ----------
        node_index : int
            Node index
        species_index : int
            Species index
            
        Returns
        -------
        list
            [source type, level, and pattern] where level is the baseline 
            concentration (or mass flow rate) of the source and pattern the 
            index of the time pattern used to add variability to the source's 
            baseline level (0 if no pattern defined for the source)
        """
        level = ctypes.c_double()
        _type = ctypes.c_int()
        pat = ctypes.c_int()
        ierr = self.ENlib.MSXgetsource(ctypes.c_int(node_index), ctypes.c_int(species_index), ctypes.byref(_type), ctypes.byref(level), ctypes.byref(pat))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(node_index=node_index, species_index=species_index)))
        src_out = [TkSourceType.get(_type.value), level.value, pat.value]
        return src_out

    def MSXgetpatternlen(self, pat):
        """Get the number of time periods within a SOURCE time pattern.

        Parameters
        ----------
        pat : int
            Pattern index

        Returns
        -------
        int
            Number of time periods in the pattern
        """
        len = ctypes.c_int()
        ierr = self.ENlib.MSXgetpatternlen(pat, ctypes.byref(len))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        return len.value

    def MSXgetpatternvalue(self, pat, period):
        """Get the multiplier at a specific time period for a given
        SOURCE time pattern

        Parameters
        ----------
        pat : int
            Pattern index
        period : int
            1-indexed period of the pattern to retrieve

        Returns
        -------
            Multiplier
        """
        val = ctypes.c_double()
        ierr = self.ENlib.MSXgetpatternvalue(pat, period, ctypes.byref(val))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        return val.value

    def MSXgetcount(self, _type):
        """Get the number of objects of a specified type.

        Parameters
        ----------
        _type : int or str or Enum
            Type of object to count

        Returns
        -------
        int
            Number of objects of specified type

        Raises
        ------
        MSXKeyError
            If the _type is invalid
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        count = ctypes.c_int()
        ierr = self.ENlib.MSXgetcount(type_ind, ctypes.byref(count))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        return count.value

    def MSXgetspecies(self, species_index):
        """Get the attributes of a chemical species given its internal
        index number.

        Parameters
        ----------
        species_index : int
            Species index to query (starting from 1 as listed in the MSX input
            file)

        Returns
        -------
        int, str, float, float
            Type, units, aTol, and rTol for the species
        """
        type_ind = ctypes.c_int()
        units = ctypes.create_string_buffer(15)
        aTol = ctypes.c_double()
        rTol = ctypes.c_double()
        ierr = self.ENlib.MSXgetspecies(species_index, ctypes.byref(type_ind), ctypes.byref(units), ctypes.byref(aTol), ctypes.byref(rTol))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        spe_out = [type_ind.value, units.value, aTol.value, rTol.value]
        return spe_out

    def MSXgeterror(self, errcode, len=100):
        """Get the text for an error message given its error code

        Parameters
        ----------
        errcode : int
            Error code
        len : int, optional
            Length of the error message, by default 100 and minimum 80

        Returns
        -------
        str
            String decoded from the DLL

        Warning
        -------
        Getting string parameters in this way is not recommended, because it
        requires setting up string arrays that may or may not be the correct
        size. Use the wntr.epanet.msx.enums package to get error information.
        """
        errmsg = ctypes.create_string_buffer(len)
        self.ENlib.MSXgeterror(errcode, ctypes.byref(errmsg), len)
        return errmsg.value.decode()

    # --------------set parameters-----------------------------------

    def MSXsetconstant(self, ind, value):
        """Set a new value to a specific reaction constant

        Parameters
        ----------
        ind : int
            Index to the variable
        value : float
            Value to give the constant
        """
        ierr = self.ENlib.MSXsetconstant(ctypes.c_int(ind), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetparameter(self, _type, ind, param, value):
        """Set a value to a particular reaction parameter for a given TANK
        or PIPE

        Parameters
        ----------
        _type : int or str or enum
            Type of value to set
        ind : int
            Tank or pipe index
        param : int
            Parameter variable index
        value : float
            Value to be set

        Raises
        ------
        MSXKeyError
            If there is no such _type
        MSXValueError
            If the _type is invalid
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [TkObjectType.NODE, TkObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        ierr = self.ENlib.MSXsetparameter(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(param), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetinitqual(self, _type, ind, spe, value):
        """Set the initial concentration of a particular chemical species
        assigned to a specific node or link of the pipe network.

        Parameters
        ----------
        _type : int or str or enum
            Type of network element to set
        ind : int
            Index of the network element
        spe : int
            Index of the species
        value : float
            Initial quality value
        """
        try:
            _type = TkObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [TkObjectType.NODE, TkObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        ierr = self.ENlib.MSXsetinitqual(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(spe), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetsource(self, node, spe, _type, level, pat):
        """Set the attributes of an external source of a particular chemical
        species in a specific node of the pipe network

        Parameters
        ----------
        node : int
            Node index
        spe : int
            Species index
        _type : int or str or enum
            Type of source
        level : float
            Source quality value
        pat : int
            Pattern index
        """
        try:
            _type = TkSourceType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        ierr = self.ENlib.MSXsetsource(ctypes.c_int(node), ctypes.c_int(spe), ctypes.c_int(type_ind), ctypes.c_double(level), ctypes.c_int(pat))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetpattern(self, pat, mult):
        """Set multipliers to a given MSX SOURCE time pattern

        Parameters
        ----------
        pat : int
            Pattern index
        mult : list-like
            Pattern multipliers
        """
        length = len(mult)
        cfactors_type = ctypes.c_double * length
        cfactors = cfactors_type()
        for i in range(length):
            cfactors[i] = float(mult[i])
        ierr = self.ENlib.MSXsetpattern(ctypes.c_int(pat), cfactors, ctypes.c_int(length))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetpatternvalue(self, pat, period, value):
        """Set the multiplier factor for a specific period within a SOURCE time
        pattern.

        Parameters
        ----------
        pat : int
            Pattern index
        period : int
            1-indexed pattern time period index
        value : float
            Value to set at that time period
        """
        ierr = self.ENlib.MSXsetpatternvalue(ctypes.c_int(pat), ctypes.c_int(period), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXaddpattern(self, patternid):
        """Add a new, empty MSX source time pattern to an MSX project.

        Parameters
        ----------
        patternid : str
            Name of the new pattern
        """
        ierr = self.ENlib.MSXaddpattern(ctypes.c_char_p(patternid.encode()))
        if ierr != 0:
            raise EpanetMsxException(ierr)
