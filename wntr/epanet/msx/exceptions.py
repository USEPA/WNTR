# coding: utf-8
"""EPANET-MSX error and exception classes."""

from enum import IntEnum
from typing import List
from ..exceptions import EpanetException, EN_ERROR_CODES, EpanetErrorEnum


MSX_ERROR_CODES = EN_ERROR_CODES.copy()
MSX_ERROR_CODES.update(
    {
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
)


class MSXErrors(IntEnum):
    too_many_chars_msx = 401
    too_few_items = 402
    invalid_keyword = 403
    invalid_numeric_value_msx = 404
    undefined_msx_object = 405
    illegal_reserved_name = 406
    name_in_use = 407
    species_already_assigned = 408
    illegal_math_expression = 409
    option_deprecated = 410
    cyclic_reference = 411
    insufficient_memory_msx = 501
    no_epanet_datafile = 502
    open_msx_fail = 503
    open_hyd_fail_msx = 504
    read_hyd_fail_msx = 505
    read_msx_fail = 506
    not_enough_pipe_reactions = 507
    not_enough_tank_reactions = 508
    open_de_solver_fail = 509
    open_ae_solver_fail = 510
    open_bin_fail_msx = 511
    io_error_msx_bin = 512
    solve_rate_failed = 513
    solve_equil_failed = 514
    unknown_object_type = 515
    illegal_object_index = 516
    undefined_object_id = 517
    invalid_property_value = 518
    msx_project_not_open = 519
    msx_project_open = 520
    compile_chem_failed = 522
    load_compiled_chem_failed = 523
    illegal_math_operation = 524
    insufficient_memory = 101
    no_network = 102
    no_init_hyd = 103
    no_hydraulics = 104
    no_init_qual = 105
    no_results = 106
    hyd_file = 107
    hyd_init_and_hyd_file = 108
    modify_time_during_solve = 109
    solve_hyd_fail = 110
    solve_qual_fail = 120
    input_file_error = 200
    syntax_error = 201
    illegal_numeric_value = 202
    undefined_node = 203
    undefined_link = 204
    undefined_pattern = 205
    undefined_curve = 206
    control_on_cv_gpv = 207
    illegal_pda_limits = 208
    illegal_node_property = 209
    illegal_link_property = 211
    undefined_trace_node = 212
    invalid_option_value = 213
    too_many_chars_inp = 214
    duplicate_id = 215
    undefined_pump = 216
    invalid_energy_value = 217
    illegal_valve_tank = 219
    illegal_tank_valve = 219
    illegal_valve_valve = 220
    misplaced_rule = 221
    link_to_self = 222
    not_enough_nodes = 223
    no_tanks_or_res = 224
    invalid_tank_levels = 225
    missing_pump_data = 226
    invalid_head_curve = 227
    nonincreasing_x_curve = 230
    unconnected_node = 233
    unconnected_node_id = 234
    no_such_source_node = 240
    no_such_control = 241
    invalid_name_format = 250
    invalid_parameter_code = 251
    invalid_id_name = 252
    no_such_demand_category = 253
    missing_coords = 254
    invalid_vertex = 255
    no_such_rule = 257
    no_such_rule_clause = 258
    delete_node_still_linked = 259
    delete_node_is_trace = 260
    delete_node_in_control = 261
    modify_network_during_solve = 262
    node_not_a_tank = 263
    same_file_names = 301
    open_inp_fail = 302
    open_rpt_fail = 303
    open_bin_fail = 304
    open_hyd_fail = 305
    hyd_file_different_network = 306
    read_hyd_fail = 307
    save_bin_fail = 308
    save_rpt_fail = 309


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
        if isinstance(code, (EpanetErrorEnum, MSXErrors)):
            code = int(code)
        elif isinstance(code, str):
            try:
                code = code.strip().replace("-", "_").replace(" ", "_")
                code = int(MSXErrors[code])
            except KeyError:
                return super(Exception, self).__init__("unknown error code: {}".format(repr(code)), *args)
        elif not isinstance(code, int):
            return super(Exception, self).__init__("unknown error code: {}".format(repr(code)), *args)
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
