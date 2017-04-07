"""
The wntr.epanet.io module contains methods for reading/writing EPANET input and output files.

.. rubric:: Classes

.. autosummary::

    InpFile
    BinFile

----


"""
from __future__ import absolute_import
import wntr.network
from wntr.network import WaterNetworkModel, Junction, Reservoir, Tank, Pipe, Pump, Valve, LinkStatus
import wntr
import io
import os, sys

from .util import FlowUnits, MassUnits, HydParam, QualParam, MixType, ResultType
from .util import to_si, from_si
from .util import StatisticsType, QualType, PressureUnits

from wntr.network.controls import TimeOfDayCondition, SimTimeCondition, ValueCondition
from wntr.network.controls import OrCondition, AndCondition, IfThenElseControl, ControlAction

import datetime
import networkx as nx
import re
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_INP_SECTIONS = ['[OPTIONS]', '[TITLE]', '[JUNCTIONS]', '[RESERVOIRS]',
                 '[TANKS]', '[PIPES]', '[PUMPS]', '[VALVES]', '[EMITTERS]',
                 '[CURVES]', '[PATTERNS]', '[ENERGY]', '[STATUS]',
                 '[CONTROLS]', '[RULES]', '[DEMANDS]', '[QUALITY]',
                 '[REACTIONS]', '[SOURCES]', '[MIXING]',
                 '[TIMES]', '[REPORT]', '[COORDINATES]', '[VERTICES]',
                 '[LABELS]', '[BACKDROP]', '[TAGS]']

_JUNC_ENTRY = ' {name:20} {elev:12.12g} {dem:12.12g} {pat:24} {com:>3s}\n'
_JUNC_LABEL = '{:21} {:>12s} {:>12s} {:24}\n'

_RES_ENTRY = ' {name:20s} {head:12.12g} {pat:>24s} {com:>3s}\n'
_RES_LABEL = '{:21s} {:>12s} {:>24s}\n'

_TANK_ENTRY = ' {name:20s} {elev:12.6g} {initlev:12.12g} {minlev:12.12g} {maxlev:12.12g} {diam:12.12g} {minvol:12.6g} {curve:20s} {com:>3s}\n'
_TANK_LABEL = '{:21s} {:>12s} {:>12s} {:>12s} {:>12s} {:>12s} {:>12s} {:20s}\n'

_PIPE_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {len:12.12g} {diam:12.12g} {rough:12.12g} {mloss:12.12g} {status:>20s} {com:>3s}\n'
_PIPE_LABEL = '{:21s} {:20s} {:20s} {:>12s} {:>12s} {:>12s} {:>12s} {:>20s}\n'

_PUMP_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {ptype:8s} {params:20s} {speed_keyword:8s} {speed:12.12g} {com:>3s}\n'
_PUMP_LABEL = '{:21s} {:20s} {:20s} {:20s}\n'

_VALVE_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {diam:12.12g} {vtype:4s} {set:12.12g} {mloss:12.12g} {com:>3s}\n'
_VALVE_LABEL = '{:21s} {:20s} {:20s} {:>12s} {:4s} {:>12s} {:>12s}\n'

_CURVE_ENTRY = ' {name:10s} {x:12f} {y:12f} {com:>3s}\n'
_CURVE_LABEL = '{:11s} {:12s} {:12s}\n'

def _split_line(line):
    _vc = line.split(';', 1)
    _cmnt = None
    _vals = None
    if len(_vc) == 0:
        pass
    elif len(_vc) == 1:
        _vals = _vc[0].split()
    elif _vc[0] == '':
        _cmnt = _vc[1]
    else:
        _vals = _vc[0].split()
        _cmnt = _vc[1]
    return _vals, _cmnt

def _is_number(s):
    """
    Checks if input is a number


    Parameters
    ----------
    s : anything

    """

    try:
        float(s)
        return True
    except ValueError:
        return False


def _str_time_to_sec(s):
    """
    Converts epanet time format to seconds.


    Parameters
    ----------
    s : string
        EPANET time string. Options are 'HH:MM:SS', 'HH:MM', 'HH'


    Returns
    -------
     Integer value of time in seconds.
    """
    pattern1 = re.compile(r'^(\d+):(\d+):(\d+)$')
    time_tuple = pattern1.search(s)
    if bool(time_tuple):
        return (int(time_tuple.groups()[0])*60*60 +
                int(time_tuple.groups()[1])*60 +
                int(round(float(time_tuple.groups()[2]))))
    else:
        pattern2 = re.compile(r'^(\d+):(\d+)$')
        time_tuple = pattern2.search(s)
        if bool(time_tuple):
            return (int(time_tuple.groups()[0])*60*60 +
                    int(time_tuple.groups()[1])*60)
        else:
            pattern3 = re.compile(r'^(\d+)$')
            time_tuple = pattern3.search(s)
            if bool(time_tuple):
                return int(time_tuple.groups()[0])*60*60
            else:
                raise RuntimeError("Time format in "
                                   "INP file not recognized. ")


def _clock_time_to_sec(s, am_pm):
    """
    Converts epanet clocktime format to seconds.


    Parameters
    ----------
    s : string
        EPANET time string. Options are 'HH:MM:SS', 'HH:MM', HH'

    am : string
        options are AM or PM


    Returns
    -------
    Integer value of time in seconds

    """
    if am_pm.upper() == 'AM':
        am = True
    elif am_pm.upper() == 'PM':
        am = False
    else:
        raise RuntimeError('am_pm option not recognized; options are AM or PM')

    pattern1 = re.compile(r'^(\d+):(\d+):(\d+)$')
    time_tuple = pattern1.search(s)
    if bool(time_tuple):
        time_sec = (int(time_tuple.groups()[0])*60*60 +
                    int(time_tuple.groups()[1])*60 +
                    int(round(float(time_tuple.groups()[2]))))
        if not am:
            time_sec += 3600*12
        if s.startswith('12'):
            time_sec -= 3600*12
        return time_sec
    else:
        pattern2 = re.compile(r'^(\d+):(\d+)$')
        time_tuple = pattern2.search(s)
        if bool(time_tuple):
            time_sec = (int(time_tuple.groups()[0])*60*60 +
                        int(time_tuple.groups()[1])*60)
            if not am:
                time_sec += 3600*12
            if s.startswith('12'):
                time_sec -= 3600*12
            return time_sec
        else:
            pattern3 = re.compile(r'^(\d+)$')
            time_tuple = pattern3.search(s)
            if bool(time_tuple):
                time_sec = int(time_tuple.groups()[0])*60*60
                if not am:
                    time_sec += 3600*12
                if s.startswith('12'):
                    time_sec -= 3600*12
                return time_sec
            else:
                raise RuntimeError("Time format in "
                                   "INP file not recognized. ")


def _sec_to_string(sec):
    hours = int(sec/3600.)
    sec -= hours*3600
    mm = int(sec/60.)
    sec -= mm*60
    return (hours, mm, int(sec))


class InpFile(object):
    """
	EPANET INP file reader and writer class.

    This class provides read
    and write functionality for EPANET INP files.
    The EPANET Users Manual provides full documentation for the INP file format in its Appendix C.
    """
    def __init__(self):
        self.sections = {}
        for sec in _INP_SECTIONS:
            self.sections[sec] = []
        self.mass_units = None
        self.flow_units = None
        self.top_comments = []
        self.curves = {}

    def read(self, inp_files, wn=None):
        """Method to read EPANET INP file and load data into a water network model object.

        Parameters
        ----------
        inp_files : str or list
            An EPANET INP input file or list of INP files to be combined

        Returns
        -------
        :class:`wntr.network.WaterNetworkModel.WaterNetworkModel`
            A water network model object

        """

        """
        .. note::
            Parsing should be done in the following order:
                - Options
                - Times
                - Curves
                - Patterns
                - Nodes
                    - Junctions
                    - Reservoirs
                    - Tanks
                - Links
                    - Pipes
                    - Pumps
                    - Valves
                - Emitters
                - Order doesn't matter for remaining sections

        """

        if wn is None:
            wn = WaterNetworkModel()
        self.wn = wn
        if not isinstance(inp_files, list):
            inp_files = [inp_files]
        wn.name = inp_files[0]

        self.curves = {}
        self.top_comments = []
        self.sections = {}
        for sec in _INP_SECTIONS:
            self.sections[sec] = []
        self.mass_units = None
        self.flow_units = None

        for filename in inp_files:
          section = None
          lnum = 0
          edata = {'fname': filename}
          with io.open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                lnum += 1
                edata['lnum'] = lnum
                line = line.strip()
                nwords = len(line.split())
                if len(line) == 0 or nwords == 0:
                    # Blank line
                    continue
                elif line.startswith('['):
                    vals = line.split(None, 1)
                    sec = vals[0].upper()
                    edata['sec'] = sec
                    if sec in _INP_SECTIONS:
                        section = sec
                        #logger.info('%(fname)s:%(lnum)-6d %(sec)13s section found' % edata)
                        continue
                    elif sec == '[END]':
                        #logger.info('%(fname)s:%(lnum)-6d %(sec)13s end of file found' % edata)
                        section = None
                        break
                    else:
                        raise RuntimeError('%(fname)s:%(lnum)d: Invalid section "%(sec)s"' % edata)
                elif section is None and line.startswith(';'):
                    self.top_comments.append(line[1:])
                    continue
                elif section is None:
                    logger.debug('Found confusing line: %s', repr(line))
                    raise RuntimeError('%(fname)s:%(lnum)d: Non-comment outside of valid section!' % edata)
                # We have text, and we are in a section
                self.sections[section].append((lnum, line))

        # Parse each of the sections

        ### OPTIONS
        self._read_options()

        ### CURVES
        self._read_curves()

        ### PATTERNS
        self._read_patterns()

        ### JUNCTIONS
        self._read_junctions()

        ### RESERVOIRS
        self._read_reservoirs()

        ### TANKS
        self._read_tanks()

        ### PIPES
        self._read_pipes()

        ### PUMPS
        self._read_pumps()

        ### VALVES
        self._read_valves()

        ### COORDINATES
        self._read_coordinates()

        ### SOURCES
        self._read_sources()

        ### TIMES
        self._read_times()

        ### STATUS
        self._read_status()

        ### CONTROLS
        self._read_controls()

        ### RULES
        self._read_rules()

        ### REACTIONS
        self._read_reactions()

        ### TITLE
        self._read_title()

        ### ENERGY
        self._read_energy()

        ### DEMANDS
        self._read_demands()

        ### EMITTERS
        self._read_emitters()

        self._read_mixing()
        self._read_report()
        self._read_vertices()
        self._read_labels()

        ### Parse Backdrop
        self._read_backdrop()

        ### TAGS
        self._read_tags()

        # Set the _inpfile io data inside the water network, so it is saved somewhere
        wn._inpfile = self
        return self.wn

    def write(self, filename, wn, units=None):
        """Write a water network model into an EPANET INP file.

        Parameters
        ----------
        filename : str
            Name of the inp file.
        units : str, int or FlowUnits
            Name of the units being written to the inp file.
        """

        if units is not None and isinstance(units, str):
            units=units.upper()
            self.flow_units = FlowUnits[units]
        elif units is not None and isinstance(units, FlowUnits):
            self.flow_units = units
        elif units is not None and isinstance(units, int):
            self.flow_units = FlowUnits(units)
        elif self.flow_units is not None:
            self.flow_units = self.flow_units
        else:
            self.flow_units = FlowUnits.GPM
        if self.mass_units is None:
            self.mass_units = MassUnits.mg
        if not isinstance(wn, WaterNetworkModel):
            raise ValueError('Must pass a WaterNetworkModel object')
        with io.open(filename, 'wb') as f:
            self._write_title(f, wn)
            self._write_junctions(f, wn)
            self._write_reservoirs(f, wn)
            self._write_tanks(f, wn)
            self._write_pipes(f, wn)
            self._write_pumps(f, wn)
            self._write_valves(f, wn)
            self._write_emitters(f, wn)

            self._write_curves(f, wn)
            self._write_patterns(f, wn)
            self._write_energy(f, wn)
            self._write_status(f, wn)
            self._write_controls(f, wn)
            self._write_rules(f, wn)
            self._write_demands(f, wn)

            self._write_quality(f, wn)
            self._write_reactions(f, wn)
            self._write_sources(f, wn)
            self._write_mixing(f, wn)

            self._write_options(f, wn)
            self._write_times(f, wn)
            self._write_report(f, wn)

            self._write_coordinates(f, wn)
            self._write_vertices(f, wn)
            self._write_labels(f, wn)
            self._write_backdrop(f, wn)
            self._write_tags(f, wn)

            self._write_end(f, wn)

    ### Network Components

    def _read_title(self):
        lines = []
        for lnum, line in self.sections['[TITLE]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            lines.append(line)
        self.wn.title = lines

    def _write_title(self, f, wn):
        if wn.name is not None:
            f.write('; Filename: {0}\n'.format(wn.name).encode('ascii'))
            f.write('; WNTR: {}\n; Created: {:%Y-%m-%d %H:%M:%S}\n'.format(wntr.__version__, datetime.datetime.now()).encode('ascii'))
        f.write('[TITLE]\n'.encode('ascii'))
        if hasattr(wn, 'title'):
            for line in wn.title:
                f.write('{}\n'.format(line).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_junctions(self):
        for lnum, line in self.sections['[JUNCTIONS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) == 3:
                self.wn.add_junction(current[0],
                                to_si(self.flow_units, float(current[2]), HydParam.Demand),
                                None,
                                to_si(self.flow_units, float(current[1]), HydParam.Elevation))
            else:
                self.wn.add_junction(current[0],
                                to_si(self.flow_units, float(current[2]), HydParam.Demand),
                                current[3],
                                to_si(self.flow_units, float(current[1]), HydParam.Elevation))

    def _write_junctions(self, f, wn):
        f.write('[JUNCTIONS]\n'.encode('ascii'))
        f.write(_JUNC_LABEL.format(';ID', 'Elevation', 'Demand', 'Pattern').encode('ascii'))
        nnames = list(wn._junctions.keys())
        nnames.sort()
        for junction_name in nnames:
            junction = wn._junctions[junction_name]
            E = {'name': junction_name,
                 'elev': from_si(self.flow_units, junction.elevation, HydParam.Elevation),
                 'dem': from_si(self.flow_units, junction.base_demand, HydParam.Demand),
                 'pat': '',
                 'com': ';'}
            if junction.demand_pattern_name is not None:
                E['pat'] = junction.demand_pattern_name
            f.write(_JUNC_ENTRY.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_reservoirs(self):
        for lnum, line in self.sections['[RESERVOIRS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) == 2:
                self.wn.add_reservoir(current[0],
                                 to_si(self.flow_units, float(current[1]), HydParam.HydraulicHead))
            else:
                self.wn.add_reservoir(current[0],
                                 to_si(self.flow_units, float(current[1]), HydParam.HydraulicHead),
                                 current[2])

    def _write_reservoirs(self, f, wn):
        f.write('[RESERVOIRS]\n'.encode('ascii'))
        f.write(_RES_LABEL.format(';ID', 'Head', 'Pattern').encode('ascii'))
        nnames = list(wn._reservoirs.keys())
        nnames.sort()
        for reservoir_name in nnames:
            reservoir = wn._reservoirs[reservoir_name]
            E = {'name': reservoir_name,
                 'head': from_si(self.flow_units, reservoir.base_head, HydParam.HydraulicHead),
                 'com': ';'}
            if reservoir.head_pattern_name is None:
                E['pat'] = ''
            else:
                E['pat'] = reservoir.head_pattern_name
            f.write(_RES_ENTRY.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_tanks(self):
        for lnum, line in self.sections['[TANKS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) == 8:  # Volume curve provided
                #logger.warn('%(fname)s:%(lnum)-6d %(sec)13s minimum tank volume is only available using EpanetSimulator; others use minimum level and cylindrical tanks.', edata)
                #logger.warn('<%(fname)s:%(sec)s:%(line)d> tank volume curves only supported in EpanetSimulator', edata)
                curve_name = current[7]
                curve_points = []
                for point in self.curves[curve_name]:
                    x = to_si(self.flow_units, point[0], HydParam.Length)
                    y = to_si(self.flow_units, point[1], HydParam.Volume)
                    curve_points.append((x, y))
                self.wn.add_curve(curve_name, 'VOLUME', curve_points)
                curve = self.wn.get_curve(curve_name)
                self.wn.add_tank(current[0],
                            to_si(self.flow_units, float(current[1]), HydParam.Elevation),
                            to_si(self.flow_units, float(current[2]), HydParam.Length),
                            to_si(self.flow_units, float(current[3]), HydParam.Length),
                            to_si(self.flow_units, float(current[4]), HydParam.Length),
                            to_si(self.flow_units, float(current[5]), HydParam.TankDiameter),
                            to_si(self.flow_units, float(current[6]), HydParam.Volume),
                            curve)
            elif len(current) == 7:  # No volume curve provided
                #logger.warn('%(fname)s:%(lnum)-6d %(sec)13s minimum tank volume is only available using EpanetSimulator; others use minimum level and cylindrical tanks.', edata)
                self.wn.add_tank(current[0],
                            to_si(self.flow_units, float(current[1]), HydParam.Elevation),
                            to_si(self.flow_units, float(current[2]), HydParam.Length),
                            to_si(self.flow_units, float(current[3]), HydParam.Length),
                            to_si(self.flow_units, float(current[4]), HydParam.Length),
                            to_si(self.flow_units, float(current[5]), HydParam.TankDiameter),
                            to_si(self.flow_units, float(current[6]), HydParam.Volume))
            else:
                raise RuntimeError('Tank entry format not recognized.')

    def _write_tanks(self, f, wn):
        f.write('[TANKS]\n'.encode('ascii'))
        f.write(_TANK_LABEL.format(';ID', 'Elevation', 'Init Level', 'Min Level', 'Max Level',
                                   'Diameter', 'Min Volume', 'Volume Curve').encode('ascii'))
        nnames = list(wn._tanks.keys())
        nnames.sort()
        for tank_name in nnames:
            tank = wn._tanks[tank_name]
            E = {'name': tank_name,
                 'elev': from_si(self.flow_units, tank.elevation, HydParam.Elevation),
                 'initlev': from_si(self.flow_units, tank.init_level, HydParam.HydraulicHead),
                 'minlev': from_si(self.flow_units, tank.min_level, HydParam.HydraulicHead),
                 'maxlev': from_si(self.flow_units, tank.max_level, HydParam.HydraulicHead),
                 'diam': from_si(self.flow_units, tank.diameter, HydParam.TankDiameter),
                 'minvol': from_si(self.flow_units, tank.min_vol, HydParam.Volume),
                 'curve': '',
                 'com': ';'}
            if tank.vol_curve is not None:
                E['curve'] = tank.vol_curve
            f.write(_TANK_ENTRY.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_pipes(self):
        for lnum, line in self.sections['[PIPES]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if current[7].upper() == 'CV':
                self.wn.add_pipe(current[0],
                            current[1],
                            current[2],
                            to_si(self.flow_units, float(current[3]), HydParam.Length),
                            to_si(self.flow_units, float(current[4]), HydParam.PipeDiameter),
                            float(current[5]),
                            float(current[6]),
                            LinkStatus.Open,
                            True)
            else:
                self.wn.add_pipe(current[0],
                            current[1],
                            current[2],
                            to_si(self.flow_units, float(current[3]), HydParam.Length),
                            to_si(self.flow_units, float(current[4]), HydParam.PipeDiameter),
                            float(current[5]),
                            float(current[6]),
                            LinkStatus[current[7].upper()])

    def _write_pipes(self, f, wn):
        f.write('[PIPES]\n'.encode('ascii'))
        f.write(_PIPE_LABEL.format(';ID', 'Node1', 'Node2', 'Length', 'Diameter',
                                   'Roughness', 'Minor Loss', 'Status').encode('ascii'))
        lnames = list(wn._pipes.keys())
        lnames.sort()
        for pipe_name in lnames:
            pipe = wn._pipes[pipe_name]
            E = {'name': pipe_name,
                 'node1': pipe.start_node,
                 'node2': pipe.end_node,
                 'len': from_si(self.flow_units, pipe.length, HydParam.Length),
                 'diam': from_si(self.flow_units, pipe.diameter, HydParam.PipeDiameter),
                 'rough': pipe.roughness,
                 'mloss': pipe.minor_loss,
                 'status': pipe.get_base_status().name,
                 'com': ';'}
            if pipe.cv:
                E['status'] = 'CV'
            f.write(_PIPE_ENTRY.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_pumps(self):
        def create_curve(curve_name):
            curve_points = []
            for point in self.curves[curve_name]:
                x = to_si(self.flow_units, point[0], HydParam.Flow)
                y = to_si(self.flow_units, point[1], HydParam.HydraulicHead)
                curve_points.append((x,y))
            self.wn.add_curve(curve_name, 'HEAD', curve_points)
            curve = self.wn.get_curve(curve_name)
            return curve

        for lnum, line in self.sections['[PUMPS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue

            pump_type = None
            value = None
            speed = None
            pattern = None

            for i in range(3, len(current), 2):
                if current[i].upper() == 'HEAD':
                    assert pump_type is None, 'In [PUMPS] entry, specify either HEAD or POWER once.'
                    pump_type = 'HEAD'
                    value = create_curve(current[i+1])
                elif current[i].upper() == 'POWER':
                    assert pump_type is None, 'In [PUMPS] entry, specify either HEAD or POWER once.'
                    pump_type = 'POWER'
                    value = to_si(self.flow_units, float(current[i+1]), HydParam.Power)
                elif current[i].upper() == 'SPEED':
                    assert speed is None, 'In [PUMPS] entry, SPEED may only be specified once.'
                    speed = float(current[i+1])
                elif current[i].upper() == 'PATTERN':
                    assert pattern is None, 'In [PUMPS] entry, PATTERN may only be specified once.'
                    pattern = current[i+1]
                else:
                    raise RuntimeError('Pump keyword in inp file not recognized.')

            if speed is None:
                speed = 1.0

            if pump_type is None:
                raise RuntimeError('Either head curve id or pump power must be specified for all pumps.')

            self.wn.add_pump(current[0], current[1], current[2], pump_type, value, speed, pattern)

    def _write_pumps(self, f, wn):
        f.write('[PUMPS]\n'.encode('ascii'))
        f.write(_PUMP_LABEL.format(';ID', 'Node1', 'Node2', 'Properties').encode('ascii'))
        lnames = list(wn._pumps.keys())
        lnames.sort()
        for pump_name in lnames:
            pump = wn._pumps[pump_name]
            E = {'name': pump_name,
                 'node1': pump.start_node,
                 'node2': pump.end_node,
                 'ptype': pump.info_type,
                 'params': '',
                 'speed_keyword': 'SPEED',
                 'speed': pump.speed,
                 'com': ';'}
            if pump.info_type == 'HEAD':
                E['params'] = pump.curve.name
            elif pump.info_type == 'POWER':
                E['params'] = str(from_si(self.flow_units, pump.power, HydParam.Power))
            else:
                raise RuntimeError('Only head or power info is supported of pumps.')
            tmp_entry = _PUMP_ENTRY
            if pump.pattern is not None:
                tmp_entry = (tmp_entry.rstrip('\n').rstrip('}').rstrip('com:>3s').rstrip(' {') +
                             ' {pattern_keyword:10s} {pattern:20s} {com:>3s}\n')
                E['pattern_keyword'] = 'PATTERN'
                E['pattern'] = pump.pattern
            f.write(tmp_entry.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_valves(self):
        for lnum, line in self.sections['[VALVES]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) == 6:
                current.append(0.0)
            else:
                if len(current) != 7:
                    raise RuntimeError('The [VALVES] section of an INP file must have 6 or 7 entries.')
            valve_type = current[4].upper()
            if valve_type in ['PRV', 'PSV', 'PBV']:
                valve_set = to_si(self.flow_units, float(current[5]), HydParam.Pressure)
            elif valve_type == 'FCV':
                valve_set = to_si(self.flow_units, float(current[5]), HydParam.Flow)
            elif valve_type == 'TCV':
                valve_set = float(current[5])
            elif valve_type == 'GPV':
                curve_name = current[5]
                curve_points = []
                for point in self.curves[curve_name]:
                    x = to_si(self.flow_units, point[0], HydParam.Flow)
                    y = to_si(self.flow_units, point[1], HydParam.HeadLoss)
                    curve_points.append((x, y))
                self.wn.add_curve(curve_name, 'HEADLOSS', curve_points)
                valve_set = curve_name
            else:
                raise RuntimeError('VALVE type "%s" unrecognized' % valve_type)
            self.wn.add_valve(current[0],
                         current[1],
                         current[2],
                         to_si(self.flow_units, float(current[3]), HydParam.PipeDiameter),
                         current[4].upper(),
                         float(current[6]),
                         valve_set)

    def _write_valves(self, f, wn):
        f.write('[VALVES]\n'.encode('ascii'))
        f.write(_VALVE_LABEL.format(';ID', 'Node1', 'Node2', 'Diameter', 'Type', 'Setting', 'Minor Loss').encode('ascii'))
        lnames = list(wn._valves.keys())
        lnames.sort()
        for valve_name in lnames:
            valve = wn._valves[valve_name]
            E = {'name': valve_name,
                 'node1': valve.start_node,
                 'node2': valve.end_node,
                 'diam': from_si(self.flow_units, valve.diameter, HydParam.PipeDiameter),
                 'vtype': valve.valve_type,
                 'set': valve._base_setting,
                 'mloss': valve.minor_loss,
                 'com': ';'}
            valve_type = valve.valve_type
            if valve_type in ['PRV', 'PSV', 'PBV']:
                valve_set = from_si(self.flow_units, valve._base_setting, HydParam.Pressure)
            elif valve_type == 'FCV':
                valve_set = from_si(self.flow_units, valve._base_setting, HydParam.Flow)
            elif valve_type == 'TCV':
                valve_set = valve._base_setting
            elif valve_type == 'GPV':
                valve_set = valve._base_setting
            E['set'] = valve_set
            f.write(_VALVE_ENTRY.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_emitters(self):
        for lnum, line in self.sections['[EMITTERS]']: # Private attribute on junctions
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            junction = self.wn.get_node(current[0])
            junction._emitter_coefficient = to_si(self.flow_units, float(current[1]), HydParam.Flow)

    def _write_emitters(self, f, wn):
        f.write('[EMITTERS]\n'.encode('ascii'))
        entry = '{:10s} {:10s}\n'
        label = '{:10s} {:10s}\n'
        f.write(label.format(';ID', 'Flow coefficient').encode('ascii'))
        njunctions = list(wn._junctions.keys())
        njunctions.sort()
        for junction_name in njunctions:
            junction = wn._junctions[junction_name]
            if junction._emitter_coefficient:
                val = from_si(self.flow_units, junction._emitter_coefficient, HydParam.Flow)
                f.write(entry.format(junction_name, str(val)).encode('ascii'))
        f.write('\n'.encode('ascii'))

    ### System Operation

    def _read_curves(self):
        for lnum, line in self.sections['[CURVES]']:
            # It should be noted carefully that these lines are never directly
            # applied to the WaterNetworkModel object. Because different curve
            # types are treated differently, each of the curves are converted
            # the first time they are used, and this is used to build up a
            # dictionary for those conversions to take place.
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            curve_name = current[0]
            if curve_name not in self.curves:
                self.curves[curve_name] = []
            self.curves[curve_name].append((float(current[1]),
                                             float(current[2])))


    def _write_curves(self, f, wn):
        f.write('[CURVES]\n'.encode('ascii'))
        f.write(_CURVE_LABEL.format(';ID', 'X-Value', 'Y-Value').encode('ascii'))
        for curve_name, curve in wn._curves.items():
            if curve.curve_type == 'VOLUME':
                f.write(';VOLUME: {}\n'.format(curve_name).encode('ascii'))
                for point in curve.points:
                    x = from_si(self.flow_units, point[0], HydParam.Length)
                    y = from_si(self.flow_units, point[1], HydParam.Volume)
                    f.write(_CURVE_ENTRY.format(name=curve_name, x=x, y=y, com=';').encode('ascii'))
            elif curve.curve_type == 'HEAD':
                f.write(';PUMP: {}\n'.format(curve_name).encode('ascii'))
                for point in curve.points:
                    x = from_si(self.flow_units, point[0], HydParam.Flow)
                    y = from_si(self.flow_units, point[1], HydParam.HydraulicHead)
                    f.write(_CURVE_ENTRY.format(name=curve_name, x=x, y=y, com=';').encode('ascii'))
            elif curve.curve_type == 'EFFICIENCY':
                f.write(';EFFICIENCY: {}\n'.format(curve_name).encode('ascii'))
                for point in curve.points:
                    x = from_si(self.flow_units, point[0], HydParam.Flow)
                    y = point[1]
                    f.write(_CURVE_ENTRY.format(name=curve_name, x=x, y=y, com=';').encode('ascii'))
            elif curve.curve_type == 'HEADLOSS':
                f.write(';HEADLOSS: {}\n'.format(curve_name).encode('ascii'))
                for point in curve.points:
                    x = from_si(self.flow_units, point[0], HydParam.Flow)
                    y = from_si(self.flow_units, point[1], HydParam.HeadLoss)
                    f.write(_CURVE_ENTRY.format(name=curve_name, x=x, y=y, com=';').encode('ascii'))
            f.write('\n'.encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_patterns(self):
        _patterns = {}
        for lnum, line in self.sections['[PATTERNS]']:
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

        for pattern_name, pattern_list in _patterns.items():
            self.wn.add_pattern(pattern_name, pattern_list)


    def _write_patterns(self, f, wn):
        num_columns = 8
        f.write('[PATTERNS]\n'.encode('ascii'))
        f.write('{:10s} {:10s}\n'.format(';ID', 'Multipliers').encode('ascii'))
        for pattern_name, pattern in wn._patterns.items():
            count = 0
            for i in pattern:
                if count % num_columns == 0:
                    f.write('\n{:s} {:f}'.format(pattern_name, i).encode('ascii'))
                else:
                    f.write(' {:f}'.format(i).encode('ascii'))
                count += 1
            f.write('\n'.encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_energy(self):
        for lnum, line in self.sections['[ENERGY]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            # Only add head curves for pumps
            if current[0].upper() == 'GLOBAL':
                if current[1].upper() == 'PRICE':
                    self.wn._energy.global_price = float(current[2])
                elif current[1].upper() == 'PATTERN':
                    self.wn._energy.global_pattern = current[2]
                elif current[1].upper() in ['EFFIC', 'EFFICIENCY']:
                    self.wn._energy.global_efficiency = float(current[2])
                else:
                    logger.warning('Unknown entry in ENERGY section: %s', line)
            elif current[0].upper() == 'DEMAND':
                self.wn._energy.demand_charge = float(current[2])
            elif current[0].upper() == 'PUMP':
                pump_name = current[1]
                pump = self.wn._pumps[pump_name]
                if current[2].upper() == 'PRICE':
                    pump._energy_price = float(current[2])
                elif current[2].upper() == 'PATTERN':
                    pump._energy_pat = current[2]
                elif current[2].upper() in ['EFFIC', 'EFFICIENCY']:
                    curve_name = current[3]
                    curve_points = []
                    for point in self.curves[curve_name]:
                        x = to_si(self.flow_units, point[0], HydParam.Flow)
                        y = point[1]
                        curve_points.append((x, y))
                    self.wn.add_curve(curve_name, 'EFFICIENCY', curve_points)
                    curve = self.wn.get_curve(curve_name)
                    pump._efficiency = curve_name
                else:
                    logger.warning('Unknown entry in ENERGY section: %s', line)
            else:
                logger.warning('Unknown entry in ENERGY section: %s', line)

    def _write_energy(self, f, wn):
        f.write('[ENERGY]\n'.encode('ascii'))
        if wn._energy is not None:
            if wn._energy.global_price is not None:
                f.write('GLOBAL PRICE   {:.4f}\n'.format(wn._energy.global_price).encode('ascii'))
            if wn._energy.global_pattern is not None:
                f.write('GLOBAL PATTERN {:s}\n'.format(wn._energy.global_pattern).encode('ascii'))
            if wn._energy.global_efficiency is not None:
                f.write('GLOBAL EFFIC   {:.4f}\n'.format(wn._energy.global_efficiency).encode('ascii'))
            if wn._energy.demand_charge is not None:
                f.write('DEMAND CHARGE  {:.4f}\n'.format(wn._energy.demand_charge).encode('ascii'))
        lnames = list(wn._pumps.keys())
        lnames.sort()
        for pump_name in lnames:
            pump = wn._pumps[pump_name]
            if pump._efficiency is not None:
                f.write('PUMP {:10s} EFFIC   {:s}\n'.format(pump_name, pump._efficiency).encode('ascii'))
            if pump._energy_price is not None:
                f.write('PUMP {:10s} PRICE   {:s}\n'.format(pump_name, pump._energy_price).encode('ascii'))
            if pump._energy_pat is not None:
                f.write('PUMP {:10s} PATTERN {:s}\n'.format(pump_name, pump._energy_pat).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_status(self):
        for lnum, line in self.sections['[STATUS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            assert(len(current) == 2), ("Error reading [STATUS] block, Check format.")
            link = self.wn.get_link(current[0])
            if (current[1].upper() == 'OPEN' or
                    current[1].upper() == 'CLOSED' or
                    current[1].upper() == 'ACTIVE'):
                new_status = LinkStatus[current[1].upper()].value
                link.status = new_status
                link._base_status = new_status
            else:
                if isinstance(link, wntr.network.Valve):
                    if link.valve_type != 'PRV':
                        continue
                    else:
                        setting = to_si(self.flow_units, float(current[2]), HydParam.Pressure)
                        link.setting = setting
                        link._base_setting = setting

    def _write_status(self, f, wn):
        f.write('[STATUS]\n'.encode('ascii'))
        f.write( '{:10s} {:10s}\n'.format(';ID', 'Setting').encode('ascii'))
        for link_name, link in wn.links(Pump):
            if link.get_base_status() == LinkStatus.CLOSED.value:
                f.write('{:10s} {:10s}\n'.format(link_name,
                        LinkStatus(link.get_base_status()).name).encode('ascii'))
        for link_name, link in wn.links(Valve):
            if link.get_base_status() == LinkStatus.CLOSED.value or link.get_base_status() == LinkStatus.Open.value:
                f.write('{:10s} {:10s}\n'.format(link_name,
                        LinkStatus(link.get_base_status()).name).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_controls(self):
        for lnum, line in self.sections['[CONTROLS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            link_name = current[1]
            link = self.wn.get_link(link_name)
            if current[5].upper() != 'TIME' and current[5].upper() != 'CLOCKTIME':
                node_name = current[5]
            current = [i.upper() for i in current]
            current[1] = link_name # don't capitalize the link name

            # Create the control action object

            status = current[2].upper()
            if status == 'OPEN' or status == 'OPENED' or status == 'CLOSED' or status == 'ACTIVE':
                setting = LinkStatus[status].value
                action_obj = wntr.network.ControlAction(link, 'status', setting)
            else:
                if isinstance(link, wntr.network.Pump):
                    action_obj = wntr.network.ControlAction(link, 'speed', float(current[2]))
                elif isinstance(link, wntr.network.Valve):
                    if link.valve_type == 'PRV' or link.valve_type == 'PSV' or link.valve_type == 'PBV':
                        setting = to_si(self.flow_units, float(current[2]), HydParam.Pressure)
                    elif link.valve_type == 'FCV':
                        setting = to_si(self.flow_units, float(current[2]), HydParam.Flow)
                    elif link.valve_type == 'TCV':
                        setting = float(current[2])
                    elif link.valve_type == 'GPV':
                        setting = current[2]
                    else:
                        raise ValueError('Unrecognized valve type {0} while parsing control {1}'.format(link.valve_type, line))
                    action_obj = wntr.network.ControlAction(link, 'setting', setting)
                else:
                    raise RuntimeError(('Links of type {0} can only have controls that change\n'.format(type(link))+
                                        'the link status. Control: {0}'.format(line)))

            # Create the control object
            if 'TIME' not in current and 'CLOCKTIME' not in current:
                if 'IF' in current:
                    node = self.wn.get_node(node_name)
                    if current[6] == 'ABOVE':
                        oper = np.greater
                    elif current[6] == 'BELOW':
                        oper = np.less
                    else:
                        raise RuntimeError("The following control is not recognized: " + line)
                    # OKAY - we are adding in the elevation. This is A PROBLEM
                    # IN THE INP WRITER. Now that we know, we can fix it, but
                    # if this changes, it will affect multiple pieces, just an
                    # FYI.
                    if isinstance(node, wntr.network.Junction):
                        threshold = to_si(self.flow_units,
                                          float(current[7]), HydParam.Pressure) + node.elevation
                    elif isinstance(node, wntr.network.Tank):
                        threshold = to_si(self.flow_units,
                                          float(current[7]), HydParam.Length) + node.elevation
                    control_obj = wntr.network.ConditionalControl((node, 'head'), oper, threshold, action_obj)
                else:
                    raise RuntimeError("The following control is not recognized: " + line)
                control_name = ''
                for i in range(len(current)-1):
                    control_name = control_name + current[i]
                control_name = control_name + str(round(threshold, 2))
            else:
                if len(current) == 6:  # at time
                    if ':' in current[5]:
                        run_at_time = int(_str_time_to_sec(current[5]))
                    else:
                        run_at_time = int(float(current[5])*3600)
                    control_obj = wntr.network.TimeControl(self.wn, run_at_time, 'SIM_TIME', False, action_obj)
                    control_name = ''
                    for i in range(len(current)-1):
                        control_name = control_name + current[i]
                    control_name = control_name + str(run_at_time)
                elif len(current) == 7:  # at clocktime
                    run_at_time = int(_clock_time_to_sec(current[5], current[6]))
                    control_obj = wntr.network.TimeControl(self.wn, run_at_time, 'SHIFTED_TIME', True, action_obj)
            self.wn.add_control(control_name, control_obj)

    def _write_controls(self, f, wn):
        def get_setting(control, control_name):
            value = control._control_action._value
            attribute = control._control_action._attribute.lower()
            if attribute == 'status':
                setting = LinkStatus(value).name
            elif attribute == 'speed':
                setting = str(value)
            elif attribute == 'setting':
                valve = control._control_action._target_obj_ref
                assert isinstance(valve, wntr.network.Valve), 'Could not write control '+str(control_name)
                valve_type = valve.valve_type
                if valve_type == 'PRV' or valve_type == 'PSV' or valve_type == 'PBV':
                    setting = str(from_si(self.flow_units, value, HydParam.Pressure))
                elif valve_type == 'FCV':
                    setting = str(from_si(self.flow_units, value, HydParam.Flow))
                elif valve_type == 'TCV':
                    setting = str(value)
                elif valve_type == 'GPV':
                    setting = value
                else:
                    raise ValueError('Valve type not recognized' + str(valve_type))
            else:
                setting = None
                logger.warning('Could not write control '+str(control_name)+' - skipping')

            return setting

        f.write('[CONTROLS]\n'.encode('ascii'))
        # Time controls and conditional controls only
        for text, all_control in wn._control_dict.items():
            if isinstance(all_control, wntr.network.TimeControl):
                entry = 'Link {link} {setting} AT {compare} {time:g}\n'
                vals = {'link': all_control._control_action._target_obj_ref.name,
                        'setting': get_setting(all_control, text),
                        'compare': 'TIME',
                        'time': all_control._run_at_time / 3600.0}
                if vals['setting'] is None:
                    continue
                if all_control._daily_flag:
                    vals['compare'] = 'CLOCKTIME'
                f.write(entry.format(**vals).encode('ascii'))
            elif isinstance(all_control, wntr.network.ConditionalControl):
                entry = 'Link {link} {setting} IF Node {node} {compare} {thresh}\n'
                vals = {'link': all_control._control_action._target_obj_ref.name,
                        'setting': get_setting(all_control, text),
                        'node': all_control._source_obj.name,
                        'compare': 'above',
                        'thresh': 0.0}
                if vals['setting'] is None:
                    continue
                if all_control._operation is np.less:
                    vals['compare'] = 'below'
                threshold = all_control._threshold - all_control._source_obj.elevation
                vals['thresh'] = from_si(self.flow_units, threshold, HydParam.HydraulicHead)
                f.write(entry.format(**vals).encode('ascii'))
            elif not isinstance(all_control, wntr.network.controls.IfThenElseControl):
                raise RuntimeError('Unknown control for EPANET INP files: %s' % type(all_control))
        f.write('\n'.encode('ascii'))

    def _read_rules(self):
        if len(self.sections['[RULES]']) > 0:
            rules = []
            rule = None
            in_if = False
            in_then = False
            in_else = False
            for lnum, line in self.sections['[RULES]']:
                line = line.split(';')[0]
                words = line.split()
                if words == []:
                    continue
                if len(words) == 0:
                    continue
                if words[0].upper() == 'RULE':
                    if rule is not None:
                        rules.append(rule)
                    rule = _EpanetRule(words[1], self.flow_units, self.mass_units)
                    in_if = False
                    in_then = False
                    in_else = False
                elif words[0].upper() == 'IF':
                    in_if = True
                    in_then = False
                    in_else = False
                    rule.add_if(line)
                elif words[0].upper() == 'THEN':
                    in_if = False
                    in_then = True
                    in_else = False
                    rule.add_then(line)
                elif words[0].upper() == 'ELSE':
                    in_if = False
                    in_then = False
                    in_else = True
                    rule.add_else(line)
                elif words[0].upper() == 'PRIORITY':
                    in_if = False
                    in_then = False
                    in_else = False
                    rule.set_priority(words[1])
                elif in_if:
                    rule.add_if(line)
                elif in_then:
                    rule.add_then(line)
                elif in_else:
                    rule.add_else(line)
                else:
                    continue
            if rule is not None:
                rules.append(rule)
            for rule in rules:
                ctrl = rule.generate_control(self.wn)
                self.wn.add_control(ctrl.name, ctrl)
                logger.debug('Added %s', str(ctrl))
            # wn._en_rules = '\n'.join(self.sections['[RULES]'])
            #logger.warning('RULES are reapplied directly to an Epanet INP file on write; otherwise unsupported.')

    def _write_rules(self, f, wn):
        f.write('[RULES]\n'.encode('ascii'))
        for text, all_control in wn._control_dict.items():
            entry = '{}\n'
            if isinstance(all_control, wntr.network.controls.IfThenElseControl):
                rule = _EpanetRule('blah', self.flow_units, self.mass_units)
                rule.from_if_then_else(all_control)
                f.write(entry.format(str(rule)).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_demands(self):
        demand_num = 0
        for lnum, line in self.sections['[DEMANDS]']: # Private object on the WaterNetweorkModel
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            demand_num = demand_num + 1
            if len(current) == 2:
                self.wn._add_demand('INP'+str(demand_num), current[0],
                                to_si(self.flow_units, float(current[1]), HydParam.Demand),
                                None)
            else:
                self.wn._add_demand('INP'+str(demand_num), current[0],
                                to_si(self.flow_units, float(current[1]), HydParam.Demand),
                                current[2])

    def _write_demands(self, f, wn):
        f.write('[DEMANDS]\n'.encode('ascii'))
        entry = '{:10s} {:10s} {:10s}\n'
        label = '{:10s} {:10s} {:10s}\n'
        f.write(label.format(';ID', 'Demand', 'Pattern').encode('ascii'))
        ndemands = list(wn._demands.keys())
        ndemands.sort()
        for demand_name in ndemands:
            demand = wn._demands[demand_name]
            E = {'node': demand.junction_name,
                 'base': from_si(self.flow_units, demand.base_demand, HydParam.Demand),
                 'pat': ''}
            if demand.demand_pattern_name is not None:
                E['pat'] = demand.demand_pattern_name
            f.write(entry.format(E['node'], str(E['base']), E['pat']).encode('ascii'))
        f.write('\n'.encode('ascii'))

    ### Water Quality

    def _read_quality(self):
        for lnum, line in self.sections['[QUALITY]']: # Private attribute on junctions
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            node = self.wn.get_node(current[0])
            if self.wn.options.quality == 'CHEMICAL':
                quality = to_si(self.flow_units, float(current[1]), QualParam.Concentration, mass_units=self.mass_units)
            elif self.wn.options.quality == 'AGE':
                quality = to_si(self.flow_units, float(current[1]), QualParam.WaterAge)
            else :
                quality = float(current[1])
            node.initial_quality = quality

    def _write_quality(self, f, wn):
        f.write('[QUALITY]\n'.encode('ascii'))
        entry = '{:10s} {:10s}\n'
        label = '{:10s} {:10s}\n'
        nnodes = list(wn._nodes.keys())
        nnodes.sort()
        for node_name in nnodes:
            node = wn._nodes[node_name]
            if node.initial_quality:
                if wn.options.quality == 'CHEMICAL':
                    quality = from_si(self.flow_units, node.initial_quality, QualParam.Concentration, mass_units=self.mass_units)
                elif wn.options.quality == 'AGE':
                    quality = from_si(self.flow_units, node.initial_quality, QualParam.WaterAge)
                else:
                    quality = node.initial_quality
                f.write(entry.format(node_name, str(quality)).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_reactions(self):
        opts = self.wn.options
        BulkReactionCoeff = QualParam.BulkReactionCoeff
        WallReactionCoeff = QualParam.WallReactionCoeff
        for lnum, line in self.sections['[REACTIONS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            assert len(current) == 3, ('INP file option in [REACTIONS] block '
                                       'not recognized: ' + line)
            key1 = current[0].upper()
            key2 = current[1].upper()
            val3 = float(current[2])
            if key1 == 'ORDER':
                if key2 == 'BULK':
                    opts.bulk_rxn_order = int(float(current[2]))
                elif key2 == 'WALL':
                    opts.wall_rxn_order = int(float(current[2]))
                elif key2 == 'TANK':
                    opts.tank_rxn_order = int(float(current[2]))
            elif key1 == 'GLOBAL':
                if key2 == 'BULK':
                    opts.bulk_rxn_coeff = to_si(self.flow_units, val3, BulkReactionCoeff,
                                                mass_units=self.mass_units,
                                                reaction_order=opts.bulk_rxn_order)
                elif key2 == 'WALL':
                    opts.wall_rxn_coeff = to_si(self.flow_units, val3, WallReactionCoeff,
                                                mass_units=self.mass_units,
                                                reaction_order=opts.wall_rxn_order)
            elif key1 == 'BULK':
                pipe = self.wn.get_link(current[1])
                pipe.bulk_rxn_coeff = to_si(self.flow_units, val3, BulkReactionCoeff,
                                            mass_units=self.mass_units,
                                            reaction_order=opts.bulk_rxn_order)
            elif key1 == 'WALL':
                pipe = self.wn.get_link(current[1])
                pipe.wall_rxn_coeff = to_si(self.flow_units, val3, WallReactionCoeff,
                                            mass_units=self.mass_units,
                                            reaction_order=opts.wall_rxn_order)
            elif key1 == 'TANK':
                tank = self.wn.get_node(current[1])
                tank.bulk_rxn_coeff = to_si(self.flow_units, val3, BulkReactionCoeff,
                                            mass_units=self.mass_units,
                                            reaction_order=opts.bulk_rxn_order)
            elif key1 == 'LIMITING':
                opts.limiting_potential = float(current[2])
            elif key1 == 'ROUGHNESS':
                opts.roughness_correlation = float(current[2])
            else:
                raise RuntimeError('Reaction option not recognized: %s'%key1)

    def _write_reactions(self, f, wn):
        f.write( '[REACTIONS]\n'.encode('ascii'))
        entry_int = ' {:s} {:s} {:d}\n'
        entry_float = ' {:s} {:s} {:<10.4f}\n'
        f.write(entry_int.format('ORDER', 'BULK', int(wn.options.bulk_rxn_order)).encode('ascii'))
        f.write(entry_int.format('ORDER', 'WALL', int(wn.options.wall_rxn_order)).encode('ascii'))
        f.write(entry_int.format('ORDER', 'TANK', int(wn.options.tank_rxn_order)).encode('ascii'))
        f.write(entry_float.format('GLOBAL','BULK',
                                   from_si(self.flow_units,
                                           wn.options.bulk_rxn_coeff,
                                           QualParam.BulkReactionCoeff,
                                           mass_units=self.mass_units,
                                           reaction_order=wn.options.bulk_rxn_order)).encode('ascii'))
        f.write(entry_float.format('GLOBAL','WALL',
                                   from_si(self.flow_units,
                                           wn.options.wall_rxn_coeff,
                                           QualParam.WallReactionCoeff,
                                           mass_units=self.mass_units,
                                           reaction_order=wn.options.wall_rxn_order)).encode('ascii'))
        if wn.options.limiting_potential is not None:
            f.write(entry_float.format('LIMITING','POTENTIAL',wn.options.limiting_potential).encode('ascii'))
        if wn.options.roughness_correlation is not None:
            f.write(entry_float.format('ROUGHNESS','CORRELATION',wn.options.roughness_correlation).encode('ascii'))
        for tank_name, tank in wn.nodes(Tank):
            if tank.bulk_rxn_coeff is not None:
                f.write(entry_float.format('TANK',tank_name,
                                           from_si(self.flow_units,
                                                   tank.bulk_rxn_coeff,
                                                   QualParam.BulkReactionCoeff,
                                                   mass_units=self.mass_units,
                                                   reaction_order=wn.options.bulk_rxn_order)).encode('ascii'))
        for pipe_name, pipe in wn.links(Pipe):
            if pipe.bulk_rxn_coeff is not None:
                f.write(entry_float.format('BULK',pipe_name,
                                           from_si(self.flow_units,
                                                   pipe.bulk_rxn_coeff,
                                                   QualParam.BulkReactionCoeff,
                                                   mass_units=self.mass_units,
                                                   reaction_order=wn.options.bulk_rxn_order)).encode('ascii'))
            if pipe.wall_rxn_coeff is not None:
                f.write(entry_float.format('WALL',pipe_name,
                                           from_si(self.flow_units,
                                                   pipe.wall_rxn_coeff,
                                                   QualParam.WallReactionCoeff,
                                                   mass_units=self.mass_units,
                                                   reaction_order=wn.options.wall_rxn_order)).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_sources(self):
        source_num = 0
        for lnum, line in self.sections['[SOURCES]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            assert(len(current) >= 3), ("Error reading sources. Check format.")
            source_num = source_num + 1
            if current[0].upper() == 'MASS':
                strength = to_si(self.flow_units, float(current[2]), QualParam.SourceMassInject, self.mass_units)
            else:
                strength = to_si(self.flow_units, float(current[2]), QualParam.Concentration, self.mass_units)
            if len(current) == 3:
                self.wn.add_source('INP'+str(source_num), current[0], current[1], strength, None)
            else:
                self.wn.add_source('INP'+str(source_num), current[0], current[1], strength,  current[3])


    def _write_sources(self, f, wn):
        f.write('[SOURCES]\n'.encode('ascii'))
        entry = '{:10s} {:10s} {:10s} {:10s}\n'
        label = '{:10s} {:10s} {:10s} {:10s}\n'
        f.write(label.format(';Node', 'Type', 'Quality', 'Pattern').encode('ascii'))
        nsources = list(wn._sources.keys())
        nsources.sort()
        for source_name in nsources:
            source = wn._sources[source_name]

            if source.source_type.upper() == 'MASS':
                strength = from_si(self.flow_units, source.quality, QualParam.SourceMassInject, self.mass_units)
            else: # CONC, SETPOINT, FLOWPACED
                strength = from_si(self.flow_units, source.quality, QualParam.Concentration, self.mass_units)

            E = {'node': source.node_name,
                 'type': source.source_type,
                 'quality': str(strength),
                 'pat': ''}
            if source.pattern_name is not None:
                E['pat'] = source.pattern_name
            f.write(entry.format(E['node'], E['type'], str(E['quality']), E['pat']).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_mixing(self):
        for lnum, line in self.sections['[MIXING]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            key = current[1].upper()
            tank_name = current[0]
            tank = self.wn.get_node(tank_name)
            if key == 'MIXED':
                tank._mix_model = MixType.Mix1
            elif key == '2COMP' and len(current) > 2:
                tank._mix_model = MixType.Mix2
                tank._mix_frac = float(current[2])
            elif key == '2COMP' and len(current) < 3:
                raise RuntimeError('Mixing model 2COMP requires fraction on tank %s'%tank_name)
            elif key == 'FIFO':
                tank._mix_model = MixType.FIFO
            elif key == 'LIFO':
                tank._mix_model = MixType.LIFO

    def _write_mixing(self, f, wn):
        f.write('[MIXING]\n'.encode('ascii'))
        f.write('{:20s} {:5s} {}\n'.format(';Tank ID', 'Model', 'Fraction').encode('ascii'))
        lnames = list(wn._tanks.keys())
        lnames.sort()
        for tank_name in lnames:
            tank = wn._tanks[tank_name]
            if tank._mix_model is not None:
                if tank._mix_model in [MixType.Mixed, MixType.Mix1, 0]:
                    f.write(' {:19s} MIXED\n'.format(tank_name).encode('ascii'))
                elif tank._mix_model in [MixType.TwoComp, MixType.Mix2, '2comp', '2COMP', 1]:
                    f.write(' {:19s} 2COMP  {}\n'.format(tank_name, tank._mix_frac).encode('ascii'))
                elif tank._mix_model in [MixType.FIFO, 2]:
                    f.write(' {:19s} FIFO\n'.format(tank_name).encode('ascii'))
                elif tank._mix_model in [MixType.LIFO, 3]:
                    f.write(' {:19s} LIFO\n'.format(tank_name).encode('ascii'))
                elif isinstance(tank._mix_model, str) and tank._mix_frac is not None:
                    f.write(' {:19s} {} {}\n'.format(tank_name, tank._mix_model, tank._mix_frac).encode('ascii'))
                elif isinstance(tank._mix_model, str):
                    f.write(' {:19s} {}\n'.format(tank_name, tank._mix_model).encode('ascii'))
                else:
                    logger.warning('Unknown mixing model: %s', tank._mix_model)
        f.write('\n'.encode('ascii'))

    ### Options and Reporting

    def _read_options(self):
        edata = {}
        wn = self.wn
        opts = wn.options
        for lnum, line in self.sections['[OPTIONS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[OPTIONS]'
            words, comments = _split_line(line)
            if words is not None and len(words) > 0:
                if len(words) < 2:
                    edata['key'] = words[0]
                    raise RuntimeError('%(fname)s:%(lnum)-6d %(sec)13s no value provided for %(key)s' % edata)
                key = words[0].upper()
                if key == 'UNITS':
                    self.flow_units = FlowUnits[words[1].upper()]
                    opts.units = words[1].upper()
                elif key == 'HEADLOSS':
                    opts.headloss = words[1].upper()
                elif key == 'HYDRAULICS':
                    opts.hydraulics = words[1].upper()
                    opts.hydraulics_filename = words[2]
                elif key == 'QUALITY':
                    opts.quality = words[1].upper()
                    if len(words) > 2:
                        opts.quality_value = words[2]
                        if 'ug' in words[2]:
                            self.mass_units = MassUnits.mg
                        else:
                            self.mass_units = MassUnits.ug
                    else:
                        self.mass_units = MassUnits.mg
                        opts.quality_value = 'mg/L'
                elif key == 'VISCOSITY':
                    opts.viscosity = float(words[1])
                elif key == 'DIFFUSIVITY':
                    opts.diffusivity = float(words[1])
                elif key == 'SPECIFIC':
                    opts.specific_gravity = float(words[2])
                elif key == 'TRIALS':
                    opts.trials = int(words[1])
                elif key == 'ACCURACY':
                    opts.accuracy = float(words[1])
                elif key == 'UNBALANCED':
                    opts.unbalanced = words[1].upper()
                    if len(words) > 2:
                        opts.unbalanced_value = int(words[2])
                elif key == 'PATTERN':
                    opts.pattern = words[1]
                elif key == 'DEMAND':
                    if len(words) > 2:
                        opts.demand_multiplier = float(words[2])
                    else:
                        edata['key'] = 'DEMAND MULTIPLIER'
                        raise RuntimeError('%(fname)s:%(lnum)-6d %(sec)13s no value provided for %(key)s' % edata)
                elif key == 'EMITTER':
                    if len(words) > 2:
                        opts.emitter_exponent = float(words[2])
                    else:
                        edata['key'] = 'EMITTER EXPONENT'
                        raise RuntimeError('%(fname)s:%(lnum)-6d %(sec)13s no value provided for %(key)s' % edata)
                elif key == 'TOLERANCE':
                    opts.tolerance = float(words[1])
                elif key == 'CHECKFREQ':
                    opts.checkfreq = float(words[1])
                elif key == 'MAXCHECK':
                    opts.maxcheck = float(words[1])
                elif key == 'DAMPLIMIT':
                    opts.damplimit = float(words[1])
                elif key == 'MAP':
                    opts.map = words[1]
                else:
                    if len(words) == 2:
                        edata['key'] = words[0]
                        setattr(opts, words[0].lower(), float(words[1]))
                        logger.warn('%(fname)s:%(lnum)-6d %(sec)13s option "%(key)s" is undocumented; adding, but please verify syntax', edata)
                    elif len(words) == 3:
                        edata['key'] = words[0] + ' ' + words[1]
                        setattr(opts, words[0].lower() + '_' + words[1].lower(), float(words[2]))
                        logger.warn('%(fname)s:%(lnum)-6d %(sec)13s option "%(key)s" is undocumented; adding, but please verify syntax', edata)
        if (type(opts.report_timestep) == float or
                type(opts.report_timestep) == int):
            if opts.report_timestep < opts.hydraulic_timestep:
                raise RuntimeError('opts.report_timestep must be greater than or equal to opts.hydraulic_timestep.')
            if opts.report_timestep % opts.hydraulic_timestep != 0:
                raise RuntimeError('opts.report_timestep must be a multiple of opts.hydraulic_timestep')


    def _write_options(self, f, wn):
        f.write('[OPTIONS]\n'.encode('ascii'))
        entry_string = '{:20s} {:20s}\n'
        entry_float = '{:20s} {:g}\n'
        f.write(entry_string.format('UNITS', self.flow_units.name).encode('ascii'))
        f.write(entry_string.format('HEADLOSS', wn.options.headloss).encode('ascii'))
        if wn.options.hydraulics is not None:
            f.write('{:20s} {:s} {:<30s}\n'.format('HYDRAULICS', wn.options.hydraulics, wn.options.hydraulics_filename).encode('ascii'))
        if wn.options.quality_value is None:
            f.write(entry_string.format('QUALITY', wn.options.quality).encode('ascii'))
        else:
            f.write('{:20s} {} {}\n'.format('QUALITY', wn.options.quality, wn.options.quality_value).encode('ascii'))
        f.write(entry_float.format('VISCOSITY', wn.options.viscosity).encode('ascii'))
        f.write(entry_float.format('DIFFUSIVITY', wn.options.diffusivity).encode('ascii'))
        f.write(entry_float.format('SPECIFIC GRAVITY', wn.options.specific_gravity).encode('ascii'))
        f.write(entry_float.format('TRIALS', wn.options.trials).encode('ascii'))
        f.write(entry_float.format('ACCURACY', wn.options.accuracy).encode('ascii'))
        f.write(entry_float.format('CHECKFREQ', wn.options.checkfreq).encode('ascii'))
        if wn.options.unbalanced_value is None:
            f.write(entry_string.format('UNBALANCED', wn.options.unbalanced).encode('ascii'))
        else:
            f.write('{:20s} {:s} {:d}\n'.format('UNBALANCED', wn.options.unbalanced, wn.options.unbalanced_value).encode('ascii'))
        if wn.options.pattern is not None:
            f.write(entry_string.format('PATTERN', wn.options.pattern).encode('ascii'))
        f.write(entry_float.format('DEMAND MULTIPLIER', wn.options.demand_multiplier).encode('ascii'))
        f.write(entry_float.format('EMITTER EXPONENT', wn.options.emitter_exponent).encode('ascii'))
        f.write(entry_float.format('TOLERANCE', wn.options.tolerance).encode('ascii'))
        if wn.options.map is not None:
            f.write(entry_string.format('MAP', wn.options.map).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_times(self):
        opts = self.wn.options
        time_format = ['am', 'AM', 'pm', 'PM']
        for lnum, line in self.sections['[TIMES]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if (current[0].upper() == 'DURATION'):
                opts.duration = _str_time_to_sec(current[1])
            elif (current[0].upper() == 'HYDRAULIC'):
                opts.hydraulic_timestep = _str_time_to_sec(current[2])
            elif (current[0].upper() == 'QUALITY'):
                opts.quality_timestep = _str_time_to_sec(current[2])
            elif (current[1].upper() == 'CLOCKTIME'):
                [time, time_format] = [current[2], current[3].upper()]
                opts.start_clocktime = _clock_time_to_sec(time, time_format)
            elif (current[0].upper() == 'STATISTIC'):
                opts.statistic = current[1].upper()
            else:
                # Other time options: RULE TIMESTEP, PATTERN TIMESTEP, REPORT TIMESTEP, REPORT START
                key_string = current[0] + '_' + current[1]
                setattr(opts, key_string.lower(), _str_time_to_sec(current[2]))

    def _write_times(self, f, wn):
        f.write('[TIMES]\n'.encode('ascii'))
        entry = '{:20s} {:10s}\n'
        time_entry = '{:20s} {:02d}:{:02d}:{:02d}\n'
        hrs, mm, sec = _sec_to_string(wn.options.duration)
        f.write(time_entry.format('DURATION', hrs, mm, sec).encode('ascii'))
        hrs, mm, sec = _sec_to_string(wn.options.hydraulic_timestep)
        f.write(time_entry.format('HYDRAULIC TIMESTEP', hrs, mm, sec).encode('ascii'))
        hrs, mm, sec = _sec_to_string(wn.options.pattern_timestep)
        f.write(time_entry.format('PATTERN TIMESTEP', hrs, mm, sec).encode('ascii'))
        hrs, mm, sec = _sec_to_string(wn.options.pattern_start)
        f.write(time_entry.format('PATTERN START', hrs, mm, sec).encode('ascii'))
        hrs, mm, sec = _sec_to_string(wn.options.report_timestep)
        f.write(time_entry.format('REPORT TIMESTEP', hrs, mm, sec).encode('ascii'))
        hrs, mm, sec = _sec_to_string(wn.options.report_start)
        f.write(time_entry.format('REPORT START', hrs, mm, sec).encode('ascii'))

        hrs, mm, sec = _sec_to_string(wn.options.start_clocktime)
        if hrs < 12:
            time_format = ' AM'
        else:
            hrs -= 12
            time_format = ' PM'
        f.write('{:20s} {:02d}:{:02d}:{:02d}{:s}\n'.format('START CLOCKTIME', hrs, mm, sec, time_format).encode('ascii'))

        hrs, mm, sec = _sec_to_string(wn.options.quality_timestep)
        f.write(time_entry.format('QUALITY TIMESTEP', hrs, mm, sec).encode('ascii'))
        hrs, mm, sec = _sec_to_string(wn.options.rule_timestep)

        ### TODO: RULE TIMESTEP is not written?!
        # f.write(time_entry.format('RULE TIMESTEP', hrs, mm, int(sec)).encode('ascii'))
        f.write(entry.format('STATISTIC', wn.options.statistic).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_report(self):
        report = wntr.network.model._Report()
        self.wn._reportopts = report
        for lnum, line in self.sections['[REPORT]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if current[0].upper() in ['PAGE', 'PAGESIZE']:
                report.pagesize = int(current[1])
            elif current[0].upper() in ['FILE']:
                report.file = current[1]
            elif current[0].upper() in ['STATUS']:
                report.status = current[1].upper()
            elif current[0].upper() in ['SUMMARY']:
                report.summary = current[1].upper()
            elif current[0].upper() in ['ENERGY']:
                report.energy = current[1].upper()
            elif current[0].upper() in ['NODES']:
                if current[1].upper() in ['NONE']:
                    report.nodes = False
                elif current[1].upper() in ['ALL']:
                    report.nodes = True
                elif not isinstance(report.nodes, list):
                    report.nodes = []
                    for ct in xrange(len(current)-2):
                        i = ct + 2
                        report.nodes.append(current[i])
                else:
                    for ct in xrange(len(current)-2):
                        i = ct + 2
                        report.nodes.append(current[i])
            elif current[0].upper() in ['LINKS']:
                if current[1].upper() in ['NONE']:
                    report.links = False
                elif current[1].upper() in ['ALL']:
                    report.links = True
                elif not isinstance(report.links, list):
                    report.links = []
                    for ct in xrange(len(current)-2):
                        i = ct + 2
                        report.links.append(current[i])
                else:
                    for ct in xrange(len(current)-2):
                        i = ct + 2
                        report.links.append(current[i])
            else:
                if current[0].lower() not in report.rpt_params.keys():
                    logger.warning('Unknown report parameter: %s', current[0])
                    continue
                elif current[1].upper() in ['YES']:
                    report.rpt_params[current[0].lower()][1] = True
                elif current[1].upper() in ['NO']:
                    report.rpt_params[current[0].lower()][1] = False
                else:
                    report.param_opts[current[0].lower()][current[1].upper()] = float(current[2])

    def _write_report(self, f, wn):
        f.write('[REPORT]\n'.encode('ascii'))
        if hasattr(wn, '_reportopts') and wn._reportopts is not None:
            report = wn._reportopts
            if report.pagesize != 0:
                f.write('PAGESIZE   {}\n'.format(report.pagesize).encode('ascii'))
            if report.file is not None:
                f.write('FILE       {}\n'.format(report.file).encode('ascii'))
            if report.status.upper() != 'NO':
                f.write('STATUS     {}\n'.format(report.status).encode('ascii'))
            if report.summary.upper() != 'YES':
                f.write('SUMMARY    {}\n'.format(report.summary).encode('ascii'))
            if report.energy.upper() != 'NO':
                f.write('STATUS     {}\n'.format(report.status).encode('ascii'))
            if report.nodes is True:
                f.write('NODES      ALL\n'.encode('ascii'))
            elif isinstance(report.nodes, str):
                f.write('NODES      {}\n'.format(report.nodes).encode('ascii'))
            elif isinstance(report.nodes, list):
                for ct, node in enumerate(report.nodes):
                    if ct == 0:
                        f.write('NODES      {}'.format(node).encode('ascii'))
                    elif ct % 10 == 0:
                        f.write('\nNODES      {}'.format(node).encode('ascii'))
                    else:
                        f.write(' {}'.format(node).encode('ascii'))
                f.write('\n'.encode('ascii'))
            if report.links is True:
                f.write('LINKS      ALL\n'.encode('ascii'))
            elif isinstance(report.links, str):
                f.write('LINKS      {}\n'.format(report.links).encode('ascii'))
            elif isinstance(report.links, list):
                for ct, link in enumerate(report.links):
                    if ct == 0:
                        f.write('LINKS      {}'.format(link).encode('ascii'))
                    elif ct % 10 == 0:
                        f.write('\nLINKS      {}'.format(link).encode('ascii'))
                    else:
                        f.write(' {}'.format(link).encode('ascii'))
                f.write('\n'.encode('ascii'))
            for key, item in report.rpt_params.items():
                if item[1] != item[0]:
                    f.write('{:10s} {}\n'.format(key.upper(), item[1]).encode('ascii'))
            for key, item in report.param_opts.items():
                for opt, val in item.items():
                    f.write('{:10s} {:10s} {}\n'.format(key.upper(), opt.upper(), val).encode('ascii'))

        f.write('\n'.encode('ascii'))

    ### Network Map/Tags

    def _read_coordinates(self):
        for lnum, line in self.sections['[COORDINATES]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            assert(len(current) == 3), ("Error reading node coordinates. Check format.")
            self.wn.set_node_coordinates(current[0], (float(current[1]), float(current[2])))

    def _write_coordinates(self, f, wn):
        f.write('[COORDINATES]\n'.encode('ascii'))
        entry = '{:10s} {:10g} {:10g}\n'
        label = '{:10s} {:10s} {:10s}\n'
        f.write(label.format(';Node', 'X-Coord', 'Y-Coord').encode('ascii'))
        coord = nx.get_node_attributes(wn._graph, 'pos')
        for key, val in coord.items():
            f.write(entry.format(key, val[0], val[1]).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_vertices(self):
        for lnum, line in self.sections['[VERTICES]']:
            line = line.split(';')[0].strip()
            current = line.split()
            if current == []:
                continue
            if len(current) != 3:
                logger.warning('Invalid VERTICES line: %s', line)
                continue
            link_name = current[0]
            link = self.wn.get_link(link_name)
            link._vertices.append((float(current[1]), float(current[2])))

    def _write_vertices(self, f, wn):
        f.write('[VERTICES]\n'.encode('ascii'))
        entry = '{:10s} {:10g} {:10g}\n'
        label = '{:10s} {:10s} {:10s}\n'
        f.write(label.format(';Link', 'X-Coord', 'Y-Coord').encode('ascii'))
        lnames = list(wn._pipes.keys())
        lnames.sort()
        for pipe_name in lnames:
            pipe = wn._pipes[pipe_name]
            for vert in pipe._vertices:
                f.write(entry.format(pipe_name, vert[0], vert[1]).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_labels(self):
        labels = []
        for lnum, line in self.sections['[LABELS]']:
            line = line.split(';')[0].strip()
            current = line.split()
            if current == []:
                continue
            labels.append(line)
        self.wn._labels = labels

    def _write_labels(self, f, wn):
        f.write('[LABELS]\n'.encode('ascii'))
        if wn._labels is not None:
            for label in wn._labels:
                f.write(' {}\n'.format(label).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_backdrop(self):
        for lnum, line in self.sections['[BACKDROP]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            key = current[0].upper()
            if key == 'DIMENSIONS' and len(current) > 4:
                self.wn._backdrop.dimensions = [current[1], current[2], current[3], current[4]]
            elif key == 'UNITS' and len(current) > 1:
                self.wn._backdrop.units = current[1]
            elif key == 'FILE' and len(current) > 1:
                self.wn._backdrop.filename = current[1]
            elif key == 'OFFSET' and len(current) > 2:
                self.wn._backdrop.offset = [current[1], current[2]]

    def _write_backdrop(self, f, wn):
        if wn._backdrop is not None:
            f.write('[BACKDROP]\n'.encode('ascii'))
            f.write('{}'.format(wn._backdrop).encode('ascii'))
            f.write('\n'.encode('ascii'))

    def _read_tags(self):
        for lnum, line in self.sections['[TAGS]']: # Private attribute on nodes and links
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if current[0] == 'NODE':
                node = self.wn.get_node(current[1])
                node.tag = current[2]
            elif current[0] == 'LINK':
                link = self.wn.get_link(current[1])
                link.tag = current[2]
            else:
                continue

    def _write_tags(self, f, wn):
        f.write('[TAGS]\n'.encode('ascii'))
        entry = '{:10s} {:10s} {:10s}\n'
        label = '{:10s} {:10s} {:10s}\n'
        f.write(label.format(';type', 'name', 'tag').encode('ascii'))
        nnodes = list(wn._nodes.keys())
        nnodes.sort()
        for node_name in nnodes:
            node = wn._nodes[node_name]
            if node.tag:
                f.write(entry.format('NODE', node_name, node.tag).encode('ascii'))
        nlinks = list(wn._links.keys())
        nlinks.sort()
        for link_name in nlinks:
            link = wn._links[link_name]
            if link.tag:
                f.write(entry.format('LINK', link_name, link.tag).encode('ascii'))
        f.write('\n'.encode('ascii'))

    ### End of File

    def _write_end(self, f, wn):
        f.write('[END]\n'.encode('ascii'))


class _EpanetRule(object):
    """contains the text for an EPANET rule"""
    def __init__(self, ruleID, inp_units=None, mass_units=None):
        self.inp_units = inp_units
        self.mass_units = mass_units
        self.ruleID = ruleID
        self._if_clauses = []
        self._then_clauses = []
        self._else_clauses = []
        self.priority = 0

    def from_if_then_else(self, control):
        """Create a rule from an IfThenElseControl object"""
        if isinstance(control, IfThenElseControl):
            self.ruleID = control.name
            self.add_control_condition(control._condition)
            for ct, action in enumerate(control._then_actions):
                if ct == 0:
                    self.add_action_on_true(action)
                else:
                    self.add_action_on_true(action, '  AND')
            for ct, action in enumerate(control._else_actions):
                if ct == 0:
                    self.add_action_on_false(action)
                else:
                    self.add_action_on_false(action, '  AND')
            self.set_priority(control._priority)
        else:
            raise ValueError('Invalid control type for rules: %s'%control.__class__.__name__)

    def add_if(self, clause):
        """Add an "if/and/or" clause from an INP file"""
        self._if_clauses.append(clause)

    def add_control_condition(self, condition, prefix=' IF'):
        """Add a ControlCondition from an IfThenElseControl"""
        if isinstance(condition, OrCondition):
            self.add_control_condition(condition._condition_1, prefix)
            self.add_control_condition(condition._condition_2, '  OR')
        elif isinstance(condition, AndCondition):
            self.add_control_condition(condition._condition_1, prefix)
            self.add_control_condition(condition._condition_2, '  AND')
        elif isinstance(condition, TimeOfDayCondition):
            fmt = '{} SYSTEM CLOCKTIME {} {}'
            clause = fmt.format(prefix, condition._relation.text, condition._sec_to_clock(condition._threshold))
            self.add_if(clause)
        elif isinstance(condition, SimTimeCondition):
            fmt = '{} SYSTEM TIME {} {}'
            clause = fmt.format(prefix, condition._relation.text, condition._sec_to_hours_min_sec(condition._threshold))
            self.add_if(clause)
        elif isinstance(condition, ValueCondition):
            fmt = '{} {} {} {} {} {}'  # CONJ, TYPE, ID, ATTRIBUTE, RELATION, THRESHOLD
            attr = condition._source_attr
            val_si = condition._repr_value(attr, condition._threshold)
            if attr.lower() in ['demand']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Demand))
            elif attr.lower() in ['head', 'level']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.HydraulicHead))
            elif attr.lower() in ['flow']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Flow))
            elif attr.lower() in ['pressure']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Flow))
            elif attr.lower() in ['setting']:
                value = '{:.6g}'.format(val_si)
            else: # status
                value = val_si
            clause = fmt.format(prefix, condition._source_obj.__class__.__name__,
                                condition._source_obj.name, condition._source_attr,
                                condition._relation.symbol, value)
            self.add_if(clause)
        else:
            raise ValueError('Unknown ControlCondition for EPANET Rules')

    def add_then(self, clause):
        """Add a "then/and" clause from an INP file"""
        self._then_clauses.append(clause)

    def add_action_on_true(self, action, prefix=' THEN'):
        """Add a "then" action from an IfThenElseControl"""
        if isinstance(action, ControlAction):
            fmt = '{} {} {} {} = {}'
            attr = action._attribute
            val_si = action._repr_value()
            if attr.lower() in ['demand']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Demand))
            elif attr.lower() in ['head', 'level']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.HydraulicHead))
            elif attr.lower() in ['flow']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Flow))
            elif attr.lower() in ['pressure']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Flow))
            elif attr.lower() in ['setting']:
                value = '{:.6g}'.format(val_si)
            else: # status
                value = val_si
            clause = fmt.format(prefix, action._target_obj_ref.__class__.__name__,
                                action._target_obj_ref.name, action._attribute,
                                value)
            self.add_then(clause)

    def add_else(self, clause):
        """Add an "else/and" clause from an INP file"""
        self._else_clauses.append(clause)

    def add_action_on_false(self, action, prefix=' ELSE'):
        """Add an "else" action from an IfThenElseControl"""
        if isinstance(action, ControlAction):
            fmt = '{} {} {} {} = {}'
            attr = action._attribute
            val_si = action._repr_value()
            if attr.lower() in ['demand']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Demand))
            elif attr.lower() in ['head', 'level']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.HydraulicHead))
            elif attr.lower() in ['flow']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Flow))
            elif attr.lower() in ['pressure']:
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Flow))
            elif attr.lower() in ['setting']:
                value = '{:.6g}'.format(val_si)
            else: # status
                value = val_si
            clause = fmt.format(prefix, action._target_obj_ref.__class__.__name__,
                                action._target_obj_ref.name, action._attribute,
                                value)
            self.add_else(clause)

    def set_priority(self, priority):
        self.priority = int(priority)

    def __str__(self):
        if self.priority >= 0:
            if len(self._else_clauses) > 0:
                return 'RULE {}\n{}\n{}\n{}\nPRIORITY {}\n; end of rule\n'.format(self.ruleID, '\n'.join(self._if_clauses), '\n'.join(self._then_clauses), '\n'.join(self._else_clauses), self.priority)
            else:
                return 'RULE {}\n{}\n{}\nPRIORITY {}\n; end of rule\n'.format(self.ruleID, '\n'.join(self._if_clauses), '\n'.join(self._then_clauses), self.priority)
        else:
            if len(self._else_clauses) > 0:
                return 'RULE {}\n{}\n{}\n{}\n; end of rule\n'.format(self.ruleID, '\n'.join(self._if_clauses), '\n'.join(self._then_clauses), '\n'.join(self._else_clauses))
            else:
                return 'RULE {}\n{}\n{}\n; end of rule\n'.format(self.ruleID, '\n'.join(self._if_clauses), '\n'.join(self._then_clauses))

    def generate_control(self, model):
        condition_list = []
        for line in self._if_clauses:
            condition = None
            words = line.split()
            if words[1].upper() == 'SYSTEM':
                if words[2].upper() == 'DEMAND':
                    ### TODO: system demand
                    pass
                elif words[2].upper() == 'TIME':
                    condition = SimTimeCondition(model, words[3], ' '.join(words[4:]))
                else:
                    condition = TimeOfDayCondition(model, words[3], ' '.join(words[4:]))
            else:
                attr = words[3].lower()
                value = ValueCondition._parse_value(words[5])
                if attr.lower() in ['demand']:
                    value = to_si(self.inp_units, value, HydParam.Demand)
                elif attr.lower() in ['head', 'level']:
                    value = to_si(self.inp_units, value, HydParam.HydraulicHead)
                elif attr.lower() in ['flow']:
                    value = to_si(self.inp_units, value, HydParam.Flow)
                elif attr.lower() in ['pressure']:
                    value = to_si(self.inp_units, value, HydParam.Flow)
                if words[1].upper() in ['NODE', 'JUNCTION', 'RESERVOIR', 'TANK']:
                    condition = ValueCondition(model.get_node(words[2]), words[3].lower(), words[4].lower(), value)
                elif words[1].upper() in ['LINK', 'PIPE', 'PUMP', 'VALVE']:
                    condition = ValueCondition(model.get_link(words[2]), words[3].lower(), words[4].lower(), value)
                else:
                    ### FIXME: raise error
                    pass
            if words[0].upper() == 'IF':
                condition_list.append(condition)
            elif words[0].upper() == 'AND':
                condition_list.append(condition)
            elif words[0].upper() == 'OR':
                if len(condition_list) > 0:
                    other = condition_list[-1]
                    condition_list.remove(other)
                else:
                    ### FIXME: raise error
                    pass
                conj = OrCondition(other, condition)
                condition_list.append(conj)
        final_condition = None
        for condition in condition_list:
            if final_condition is None:
                final_condition = condition
            else:
                final_condition = AndCondition(final_condition, condition)
        then_acts = []
        for act in self._then_clauses:
            words = act.strip().split()
            if len(words) < 6:
                # TODO: raise error
                pass
            link = model.get_link(words[2])
            attr = words[3].lower()
            value = ValueCondition._parse_value(words[5])
            if attr.lower() in ['demand']:
                value = to_si(self.inp_units, value, HydParam.Demand)
            elif attr.lower() in ['head', 'level']:
                value = to_si(self.inp_units, value, HydParam.HydraulicHead)
            elif attr.lower() in ['flow']:
                value = to_si(self.inp_units, value, HydParam.Flow)
            elif attr.lower() in ['pressure']:
                value = to_si(self.inp_units, value, HydParam.Flow)
            then_acts.append(ControlAction(link, attr, value))
        else_acts = []
        for act in self._else_clauses:
            words = act.strip().split()
            if len(words) < 6:
                # TODO: raise error
                pass
            link = model.get_link(words[2])
            attr = words[3].lower()
            value = ValueCondition._parse_value(words[5])
            if attr.lower() in ['demand']:
                value = to_si(self.inp_units, value, HydParam.Demand)
            elif attr.lower() in ['head', 'level']:
                value = to_si(self.inp_units, value, HydParam.HydraulicHead)
            elif attr.lower() in ['flow']:
                value = to_si(self.inp_units, value, HydParam.Flow)
            elif attr.lower() in ['pressure']:
                value = to_si(self.inp_units, value, HydParam.Flow)
            else_acts.append(ControlAction(link, attr, value))
        return IfThenElseControl(final_condition, then_acts, else_acts, priority=self.priority, name=self.ruleID)



class BinFile(object):
    """
    Read an EPANET 2.x binary output file.

    Abstract class, does not save any of the data read, simply calls the
    abstract functions at the appropriate times.

    Parameters
    ----------
    results_type : list of ~wntr.epanet.util.ResultType
        If ``None``, then all results will be saved (node quality, demand, link flow, etc.).
        Otherwise, a list of result types can be passed to limit the memory used. This can
        also be specified in a save_results_line call, but will default to this list.
    network : bool
        Save a new WaterNetworkModel from the description in the output binary file. Certain
        elements may be missing, such as patterns and curves, if this is done.
    energy : bool
        Save the pump energy results.
    statistics : bool
        Save the statistics lines (different from the stats flag in the inp file) that are
        automatically calculated regarding hydraulic conditions.

    Attributes
    ----------
    results : :class:`~wntr.sim.results.NetResults`
        A WNTR results object will be created and added to the instance after read.


    """
    def __init__(self, result_types=None, network=False, energy=False, statistics=False):
        if os.name in ['nt', 'dos'] or sys.platform in ['darwin']:
            self.ftype = '=f4'
        else:
            self.ftype = '=f4'
        self.idlen = 32
        self.hydraulic_id = None
        self.quality_id = None
        self.node_names = None
        self.link_names = None
        self.report_times = None
        self.flow_units = None
        self.pres_units = None
        self.mass_units = None
        self.quality_type = None
        self.num_nodes = None
        self.num_tanks = None
        self.num_links = None
        self.num_pumps = None
        self.num_valves = None
        self.report_start = None
        self.report_step = None
        self.duration = None
        self.chemical = None
        self.chem_units = None
        self.inp_file = None
        self.rpt_file = None
        self.results = wntr.sim.NetResults()
        if result_types is None:
            self.items = [ member for name, member in ResultType.__members__.items() ]
        else:
            self.items = result_types
        self.create_network = network
        self.keep_energy = energy
        self.keep_statistics = statistics

    def setup_ep_results(self, times, nodes, links, result_types=None):
        """Set up the results object (or file, etc.) for save_ep_line() calls to use.

        The basic implementation sets up a dictionary of pandas DataFrames with the keys
        being member names of the ResultsType class. If the items parameter is left blank,
        the function will use the items that were specified during object creation.
        If this too, was blank, then all results parameters will be saved.

        """
        if result_types is None:
            result_types = self.items
        link_items = [ member.name for member in result_types if member.is_link ]
        node_items = [ member.name for member in result_types if member.is_node ]
        self.results.node = pd.Panel(items=node_items, major_axis=times, minor_axis=nodes)
        self.results.link = pd.Panel(items=link_items, major_axis=times, minor_axis=links)
        self.results.time = times
        self.results.network_name = self.inp_file

    def save_ep_line(self, period, result_type, values):
        """
        Save an extended period set of values.

        Each report period contains all the hydraulics and quality values for
        the nodes and links. Nodes and link values are provided in the same
        order as the names are specified in the prolog.

        The result types for node data are: :attr:`ResultType.demand`, :attr:`ResultType.head`,
        :attr:`ResultType.pressure` and :attr:`ResultType.quality`.

        The result types for link data are: :attr:`ResultType.linkquality`,
        :attr:`ResultType.flowrate`, and :attr:`ResultType.velocity`.

        Parameters
        ----------
        period : int
            the report period
        result_type : str
            one of the type strings listed above
        values : numpy.array
            the values to save, in the node or link order specified earlier in the file

        """
        if result_type in [ResultType.quality, ResultType.linkquality]:
            if self.quality_type is QualType.Chem:
                values = QualParam.Concentration._to_si(self.flow_units, values, mass_units=self.mass_units)
            elif self.quality_type is QualType.Age:
                values = QualParam.WaterAge._to_si(self.flow_units, values)
        elif result_type == ResultType.demand:
            values = HydParam.Demand._to_si(self.flow_units, values)
        elif result_type == ResultType.flowrate:
            values = HydParam.Flow._to_si(self.flow_units, values)
        elif result_type in [ResultType.head, ResultType.headloss]:
            values = HydParam.HydraulicHead._to_si(self.flow_units, values)
        elif result_type == ResultType.pressure:
            values = HydParam.Pressure._to_si(self.flow_units, values)
        elif result_type == ResultType.velocity:
            values = HydParam.Velocity._to_si(self.flow_units, values)
        if result_type in self.items:
            if result_type.is_node:
                self.results.node[result_type.name].iloc[period] = values
            else:
                self.results.link[result_type.name].iloc[period] = values

    def save_network_desc_line(self, element, values):
        """Save network description meta-data and element characteristics.

        This method, by default, does nothing. It is available to be overloaded, but the
        core implementation assumes that an INP file exists that will have a better,
        human readable network description.

        Parameters
        ----------
        element : str
            the information being saved
        values : numpy.array
            the values that go with the information

        """
        #print('    Network: {} = {}'.format(element, values))
        pass

    def save_energy_line(self, pump_idx, pump_name, values):
        """Save pump energy from the output file.

        This method, by default, does nothing. It is available to be overloaded in
        order to save information for pump energy calculations.

        Parameters
        ----------
        pump_idx : int
            the pump index
        pump_name : str
            the pump name
        values : numpy.array
            the values to save

        """
        #print('    Energy: {} = {}'.format(pump_name, values))
        pass

    def finalize_save(self, good_read, sim_warnings):
        """Do any final post-read saves, writes, or processing.

        Parameters
        ----------
        good_read : bool
            was the full file read correctly
        sim_warnings : int
            were there warnings issued during the simulation


        """
        pass

    def read(self, filename):
        """Read a binary file and create a results object.

        Parameters
        ----------
        filename : str
            An EPANET BIN output file

        Returns
        -------
        object
            Returns the :attr:`~results` object, whatever it has been overloaded to be



        .. note:: Overloading
            This function should **not** be overloaded. Instead, overload the other functions
            to change how it saves the results. Specifically, overload :func:`~setup_ep_results`,
            :func:`~save_ep_line` and :func:`~finalize_save` to change how extended period
            simulation results in a different format (such as directly to a file or database).

        """
        logger.debug('Read binary EPANET data from %s',filename)
        with open(filename, 'rb') as fin:
            ftype = self.ftype
            idlen = self.idlen
            logger.debug('... read prolog information ...')
            prolog = np.fromfile(fin, dtype=np.int32, count=15)
            magic1 = prolog[0]
            version = prolog[1]
            nnodes = prolog[2]
            ntanks = prolog[3]
            nlinks = prolog[4]
            npumps = prolog[5]
            nvalve = prolog[6]
            wqopt = QualType(prolog[7])
            srctrace = prolog[8]
            flowunits = FlowUnits(prolog[9])
            presunits = PressureUnits(prolog[10])
            statsflag = StatisticsType(prolog[11])
            reportstart = prolog[12]
            reportstep = prolog[13]
            duration = prolog[14]
            logger.info('EPANET/Toolkit version %d',version)
            logger.info('Nodes: %d; Tanks/Resrv: %d Links: %d; Pumps: %d; Valves: %d',
                         nnodes, ntanks, nlinks, npumps, nvalve)
            logger.info('WQ opt: %s; Trace Node: %s; Flow Units %s; Pressure Units %s',
                         wqopt, srctrace, flowunits, presunits)
            logger.info('Statistics: %s; Report Start %d, step %d; Duration=%d sec',
                         statsflag, reportstart, reportstep, duration)

            # Ignore the title lines
            np.fromfile(fin, dtype=np.uint8, count=240)
            inpfile = np.fromfile(fin, dtype=np.uint8, count=260)
            rptfile = np.fromfile(fin, dtype=np.uint8, count=260)
            chemical = ''.join([chr(f) for f in np.fromfile(fin, dtype=np.uint8, count=idlen) if f!=0 ])
            wqunits = ''.join([chr(f) for f in np.fromfile(fin, dtype=np.uint8, count=idlen) if f!=0 ])
            mass = wqunits.split('/',1)[0]
            if mass in ['mg', 'ug', u'mg', u'ug']:
                massunits = MassUnits[mass]
            else:
                massunits = MassUnits.mg
            self.flow_units = flowunits
            self.pres_units = presunits
            self.quality_type = wqopt
            self.mass_units = massunits
            self.num_nodes = nnodes
            self.num_tanks = ntanks
            self.num_links = nlinks
            self.num_pumps = npumps
            self.num_valves = nvalve
            self.report_start = reportstart
            self.report_step = reportstep
            self.duration = duration
            self.chemical = chemical
            self.chem_units = wqunits
            self.inp_file = inpfile
            self.rpt_file = rptfile
            nodenames = []
            linknames = []
            for i in range(nnodes):
                name = ''.join([chr(f) for f in np.fromfile(fin, dtype=np.uint8, count=idlen) if f!=0 ])
                nodenames.append(name)
            for i in range(nlinks):
                name = ''.join([chr(f) for f in np.fromfile(fin, dtype=np.uint8, count=idlen) if f!=0 ])
                linknames.append(name)
            self.node_names = nodenames
            self.link_names = linknames
            linkstart = np.fromfile(fin, dtype=np.int32, count=nlinks)
            linkend = np.fromfile(fin, dtype=np.int32, count=nlinks)
            linktype = np.fromfile(fin, dtype=np.int32, count=nlinks)
            tankidxs = np.fromfile(fin, dtype=np.int32, count=ntanks)
            tankarea = np.fromfile(fin, dtype=np.dtype(ftype), count=ntanks)
            elevation = np.fromfile(fin, dtype=np.dtype(ftype), count=nnodes)
            linklen = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
            diameter = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
            self.save_network_desc_line('link_start', linkstart)
            self.save_network_desc_line('link_end', linkend)
            self.save_network_desc_line('link_type', linktype)
            self.save_network_desc_line('tank_node_index', tankidxs)
            self.save_network_desc_line('tank_area', tankarea)
            self.save_network_desc_line('node_elevation', elevation)
            self.save_network_desc_line('link_length', linklen)
            self.save_network_desc_line('link_diameter', diameter)

            logger.debug('... read energy data ...')
            for i in range(npumps):
                pidx = int(np.fromfile(fin,dtype=np.int32, count=1))
                energy = np.fromfile(fin, dtype=np.dtype(ftype), count=6)
                self.save_energy_line(pidx, linknames[pidx-1], energy)
            peakenergy = np.fromfile(fin, dtype=np.dtype(ftype), count=1)
            self.peak_energy = peakenergy

            logger.debug('... read EP simulation data ...')
            reporttimes = np.arange(reportstart, duration+reportstep, reportstep)
            nrptsteps = len(reporttimes)
            if statsflag in [StatisticsType.Maximum, StatisticsType.Minimum, StatisticsType.Range]:
                nrptsteps = 1
                reporttimes = [reportstart + reportstep]
            self.num_periods = nrptsteps
            self.report_times = reporttimes

            logger.debug('... set up results object ...')
            self.setup_ep_results(reporttimes, nodenames, linknames)

            for ts in range(nrptsteps):
                try:
                    demand = np.fromfile(fin, dtype=np.dtype(ftype), count=nnodes)
                    head = np.fromfile(fin, dtype=np.dtype(ftype), count=nnodes)
                    pressure = np.fromfile(fin, dtype=np.dtype(ftype), count=nnodes)
                    quality = np.fromfile(fin, dtype=np.dtype(ftype), count=nnodes)
                    flow = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
                    velocity = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
                    headloss = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
                    linkquality = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
                    linkstatus = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
                    linksetting = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
                    reactionrate = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
                    frictionfactor = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
                    self.save_ep_line(ts, ResultType.demand, demand)
                    self.save_ep_line(ts, ResultType.head, head)
                    self.save_ep_line(ts, ResultType.pressure, pressure)
                    self.save_ep_line(ts, ResultType.quality, quality)
                    self.save_ep_line(ts, ResultType.flowrate, flow)
                    self.save_ep_line(ts, ResultType.velocity, velocity)
                    self.save_ep_line(ts, ResultType.headloss, headloss)
                    self.save_ep_line(ts, ResultType.linkquality, linkquality)
                    self.save_ep_line(ts, ResultType.status, linkstatus)
                    self.save_ep_line(ts, ResultType.setting, linksetting)
                    self.save_ep_line(ts, ResultType.rxnrate, reactionrate)
                    self.save_ep_line(ts, ResultType.frictionfact, frictionfactor)
                except Exception as e:
                    logger.exception('Error reading or writing EP line: %s', e)
                    logger.warning('Missing results from report period %d',ts)

            logger.debug('... read epilog ...')
            # Read the averages and then the number of periods for checks
            averages = np.fromfile(fin, dtype=np.dtype(ftype), count=4)
            self.averages = averages
            np.fromfile(fin, dtype=np.int32, count=1)
            warnflag = np.fromfile(fin, dtype=np.int32, count=1)
            magic2 = np.fromfile(fin, dtype=np.int32, count=1)
            if magic1 != magic2:
                logger.critical('The magic number did not match -- binary incomplete or incorrectly read. If you believe this file IS complete, please try a different float type. Current type is "%s"',ftype)
            #print numperiods, warnflag, magic
            if warnflag != 0:
                logger.warning('Warnings were issued during simulation')
        self.finalize_save(magic1==magic2, warnflag)
        return self.results
