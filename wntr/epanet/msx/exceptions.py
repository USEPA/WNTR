# coding: utf-8
"""
The wntr.epanet.msx.exceptions module contains Exceptions for EPANET-MSX
IO operations.
"""

from typing import List

from ..exceptions import EpanetException

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
"""A dictionary of the error codes and their meanings from the EPANET-MSX toolkit.

:meta hide-value:
"""


class EpanetMsxException(EpanetException):
    def __init__(self, code: int, *args: List[object], line_num=None,
                 line=None) -> None:
        """Exception class for EPANET-MSX Toolkit and IO exceptions

        Parameters
        ----------
        code : int or str or MSXErrors
            EPANET-MSX error code (int) or a string mapping to the MSXErrors
            enum members
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these
            will be used to replace the format, otherwise they will be output
            at the end of the Exception message.
        line_num : int, optional
            Line number, if reading an INP file, by default None
        line : str, optional
            Contents of the line, by default None
        """
        if not code or int(code) < 400:
            return super().__init__(code, *args, line_num=line_num, line=line)
        msg = MSX_ERROR_CODES.get(code, "unknown MSX error number {}".format(code))
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
        """MSX-specific error that is due to a syntax error in an msx-file.

        Parameters
        ----------
        code : int or str or MSXErrors
            EPANET-MSX error code (int) or a string mapping to the MSXErrors
            enum members
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these
            will be used to replace the format, otherwise they will be output
            at the end of the Exception message.
        line_num : int, optional
            Line number, if reading an INP file, by default None
        line : str, optional
            Contents of the line, by default None
        """
        super().__init__(code, *args, line_num=line_num, line=line)


class MSXKeyError(EpanetMsxException, KeyError):
    def __init__(self, code, name, *args, line_num=None, line=None) -> None:
        """MSX-specific error that is due to a missing or unacceptably named
        variable/speces/etc.

        Parameters
        ----------
        code : int or str or MSXErrors
            EPANET-MSX error code (int) or a string mapping to the MSXErrors
            enum members
        name : str
            Key/name/id that is missing
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these
            will be used to replace the format, otherwise they will be output
            at the end of the Exception message.
        line_num : int, optional
            Line number, if reading an INP file, by default None
        line : str, optional
            Contents of the line, by default None
        """
        super().__init__(code, name, *args, line_num=line_num, line=line)


class MSXValueError(EpanetMsxException, ValueError):
    def __init__(self, code, value, *args, line_num=None, line=None) -> None:
        """MSX-specific error that is related to an invalid value.

        Parameters
        ----------
        code : int or str or MSXErrors
            EPANET-MSX error code (int) or a string mapping to the MSXErrors
            enum members
        value : Any
            Value that is invalid
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these
            will be used to replace the format, otherwise they will be output
            at the end of the Exception message.
        line_num : int, optional
            Line number, if reading an INP file, by default None
        line : str, optional
            Contents of the line, by default None
        """

        super().__init__(code, value, *args, line_num=line_num, line=line)
