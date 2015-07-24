"""
QUESTIONS
"""

"""
TODO 1. Only pump head curves are being assigned to pumps. Other curves are stored but not assigned. Unit conversion in curves.
TODO 2. Test to see if add_junction, add_pipe, etc methods can be called with keys. Change all of them for clarity.
TODO 3. [STATUS] block from Net3.
TODO 4. Pipes that have status CV.
TODO 5. What if '[' or ']' is in comments of inp file?
TODO 6. Add error or something if user tries to specify Hydraulics or Quality in inp file. I don't think the parser will even handle these correctly right now.
TODO 7. What if an inp file is parsed after a water network has been populated? What if an inp file is parsed twice?
TODO 8. Document somehow that [TAGS], [DEMANDS], [RULES], [ENERGY], [EMITTERS], [QUALITY], [SOURCES], [REACTIONS], [MIXING], [REPORT], [VERTICES], [LABELS], [BACKDROP] in an inp file is not used/supported.
TODO 9. Add pump is only used for power pumps?
TODO 10. What if a comment is left at the end of a line that has junction/tank/etc. info?
TODO 11. I think start clocktime is broken
TODO 12. Document Somehow that the only type of curve supported is a head vs. flow curve.
"""

from epanetlib.units import convert
from epanetlib.network.WaterNetworkModel import Pump, Tank, Curve

import warnings
import re
import networkx as nx
import copy

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def str_time_to_sec(s):
    """
    Converts epanet time format to seconds.

    Parameters
    --------
    s : string
        EPANET time string. Options are 'HH:MM:SS', 'HH:MM', 'HH'

    Returns
    -------
     Integer value of time in seconds.
    """
    pattern1 = re.compile(r'^(\d+):(\d+):(\d+)$')
    time_tuple = pattern1.search(s)
    if bool(time_tuple):
        return int(time_tuple.groups()[0])*60*60 + int(time_tuple.groups()[1])*60 + int(round(time_tuple.groups()[2]))
    else:
        pattern2 = re.compile(r'^(\d+):(\d+)$')
        time_tuple = pattern2.search(s)
        if bool(time_tuple):
            return int(time_tuple.groups()[0])*60*60 + int(time_tuple.groups()[1])*60
        else:
            pattern3 = re.compile(r'^(\d+)$')
            time_tuple = pattern3.search(s)
            if bool(time_tuple):
                return int(time_tuple.groups()[0])*60*60
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
        self._pump_info = {} # A dictionary storing pump info
        self._time_controls = {}
        self._conditional_controls = {}
        self._node_coordinates = {}
        self._curve_map = {} # Map from pump name to curve name
        self._link_status = {} # Map from link name to the initial status

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
                    if current[0].upper() == 'UNBALANCED':
                        wn.add_option('UNBALANCED', current[1] + ' ' + current[2])
                    else:
                        wn.add_option(current[0].upper() + ' ' + current[1].upper(), float(current[2]) if is_number(current[2]) else current[2].upper())

        f.close()

        # Read file again to get all network parameters

        # INP file units to convert from
        inp_units = epanet_unit_id[wn.options['UNITS']]

        # Change units in options dictionary
        if 'MINIMUM PRESSURE' in wn.options:
            raise RuntimeError('Specifying nominal and/or minimum pressures in an inp file is not supported') # Updated 5/27/15
            #pressure_value = wn.options['MINIMUM PRESSURE']
            #wn.options['MINIMUM PRESSURE'] = convert('Pressure', inp_units, pressure_value)
        if 'NOMINAL PRESSURE' in wn.options:
            raise RuntimeError('Specifying nominal and/or minimum pressures in an inp file is not supported') # Updated 5/27/15
            #pressure_value = wn.options['NOMINAL PRESSURE']
            #wn.options['NOMINAL PRESSURE'] = convert('Pressure', inp_units, pressure_value)
            #assert wn.options['NOMINAL PRESSURE'] >= wn.options['MINIMUM PRESSURE'], "Nominal pressure must be greater than minimum pressure. "

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
        status = False

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
                status = False

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
            elif '[STATUS]' in line:
                status = True
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
                valve_type = current[4].upper()
                if valve_type != 'PRV':
                    raise warnings.warn("Only PRV valves are currently supported. ")
                wn.add_valve(current[0], current[1], current[2], convert('Pipe Diameter', inp_units, float(current[3])),
                                                                 current[4].upper(), float(current[6]),
                                                                 convert('Pressure', inp_units, float(current[5].upper())))
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
                if current[3].upper() == 'SPEED':
                    raise RuntimeError('Speed settings for pumps are not currently supported')
                elif current[3].upper() == 'PATTERN':
                    raise RuntimeError('Speed patterns for pumps are not currently supported')
                elif current[3].upper() == 'HEAD':
                    self._pump_info[current[0]] = (current[1], current[2], current[4])
                    self._curve_map[current[0]] = current[4]
                elif current[3].upper() == 'POWER':
                    wn.add_pump(current[0], current[1], current[2], current[3].upper(),
                                convert('Power', inp_units, float(current[4])))
                else:
                    raise RuntimeError('Pump keyword in inp file not recognized.')

            if reservoirs:
                current = line.split()
                if (current == []) or (current[0].startswith(';')) or (current[0] == ';ID'):
                    continue
                if (len(current) == 2 or current[2].startswith(';')):
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
                    self._curve_map[current[7]] = current[0] # Is this backwards?
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
                if (current[0].upper() == 'DURATION'):
                    wn.add_time_parameter('DURATION', str_time_to_sec(current[1]))
                elif (current[0].upper() == 'HYDRAULIC'):
                    wn.add_time_parameter('HYDRAULIC TIMESTEP', str_time_to_sec(current[2]))
                elif (current[0].upper() == 'QUALITY'):
                    wn.add_time_parameter('QUALITY TIMESTEP', str_time_to_sec(current[2]))
                elif (current[1].upper() == 'CLOCKTIME'):
                    [time, time_format] = [current[2], current[3].upper()]
                    # convert time in AM or PM into minute of day
                    if '12' in time and time_format == 'AM':
                        time = '0'
                    if time_format == 'AM':
                        time_min = str_time_to_sec(time)
                    elif time_format == 'PM':
                        time_min = str_time_to_sec(time)
                    else:
                        RuntimeError("Time format in INP file not recognized: " + time_format)
                    wn.add_time_parameter('START CLOCKTIME', time_min)
                elif (current[0].upper() == 'STATISTIC'):
                    wn.add_time_parameter('STATISTIC', current[1])
                else:  # Other time options
                    key_string = current[0] + ' ' + current[1]
                    wn.add_time_parameter(key_string.upper(), str_time_to_sec(current[2]))

                if 'PATTERN START' in wn.time_options.keys():
                    if wn.time_options['PATTERN START'] != 0.0:
                        raise ValueError('Currently, only a patern start time of 0.0 is supported')

                if 'REPORT START' in wn.time_options.keys():
                    if wn.time_options['REPORT START'] != 0.0:
                        raise ValueError('Currently, only a report start time of 0.0 is supported')

                if 'REPORT TIMESTEP' in wn.time_options.keys():
                    if wn.time_options['REPORT TIMESTEP'] != wn.time_options['HYDRAULIC TIMESTEP']:
                        raise ValueError('Currently, only a report timestep equal to the hydraulic timestep is supported')

                if 'START CLOCKTIME' in wn.time_options.keys():
                    if wn.time_options['START CLOCKTIME'] != 0.0:
                        raise ValueError('Currently, only a start clocktime of 12 am is supported')

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
                self._curves[curve_name].append((convert('Flow', inp_units, float(current[1])), convert('Hydraulic Head', inp_units, float(current[2]))))
            if controls:
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                current_copy = copy.deepcopy(current)
                current = [i.upper() for i in current]
                current[1] = current_copy[1] # don't capitalize the link name
                if 'TIME' not in current:
                    #warnings.warn("Warning: Conditional controls are currently not supported by the PYOMO simulator. "
                    #              "Only time controls are supported.")
                    if 'IF' in current:
                        link_name = current[1]
                        if link_name not in self._conditional_controls:
                            self._conditional_controls[link_name] = {}
                        node_index = current.index('NODE') + 1
                        node_name = current_copy[node_index]
                        node = wn.get_node(node_name)
                        #if not isinstance(node, Tank):
                        #    raise RuntimeError("Conditional controls are only supported for Tank levels."
                        #                       + node_name + " is not a tank.")
                        if 'OPEN' in current and 'BELOW' in current:
                            value_index = current.index('BELOW') + 1
                            value = convert("Hydraulic Head", inp_units, float(current[value_index]))
                            wn.add_conditional_controls(link_name, node_name, value, 'OPEN', 'BELOW')
                        elif 'OPEN' in current and 'ABOVE' in current:
                            value_index = current.index('ABOVE') + 1
                            value = convert("Hydraulic Head", inp_units, float(current[value_index]))
                            wn.add_conditional_controls(link_name, node_name, value, 'OPEN', 'ABOVE')
                        elif 'CLOSED' in current and 'ABOVE' in current:
                            value_index = current.index('ABOVE') + 1
                            value = convert("Hydraulic Head", inp_units, float(current[value_index]))
                            wn.add_conditional_controls(link_name, node_name, value, 'CLOSED', 'ABOVE')
                        elif 'CLOSED' in current and 'BELOW' in current:
                            value_index = current.index('BELOW') + 1
                            value = convert("Hydraulic Head", inp_units, float(current[value_index]))
                            wn.add_conditional_controls(link_name, node_name, value, 'CLOSED', 'BELOW')
                        else:
                            raise RuntimeError("Conditional control not recognized: " + line)
                    else:
                        raise RuntimeError("The following control is not recognized: " + line)
                else:
                    assert(len(current) == 6), "Error reading time controls. Check format." # This means ClockTime format is not supported?
                    link_name = current[1]
                    if link_name not in self._time_controls:
                        if current[2].upper() == 'OPEN':
                            self._time_controls[link_name] = {'open_times': [str_time_to_sec(current[5])], 'closed_times': []}
                        elif current[2].upper() == 'CLOSED':
                            self._time_controls[link_name] = {'open_times': [], 'closed_times': [str_time_to_sec(current[5])]}
                        else:
                            raise RuntimeError("Time control format not recognized.")
                    else:
                        if current[2].upper() == 'OPEN':
                            self._time_controls[link_name]['open_times'].append(str_time_to_sec(current[5]))
                        elif current[2].upper() == 'CLOSED':
                            self._time_controls[link_name]['closed_times'].append(str_time_to_sec(current[5]))
                        else:
                            raise RuntimeError("Time control format not recognized.")
            if coordinates:
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                assert(len(current) == 3), "Error reading node coordinates. Check format."
                self._node_coordinates[current[0]] = (float(current[1]), float(current[2]))
            if status:
                current = line.split()
                if (current == []) or (current[0].startswith(';')):
                    continue
                assert(len(current) == 2), "Error reading [STATUS] block, Check format."
                self._link_status[current[0]] = current[1].upper()

        f.close()

        # Add patterns to their set
        for pattern_name, pattern_list in self._patterns.iteritems():
            wn.add_pattern(pattern_name, pattern_list)
        # Add initial status to link
        for link_name, status in self._link_status.iteritems():
            if link_name not in self._time_controls:
                if status == 'OPEN':
                    self._time_controls[link_name] = {'open_times': [wn.time_options['START CLOCKTIME']], 'closed_times': []}
                elif status == 'CLOSED':
                    self._time_controls[link_name] = {'open_times': [], 'closed_times': [wn.time_options['START CLOCKTIME']]}
                else:
                    raise RuntimeError("Link status format not recognized.")
            else:
                if status == 'OPEN':
                    self._time_controls[link_name]['open_times'].append(wn.time_options['START CLOCKTIME'])
                elif status == 'CLOSED':
                    self._time_controls[link_name]['closed_times'].append(wn.time_options['START CLOCKTIME'])
                else:
                    raise RuntimeError("Link status format not recognized.")
        # Add time control
        for control_link, control_dict in self._time_controls.iteritems():
            wn.add_time_control(control_link, control_dict['open_times'], control_dict['closed_times'])

        # Add pumps with curve info
        for pump_name, pump_info_tuple in self._pump_info.iteritems():
            # Get curve information
            curve_name = self._curve_map[pump_name]
            curve_points = self._curves[curve_name]
            curve = Curve(curve_name, 'HEAD', curve_points)
            # Get Pump information
            start_node = pump_info_tuple[0]
            end_node = pump_info_tuple[1]
            # Add pump
            wn.add_pump(pump_name, start_node, end_node, 'HEAD', curve)

        # Set node coordinates
        for name, node in wn.nodes():
            wn.set_node_coordinates(name, self._node_coordinates[name])

        """
        # Add curve to network class
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
        """



