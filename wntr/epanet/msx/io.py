# coding: utf-8
"""
The wntr.epanet.msx io module contains methods for reading/writing EPANET
MSX input and output files.
"""

import datetime
import logging
import sys
from typing import Union

import numpy as np
import pandas as pd
from wntr.msx.elements import Constant, Parameter, Species, Term

import wntr.network
from wntr.epanet.msx.exceptions import EpanetMsxException, MSXValueError
from wntr.epanet.util import ENcomment
from wntr.msx.base import VariableType, SpeciesType
from wntr.msx.model import MsxModel

sys_default_enc = sys.getdefaultencoding()

logger = logging.getLogger(__name__)

MAX_LINE = 1024

_INP_SECTIONS = [
    "[TITLE]",
    "[OPTIONS]",
    "[SPECIES]",
    "[COEFFICIENTS]",
    "[TERMS]",
    "[PIPES]",
    "[TANKS]",
    "[SOURCES]",
    "[QUALITY]",
    "[PARAMETERS]",
    "[DIFFUSIVITY]",
    "[PATTERNS]",
    "[REPORT]",
]


def _split_line(line):
    _vc = line.split(";", 1)
    _cmnt = None
    _vals = None
    if len(_vc) == 0:
        pass
    elif len(_vc) == 1:
        _vals = _vc[0].split()
    elif _vc[0] == "":
        _cmnt = _vc[1].strip()
    else:
        _vals = _vc[0].split()
        _cmnt = _vc[1].strip()
    return _vals, _cmnt


class MsxFile(object):
    """An EPANET-MSX input file reader.

    .. rubric:: Class Methods
    .. autosummary::
        :nosignatures:

        read
        write

    """

    def __init__(self):
        self.rxn: MsxModel = None
        self.sections = dict()
        for sec in _INP_SECTIONS:
            self.sections[sec] = []
        self.top_comments = []
        self.patterns = dict()

    @classmethod
    def read(cls, msx_filename: str, rxn_model: MsxModel = None):
        """
        Read an EPANET-MSX input file (.msx) and load data into a MsxModel.
        Only MSX 2.0 files are recognized.

        Parameters
        ----------
        msx_file : str
            Filename of the .msx file to read in
        rxn_model : MsxModel, optional
            Multi-species water quality model to put data into,
            by default None (new model)

        Returns
        -------
        MsxModel
            Multi-species water quality model with the new species, reactions
            and other options added
        """
        if rxn_model is None:
            rxn_model = MsxModel()
        obj = cls()
        obj.rxn = rxn_model
        # if not isinstance(msx_file, list):
        #     msx_file = [msx_file]
        rxn_model._orig_file = msx_filename

        obj.patterns = dict()
        obj.top_comments = []
        obj.sections = dict()
        for sec in _INP_SECTIONS:
            obj.sections[sec] = []

        def _read():
            section = None
            lnum = 0
            edata = {"fname": msx_filename}
            with open(msx_filename, "r", encoding=sys_default_enc) as f:
                for line in f:
                    lnum += 1
                    edata["lnum"] = lnum
                    line = line.strip()
                    nwords = len(line.split())
                    if len(line) == 0 or nwords == 0:
                        # Blank line
                        continue
                    elif line.startswith("["):
                        vals = line.split(None, 1)
                        sec = vals[0].upper()
                        # Add handlers to deal with extra 'S'es (or missing 'S'es) in INP file
                        if sec not in _INP_SECTIONS:
                            trsec = sec.replace("]", "S]")
                            if trsec in _INP_SECTIONS:
                                sec = trsec
                        if sec not in _INP_SECTIONS:
                            trsec = sec.replace("S]", "]")
                            if trsec in _INP_SECTIONS:
                                sec = trsec
                        edata["sec"] = sec
                        if sec in _INP_SECTIONS:
                            section = sec
                            # logger.info('%(fname)s:%(lnum)-6d %(sec)13s section found' % edata)
                            continue
                        # elif sec == "[END]":
                        #     # logger.info('%(fname)s:%(lnum)-6d %(sec)13s end of file found' % edata)
                        #     section = None
                        #     break
                        else:
                            logger.warning('%(fname)s:%(lnum)d: Invalid section "%(sec)s"' % edata)
                            raise EpanetMsxException(201, note="at line {}:\n{}".format(lnum, line))
                    elif section is None and line.startswith(";"):
                        obj.top_comments.append(line[1:])
                        continue
                    elif section is None:
                        logger.debug("Found confusing line: %s", repr(line))
                        raise EpanetMsxException(201, note="at line {}:\n{}".format(lnum, line))
                    # We have text, and we are in a section
                    obj.sections[section].append((lnum, line))

        try:
            _read()
            obj._read_title()
            obj._read_options()
            obj._read_species()
            obj._read_coefficients()
            obj._read_terms()
            obj._read_pipes()
            obj._read_tanks()
            obj._read_source_dict()
            obj._read_quality()
            obj._read_parameters()
            obj._read_diffusivity()
            obj._read_patterns()
            obj._read_report()
            return obj.rxn
        except Exception as e:
            raise EpanetMsxException(200) from e

    @classmethod
    def write(cls, filename: str, msx: MsxModel):
        """Write an MSX input file.

        Parameters
        ----------
        filename : str
            Filename to write
        rxn : MsxModel
            Multi-species water quality model
        """
        obj = cls()
        obj.rxn = msx
        with open(filename, "w") as fout:
            fout.write("; WNTR-reactions MSX file generated {}\n".format(datetime.datetime.now()))
            fout.write("\n")
            obj._write_title(fout)
            obj._write_options(fout)
            obj._write_species(fout)
            obj._write_coefficients(fout)
            obj._write_terms(fout)
            obj._write_pipes(fout)
            obj._write_tanks(fout)
            obj._write_diffusivity(fout)
            obj._write_parameters(fout)
            obj._write_patterns(fout)
            obj._write_report(fout)
            obj._write_quality(fout)
            obj._write_source_dict(fout)

    def _read_title(self):
        lines = []
        title = None
        comments = ""
        for lnum, line in self.sections["[TITLE]"]:
            vals, comment = _split_line(line)
            if title is None and vals is not None:
                title = " ".join(vals)
            if comment:
                lines.append(comment.strip())
        if self.top_comments:
            comments = "\n".join(self.top_comments)
        if len(lines) > 0:
            comments = comments + ("\n" if comments else "") + "\n".join(lines)
        self.rxn.title = title
        self.rxn.description = comments

    def _read_options(self):
        for lnum, line in self.sections["[OPTIONS]"]:
            vals, comment = _split_line(line)
            try:
                if len(vals) < 2:
                    raise EpanetMsxException(402, note="at line {} of [OPTIONS] section:\n{}".format(lnum, line))
                name, val = vals[0].upper(), vals[1].upper()
                if name == "AREA_UNITS":
                    self.rxn._options.area_units = val
                elif name == "RATE_UNITS":
                    self.rxn._options.rate_units = val
                elif name == "SOLVER":
                    self.rxn._options.solver = val
                elif name == "COUPLING":
                    self.rxn._options.coupling = val
                elif name == "TIMESTEP":
                    self.rxn._options.timestep = int(val)
                elif name == "ATOL":
                    self.rxn._options.atol = float(val)
                elif name == "RTOL":
                    self.rxn._options.rtol = float(val)
                elif name == "COMPILER":
                    self.rxn._options.compiler = val
                elif name == "SEGMENTS":
                    self.rxn._options.segments = int(val)
                elif name == "PECLET":
                    self.rxn._options.peclet = int(val)
                else:
                    raise EpanetMsxException(403, note="at line {} of [OPTIONS] section:\n{}".format(lnum, line))
            except ValueError:
                raise EpanetMsxException(404, note="at line {} of [OPTIONS] section:\n{}".format(lnum, line))
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [OPTIONS] section:\n{}".format(lnum, line)) from e

    def _read_species(self):
        note = ENcomment()
        for lnum, line in self.sections["[SPECIES]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) < 3:
                    raise EpanetMsxException(402, note="at line {} of [SPECIES] section:\n{}".format(lnum, line))
                try:
                    typ = SpeciesType.get(vals[0], allow_none=False)
                except ValueError as e:
                    raise MSXValueError(403, vals[0], note="at line {} of [SPECIES] section:\n{}".format(lnum, line)) from e
                if len(vals) == 3:
                    self.rxn.add_species(vals[1], typ, vals[2], note=note)
                elif len(vals) == 5:
                    self.rxn.add_species(vals[1], typ, vals[2], float(vals[3]), float(vals[4]), note=note)
                else:
                    raise EpanetMsxException(201, note="at line {} of [SPECIES] section:\n{}".format(lnum, line))
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [SPECIES] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_coefficients(self):
        note = ENcomment()
        for lnum, line in self.sections["[COEFFICIENTS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) < 3:
                    raise EpanetMsxException(402, note="at line {} of [COEFFICIENTS] section:\n{}".format(lnum, line))
                typ = VariableType.get(vals[0], allow_none=False)
                if typ is VariableType.CONSTANT:
                    self.rxn.add_constant(vals[1], float(vals[2]), note=note)
                elif typ is VariableType.PARAMETER:
                    self.rxn.add_parameter(vals[1], float(vals[2]), note=note)
                else:
                    raise MSXValueError(403, vals[0], note="at line {} of [COEFFICIENTS] section:\n{}".format(lnum, line))
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [COEFFICIENTS] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_terms(self):
        note = ENcomment()
        for lnum, line in self.sections["[TERMS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) < 2:
                    raise SyntaxError("Invalid [TERMS] entry")
                self.rxn.add_term(vals[0], " ".join(vals[1:]), note=note)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [TERMS] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_pipes(self):
        note = ENcomment()
        for lnum, line in self.sections["[PIPES]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) < 3:
                    raise SyntaxError("Invalid [PIPES] entry")
                reaction = self.rxn.add_reaction(vals[1], "pipe", vals[0], " ".join(vals[2:]), note=note)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [PIPES] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_tanks(self):
        note = ENcomment()
        for lnum, line in self.sections["[TANKS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) < 3:
                    raise SyntaxError("Invalid [TANKS] entry")
                self.rxn.add_reaction(vals[1], "tank", vals[0], " ".join(vals[2:]), note=note)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [TANKS] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_source_dict(self):
        note = ENcomment()
        for lnum, line in self.sections["[SOURCES]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) == 4:
                    typ, node, spec, strength = vals
                    pat = None
                else:
                    typ, node, spec, strength, pat = vals
                if spec not in self.rxn.reaction_system:
                    raise ValueError("Undefined species in [SOURCES] section: {}".format(spec))
                if spec not in self.rxn.network_data.sources.keys():
                    self.rxn.network_data.sources[spec] = dict()
                source = dict(source_type=typ, strength=strength, pattern=pat, note=note)
                self.rxn.network_data.sources[spec][node] = source
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [SOURCES] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_quality(self):
        note = ENcomment()
        for lnum, line in self.sections["[QUALITY]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) == 4:
                    cmd, netid, spec, concen = vals
                else:
                    cmd, spec, concen = vals
                if cmd[0].lower() not in ["g", "n", "l"]:
                    raise SyntaxError("Unknown first word in [QUALITY] section")
                if spec not in self.rxn.reaction_system.species:
                    raise ValueError("Undefined species in [QUALITY] section: {}".format(spec))
                # FIXME: check for existence
                # if spec not in self.rxn.net.initial_quality:
                #     self.rxn.net.new_quality_values(spec)
                #     self.rxn._inital_qual_dict[spec]["global"] = None
                #     self.rxn._inital_qual_dict[spec]["nodes"] = dict()
                #     self.rxn._inital_qual_dict[spec]["links"] = dict()
                if cmd[0].lower() == "g":
                    self.rxn.network_data.initial_quality[spec].global_value = float(concen)
                elif cmd[0].lower() == "n":
                    self.rxn.network_data.initial_quality[spec].node_values[netid] = float(concen)
                elif cmd[1].lower() == "l":
                    self.rxn.network_data.initial_quality[spec].link_values[netid] = float(concen)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [QUALITY] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_parameters(self):
        note = ENcomment()
        for lnum, line in self.sections["[PARAMETERS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                typ, netid, paramid, value = vals
                if paramid not in self.rxn.reaction_system.parameters:
                    raise ValueError("Invalid parameter {}".format(paramid))
                value = float(value)
                if typ.lower()[0] == "p":
                    self.rxn.network_data.parameter_values[paramid].pipe_values[netid] = value
                elif typ.lower()[0] == "t":
                    self.rxn.network_data.parameter_values[paramid].tank_values[netid] = value
                else:
                    raise ValueError("Invalid parameter type {}".format(typ))
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [PARAMETERS] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_diffusivity(self):
        note = ENcomment()
        for lnum, line in self.sections["[DIFFUSIVITY]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) != 2:
                    raise SyntaxError("Invalid [DIFFUSIVITIES] entry")
                species = self.rxn.reaction_system.species[vals[0]]
                species.diffusivity = float(vals[1])
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [DIFFUSIVITIES] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_patterns(self):
        _patterns = dict()
        for lnum, line in self.sections["[PATTERNS]"]:
            # read the lines for each pattern -- patterns can be multiple lines of arbitrary length
            line = line.split(";")[0]
            current = line.split()
            if current == []:
                continue
            pattern_name = current[0]
            if pattern_name not in _patterns:
                _patterns[pattern_name] = []
                for i in current[1:]:
                    _patterns[pattern_name].append(float(i))
            else:
                for i in current[1:]:
                    _patterns[pattern_name].append(float(i))
        for pattern_name, pattern in _patterns.items():
            # add the patterns to the water newtork model
            self.rxn.network_data.add_pattern(pattern_name, pattern)

    def _read_report(self):
        note = ENcomment()
        for lnum, line in self.sections["[REPORT]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) == 0:
                    continue
                if len(vals) < 2:
                    raise SyntaxError("Invalid number of arguments in [REPORT] section")
                cmd = vals[0][0].lower()
                if cmd == "n":  # NODES
                    if self.rxn._options.report.nodes is None:
                        if vals[1].upper() == "ALL":
                            self.rxn._options.report.nodes = "ALL"
                        else:
                            self.rxn._options.report.nodes = list()
                            self.rxn._options.report.nodes.extend(vals[1:])
                    elif isinstance(self.rxn._options.report.nodes, list):
                        if vals[1].upper() == "ALL":
                            self.rxn._options.report.nodes = "ALL"
                        else:
                            self.rxn._options.report.nodes.extend(vals[1:])
                elif cmd == "l":  # LINKS
                    if self.rxn._options.report.links is None:
                        if vals[1].upper() == "ALL":
                            self.rxn._options.report.links = "ALL"
                        else:
                            self.rxn._options.report.links = list()
                            self.rxn._options.report.links.extend(vals[1:])
                    elif isinstance(self.rxn._options.report.links, list):
                        if vals[1].upper() == "ALL":
                            self.rxn._options.report.links = "ALL"
                        else:
                            self.rxn._options.report.links.extend(vals[1:])
                elif cmd == "f":
                    self.rxn._options.report.report_filename = vals[1]
                elif cmd == "p":
                    self.rxn._options.report.pagesize = vals[1]
                elif cmd == "s":
                    if vals[1] not in self.rxn.reaction_system.species:
                        raise ValueError("Undefined species in [REPORT] section: {}".format(vals[1]))
                    self.rxn._options.report.species[vals[1]] = True if vals[2].lower().startswith("y") else False
                    if len(vals) == 4:
                        self.rxn._options.report.species_precision[vals[1]] = int(vals[3])
                else:
                    raise SyntaxError("Invalid syntax in [REPORT] section: unknown first word")
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [REPORT] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _write_title(self, fout):
        fout.write("[TITLE]\n")
        fout.write("  {}\n".format(self.rxn.title))
        fout.write("\n")

    def _write_options(self, fout):
        opts = self.rxn._options
        fout.write("[OPTIONS]\n")
        fout.write("  AREA_UNITS  {}\n".format(opts.area_units.upper()))
        fout.write("  RATE_UNITS  {}\n".format(opts.rate_units.upper()))
        fout.write("  SOLVER      {}\n".format(opts.solver.upper()))
        fout.write("  COUPLING    {}\n".format(opts.coupling.upper()))
        fout.write("  TIMESTEP    {}\n".format(opts.timestep))
        fout.write("  ATOL        {}\n".format(opts.atol))
        fout.write("  RTOL        {}\n".format(opts.rtol))
        fout.write("  COMPILER    {}\n".format(opts.compiler.upper()))
        fout.write("  SEGMENTS    {}\n".format(opts.segments))
        fout.write("  PECLET      {}\n".format(opts.peclet))
        fout.write("\n")

    def _write_species(self, fout):
        fout.write("[SPECIES]\n")

        def to_msx_string(spec: Species) -> str:
            tols = spec.get_tolerances()
            if tols is None:
                tolstr = ""
            else:
                tolstr = " {:12.6g} {:12.6g}".format(*tols)
            return "{:<12s} {:<8s} {:<8s}{:s}".format(
                spec.species_type.name.upper(),
                spec.name,
                spec.units,
                tolstr,
            )

        for var in self.rxn.reaction_system.species.values():
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        fout.write("\n")

    def _write_coefficients(self, fout):
        fout.write("[COEFFICIENTS]\n")

        def to_msx_string(coeff: Union[Constant, Parameter]) -> str:
            # if self.units is not None:
            #     post = r' ; {"units"="' + str(self.units) + r'"}'
            # else:
            post = ""
            return "{:<12s} {:<8s} {:<16s}{}".format(
                coeff.var_type.name.upper(),
                coeff.name,
                str(coeff.global_value if isinstance(coeff, Parameter) else coeff.value),
                post,
            )

        for var in self.rxn.reaction_system.constants.values():
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        for var in self.rxn.reaction_system.parameters.values():
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        fout.write("\n")

    def _write_terms(self, fout):
        fout.write("[TERMS]\n")

        def to_msx_string(term: Term) -> str:
            return "{:<8s} {:<64s}".format(term.name, term.expression)

        for var in self.rxn.reaction_system.terms.values():
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        fout.write("\n")

    def _write_pipes(self, fout):
        fout.write("[PIPES]\n")
        for spec in self.rxn.reaction_system.species.values():
            var = spec.pipe_reaction
            if var is None:
                raise MSXValueError(507, note=" species {}".format(str(spec)))
            if isinstance(var.note, ENcomment):
                fout.write(
                    "{}\n".format(
                        var.note.wrap_msx_string(
                            "{:<12s} {:<8s} {:<32s}".format(var.expression_type.name.upper(), str(var.species_name), var.expression)
                        )
                    )
                )
            elif isinstance(var.note, str):
                fout.write(
                    "  {} ; {}\n".format(
                        "{:<12s} {:<8s} {:<32s}".format(var.expression_type.name.upper(), str(var.species_name), var.expression),
                        var.note,
                    )
                )
            else:
                fout.write(
                    "  {}\n".format(
                        "{:<12s} {:<8s} {:<32s}".format(var.expression_type.name.upper(), str(var.species_name), var.expression)
                    )
                )
        fout.write("\n")

    def _write_tanks(self, fout):
        fout.write("[TANKS]\n")
        for spec in self.rxn.reaction_system.species.values():
            if spec.species_type.name == 'WALL':
                continue
            try:
                var = spec.tank_reaction
            except KeyError:
                logger.warn('Species {} does not have a tank reaction - this may be a problem'.format(str(spec)))
                continue
            if var is None:
                raise MSXValueError(508, note=" species {}".format(str(spec)))
            if isinstance(var.note, ENcomment):
                fout.write(
                    "{}\n".format(
                        var.note.wrap_msx_string(
                            "{:<12s} {:<8s} {:<32s}".format(var.expression_type.name.upper(), str(var.species_name), var.expression)
                        )
                    )
                )
            elif isinstance(var.note, str):
                fout.write(
                    "  {} ; {}\n".format(
                        "{:<12s} {:<8s} {:<32s}".format(var.expression_type.name.upper(), str(var.species_name), var.expression),
                        var.note,
                    )
                )
            else:
                fout.write(
                    "  {}\n".format(
                        "{:<12s} {:<8s} {:<32s}".format(var.expression_type.name.upper(), str(var.species_name), var.expression)
                    )
                )
        fout.write("\n")

    def _write_source_dict(self, fout):
        fout.write("[SOURCES]\n")
        for species in self.rxn.network_data.sources.keys():
            for node, src in self.rxn.network_data.sources[species].items():
                if isinstance(src["note"], ENcomment):
                    fout.write(
                        src["note"].wrap_msx_string(
                            "{:<10s} {:<8s} {:<8s} {:12s} {:<12s}".format(
                                src["source_type"],
                                node,
                                species,
                                src["strength"],
                                src["pattern"] if src["pattern"] is not None else "",
                            )
                        )
                    )
                elif isinstance(src["note"], str):
                    fout.write(
                        "  {:<10s} {:<8s} {:<8s} {} {:<12s} ; {}\n".format(
                            src["source_type"],
                            node,
                            species,
                            src["strength"],
                            src["pattern"] if src["pattern"] is not None else "",
                            src["note"],
                        )
                    )
                else:
                    fout.write(
                        "  {:<10s} {:<8s} {:<8s} {} {:<12s}\n".format(
                            src["source_type"],
                            node,
                            species,
                            src["strength"],
                            src["pattern"] if src["pattern"] is not None else "",
                        )
                    )
                if src["note"] is not None:
                    fout.write("\n")
        fout.write("\n")

    def _write_quality(self, fout):
        fout.write("[QUALITY]\n")
        for species, val in self.rxn.network_data.initial_quality.items():
            for typ in ["node_values", "link_values"]:
                for node, conc in getattr(val, typ).items():
                    fout.write("  {:<8s} {:<8s} {:<8s} {}\n".format(typ.upper()[0:4], node, species, conc))
            if val.global_value:
                fout.write("  {:<8s} {:<8s} {}\n".format("GLOBAL", species, val.global_value))
        fout.write("\n")

    def _write_parameters(self, fout):
        fout.write("[PARAMETERS]\n")
        for name, var in self.rxn.network_data.parameter_values.items():
            had_entries = False
            for pipeID, value in var.pipe_values.items():
                fout.write("  PIPE     {:<8s} {:<8s} {}\n".format(pipeID, name, value))
                had_entries = True
            for tankID, value in var.tank_values.items():
                fout.write("  PIPE     {:<8s} {:<8s} {}\n".format(tankID, name, value))
                had_entries = True
            if had_entries:
                fout.write("\n")
        fout.write("\n")

    def _write_patterns(self, fout):
        fout.write("[PATTERNS]\n")
        for pattern_name, pattern in self.rxn.network_data.patterns.items():
            num_columns = 10
            count = 0
            for i in pattern:  # .multipliers:
                if count % num_columns == 0:
                    fout.write("\n  {:<8s} {:g}".format(pattern_name, i))
                else:
                    fout.write("  {:g}".format(i))
                count += 1
            fout.write("\n")
        fout.write("\n")

    def _write_diffusivity(self, fout):
        fout.write("[DIFFUSIVITY]\n")
        for name in self.rxn.species_name_list:
            spec: Species = self.rxn.reaction_system.species[name]
            if spec.diffusivity is not None:
                fout.write("  {:<8s} {}\n".format(name, spec.diffusivity))
        fout.write("\n")

    def _write_report(self, fout):
        fout.write("[REPORT]\n")
        if self.rxn._options.report.nodes is not None:
            if isinstance(self.rxn._options.report.nodes, str):
                fout.write("  NODES     {}\n".format(self.rxn.options.report.nodes))
            else:
                fout.write("  NODES     {}\n".format(" ".join(self.rxn.options.report.nodes)))
        if self.rxn._options.report.links is not None:
            if isinstance(self.rxn._options.report.links, str):
                fout.write("  LINKS     {}\n".format(self.rxn.options.report.links))
            else:
                fout.write("  LINKS     {}\n".format(" ".join(self.rxn.options.report.links)))
        for spec, val in self.rxn._options.report.species.items():
            fout.write(
                "  SPECIES   {:<8s} {:<3s} {}\n".format(
                    spec,
                    "YES" if val else "NO",
                    self.rxn._options.report.species_precision[spec]
                    if spec in self.rxn._options.report.species_precision.keys()
                    else "",
                )
            )
        if self.rxn._options.report.report_filename:
            fout.write("  FILE      {}\n".format(self.rxn._options.report.report_filename))
        if self.rxn._options.report.pagesize:
            fout.write("  PAGESIZE  {}\n".format(self.rxn._options.report.pagesize))
        fout.write("\n")


def MsxBinFile(filename, wn, res = None):
    duration = int(wn.options.time.duration)
    if res is None:
        from wntr.sim.results import SimulationResults
        res = SimulationResults()
    with open(filename, "rb") as fin:
        ftype = "=f4"
        idlen = 32
        prolog = np.fromfile(fin, dtype=np.int32, count=6)
        magic1 = prolog[0]
        version = prolog[1]
        nnodes = prolog[2]
        nlinks = prolog[3]
        nspecies = prolog[4]
        reportstep = prolog[5]
        species_list = []
        node_list = wn.node_name_list
        link_list = wn.link_name_list
        # print(magic1, version, nnodes, nlinks, nspecies, reportstep)

        species_mass = []
        for i in range(nspecies):
            species_len = np.fromfile(fin, dtype=np.int32, count=1)[0]
            # print(species_len)
            species_name = "".join(chr(f) for f in np.fromfile(fin, dtype=np.uint8, count=species_len) if f != 0)
            # print(species_name)
            species_list.append(species_name)
            species_mass.append("".join(chr(f) for f in np.fromfile(fin, dtype=np.uint8, count=16) if f != 0))
            
        timerange = range(0, duration + 1, reportstep)

        tr = len(timerange)

        row1 = ["node"] * nnodes * len(species_list) + ["link"] * nlinks * len(species_list)
        row2 = []
        for i in [nnodes, nlinks]:
            for j in species_list:
                row2.append([j] * i)
        row2 = [y for x in row2 for y in x]
        row3 = [node_list for i in species_list] + [link_list for i in species_list]
        row3 = [y for x in row3 for y in x]

        tuples = list(zip(row1, row2, row3))
        index = pd.MultiIndex.from_tuples(tuples, names=["type", "species", "name"])

        try:
            data = np.fromfile(fin, dtype=np.dtype(ftype), count=tr * (len(species_list * (nnodes + nlinks))))
            data = np.reshape(data, (tr, len(species_list * (nnodes + nlinks))))
        except Exception as e:
            print(e)
            print("oops")

        postlog = np.fromfile(fin, dtype=np.int32, count=4)
        offset = postlog[0]
        numreport = postlog[1]
        errorcode = postlog[2]
        magicnew = postlog[3]
        if errorcode != 0:
            print(f"ERROR CODE: {errorcode}")
            print(offset, numreport)

        df_fin = pd.DataFrame(index=index, columns=timerange).transpose()
        if magic1 == magicnew:
            # print("Magic# Match")
            df_fin = pd.DataFrame(data.transpose(), index=index, columns=timerange)
            df_fin = df_fin.transpose()

        else:
            print("Magic#s do not match!")
    for species in species_list:
        res.node[species] = df_fin['node'][species]
        res.link[species] = df_fin['link'][species]
    return res
