from epanetlib.units import convert
from epanetlib.network.WaterNetworkModel import Pump, Tank

import warnings
import re
import networkx as nx

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def str_time_to_min(s):
    """
    Converts epanet time format to minutes.

    Parameters
    --------
    s : string
        EPANET time string. Options are 'HH:MM:SS', 'HH:MM', 'HH'

    Return
    ------
     Integer value of time in minutes. Seconds are rounded.
    """
    pattern1 = re.compile(r'^(\d+):(\d+):(\d+)$')
    time_tuple = pattern1.search(s)
    if bool(time_tuple):
        return int(time_tuple.groups()[0])*60 + int(time_tuple.groups()[1]) + int(round(float(time_tuple.groups()[2])/60.0))
    else:
        pattern2 = re.compile(r'^(\d+):(\d+)$')
        time_tuple = pattern2.search(s)
        if bool(time_tuple):
            return int(time_tuple.groups()[0])*60 + int(time_tuple.groups()[1])
        else:
            pattern3 = re.compile(r'^(\d+)$')
            time_tuple = pattern3.search(s)
            if bool(time_tuple):
                return int(time_tuple.groups()[0])*60
            else:
                raise RuntimeError("Time format in [CONTROLS] block of "
                                   "INP file not recognized. ")

# EPANET unit ids used in unit conversion when reading inp files
epanet_unit_id = {'CFS': 0, 'GPM': 1, 'MGD': 2, 'IMGD': 3, 'AFD': 4,
                  'LPS': 5, 'LPM': 6, 'MLD': 7, 'CMH':  8, 'CMD': 9}

class ParseWaterNetwork(object):
    def __init__(self):
        self._patterns = {}
        self._curves = {}
        self._time_controls = {}
        self._node_coordinates = {}
        self._curve_map = {}

    def read_inp_file(self, wn, inp_file_name):
        """
        Method to read EPANET INP file and load data into a
        water network object.

        wn : WaterNetwork object
            A water network object
        inp_file_name: string
            Name of the EPANET INP file
        """

        # First read inp file to get options, specifically units

        f = file(inp_file_name, 'r')

        # Set name of water network
        wn.name = inp_file_name

        # Flags indicating the type of network element being read
        options = False

        for line in f:
            if ']' in line:
                # Set flag to false
                options = False

            if '[OPTIONS]' in line:
                options = True
                continue

            if options:
                # all options are stored as string
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                if len(current) == 2:
                    if current[0].upper() == 'PATTERN':
                        wn.add_option('PATTERN', current[1])
                    else:
                        wn.add_option(current[0].upper(), float(current[1]) if is_number(current[1]) else current[1].upper())
                if len(current) > 2:
                    if (current[0] == 'Unbalanced') or (current[0] == 'UNBALANCED'):
                        wn.add_option('UNBALANCED', current[1] + ' ' + current[2])
                    else:
                        wn.add_option(current[0].upper() + ' ' + current[1].upper(), float(current[2]) if is_number(current[2]) else current[2].upper())
        f.close()

        # Read file again to get all network parameters

        # INP file units to convert from
        inp_units = epanet_unit_id[wn.options['UNITS']]

        f = file(inp_file_name, 'r')

        time_format = ['am', 'AM', 'pm', 'PM']

        # Flags indicating the type of network element being read
        pipes = False
        junctions = False
        valves = False
        pumps = False
        tanks = False
        reservoirs = False
        patterns = False
        curves = False
        times = False
        controls = False
        coordinates = False

        for line in f:
            if ']' in line:
                # Set all flags to false
                pipes = False
                junctions = False
                valves = False
                pumps = False
                tanks = False
                reservoirs = False
                patterns = False
                curves = False
                times = False
                controls = False
                coordinates = False

            if '[PIPES]' in line:
                pipes = True
                continue
            elif '[JUNCTIONS]' in line:
                junctions = True
                continue
            elif '[VALVES]' in line:
                valves = True
                continue
            elif '[PUMPS]' in line:
                pumps = True
                continue
            elif '[TANKS]' in line:
                tanks = True
                continue
            elif '[RESERVOIRS]' in line:
                reservoirs = True
                continue
            elif '[PATTERNS]' in line:
                patterns = True
                continue
            elif '[CURVES]' in line:
                curves = True
                continue
            elif '[TIMES]' in line:
                times = True
                continue
            elif '[CONTROLS]' in line:
                controls = True
                continue
            elif '[COORDINATES]' in line:
                coordinates = True
                continue

            if pipes:
                current = line.split()
                if (current == []) or (current[0].startswith(';')) or (current[0] == ';ID'):
                    continue
                wn.add_pipe(current[0], current[1], current[2], convert('Length', inp_units, float(current[3])),
                                                                convert('Pipe Diameter', inp_units, float(current[4])),
                                                                float(current[5]), float(current[6]), current[7].upper())
            if valves:
                current = line.split()
                if (current == []) or (current[0].startswith(';')) or (current[0] == ';ID'):
                    continue
                wn.add_valve(current[0], current[1], current[2], convert('Pipe Diameter', inp_units, float(current[3])),
                                                                 current[4].upper(), float(current[6]), current[5].upper())
            if junctions:
                current = line.split()
                if (current == []) or (current[0].startswith(';')) or (current[0] == ';ID'):
                    continue
                if current[-1] == ';':
                    del current[-1]
                if len(current) == 3:
                    wn.add_junction(current[0], convert('Demand', inp_units, float(current[2])), None, convert('Elevation', inp_units, float(current[1])))
                else:
                    wn.add_junction(current[0], convert('Demand', inp_units, float(current[2])), current[3], convert('Elevation', inp_units, float(current[1])))
            if pumps:
                current = line.split()
                if (current == []) or (current[0].startswith(';')) or (current[0] == ';ID'):
                    continue
                # Only add head curves for pumps
                if current[3].upper() == 'HEAD':
                    wn.add_pump(current[0], current[1], current[2], current[4])
                    self._curve_map[current[4]] = current[0]
                else:
                    warnings.warn("Only HEAD curves are supported for pumps. " + current[3] + " curve is currently not supported. ")
            if reservoirs:
                current = line.split()
                if (current == []) or (current[0].startswith(';')) or (current[0] == ';ID'):
                    continue
                if len(current) == 2:
                    wn.add_reservoir(current[0], convert('Hydraulic Head', inp_units, float(current[1])))
                else:
                    wn.add_reservoir(current[0], convert('Hydraulic Head', inp_units, float(current[1])), current[2])
            if tanks:
                current = line.split()
                if (current == []) or (current[0].startswith(';')) or (current[0] == ';ID'):
                    continue
                if current[-1] == ';':
                    del current[-1]
                if len(current) == 8:  # Volume curve provided
                    wn.add_tank(current[0], convert('Elevation', inp_units, float(current[1])),
                                            convert('Length', inp_units, float(current[2])),
                                            convert('Length', inp_units, float(current[3])),
                                            convert('Length', inp_units, float(current[4])),
                                            convert('Tank Diameter', inp_units, float(current[5])),
                                            convert('Volume', inp_units, float(current[6])),
                                            current[7])
                    self._curve_map[current[7]] = current[0]
                elif len(current) == 7:  # No volume curve provided
                    wn.add_tank(current[0], convert('Elevation', inp_units, float(current[1])),
                                            convert('Length', inp_units, float(current[2])),
                                            convert('Length', inp_units, float(current[3])),
                                            convert('Length', inp_units, float(current[4])),
                                            convert('Tank Diameter', inp_units, float(current[5])),
                                            convert('Volume', inp_units, float(current[6])))
            if times:
                # times options are saved a tuple of floats (hr,min) or (time, 'am/pm')
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                if (current[0] == 'Duration') or (current[0] == 'DURATION'):
                    wn.add_time_parameter('DURATION', str_time_to_min(current[1]))
                elif (current[0] == 'Hydraulic') or (current[0] == 'HYDRAULIC'):
                    wn.add_time_parameter('HYDRAULIC TIMESTEP', str_time_to_min(current[2]))
                elif (current[0] == 'Quality') or (current[0] == 'QUALITY'):
                    wn.add_time_parameter('QUALITY TIMESTEP', str_time_to_min(current[2]))
                elif (current[1] == 'ClockTime') or (current[1] == 'CLOCKTIME'):
                    [time, time_format] = [current[2], current[3].upper()]
                    # convert time in AM or PM into minute of day
                    if '12' in time:
                        time = '0'
                    if time_format == 'AM':
                        time_min = str_time_to_min(time)
                    elif time_format == 'PM':
                        time_min = str_time_to_min(time)
                    else:
                        RuntimeError("Time format in INP file not recognized: " + time_format)
                    wn.add_time_parameter('START CLOCKTIME', time_min)
                elif (current[0] == 'Statistic') or (current[0] == 'STATISTIC'):
                    wn.add_time_parameter('STATISTIC', current[1])
                else:  # Other time options
                    key_string = current[0] + ' ' + current[1]
                    wn.add_time_parameter(key_string.upper(), str_time_to_min(current[2]))
            if patterns:
                # patterns are stored in a pattern dictionary pattern_dict = {'pattern_1': [ 23, 3, 4 ...], ... }
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                pattern_name = current[0]
                if pattern_name not in self._patterns:
                    self._patterns[pattern_name] = []
                    for i in current[1:]:
                        self._patterns[pattern_name].append(float(i))
                else:
                    for i in current[1:]:
                        self._patterns[pattern_name].append(float(i))
            if curves:
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                curve_name = current[0]
                if curve_name not in self._curves:
                    self._curves[curve_name] = []
                    self._curves[curve_name].append((float(current[1]), float(current[2])))
                else:
                    self._curves[curve_name].append((float(current[1]), float(current[2])))
            if controls:
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                current = [i.upper() for i in current]
                if 'TIME' not in current:
                    warnings.warn("Warning: Conditional controls are currently not supported. "
                                  "Only time controls are supported.")
                else:
                    assert(len(current) == 6), "Error reading time controls. Check format."
                    link_name = current[1]
                    if link_name not in self._time_controls:
                        if current[2].upper() == 'OPEN':
                            self._time_controls[link_name] = {'open_times': [str_time_to_min(current[5])], 'closed_times': []}
                        elif current[2].upper() == 'CLOSED':
                            self._time_controls[link_name] = {'open_times': [], 'closed_times': [str_time_to_min(current[5])]}
                        else:
                            raise RuntimeError("Time control format not recognized.")
                    else:
                        if current[2].upper() == 'OPEN':
                            self._time_controls[link_name]['open_times'].append(str_time_to_min(current[5]))
                        elif current[2].upper() == 'CLOSED':
                            self._time_controls[link_name]['closed_times'].append(str_time_to_min(current[5]))
                        else:
                            raise RuntimeError("Time control format not recognized.")
            if coordinates:
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                assert(len(current) == 3), "Error reading node coordinates. Check format."
                self._node_coordinates[current[0]] = (float(current[1]), float(current[2]))

        f.close()


        # Add patterns to their set
        for pattern_name, pattern_list in self._patterns.iteritems():
            wn.add_pattern(pattern_name, pattern_list)
        for control_link, control_dict in self._time_controls.iteritems():
            wn.add_time_control(control_link, control_dict['open_times'], control_dict['closed_times'])

        # Add curves
        for curve_name, tupleList in self._curves.iteritems():
            # Get the network element the curve is related to
            # For now, only pump and tank volume curves are supported
            try:
                curve_element = wn.get_link(self._curve_map[curve_name])
            except AttributeError:
                try:
                    curve_element = wn.get_node(self._curve_map[curve_name])
                except AttributeError:
                    warnings.warn("Could not find node or link connected to curve: " + curve_name)

            if isinstance(curve_element, Pump):
                converted_tuples = []
                for (flow, head) in tupleList:
                    converted_tuples.append((convert('Flow', inp_units, flow), convert('Hydraulic Head', inp_units, head)))
                wn.add_curve(curve_name, 'Pump', converted_tuples)
            elif isinstance(curve_element, Tank):
                converted_tuples = []
                for (volume, height) in tupleList:
                    converted_tuples.append((convert('Volume', inp_units, volume), convert('Hydraulic Head', inp_units, height)))
                wn.add_curve(curve_name, 'Volume', converted_tuples)
            else:
                warnings.warn("The following curve type is currently not supported: " + curve_name)

        ### Load the network connectivity into the NetworkX graph ###

        # Set name
        wn.graph.name = inp_file_name
        # Add nodes along with their coordinates
        for name, node in wn.nodes():
            wn.graph.add_node(name, pos=self._node_coordinates[name])
        # Add links and their connectivity
        for link_name, link in wn.links():
            wn.graph.add_edge(link.start_node(), link.end_node(), key=link_name)

