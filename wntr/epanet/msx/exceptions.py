# coding: utf-8
"""EPANET-MSX error and exception classes."""

from enum import IntEnum
from typing import List

from wntr.utils.enumtools import add_get

from ..exceptions import EN_ERROR_CODES, EpanetException

MSX_ERROR_CODES = {
    # MSX syntax errors
    401: "too many characters",
    402: "too few input items",
    403: "invalid keyword: '%s'",
    404: "invalid numeric value: '%s'",
    405: "reference to undefined object: '%s'",
    406: "illegal use of reserved name: '%s'",
    407: "name already used by another object: '%s'",
    408: "species already assigned an expression: '%s'",
    409: "illegal math expression",
    410: "option no longer supported",
    411: "term '%s' contains a cyclic reference",
    # MSX runtime errors
    501: "insufficient memory available",
    502: "no EPANET data file supplied",
    503: "could not open MSX input file %s",
    504: "could not open hydraulic results file",
    505: "could not read hydraulic results file",
    506: "could not read MSX input file %s",
    507: "too few pipe reaction expressions",
    508: "too few tank reaction expressions",
    509: "could not open differential equation solver",
    510: "could not open algebraic equation solver",
    511: "could not open binary results file",
    512: "read/write error on binary results file",
    513: "could not integrate reaction rate expressions",
    514: "could not solve reaction equilibrium expressions",
    515: "reference made to an unknown type of object %s",
    516: "reference made to an illegal object index %s",
    517: "reference made to an undefined object ID %s",
    518: "invalid property values were specified",
    519: "an MSX project was not opened",
    520: "an MSX project is already opened",
    522: "could not compile chemistry functions",
    523: "could not load functions from compiled chemistry file",
    524: "illegal math operation",
}
"""Dictionary of MSX error codes and meanings.
See :class:`MsxErrorEnum` for the list of error codes and their meanings.

:meta hide-value:
"""


@add_get(prefix="ERR_")
class MsxErrorEnum(IntEnum):
    """The EPANET-MSX input and toolkit error numbers, keys, and descriptions.
    """

    MAX_CHARS = 401
    "too many characters"
    NUM_ITEMS = 402
    "too few input items"
    INVALID_KEYWORD = 403
    "invalid keyword"
    INVALID_NUMBER = 404
    "invalid numeric value"
    UNDEFINED_OBJECT_TYPE = 405
    "reference to undefined object"
    RESERVED_NAME = 406
    "illegal use of reserved name"
    NAME = 407
    "name already used by another object"
    SPECIES_EXPR = 408
    "species already assigned an expression"
    ILLEGAL_MATH_EXPR = 409
    "illegal math expression"
    DEPRECATED = 410
    "option no longer supported"
    CYCLIC_REFERENCE = 411
    "term contains a cyclic reference"
    MEMORY = 501
    "insufficient memory available"
    NO_EPANET_FILE = 502
    "no EPANET data file supplied"
    OPEN_MSX_FILE = 503
    "could not open MSX input file"
    OPEN_HYD_FILE = 504
    "could not open hydraulic results file"
    READ_HYD_FILE = 505
    "could not read hydraulic results file"
    MSX_INPUT = 506
    "could not read MSX input file"
    NUM_PIPE_EXPR = 507
    "too few pipe reaction expressions"
    NUM_TANK_EXPR = 508
    "too few tank reaction expressions"
    INTEGRATOR_OPEN = 509
    """could not open differential equation solver"""
    NEWTON_OPEN = 510
    "could not open algebraic equation solver"
    OPEN_OUT_FILE = 511
    """could not open binary results file"""
    IO_OUT_FILE = 512
    """read/write error on binary results file"""
    INTEGRATION = 513
    """could not integrate reaction rate expressions"""
    NEWTON = 514
    """could not solve reaction equilibrium expressions"""
    INVALID_OBJECT_TYPE = 515
    """reference made to an unknown type of object"""
    INVALID_OBJECT_INDEX = 516
    """reference made to an illegal object index"""
    UNDEFINED_OBJECT_ID = 517
    """reference made to an undefined object ID"""
    INVALID_OBJECT_PARAMS = 518
    """invalid property values were specified"""
    MSX_NOT_OPENED = 519
    """an MSX project was not opened"""
    MSX_OPENED = 520
    """an MSX project is already opened"""
    COMPILE_FAILED = 522
    """could not compile chemistry functions"""
    COMPLED_LOAD = 523
    """could not load functions from compiled chemistry file"""
    ILLEGAL_MATH = 524
    """illegal math operation"""


class EpanetMsxException(EpanetException):
    def __init__(self, code: int, *args: List[object], line_num=None, line=None) -> None:
        """An Exception class for EPANET-MSX Toolkit and IO exceptions.

        Parameters
        ----------
        code : int or str or MSXErrors
            The EPANET-MSX error code (int) or a string mapping to the MSXErrors enum members
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these will be used to
            replace the format, otherwise they will be output at the end of the Exception message.
        line_num : int, optional
            The line number, if reading an INP file, by default None
        line : str, optional
            The contents of the line, by default None
        """
        try:
            code = MsxErrorEnum.get(code)
        except:
            return super().__init__(code, *args, line_num=line_num, line=line)
        if int(code) < 400:
            return super().__init__(code, *args, line_num=line_num, line=line)
        msg = MSX_ERROR_CODES.get(code, "unknown error")
        if args is not None:
            args = [*args]
        if r"%" in msg and len(args) > 0:
            msg = msg % args.pop(0)
        if len(args) > 0:
            msg = msg + " " + str(args)
        if line_num:
            msg = msg + ", at line {}".format(line_num)
        if line:
            msg = msg + ":\n   " + str(line)
        msg = "(Error {}) ".format(code) + msg
        super(Exception, self).__init__(msg)


class MSXSyntaxError(EpanetMsxException, SyntaxError):
    def __init__(self, code, *args, line_num=None, line=None) -> None:
        """An MSX-specific error that is due to a syntax error in an msx-file.

        Parameters
        ----------
        code : int or str or MSXErrors
            The EPANET-MSX error code (int) or a string mapping to the MSXErrors enum members
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these will be used to
            replace the format, otherwise they will be output at the end of the Exception message.
        line_num : int, optional
            The line number, if reading an INP file, by default None
        line : str, optional
            The contents of the line, by default None
        """
        super().__init__(code, *args, line_num=line_num, line=line)


class MSXKeyError(EpanetMsxException, KeyError):
    def __init__(self, code, name, *args, line_num=None, line=None) -> None:
        """An MSX-specific error that is due to a missing or unacceptably named variable/speces/etc.

        Parameters
        ----------
        code : int or str or MSXErrors
            The EPANET-MSX error code (int) or a string mapping to the MSXErrors enum members
        name : str
            The key/name/id that is missing
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these will be used to
            replace the format, otherwise they will be output at the end of the Exception message.
        line_num : int, optional
            The line number, if reading an INP file, by default None
        line : str, optional
            The contents of the line, by default None
        """
        super().__init__(code, name, *args, line_num=line_num, line=line)


class MSXValueError(EpanetMsxException, ValueError):
    def __init__(self, code, value, *args, line_num=None, line=None) -> None:
        """An MSX-specific error that is related to an invalid value.

        Parameters
        ----------
        code : int or str or MSXErrors
            The EPANET-MSX error code (int) or a string mapping to the MSXErrors enum members
        value : Any
            The value that is invalid
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these will be used to
            replace the format, otherwise they will be output at the end of the Exception message.
        line_num : int, optional
            The line number, if reading an INP file, by default None
        line : str, optional
            The contents of the line, by default None
        """

        super().__init__(code, value, *args, line_num=line_num, line=line)
