from wntr.utils import convert
import wntr.network

import warnings
import re
import networkx as nx
import copy
import logging
import numpy as np

logger = logging.getLogger('wntr.network.ParseWaterNetwork')

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
        return int(time_tuple.groups()[0])*60*60 + int(time_tuple.groups()[1])*60 + int(round(float(time_tuple.groups()[2])))
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
        raise RuntimeError('am_pm option not recognized. Options are AM or PM.')

    pattern1 = re.compile(r'^(\d+):(\d+):(\d+)$')
    time_tuple = pattern1.search(s)
    if bool(time_tuple):
        time_sec = int(time_tuple.groups()[0])*60*60 + int(time_tuple.groups()[1])*60 + int(round(float(time_tuple.groups()[2])))
        if not am:
            time_sec += 3600*12
        if s.startswith('12'):
            time_sec -= 3600*12
        return time_sec
    else:
        pattern2 = re.compile(r'^(\d+):(\d+)$')
        time_tuple = pattern2.search(s)
        if bool(time_tuple):
            time_sec = int(time_tuple.groups()[0])*60*60 + int(time_tuple.groups()[1])*60
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


# EPANET unit ids used in unit conversion when reading inp files
epanet_unit_id = {'CFS': 0, 'GPM': 1, 'MGD': 2, 'IMGD': 3, 'AFD': 4,
                  'LPS': 5, 'LPM': 6, 'MLD': 7, 'CMH':  8, 'CMD': 9}


class ParseWaterNetwork(object):
    def __init__(self):
        self._patterns = {}
        self._curves = {}
        self._time_controls = {}
        self._conditional_controls = {}
        self._link_status = {} # Map from link name to the initial status

    def read_inp_file(self, wn, inp_file_name):
        """
        Method to read EPANET INP file and load data into a
        water network object.
        
        Parameters
        ----------
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
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                if current[0].upper() == 'HEADLOSS':
                    if current[1].upper() != 'H-W':
                        logger.warning('WNTR currently only supports the '+current[1]+' headloss formula in the EpanetSimulator.')
                if current[0].upper() == 'QUALITY':
                    if current[1].upper() != 'NONE':
                        logger.warning('WNTR only supports water quality analysis in the EpanetSimulator.')
                if current[0].upper() == 'HYDRAULICS' or current[0].upper() == 'MAP':
                    logger.warning('The '+current[0]+' option in the inp file is currently only supported in the EpanetSimulator.')
                if current[0].upper() == 'DEMAND':
                    if float(current[2]) != 1.0:
                        logger.warning('The '+current[0]+' '+current[1]+' option in the inp file is currently only supported in the EpanetSimulator.')
                if len(current) == 2:
                    if current[0].upper() == 'PATTERN' or current[0].upper() == 'MAP':
                        setattr(wn.options, current[0].lower(), current[1])
                    elif current[0].upper() == 'QUALITY':
                        wn.options.quality_option = current[1].upper()
                    elif current[0].upper() == 'UNBALANCED':
                        wn.options.unbalanced_option = current[1].upper()
                    else:
                        setattr(wn.options, current[0].lower(), float(current[1]) if is_number(current[1]) else current[1].upper())
                if len(current) > 2:
                    if current[0].upper() == 'UNBALANCED':
                        wn.options.unbalanced_option = current[1].upper()
                        wn.options.unbalanced_value = int(current[2])
                    elif current[0].upper() == 'HYDRAULICS':
                        wn.options.hydraulics_option = current[1].upper()
                        wn.options.hydraulics_filename = current[2]
                    elif current[0].upper() == 'QUALITY':
                        wn.options.quality_option = current[1].upper()
                        wn.options.quality_value = current[2]
                    else:
                        setattr(wn.options, current[0].lower()+'_'+current[1].lower(), float(current[2]) if is_number(current[2]) else current[2].upper())

        if type(wn.options.report_timestep)==float or type(wn.options.report_timestep)==int:
            if wn.options.report_timestep<wn.options.hydraulic_timestep:
                raise RuntimeError('wn.options.report_timestep must be greater than or equal to wn.options.hydraulic_timestep.')
            if wn.options.report_timestep%wn.options.hydraulic_timestep != 0:
                raise RuntimeError('wn.options.report_timestep must be a multiple of wn.options.hydraulic_timestep')
        f.close()

        # INP file units to convert from
        inp_units = epanet_unit_id[wn.options.units]

        #
        # Read file again to get reservoirs
        #
        f = file(inp_file_name, 'r')
        reservoirs = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                reservoirs = False

            if '[RESERVOIRS]' in line:
                reservoirs = True
                continue

            if reservoirs:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                if len(current) == 2:
                    wn.add_reservoir(current[0], convert('Hydraulic Head', inp_units, float(current[1])))
                else:
                    logger.warning('Patterns for reservoir heads are currently only supported in the EpanetSimulator.')
                    wn.add_reservoir(current[0], convert('Hydraulic Head', inp_units, float(current[1])), current[2])

        f.close()

        #
        # Read file again to get junctions
        #
        f = file(inp_file_name, 'r')
        junctions = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                junctions = False

            if '[JUNCTIONS]' in line:
                junctions = True
                continue

            if junctions:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                if len(current) == 3:
                    wn.add_junction(current[0], convert('Demand', inp_units, float(current[2])), None, convert('Elevation', inp_units, float(current[1])))
                else:
                    wn.add_junction(current[0], convert('Demand', inp_units, float(current[2])), current[3], convert('Elevation', inp_units, float(current[1])))

        f.close()

        #
        # Read file again to get tanks
        #
        f = file(inp_file_name, 'r')
        tanks = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                tanks = False

            if '[TANKS]' in line:
                tanks = True
                continue

            if tanks:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                if len(current) == 8:  # Volume curve provided
                    if float(current[6]) != 0:
                        logger.warning('Currently, only the EpanetSimulator utilizes minimum volumes for tanks. The other simulators only use the minimum level and only support cylindrical tanks.')
                    logger.warning('Currently, only the EpanetSimulator supports volume curves. The other simulators only support cylindrical tanks.')
                    curve_name = current[7]
                    curve_points = []
                    for point in self._curves[curve_name]:
                        x = convert('Length', inp_units, point[0])
                        y = convert('Volume', inp_units, point[1])
                        curve_points.append((x,y))
                    wn.add_curve(curve_name, 'VOLUME', curve_points)
                    curve = wn.get_curve(curve_name)
                    wn.add_tank(current[0], convert('Elevation', inp_units, float(current[1])),
                                            convert('Length', inp_units, float(current[2])),
                                            convert('Length', inp_units, float(current[3])),
                                            convert('Length', inp_units, float(current[4])),
                                            convert('Tank Diameter', inp_units, float(current[5])),
                                            convert('Volume', inp_units, float(current[6])),
                                            curve)
                elif len(current) == 7:  # No volume curve provided
                    if float(current[6]) != 0:
                        logger.warning('Currently, only the EpanetSimulator utilizes minimum volumes for tanks. The other simulators only use the minimum level and only support sylindrical tanks.')
                    wn.add_tank(current[0], convert('Elevation', inp_units, float(current[1])),
                                            convert('Length', inp_units, float(current[2])),
                                            convert('Length', inp_units, float(current[3])),
                                            convert('Length', inp_units, float(current[4])),
                                            convert('Tank Diameter', inp_units, float(current[5])),
                                            convert('Volume', inp_units, float(current[6])))
                else:
                    raise RuntimeError('Tank entry format not recognized.')

        f.close()

        #
        # Read file again to get pipes
        #
        f = file(inp_file_name, 'r')
        pipes = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                pipes = False

            if '[PIPES]' in line:
                pipes = True
                continue

            if pipes:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                if float(current[6]) != 0:
                    logger.warning('Currently, only the EpanetSimulator supports non-zero minor losses in pipes.')
                if current[7].upper() == 'CV':
                    wn.add_pipe(current[0], 
                                current[1], 
                                current[2], 
                                convert('Length', inp_units, float(current[3])),
                                convert('Pipe Diameter', inp_units, float(current[4])),
                                float(current[5]), 
                                float(current[6]), 
                                'OPEN', 
                                True)
                else:
                    wn.add_pipe(current[0], 
                                current[1], 
                                current[2], 
                                convert('Length', inp_units, float(current[3])),
                                convert('Pipe Diameter', inp_units, float(current[4])),
                                float(current[5]), 
                                float(current[6]), 
                                current[7].upper())

        f.close()

        #
        # Read file again to get valves
        #
        f = file(inp_file_name, 'r')
        valves = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                valves = False

            if '[VALVES]' in line:
                valves = True
                continue

            if valves:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                valve_type = current[4].upper()
                if valve_type != 'PRV':
                    logger.warning("Only PRV valves are currently supported. ")
                    #continue
                if float(current[6]) != 0:
                    logger.warning('Currently, only the EpanetSimulator supports non-zero minor losses in valves.')
                wn.add_valve(current[0], current[1], current[2], convert('Pipe Diameter', inp_units, float(current[3])),
                                                                 current[4].upper(), float(current[6]),
                                                                 convert('Pressure', inp_units, float(current[5].upper())))

        f.close()

        #
        # Read file again to get curves
        #
        f = file(inp_file_name, 'r')
        curves = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                curves = False

            if '[CURVES]' in line:
                curves = True
                continue

            if curves:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                curve_name = current[0]
                if curve_name not in self._curves:
                    self._curves[curve_name] = []
                self._curves[curve_name].append((float(current[1]), float(current[2])))#self._curves[curve_name].append((convert('Flow', inp_units, float(current[1])), convert('Hydraulic Head', inp_units, float(current[2]))))

        f.close()

        #
        # Read file again to get pumps
        #
        f = file(inp_file_name, 'r')
        pumps = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                pumps = False

            if '[PUMPS]' in line:
                pumps = True
                continue

            if pumps:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                # Only add head curves for pumps
                if current[3].upper() == 'SPEED':
                    logger.warning('Speed settings for pumps are currently only supported in the EpanetSimulator.')
                    continue
                elif current[3].upper() == 'PATTERN':
                    logger.warning('Speed patterns for pumps are currently only supported in the EpanetSimulator.')
                    continue
                elif current[3].upper() == 'HEAD':
                    curve_name = current[4]
                    curve_points = []
                    for point in self._curves[curve_name]:
                        x = convert('Flow', inp_units, point[0])
                        y = convert('Hydraulic Head', inp_units, point[1])
                        curve_points.append((x,y))
                    wn.add_curve(curve_name, 'HEAD', curve_points)
                    curve = wn.get_curve(curve_name)
                    wn.add_pump(current[0], current[1], current[2], 'HEAD', curve)
                elif current[3].upper() == 'POWER':
                    wn.add_pump(current[0], current[1], current[2], current[3].upper(),
                                convert('Power', inp_units, float(current[4])))
                else:
                    raise RuntimeError('Pump keyword in inp file not recognized.')

        f.close()

        #
        # Read file again to get patterns
        #
        f = file(inp_file_name, 'r')
        patterns = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                patterns = False

            if '[PATTERNS]' in line:
                patterns = True
                continue

            if patterns:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                pattern_name = current[0]
                if pattern_name not in self._patterns:
                    self._patterns[pattern_name] = []
                    for i in current[1:]:
                        self._patterns[pattern_name].append(float(i))
                else:
                    for i in current[1:]:
                        self._patterns[pattern_name].append(float(i))

        for pattern_name, pattern_list in self._patterns.iteritems():
            wn.add_pattern(pattern_name, pattern_list)

        f.close()

        #
        # Read file again to get times
        #
        f = file(inp_file_name, 'r')
        time_format = ['am', 'AM', 'pm', 'PM']
        times = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                times = False

            if '[TIMES]' in line:
                times = True
                continue

            if times:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                if (current[0].upper() == 'DURATION'):
                    wn.options.duration = str_time_to_sec(current[1])
                elif (current[0].upper() == 'HYDRAULIC'):
                    wn.options.hydraulic_timestep = str_time_to_sec(current[2])
                elif (current[0].upper() == 'QUALITY'):
                    wn.options.quality_timestep = str_time_to_sec(current[2])
                elif (current[1].upper() == 'CLOCKTIME'):
                    [time, time_format] = [current[2], current[3].upper()]
                    wn.options.start_clocktime = clock_time_to_sec(time, time_format)
                elif (current[0].upper() == 'STATISTIC'):
                    wn.options.statistic = current[1].upper()
                else:  # Other time options
                    key_string = current[0] + '_' + current[1]
                    setattr(wn.options, key_string.lower(), str_time_to_sec(current[2]))

        if wn.options.pattern_start != 0.0:
            logger.warning('Currently, only the EpanetSimulator supports a non-zero patern start time.')

        if wn.options.report_start != 0.0:
            logger.warning('Currently, only the EpanetSimulator supports a non-zero report start time.')

        if wn.options.report_timestep != wn.options.hydraulic_timestep:
            logger.warning('Currently, only a the EpanetSimulator supports a report timestep that is not equal to the hydraulic timestep.')
            
        if wn.options.start_clocktime != 0.0:
            logger.warning('Currently, only the EpanetSimulator supports a start clocktime other than 12 am.')
                        
        if wn.options.statistic != 'NONE':
            logger.warning('Currently, only the EpanetSimulator supports the STATISTIC option in the inp file.')

        f.close()

        #
        # Read file again to get controls
        #
        f = file(inp_file_name, 'r')
        controls = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                controls = False

            if '[CONTROLS]' in line:
                controls = True
                continue

            if controls:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                current_copy = current
                current = [i.upper() for i in current]
                current[1] = current_copy[1] # don't capitalize the link name

                # Create the control action object
                link_name = current[1]
                #print (link_name in wn._links.keys())
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
                            logger.warning('Currently, valves of type '+link.valve_type+' are only supported in the EpanetSimulator.')
                            continue
                        else:
                            status = convert('Pressure', inp_units, float(current[2]))
                            action_obj = wntr.network.ControlAction(link, 'setting', status)

                # Create the control object
                if 'TIME' not in current and 'CLOCKTIME' not in current:
                    current[5] = current_copy[5]
                    if 'IF' in current:
                        node_name = current[5]
                        node = wn.get_node(node_name)
                        if current[6]=='ABOVE':
                            oper = np.greater
                        elif current[6]=='BELOW':
                            oper = np.less
                        else:
                            raise RuntimeError("The following control is not recognized: " + line)
                        ### OKAY - we are adding in the elevation. This is A PROBLEM IN THE INP WRITER. Now that we know, we can fix it, but if this changes, it will affect multiple pieces, just an FYI.
                        if isinstance(node, wntr.network.Junction):
                            threshold = convert('Pressure',inp_units,float(current[7]))+node.elevation
                        elif isinstance(node, wntr.network.Tank):
                            threshold = convert('Length',inp_units,float(current[7]))+node.elevation
                        control_obj = wntr.network.ConditionalControl((node,'head'),oper,threshold,action_obj)
                    else:
                        raise RuntimeError("The following control is not recognized: " + line)
                    control_name = ''
                    for i in xrange(len(current)-1):
                        control_name = control_name + current[i]
                    control_name = control_name + str(round(threshold,2))
                else:
                    if len(current) != 6:
                        logger.warning('Using CLOCKTIME in time controls is currently only supported by the EpanetSimulator.')
                    if len(current) == 6: # at time
                        if ':' in current[5]:
                            fire_time = str_time_to_sec(current[5])
                        else:
                            fire_time = int(float(current[5])*3600)
                        control_obj = wntr.network.TimeControl(wn, fire_time, 'SIM_TIME', False, action_obj)
                        control_name = ''
                        for i in xrange(len(current)-1):
                            control_name = control_name + current[i]
                        control_name = control_name + str(fire_time)
                    elif len(current) == 7: # at clocktime
                        fire_time = clock_time_to_sec(current[5], current[6])
                        control_obj = wntr.network.TimeControl(wn, fire_time, 'SHIFTED_TIME', True, action_obj)
                wn.add_control(control_name, control_obj)

        f.close()

        #
        # Read file again to get coordinates
        #
        f = file(inp_file_name, 'r')
        coordinates = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                coordinates = False

            if '[COORDINATES]' in line:
                coordinates = True
                continue

            if coordinates:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                assert(len(current) == 3), "Error reading node coordinates. Check format."
                wn.set_node_coordinates(current[0], (float(current[1]), float(current[2])))

        f.close()

        #
        # Read file again to get status
        #
        f = file(inp_file_name, 'r')
        status = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                status = False

            if '[STATUS]' in line:
                status = True
                continue

            if status:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                assert(len(current) == 2), "Error reading [STATUS] block, Check format."
                link = wn.get_link(current[0])
                if current[1].upper() == 'OPEN' or current[1].upper() == 'CLOSED' or current[1].upper() == 'ACTIVE':
                    new_status = wntr.network.LinkStatus.str_to_status(current[1])
                    link.status = new_status
                    link._base_status = new_status
                else:
                    if isinstance(link, wntr.network.Pump):
                        logger.warning('Currently, pump speed settings are only supported in the EpanetSimulator.')
                        continue
                    elif isinstance(link, wntr.network.Valve):
                        if link.valve_type != 'PRV':
                            logger.warning('Currently, valves of type '+link.valve_type+' are only supported in the EpanetSimulator.')
                            continue
                        else:
                            setting = convert('Pressure', inp_units, float(current[2]))
                            link.setting = setting
                            link._base_setting = setting

        f.close()

        #
        # Read file again to get reactions
        #
        f = file(inp_file_name, 'r')
        reactions = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                reactions = False

            if '[REACTIONS]' in line:
                reactions = True
                continue

            if reactions:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                assert len(current) == 3, 'INP file option in [REACTIONS] block not recognized: '+line
                if current[0].upper() == 'ORDER' and current[1].upper() == 'BULK':
                    wn.options.bulk_rxn_order = float(current[2])
                elif current[0].upper() == 'ORDER' and current[1].upper() == 'WALL':
                    wn.options.wall_rxn_order = float(current[2])
                elif current[0].upper() == 'ORDER' and current[1].upper() == 'TANK':
                    wn.options.tank_rxn_order = float(current[2])
                elif current[0].upper() == 'GLOBAL' and current[1].upper() == 'BULK':
                    wn.options.bulk_rxn_coeff = float(current[2])
                elif current[0].upper() == 'GLOBAL' and current[1].upper() == 'WALL':
                    wn.options.wall_rxn_coeff = float(current[2])
                elif current[0].upper() == 'BULK':
                    pipe = wn.get_link(current[1])
                    pipe.bulk_rxn_coeff = float(current[2])
                elif current[0].upper() == 'WALL':
                    pipe = wn.get_link(current[1])
                    pipe.wall_rxn_coeff = float(current[2])
                elif current[0].upper() == 'TANK':
                    tank = wn.get_node(current[1])
                    tank.bulk_rxn_coeff = float(current[2])
                elif current[0].upper() == 'LIMITING':
                    wn.options.limiting_potential = float(current[2])
                elif current[0].upper() == 'ROUGHNESS':
                    wn.options.roughness_correlation = float(current[2])
                else:
                    raise RuntimeError('Reaction option not recognized')

        f.close()

        #
        # Read file again to get demands
        #
        f = file(inp_file_name, 'r')
        demands = False
        warning_flag = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                demands = False

            if '[DEMANDS]' in line:
                demands = True
                continue

            if demands:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                else:
                    warning_flag = True
        if warning_flag:
            logger.warning('Multiple demands per junction are currently only supported by the EpanetSimulator. Please check the [DEMANDS] section of your inp file.')

        f.close()

        #
        # Read file again to get rules
        #
        f = file(inp_file_name, 'r')
        rules = False
        warning_flag = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                rules = False

            if '[RULES]' in line:
                rules = True
                continue

            if rules:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                else:
                    warning_flag = True
        if warning_flag:
            logger.warning('Rules are currently only supported in the EpanetSimulator.')

        f.close()

        #
        # Read file again to get energy
        #
        f = file(inp_file_name, 'r')
        energy = False
        warning_flag = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                energy = False

            if '[ENERGY]' in line:
                energy = True
                continue

            if energy:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                else:
                    warning_flag = True
        if warning_flag:
            logger.warning('Energy analyses are currently only performed by the EpanetSimulator.')

        f.close()

        #
        # Read file again to get emitters
        #
        f = file(inp_file_name, 'r')
        emitters = False
        warning_flag = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                emitters = False

            if '[EMITTERS]' in line:
                emitters = True
                continue

            if emitters:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                else:
                    warning_flag = True
        if warning_flag:
            logger.warning('Emitters are currently only supported by the EpanetSimulator.')
        f.close()

        #
        # Read file again to get report
        #
        f = file(inp_file_name, 'r')
        report = False
        warning_flag = False
        for line in f:
            if ']' in line:
                # Set all flags to false
                report = False

            if '[REPORT]' in line:
                report = True
                continue

            if report:
                line = line.split(';')[0]
                current = line.split()
                if current == []:
                    continue
                else:
                    warning_flag = True
        if warning_flag:
            logger.warning('Currently, only the EpanetSimulator supports the [REPORT] section of the inp file.')

        f.close()
