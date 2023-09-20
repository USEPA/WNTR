"""
The wntr.reaction.toolkit module is a Python extension for the EPANET MSX
Programmers Toolkit DLLs.

.. note::
    
    Code in this section taken from code originally written by Junli Hao 07/29/2018, 
    "EPANET-MSX-Python-wrapper" on GitHub, licensed under the BSD license. See LICENSE.txt for more 
    details.
"""
import ctypes
from enum import IntEnum
import os
import os.path
import platform
import sys
from ctypes import byref
from typing import Union

from pkg_resources import resource_filename

from wntr.epanet.msx.enums import ObjectType, SourceType

from ..toolkit import ENepanet
from ..util import SizeLimits
from .exceptions import EpanetMsxException, MSX_ERROR_CODES, MSXKeyError, MSXValueError

epanet_toolkit = "wntr.epanet.toolkit"

if os.name in ["nt", "dos"]:
    libepanet = resource_filename(__name__, "../Windows/epanet2.dll")
    libmsx = resource_filename(__name__, "../Windows/epanetmsx.dll")
elif sys.platform in ["darwin"]:
    libepanet = resource_filename(__name__, "../Darwin/libepanet.dylib")
    libmsx = resource_filename(__name__, "../Darwin/libepanetmsx.dylib")
else:
    libepanet = resource_filename(__name__, "../Linux/libepanet2.so")
    libmsx = resource_filename(__name__, "../Linux/libepanetmsx.so")

import logging

logger = logging.getLogger(__name__)


class MSXepanet(ENepanet):
    def __init__(self, inpfile="", rptfile="", binfile="", msxfile=""):

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

    # ----------running the simulation-----------------------------------------------------
    def MSXopen(self, msxfile):
        """Opens the MSX Toolkit to analyze a particular distribution system.

        Parameters
        ----------
        msxfile : str
            name of the MSX input file
        """
        ierr = self.ENlib.MSXopen(ctypes.c_char_p(msxfile.encode()))
        if ierr != 0:
            raise EpanetMsxException(ierr, msxfile)

    def MSXclose(self):
        """Closes down the Toolkit system (including all files being processed)"""
        ierr = self.ENlib.MSXclose()
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXusehydfile(self, filename):
        """Uses the contents of the specified file as the current binary hydraulics file

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
        """Initializes the MSX system before solving for water quality results in step-wise fashion
        set saveFlag to 1 if water quality results should be saved to a scratch binary file, or to 0 is not saved to file"""
        saveFlag = int(saveFlag)
        ierr = self.ENlib.MSXinit(saveFlag)
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsolveQ(self):
        """solves for water quality over the entire simulation period and saves the results to an internal scratch file"""
        ierr = self.ENlib.MSXsolveQ()
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXstep(self):
        """Advances the water quality simulation one water quality time step.
        The time remaining in the overall simulation is returned as tleft, the current time as t."""
        t = ctypes.c_long()
        tleft = ctypes.c_long()
        ierr = self.ENlib.MSXstep(ctypes.byref(t), ctypes.byref(tleft))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        out = [t.value, tleft.value]
        return out

    def MSXsaveoutfile(self, filename):
        """saves water quality results computed for each node, link and reporting time period to a named binary file
        
        Parameters
        ----------
        filename : str
            Save a binary results file
        """
        ierr = self.ENlib.MSXsaveoutfile(ctypes.c_char_p(filename.encode()))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsavemsxfile(self, filename):
        """saves the data associated with the current MSX project into a new MSX input file
        
        Parameters
        ----------
        filename : str
            the name of the MSX input file to create
        """
        ierr = self.ENlib.MSXsavemsxfile(ctypes.c_char_p(filename.encode()))
        if ierr != 0:
            raise EpanetMsxException(ierr, filename)

    def MSXreport(self):
        """Writes water quality simulations results as instructed by the MSX input file to a text file"""
        ierr = self.ENlib.MSXreport()
        if ierr != 0:
            raise EpanetMsxException(ierr)

    # ---------get parameters---------------------------------------------------------------
    def MSXgetindex(self, _type: Union[int, ObjectType], name):
        """Retrieves the internal index of an MSX object given its name.

        Parameters
        ----------
        _type : int, str or ObjectType
            The type of object to get an index for
        name : str 
            The name of the object to get an index for

        Returns
        -------
        int
            The internal index
        
        Raises
        ------
        MSXKeyError
            if an invalid str is passed for _type
        MSXValueError
            if _type is not a valid MSX object type
        """
        try:
            _type = ObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        ind = ctypes.c_int()
        ierr = self.ENlib.MSXgetindex(type_ind, ctypes.c_char_p(name.encode()), ctypes.byref(ind))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, name=name)))
        return ind.value

    def MSXgetIDlen(self, _type, index):
        """Retrieves the number of characters in the ID name of an MSX object given its internal index number.

        Parameters
        ----------
        _type : int, str or ObjectType
            The type of object to get an index for
        index : int 
            The index of the object to get the ID length for

        Returns
        -------
        int
            the length of the object ID
        """
        try:
            _type = ObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        len = ctypes.c_int()
        ierr = self.ENlib.MSXgetIDlen(type_ind, ctypes.c_int(index), ctypes.byref(len))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, index=index)))
        return len.value

    def MSXgetID(self, _type, index):
        """Retrieves the ID name of an object given its internal index number

        Parameters
        ----------
        _type : int, str or ObjectType
            The type of object to get an index for
        index : int 
            The index of the object to get the ID for

        Returns
        -------
        str
            the object ID
        """
        try:
            _type = ObjectType.get(_type)
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
        """Retrieves the initial concentration of a particular chemical species assigned to a specific node
        or link of the pipe network

        Parameters
        ----------
        _type : str, int or ObjectType
            the type of object
        node_link_index : int
            the object index
        species_index : int
            the species index

        Returns
        -------
        float
            the initial quality value for that node or link

        Raises
        ------
        MSXKeyError
            the type passed in for ``_type`` is not valid
        MSXValueError
            the value for ``_type`` is not valid
        EpanetMsxException
            any other error from the C-API
        """
        try:
            _type = ObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [ObjectType.NODE, ObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        iniqual = ctypes.c_double()
        ierr = self.ENlib.MSXgetinitqual(ctypes.c_int(type_ind), ctypes.c_int(node_link_index), ctypes.c_int(species_index), ctypes.byref(iniqual))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, node_link_index=node_link_index, species_index=species_index)))
        return iniqual.value

    def MSXgetqual(self, _type, node_link_index, species_index):
        """Retrieves a chemical species concentration at a given node or the average concentration along a link at the current simulation time step

        Parameters
        ----------
        _type : str, int or ObjectType
            the type of object
        node_link_index : int
            the object index
        species_index : int
            the species index

        Returns
        -------
        float
            the current quality value for that node or link

        Raises
        ------
        MSXKeyError
            the type passed in for ``_type`` is not valid
        MSXValueError
            the value for ``_type`` is not valid
        EpanetMsxException
            any other error from the C-API
        """
        try:
            _type = ObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [ObjectType.NODE, ObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        qual = ctypes.c_double()
        ierr = self.ENlib.MSXgetqual(ctypes.c_int(type_ind), ctypes.c_int(node_link_index), ctypes.c_int(species_index), ctypes.byref(qual))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, node_link_index=node_link_index, species_index=species_index)))
        return qual.value

    def MSXgetconstant(self, constant_index):
        """Retrieves the value of a particular reaction constant

        Parameters
        ----------
        constant_index : int
            index to the constant

        Returns
        -------
        float
            the value of the constant

        Raises
        ------
        EpanetMsxException
            a toolkit error occurred
        """
        const = ctypes.c_double()
        ierr = self.ENlib.MSXgetconstant(constant_index, ctypes.byref(const))
        if ierr != 0:
            raise EpanetMsxException(ierr, constant_index)
        return const.value

    def MSXgetparameter(self, _type, node_link_index, param_index):
        """Retrieves the value of a particular reaction parameter for a given TANK or PIPE.

        Parameters
        ----------
        _type : _type_
            _description_
        node_link_index : _type_
            _description_
        param_index : _type_
            _description_

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        MSXKeyError
            _description_
        MSXValueError
            _description_
        EpanetMsxException
            _description_
        """
        try:
            _type = ObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [ObjectType.NODE, ObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        param = ctypes.c_double()
        ierr = self.ENlib.MSXgetparameter(ctypes.c_int(type_ind), ctypes.c_int(node_link_index), ctypes.c_int(param_index), ctypes.byref(param))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(_type=_type, node_link_index=node_link_index, param_index=param_index)))
        return param.value

    def MSXgetsource(self, node_index, species_index):
        """Retrieves information on any external source of a particular chemical species assigned to a specific node of the pipe network
        """
        #level is returned with the baseline concentration (or mass flow rate) of the source
        #pat is returned with the index of the time pattern used to add variability to the source's baseline level (0 if no pattern defined for the source)"""
        level = ctypes.c_double()
        _type = ctypes.c_int()
        pat = ctypes.c_int()
        ierr = self.ENlib.MSXgetsource(ctypes.c_int(node_index), ctypes.c_int(species_index), ctypes.byref(_type), ctypes.byref(level), ctypes.byref(pat))
        if ierr != 0:
            raise EpanetMsxException(ierr, repr(dict(node_index=node_index, species_index=species_index)))
        src_out = [SourceType.get(_type.value), level.value, pat.value]
        return src_out

    def MSXgetpatternlen(self, pat):
        """Retrieves the number of time periods within a SOURCE time pattern.

        Parameters
        ----------
        pat : _type_
            _description_

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        EpanetMsxException
            _description_
        """
        len = ctypes.c_int()
        ierr = self.ENlib.MSXgetpatternlen(pat, ctypes.byref(len))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        return len.value

    def MSXgetpatternvalue(self, pat, period):
        """Retrieves the multiplier at a specific time period for a given SOURCE time pattern

        Parameters
        ----------
        pat : _type_
            _description_
        period : int
            1-indexed period of the pattern to retrieve

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        EpanetMsxException
            _description_
        """
        val = ctypes.c_double()
        ierr = self.ENlib.MSXgetpatternvalue(pat, period, ctypes.byref(val))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        return val.value

    def MSXgetcount(self, _type):
        """Retrieves the number of objects of a specified type.

        Parameters
        ----------
        _type : _type_
            _description_

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        MSXKeyError
            _description_
        EpanetMsxException
            _description_
        """
        try:
            _type = ObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        count = ctypes.c_int()
        ierr = self.ENlib.MSXgetcount(type_ind, ctypes.byref(count))
        if ierr != 0:
            raise EpanetMsxException(ierr)
        return count.value

    def MSXgetspecies(self, species_index):
        """Retrieves the attributes of a chemical species given its internal index number.
        species is the sequence number of the species (starting from 1 as listed in the MSX input file

        Parameters
        ----------
        species_index : _type_
            _description_

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        EpanetMsxException
            _description_
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
        """returns the text for an error message given its error code

        Parameters
        ----------
        errcode : _type_
            _description_
        len : int, optional
            _description_, by default 100 and minimum 80

        Returns
        -------
        _type_
            _description_
        """
        errmsg = ctypes.create_string_buffer(len)
        self.ENlib.MSXgeterror(errcode, ctypes.byref(errmsg), len)
        return errmsg.value.decode()

    # --------------set parameters-----------------------------------

    def MSXsetconstant(self, ind, value):
        """assigns a new value to a specific reaction constant

        Parameters
        ----------
        ind : _type_
            _description_
        value : _type_
            _description_

        Raises
        ------
        EpanetMsxException
            _description_
        """
        ierr = self.ENlib.MSXsetconstant(ctypes.c_int(ind), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetparameter(self, _type, ind, param, value):
        """assigns a value to a particular reaction parameter for a given TANK or PIPE

        Parameters
        ----------
        _type : _type_
            _description_
        ind : _type_
            _description_
        param : _type_
            _description_
        value : _type_
            _description_

        Raises
        ------
        MSXKeyError
            _description_
        MSXValueError
            _description_
        EpanetMsxException
            _description_
        """
        try:
            _type = ObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [ObjectType.NODE, ObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        ierr = self.ENlib.MSXsetparameter(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(param), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetinitqual(self, _type, ind, spe, value):
        """Retrieves the initial concentration of a particular chemical species assigned to a specific node
        or link of the pipe network.

        Parameters
        ----------
        _type : _type_
            _description_
        ind : _type_
            _description_
        spe : _type_
            _description_
        value : _type_
            _description_

        Raises
        ------
        MSXKeyError
            _description_
        MSXValueError
            _description_
        EpanetMsxException
            _description_
        """
        try:
            _type = ObjectType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        if _type not in [ObjectType.NODE, ObjectType.LINK]:
            raise MSXValueError(515, repr(_type))
        type_ind = int(_type)
        ierr = self.ENlib.MSXsetinitqual(ctypes.c_int(type_ind), ctypes.c_int(ind), ctypes.c_int(spe), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetsource(self, node, spe, _type, level, pat):
        """sets the attributes of an external source of a particular chemical species in a specific node of the pipe network

        Parameters
        ----------
        node : _type_
            _description_
        spe : _type_
            _description_
        _type : _type_
            _description_
        level : _type_
            _description_
        pat : _type_
            _description_

        Raises
        ------
        MSXKeyError
            _description_
        EpanetMsxException
            _description_
        """
        try:
            _type = SourceType.get(_type)
        except KeyError:
            raise MSXKeyError(515, repr(_type))
        type_ind = int(_type)
        ierr = self.ENlib.MSXsetsource(ctypes.c_int(node), ctypes.c_int(spe), ctypes.c_int(type_ind), ctypes.c_double(level), ctypes.c_int(pat))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXsetpattern(self, pat, mult):
        """assigns a new set of multipliers to a given MSX SOURCE time pattern

        Parameters
        ----------
        pat : _type_
            _description_
        mult : _type_
            _description_

        Raises
        ------
        EpanetMsxException
            _description_
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
        """Sets the multiplier factor for a specific period within a SOURCE time pattern.

        Parameters
        ----------
        pat : _type_
            _description_
        period : _type_
            _description_
        value : _type_
            _description_

        Raises
        ------
        EpanetMsxException
            _description_
        """
        ierr = self.ENlib.MSXsetpatternvalue(ctypes.c_int(pat), ctypes.c_int(period), ctypes.c_double(value))
        if ierr != 0:
            raise EpanetMsxException(ierr)

    def MSXaddpattern(self, patternid):
        """Adds a new, empty MSX source time pattern to an MSX project.

        Parameters
        ----------
        patternid : _type_
            _description_

        Raises
        ------
        EpanetMsxException
            _description_
        """
        ierr = self.ENlib.MSXaddpattern(ctypes.c_char_p(patternid.encode()))
        if ierr != 0:
            raise EpanetMsxException(ierr)
