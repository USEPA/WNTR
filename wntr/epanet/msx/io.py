# coding: utf-8
"""I/O functions for EPANET-MSX toolkit compatibility"""

import datetime
import logging
import sys
from io import FileIO, TextIOWrapper

import numpy as np
import pandas as pd

import wntr.network
from wntr.epanet.msx.exceptions import EpanetMsxException
from wntr.epanet.util import ENcomment
from wntr.network.elements import Source
from wntr.quality.base import LocationType, VariableType
from wntr.quality.multispecies import MultispeciesQualityModel, Parameter, Species
from wntr.utils.citations import Citation

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
    "[END]",
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
        self.rxn: MultispeciesQualityModel = None
        self.sections = dict()
        for sec in _INP_SECTIONS:
            self.sections[sec] = []
        self.top_comments = []
        self.patterns = dict()

    @classmethod
    def read(cls, msx_filename: str, rxn_model: MultispeciesQualityModel = None):
        """
        Read an EPANET-MSX input file (.msx) and load data into a water quality
        reactions model. Only MSX 2.0 files are recognized.

        Parameters
        ----------
        msx_file : str
            the filename of the .msx file to read in
        rxn_model : WaterQualityReactionsModel, optional
            the model to put data into, by default None (new model)

        Returns
        -------
        WaterQualityReactionsModel
            the model with the new species, reactions and other options added
        """
        if rxn_model is None:
            rxn_model = MultispeciesQualityModel()
        obj = cls()
        obj.rxn = rxn_model
        # if not isinstance(msx_file, list):
        #     msx_file = [msx_file]
        rxn_model.filename = msx_filename

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
            obj._read_end()
            return obj.rxn
        except Exception as e:
            raise EpanetMsxException(200) from e

    @classmethod
    def write(cls, filename: str, msx: MultispeciesQualityModel):
        """Write an MSX input file.

        Parameters
        ----------
        filename : str
            the filename to write
        rxn : MultispeciesQualityModel
            the multispecies reaction model
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
            obj._write_source_dict(fout)
            obj._write_quality(fout)
            obj._write_diffusivity(fout)
            obj._write_parameters(fout)
            obj._write_patterns(fout)
            obj._write_report(fout)
            obj._write_end(fout)
            fout.write("; END of MSX file generated by WNTR\n")

    def _read_end(self):
        pass

    def _write_end(self, fout):
        fout.write("[END]\n")
        pass
    

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
        self.rxn.desc = comments

    def _read_options(self):
        lines = []
        note = ENcomment()
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
        lines = []
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
                if len(vals) == 3:
                    species = self.rxn.add_species(vals[0], vals[1], vals[2], note=note)
                elif len(vals) == 5:
                    species = self.rxn.add_species(vals[0], vals[1], vals[2], float(vals[3]), float(vals[4]), note=note)
                else:
                    raise EpanetMsxException(201, note="at line {} of [SPECIES] section:\n{}".format(lnum, line))
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [SPECIES] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_coefficients(self):
        lines = []
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
                coeff = self.rxn.add_coefficient(vals[0], vals[1], float(vals[2]), note=note)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [COEFFICIENTS] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_terms(self):
        lines = []
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
                term = self.rxn.add_other_term(vals[0], " ".join(vals[1:]), note=note)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [TERMS] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_pipes(self):
        lines = []
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
                reaction = self.rxn.add_pipe_reaction(vals[1], vals[0], " ".join(vals[2:]), note=note)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [PIPES] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_tanks(self):
        lines = []
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
                reaction = self.rxn.add_tank_reaction(vals[1], vals[0], " ".join(vals[2:]), note=note)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [TANKS] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_source_dict(self):
        lines = []
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
                if not self.rxn.has_variable(spec):
                    raise ValueError("Undefined species in [SOURCES] section: {}".format(spec))
                if spec not in self.rxn._source_dict.keys():
                    self.rxn._source_dict[spec] = dict()
                source = dict(source_type=typ, strength=strength, pattern=pat, note=note)
                self.rxn._source_dict[spec][node] = source
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [SOURCES] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_quality(self):
        lines = []
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
                if not self.rxn.has_variable(spec):
                    raise ValueError("Undefined species in [QUALITY] section: {}".format(spec))
                if spec not in self.rxn._inital_qual_dict.keys():
                    self.rxn._inital_qual_dict[spec] = dict(global_value=None, nodes=dict(), links=dict())
                if cmd[0].lower() == "g":
                    self.rxn._species[spec].initial_quality = float(concen)
                elif cmd[0].lower() == "n":
                    self.rxn._inital_qual_dict[spec]["nodes"][netid] = float(concen)
                elif cmd[1].lower() == "l":
                    self.rxn._inital_qual_dict[spec]["links"][netid] = float(concen)
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [QUALITY] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_parameters(self):
        lines = []
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
                coeff = self.rxn.get_variable(paramid)
                if not isinstance(coeff, Parameter):
                    raise ValueError("Invalid parameter {}".format(paramid))
                value = float(value)
                if typ.lower()[0] == "p":
                    coeff.pipe_values[netid] = value
                elif typ.lower()[0] == "t":
                    coeff.tank_values[netid] = value
                else:
                    raise ValueError("Invalid parameter type {}".format(typ))
            except EpanetMsxException:
                raise
            except Exception as e:
                raise EpanetMsxException(201, note="at line {} of [PARAMETERS] section:\n{}".format(lnum, line)) from e
            else:
                note = ENcomment()

    def _read_diffusivity(self):
        lines = []
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
                species = self.rxn.get_variable(vals[0])
                if not isinstance(species, Species):
                    raise RuntimeError("Invalid species {} in diffusivity".format(vals[0]))
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
            self.rxn.add_pattern(pattern_name, pattern)

    def _read_report(self):
        lines = []
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
                    if not self.rxn.has_variable(vals[1]):
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

        def to_msx_string(self) -> str:
            tols = self.get_tolerances()
            if tols is None:
                tolstr = ""
            else:
                tolstr = " {:12.6g} {:12.6g}".format(*tols)
            return "{:<12s} {:<8s} {:<8s}{:s}".format(
                self.var_type.name.upper(),
                self.name,
                self.units,
                tolstr,
            )

        for var in self.rxn.variables(var_type=VariableType.BULK):
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        for var in self.rxn.variables(var_type=VariableType.WALL):
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        fout.write("\n")

    def _write_coefficients(self, fout):
        fout.write("[COEFFICIENTS]\n")

        def to_msx_string(self) -> str:
            # if self.units is not None:
            #     post = r' ; {"units"="' + str(self.units) + r'"}'
            # else:
            post = ""
            return "{:<12s} {:<8s} {:<16s}{}".format(self.var_type.name.upper(), self.name, str(self.global_value), post)

        for var in self.rxn.variables(var_type=VariableType.CONST):
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        for var in self.rxn.variables(var_type=VariableType.PARAM):
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        fout.write("\n")

    def _write_terms(self, fout):
        fout.write("[TERMS]\n")

        def to_msx_string(self) -> str:
            return "{:<8s} {:<64s}".format(self.name, self.expression)

        for var in self.rxn.variables(var_type=VariableType.TERM):
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string(to_msx_string(var))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(to_msx_string(var), var.note))
            else:
                fout.write("  {}\n".format(to_msx_string(var)))
        fout.write("\n")

    def _write_pipes(self, fout):
        fout.write("[PIPES]\n")
        for var in self.rxn.reactions(location=LocationType.PIPE):
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string("{:<12s} {:<8s} {:<32s}".format(var.expr_type.name.upper(), str(var.species), var.expression))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format("{:<12s} {:<8s} {:<32s}".format(var.expr_type.name.upper(), str(var.species), var.expression), var.note))
            else:
                fout.write("  {}\n".format("{:<12s} {:<8s} {:<32s}".format(var.expr_type.name.upper(), str(var.species), var.expression)))
        fout.write("\n")

    def _write_tanks(self, fout):
        fout.write("[TANKS]\n")
        for var in self.rxn.reactions(location=LocationType.TANK):
            if isinstance(var.note, ENcomment):
                fout.write("{}\n".format(var.note.wrap_msx_string("{:<12s} {:<8s} {:<32s}".format(var.expr_type.name.upper(), str(var.species), var.expression))))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format("{:<12s} {:<8s} {:<32s}".format(var.expr_type.name.upper(), str(var.species), var.expression), var.note))
            else:
                fout.write("  {}\n".format("{:<12s} {:<8s} {:<32s}".format(var.expr_type.name.upper(), str(var.species), var.expression)))
        fout.write("\n")

    def _write_source_dict(self, fout):
        fout.write("[SOURCES]\n")
        for species in self.rxn._source_dict.keys():
            for node, src in self.rxn._source_dict[species].items():
                if isinstance(src["note"], ENcomment):
                    fout.write(
                        src["note"].wrap_msx_string(
                            "{:<10s} {:<8s} {:<8s} {:12s} {:<12s}".format(src["source_type"], node, species, src["strength"], src["pattern"] if src["pattern"] is not None else "")
                        )
                    )
                elif isinstance(src["note"], str):
                    fout.write(
                        "  {:<10s} {:<8s} {:<8s} {} {:<12s} ; {}\n".format(
                            src["source_type"], node, species, src["strength"], src["pattern"] if src["pattern"] is not None else "", src["note"]
                        )
                    )
                else:
                    fout.write(
                        "  {:<10s} {:<8s} {:<8s} {} {:<12s}\n".format(src["source_type"], node, species, src["strength"], src["pattern"] if src["pattern"] is not None else "")
                    )
                if src["note"] is not None:
                    fout.write("\n")
        fout.write("\n")

    def _write_quality(self, fout):
        fout.write("[QUALITY]\n")
        for spec, species in self.rxn._species.items():
            if species.initial_quality is not None:
                fout.write("  {:<8s} {:<8s} {}\n".format("GLOBAL", species.name, species.initial_quality))
        for species in self.rxn._inital_qual_dict.keys():
            for typ, val in self.rxn._inital_qual_dict[species].items():
                if typ in ["nodes", "links"]:
                    for node, conc in val.items():
                        fout.write("  {:<8s} {:<8s} {:<8s} {}\n".format(typ.upper()[0:4], node, species, conc))
        fout.write("\n")

    def _write_parameters(self, fout):
        fout.write("[PARAMETERS]\n")
        for var in self.rxn.variables(var_type=VariableType.PARAM):
            had_entries = False
            if not isinstance(var, Parameter):
                pass
            paramID = var.name
            for pipeID, value in var.pipe_values.items():
                fout.write("  PIPE     {:<8s} {:<8s} {}\n".format(pipeID, paramID, value))
                had_entries = True
            for tankID, value in var.tank_values.items():
                fout.write("  PIPE     {:<8s} {:<8s} {}\n".format(tankID, paramID, value))
                had_entries = True
            if had_entries:
                fout.write("\n")
        fout.write("\n")

    def _write_patterns(self, fout):
        fout.write("[PATTERNS]\n")
        for pattern_name, pattern in self.rxn._pattern_dict.items():
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
            spec: Species = self.rxn.get_variable(name)
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
                    self.rxn._options.report.species_precision[spec] if spec in self.rxn._options.report.species_precision.keys() else "",
                )
            )
        if self.rxn._options.report.report_filename:
            fout.write("  FILE      {}\n".format(self.rxn._options.report.report_filename))
        if self.rxn._options.report.pagesize:
            fout.write("  PAGESIZE  {}\n".format(self.rxn._options.report.pagesize))
        fout.write("\n")


def MsxBinFile(filename, wn: wntr.network.WaterNetworkModel):
    duration = int(wn.options.time.duration)

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

        for i in range(nspecies):
            species_len = int(np.fromfile(fin, dtype=np.int32, count=1))
            species_name = "".join(chr(f) for f in np.fromfile(fin, dtype=np.uint8, count=species_len) if f != 0)
            species_list.append(species_name)
        species_mass = []
        for i in range(nspecies):
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
    return df_fin
