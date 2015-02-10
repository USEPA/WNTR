from epanetlib.units import convert 
import warnings

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

# EPANET unit ids used in unit conversion when reading inp files
epanet_unit_id = {'CFS': 0, 'GPM': 1, 'MGD': 2, 'IMGD': 3, 'AFD': 4,
                  'LPS': 5, 'LPM': 6, 'MLD': 7, 'CMH':  8, 'CMD': 9}

class ParseWaterNetwork(object):
    def __init__(self):
        self._patterns = {}
        self._curves = {}

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
                    wn.add_option(current[0].upper(), float(current[1]) if is_number(current[1]) else current[1].upper())
                if len(current) > 2:
                    if (current[0] == 'Unbalanced') or (current[0] == 'UNBALANCED'):
                        wn.add_option('UNBALANCED', current[1] + ' ' + current[2])
                    else:
                        wn.add_option(current[0].upper() + ' ' + current[1].upper(), float(current[2]) if is_number(current[2]) else current[2].upper())
        f.close()

        # Read file again to get all network parameters

        # INP file units to convert from
        inp_units = epanet_unit_id[wn.get_option('UNITS')]

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
                    wn.add_junction(current[0], float(current[2]), None, convert('Elevation', inp_units, float(current[1])))
                else:
                    wn.add_junction(current[0], float(current[2]), current[3], convert('Elevation', inp_units, float(current[1])))
            if pumps:
                current = line.split()
                if (current == []) or (current[0].startswith(';')) or (current[0] == ';ID'):
                    continue
                wn.add_pump(current[0], current[1], current[2], current[3])
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
                    [hr, minutes] = current[1].split(':')
                    wn.add_time_parameter('Duration', (float(hr), float(minutes)))
                elif (current[0] == 'Hydraulic') or (current[0] == 'HYDRAULIC'):
                    [hr, minutes] = current[2].split(':')
                    wn.add_time_parameter('Hydraulic Timestep', (float(hr), float(minutes)))
                elif (current[0] == 'Quality') or (current[0] == 'QUALITY'):
                    [hr, minutes] = current[2].split(':')
                    wn.add_time_parameter('Quality Timestep', (float(hr), float(minutes)))
                elif (current[1] == 'ClockTime') or (current[1] == 'CLOCKTIME'):
                    [time, time_format] = [current[2], current[3]]
                    wn.add_time_parameter('Start ClockTime', (float(time), time_format))
                elif (current[0] == 'Statistic') or (current[0] == 'STATISTIC'):
                    wn.add_time_parameter('Statistic', current[1])
                else:  # Other time options
                    [hr, minutes] = current[2].split(':')
                    key_string = current[0] + ' ' + current[1]
                    wn.add_time_parameter(key_string, (float(hr), float(minutes)))
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

        f.close()

        # TODO Units need to be changed for curves depending on the type of curve

        # Add the curves and patterns to their set
        for curve_name, tupleList in self._curves.iteritems():
            wn.add_curve(curve_name, tupleList)
        for pattern_name, pattern_list in self._patterns.iteritems():
            wn.add_pattern(pattern_name, pattern_list)

