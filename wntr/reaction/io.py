# coding: utf-8

import logging
import sys

from wntr.network.elements import Source
from wntr.reaction.model import WaterQualityReactionsModel
from wntr.reaction.variables import Parameter, Species

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
        _cmnt = _vc[1]
    else:
        _vals = _vc[0].split()
        _cmnt = _vc[1]
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
        prev_comment = None
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
        prev_comment = None
        for lnum, line in self.sections["[SPECIES]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) not in [3, 5]:
                    raise SyntaxError("Invalid [SPECIES] entry")
                if len(vals) == 3:
                    species = self.rxn.add_species(vals[0], vals[1], vals[2], note=comment)
                elif len(vals) == 5:
                    species = self.rxn.add_species(vals[0], vals[1], vals[2], float(vals[3]), float(vals[4]), note=comment)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_coefficients(self):
        lines = []
        prev_comment = None
        for lnum, line in self.sections["[COEFFICIENTS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) != 3:
                    raise SyntaxError("Invalid [COEFFICIENTS] entry")
                coeff = self.rxn.add_coefficient(vals[0], vals[1], float(vals[2]), note=comment)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_terms(self):
        lines = []
        prev_comment = None
        for lnum, line in self.sections["[TERMS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) < 2:
                    raise SyntaxError("Invalid [TERMS] entry")
                term = self.rxn.add_other_term(vals[0], " ".join(vals[1:]), note=comment)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_pipes(self):
        lines = []
        prev_comment = None
        for lnum, line in self.sections["[PIPES]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) < 3:
                    raise SyntaxError("Invalid [PIPES] entry")
                reaction = self.rxn.add_pipe_reaction(vals[1], vals[0], " ".join(vals[2:]), note=comment)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_tanks(self):
        lines = []
        prev_comment = None
        for lnum, line in self.sections["[TANKS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) < 3:
                    raise SyntaxError("Invalid [TANKS] entry")
                reaction = self.rxn.add_tank_reaction(vals[1], vals[0], " ".join(vals[2:]), note=comment)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_sources(self):
        lines = []
        prev_comment = None
        for lnum, line in self.sections["[SOURCES]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) == 4:
                    typ, node, spec, strength = vals
                    pat = None
                else:
                    typ, node, spec, strength, pat = vals
                if not self.rxn.has_variable(spec):
                    raise ValueError('Undefined species in [QUALITY] section: {}'.format(spec))
                if spec not in self.rxn._sources.keys():
                    self.rxn._sources[spec] = dict()
                source = Source(None, name=spec, node_name=node, source_type=typ, strength=strength, pattern=pat)
                self.rxn._sources[spec][node] = source
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_quality(self):
        lines = []
        prev_comment = None
        for lnum, line in self.sections["[QUALITY]"]:
            vals, comment = _split_line(line)
            if len(vals) == 0: continue
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) == 4:
                    cmd, netid, spec, concen = vals
                else:
                    cmd, spec, concen = vals
                if cmd[0].lower() not in ['g', 'n', 'l']:
                    raise SyntaxError('Unknown first word in [QUALITY] section')
                if not self.rxn.has_variable(spec):
                    raise ValueError('Undefined species in [QUALITY] section: {}'.format(spec))
                if spec not in self.rxn._inital_quality.keys():
                    self.rxn._inital_quality[spec] = dict(global_value=None, nodes=dict(), links=dict())
                if cmd[0].lower() == 'g':
                    self.rxn._inital_quality[spec]['global_value'] = float(concen)
                elif cmd[0].lower() == 'n':
                    self.rxn._inital_quality[spec]['nodes'][netid] = float(concen)
                elif cmd[1].lower() == 'l':
                    self.rxn._inital_quality[spec]['links'][netid] = float(concen)
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_parameters(self):
        lines = []
        prev_comment = None
        for lnum, line in self.sections["[PARAMETERS]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                typ, netid, paramid, value = vals
                coeff = self.rxn.get_variable(paramid)
                if not isinstance(coeff, Parameter):
                    raise RuntimeError("Invalid parameter {}".format(paramid))
                value = float(value)
                if typ.lower()[0] == "p":
                    coeff.pipe_values[netid] = vals
                elif typ.lower()[0] == "t":
                    coeff.tank_values[netid] = vals
                else:
                    raise RuntimeError("Invalid parameter type {}".format(typ))
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def _read_diffusivity(self):
        lines = []
        prev_comment = None
        for lnum, line in self.sections["[DIFFUSIVITY]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) != 2:
                    raise SyntaxError("Invalid [DIFFUSIVITIES] entry")
                species = self.rxn.get_variable(vals[0])
                if not isinstance(species, Species):
                    raise RuntimeError("Invalid species {} in diffusivity".format(vals[0]))
                species.diffusivity = float(vals[1])
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

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
        prev_comment = None
        for lnum, line in self.sections["[REPORT]"]:
            vals, comment = _split_line(line)
            if vals is None:
                prev_comment = comment
                continue
            if prev_comment is not None and comment is None:
                comment = prev_comment
                prev_comment = None
            try:
                if len(vals) == 0:
                    continue
                if len(vals) < 2:
                    raise SyntaxError('Invalid number of arguments in [REPORT] section')
                cmd = vals[0][0].lower()
                if cmd == 'n': # NODES
                    if self.rxn._options.report.nodes is None:
                        if vals[1].upper() == 'ALL':
                            self.rxn._options.report.nodes = 'ALL'
                        else:
                            self.rxn._options.report.nodes = list()
                            self.rxn._options.report.nodes.extend(vals[1:])
                    elif isinstance(self.rxn._options.report.nodes, list):
                        if vals[1].upper() == 'ALL':
                            self.rxn._options.report.nodes = 'ALL'
                        else:
                            self.rxn._options.report.nodes.extend(vals[1:])
                elif cmd == 'l': # LINKS
                    if self.rxn._options.report.links is None:
                        if vals[1].upper() == 'ALL':
                            self.rxn._options.report.links = 'ALL'
                        else:
                            self.rxn._options.report.links = list()
                            self.rxn._options.report.links.extend(vals[1:])
                    elif isinstance(self.rxn._options.report.links, list):
                        if vals[1].upper() == 'ALL':
                            self.rxn._options.report.links = 'ALL'
                        else:
                            self.rxn._options.report.links.extend(vals[1:])
                elif cmd == 'f':
                    self.rxn._options.report.report_filename = vals[1]
                elif cmd == 'p':
                    self.rxn._options.report.pagesize = vals[1]
                elif cmd == 's':
                    if not self.rxn.has_variable(vals[1]):
                        raise ValueError('Undefined species in [REPORT] section: {}'.format(vals[1]))
                    self.rxn._options.report.species[vals[1]] = True if vals[2].lower().startswith('y') else False
                    if len(vals) == 4:
                        self.rxn._options.report.species_precision[vals[1]] = int(vals[3])
                else:
                    raise SyntaxError('Invalid syntax in [REPORT] section: unknown first word')
            except Exception as e:
                raise RuntimeError('Error on line {} of file "{}": {}'.format(lnum, self.rxn.filename, line)) from e

    def write(self, filename, rxn_model):
        pass


class MsxBinFile(object):
    def __init__(self):
        pass

    def read(self, filename):
        pass
