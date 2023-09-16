# coding: utf-8
"""Exceptions for EPANET toolkit and IO operations."""

from enum import IntEnum
from typing import List

EN_ERROR_CODES = {
    # Runtime errors
    1: "At %s, system hydraulically unbalanced - convergence to a hydraulic solution was not achieved in the allowed number of trials",
    2: "At %s, system may be hydraulically unstable - hydraulic convergence was only achieved after the status of all links was held fixed",
    3: "At %s, system disconnected - one or more nodes with positive demands were disconnected for all supply sources",
    4: "At %s, pumps cannot deliver enough flow or head - one or more pumps were forced to either shut down (due to insufficient head) or operate beyond the maximum rated flow",
    5: "At %s, vavles cannot deliver enough flow - one or more flow control valves could not deliver the required flow even when fully open",
    6: "At %s, system has negative pressures - negative pressures occurred at one or more junctions with positive demand",
    101: "insufficient memory available",
    102: "no network data available",
    103: "hydraulics not initialized",
    104: "no hydraulics for water quality analysis",
    105: "water quality not initialized",
    106: "no results saved to report on",
    107: "hydraulics supplied from external file",
    108: "cannot use external file while hydraulics solver is active",
    109: "cannot change time parameter when solver is active",
    110: "cannot solve network hydraulic equations",
    120: "cannot solve water quality transport equations",
    # Apply only to an input file
    200: "one or more errors in input file %s",
    201: "syntax error (%s)",
    # Apply to both IO file and API functions
    202: "illegal numeric value, %s",
    203: "undefined node, %s",
    204: "undefined link, %s",
    205: "undefined time pattern, %s",
    206: "undefined curve, %s",
    207: "attempt to control a CV/GPV link",
    208: "illegal PDA pressure limits",
    209: "illegal node property value",
    211: "illegal link property value",
    212: "undefined trace node",
    213: "invalid option value %s",
    214: "too many characters in input line",
    215: "duplicate ID label",
    216: "reference to undefined pump",
    217: "pump has no head curve or power defined",
    219: "illegal valve connection to tank node",
    220: "illegal valve connection to another valve",
    221: "misplaced rule clause in rule-based control",
    222: "link assigned same start and end nodes",
    # Network consistency
    223: "not enough nodes in network",
    224: "no tanks or reservoirs in network",
    225: "invalid lower/upper levels for tank",
    226: "no head curve or power rating for pump",
    227: "invalid head curve for pump",
    230: "nonincreasing x-values for curve",
    233: "network has unconnected node",
    234: "network has an unconnected node with ID %s",
    # API functions only
    240: "nonexistent water quality source",
    241: "nonexistent control",
    250: "invalid format (e.g. too long an ID name)",
    251: "invalid parameter code",
    252: "invalid ID name",
    253: "nonexistent demand category",
    254: "node with no coordinates",
    255: "invalid link vertex",
    257: "nonexistent rule",
    258: "nonexistent rule clause",
    259: "attempt to delete a node that still has links connected to it",
    260: "attempt to delete node assigned as a Trace Node",
    261: "attempt to delete a node or link contained in a control",
    262: "attempt to modify network structure while a solver is open",
    263: "node is not a tank",
    # File errors
    301: "identical file names used for different types of files",
    302: "cannot open input file %s",
    303: "cannot open report file %s",
    304: "cannot open binary output file %s",
    305: "cannot open hydraulics file %s",
    306: "hydraulics file does not match network data",
    307: "cannot read hydraulics file %s",
    308: "cannot save results to binary file %s",
    309: "cannot save results to report file %s",
}
"""A dictionary of the error codes and their meanings from the EPANET toolkit.
See :class:`EpanetErrors` for the documentation of each code number.

:meta hide-value:
"""

class EpanetErrorEnum(IntEnum):
    """A list of short phrases that can be used in place of the error code numbers."""
    warn_unbalanced = 1
    """system hydraulically unbalanced - convergence to a hydraulic solution was not achieved in the allowed number of trials"""
    warn_unstable = 2
    """system may be hydraulically unstable - hydraulic convergence was only achieved after the status of all links was held fixed"""
    warn_disconnected = 3
    """system disconnected - one or more nodes with positive demands were disconnected for all supply sources"""
    warn_pumps = 4
    """pumps cannot deliver enough flow or head - one or more pumps were forced to either shut down (due to insufficient head) or operate beyond the maximum rated flow"""
    warn_valves = 5
    """vavles cannot deliver enough flow - one or more flow control valves could not deliver the required flow even when fully open"""
    warn_pressures = 6
    """system has negative pressures - negative pressures occurred at one or more junctions with positive demand"""
    insufficient_memory = 101
    """insufficient memory available"""
    no_network = 102
    """no network data available"""
    no_init_hyd = 103
    """hydraulics not initialized"""
    no_hydraulics = 104
    """no hydraulics for water quality analysis"""
    no_init_qual = 105
    """water quality not initialized"""
    no_results = 106
    """no results saved to report on"""
    hyd_file = 107
    """hydraulics supplied from external file"""
    hyd_init_and_hyd_file = 108
    """cannot use external file while hydraulics solver is active"""
    modify_time_during_solve = 109
    """cannot change time parameter when solver is active"""
    solve_hyd_fail = 110
    """cannot solve network hydraulic equations"""
    solve_qual_fail = 120
    """cannot solve water quality transport equations"""
    input_file_error = 200
    """one or more errors in input file"""
    syntax_error = 201
    """syntax error"""
    illegal_numeric_value = 202
    """illegal numeric value"""
    undefined_node = 203
    """undefined node"""
    undefined_link = 204
    """undefined link"""
    undefined_pattern = 205
    """undefined time pattern"""
    undefined_curve = 206
    """undefined curve"""
    control_on_cv_gpv = 207
    """attempt to control a CV/GPV link"""
    illegal_pda_limits = 208
    """illegal PDA pressure limits"""
    illegal_node_property = 209
    """illegal node property value"""
    illegal_link_property = 211
    """illegal link property value"""
    undefined_trace_node = 212
    """undefined trace node"""
    invalid_option_value = 213
    """invalid option value"""
    too_many_chars_inp = 214
    """too many characters in input line"""
    duplicate_id = 215
    """duplicate ID label"""
    undefined_pump = 216
    """reference to undefined pump"""
    invalid_energy_value = 217
    """pump has no head curve or power defined"""
    illegal_valve_tank = 219
    """illegal valve connection to tank node"""
    illegal_tank_valve = 219
    """illegal valve connection to tank node"""
    illegal_valve_valve = 220
    """illegal valve connection to another valve"""
    misplaced_rule = 221
    """misplaced rule clause in rule-based control"""
    link_to_self = 222
    """link assigned same start and end nodes"""
    not_enough_nodes = 223
    """not enough nodes in network"""
    no_tanks_or_res = 224
    """no tanks or reservoirs in network"""
    invalid_tank_levels = 225
    """invalid lower/upper levels for tank"""
    missing_pump_data = 226
    """no head curve or power rating for pump"""
    invalid_head_curve = 227
    """invalid head curve for pump"""
    nonincreasing_x_curve = 230
    """nonincreasing x-values for curve"""
    unconnected_node = 233
    """network has unconnected node"""
    unconnected_node_id = 234
    """network has an unconnected node with ID"""
    no_such_source_node = 240
    """nonexistent water quality source"""
    no_such_control = 241
    """nonexistent control"""
    invalid_name_format = 250
    """invalid format (e.g. too long an ID name)"""
    invalid_parameter_code = 251
    """invalid parameter code"""
    invalid_id_name = 252
    """invalid ID name"""
    no_such_demand_category = 253
    """nonexistent demand category"""
    missing_coords = 254
    """node with no coordinates"""
    invalid_vertex = 255
    """invalid link vertex"""
    no_such_rule = 257
    """nonexistent rule"""
    no_such_rule_clause = 258
    """nonexistent rule clause"""
    delete_node_still_linked = 259
    """attempt to delete a node that still has links connected to it"""
    delete_node_is_trace = 260
    """attempt to delete node assigned as a Trace Node"""
    delete_node_in_control = 261
    """attempt to delete a node or link contained in a control"""
    modify_network_during_solve = 262
    """attempt to modify network structure while a solver is open"""
    node_not_a_tank = 263
    """node is not a tank"""
    same_file_names = 301
    """identical file names used for different types of files"""
    open_inp_fail = 302
    """cannot open input file"""
    open_rpt_fail = 303
    """cannot open report file"""
    open_bin_fail = 304
    """cannot open binary output file"""
    open_hyd_fail = 305
    """cannot open hydraulics file"""
    hyd_file_different_network = 306
    """hydraulics file does not match network data"""
    read_hyd_fail = 307
    """cannot read hydraulics file"""
    save_bin_fail = 308
    """cannot save results to binary file"""
    save_rpt_fail = 309
    """cannot save results to report file"""


class EpanetException(Exception):

    def __init__(self, code: int, *args: List[object], line_num=None, line=None) -> None:
        """An Exception class for EPANET Toolkit and IO exceptions.

        Parameters
        ----------
        code : int or str or EpanetErrors
            The EPANET error code (int) or a string mapping to the EpanetErrors enum members
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these will be used to 
            replace the format, otherwise they will be output at the end of the Exception message.
        line_num : int, optional
            The line number, if reading an INP file, by default None
        line : str, optional
            The contents of the line, by default None
        """
        if isinstance(code, EpanetErrorEnum):
            code = int(code)
        elif isinstance(code, str):
            try:
                code = code.strip().replace('-','_').replace(' ','_')
                code = int(EpanetErrorEnum[code])
            except KeyError:
                return super().__init__('unknown error code: {}'.format(repr(code)), *args)
        elif not isinstance(code, int):
            return super().__init__('unknown error code: {}'.format(repr(code)), *args)
        msg = EN_ERROR_CODES.get(code, 'unknown error')
        if args is not None:
            args = [*args]
        if r'%' in msg and len(args) > 0:
            msg = msg % repr(args.pop(0))
        if len(args) > 0:
            msg = msg + ' ' + repr(args)
        if line_num:
            msg = msg + ", at line {}".format(line_num)
        if line:
            msg = msg + ':\n   ' + str(line)
        msg = '(Error {}) '.format(code) + msg
        super().__init__(msg)

class ENSyntaxError(EpanetException, SyntaxError):
    def __init__(self, code, *args, line_num=None, line=None) -> None:
        """An EPANET exception class that also subclasses SyntaxError

        Parameters
        ----------
        code : int or str or EpanetErrors
            The EPANET error code (int) or a string mapping to the EpanetErrors enum members
        args : additional non-keyword arguments, optional
            If there is a string-format within the error code's text, these will be used to 
            replace the format, otherwise they will be output at the end of the Exception message.
        line_num : int, optional
            The line number, if reading an INP file, by default None
        line : str, optional
            The contents of the line, by default None
        """
        super().__init__(code, *args, line_num=line_num, line=line)

class ENKeyError(EpanetException, KeyError):
    def __init__(self, code, name, *args, line_num=None, line=None) -> None:
        """An EPANET exception class that also subclasses KeyError.

        Parameters
        ----------
        code : int or str or EpanetErrors
            The EPANET error code (int) or a string mapping to the EpanetErrors enum members
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

class ENValueError(EpanetException, ValueError):
    def __init__(self, code, value, *args, line_num=None, line=None) -> None:
        """An EPANET exception class that also subclasses ValueError

        Parameters
        ----------
        code : int or str or EpanetErrors
            The EPANET error code (int) or a string mapping to the EpanetErrors enum members
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
