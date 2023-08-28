# coding: utf-8

import sys
import logging
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
        for lnum, line in self.sections['[TITLE]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            lines.append(line)
        if len(lines) > 0:
            self.rxn.title = lines[0]
        if len(lines) > 1:
            self.rxn.desc = '\n'.join(lines[1:])

    def _read_options(self):
        lines = []
        for lnum, line in self.sections['[OPTIONS]']:
            vals, comment = _split_line(line)
            if len(vals) != 2:
                raise RuntimeError('Invalid options line: "{}"'.format(line))
            name, val = vals[0].upper(), vals[1].upper()
            try:
                if name == 'AREA_UNITS':
                    self.rxn._options.quality.area_units = val
                elif name == 'RATE_UNITS':
                    self.rxn._options.quality.rate_units = val
                elif name == 'SOLVER':
                    self.rxn._options.quality.solver = val
                elif name == 'COUPLING':
                    self.rxn._options.quality.coupling = val
                elif name == 'TIMESTEP':
                    self.rxn._options.time.timestep = int(val)
                elif name == 'ATOL':
                    self.rxn._options.quality.atol = float(val)
                elif name == 'RTOL':
                    self.rxn._options.quality.rtol = float(val)
                elif name == 'COMPILER':
                    self.rxn._options.quality.compiler = val
                elif name == 'SEGMENTS':
                    self.rxn._options.quality.segments = int(val)
                elif name == 'PECLET':
                    self.rxn._options.quality.peclet = int(val)
            except Exception as e:
                raise ('Error in options line: "{}"'.format(line)) from e
                
    def _read_species(self):
        lines = []
        for lnum, line in self.sections['[SPECIES]']:
            vals, comment = _split_line(line)
            if len(vals) not in [3, 5]:
                raise RuntimeError('Invalid species line: "{}"'.format(line))
            try:
                if len(vals) == 3:
                    species = self.rxn.add_species(vals[0], vals[1], vals[2], note=comment)
                elif len(vals) == 5:
                    species = self.rxn.add_species(vals[0], vals[1], vals[2], float(vals[3]), float(vals[4]), note=comment)
            except Exception as e:
                raise RuntimeError('Invalid species line: "{}"'.format(line)) from e

    def _read_coefficients(self):
        lines = []
        for lnum, line in self.sections['[COEFFICIENTS]']:
            vals, comment = _split_line(line)
            if len(vals) != 3:
                raise RuntimeError('Invalid coefficient line: "{}"'.format(line))
            try:
                coeff = self.rxn.add_coefficient(vals[0], vals[1], float(vals[2]), note=comment)
            except Exception as e:
                raise RuntimeError('Invalid coefficient line: "{}"'.format(line)) from e

    def _read_terms(self):
        lines = []
        for lnum, line in self.sections['[TERMS]']:
            vals, comment = _split_line(line)
            if len(vals) < 2:
                raise RuntimeError('Invalid term line: "{}"'.format(line))
            term = self.rxn.add_other_term(vals[0], ' '.join(vals[1:]), note=comment)

    def _read_pipes(self):
        lines = []
        for lnum, line in self.sections['[PIPES]']:
            vals, comment = _split_line(line)
            if len(vals) < 3:
                raise RuntimeError('Invalid tanks line: "{}"'.format(line))
            reaction = self.rxn.add_pipe_reaction(vals[0], vals[1], vals[2:], note=comment)

    def _read_tanks(self):
        lines = []
        for lnum, line in self.sections['[TANKS]']:
            vals, comment = _split_line(line)
            if len(vals) < 3:
                raise RuntimeError('Invalid tanks line: "{}"'.format(line))
            reaction = self.rxn.add_tank_reaction(vals[0], vals[1], vals[2:], note=comment)

    def _read_sources(self):
        lines = []
        for lnum, line in self.sections['[SOURCES]']:
            vals, comment = _split_line(line)
            try:
                if len(vals) == 4:
                    typ, node, spec, strength = vals
                    pat = None
                else:
                    typ, node, spec, strength, pat = vals
                source = Source(None, name=spec, node_name=node, source_type=typ, strength=strength, pattern=pat)
                self.rxn._sources['{}:{}:{}'.format(typ,node,spec)] = source
            except Exception as e:
                raise RuntimeError('Invalid sources line: "{}"'.format(line)) from e

    def _read_quality(self):
        lines = []
        for lnum, line in self.sections['[QUALITY]']:
            vals, comment = _split_line(line)
            self.rxn._inital_quality.extend(lines)

    def _read_parameters(self):
        lines = []
        for lnum, line in self.sections['[PARAMETERS]']:
            vals, comment = _split_line(line)
            try:
                typ, netid, paramid, value = vals
                coeff = self.rxn.get_variable(paramid)
                if not isinstance(coeff, Parameter):
                    raise RuntimeError('Invalid parameter {}'.format(paramid))
                value = float(value)
                if typ.lower()[0] == 'p':
                    coeff.pipe_values[netid] = vals
                elif typ.lower()[0] == 't':
                    coeff.tank_values[netid] = vals
                else:
                    raise RuntimeError('Invalid parameter type {}'.format(typ))
            except Exception as e:
                raise RuntimeError('Invalid parameters line: "{}"'.format(line)) from e

    def _read_diffusivity(self):
        lines = []
        for lnum, line in self.sections['[DIFFUSIVITY]']:
            vals, comment = _split_line(line)
            if len(vals) != 2:
                raise RuntimeError('Error in diffusivity line: "{}"'.format(line))
            try:
                species = self.rxn.get_variable(vals[0])
            except:
                raise RuntimeError('Invalid species {} in diffusivity line: "{}"'.format(vals[0], line))
            if not isinstance(species, Species):
                raise RuntimeError('Invalid species {} in diffusivity line: "{}"'.format(vals[0], line))
            try:
                species.diffusivity = float(vals[1])
            except Exception as e:
                raise RuntimeError('Error in diffusivity line: "{}"'.format(line)) from e

    def _read_patterns(self):
        _patterns = dict()
        for lnum, line in self.sections['[PATTERNS]']:
            # read the lines for each pattern -- patterns can be multiple lines of arbitrary length
            line = line.split(';')[0]
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
        for lnum, line in self.sections['[REPORT]']:
            vals, comment = _split_line(line)
            self.rxn._report.extend(lines)

    def write(self, filename, rxn_model):
        pass


class MsxBinFile(object):
    def __init__(self):
        pass

    def read(self, filename):
        pass
