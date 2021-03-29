"""
The wntr.epanet.io module contains methods for reading/writing EPANET input and output files.

.. rubric:: Contents

.. autosummary::

    InpFile
    BinFile

----


"""
from __future__ import absolute_import

import datetime
import re
import io
import os, sys
import logging
import six
import warnings
import numpy as np
import pandas as pd
import difflib
from collections import OrderedDict

#from .time_utils import run_lineprofile

import wntr
import wntr.network
from wntr.network.base import Link
from wntr.network.model import WaterNetworkModel
from wntr.network.elements import Junction, Reservoir, Tank, Pipe, Pump, Valve
from wntr.network.options import Options
from wntr.network.model import Pattern, LinkStatus, Curve, Demands, Source
from wntr.network.controls import TimeOfDayCondition, SimTimeCondition, ValueCondition, Comparison
from wntr.network.controls import OrCondition, AndCondition, Control, ControlAction, _ControlType, Rule

from .util import FlowUnits, MassUnits, HydParam, QualParam, MixType, ResultType, EN
from .util import to_si, from_si
from .util import StatisticsType, QualType, PressureUnits

logger = logging.getLogger(__name__)

_INP_SECTIONS = ['[OPTIONS]', '[TITLE]', '[JUNCTIONS]', '[RESERVOIRS]',
                 '[TANKS]', '[PIPES]', '[PUMPS]', '[VALVES]', '[EMITTERS]',
                 '[CURVES]', '[PATTERNS]', '[ENERGY]', '[STATUS]',
                 '[CONTROLS]', '[RULES]', '[DEMANDS]', '[QUALITY]',
                 '[REACTIONS]', '[SOURCES]', '[MIXING]',
                 '[TIMES]', '[REPORT]', '[COORDINATES]', '[VERTICES]',
                 '[LABELS]', '[BACKDROP]', '[TAGS]']

_JUNC_ENTRY = ' {name:20} {elev:15.11g} {dem:15.11g} {pat:24} {com:>3s}\n'
_JUNC_LABEL = '{:21} {:>12s} {:>12s} {:24}\n'

_RES_ENTRY = ' {name:20s} {head:15.11g} {pat:>24s} {com:>3s}\n'
_RES_LABEL = '{:21s} {:>20s} {:>24s}\n'

_TANK_ENTRY = ' {name:20s} {elev:15.11g} {initlev:15.11g} {minlev:15.11g} {maxlev:15.11g} {diam:15.11g} {minvol:15.11g} {curve:20s} {overflow:20s} {com:>3s}\n'
_TANK_LABEL = '{:21s} {:>20s} {:>20s} {:>20s} {:>20s} {:>20s} {:>20s} {:20s} {:20s}\n'

_PIPE_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {len:15.11g} {diam:15.11g} {rough:15.11g} {mloss:15.11g} {status:>20s} {com:>3s}\n'
_PIPE_LABEL = '{:21s} {:20s} {:20s} {:>20s} {:>20s} {:>20s} {:>20s} {:>20s}\n'

_PUMP_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {ptype:8s} {params:20s} {com:>3s}\n'
_PUMP_LABEL = '{:21s} {:20s} {:20s} {:20s}\n'

_VALVE_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {diam:15.11g} {vtype:4s} {set:15.11g} {mloss:15.11g} {com:>3s}\n'
_GPV_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {diam:15.11g} {vtype:4s} {set:20s} {mloss:15.11g} {com:>3s}\n'
_VALVE_LABEL = '{:21s} {:20s} {:20s} {:>20s} {:4s} {:>20s} {:>20s}\n'

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
    Converts EPANET time format to seconds.


    Parameters
    ----------
    s : string
        EPANET time string. Options are 'HH:MM:SS', 'HH:MM', 'HH'


    Returns
    -------
    int
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
    Converts EPANET clocktime format to seconds.


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
        if s.startswith('12'):
            time_sec -= 3600*12
        if not am:
            if time_sec >= 3600*12:
                raise RuntimeError('Cannot specify am/pm for times greater than 12:00:00')
            time_sec += 3600*12
        return time_sec
    else:
        pattern2 = re.compile(r'^(\d+):(\d+)$')
        time_tuple = pattern2.search(s)
        if bool(time_tuple):
            time_sec = (int(time_tuple.groups()[0])*60*60 +
                        int(time_tuple.groups()[1])*60)
            if s.startswith('12'):
                time_sec -= 3600*12
            if not am:
                if time_sec >= 3600 * 12:
                    raise RuntimeError('Cannot specify am/pm for times greater than 12:00:00')
                time_sec += 3600*12
            return time_sec
        else:
            pattern3 = re.compile(r'^(\d+)$')
            time_tuple = pattern3.search(s)
            if bool(time_tuple):
                time_sec = int(time_tuple.groups()[0])*60*60
                if s.startswith('12'):
                    time_sec -= 3600*12
                if not am:
                    if time_sec >= 3600 * 12:
                        raise RuntimeError('Cannot specify am/pm for times greater than 12:00:00')
                    time_sec += 3600*12
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

    This class provides read and write functionality for EPANET INP files.
    The EPANET Users Manual provides full documentation for the INP file format.
    """
    def __init__(self):
        self.sections = OrderedDict()
        for sec in _INP_SECTIONS:
            self.sections[sec] = []
        self.mass_units = None
        self.flow_units = None
        self.top_comments = []
        self.curves = OrderedDict()

    def read(self, inp_files, wn=None):
        """
        Method to read an EPANET INP file and load data into a water network model object.
        Both EPANET 2.0 and EPANET 2.2 INP file options are recognized and handled.

        Parameters
        ----------
        inp_files : str or list
            An EPANET INP input file or list of INP files to be combined

        Returns
        -------
        :class:`~wntr.network.model.WaterNetworkModel`
            A water network model object

        """
        if wn is None:
            wn = WaterNetworkModel()
        self.wn = wn
        if not isinstance(inp_files, list):
            inp_files = [inp_files]
        wn.name = inp_files[0]

        self.curves = OrderedDict()
        self.top_comments = []
        self.sections = OrderedDict()
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
                    # Add handlers to deal with extra 'S'es (or missing 'S'es) in INP file
                    if sec not in _INP_SECTIONS:
                        trsec = sec.replace(']','S]')
                        if trsec in _INP_SECTIONS:
                            sec = trsec
                    if sec not in _INP_SECTIONS:
                        trsec = sec.replace('S]',']')
                        if trsec in _INP_SECTIONS:
                            sec = trsec
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
        # The order of operations is important as certain things require prior knowledge

        ### OPTIONS
        self._read_options()

        ### TIMES
        self._read_times()

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
        
        ### QUALITY
        self._read_quality()

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
        
        ### Finish tags
        self._read_end()
        
        return self.wn

    def write(self, filename, wn, units=None, version=2.2, force_coordinates=False):
        """
        Write a water network model into an EPANET INP file.

        .. note::

            Please note that by default, an EPANET 2.2 formatted file is written by WNTR. An INP file
            with version 2.2 options *will not* work with EPANET 2.0 (neither command line nor GUI). 
            By default, WNTR will use the EPANET 2.2 toolkit.
        

        Parameters
        ----------
        filename : str
            Name of the EPANET INP file.
        units : str, int or FlowUnits
            Name of the units for the EPANET INP file to be written in.
        version : float, {2.0, **2.2**}
            Defaults to 2.2; use 2.0 to guarantee backward compatability, but this will turn off PDD mode 
            and supress the writing of other EPANET 2.2-specific options. If PDD mode is specified, a 
            warning will be issued.
        force_coordinates : bool
            This only applies if `self.options.graphics.map_filename` is not `None`,
            and will force the COORDINATES section to be written even if a MAP file is
            provided. False by default, but coordinates **are** written by default since
            the MAP file is `None` by default.
		"""

        if not isinstance(wn, WaterNetworkModel):
            raise ValueError('Must pass a WaterNetworkModel object')
        if units is not None and isinstance(units, str):
            units=units.upper()
            self.flow_units = FlowUnits[units]
        elif units is not None and isinstance(units, FlowUnits):
            self.flow_units = units
        elif units is not None and isinstance(units, int):
            self.flow_units = FlowUnits(units)
        elif self.flow_units is not None:
            self.flow_units = self.flow_units
        elif isinstance(wn.options.hydraulic.inpfile_units, str):
            units = wn.options.hydraulic.inpfile_units.upper()
            self.flow_units = FlowUnits[units]
        else:
            self.flow_units = FlowUnits.GPM
        if self.mass_units is None:
            self.mass_units = MassUnits.mg
        with io.open(filename, 'wb') as f:
            self._write_title(f, wn)
            self._write_junctions(f, wn)
            self._write_reservoirs(f, wn)
            self._write_tanks(f, wn, version=version)
            self._write_pipes(f, wn)
            self._write_pumps(f, wn)
            self._write_valves(f, wn)

            self._write_tags(f, wn)
            self._write_demands(f, wn)
            self._write_status(f, wn)
            self._write_patterns(f, wn)
            self._write_curves(f, wn)
            self._write_controls(f, wn)
            self._write_rules(f, wn)
            self._write_energy(f, wn)
            self._write_emitters(f, wn)

            self._write_quality(f, wn)
            self._write_sources(f, wn)
            self._write_reactions(f, wn)
            self._write_mixing(f, wn)

            self._write_times(f, wn)
            self._write_report(f, wn)
            self._write_options(f, wn, version=version)

            if wn.options.graphics.map_filename is None or force_coordinates is True:
                self._write_coordinates(f, wn)
            self._write_vertices(f, wn)
            self._write_labels(f, wn)
            self._write_backdrop(f, wn)

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
#        try:
            for lnum, line in self.sections['[JUNCTIONS]']:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                if len(current) > 3:
                    pat = current[3]
                elif self.wn.options.hydraulic.pattern:
                    pat = self.wn.options.hydraulic.pattern
                else:
                    pat = self.wn.patterns.default_pattern
                base_demand = 0.0
                if len(current) > 2:
                    base_demand = to_si(self.flow_units, float(current[2]), HydParam.Demand)
                self.wn.add_junction(current[0],
                                base_demand,
                                pat,
                                to_si(self.flow_units, float(current[1]), HydParam.Elevation),
                                demand_category=None)
#        except Exception as e:
#            print(line)
#            raise e

    def _write_junctions(self, f, wn):
        f.write('[JUNCTIONS]\n'.encode('ascii'))
        f.write(_JUNC_LABEL.format(';ID', 'Elevation', 'Demand', 'Pattern').encode('ascii'))
        nnames = list(wn.junction_name_list)
        # nnames.sort()
        for junction_name in nnames:
            junction = wn.nodes[junction_name]
            if junction.demand_timeseries_list:
                base_demands = junction.demand_timeseries_list.base_demand_list()
                demand_patterns = junction.demand_timeseries_list.pattern_list()
                if base_demands:
                    base_demand = base_demands[0]
                else:
                    base_demand = 0.0
                if demand_patterns:
                    if demand_patterns[0] == wn.options.hydraulic.pattern:
                        demand_pattern = None
                    else:
                        demand_pattern = demand_patterns[0]
                else:
                    demand_pattern = None
            else:
                base_demand = 0.0
                demand_pattern = None
            E = {'name': junction_name,
                 'elev': from_si(self.flow_units, junction.elevation, HydParam.Elevation),
                 'dem': from_si(self.flow_units, base_demand, HydParam.Demand),
                 'pat': '',
                 'com': ';'}
            if demand_pattern is not None:
                E['pat'] = str(demand_pattern)
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
        nnames = list(wn.reservoir_name_list)
        # nnames.sort()
        for reservoir_name in nnames:
            reservoir = wn.nodes[reservoir_name]
            E = {'name': reservoir_name,
                 'head': from_si(self.flow_units, reservoir.head_timeseries.base_value, HydParam.HydraulicHead),
                 'com': ';'}
            if reservoir.head_timeseries.pattern is None:
                E['pat'] = ''
            else:
                E['pat'] = reservoir.head_timeseries.pattern.name
            f.write(_RES_ENTRY.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_tanks(self):
        for lnum, line in self.sections['[TANKS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            volume = None
            if len(current) >= 8:  # Volume curve provided
                volume = float(current[6])
                curve_name = current[7]
                if curve_name == '*':
                    curve_name = None
                else:
                    curve_points = []
                    for point in self.curves[curve_name]:
                        x = to_si(self.flow_units, point[0], HydParam.Length)
                        y = to_si(self.flow_units, point[1], HydParam.Volume)
                        curve_points.append((x, y))
                    self.wn.add_curve(curve_name, 'VOLUME', curve_points)
#                curve = self.wn.get_curve(curve_name)
                if len(current) == 9:
                    overflow = current[8]
                else:
                    overflow = False
            elif len(current) == 7:
                curve_name = None
                overflow = False
                volume = float(current[6])
            elif len(current) == 6:
                curve_name = None
                overflow = False
                volume = 0.0
            else:
                raise RuntimeError('Tank entry format not recognized.')
            self.wn.add_tank(current[0],
                        to_si(self.flow_units, float(current[1]), HydParam.Elevation),
                        to_si(self.flow_units, float(current[2]), HydParam.Length),
                        to_si(self.flow_units, float(current[3]), HydParam.Length),
                        to_si(self.flow_units, float(current[4]), HydParam.Length),
                        to_si(self.flow_units, float(current[5]), HydParam.TankDiameter),
                        to_si(self.flow_units, float(volume), HydParam.Volume),
                        curve_name, overflow)

    def _write_tanks(self, f, wn, version=2.2):
        f.write('[TANKS]\n'.encode('ascii'))
        if version != 2.2:
            f.write(_TANK_LABEL.format(';ID', 'Elevation', 'Init Level', 'Min Level', 'Max Level',
                                       'Diameter', 'Min Volume', 'Volume Curve','').encode('ascii'))
        else:
            f.write(_TANK_LABEL.format(';ID', 'Elevation', 'Init Level', 'Min Level', 'Max Level',
                            'Diameter', 'Min Volume', 'Volume Curve','Overflow').encode('ascii'))
        nnames = list(wn.tank_name_list)
        # nnames.sort()
        for tank_name in nnames:
            tank = wn.nodes[tank_name]
            E = {'name': tank_name,
                 'elev': from_si(self.flow_units, tank.elevation, HydParam.Elevation),
                 'initlev': from_si(self.flow_units, tank.init_level, HydParam.HydraulicHead),
                 'minlev': from_si(self.flow_units, tank.min_level, HydParam.HydraulicHead),
                 'maxlev': from_si(self.flow_units, tank.max_level, HydParam.HydraulicHead),
                 'diam': from_si(self.flow_units, tank.diameter, HydParam.TankDiameter),
                 'minvol': from_si(self.flow_units, tank.min_vol, HydParam.Volume),
                 'curve': '',
                 'overflow': '',
                 'com': ';'}
            if tank.vol_curve is not None:
                E['curve'] = tank.vol_curve.name
            if version ==2.2:
                if tank.overflow:
                    E['overflow'] = 'YES'
                    if tank.vol_curve is None:
                        E['curve'] = '*'
            f.write(_TANK_ENTRY.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_pipes(self):
        for lnum, line in self.sections['[PIPES]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) == 8:
                minor_loss = float(current[6])
                if current[7].upper() == 'CV':
                    link_status = LinkStatus.Open
                    check_valve_flag = True
                else:
                    link_status = LinkStatus[current[7].upper()]
                    check_valve_flag = False
            elif len(current) == 7:
                minor_loss = float(current[6])
                link_status = LinkStatus.Open
                check_valve_flag = False
            elif len(current) == 6:
                minor_loss = 0.
                link_status = LinkStatus.Open
                check_valve_flag = False

            self.wn.add_pipe(current[0],
                        current[1],
                        current[2],
                        to_si(self.flow_units, float(current[3]), HydParam.Length),
                        to_si(self.flow_units, float(current[4]), HydParam.PipeDiameter),
                        float(current[5]),
                        minor_loss,
                        link_status,
                        check_valve_flag)

    def _write_pipes(self, f, wn):
        f.write('[PIPES]\n'.encode('ascii'))
        f.write(_PIPE_LABEL.format(';ID', 'Node1', 'Node2', 'Length', 'Diameter',
                                   'Roughness', 'Minor Loss', 'Status').encode('ascii'))
        lnames = list(wn.pipe_name_list)
        # lnames.sort()
        for pipe_name in lnames:
            pipe = wn.links[pipe_name]
            E = {'name': pipe_name,
                 'node1': pipe.start_node_name,
                 'node2': pipe.end_node_name,
                 'len': from_si(self.flow_units, pipe.length, HydParam.Length),
                 'diam': from_si(self.flow_units, pipe.diameter, HydParam.PipeDiameter),
                 'rough': pipe.roughness,
                 'mloss': pipe.minor_loss,
                 'status': str(pipe.initial_status),
                 'com': ';'}
            if pipe.cv:
                E['status'] = 'CV'
            f.write(_PIPE_ENTRY.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_pumps(self):
        def create_curve(curve_name):
            curve_points = []
            if curve_name not in self.wn.curve_name_list or \
                    self.wn.get_curve(curve_name) is None:
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
#                    assert pump_type is None, 'In [PUMPS] entry, specify either HEAD or POWER once.'
                    pump_type = 'HEAD'
                    value = create_curve(current[i+1])
                elif current[i].upper() == 'POWER':
#                    assert pump_type is None, 'In [PUMPS] entry, specify either HEAD or POWER once.'
                    pump_type = 'POWER'
                    value = to_si(self.flow_units, float(current[i+1]), HydParam.Power)
                elif current[i].upper() == 'SPEED':
#                    assert speed is None, 'In [PUMPS] entry, SPEED may only be specified once.'
                    speed = float(current[i+1])
                elif current[i].upper() == 'PATTERN':
#                    assert pattern is None, 'In [PUMPS] entry, PATTERN may only be specified once.'
                    pattern = self.wn.get_pattern(current[i+1])
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
        lnames = list(wn.pump_name_list)
        # lnames.sort()
        for pump_name in lnames:
            pump = wn.links[pump_name]
            E = {'name': pump_name,
                 'node1': pump.start_node_name,
                 'node2': pump.end_node_name,
                 'ptype': pump.pump_type,
                 'params': '',
#                 'speed_keyword': 'SPEED',
#                 'speed': pump.speed_timeseries.base_value,
                 'com': ';'}
            if pump.pump_type == 'HEAD':
                E['params'] = pump.pump_curve_name
            elif pump.pump_type == 'POWER':
                E['params'] = str(from_si(self.flow_units, pump.power, HydParam.Power))
            else:
                raise RuntimeError('Only head or power info is supported of pumps.')
            tmp_entry = _PUMP_ENTRY
            if pump.speed_timeseries.base_value != 1:
                E['speed_keyword'] = 'SPEED'
                E['speed'] = pump.speed_timeseries.base_value
                tmp_entry = (tmp_entry.rstrip('\n').rstrip('}').rstrip('com:>3s').rstrip(' {') +
                             ' {speed_keyword:8s} {speed:15.11g} {com:>3s}\n')
            if pump.speed_timeseries.pattern is not None:
                tmp_entry = (tmp_entry.rstrip('\n').rstrip('}').rstrip('com:>3s').rstrip(' {') +
                             ' {pattern_keyword:10s} {pattern:20s} {com:>3s}\n')
                E['pattern_keyword'] = 'PATTERN'
                E['pattern'] = pump.speed_timeseries.pattern.name
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
        lnames = list(wn.valve_name_list)
        # lnames.sort()
        for valve_name in lnames:
            valve = wn.links[valve_name]
            E = {'name': valve_name,
                 'node1': valve.start_node_name,
                 'node2': valve.end_node_name,
                 'diam': from_si(self.flow_units, valve.diameter, HydParam.PipeDiameter),
                 'vtype': valve.valve_type,
                 'set': valve._setting,
                 'mloss': valve.minor_loss,
                 'com': ';'}
            valve_type = valve.valve_type
            formatter = _VALVE_ENTRY
            if valve_type in ['PRV', 'PSV', 'PBV']:
                valve_set = from_si(self.flow_units, valve._setting, HydParam.Pressure)
            elif valve_type == 'FCV':
                valve_set = from_si(self.flow_units, valve._setting, HydParam.Flow)
            elif valve_type == 'TCV':
                valve_set = valve._setting
            elif valve_type == 'GPV':
                valve_set = valve.headloss_curve_name
                formatter = _GPV_ENTRY
            E['set'] = valve_set
            f.write(formatter.format(**E).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_emitters(self):
        for lnum, line in self.sections['[EMITTERS]']: # Private attribute on junctions
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            junction = self.wn.get_node(current[0])
            junction.emitter_coefficient = to_si(self.flow_units, float(current[1]), HydParam.EmitterCoeff)

    def _write_emitters(self, f, wn):
        f.write('[EMITTERS]\n'.encode('ascii'))
        entry = '{:10s} {:10s}\n'
        label = '{:10s} {:10s}\n'
        f.write(label.format(';ID', 'Flow coefficient').encode('ascii'))
        njunctions = list(wn.junction_name_list)
        # njunctions.sort()
        for junction_name in njunctions:
            junction = wn.nodes[junction_name]
            if junction.emitter_coefficient:
                val = from_si(self.flow_units, junction.emitter_coefficient, HydParam.EmitterCoeff)
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
            self.wn.curves[curve_name] = None
            

    def _write_curves(self, f, wn):
        f.write('[CURVES]\n'.encode('ascii'))
        f.write(_CURVE_LABEL.format(';ID', 'X-Value', 'Y-Value').encode('ascii'))
        curves = list(wn.curve_name_list)
        # curves.sort()
        for curve_name in curves:
            curve = wn.get_curve(curve_name)
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
            else:
                f.write(';UNKNOWN: {}\n'.format(curve_name).encode('ascii'))
                for point in curve.points:
                    x = point[0]
                    y = point[1]
                    f.write(_CURVE_ENTRY.format(name=curve_name, x=x, y=y, com=';').encode('ascii'))
            f.write('\n'.encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_patterns(self):
        _patterns = OrderedDict()
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
            self.wn.add_pattern(pattern_name, pattern)
        if not self.wn.options.hydraulic.pattern and '1' in _patterns.keys():
            # If there is a pattern called "1", then it is the default pattern if no other is supplied
            self.wn.options.hydraulic.pattern = '1'
        elif self.wn.options.hydraulic.pattern not in _patterns.keys():
            # Sanity check - if the default pattern does not exist and it is not '1' then balk
            # If default is '1' but it does not exist, then it is constant
            # Any other default that does not exist is an error
            if self.wn.options.hydraulic.pattern is not None and self.wn.options.hydraulic.pattern != '1':
                raise KeyError('Default pattern {} is undefined'.format(self.wn.options.hydraulic.pattern))
            self.wn.options.hydraulic.pattern = None

    def _write_patterns(self, f, wn):
        num_columns = 6
        f.write('[PATTERNS]\n'.encode('ascii'))
        f.write('{:10s} {:10s}\n'.format(';ID', 'Multipliers').encode('ascii'))
        patterns = list(wn.pattern_name_list)
        # patterns.sort()
        for pattern_name in patterns:
            pattern = wn.get_pattern(pattern_name)
            count = 0
            for i in pattern.multipliers:
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
                    self.wn.options.energy.global_price = from_si(self.flow_units, float(current[2]), HydParam.Energy)
                elif current[1].upper() == 'PATTERN':
                    self.wn.options.energy.global_pattern = current[2]
                elif current[1].upper() in ['EFFIC', 'EFFICIENCY']:
                    self.wn.options.energy.global_efficiency = float(current[2])
                else:
                    logger.warning('Unknown entry in ENERGY section: %s', line)
            elif current[0].upper() == 'DEMAND':
                self.wn.options.energy.demand_charge = float(current[2])
            elif current[0].upper() == 'PUMP':
                pump_name = current[1]
                pump = self.wn.links[pump_name]
                if current[2].upper() == 'PRICE':
                    pump.energy_price = from_si(self.flow_units, float(current[3]), HydParam.Energy)
                elif current[2].upper() == 'PATTERN':
                    pump.energy_pattern = current[3]
                elif current[2].upper() in ['EFFIC', 'EFFICIENCY']:
                    curve_name = current[3]
                    curve_points = []
                    for point in self.curves[curve_name]:
                        x = to_si(self.flow_units, point[0], HydParam.Flow)
                        y = point[1]
                        curve_points.append((x, y))
                    self.wn.add_curve(curve_name, 'EFFICIENCY', curve_points)
                    curve = self.wn.get_curve(curve_name)
                    pump.efficiency = curve
                else:
                    logger.warning('Unknown entry in ENERGY section: %s', line)
            else:
                logger.warning('Unknown entry in ENERGY section: %s', line)

    def _write_energy(self, f, wn):
        f.write('[ENERGY]\n'.encode('ascii'))
        if True: #wn.energy is not None:
            if wn.options.energy.global_efficiency is not None:
                f.write('GLOBAL EFFICIENCY      {:.4f}\n'.format(wn.options.energy.global_efficiency).encode('ascii'))
            if wn.options.energy.global_price is not None:
                f.write('GLOBAL PRICE           {:.4f}\n'.format(to_si(self.flow_units, wn.options.energy.global_price, HydParam.Energy)).encode('ascii'))
            if wn.options.energy.demand_charge is not None:
                f.write('DEMAND CHARGE          {:.4f}\n'.format(wn.options.energy.demand_charge).encode('ascii'))
            if wn.options.energy.global_pattern is not None:
                f.write('GLOBAL PATTERN         {:s}\n'.format(wn.options.energy.global_pattern).encode('ascii'))
        lnames = list(wn.pump_name_list)
        lnames.sort()
        for pump_name in lnames:
            pump = wn.links[pump_name]
            if pump.efficiency is not None:
                f.write('PUMP {:10s} EFFIC   {:s}\n'.format(pump_name, pump.efficiency.name).encode('ascii'))
            if pump.energy_price is not None:
                f.write('PUMP {:10s} PRICE   {:.4f}\n'.format(pump_name, to_si(self.flow_units, pump.energy_price, HydParam.Energy)).encode('ascii'))
            if pump.energy_pattern is not None:
                f.write('PUMP {:10s} PATTERN {:s}\n'.format(pump_name, pump.energy_pattern).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_status(self):
        for lnum, line in self.sections['[STATUS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
#            assert(len(current) == 2), ("Error reading [STATUS] block, Check format.")
            link = self.wn.get_link(current[0])
            if (current[1].upper() == 'OPEN' or
                    current[1].upper() == 'CLOSED' or
                    current[1].upper() == 'ACTIVE'):
                new_status = LinkStatus[current[1].upper()]
                link.initial_status = new_status
                link._user_status = new_status
            else:
                if isinstance(link, wntr.network.Valve):
                    new_status = LinkStatus.Active
                    valve_type = link.valve_type
                    if valve_type in ['PRV', 'PSV', 'PBV']:
                        setting = to_si(self.flow_units, float(current[1]), HydParam.Pressure)
                    elif valve_type == 'FCV':
                        setting = to_si(self.flow_units, float(current[1]), HydParam.Flow)
                    elif valve_type == 'TCV':
                        setting = float(current[1])
                    else:
                        continue
                else:
                    new_status = LinkStatus.Open
                    setting = float(current[1])
#                link.setting = setting
                link.initial_setting = setting
                link._user_status = new_status
                link.initial_status = new_status

    def _write_status(self, f, wn):
        f.write('[STATUS]\n'.encode('ascii'))
        f.write( '{:10s} {:10s}\n'.format(';ID', 'Setting').encode('ascii'))
        for link_name, link in wn.links():
            if isinstance(link, Pipe):
                continue
            if isinstance(link, Pump):
                setting = link.initial_setting
                if type(setting) is float and setting != 1.0:
                    f.write('{:10s} {:10.10g}\n'.format(link_name,
                            setting).encode('ascii'))
            if link.initial_status in (LinkStatus.Closed,):
                f.write('{:10s} {:10s}\n'.format(link_name,
                        LinkStatus(link.initial_status).name).encode('ascii'))
            if isinstance(link, wntr.network.Valve) and link.initial_status in (LinkStatus.Open, LinkStatus.Opened):
#           if link.initial_status in (LinkStatus.Closed,):
                f.write('{:10s} {:10s}\n'.format(link_name,
                        LinkStatus(link.initial_status).name).encode('ascii'))
#                if link.initial_status is LinkStatus.Active:
#                    valve_type = link.valve_type
#                    if valve_type in ['PRV', 'PSV', 'PBV']:
#                        setting = from_si(self.flow_units, link.initial_setting, HydParam.Pressure)
#                    elif valve_type == 'FCV':
#                        setting = from_si(self.flow_units, link.initial_setting, HydParam.Flow)
#                    elif valve_type == 'TCV':
#                        setting = link.initial_setting
#                    else:
#                        continue
#                    continue
#                elif isinstance(link, wntr.network.Pump):
#                    setting = link.initial_setting
#                else: continue
#                f.write('{:10s} {:10.10g}\n'.format(link_name,
#                        setting).encode('ascii'))
#        f.write('\n'.encode('ascii'))

    def _read_controls(self):
        control_count = 0
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
                    action_obj = wntr.network.ControlAction(link, 'base_speed', float(current[2]))
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
            control_count += 1
            control_name = 'control '+str(control_count)
            if 'TIME' not in current and 'CLOCKTIME' not in current:
                threshold = None
                if 'IF' in current:
                    node = self.wn.get_node(node_name)
                    if current[6] == 'ABOVE':
                        oper = np.greater_equal
                    elif current[6] == 'BELOW':
                        oper = np.less_equal
                    else:
                        raise RuntimeError("The following control is not recognized: " + line)
                    # OKAY - we are adding in the elevation. This is A PROBLEM
                    # IN THE INP WRITER. Now that we know, we can fix it, but
                    # if this changes, it will affect multiple pieces, just an
                    # FYI.
                    if node.node_type == 'Junction':
                        threshold = to_si(self.flow_units,
                                          float(current[7]), HydParam.Pressure)# + node.elevation
                        control_obj = Control._conditional_control(node, 'pressure', oper, threshold, action_obj, control_name)
                    elif node.node_type == 'Tank':
                        threshold = to_si(self.flow_units, 
                                          float(current[7]), HydParam.HydraulicHead)# + node.elevation
                        control_obj = Control._conditional_control(node, 'level', oper, threshold, action_obj, control_name)
                else:
                    raise RuntimeError("The following control is not recognized: " + line)
#                control_name = ''
#                for i in range(len(current)-1):
#                    control_name = control_name + '/' + current[i]
#                control_name = control_name + '/' + str(round(threshold, 2))
            else:
                if 'CLOCKTIME' not in current:  # at time
                    if 'TIME' not in current:
                        raise ValueError('Unrecognized line in inp file: {0}'.format(line))

                    if ':' in current[5]:
                        run_at_time = int(_str_time_to_sec(current[5]))
                    else:
                        run_at_time = int(float(current[5])*3600)
                    control_obj = Control._time_control(self.wn, run_at_time, 'SIM_TIME', False, action_obj, control_name)
#                    control_name = ''
#                    for i in range(len(current)-1):
#                        control_name = control_name + '/' + current[i]
#                    control_name = control_name + '/' + str(run_at_time)
                else:  # at clocktime
                    if len(current) < 7:
                        if ':' in current[5]:
                            run_at_time = int(_str_time_to_sec(current[5]))
                        else:
                            run_at_time = int(float(current[5])*3600)
                    else:
                        run_at_time = int(_clock_time_to_sec(current[5], current[6]))
                    control_obj = Control._time_control(self.wn, run_at_time, 'CLOCK_TIME', True, action_obj, control_name)
#                    control_name = ''
#                    for i in range(len(current)-1):
#                        control_name = control_name + '/' + current[i]
#                    control_name = control_name + '/' + str(run_at_time)
            if control_name in self.wn.control_name_list:
                warnings.warn('One or more [CONTROLS] were duplicated in "{}"; duplicates are ignored.'.format(self.wn.name), stacklevel=0)
                logger.warning('Control already exists: "{}"'.format(control_name))
            else:
                self.wn.add_control(control_name, control_obj)

    def _write_controls(self, f, wn):
        def get_setting(control_action, control_name):
            value = control_action._value
            attribute = control_action._attribute.lower()
            if attribute == 'status':
                setting = LinkStatus(value).name
            elif attribute == 'base_speed':
                setting = str(value)
            elif attribute == 'setting' and isinstance(control_action._target_obj, Valve):
                valve = control_action._target_obj
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
            elif attribute == 'setting':
                setting = value
            else:
                setting = None
                logger.warning('Could not write control '+str(control_name)+' - skipping')

            return setting

        f.write('[CONTROLS]\n'.encode('ascii'))
        # Time controls and conditional controls only
        for text, all_control in wn.controls():
            control_action = all_control._then_actions[0]
            if all_control.epanet_control_type is not _ControlType.rule:
                if len(all_control._then_actions) != 1 or len(all_control._else_actions) != 0:
                    logger.error('Too many actions on CONTROL "%s"'%text)
                    raise RuntimeError('Too many actions on CONTROL "%s"'%text)
                if not isinstance(control_action.target()[0], Link):
                    continue
                if isinstance(all_control._condition, (SimTimeCondition, TimeOfDayCondition)):
                    entry = '{ltype} {link} {setting} AT {compare} {time:g}\n'
                    vals = {'ltype': control_action._target_obj.link_type,
                            'link': control_action._target_obj.name,
                            'setting': get_setting(control_action, text),
                            'compare': 'TIME',
                            'time': all_control._condition._threshold / 3600.0}
                    if vals['setting'] is None:
                        continue
                    if isinstance(all_control._condition, TimeOfDayCondition):
                        vals['compare'] = 'CLOCKTIME'
                    f.write(entry.format(**vals).encode('ascii'))
                elif isinstance(all_control._condition, (ValueCondition)):
                    entry = '{ltype} {link} {setting} IF {ntype} {node} {compare} {thresh}\n'
                    vals = {'ltype': control_action._target_obj.link_type,
                            'link': control_action._target_obj.name,
                            'setting': get_setting(control_action, text),
                            'ntype': all_control._condition._source_obj.node_type,
                            'node': all_control._condition._source_obj.name,
                            'compare': 'above',
                            'thresh': 0.0}
                    if vals['setting'] is None:
                        continue
                    if all_control._condition._relation in [np.less, np.less_equal, Comparison.le, Comparison.lt]:
                        vals['compare'] = 'below'
                    threshold = all_control._condition._threshold
                    if isinstance(all_control._condition._source_obj, Tank):
                        vals['thresh'] = from_si(self.flow_units, threshold, HydParam.HydraulicHead)
                    elif isinstance(all_control._condition._source_obj, Junction):
                        vals['thresh'] = from_si(self.flow_units, threshold, HydParam.Pressure) 
                    else: 
                        raise RuntimeError('Unknown control for EPANET INP files: %s' %type(all_control))
                    f.write(entry.format(**vals).encode('ascii'))
                elif not isinstance(all_control, Control):
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
        for text, all_control in wn.controls():
            entry = '{}\n'
            if all_control.epanet_control_type == _ControlType.rule:
                if all_control.name == '':
                    all_control._name = text
                rule = _EpanetRule('blah', self.flow_units, self.mass_units)
                rule.from_if_then_else(all_control)
                f.write(entry.format(str(rule)).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_demands(self):
        demand_num = 0
        has_been_read = set()
        for lnum, line in self.sections['[DEMANDS]']:
            ldata = line.split(';')
            if len(ldata) > 1:
                category = ldata[1]
            else:
                category = None
            current = ldata[0].split()
            if current == []:
                continue
            demand_num = demand_num + 1
            node = self.wn.get_node(current[0])
            if len(current) == 2:
                pattern = None
            else:
                pattern = self.wn.get_pattern(current[2])
            if node.name not in has_been_read:
                has_been_read.add(node.name)
                while len(node.demand_timeseries_list) > 0:
                    del node.demand_timeseries_list[-1]
            # In EPANET, the [DEMANDS] section overrides demands specified in [JUNCTIONS]
            # node.demand_timeseries_list.remove_category('EN2 base')
            node.demand_timeseries_list.append((to_si(self.flow_units, float(current[1]), HydParam.Demand),
                                         pattern, category))

    def _write_demands(self, f, wn):
        f.write('[DEMANDS]\n'.encode('ascii'))
        entry = '{:10s} {:10s} {:10s}{:s}\n'
        label = '{:10s} {:10s} {:10s}\n'
        f.write(label.format(';ID', 'Demand', 'Pattern').encode('ascii'))
        nodes = list(wn.junction_name_list)
        # nodes.sort()
        for node in nodes:
            demands = wn.get_node(node).demand_timeseries_list
            if len(demands) > 1:
                for ct, demand in enumerate(demands):
                    cat = str(demand.category)
                    #if cat == 'EN2 base':
                    #    cat = ''
                    if cat.lower() == 'none':
                        cat = ''
                    else:
                        cat = ' ;' + demand.category
                    E = {'node': node,
                         'base': from_si(self.flow_units, demand.base_value, HydParam.Demand),
                         'pat': '',
                         'cat': cat }
                    if demand.pattern_name in wn.pattern_name_list:
                        E['pat'] = demand.pattern_name
                    f.write(entry.format(E['node'], str(E['base']), E['pat'], E['cat']).encode('ascii'))
        f.write('\n'.encode('ascii'))

    ### Water Quality

    def _read_quality(self):
        for lnum, line in self.sections['[QUALITY]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            node = self.wn.get_node(current[0])
            if self.wn.options.quality.parameter == 'CHEMICAL':
                quality = to_si(self.flow_units, float(current[1]), QualParam.Concentration, mass_units=self.mass_units)
            elif self.wn.options.quality.parameter == 'AGE':
                quality = to_si(self.flow_units, float(current[1]), QualParam.WaterAge)
            else :
                quality = float(current[1])
            node.initial_quality = quality

    def _write_quality(self, f, wn):
        f.write('[QUALITY]\n'.encode('ascii'))
        entry = '{:10s} {:10s}\n'
        label = '{:10s} {:10s}\n'
        nnodes = list(wn.nodes.keys())
        # nnodes.sort()
        for node_name in nnodes:
            node = wn.nodes[node_name]
            if node.initial_quality:
                if wn.options.quality.parameter == 'CHEMICAL':
                    quality = from_si(self.flow_units, node.initial_quality, QualParam.Concentration, mass_units=self.mass_units)
                elif wn.options.quality.parameter == 'AGE':
                    quality = from_si(self.flow_units, node.initial_quality, QualParam.WaterAge)
                else:
                    quality = node.initial_quality
                f.write(entry.format(node_name, str(quality)).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_reactions(self):
        BulkReactionCoeff = QualParam.BulkReactionCoeff
        WallReactionCoeff = QualParam.WallReactionCoeff
        if self.mass_units is None:
            self.mass_units = MassUnits.mg
        for lnum, line in self.sections['[REACTIONS]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
#            assert len(current) == 3, ('INP file option in [REACTIONS] block '
#                                       'not recognized: ' + line)
            key1 = current[0].upper()
            key2 = current[1].upper()
            val3 = float(current[2])
            if key1 == 'ORDER':
                if key2 == 'BULK':
                    self.wn.options.reaction.bulk_order = int(float(current[2]))
                elif key2 == 'WALL':
                    self.wn.options.reaction.wall_order = int(float(current[2]))
                elif key2 == 'TANK':
                    self.wn.options.reaction.tank_order = int(float(current[2]))
            elif key1 == 'GLOBAL':
                if key2 == 'BULK':
                    self.wn.options.reaction.bulk_coeff = to_si(self.flow_units, val3, BulkReactionCoeff,
                                                mass_units=self.mass_units,
                                                reaction_order=self.wn.options.reaction.bulk_order)
                elif key2 == 'WALL':
                    self.wn.options.reaction.wall_coeff = to_si(self.flow_units, val3, WallReactionCoeff,
                                                mass_units=self.mass_units,
                                                reaction_order=self.wn.options.reaction.wall_order)
            elif key1 == 'BULK':
                pipe = self.wn.get_link(current[1])
                pipe.bulk_coeff = to_si(self.flow_units, val3, BulkReactionCoeff,
                                            mass_units=self.mass_units,
                                            reaction_order=self.wn.options.reaction.bulk_order)
            elif key1 == 'WALL':
                pipe = self.wn.get_link(current[1])
                pipe.wall_coeff = to_si(self.flow_units, val3, WallReactionCoeff,
                                            mass_units=self.mass_units,
                                            reaction_order=self.wn.options.reaction.wall_order)
            elif key1 == 'TANK':
                tank = self.wn.get_node(current[1])
                tank.bulk_coeff = to_si(self.flow_units, val3, BulkReactionCoeff,
                                            mass_units=self.mass_units,
                                            reaction_order=self.wn.options.reaction.bulk_order)
            elif key1 == 'LIMITING':
                self.wn.options.reaction.limiting_potential = float(current[2])
            elif key1 == 'ROUGHNESS':
                self.wn.options.reaction.roughness_correl = float(current[2])
            else:
                raise RuntimeError('Reaction option not recognized: %s'%key1)

    def _write_reactions(self, f, wn):
        f.write( '[REACTIONS]\n'.encode('ascii'))
        f.write(';Type           Pipe/Tank               Coefficient\n'.encode('ascii'))
        entry_int = ' {:s} {:s} {:d}\n'
        entry_float = ' {:s} {:s} {:<10.4f}\n'
        for tank_name, tank in wn.nodes(Tank):
            if tank.bulk_coeff is not None:
                f.write(entry_float.format('TANK',tank_name,
                                           from_si(self.flow_units,
                                                   tank.bulk_coeff,
                                                   QualParam.BulkReactionCoeff,
                                                   mass_units=self.mass_units,
                                                   reaction_order=wn.options.reaction.bulk_order)).encode('ascii'))
        for pipe_name, pipe in wn.links(Pipe):
            if pipe.bulk_coeff is not None:
                f.write(entry_float.format('BULK',pipe_name,
                                           from_si(self.flow_units,
                                                   pipe.bulk_coeff,
                                                   QualParam.BulkReactionCoeff,
                                                   mass_units=self.mass_units,
                                                   reaction_order=wn.options.reaction.bulk_order)).encode('ascii'))
            if pipe.wall_coeff is not None:
                f.write(entry_float.format('WALL',pipe_name,
                                           from_si(self.flow_units,
                                                   pipe.wall_coeff,
                                                   QualParam.WallReactionCoeff,
                                                   mass_units=self.mass_units,
                                                   reaction_order=wn.options.reaction.wall_order)).encode('ascii'))
        f.write('\n'.encode('ascii'))
#        f.write('[REACTIONS]\n'.encode('ascii'))  # EPANET GUI puts this line in here
        f.write(entry_int.format('ORDER', 'BULK', int(wn.options.reaction.bulk_order)).encode('ascii'))
        f.write(entry_int.format('ORDER', 'TANK', int(wn.options.reaction.tank_order)).encode('ascii'))
        f.write(entry_int.format('ORDER', 'WALL', int(wn.options.reaction.wall_order)).encode('ascii'))
        f.write(entry_float.format('GLOBAL','BULK',
                                   from_si(self.flow_units,
                                           wn.options.reaction.bulk_coeff,
                                           QualParam.BulkReactionCoeff,
                                           mass_units=self.mass_units,
                                           reaction_order=wn.options.reaction.bulk_order)).encode('ascii'))
        f.write(entry_float.format('GLOBAL','WALL',
                                   from_si(self.flow_units,
                                           wn.options.reaction.wall_coeff,
                                           QualParam.WallReactionCoeff,
                                           mass_units=self.mass_units,
                                           reaction_order=wn.options.reaction.wall_order)).encode('ascii'))
        if wn.options.reaction.limiting_potential is not None:
            f.write(entry_float.format('LIMITING','POTENTIAL',wn.options.reaction.limiting_potential).encode('ascii'))
        if wn.options.reaction.roughness_correl is not None:
            f.write(entry_float.format('ROUGHNESS','CORRELATION',wn.options.reaction.roughness_correl).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_sources(self):
        source_num = 0
        for lnum, line in self.sections['[SOURCES]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
#            assert(len(current) >= 3), ("Error reading sources. Check format.")
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
        # nsources.sort()
        for source_name in nsources:
            source = wn._sources[source_name]

            if source.source_type.upper() == 'MASS':
                strength = from_si(self.flow_units, source.strength_timeseries.base_value, QualParam.SourceMassInject, self.mass_units)
            else: # CONC, SETPOINT, FLOWPACED
                strength = from_si(self.flow_units, source.strength_timeseries.base_value, QualParam.Concentration, self.mass_units)

            E = {'node': source.node_name,
                 'type': source.source_type,
                 'quality': str(strength),
                 'pat': ''}
            if source.strength_timeseries.pattern_name is not None:
                E['pat'] = source.strength_timeseries.pattern_name
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
                tank.mixing_model = MixType.Mix1
            elif key == '2COMP' and len(current) > 2:
                tank.mixing_model = MixType.Mix2
                tank.mixing_fraction = float(current[2])
            elif key == '2COMP' and len(current) < 3:
                raise RuntimeError('Mixing model 2COMP requires fraction on tank %s'%tank_name)
            elif key == 'FIFO':
                tank.mixing_model = MixType.FIFO
            elif key == 'LIFO':
                tank.mixing_model = MixType.LIFO

    def _write_mixing(self, f, wn):
        f.write('[MIXING]\n'.encode('ascii'))
        f.write('{:20s} {:5s} {}\n'.format(';Tank ID', 'Model', 'Fraction').encode('ascii'))
        lnames = list(wn.tank_name_list)
        # lnames.sort()
        for tank_name in lnames:
            tank = wn.nodes[tank_name]
            if tank._mixing_model is not None:
                if tank._mixing_model in [MixType.Mixed, MixType.Mix1, 0]:
                    f.write(' {:19s} MIXED\n'.format(tank_name).encode('ascii'))
                elif tank._mixing_model in [MixType.TwoComp, MixType.Mix2, '2comp', '2COMP', 1]:
                    f.write(' {:19s} 2COMP  {}\n'.format(tank_name, tank.mixing_fraction).encode('ascii'))
                elif tank._mixing_model in [MixType.FIFO, 2]:
                    f.write(' {:19s} FIFO\n'.format(tank_name).encode('ascii'))
                elif tank._mixing_model in [MixType.LIFO, 3]:
                    f.write(' {:19s} LIFO\n'.format(tank_name).encode('ascii'))
                elif isinstance(tank._mixing_model, str) and tank.mixing_fraction is not None:
                    f.write(' {:19s} {} {}\n'.format(tank_name, tank._mixing_model, tank.mixing_fraction).encode('ascii'))
                elif isinstance(tank._mixing_model, str):
                    f.write(' {:19s} {}\n'.format(tank_name, tank._mixing_model).encode('ascii'))
                else:
                    logger.warning('Unknown mixing model: %s', tank._mixing_model)
        f.write('\n'.encode('ascii'))

    ### Options and Reporting

    def _read_options(self):
        edata = OrderedDict()
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
                    opts.hydraulic.inpfile_units = words[1].upper()
                elif key == 'HEADLOSS':
                    opts.hydraulic.headloss = words[1].upper()
                elif key == 'HYDRAULICS':
                    opts.hydraulic.hydraulics = words[1].upper()
                    opts.hydraulic.hydraulics_filename = words[2]
                elif key == 'QUALITY':
                    mode = words[1].upper()
                    if mode in ['NONE', 'AGE']:
                        opts.quality.parameter = words[1].upper()
                    elif mode in ['TRACE']:
                        opts.quality.parameter = 'TRACE'
                        opts.quality.trace_node = words[2]
                    else:
                        opts.quality.parameter = 'CHEMICAL'
                        opts.quality.chemical_name = words[1]
                        if len(words) > 2:
                            if 'mg' in words[2].lower():
                                self.mass_units = MassUnits.mg
                                opts.quality.inpfile_units = words[2]
                            elif 'ug' in words[2].lower():
                                self.mass_units = MassUnits.ug
                                opts.quality.inpfile_units = words[2]
                            else:
                                raise ValueError('Invalid chemical units in OPTIONS section')
                        else:
                            self.mass_units = MassUnits.mg
                            opts.quality.inpfile_units = 'mg/L'                            
                elif key == 'VISCOSITY':
                    opts.hydraulic.viscosity = float(words[1])
                elif key == 'DIFFUSIVITY':
                    opts.hydraulic.diffusivity = float(words[1])
                elif key == 'SPECIFIC':
                    opts.hydraulic.specific_gravity = float(words[2])
                elif key == 'TRIALS':
                    opts.hydraulic.trials = int(words[1])
                elif key == 'ACCURACY':
                    opts.hydraulic.accuracy = float(words[1])
                elif key == 'HEADERROR':
                    opts.hydraulic.headerror = float(words[1])
                elif key == 'FLOWCHANGE':
                    opts.hydraulic.flowchange = float(words[1])
                elif key == 'UNBALANCED':
                    opts.hydraulic.unbalanced = words[1].upper()
                    if len(words) > 2:
                        opts.hydraulic.unbalanced_value = int(words[2])
                elif key == 'MINIMUM':
                    minimum_pressure = to_si(self.flow_units, float(words[2]), HydParam.Pressure)
                    opts.hydraulic.minimum_pressure = minimum_pressure
                elif key == 'REQUIRED':
                    required_pressure = to_si(self.flow_units, float(words[2]), HydParam.Pressure)
                    opts.hydraulic.required_pressure = required_pressure
                elif key == 'PRESSURE':
                    opts.hydraulic.pressure_exponent = float(words[2])
                elif key == 'PATTERN':
                    opts.hydraulic.pattern = words[1]
                elif key == 'DEMAND':
                    if len(words) > 2:
                        if words[1].upper() == 'MULTIPLIER':
                            opts.hydraulic.demand_multiplier = float(words[2])
                        elif words[1].upper() == 'MODEL':
                            opts.hydraulic.demand_model = words[2]
                        else:
                            edata['key'] = ' '.join(words)
                            raise RuntimeError('%(fname)s:%(lnum)-6d %(sec)13s unknown option %(key)s' % edata)
                    else:
                        edata['key'] = ' '.join(words)
                        raise RuntimeError('%(fname)s:%(lnum)-6d %(sec)13s no value provided for %(key)s' % edata)
                elif key == 'EMITTER':
                    if len(words) > 2:
                        opts.hydraulic.emitter_exponent = float(words[2])
                    else:
                        edata['key'] = 'EMITTER EXPONENT'
                        raise RuntimeError('%(fname)s:%(lnum)-6d %(sec)13s no value provided for %(key)s' % edata)
                elif key == 'TOLERANCE':
                    opts.quality.tolerance = float(words[1])
                elif key == 'CHECKFREQ':
                    opts.hydraulic.checkfreq = float(words[1])
                elif key == 'MAXCHECK':
                    opts.hydraulic.maxcheck = float(words[1])
                elif key == 'DAMPLIMIT':
                    opts.hydraulic.damplimit = float(words[1])
                elif key == 'MAP':
                    opts.graphics.map_filename = words[1]
                else:
                    if len(words) == 2:
                        edata['key'] = words[0]
                        setattr(opts, words[0].lower(), float(words[1]))
                        logger.warn('%(fname)s:%(lnum)-6d %(sec)13s option "%(key)s" is undocumented; adding, but please verify syntax', edata)
                    elif len(words) == 3:
                        edata['key'] = words[0] + ' ' + words[1]
                        setattr(opts, words[0].lower() + '_' + words[1].lower(), float(words[2]))
                        logger.warn('%(fname)s:%(lnum)-6d %(sec)13s option "%(key)s" is undocumented; adding, but please verify syntax', edata)
        if (type(opts.time.report_timestep) == float or
                type(opts.time.report_timestep) == int):
            if opts.time.report_timestep < opts.time.hydraulic_timestep:
                raise RuntimeError('opts.report_timestep must be greater than or equal to opts.hydraulic_timestep.')
            if opts.time.report_timestep % opts.time.hydraulic_timestep != 0:
                raise RuntimeError('opts.report_timestep must be a multiple of opts.hydraulic_timestep')

    def _write_options(self, f, wn, version=2.2):
        f.write('[OPTIONS]\n'.encode('ascii'))
        entry_string = '{:20s} {:20s}\n'
        entry_float = '{:20s} {:.11g}\n'
        f.write(entry_string.format('UNITS', self.flow_units.name).encode('ascii'))

        f.write(entry_string.format('HEADLOSS', wn.options.hydraulic.headloss).encode('ascii'))

        f.write(entry_float.format('SPECIFIC GRAVITY', wn.options.hydraulic.specific_gravity).encode('ascii'))

        f.write(entry_float.format('VISCOSITY', wn.options.hydraulic.viscosity).encode('ascii'))

        f.write(entry_float.format('TRIALS', wn.options.hydraulic.trials).encode('ascii'))

        f.write(entry_float.format('ACCURACY', wn.options.hydraulic.accuracy).encode('ascii'))

        f.write(entry_float.format('CHECKFREQ', wn.options.hydraulic.checkfreq).encode('ascii'))

        f.write(entry_float.format('MAXCHECK', wn.options.hydraulic.maxcheck).encode('ascii'))

        # EPANET 2.2 OPTIONS
        if version == 2.0:
            pass
        else:
            if wn.options.hydraulic.headerror != 0: 
                f.write(entry_float.format('HEADERROR', wn.options.hydraulic.headerror).encode('ascii'))

            if wn.options.hydraulic.flowchange != 0:
                f.write(entry_float.format('FLOWCHANGE', wn.options.hydraulic.flowchange).encode('ascii'))

        # EPANET 2.x OPTIONS
        if wn.options.hydraulic.damplimit != 0:
            f.write(entry_float.format('DAMPLIMIT', wn.options.hydraulic.damplimit).encode('ascii'))

        if wn.options.hydraulic.unbalanced_value is None:
            f.write(entry_string.format('UNBALANCED', wn.options.hydraulic.unbalanced).encode('ascii'))
        else:
            f.write('{:20s} {:s} {:d}\n'.format('UNBALANCED', wn.options.hydraulic.unbalanced, wn.options.hydraulic.unbalanced_value).encode('ascii'))

        if wn.options.hydraulic.pattern is not None:
            f.write(entry_string.format('PATTERN', wn.options.hydraulic.pattern).encode('ascii'))

        f.write(entry_float.format('DEMAND MULTIPLIER', wn.options.hydraulic.demand_multiplier).encode('ascii'))

        # EPANET 2.2 OPTIONS
        if version == 2.0:
            if wn.options.hydraulic.demand_model in ['PDA', 'PDD']: 
                logger.critical('You have specified a PDD analysis using EPANET 2.0. This is not supported in EPANET 2.0. The analysis will default to DD mode.')
        else:
            if wn.options.hydraulic.demand_model in ['PDA', 'PDD']: 
                f.write('{:20s} {}\n'.format('DEMAND MODEL', wn.options.hydraulic.demand_model).encode('ascii'))

                minimum_pressure = from_si(self.flow_units, wn.options.hydraulic.minimum_pressure, HydParam.Pressure)
                f.write('{:20s} {:.2f}\n'.format('MINIMUM PRESSURE', minimum_pressure).encode('ascii'))

                required_pressure = from_si(self.flow_units, wn.options.hydraulic.required_pressure, HydParam.Pressure)
                f.write('{:20s} {:.2f}\n'.format('REQUIRED PRESSURE', required_pressure).encode('ascii'))

                f.write('{:20s} {}\n'.format('PRESSURE EXPONENT', wn.options.hydraulic.pressure_exponent).encode('ascii'))

        # EPANET 2.0+ OPTIONS
        f.write(entry_float.format('EMITTER EXPONENT',  wn.options.hydraulic.emitter_exponent).encode('ascii'))

        if wn.options.quality.parameter.upper() in ['NONE', 'AGE']:
            f.write(entry_string.format('QUALITY', wn.options.quality.parameter).encode('ascii'))
        elif wn.options.quality.parameter.upper() in ['TRACE']:
            f.write('{:20s} {} {}\n'.format('QUALITY', wn.options.quality.parameter, wn.options.quality.trace_node).encode('ascii'))
        else:
            f.write('{:20s} {} {}\n'.format('QUALITY', wn.options.quality.chemical_name, wn.options.quality.inpfile_units).encode('ascii'))

        f.write(entry_float.format('DIFFUSIVITY', wn.options.quality.diffusivity).encode('ascii'))

        f.write(entry_float.format('TOLERANCE', wn.options.quality.tolerance).encode('ascii'))

        if wn.options.hydraulic.hydraulics is not None:
            f.write('{:20s} {:s} {:<30s}\n'.format('HYDRAULICS', wn.options.hydraulic.hydraulics, wn.options.hydraulic.hydraulics_filename).encode('ascii'))

        if wn.options.graphics.map_filename is not None:
            f.write(entry_string.format('MAP', wn.options.graphics.map_filename).encode('ascii'))
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
                opts.time.duration = _str_time_to_sec(current[1])
            elif (current[0].upper() == 'HYDRAULIC'):
                opts.time.hydraulic_timestep = _str_time_to_sec(current[2])
            elif (current[0].upper() == 'QUALITY'):
                opts.time.quality_timestep = _str_time_to_sec(current[2])
            elif (current[1].upper() == 'CLOCKTIME'):
                if len(current) > 3:
                    time_format = current[3].upper()
                else:
                    # Kludge for 24hr time that needs an AM/PM
                    time_format = 'AM'
                time = current[2]
                opts.time.start_clocktime = _clock_time_to_sec(time, time_format)
            elif (current[0].upper() == 'STATISTIC'):
                opts.time.statistic = current[1].upper()
            else:
                # Other time options: RULE TIMESTEP, PATTERN TIMESTEP, REPORT TIMESTEP, REPORT START
                key_string = current[0] + '_' + current[1]
                setattr(opts.time, key_string.lower(), _str_time_to_sec(current[2]))

    def _write_times(self, f, wn):
        f.write('[TIMES]\n'.encode('ascii'))
        entry = '{:20s} {:10s}\n'
        time_entry = '{:20s} {:02d}:{:02d}:{:02d}\n'
        time = wn.options.time

        hrs, mm, sec = time.seconds_to_tuple(time.duration)
        f.write(time_entry.format('DURATION', hrs, mm, sec).encode('ascii'))

        hrs, mm, sec = time.seconds_to_tuple(time.hydraulic_timestep)
        f.write(time_entry.format('HYDRAULIC TIMESTEP', hrs, mm, sec).encode('ascii'))

        hrs, mm, sec = time.seconds_to_tuple(time.quality_timestep)
        f.write(time_entry.format('QUALITY TIMESTEP', hrs, mm, sec).encode('ascii'))

        hrs, mm, sec = time.seconds_to_tuple(time.pattern_timestep)
        f.write(time_entry.format('PATTERN TIMESTEP', hrs, mm, sec).encode('ascii'))

        hrs, mm, sec = time.seconds_to_tuple(time.pattern_start)
        f.write(time_entry.format('PATTERN START', hrs, mm, sec).encode('ascii'))

        hrs, mm, sec = time.seconds_to_tuple(time.report_timestep)
        f.write(time_entry.format('REPORT TIMESTEP', hrs, mm, sec).encode('ascii'))

        hrs, mm, sec = time.seconds_to_tuple(time.report_start)
        f.write(time_entry.format('REPORT START', hrs, mm, sec).encode('ascii'))

        hrs, mm, sec = time.seconds_to_tuple(time.start_clocktime)
        if hrs < 12:
            time_format = ' AM'
        else:
            hrs -= 12
            time_format = ' PM'
        f.write('{:20s} {:02d}:{:02d}:{:02d}{:s}\n'.format('START CLOCKTIME', hrs, mm, sec, time_format).encode('ascii'))

        hrs, mm, sec = time.seconds_to_tuple(time.rule_timestep)

        ### TODO: RULE TIMESTEP is not written?!
        f.write(time_entry.format('RULE TIMESTEP', hrs, mm, int(sec)).encode('ascii'))
        f.write(entry.format('STATISTIC', wn.options.time.statistic).encode('ascii'))
        f.write('\n'.encode('ascii'))

    def _read_report(self):
        for lnum, line in self.sections['[REPORT]']:
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if current[0].upper() in ['PAGE', 'PAGESIZE']:
                self.wn.options.report.pagesize = int(current[1])
            elif current[0].upper() in ['FILE']:
                self.wn.options.report.file = current[1]
            elif current[0].upper() in ['STATUS']:
                self.wn.options.report.status = current[1].upper()
            elif current[0].upper() in ['SUMMARY']:
                self.wn.options.report.summary = current[1].upper()
            elif current[0].upper() in ['ENERGY']:
                self.wn.options.report.energy = current[1].upper()
            elif current[0].upper() in ['NODES']:
                if current[1].upper() in ['NONE']:
                    self.wn.options.report.nodes = False
                elif current[1].upper() in ['ALL']:
                    self.wn.options.report.nodes = True
                elif not isinstance(self.wn.options.report.nodes, list):
                    self.wn.options.report.nodes = []
                    for ct in range(len(current)-2):
                        i = ct + 2
                        self.wn.options.report.nodes.append(current[i])
                else:
                    for ct in range(len(current)-2):
                        i = ct + 2
                        self.wn.options.report.nodes.append(current[i])
            elif current[0].upper() in ['LINKS']:
                if current[1].upper() in ['NONE']:
                    self.wn.options.report.links = False
                elif current[1].upper() in ['ALL']:
                    self.wn.options.report.links = True
                elif not isinstance(self.wn.options.report.links, list):
                    self.wn.options.report.links = []
                    for ct in range(len(current)-2):
                        i = ct + 2
                        self.wn.options.report.links.append(current[i])
                else:
                    for ct in range(len(current)-2):
                        i = ct + 2
                        self.wn.options.report.links.append(current[i])
            else:
                if current[0].lower() not in self.wn.options.report.report_params.keys():
                    logger.warning('Unknown report parameter: %s', current[0])
                    continue
                elif current[1].upper() in ['YES']:
                    self.wn.options.report.report_params[current[0].lower()][1] = True
                elif current[1].upper() in ['NO']:
                    self.wn.options.report.report_params[current[0].lower()][1] = False
                else:
                    self.wn.options.report.param_opts[current[0].lower()][current[1].upper()] = float(current[2])

    def _write_report(self, f, wn):
        f.write('[REPORT]\n'.encode('ascii'))
        report = wn.options.report
        if report.status.upper() != 'NO':
            f.write('STATUS     {}\n'.format(report.status).encode('ascii'))
        if report.summary.upper() != 'YES':
            f.write('SUMMARY    {}\n'.format(report.summary).encode('ascii'))
        if report.pagesize is not None:
            f.write('PAGE       {}\n'.format(report.pagesize).encode('ascii'))
        if report.report_filename is not None:
            f.write('FILE       {}\n'.format(report.report_filename).encode('ascii'))
        if report.energy.upper() != 'NO':
            f.write('ENERGY     {}\n'.format(report.status).encode('ascii'))
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
        # FIXME: defaults no longer located here
#        for key, item in report.report_params.items():
#            if item[1] != item[0]:
#                f.write('{:10s} {}\n'.format(key.upper(), item[1]).encode('ascii'))
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
#            assert(len(current) == 3), ("Error reading node coordinates. Check format.")
            node = self.wn.get_node(current[0])
            node.coordinates = (float(current[1]), float(current[2]))

    def _write_coordinates(self, f, wn):
        f.write('[COORDINATES]\n'.encode('ascii'))
        entry = '{:10s} {:20.9f} {:20.9f}\n'
        label = '{:10s} {:10s} {:10s}\n'
        f.write(label.format(';Node', 'X-Coord', 'Y-Coord').encode('ascii'))
        for name, node in wn.nodes():
            val = node.coordinates
            f.write(entry.format(name, val[0], val[1]).encode('ascii'))
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
        entry = '{:10s} {:20.9f} {:20.9f}\n'
        label = '{:10s} {:10s} {:10s}\n'
        f.write(label.format(';Link', 'X-Coord', 'Y-Coord').encode('ascii'))
        lnames = list(wn.pipe_name_list)
        # lnames.sort()
        for pipe_name in lnames:
            pipe = wn.links[pipe_name]
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
                self.wn.options.graphics.dimensions = [current[1], current[2], current[3], current[4]]
            elif key == 'UNITS' and len(current) > 1:
                self.wn.options.graphics.units = current[1]
            elif key == 'FILE' and len(current) > 1:
                self.wn.options.graphics.image_filename = current[1]
            elif key == 'OFFSET' and len(current) > 2:
                self.wn.options.graphics.offset = [current[1], current[2]]

    def _write_backdrop(self, f, wn):
        if wn.options.graphics is not None:
            f.write('[BACKDROP]\n'.encode('ascii'))
            if wn.options.graphics.dimensions is not None:
                f.write('DIMENSIONS    {0}    {1}    {2}    {3}\n'.format(wn.options.graphics.dimensions[0],
                                                                        wn.options.graphics.dimensions[1],
                                                                        wn.options.graphics.dimensions[2],
                                                                        wn.options.graphics.dimensions[3]).encode('ascii'))
            if wn.options.graphics.units is not None:
                f.write('UNITS    {0}\n'.format(wn.options.graphics.units).encode('ascii'))
            if wn.options.graphics.image_filename is not None:
                f.write('FILE    {0}\n'.format(wn.options.graphics.image_filename).encode('ascii'))
            if wn.options.graphics.offset is not None:
                f.write('OFFSET    {0}    {1}\n'.format(wn.options.graphics.offset[0], wn.options.graphics.offset[1]).encode('ascii'))
            f.write('\n'.encode('ascii'))

    def _read_tags(self):
        for lnum, line in self.sections['[TAGS]']: 
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
        nnodes = list(wn.node_name_list)
        # nnodes.sort()
        for node_name in nnodes:
            node = wn.nodes[node_name]
            if node.tag:
                f.write(entry.format('NODE', node_name, node.tag).encode('ascii'))
        nlinks = list(wn.link_name_list)
        nlinks.sort()
        for link_name in nlinks:
            link = wn.links[link_name]
            if link.tag:
                f.write(entry.format('LINK', link_name, link.tag).encode('ascii'))
        f.write('\n'.encode('ascii'))

    ### End of File

    def _read_end(self):
        """Finalize read by verifying that all curves have been dealt with"""
        def create_curve(curve_name):
            curve_points = []
            if curve_name not in self.wn.curve_name_list or self.wn.get_curve(curve_name) is None:
                for point in self.curves[curve_name]:
                    x = point[0]
                    y = point[1]
                    curve_points.append((x,y))
                self.wn.add_curve(curve_name, None, curve_points)
            curve = self.wn.get_curve(curve_name)
            return curve

        curve_name_list = self.wn.curve_name_list
        for name, curvedata in self.curves.items():
            if name not in curve_name_list or self.wn.get_curve(name) is None:
                warnings.warn('Not all curves were used in "{}"; added with type None, units conversion left to user'.format(self.wn.name))
                logger.warning('Curve was not used: "{}"; saved as curve type None and unit conversion not performed'.format(name))
                create_curve(name)

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
        """Create a rule from a Rule object"""
        if isinstance(control, Rule):
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
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Pressure))
            elif attr.lower() in ['setting']:
                if isinstance(condition._source_obj, Valve):
                    if condition._source_obj.valve_type.upper() in ['PRV', 'PBV', 'PSV']:
                        value = from_si(self.inp_units, val_si, HydParam.Pressure)
                    elif condition._source_obj.valve_type.upper() in ['FCV']:
                        value = from_si(self.inp_units, val_si, HydParam.Flow)
                    else:
                        value = val_si
                else:
                    value = val_si
                value = '{:.6g}'.format(value)
            else: # status
                value = val_si
            if isinstance(condition._source_obj, Valve):
                cls = 'Valve'
            elif isinstance(condition._source_obj, Pump):
                cls = 'Pump'
            else:
                cls = condition._source_obj.__class__.__name__
            clause = fmt.format(prefix, cls,
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
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Pressure))
            elif attr.lower() in ['setting']:
                if isinstance(action.target()[0], Valve):
                    if action.target()[0].valve_type.upper() in ['PRV', 'PBV', 'PSV']:
                        value = from_si(self.inp_units, val_si, HydParam.Pressure)
                    elif action.target()[0].valve_type.upper() in ['FCV']:
                        value = from_si(self.inp_units, val_si, HydParam.Flow)
                    else:
                        value = val_si
                else:
                    value = val_si
                value = '{:.6g}'.format(value)
            else: # status
                value = val_si
            if isinstance(action.target()[0], Valve):
                cls = 'Valve'
            elif isinstance(action.target()[0], Pump):
                cls = 'Pump'
            else:
                cls = action.target()[0].__class__.__name__
            clause = fmt.format(prefix, cls,
                                action.target()[0].name, action.target()[1],
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
                value = '{:.6g}'.format(from_si(self.inp_units, val_si, HydParam.Pressure))
            elif attr.lower() in ['setting']:
                if isinstance(action.target()[0], Valve):
                    if action.target()[0].valve_type.upper() in ['PRV', 'PBV', 'PSV']:
                        value = from_si(self.inp_units, val_si, HydParam.Pressure)
                    elif action.target()[0].valve_type.upper() in ['FCV']:
                        value = from_si(self.inp_units, val_si, HydParam.Flow)
                    else:
                        value = val_si
                else:
                    value = val_si
                value = '{:.6g}'.format(value)
            else: # status
                value = val_si
            if isinstance(action.target()[0], Valve):
                cls = 'Valve'
            elif isinstance(action.target()[0], Pump):
                cls = 'Pump'
            else:
                cls = action.target()[0].__class__.__name__
            clause = fmt.format(prefix, cls,
                                action.target()[0].name, action.target()[1],
                                value)
            self.add_else(clause)

    def set_priority(self, priority):
        self.priority = int(float(priority))

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
                elif attr.lower() in ['head']:
                    value = to_si(self.inp_units, value, HydParam.HydraulicHead)
                elif attr.lower() in ['level']:
                    value = to_si(self.inp_units, value, HydParam.HydraulicHead)
                elif attr.lower() in ['flow']:
                    value = to_si(self.inp_units, value, HydParam.Flow)
                elif attr.lower() in ['pressure']:
                    value = to_si(self.inp_units, value, HydParam.Pressure)
                elif attr.lower() in ['setting']:
                    link = model.get_link(words[2])
                    if isinstance(link, wntr.network.Pump):
                        value = value
                    elif isinstance(link, wntr.network.Valve):
                        if link.valve_type.upper() in ['PRV', 'PBV', 'PSV']:
                            value = to_si(self.inp_units, value, HydParam.Pressure)
                        elif link.valve_type.upper() in ['FCV']:
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
                value = to_si(self.inp_units, value, HydParam.Pressure)
            elif attr.lower() in ['setting']:
                if isinstance(link, Valve):
                    if link.valve_type.upper() in ['PRV', 'PBV', 'PSV']:
                        value = to_si(self.inp_units, value, HydParam.Pressure)
                    elif link.valve_type.upper() in ['FCV']:
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
                value = to_si(self.inp_units, value, HydParam.Pressure)
            elif attr.lower() in ['setting']:
                if isinstance(link, Valve):
                    if link.valve_type.upper() in ['PRV', 'PBV', 'PSV']:
                        value = to_si(self.inp_units, value, HydParam.Pressure)
                    elif link.valve_type.upper() in ['FCV']:
                        value = to_si(self.inp_units, value, HydParam.Flow)
            else_acts.append(ControlAction(link, attr, value))
        return Rule(final_condition, then_acts, else_acts, priority=self.priority, name=self.ruleID)


class BinFile(object):
    """
    EPANET binary output file reader class.
    
    This class provides read functionality for EPANET binary output files.
    
    Parameters
    ----------
    results_type : list of :class:`~wntr.epanet.util.ResultType`, default=None
        This parameter is *only* active when using a subclass of the BinFile that implements
	a custom reader or writer.
        If ``None``, then all results will be saved (node quality, demand, link flow, etc.).
        Otherwise, a list of result types can be passed to limit the memory used.
    network : bool, default=False
        Save a new WaterNetworkModel from the description in the output binary file. Certain
        elements may be missing, such as patterns and curves, if this is done.
    energy : bool, default=False
        Save the pump energy results.
    statistics : bool, default=False
        Save the statistics lines (different from the stats flag in the inp file) that are
        automatically calculated regarding hydraulic conditions.
    convert_status : bool, default=True
        Convert the EPANET link status (8 values) to simpler WNTR status (3 values). By 
        default, this is done, and the encoded-cause status values are converted simple state
        values, instead.

    Returns
    ----------
    :class:`~wntr.sim.results.SimulationResults`
        A WNTR results object will be created and added to the instance after read.

    """
    def __init__(self, result_types=None, network=False, energy=False, statistics=False,
                 convert_status=True):
        if os.name in ['nt', 'dos'] or sys.platform in ['darwin']:
            self.ftype = '=f4'
        else:
            self.ftype = '=f4'
        self.idlen = 32
        self.convert_status = convert_status
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
        self.report_file = None
        self.results = wntr.sim.SimulationResults()
        if result_types is None:
            self.items = [ member for name, member in ResultType.__members__.items() ]
        else:
            self.items = result_types
        self.create_network = network
        self.keep_energy = energy
        self.keep_statistics = statistics

    def _get_time(self, t):
        s = int(t)
        h = int(s/3600)
        s -= h*3600
        m = int(s/60)
        s -= m*60
        s = int(s)
        return '{:02}:{:02}:{:02}'.format(h, m, s)
    
    def setup_ep_results(self, times, nodes, links, result_types=None):
        """Set up the results object (or file, etc.) for save_ep_line() calls to use.

        The basic implementation sets up a dictionary of pandas DataFrames with the keys
        being member names of the ResultsType class. If the items parameter is left blank,
        the function will use the items that were specified during object creation.
        If this too was blank, then all results parameters will be saved.

        """
        if result_types is None:
            result_types = self.items
        for member in result_types:
            if member.is_node:
                self.results.node[member.name] = pd.DataFrame(index=times, columns=nodes)
            elif member.is_link:
                self.results.link[member.name] = pd.DataFrame(index=times, columns=links)
            else:
                pass
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
            The report period
        result_type : str
            One of the type strings listed above
        values : numpy.array
            The values to save, in the node or link order specified earlier in the file

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
        elif result_type == ResultType.head:
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
            The information being saved
        values : numpy.array
            The values that go with the information

        """
        self.results.meta[element] = values

    def save_energy_line(self, pump_idx, pump_name, values):
        """Save pump energy from the output file.

        This method, by default, does nothing. It is available to be overloaded
        in order to save information for pump energy calculations.

        Parameters
        ----------
        pump_idx : int
            the pump index
        pump_name : str
            the pump name
        values : numpy.array
            the values to save
			
        """
        pass

    def finalize_save(self, good_read, sim_warnings):
        """Post-process data before writing results.
        
        This method, by default, does nothing. It is available to be overloaded 
        in order to post process data.
        
        Parameters
        ----------
        good_read : bool
            was the full file read correctly
        sim_warnings : int
            were there warnings issued during the simulation
			
        """
        pass

#    @run_lineprofile()
    def read(self, filename, convergence_error=False, custom_handlers=False):
        """Read a binary file and create a results object.

        Parameters
        ----------
        filename : str
            An EPANET BIN output file
        convergence_error: bool (optional)
            If convergence_error is True, an error will be raised if the
            simulation does not converge. If convergence_error is False, partial results are returned, 
            a warning will be issued, and results.error_code will be set to 0
            if the simulation does not converge.  Default = False.
        custom_handlers : bool, optional
            If true, then the the custom, by-line handlers will be used. (:func:`~save_ep_line`, 
            :func:`~setup_ep_results`, :func:`~finalize_save`, etc.) Otherwise read will use
            a faster, all-at-once reader that reads all results.

        Returns
        -------
        object
            returns a WaterNetworkResults object

        .. note:: Overloading
            This function should **not** be overloaded. Instead, overload the other functions
            to change how it saves the results. Specifically, overload :func:`~setup_ep_results`,
            :func:`~save_ep_line` and :func:`~finalize_save` to change how extended period
            simulation results in a different format (such as directly to a file or database).
            
        """
        self.results = wntr.sim.SimulationResults()
        
        logger.debug('Read binary EPANET data from %s',filename)
        dt_str = '|S{}'.format(self.idlen)
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
            logger.debug('EPANET/Toolkit version %d',version)
            logger.debug('Nodes: %d; Tanks/Resrv: %d Links: %d; Pumps: %d; Valves: %d',
                         nnodes, ntanks, nlinks, npumps, nvalve)
            logger.debug('WQ opt: %s; Trace Node: %s; Flow Units %s; Pressure Units %s',
                         wqopt, srctrace, flowunits, presunits)
            logger.debug('Statistics: %s; Report Start %d, step %d; Duration=%d sec',
                         statsflag, reportstart, reportstep, duration)

            # Ignore the title lines
            np.fromfile(fin, dtype=np.uint8, count=240)
            inpfile = np.fromfile(fin, dtype=np.uint8, count=260)
            rptfile = np.fromfile(fin, dtype=np.uint8, count=260)
            chemical = str(np.fromfile(fin, dtype=dt_str, count=1)[0])
#            wqunits = ''.join([chr(f) for f in np.fromfile(fin, dtype=np.uint8, count=idlen) if f!=0 ])
            wqunits = str(np.fromfile(fin, dtype=dt_str, count=1)[0])
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
            self.report_file = rptfile
            nodenames = []
            linknames = []
            nodenames = np.array(np.fromfile(fin, dtype=dt_str, count=nnodes), dtype=str).tolist()
            linknames = np.array(np.fromfile(fin, dtype=dt_str, count=nlinks), dtype=str).tolist()
            self.node_names = nodenames
            self.link_names = linknames
            linkstart = np.array(np.fromfile(fin, dtype=np.int32, count=nlinks), dtype=int)
            linkend = np.array(np.fromfile(fin, dtype=np.int32, count=nlinks), dtype=int)
            linktype = np.fromfile(fin, dtype=np.int32, count=nlinks)
            tankidxs = np.fromfile(fin, dtype=np.int32, count=ntanks)
            tankarea = np.fromfile(fin, dtype=np.dtype(ftype), count=ntanks)
            elevation = np.fromfile(fin, dtype=np.dtype(ftype), count=nnodes)
            linklen = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
            diameter = np.fromfile(fin, dtype=np.dtype(ftype), count=nlinks)
            """
            self.save_network_desc_line('link_start', linkstart)
            self.save_network_desc_line('link_end', linkend)
            self.save_network_desc_line('link_type', linktype)
            self.save_network_desc_line('tank_node_index', tankidxs)
            self.save_network_desc_line('tank_area', tankarea)
            self.save_network_desc_line('node_elevation', elevation)
            self.save_network_desc_line('link_length', linklen)
            self.save_network_desc_line('link_diameter', diameter)
            """
            logger.debug('... read energy data ...')
            for i in range(npumps):
                pidx = int(np.fromfile(fin,dtype=np.int32, count=1))
                energy = np.fromfile(fin, dtype=np.dtype(ftype), count=6)
                self.save_energy_line(pidx, linknames[pidx-1], energy)
            peakenergy = np.fromfile(fin, dtype=np.dtype(ftype), count=1)
            self.peak_energy = peakenergy

            logger.debug('... read EP simulation data ...')
            reporttimes = np.arange(reportstart, duration+reportstep-(duration%reportstep), reportstep)
            nrptsteps = len(reporttimes)
            statsN = nrptsteps
            if statsflag in [StatisticsType.Maximum, StatisticsType.Minimum, StatisticsType.Range]:
                nrptsteps = 1
                reporttimes = [reportstart + reportstep]
            self.num_periods = nrptsteps
            self.report_times = reporttimes

            # set up results metadata dictionary
            """
            if wqopt == QualType.Age:
                self.results.meta['quality_mode'] = 'AGE'
                self.results.meta['quality_units'] = 's'
            elif wqopt == QualType.Trace:
                self.results.meta['quality_mode'] = 'TRACE'
                self.results.meta['quality_units'] = '%'
                self.results.meta['quality_trace'] = srctrace
            elif wqopt == QualType.Chem:
                self.results.meta['quality_mode'] = 'CHEMICAL'
                self.results.meta['quality_units'] = wqunits
                self.results.meta['quality_chem'] = chemical
            self.results.time = reporttimes
            self.save_network_desc_line('report_times', reporttimes)
            self.save_network_desc_line('node_elevation', pd.Series(data=elevation, index=nodenames))
            self.save_network_desc_line('link_length', pd.Series(data=linklen, index=linknames))
            self.save_network_desc_line('link_diameter', pd.Series(data=diameter, index=linknames))
            self.save_network_desc_line('stats_mode', statsflag)
            self.save_network_desc_line('stats_N', statsN)
            nodetypes = np.array(['Junction']*self.num_nodes, dtype='|S10')
            nodetypes[tankidxs-1] = 'Tank'
            nodetypes[tankidxs[tankarea==0]-1] = 'Reservoir'
            linktypes = np.array(['Pipe']*self.num_links)
            linktypes[ linktype == EN.PUMP ] = 'Pump'
            linktypes[ linktype > EN.PUMP ] = 'Valve'
            self.save_network_desc_line('link_type', pd.Series(data=linktypes, index=linknames, copy=True))
            linktypes[ linktype == EN.CVPIPE ] = 'CV'
            linktypes[ linktype == EN.FCV ] = 'FCV'
            linktypes[ linktype == EN.PRV ] = 'PRV'
            linktypes[ linktype == EN.PSV ] = 'PSV'
            linktypes[ linktype == EN.PBV ] = 'PBV'
            linktypes[ linktype == EN.TCV ] = 'TCV'
            linktypes[ linktype == EN.GPV ] = 'GPV'
            self.save_network_desc_line('link_subtype', pd.Series(data=linktypes, index=linknames, copy=True))
            self.save_network_desc_line('node_type', pd.Series(data=nodetypes, index=nodenames, copy=True))
            self.save_network_desc_line('node_names', np.array(nodenames, dtype=str))
            self.save_network_desc_line('link_names', np.array(linknames, dtype=str))
            names = np.array(nodenames, dtype=str)
            self.save_network_desc_line('link_start', pd.Series(data=names[linkstart-1], index=linknames, copy=True))
            self.save_network_desc_line('link_end', pd.Series(data=names[linkend-1], index=linknames, copy=True))
            """
            if custom_handlers is True:  
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
            else:
#                type_list = 4*nnodes*['node'] + 8*nlinks*['link']
                name_list = nodenames*4 + linknames*8
                valuetype = nnodes*['demand']+nnodes*['head']+nnodes*['pressure']+nnodes*['quality'] + nlinks*['flow']+nlinks*['velocity']+nlinks*['headloss']+nlinks*['linkquality']+nlinks*['linkstatus']+nlinks*['linksetting']+nlinks*['reactionrate']+nlinks*['frictionfactor']
                
#                tuples = zip(type_list, valuetype, name_list)
                tuples = list(zip(valuetype, name_list))
#                tuples = [(valuetype[i], v) for i, v in enumerate(name_list)]
                index = pd.MultiIndex.from_tuples(tuples, names=['value','name'])      
                
                try:
                    data = np.fromfile(fin, dtype = np.dtype(ftype), count = (4*nnodes+8*nlinks)*nrptsteps)
                except Exception as e:
                    logger.exception('Failed to process file: %s', e)
                    
                N = int(np.floor(len(data)/(4*nnodes+8*nlinks)))
                if N < nrptsteps:
                    t = reporttimes[N]
                    if convergence_error:
                        logger.error('Simulation did not converge at time ' + self._get_time(t) + '.')
                        raise RuntimeError('Simulation did not converge at time ' + self._get_time(t) + '.')
                    else:
                        data = data[0:N*(4*nnodes+8*nlinks)]
                        data = np.reshape(data, (N, (4*nnodes+8*nlinks)))
                        reporttimes = reporttimes[0:N]
                        warnings.warn('Simulation did not converge at time ' + self._get_time(t) + '.')
                        self.results.error_code = wntr.sim.results.ResultsStatus.error
                else:
                    data = np.reshape(data, (nrptsteps, (4*nnodes+8*nlinks)))
                    self.results.error_code = None

                df = pd.DataFrame(data.transpose(), index =index, columns = reporttimes)
                df = df.transpose()
                
                self.results.node = {}
                self.results.link = {}
                self.results.network_name = self.inp_file
                
                # Node Results
                self.results.node['demand'] = HydParam.Demand._to_si(self.flow_units, df['demand'])
                self.results.node['head'] = HydParam.HydraulicHead._to_si(self.flow_units, df['head'])
                self.results.node['pressure'] = HydParam.Pressure._to_si(self.flow_units, df['pressure'])

                # Water Quality Results (node and link)
                if self.quality_type is QualType.Chem:
                    self.results.node['quality'] = QualParam.Concentration._to_si(self.flow_units, df['quality'], mass_units=self.mass_units)
                    self.results.link['quality'] = QualParam.Concentration._to_si(self.flow_units, df['linkquality'], mass_units=self.mass_units)
                elif self.quality_type is QualType.Age:
                    self.results.node['quality'] = QualParam.WaterAge._to_si(self.flow_units, df['quality'], mass_units=self.mass_units)
                    self.results.link['quality'] = QualParam.WaterAge._to_si(self.flow_units, df['linkquality'], mass_units=self.mass_units)
                else:
                    self.results.node['quality'] = df['quality']
                    self.results.link['quality'] = df['linkquality']

                # Link Results
                self.results.link['flowrate'] = HydParam.Flow._to_si(self.flow_units, df['flow'])
                self.results.link['headloss'] = df['headloss']  # Unit is per 1000
                self.results.link['velocity'] = HydParam.Velocity._to_si(self.flow_units, df['velocity'])
                
#                self.results.link['status'] = df['linkstatus']
                status = np.array(df['linkstatus'])
                if self.convert_status:
                    status[status <= 2] = 0
                    status[status == 3] = 1
                    status[status >= 5] = 1
                    status[status == 4] = 2
                self.results.link['status'] = pd.DataFrame(data=status, columns=linknames, index=reporttimes)
                
                settings = np.array(df['linksetting'])
                settings[:, linktype == EN.PRV] = to_si(self.flow_units, settings[:, linktype == EN.PRV], HydParam.Pressure)
                settings[:, linktype == EN.PSV] = to_si(self.flow_units, settings[:, linktype == EN.PSV], HydParam.Pressure)
                settings[:, linktype == EN.PBV] = to_si(self.flow_units, settings[:, linktype == EN.PBV], HydParam.Pressure)
                settings[:, linktype == EN.FCV] = to_si(self.flow_units, settings[:, linktype == EN.FCV], HydParam.Flow)
                self.results.link['setting'] = pd.DataFrame(data=settings, columns=linknames, index=reporttimes)
                self.results.link['friction_factor'] = df['frictionfactor']
                self.results.link['reaction_rate'] = df['reactionrate']
                
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


class NoSectionError(Exception):
    pass


class _InpFileDifferHelper(object):  # pragma: no cover
    def __init__(self, f):
        """
        Parameters
        ----------
        f: str
        """
        self._f = open(f, 'r')
        self._num_lines = len(self._f.readlines())
        self._end = self._f.tell()
        self._f.seek(0)

    @property
    def f(self):
        return self._f

    def iter(self, start=0, stop=None, skip_section_headings=True):
        if stop is None:
            stop = self._end
        f = self.f
        f.seek(start)
        while f.tell() != stop:
            loc = f.tell()
            line = f.readline()
            if line.startswith(';'):
                continue
            if skip_section_headings:
                if line.startswith('['):
                    continue
            if len(line.split()) == 0:
                continue
            line = line.split(';')[0]
            yield loc, line

    def get_section(self, sec):
        """
        Parameters
        ----------
        sec: str
            The section

        Returns
        -------
        start: int
            The starting point in the file for sec
        end: int
            The ending point in the file for sec
			
        """
        start = None
        end = None
        in_sec = False
        for loc, line in self.iter(0, None, skip_section_headings=False):
            line = line.split(';')[0]
            if sec in line:
                start = loc
                in_sec = True
            elif '[' in line:
                if in_sec:
                    end = loc
                    in_sec = False
                    break
        if start is None:
            raise NoSectionError('Could not find section ' + sec)
        if end is None:
            end = self._end
        return start, end

    def contains_section(self, sec):
        """
        Parameters
        ----------
        sec: str
        """
        try:
            self.get_section(sec)
            return True
        except NoSectionError:
            return False


def _convert_line(line):  # pragma: no cover
    """
    Parameters
    ----------
    line: str

    Returns
    -------
    list
	
    """
    line = line.upper().split()
    tmp = []
    for i in line:
        if '.' in i:
            try:
                tmp.append(float(i))
            except:
                tmp.append(i)
        else:
            try:
                tmp.append(int(i))
            except:
                tmp.append(i)
    return tmp


def _compare_lines(line1, line2, tol=1e-14):  # pragma: no cover
    """
    Parameters
    ----------
    line1: list of str
    line2: list of str

    Returns
    -------
    bool
	
    """
    if len(line1) != len(line2):
        return False

    for i, a in enumerate(line1):
        b = line2[i]
        if type(a) not in {int, float}:
            if a != b:
                return False
        elif type(a) is int and type(b) is int:
            if a != b:
                return False
        elif type(a) in {int, float} and type(b) in {int, float}:
            if abs(a - b) > tol:
                return False
        else:
            if a != b:
                return False

    return True


def _clean_line(wn, sec, line):  # pragma: no cover
    """
    Parameters
    ----------
    wn: wntr.network.WaterNetworkModel
    sec: str
    line: list of str

    Returns
    -------
    new_list: list of str
	
    """
    if sec == '[JUNCTIONS]':
        if len(line) == 4:
            other = wn.options.hydraulic.pattern
            if other is None:
                other = 1
            if (type(line[3]) is int) and (other is int):
                other = int(other)
            if line[3] == other:
                return line[:3]

    return line

def _diff_inp_files(file1, file2=None, float_tol=1e-8, max_diff_lines_per_section=5, 
                    htmldiff_file='diff.html'):   # pragma: no cover
    """
    Parameters
    ----------
    file1: str
    file2: str
    float_tol: float
    max_diff_lines_per_section: int
    htmldiff_file: str
    """
    wn = InpFile().read(file1)
    f1 = _InpFileDifferHelper(file1)
    if file2 is None:
        file2 = 'temp.inp'
        wn.write_inpfile(file2)
    f2 = _InpFileDifferHelper(file2)

    different_lines_1 = []
    different_lines_2 = []
    n = 0
    
    for section in _INP_SECTIONS:
        if not f1.contains_section(section):
            if f2.contains_section(section):
                print('\tfile1 does not contain section {0} but file2 does.'.format(section))
            continue
        start1, stop1 = f1.get_section(section)
        start2, stop2 = f2.get_section(section)

        if section == '[PATTERNS]':
            new_lines_1 = []
            new_lines_2 = []
            label = None
            tmp_line = None
            tmp_loc = None
            for loc1, line1 in f1.iter(start1, stop1):
                tmp_label = line1.split()[0]
                if tmp_label != label:
                    if label is not None:
                        new_lines_1.append((tmp_loc, tmp_line))
                    tmp_loc = loc1
                    tmp_line = line1
                    label = tmp_label
                else:
                    tmp_line += " " + " ".join(line1.split()[1:])
            if tmp_line is not None:
                new_lines_1.append((tmp_loc, tmp_line))
            label = None
            tmp_line = None
            tmp_loc = None
            for loc2, line2 in f2.iter(start2, stop2):
                tmp_label = line2.split()[0]
                if tmp_label != label:
                    if label is not None:
                        new_lines_2.append((tmp_loc, tmp_line))
                    tmp_loc = loc2
                    tmp_line = line2
                    label = tmp_label
                else:
                    tmp_line += " " + " ".join(line2.split()[1:])
            if tmp_line is not None:
                new_lines_2.append((tmp_loc, tmp_line))
        else:
            new_lines_1 = list(f1.iter(start1, stop1))
            new_lines_2 = list(f2.iter(start2, stop2))

        different_lines_1.append(section)
        different_lines_2.append(section)

        if len(new_lines_1) != len(new_lines_2):
            assert len(different_lines_1) == len(different_lines_2)
            n1 = 0
            n2 = 0
            for loc1, line1 in new_lines_1:
                different_lines_1.append(line1)
                n1 += 1
            for loc2, line2 in new_lines_2:
                different_lines_2.append(line2)
                n2 += 1
            if n1 > n2:
                n = n1 - n2
                for i in range(n):
                    different_lines_2.append("")
            elif n2 > n1:
                n = n2 - n1
                for i in range(n):
                    different_lines_1.append("")
            else:
                raise RuntimeError('Unexpected')
            continue
        
        section_line_counter = 0
        f2_iter = iter(new_lines_2)
        for loc1, line1 in new_lines_1:
            orig_line_1 = line1
            loc2, line2 = next(f2_iter)
            orig_line_2 = line2
            line1 = _convert_line(line1)
            line2 = _convert_line(line2)
            line1 = _clean_line(wn, section, line1)
            line2 = _clean_line(wn, section, line2)
            if not _compare_lines(line1, line2, tol=float_tol):
                if section_line_counter < max_diff_lines_per_section:
                    section_line_counter = section_line_counter+1
                else:
                    break
                different_lines_1.append(orig_line_1)
                different_lines_2.append(orig_line_2)
    
    if len(different_lines_1) < 200: # If lines < 200 use difflib
        differ = difflib.HtmlDiff()
        html_diff = differ.make_file(different_lines_1, different_lines_2)
    else: # otherwise, create a simple html file
        differ_df = pd.DataFrame([different_lines_1, different_lines_2], 
                           index=[file1, file2]).transpose()
        html_diff = differ_df.to_html()
        
    g = open(htmldiff_file, 'w')
    g.write(html_diff)
    g.close()
    
    return n
