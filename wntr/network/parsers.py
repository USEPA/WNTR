# -*- coding: utf-8 -*-
"""
Created on Mon Dec 12 10:00:59 2016

@author: dbhart
"""
from wntr.utils.units import FlowUnits, MassUnits, QualParam, HydParam
import wntr.network
from wntr.network import WaterNetworkModel, Junction, Reservoir, Tank, Pipe, Pump, Valve, LinkStatus
import wntr

import datetime
import networkx as nx
import re
import logging
import numpy as np

logger = logging.getLogger(__name__)

_INP_SECTIONS = ['[OPTIONS]', '[TITLE]', '[JUNCTIONS]', '[RESERVOIRS]',
                 '[TANKS]', '[PIPES]', '[PUMPS]', '[VALVES]', '[EMITTERS]',
                 '[CURVES]', '[PATTERNS]', '[ENERGY]', '[STATUS]',
                 '[CONTROLS]', '[RULES]', '[DEMANDS]', '[QUALITY]',
                 '[REACTIONS]', '[SOURCES]', '[MIXING]',
                 '[TIMES]', '[REPORT]', '[COORDINATES]', '[VERTICES]',
                 '[LABELS]', '[BACKDROP]', '[TAGS]']

_JUNC_ENTRY = ' {name:20} {elev:12f} {dem:12f} {pat:24} {com:>3s}\n'
_JUNC_LABEL = '{:21} {:>12s} {:>12s} {:24}\n'

_RES_ENTRY = ' {name:20s} {head:12f} {pat:>24s} {com:>3s}\n'
_RES_LABEL = '{:21s} {:>12s} {:>24s}\n'

_TANK_ENTRY = ' {name:20s} {elev:12f} {initlev:12f} {minlev:12f} {maxlev:12f} {diam:12f} {minvol:12f} {curve:20s} {com:>3s}\n'
_TANK_LABEL = '{:21s} {:>12s} {:>12s} {:>12s} {:>12s} {:>12s} {:>12s} {:20s}\n'

_PIPE_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {len:12f} {diam:12f} {rough:12f} {mloss:12f} {status:>20s} {com:>3s}\n'
_PIPE_LABEL = '{:21s} {:20s} {:20s} {:>12s} {:>12s} {:>12s} {:>12s} {:>20s}\n'

_PUMP_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {ptype:8s} {params:20s} {com:>3s}\n'
_PUMP_LABEL = '{:21s} {:20s} {:20s} {:20s}\n'

_VALVE_ENTRY = ' {name:20s} {node1:20s} {node2:20s} {diam:12f} {vtype:4s} {set:12f} {mloss:12f} {com:>3s}\n'
_VALVE_LABEL = '{:21s} {:20s} {:20s} {:>12s} {:4s} {:>12s} {:>12s}\n'

_CURVE_ENTRY = '{name:10s} {x:12f} {y:12f} {com:>3s}\n'
_CURVE_LABEL = '{:10s} {:12s} {:12s}\n'

def is_number(s):
    """
    Checks if imput is a number

    Parameters
    ----------
    s : anything
    """

    try:
        float(s)
        return True
    except ValueError:
        return False


def str_time_to_sec(s):
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


def clock_time_to_sec(s, am_pm):
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


class EN2InpFile(object):
    def __init__(self):
        self.sections = {}
        for sec in _INP_SECTIONS:
            self.sections[sec] = []
        self.mass_units = None
        self.flow_units = None
        self.top_comments = []
        self.curves = {}

    def parse(self, filename, wn=None):
        """Method to read EPANET INP file and load data into a water network object."""
        if wn is None:
            wn = WaterNetworkModel()
        wn.name = filename
        opts = wn.options

        _patterns = {}
        self.curves = {}
        self.top_comments = []
        self.sections = {}
        for sec in _INP_SECTIONS:
            self.sections[sec] = []
        self.mass_units = None
        self.flow_units = None

        def split_line(line):
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

        section = None
        lnum = 0
        edata = {'fname': filename}
        with open(filename, 'r') as f:
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
                        logger.info('%(fname)s:%(lnum)-6d %(sec)13s section found' % edata)
                        continue
                    elif sec == '[END]':
                        logger.info('%(fname)s:%(lnum)-6d %(sec)13s end of file found' % edata)
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
        for lnum, line in self.sections['[OPTIONS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[OPTIONS]'
            words, comments = split_line(line)
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
                    opts.hydraulics_option = words[1].upper()
                    opts.hydraulics_filename = words[2]
                elif key == 'QUALITY':
                    opts.quality_option = words[1].upper()
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
                    opts.specific_gravity = int(words[1])
                elif key == 'ACCURACY':
                    opts.accuracy = float(words[1])
                elif key == 'UNBALANCED':
                    opts.unbalanced_option = words[1].upper()
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
                    opts.tolerance = float(words[1])
                elif key == 'MAXCHECK':
                    opts.tolerance = float(words[1])
                elif key == 'DAMPLIMIT':
                    opts.tolerance = float(words[1])
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

        inp_units = self.flow_units
        mass_units = self.mass_units

        if (type(opts.report_timestep) == float or
                type(opts.report_timestep) == int):
            if opts.report_timestep < opts.hydraulic_timestep:
                raise RuntimeError('opts.report_timestep must be greater than or equal to opts.hydraulic_timestep.')
            if opts.report_timestep % opts.hydraulic_timestep != 0:
                raise RuntimeError('opts.report_timestep must be a multiple of opts.hydraulic_timestep')

        for lnum, line in self.sections['[CURVES]']:
            # It should be noted carefully that these lines are never directly
            # applied to the WaterNetworkModel object. Because different curve
            # types are treated differently, each of the curves are converted
            # the first time they are used, and this is used to build up a
            # dictionary for those conversions to take place.
            edata['lnum'] = lnum
            edata['sec'] = '[CURVES]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            curve_name = current[0]
            if curve_name not in self.curves:
                self.curves[curve_name] = []
            self.curves[curve_name].append((float(current[1]),
                                             float(current[2])))

        for lnum, line in self.sections['[PATTERNS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[PATTERNS]'
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

        for pattern_name, pattern_list in _patterns.iteritems():
            wn.add_pattern(pattern_name, pattern_list)

        for lnum, line in self.sections['[JUNCTIONS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[JUNCTIONS]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) == 3:
                wn.add_junction(current[0],
                                HydParam.Demand.to_si(inp_units, float(current[2])),
                                None,
                                HydParam.Elevation.to_si(inp_units, float(current[1])))
            else:
                wn.add_junction(current[0],
                                HydParam.Demand.to_si(inp_units, float(current[2])),
                                current[3],
                                HydParam.Elevation.to_si(inp_units, float(current[1])))

        for lnum, line in self.sections['[RESERVOIRS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[RESERVOIRS]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) == 2:
                wn.add_reservoir(current[0],
                                 HydParam.HydraulicHead.to_si(inp_units, float(current[1])))
            else:
                wn.add_reservoir(current[0],
                                 HydParam.HydraulicHead.to_si(inp_units, float(current[1])),
                                 current[2])
                logger.warn('%(fname)s:%(lnum)-6d %(sec)13s reservoir head patterns only supported in EpanetSimulator', edata)

        for lnum, line in self.sections['[TANKS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[TANKS]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) == 8:  # Volume curve provided
                if float(current[6]) != 0:
                    logger.warn('%(fname)s:%(lnum)-6d %(sec)13s minimum tank volume is only available using EpanetSimulator; others use minimum level and cylindrical tanks.', edata)
                logger.warn('<%(fname)s:%(sec)s:%(line)d> tank volume curves only supported in EpanetSimulator', edata)
                curve_name = current[7]
                curve_points = []
                for point in self.curves[curve_name]:
                    x = HydParam.Length.to_si(inp_units, point[0])
                    y = HydParam.Volume.to_si(inp_units, point[1])
                    curve_points.append((x, y))
                wn.add_curve(curve_name, 'VOLUME', curve_points)
                curve = wn.get_curve(curve_name)
                wn.add_tank(current[0],
                            HydParam.Elevation.to_si(inp_units, float(current[1])),
                            HydParam.Length.to_si(inp_units, float(current[2])),
                            HydParam.Length.to_si(inp_units, float(current[3])),
                            HydParam.Length.to_si(inp_units, float(current[4])),
                            HydParam.TankDiameter.to_si(inp_units, float(current[5])),
                            HydParam.Volume.to_si(inp_units, float(current[6])),
                            curve)
            elif len(current) == 7:  # No volume curve provided
                if float(current[6]) != 0:
                    logger.warn('%(fname)s:%(lnum)-6d %(sec)13s minimum tank volume is only available using EpanetSimulator; others use minimum level and cylindrical tanks.', edata)
                wn.add_tank(current[0],
                            HydParam.Elevation.to_si(inp_units, float(current[1])),
                            HydParam.Length.to_si(inp_units, float(current[2])),
                            HydParam.Length.to_si(inp_units, float(current[3])),
                            HydParam.Length.to_si(inp_units, float(current[4])),
                            HydParam.TankDiameter.to_si(inp_units, float(current[5])),
                            HydParam.Volume.to_si(inp_units, float(current[6])))
            else:
                edata['line'] = line
                logger.error('%(fname)s:%(lnum)-6d %(sec)13s tank entry format not recognized: "%(line)s"', edata)
                raise RuntimeError('Tank entry format not recognized.')

        for lnum, line in self.sections['[PIPES]']:
            edata['lnum'] = lnum
            edata['sec'] = '[PIPES]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if float(current[6]) != 0:
                logger.warn('%(fname)s:%(lnum)-6d %(sec)13s non-zero minor losses only supported in EpanetSimulator', edata)
            if current[7].upper() == 'CV':
                wn.add_pipe(current[0],
                            current[1],
                            current[2],
                            HydParam.Length.to_si(inp_units, float(current[3])),
                            HydParam.PipeDiameter.to_si(inp_units, float(current[4])),
                            float(current[5]),
                            float(current[6]),
                            'OPEN',
                            True)
            else:
                wn.add_pipe(current[0],
                            current[1],
                            current[2],
                            HydParam.Length.to_si(inp_units, float(current[3])),
                            HydParam.PipeDiameter.to_si(inp_units, float(current[4])),
                            float(current[5]),
                            float(current[6]),
                            current[7].upper())

        for lnum, line in self.sections['[PUMPS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[PUMPS]'
            edata['line'] = line
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            # Only add head curves for pumps
            if current[3].upper() == 'SPEED':
                logger.warning('%(fname)s:%(lnum)-6d %(sec)13s speed settings for pumps are currently only supported in the EpanetSimulator.', edata)
                continue
            elif current[3].upper() == 'PATTERN':
                logger.warning('%(fname)s:%(lnum)-6d %(sec)13s speed patterns for pumps are currently only supported in the EpanetSimulator.', edata)
                continue
            elif current[3].upper() == 'HEAD':
                curve_name = current[4]
                curve_points = []
                for point in self.curves[curve_name]:
                    x = HydParam.Flow.to_si(inp_units, point[0])
                    y = HydParam.HydraulicHead.to_si(inp_units, point[1])
                    curve_points.append((x, y))
                wn.add_curve(curve_name, 'HEAD', curve_points)
                curve = wn.get_curve(curve_name)
                wn.add_pump(current[0],
                            current[1],
                            current[2],
                            'HEAD',
                            curve)
            elif current[3].upper() == 'POWER':
                wn.add_pump(current[0],
                            current[1],
                            current[2],
                            current[3].upper(),
                            HydParam.Power.to_si(inp_units, float(current[4])))
            else:
                logger.error('%(fname)s:%(lnum)-6d %(sec)13s pump keyword not recognized: "%(line)s"', edata)
                raise RuntimeError('Pump keyword in inp file not recognized.')

        for lnum, line in self.sections['[VALVES]']:
            edata['lnum'] = lnum
            edata['sec'] = '[VALVES]'
            edata['line'] = line
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if len(current) < 7:
                current[6] = 0
            valve_type = current[4].upper()
            if valve_type != 'PRV':
                logger.warning("%(fname)s:%(lnum)-6d %(sec)13s only PRV valves are currently supported.", edata)
            if float(current[6]) != 0:
                logger.warning('%(fname)s:%(lnum)-6d %(sec)13s currently, only the EpanetSimulator supports non-zero minor losses in valves.', edata)
            if valve_type in ['PRV', 'PSV', 'PBV']:
                valve_set = HydParam.Pressure.to_si(inp_units, float(current[5]))
            elif valve_type == 'FCV':
                valve_set = HydParam.Flow.to_si(inp_units, float(current[5]))
            elif valve_type == 'TCV':
                valve_set = float(current[5])
            elif valve_type == 'GPV':
                valve_set = current[5]
            else:
                logger.error('%(fname)s:%(lnum)-6d %(sec)13s valve type unrecognized: %(line)s', edata)
                raise RuntimeError('VALVE type "%s" unrecognized' % valve_type)
            wn.add_valve(current[0],
                         current[1],
                         current[2],
                         HydParam.PipeDiameter.to_si(inp_units, float(current[3])),
                         current[4].upper(),
                         float(current[6]),
                         valve_set)

        for lnum, line in self.sections['[COORDINATES]']:
            edata['lnum'] = lnum
            edata['sec'] = '[COORDINATES]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            assert(len(current) == 3), ("Error reading node coordinates. Check format.")
            wn.set_node_coordinates(current[0], (float(current[1]), float(current[2])))

        time_format = ['am', 'AM', 'pm', 'PM']
        for lnum, line in self.sections['[TIMES]']:
            edata['lnum'] = lnum
            edata['sec'] = '[TIMES]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            if (current[0].upper() == 'DURATION'):
                opts.duration = str_time_to_sec(current[1])
            elif (current[0].upper() == 'HYDRAULIC'):
                opts.hydraulic_timestep = str_time_to_sec(current[2])
            elif (current[0].upper() == 'QUALITY'):
                opts.quality_timestep = str_time_to_sec(current[2])
            elif (current[1].upper() == 'CLOCKTIME'):
                [time, time_format] = [current[2], current[3].upper()]
                opts.start_clocktime = clock_time_to_sec(time, time_format)
            elif (current[0].upper() == 'STATISTIC'):
                opts.statistic = current[1].upper()
            else:  # Other time options
                key_string = current[0] + '_' + current[1]
                setattr(opts, key_string.lower(), str_time_to_sec(current[2]))

        if opts.pattern_start != 0.0:
            logger.warning('Currently, only the EpanetSimulator supports a non-zero patern start time.')

        if opts.report_start != 0.0:
            logger.warning('Currently, only the EpanetSimulator supports a non-zero report start time.')

        if opts.report_timestep != opts.hydraulic_timestep:
            logger.warning('Currently, only a the EpanetSimulator supports a report timestep that is not equal to the hydraulic timestep.')

        if opts.start_clocktime != 0.0:
            logger.warning('Currently, only the EpanetSimulator supports a start clocktime other than 12 am.')

        if opts.statistic != 'NONE':
            logger.warning('Currently, only the EpanetSimulator supports the STATISTIC option in the inp file.')

        for lnum, line in self.sections['[STATUS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[STATUS]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            assert(len(current) == 2), ("Error reading [STATUS] block, Check format.")
            link = wn.get_link(current[0])
            if (current[1].upper() == 'OPEN' or
                    current[1].upper() == 'CLOSED' or
                    current[1].upper() == 'ACTIVE'):
                new_status = wntr.network.LinkStatus.str_to_status(current[1])
                link.status = new_status
                link._base_status = new_status
            else:
                if isinstance(link, wntr.network.Pump):
                    logger.warning('Currently, pump speed settings are only supported in the EpanetSimulator.')
                    continue
                elif isinstance(link, wntr.network.Valve):
                    if link.valve_type != 'PRV':
                        logger.warning('Currently, valves of type ' + link.valve_type + ' are only supported in the EpanetSimulator.')
                        continue
                    else:
                        setting = HydParam.Pressure.to_si(inp_units,
                                                          float(current[2]))
                        link.setting = setting
                        link._base_setting = setting

        for lnum, line in self.sections['[CONTROLS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[CONTROLS]'
            line = line.split(';')[0]
            current = line.split()
            if current == []:
                continue
            current_copy = current
            current = [i.upper() for i in current]
            current[1] = current_copy[1]  # don't capitalize the link name

            # Create the control action object
            link_name = current[1]
            # print (link_name in wn._links.keys())
            link = wn.get_link(link_name)
            if type(current[2]) == str:
                status = wntr.network.LinkStatus.str_to_status(current[2])
                action_obj = wntr.network.ControlAction(link, 'status', status)
            elif type(current[2]) == float or type(current[2]) == int:
                if isinstance(link, wntr.network.Pump):
                    logger.warning('Currently, pump speed settings are only supported in the EpanetSimulator.')
                    continue
                elif isinstance(link, wntr.network.Valve):
                    if link.valve_type != 'PRV':
                        logger.warning('Currently, valves of type %s are only supported in the EpanetSimulator.',link.valve_type)
                        continue
                    else:
                        status = HydParam.Pressure.to_si(inp_units,
                                                         float(current[2]))
                        action_obj = wntr.network.ControlAction(link, 'setting', status)

            # Create the control object
            if 'TIME' not in current and 'CLOCKTIME' not in current:
                current[5] = current_copy[5]
                if 'IF' in current:
                    node_name = current[5]
                    node = wn.get_node(node_name)
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
                        threshold = HydParam.Pressure.to_si(inp_units, float(current[7])) + node.elevation
                    elif isinstance(node, wntr.network.Tank):
                        threshold = HydParam.Length.to_si(inp_units,  float(current[7])) + node.elevation
                    control_obj = wntr.network.ConditionalControl((node, 'head'), oper, threshold, action_obj)
                else:
                    raise RuntimeError("The following control is not recognized: " + line)
                control_name = ''
                for i in xrange(len(current)-1):
                    control_name = control_name + current[i]
                control_name = control_name + str(round(threshold, 2))
            else:
                if len(current) != 6:
                    logger.warning('Using CLOCKTIME in time controls is currently only supported by the EpanetSimulator.')
                if len(current) == 6:  # at time
                    if ':' in current[5]:
                        fire_time = str_time_to_sec(current[5])
                    else:
                        fire_time = int(float(current[5])*3600)
                    control_obj = wntr.network.TimeControl(wn, fire_time, 'SIM_TIME', False, action_obj)
                    control_name = ''
                    for i in xrange(len(current)-1):
                        control_name = control_name + current[i]
                    control_name = control_name + str(fire_time)
                elif len(current) == 7:  # at clocktime
                    fire_time = clock_time_to_sec(current[5], current[6])
                    control_obj = wntr.network.TimeControl(wn, fire_time, 'SHIFTED_TIME', True, action_obj)
            wn.add_control(control_name, control_obj)

        BulkReactionCoeff = QualParam.BulkReactionCoeff
        WallReactionCoeff = QualParam.WallReactionCoeff
        for lnum, line in self.sections['[REACTIONS]']:
            edata['lnum'] = lnum
            edata['sec'] = '[REACTIONS]'
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
                    opts.bulk_rxn_coeff = BulkReactionCoeff.to_si(inp_units, val3, mass_units, opts.bulk_rxn_order)
                elif key2 == 'WALL':
                    opts.wall_rxn_coeff = WallReactionCoeff.to_si(inp_units, val3, mass_units, opts.wall_rxn_order)
            elif key1 == 'BULK':
                pipe = wn.get_link(current[1])
                pipe.bulk_rxn_coeff = BulkReactionCoeff.to_si(inp_units, val3, mass_units, opts.bulk_rxn_order)
            elif key1 == 'WALL':
                pipe = wn.get_link(current[1])
                pipe.wall_rxn_coeff = WallReactionCoeff.to_si(inp_units, val3, mass_units, opts.wall_rxn_order)
            elif key1 == 'TANK':
                tank = wn.get_node(current[1])
                tank.bulk_rxn_coeff = BulkReactionCoeff.to_si(inp_units, val3, mass_units, opts.bulk_rxn_order)
            elif key1 == 'LIMITING':
                opts.limiting_potential = float(current[2])
            elif key1 == 'ROUGHNESS':
                opts.roughness_correlation = float(current[2])
            else:
                raise RuntimeError('Reaction option not recognized')

        if len(self.sections['[TITLE]']) > 0:
            pass
            # wn._en_title = '\n'.join(self.sections['[TITLE]'])
        else:
            pass

        if len(self.sections['[ENERGY]']) > 0:
            # wn._en_energy = '\n'.join(self.sections['[ENERGY]'])
            logger.warning('ENERGY section is reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[RULES]']) > 0:
            # wn._en_rules = '\n'.join(self.sections['[RULES]'])
            logger.warning('RULES are reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[DEMANDS]']) > 0:
            # wn._en_demands = '\n'.join(self.sections['[DEMANDS]'])
            logger.warning('Multiple DEMANDS are reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[QUALITY]']) > 0:
            # wn._en_quality = '\n'.join(self.sections['[QUALITY]'])
            logger.warning('QUALITY section is reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[EMITTERS]']) > 0:
            # wn._en_emitters = '\n'.join(self.sections['[EMITTERS]'])
            logger.warning('EMITTERS are currently reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[SOURCES]']) > 0:
            logger.warning('SOURCES are currently reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[MIXING]']) > 0:
            logger.warning('MIXING is currently reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[REPORT]']) > 0:
            logger.warning('REPORT is currently reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[VERTICES]']) > 0:
            logger.warning('VERTICES are currently reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[LABELS]']) > 0:
            logger.warning('LABELS are currently reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[BACKDROP]']) > 0:
            logger.warning('BACKDROP is currently reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        if len(self.sections['[TAGS]']) > 0:
            logger.warning('TAGS are currently reapplied directly to an Epanet INP file on write; otherwise unsupported.')

        wn._en2data = self
        return wn

    def dump(self, filename, wn, units='GPM'):
        """Write the current network into an EPANET inp file.
        Parameters
        ----------
        filename : string
            Name of the inp file. example - Net3_adjusted_demands.inp
        wn : WaterNetworkModel
            The water network model to dump
        units : string
            Name of the units being written to the inp file

        """
        # TODO: This is still a very alpha version with hard coded unit conversions to LPS (among other things).

        units=units.upper()
        inp_units = FlowUnits[units]
        flowunit = int(inp_units)

        f = open(filename, 'w')

        # Print title
        if wn.name is not None:
            f.write('; Filename: {0}\n'.format(wn.name))
            f.write('; WNTR: {}\n; Created: {:%Y-%m-%d %H:%M:%S}\n'.format(wntr.__version__, datetime.datetime.now()))
        f.write('[TITLE]\n')
        for lnum, line in self.sections['[TITLE]']:
            f.write('{}\n'.format(line))
        f.write('\n')

        # Print junctions information
        f.write('[JUNCTIONS]\n')
        f.write(_JUNC_LABEL.format(';ID', 'Elevation', 'Demand', 'Pattern'))
        for junction_name, junction in wn.nodes(Junction):
            E = {'name': junction_name,
                 'elev': HydParam.Elevation.from_si(inp_units, junction.elevation),
                 'dem': HydParam.Demand.from_si(inp_units, junction.base_demand),
                 'pat': '',
                 'com': ';'}
            if junction.demand_pattern_name is not None:
                E['pat'] = junction.demand_pattern_name
            f.write(_JUNC_ENTRY.format(**E))
        f.write('\n')

        # Print reservoir information
        f.write('[RESERVOIRS]\n')
        f.write(_RES_LABEL.format(';ID', 'Head', 'Pattern'))
        for reservoir_name, reservoir in wn.nodes(Reservoir):
            E = {'name': reservoir_name,
                 'head': HydParam.HydraulicHead.from_si(inp_units, reservoir.base_head),
                 'com': ';'}
            if reservoir.head_pattern_name is None:
                E['pat'] = ''
            else:
                E['pat'] = reservoir.head_pattern_name
            f.write(_RES_ENTRY.format(**E))
        f.write('\n')

        # Print tank information
        f.write('[TANKS]\n')
        f.write(_TANK_LABEL.format(';ID', 'Elevation', 'Init Level', 'Min Level', 'Max Level',
                                   'Diameter', 'Min Volume', 'Volume Curve'))
        for tank_name, tank in wn.nodes(Tank):
            E = {'name': tank_name,
                 'elev': HydParam.Elevation.from_si(inp_units, tank.elevation),
                 'initlev': HydParam.HydraulicHead.from_si(inp_units, tank.init_level),
                 'minlev': HydParam.HydraulicHead.from_si(inp_units, tank.min_level),
                 'maxlev': HydParam.HydraulicHead.from_si(inp_units, tank.max_level),
                 'diam': HydParam.TankDiameter.from_si(inp_units, tank.diameter),
                 'minvol': HydParam.Volume.from_si(inp_units, tank.min_vol),
                 'curve': '',
                 'com': ';'}
            if tank.vol_curve is not None:
                E['curve'] = tank.vol_curve
            f.write(_TANK_ENTRY.format(**E))
        f.write('\n')

        # Print pipe information
        f.write('[PIPES]\n')
        f.write(_PIPE_LABEL.format(';ID', 'Node1', 'Node2', 'Length', 'Diameter',
                                   'Roughness', 'Minor Loss', 'Status'))
        for pipe_name, pipe in wn.links(Pipe):
            E = {'name': pipe_name,
                 'node1': pipe.start_node(),
                 'node2': pipe.end_node(),
                 'len': HydParam.Length.from_si(inp_units, pipe.length),
                 'diam': HydParam.PipeDiameter.from_si(inp_units, pipe.diameter),
                 'rough': pipe.roughness,
                 'mloss': pipe.minor_loss,
                 'status': LinkStatus.status_to_str(pipe.get_base_status()),
                 'com': ';'}
            if pipe.cv:
                E['status'] = 'CV'
            f.write(_PIPE_ENTRY.format(**E))
        f.write('\n')

        # Print pump information
        f.write('[PUMPS]\n')
        f.write(_PUMP_LABEL.format(';ID', 'Node1', 'Node2', 'Parameters'))
        for pump_name, pump in wn.links(Pump):
            E = {'name': pump_name,
                 'node1': pump.start_node(),
                 'node2': pump.end_node(),
                 'ptype': pump.info_type,
                 'params': '',
                 'com': ';'}
            if pump.info_type == 'HEAD':
                E['params'] = pump.curve.name
            elif pump.info_type == 'POWER':
                E['params'] = str(HydParam.Power.from_si(inp_units, pump.power))
            else:
                raise RuntimeError('Only head or power info is supported of pumps.')
            f.write(_PUMP_ENTRY.format(**E))
        f.write('\n')

        # Print valve information
        f.write('[VALVES]\n')
        f.write(_VALVE_LABEL.format(';ID', 'Node1', 'Node2', 'Diameter', 'Type', 'Setting', 'Minor Loss'))
        for valve_name, valve in wn.links(Valve):
            E = {'name': valve_name,
                 'node1': valve.start_node(),
                 'node2': valve.end_node(),
                 'diam': HydParam.PipeDiameter.from_si(inp_units, valve.diameter),
                 'vtype': valve.valve_type,
                 'set': valve._base_setting,
                 'mloss': valve.minor_loss,
                 'com': ';'}
            f.write(_VALVE_ENTRY.format(**E))
        f.write('\n')

        # Print status information
        f.write('[STATUS]\n')
        f.write( '{:10s} {:10s}\n'.format(';ID', 'Setting'))
        for link_name, link in wn.links(Pump):
            if link.get_base_status() == LinkStatus.closed:
                f.write('{:10s} {:10s}\n'.format(link_name,
                        LinkStatus.status_to_str(link.get_base_status())))
        for link_name, link in wn.links(Valve):
            if link.get_base_status() == LinkStatus.closed or link.get_base_status() == LinkStatus.opened:
                f.write('{:10s} {:10s}\n'.format(link_name,
                        LinkStatus.status_to_str(link.get_base_status())))
        f.write('\n')

        # Print pattern information
        num_columns = 8
        f.write('[PATTERNS]\n')
        f.write('{:10s} {:10s}\n'.format(';ID', 'Multipliers'))
        for pattern_name, pattern in wn._patterns.iteritems():
            count = 0
            for i in pattern:
                if count % num_columns == 0:
                    f.write('\n%s %f'%(pattern_name, i,))
                else:
                    f.write(' %f'%(i,))
                count += 1
            f.write('\n')
        f.write('\n')

        # Print curves
        f.write('[CURVES]\n')
        f.write(_CURVE_LABEL.format(';ID', 'X-Value', 'Y-Value'))
        for curve_name, curve in wn._curves.items():
            if curve.curve_type == 'VOLUME':
                f.write(';VOLUME: {}\n'.format(curve_name))
                for point in curve.points:
                    x = HydParam.Length.from_si(inp_units, point[0])
                    y = HydParam.Volume.from_si(inp_units, point[1])
                    f.write(_CURVE_ENTRY.format(name=curve_name, x=x, y=y, com=';'))
            elif curve.curve_type == 'HEAD':
                f.write(';HEAD: {}\n'.format(curve_name))
                for point in curve.points:
                    x = HydParam.Flow.from_si(inp_units, point[0])
                    y = HydParam.HydraulicHead.from_si(inp_units, point[1])
                    f.write(_CURVE_ENTRY.format(name=curve_name, x=x, y=y, com=';'))
            f.write('\n')
        for curve_name, curve in self.curves.items():
            if curve_name not in wn._curves.keys():
                for point in curve:
                    f.write(_CURVE_ENTRY.format(name=curve_name, x=point[0], y=point[1], com=';'))
                f.write('\n')
        f.write('\n')

        # Print Controls
        f.write( '[CONTROLS]\n')
        # Time controls and conditional controls only
        for text, all_control in wn._control_dict.items():
            if isinstance(all_control,wntr.network.TimeControl):
                f.write('%s\n'%all_control.to_inp_string())
            elif isinstance(all_control,wntr.network.ConditionalControl):
                f.write('%s\n'%all_control.to_inp_string(flowunit))
        f.write('\n')

        # Report
        f.write('[REPORT]\n')
        if len(self.sections['[REPORT]']) > 0:
            for lnum, line in self.sections['[REPORT]']:
                f.write('{}\n'.format(line))
        else:
            f.write('Status Yes\n')
            f.write('Summary yes\n')
        f.write('\n')

        # Options
        f.write('[OPTIONS]\n')
        entry_string = '{:20s} {:20s}\n'
        entry_float = '{:20s} {:g}\n'
        f.write(entry_string.format('UNITS', inp_units.name))
        f.write(entry_string.format('HEADLOSS', wn.options.headloss))
        if wn.options.hydraulics_option is not None:
            f.write('{:20s} {:s} {:<30s}\n'.format('HYDRAULICS', wn.options.hydraulics_option, wn.options.hydraulics_filename))
        if wn.options.quality_value is None:
            f.write(entry_string.format('QUALITY', wn.options.quality_option))
        else:
            f.write('{:20s} {} {}\n'.format('QUALITY', wn.options.quality_option, wn.options.quality_value))
        f.write(entry_float.format('VISCOSITY', wn.options.viscosity))
        f.write(entry_float.format('DIFFUSIVITY', wn.options.diffusivity))
        f.write(entry_float.format('SPECIFIC GRAVITY', wn.options.specific_gravity))
        f.write(entry_float.format('TRIALS', wn.options.trials))
        f.write(entry_float.format('ACCURACY', wn.options.accuracy))
        f.write(entry_float.format('CHECKFREQ', wn.options.checkfreq))
        if wn.options.unbalanced_value is None:
            f.write(entry_string.format('UNBALANCED', wn.options.unbalanced_option))
        else:
            f.write('{:20s} {:s} {:d}\n'.format('UNBALANCED', wn.options.unbalanced_option, wn.options.unbalanced_value))
        if wn.options.pattern is not None:
            f.write(entry_string.format('PATTERN', wn.options.pattern))
        f.write(entry_float.format('DEMAND MULTIPLIER', wn.options.demand_multiplier))
        f.write(entry_float.format('EMITTER EXPONENT', wn.options.emitter_exponent))
        f.write(entry_float.format('TOLERANCE', wn.options.tolerance))
        if wn.options.map is not None:
            f.write(entry_string.format('MAP', wn.options.map))

        f.write('\n')

        # Reaction Options
        f.write( '[REACTIONS]\n')
        entry_float = ' {:s} {:s} {:<10.8f}\n'
        f.write(entry_float.format('ORDER','BULK',wn.options.bulk_rxn_order))
        f.write(entry_float.format('ORDER','WALL',wn.options.wall_rxn_order))
        f.write(entry_float.format('ORDER','TANK',wn.options.tank_rxn_order))
        f.write(entry_float.format('GLOBAL','BULK',
                                   QualParam.BulkReactionCoeff.from_si(inp_units,
                                                                       wn.options.bulk_rxn_coeff,
                                                                       self.mass_units,
                                                                       wn.options.bulk_rxn_order)))
        f.write(entry_float.format('GLOBAL','WALL',
                                   QualParam.WallReactionCoeff.from_si(inp_units,
                                                                       wn.options.wall_rxn_coeff,
                                                                       self.mass_units,
                                                                       wn.options.wall_rxn_order)))
        if wn.options.limiting_potential is not None:
            f.write(entry_float.format('LIMITING','POTENTIAL',wn.options.limiting_potential))
        if wn.options.roughness_correlation is not None:
            f.write(entry_float.format('ROUGHNESS','CORRELATION',wn.options.roughness_correlation))
        for tank_name, tank in wn.nodes(Tank):
            if tank.bulk_rxn_coeff is not None:
                f.write(entry_float.format('TANK',tank_name,
                                           QualParam.BulkReactionCoeff.from_si(inp_units,
                                                                       tank.bulk_rxn_coeff,
                                                                       self.mass_units,
                                                                       wn.options.bulk_rxn_order)))
        for pipe_name, pipe in wn.links(Pipe):
            if pipe.bulk_rxn_coeff is not None:
                f.write(entry_float.format('BULK',pipe_name,
                                           QualParam.BulkReactionCoeff.from_si(inp_units,
                                                                       pipe.bulk_rxn_coeff,
                                                                       self.mass_units,
                                                                       wn.options.bulk_rxn_order)))
            if pipe.wall_rxn_coeff is not None:
                f.write(entry_float.format('WALL',pipe_name,
                                           QualParam.WallReactionCoeff.from_si(inp_units,
                                                                       pipe.wall_rxn_coeff,
                                                                       self.mass_units,
                                                                       wn.options.wall_rxn_order)))
        f.write('\n')

        # Time options
        f.write('[TIMES]\n')
        entry = '{:20s} {:10s}\n'
        time_entry = '{:20s} {:d}:{:d}:{:d}\n'
        hrs, mm, sec = wn._sec_to_string(wn.options.duration)
        f.write(time_entry.format('DURATION', hrs, mm, sec))
        hrs, mm, sec = wn._sec_to_string(wn.options.hydraulic_timestep)
        f.write(time_entry.format('HYDRAULIC TIMESTEP', hrs, mm, sec))
        hrs, mm, sec = wn._sec_to_string(wn.options.pattern_timestep)
        f.write(time_entry.format('PATTERN TIMESTEP', hrs, mm, sec))
        hrs, mm, sec = wn._sec_to_string(wn.options.pattern_start)
        f.write(time_entry.format('PATTERN START', hrs, mm, sec))
        hrs, mm, sec = wn._sec_to_string(wn.options.report_timestep)
        f.write(time_entry.format('REPORT TIMESTEP', hrs, mm, sec))
        hrs, mm, sec = wn._sec_to_string(wn.options.report_start)
        f.write(time_entry.format('REPORT START', hrs, mm, sec))

        hrs, mm, sec = wn._sec_to_string(wn.options.start_clocktime)
        if hrs < 12:
            time_format = ' AM'
        else:
            hrs -= 12
            time_format = ' PM'
        f.write('{:20s} {:d}:{:d}:{:d}{:s}\n'.format('START CLOCKTIME', hrs, mm, sec, time_format))

        hrs, mm, sec = wn._sec_to_string(wn.options.quality_timestep)
        f.write(time_entry.format('QUALITY TIMESTEP', hrs, mm, sec))
        hrs, mm, sec = wn._sec_to_string(wn.options.rule_timestep)
        f.write(time_entry.format('RULE TIMESTEP', hrs, mm, int(sec)))
        f.write(entry.format('STATISTIC', wn.options.statistic))
        f.write('\n')

        # Coordinates
        f.write('[COORDINATES]\n')
        entry = '{:10s} {:<10.2f} {:<10.2f}\n'
        label = '{:10s} {:10s} {:10s}\n'
        f.write(label.format(';Node', 'X-Coord', 'Y-Coord'))
        coord = nx.get_node_attributes(wn._graph, 'pos')
        for key, val in coord.iteritems():
            f.write(entry.format(key, val[0], val[1]))
        f.write('\n')

        unmodified = ['[ENERGY]', '[RULES]', '[DEMANDS]', '[QUALITY]', '[EMITTERS]', '[SOURCES]',
                      '[MIXING]', '[VERTICES]', '[LABELS]', '[BACKDROP]', '[TAGS]']

        for section in unmodified:
            if len(self.sections[section]) > 0:
                logger.debug('Writting data from original epanet file: %s', section)
                f.write('{0}\n'.format(section))
                for lnum, line in self.sections[section]:
                    f.write('{0}\n'.format(line))
                f.write('\n')

        f.write('[END]\n')
        f.close()

    def _sec_to_string(self, sec):
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        return (hours, mm, int(sec))


