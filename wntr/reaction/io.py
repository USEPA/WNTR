# coding: utf-8

import datetime
from io import FileIO, TextIOWrapper
import logging
import sys

from wntr.network.elements import Source
from wntr.reaction.base import MSXComment, RxnLocationType, RxnVariableType
from wntr.reaction.model import WaterQualityReactionsModel
from wntr.reaction.variables import Parameter, Species
from wntr.utils.citations import Citation

sys_default_enc = sys.getdefaultencoding()


logger = logging.getLogger(__name__)

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
    def __init__(self):
        self.sections = dict()
        for sec in _INP_SECTIONS:
            self.sections[sec] = []
        self.top_comments = []
        self.patterns = dict()

    def read(self, msx_file, rxn_model=None):
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
            rxn_model = WaterQualityReactionsModel()
        self.rxn = rxn_model
        # if not isinstance(msx_file, list):
        #     msx_file = [msx_file]
        rxn_model.filename = msx_file

        self.patterns = dict()
        self.top_comments = []
        self.sections = dict()
        for sec in _INP_SECTIONS:
            self.sections[sec] = []

        section = None
        lnum = 0
        edata = {"fname": msx_file}
        with open(msx_file, "r", encoding=sys_default_enc) as f:
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
                    elif sec == "[END]":
                        # logger.info('%(fname)s:%(lnum)-6d %(sec)13s end of file found' % edata)
                        section = None
                        break
                    else:
                        raise RuntimeError('%(fname)s:%(lnum)d: Invalid section "%(sec)s"' % edata)
                elif section is None and line.startswith(";"):
                    self.top_comments.append(line[1:])
                    continue
                elif section is None:
                    logger.debug("Found confusing line: %s", repr(line))
                    raise RuntimeError("%(fname)s:%(lnum)d: Non-comment outside of valid section!" % edata)
                # We have text, and we are in a section
                self.sections[section].append((lnum, line))

        self._read_title()
        self._read_options()
        self._read_species()
        self._read_coefficients()
        self._read_terms()
        self._read_pipes()
        self._read_tanks()
        self._read_sources()
        self._read_quality()
        self._read_parameters()
        self._read_diffusivity()
        self._read_patterns()
        self._read_report()
        return self.rxn

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
        note = MSXComment()
        for lnum, line in self.sections["[OPTIONS]"]:
            vals, comment = _split_line(line)
            try:
                if len(vals) != 2:
                    raise SyntaxError("Invalid [OPTIONS] entry")
                name, val = vals[0].upper(), vals[1].upper()
                if name == "AREA_UNITS":
                    self.rxn._options.quality.area_units = val
                elif name == "RATE_UNITS":
                    self.rxn._options.quality.rate_units = val
                elif name == "SOLVER":
                    self.rxn._options.quality.solver = val
                elif name == "COUPLING":
                    self.rxn._options.quality.coupling = val
                elif name == "TIMESTEP":
                    self.rxn._options.quality.timestep = int(val)
                elif name == "ATOL":
                    self.rxn._options.quality.atol = float(val)
                elif name == "RTOL":
                    self.rxn._options.quality.rtol = float(val)
                elif name == "COMPILER":
                    self.rxn._options.quality.compiler = val
                elif name == "SEGMENTS":
                    self.rxn._options.quality.segments = int(val)
                elif name == "PECLET":
                    self.rxn._options.quality.peclet = int(val)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_species(self):
        lines = []
        note = MSXComment()
        for lnum, line in self.sections["[SPECIES]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) not in [3, 5]:
                    raise SyntaxError("Invalid [SPECIES] entry")

                if len(vals) == 3:
                    species = self.rxn.add_species(vals[0], vals[1], vals[2], note=note)
                elif len(vals) == 5:
                    species = self.rxn.add_species(vals[0], vals[1], vals[2], float(vals[3]), float(vals[4]), note=note)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def _read_coefficients(self):
        lines = []
        note = MSXComment()
        for lnum, line in self.sections["[COEFFICIENTS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                if comment is not None:
                    note.pre.append(comment)
                continue
            try:
                if comment is not None:
                    note.post = comment
                if len(vals) != 3:
                    raise SyntaxError("Invalid [COEFFICIENTS] entry")
                coeff = self.rxn.add_coefficient(vals[0], vals[1], float(vals[2]), note=note)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def _read_terms(self):
        lines = []
        note = MSXComment()
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
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def _read_pipes(self):
        lines = []
        note = MSXComment()
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
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def _read_tanks(self):
        lines = []
        note = MSXComment()
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
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def _read_sources(self):
        lines = []
        note = MSXComment()
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
                    raise ValueError("Undefined species in [QUALITY] section: {}".format(spec))
                if spec not in self.rxn._sources.keys():
                    self.rxn._sources[spec] = dict()
                source = dict(source_type=typ, strength=strength, pattern=pat, note=note)
                self.rxn._sources[spec][node] = source
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def _read_quality(self):
        lines = []
        note = MSXComment()
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
                if spec not in self.rxn._inital_quality.keys():
                    self.rxn._inital_quality[spec] = dict(global_value=None, nodes=dict(), links=dict())
                if cmd[0].lower() == "g":
                    self.rxn._inital_quality[spec]["global_value"] = float(concen)
                elif cmd[0].lower() == "n":
                    self.rxn._inital_quality[spec]["nodes"][netid] = float(concen)
                elif cmd[1].lower() == "l":
                    self.rxn._inital_quality[spec]["links"][netid] = float(concen)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def _read_parameters(self):
        lines = []
        note = MSXComment()
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
                    raise RuntimeError("Invalid parameter {}".format(paramid))
                value = float(value)
                if typ.lower()[0] == "p":
                    coeff.pipe_values[netid] = value
                elif typ.lower()[0] == "t":
                    coeff.tank_values[netid] = value
                else:
                    raise RuntimeError("Invalid parameter type {}".format(typ))
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def _read_diffusivity(self):
        lines = []
        note = MSXComment()
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
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

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
        note = MSXComment()
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
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e
            else:
                note = MSXComment()

    def write(self, filename: str, rxn: WaterQualityReactionsModel):
        self.rxn = rxn
        with open(filename, "w") as fout:

            fout.write("; WNTR-reactions MSX file generated {}\n".format(datetime.datetime.now()))
            fout.write("\n")
            self._write_title(fout)
            self._write_options(fout)
            self._write_species(fout)
            self._write_coefficients(fout)
            self._write_terms(fout)
            self._write_pipes(fout)
            self._write_tanks(fout)
            self._write_sources(fout)
            self._write_quality(fout)
            self._write_diffusivity(fout)
            self._write_parameters(fout)
            self._write_patterns(fout)
            self._write_report(fout)
            fout.write("; END of MSX file generated by WNTR\n")

    def _write_title(self, fout):
        fout.write("[TITLE]\n")
        fout.write("  {}\n".format(self.rxn.title))
        fout.write("\n")
        # if self.rxn.desc is not None:
        #     desc = self.rxn.desc.splitlines()
        #     desc = " ".join(desc)
        #     fout.write("; @desc={}\n".format(desc))
        #     fout.write("\n")
        # if self.rxn.citations is not None:
        #     if isinstance(self.rxn.citations, list):
        #         for citation in self.rxn.citations:
        #             fout.write("; @cite={}\n".format(citation.to_dict() if isinstance(citation, Citation) else str(citation)))
        #             fout.write("\n")
        #     else:
        #         citation = self.rxn.citations
        #         fout.write("; @cite={}\n".format(citation.to_dict() if isinstance(citation, Citation) else str(citation)))
        # fout.write("\n")

    def _write_options(self, fout):
        opts = self.rxn._options
        fout.write("[OPTIONS]\n")
        fout.write("  AREA_UNITS  {}\n".format(opts.quality.area_units.upper()))
        fout.write("  RATE_UNITS  {}\n".format(opts.quality.rate_units.upper()))
        fout.write("  SOLVER      {}\n".format(opts.quality.solver.upper()))
        fout.write("  COUPLING    {}\n".format(opts.quality.coupling.upper()))
        fout.write("  TIMESTEP    {}\n".format(opts.quality.timestep))
        fout.write("  ATOL        {}\n".format(opts.quality.atol))
        fout.write("  RTOL        {}\n".format(opts.quality.rtol))
        fout.write("  COMPILER    {}\n".format(opts.quality.compiler.upper()))
        fout.write("  SEGMENTS    {}\n".format(opts.quality.segments))
        fout.write("  PECLET      {}\n".format(opts.quality.peclet))
        fout.write("\n")

    def _write_species(self, fout):
        fout.write("[SPECIES]\n")
        for var in self.rxn.variables(var_type=RxnVariableType.BULK):
            if isinstance(var.note, MSXComment):
                fout.write("{}\n".format(var.note.wrap_msx_string(var.to_msx_string())))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(var.to_msx_string(), var.note))
            else:
                fout.write("  {}\n".format(var.to_msx_string()))
        for var in self.rxn.variables(var_type=RxnVariableType.WALL):
            if isinstance(var.note, MSXComment):
                fout.write("{}\n".format(var.note.wrap_msx_string(var.to_msx_string())))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(var.to_msx_string(), var.note))
            else:
                fout.write("  {}\n".format(var.to_msx_string()))
        fout.write("\n")

    def _write_coefficients(self, fout):
        fout.write("[COEFFICIENTS]\n")
        for var in self.rxn.variables(var_type=RxnVariableType.CONST):
            if isinstance(var.note, MSXComment):
                fout.write("{}\n".format(var.note.wrap_msx_string(var.to_msx_string())))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(var.to_msx_string(), var.note))
            else:
                fout.write("  {}\n".format(var.to_msx_string()))
        for var in self.rxn.variables(var_type=RxnVariableType.PARAM):
            if isinstance(var.note, MSXComment):
                fout.write("{}\n".format(var.note.wrap_msx_string(var.to_msx_string())))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(var.to_msx_string(), var.note))
            else:
                fout.write("  {}\n".format(var.to_msx_string()))
        fout.write("\n")

    def _write_terms(self, fout):
        fout.write("[TERMS]\n")
        for var in self.rxn.variables(var_type=RxnVariableType.TERM):
            if isinstance(var.note, MSXComment):
                fout.write("{}\n".format(var.note.wrap_msx_string(var.to_msx_string())))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(var.to_msx_string(), var.note))
            else:
                fout.write("  {}\n".format(var.to_msx_string()))
        fout.write("\n")

    def _write_pipes(self, fout):
        fout.write("[PIPES]\n")
        for var in self.rxn.reactions(location=RxnLocationType.PIPE):
            if isinstance(var.note, MSXComment):
                fout.write("{}\n".format(var.note.wrap_msx_string(var.to_msx_string())))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(var.to_msx_string(), var.note))
            else:
                fout.write("  {}\n".format(var.to_msx_string()))
        fout.write("\n")

    def _write_tanks(self, fout):
        fout.write("[TANKS]\n")
        for var in self.rxn.reactions(location=RxnLocationType.TANK):
            if isinstance(var.note, MSXComment):
                fout.write("{}\n".format(var.note.wrap_msx_string(var.to_msx_string())))
            elif isinstance(var.note, str):
                fout.write("  {} ; {}\n".format(var.to_msx_string(), var.note))
            else:
                fout.write("  {}\n".format(var.to_msx_string()))
        fout.write("\n")

    def _write_sources(self, fout):
        fout.write("[SOURCES]\n")
        for species in self.rxn._sources.keys():
            for node, src in self.rxn._sources[species].items():
                if isinstance(src["note"], MSXComment):
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
        for species in self.rxn._inital_quality.keys():
            for typ, val in self.rxn._inital_quality[species].items():
                if typ == "global_value":
                    fout.write("  {:<8s} {:<8s} {}\n".format("GLOBAL", species, val))
                elif typ in ["nodes", "links"]:
                    for node, conc in val.items():
                        fout.write("  {:<8s} {:<8s} {:<8s} {}\n".format(typ.upper()[0:4], node, species, conc))
        fout.write("\n")

    def _write_parameters(self, fout):
        fout.write("[PARAMETERS]\n")
        for var in self.rxn.variables(var_type=RxnVariableType.PARAM):
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
        for pattern_name, pattern in self.rxn._patterns.items():
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


class MsxBinFile(object):
    def __init__(self):
        pass

    def read(self, filename):
        pass
