# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 11:19:42 2016

@author: dbhart
"""

import logging
logger = logging.getLogger(__name__)
import warnings

try: 
    import tables
except e:
    warnings.warn('PyTables is not installed. HDF5 formatting will not work.')
    raise e

from tables import IsDescription, StringCol, Float32Col, Int8Col, Int32Col, \
                   Enum, EnumCol, Filters, Float32Atom
from wntr.network import ConditionalControl, TimeControl
import numpy as np

node_type = Enum([r'Junction',r'Reservoir',r'Tank']) #capitalized to match class names
link_type = Enum(['Pipe','Valve','Pump']) # capitalized to match class names
valve_type = Enum(['PRV','PSV','PBV','FCV','TCV','GPV'])
link_status = Enum(['CLOSED','OPEN','ACTIVE','CV']) #link is open or closed, has a check valve, or uses a numeric setting
source_type = Enum(['CONCEN','MASS','FLOWPACED','SETPOINT'])
curve_type = Enum(['HEAD','EFFICIENCY','VOLUME','HEADLOSS']) #pumps, pumps, tanks, GPVs
mixing_model = Enum(['MIXED','2COMP','FIFO','LIFO'])
control_type = Enum(['TIME','CLOCKTIME','CONDITIONAL'])
above_below = Enum(['ABOVE','BELOW'])
and_or = Enum(['AND','OR'])
reaction_type = Enum(['BULK','WALL','TANK'])
filters = Filters(complevel=9, complib='zlib', fletcher32=True, shuffle=True)


#
#  NETWORK TOPOLOGY TABLES
#

class NodeTable(IsDescription):
    label = StringCol(64)
    node_class = EnumCol(node_type, r'Junction', base='uint8')
    class_index = Int32Col()
    tag = Int8Col()

class JunctionTable(IsDescription):
    label = StringCol(64)
    x_coord = Float32Col()
    y_coord = Float32Col()
    elevation = Float32Col()
    base_demand = Float32Col()
    demand_pattern = StringCol(72)
    demand_categories = Int8Col()
    
class ReservoirTable(IsDescription):
    label = StringCol(64)
    x_coord = Float32Col()
    y_coord = Float32Col()
    total_head = Float32Col()
    head_pattern = StringCol(72)
    
class TankTable(IsDescription):
    label = StringCol(64)
    x_coord = Float32Col()
    y_coord = Float32Col()
    elevation = Float32Col()
    minimum_level = Float32Col()
    maximum_level = Float32Col()
    diameter = Float32Col()
    minimum_volume = Float32Col()
    volume_curve = StringCol(64)
    initial_level = Float32Col()

class EmitterTable(IsDescription):
    junction_label = StringCol(64)
    flow_coefficient = Float32Col()

class LinkTable(IsDescription):
    label = StringCol(64)
    link_class = EnumCol(link_type, 'Pipe', base='uint8')
    class_index = Int32Col()
    tag = Int8Col()

class PipeTable(IsDescription):
    label = StringCol(64)
    start_node = StringCol(64)
    end_node =StringCol(64)
    length = Float32Col()
    diameter = Float32Col()
    roughness = Float32Col()
    loss_coefficient = Float32Col()
    
class PumpTable(IsDescription):
    label = StringCol(64)
    start_node = StringCol(64)
    end_node = StringCol(64)
    power = Float32Col()
    head_curve = StringCol(64)
    speed = Float32Col()
    speed_pattern = StringCol(72)

class ValveTable(IsDescription):
    label = StringCol(64)
    start_node = StringCol(64)
    end_node = StringCol(64)
    diameter = Float32Col()
    valve_type = StringCol(3)
    setting = Float32Col()
    gpv_pattern = StringCol(72)
    loss_coefficient = Float32Col()

class TagTable(IsDescription):
    name = StringCol(16)

#
#   CURVES AND PATTERNS
#


class CurveTable(IsDescription):
    label = StringCol(64)
    curve_type = EnumCol(curve_type, 'HEAD', base='uint8')
    num_points = Int8Col()

class CurvePointsTable(IsDescription):
    label = StringCol(64)
    x = Float32Col()
    y = Float32Col()

class PatternTable(IsDescription):
    label = StringCol(72)
    num_points = Int32Col()

class PatternPointsTable(IsDescription):
    label = StringCol(72)
    mult = Float32Col()

#
#  NETWORK OPERATIONS TABLES
#

class DemandTable(IsDescription):
    junction_label = StringCol(64)
    base_demand = Float32Col()
    demand_pattern = StringCol(72)
    demand_category = StringCol(16)

class ControlTable(IsDescription):
    link_label = StringCol(64)
    control_type = EnumCol(control_type, 'CONDITIONAL', base='uint8')
    status = EnumCol(link_status, 'OPEN', base='uint8')
    new_setting = Float32Col()
    node_check = StringCol(64)
    above_below = EnumCol(above_below, 'ABOVE', base='uint8')
    threshold = Float32Col()
    
class RuleTable(IsDescription):
    rule_id = StringCol(32)
    class conditions(IsDescription):
        and_or = EnumCol(and_or, 'AND', base='uint8')
        clause = StringCol(128)
    class then_actions(IsDescription):
        action = StringCol(128)
    class else_actions(IsDescription):
        action = StringCol(128)
    priority = Int8Col()

class InitialStatusTable(IsDescription):
    link_label = StringCol(64)
    link_status = EnumCol(link_status, 'OPEN', base='uint8')
    link_setting = Float32Col()

#
#      WATER QUALITY CONFIGURATION
#

class ReactionTable(IsDescription):
    net_label = StringCol(64)
    reaction_type = EnumCol(reaction_type, 'BULK', base='uint8')
    value = Float32Col()
    
class SourcesTable(IsDescription):
    node_label = StringCol(64)
    source_type = EnumCol(source_type, 'CONCEN', base='uint8')
    strength = Float32Col()
    source_pattern = StringCol(72)

class MixingTable(IsDescription):
    tank_label = StringCol(64)
    mixing_model = EnumCol(mixing_model, 'MIXED', base='uint8')
    mixing_volume = Float32Col()

class InitialQualityTable(IsDescription):
    node_label = StringCol(64)
    node_quality = Float32Col()



class WNMTablesFile(object):
    
    def __init__(self, filename=None):
        self._filename = filename
        self._network = None
        self.num_links = 0
        self.num_nodes = 0
        self.num_times = 0
        self.times = None
        self.scenarios = []
        
    def write_model(self, network, filename=None):
        """
        Write all the network-topology and options data to the file.
        """
        if filename is not None:
            self._filename = filename
        if self._filename is None:
            raise IOError('No filename supplied in WNMTablesFile.write_model()')
        h5file = tables.open_file(self._filename, mode='w', title='WNTR File')
        model = h5file.create_group(h5file.root,'model',network.name,filters=filters)
        netgrp = h5file.create_group(model,'network','Network Description Model',filters=filters)
        hydgrp = h5file.create_group(model,'hydraulics','Hydraulics Operations Model',filters=filters)
        qualgrp = h5file.create_group(model,'quality','Water Quality Model',filters=filters)
        patgrp = h5file.create_group(model,'patterns','Patterns and Curves',filters=filters)
        netattrs = model._v_attrs
        for k,v in network.options.__dict__.items():
            setattr(netattrs,k,v)
        self.num_links = network.num_links()
        self.num_nodes = network.num_nodes()
        self.times = np.arange(0, network.options.duration+network.options.hydraulic_timestep, network.options.hydraulic_timestep)
        self.num_times = len(self.times)
        netattrs.num_tanks = network.num_tanks()
        netattrs.num_pumps = network.num_pumps()
        netattrs.num_junctions = network.num_junctions()
        netattrs.num_pipes = network.num_pipes()
        netattrs.num_valves = network.num_valves()
        netattrs.num_reservoirs = network.num_reservoirs()
        netattrs.num_links = network.num_links()
        netattrs.num_nodes = network.num_nodes()
        tblNodes = h5file.create_table(netgrp,'nodes',NodeTable,'Node IDs, Classes and Class-Table Indices',filters=filters)
        tblLinks = h5file.create_table(netgrp,'links',LinkTable,'Link IDs, Classes and Class-Table Indices',filters=filters)
        tblJunctions = h5file.create_table(netgrp,'junctions',JunctionTable,'Junction information',filters=filters)
        tblReservoirs = h5file.create_table(netgrp, 'reservoirs', ReservoirTable, 'Reservoir information',filters=filters)
        tblTanks = h5file.create_table(netgrp,'tanks',TankTable,'Tank information',filters=filters)
        #tblEmitters = h5file.create_table(netgrp,'emitters',EmitterTable,'Emitter information',filters=filters)
        tblPipes = h5file.create_table(netgrp,'pipes',PipeTable,'Pipe information',filters=filters)
        tblPumps = h5file.create_table(netgrp,'pumps',PumpTable,'Pump information',filters=filters)
        tblValves = h5file.create_table(netgrp,'valves',ValveTable,'Valve information',filters=filters)
        #tblTags = h5file.create_table(netgrp,'tags',TagTable,'Tags',filters=filters)
        tblPatterns = h5file.create_table(patgrp, 'patterns',PatternTable,'Multiplier patterns',filters=filters)
        tblPatternPoints = h5file.create_table(patgrp, 'pattern_points',PatternPointsTable,'Multiplier values',filters=filters)
        tblCurvePoints = h5file.create_table(patgrp, 'curve_points',CurvePointsTable,'Curve values',filters=filters)
        tblCurves = h5file.create_table(patgrp, 'curves', CurveTable,'Curves',filters=filters)
        #tblDemands = h5file.create_table(hydgrp,'demands',DemandTable,'Other demands',filters=filters)
        tblControls = h5file.create_table(hydgrp,'controls',ControlTable,'Simple controls',filters=filters)
        #tblRules = h5file.create_table(hydgrp,'rules',RuleTable,'Complex rules',filters=filters)
        tblInitStatus = h5file.create_table(hydgrp,'status',InitialStatusTable,'Initial pipe, pump and valve statuses',filters=filters)
        #tblReactions = h5file.create_table(qualgrp,'reactions',ReactionTable,'Reaction definitions for specific pipes and tanks',filters=filters)
        #tblMixing = h5file.create_table(qualgrp,'mixing',MixingTable,'Mixing rules for individual tanks',filters=filters)
        #tblSources = h5file.create_table(qualgrp,'sources',SourcesTable,'Chemical source points',filters=filters)
        tblInitQuality = h5file.create_table(qualgrp,'quality',InitialQualityTable,'Initial water quality',filters=filters)
        
        # Load in the patterns
        pattern = tblPatterns.row
        pat_point = tblPatternPoints.row
        for label, values in network._patterns.items():
            pattern['label'] = label
            pattern['num_points'] = len(values)
            for m in values:
                pat_point['label'] = label
                pat_point['mult'] = m
                pat_point.append()
            pattern.append()
        tblPatternPoints.flush()
        tblPatterns.flush()
        ##
        ## Example to read back out:
        ## points = [ p['mult'] for p in tblPatternPoints if p['label'] == 'PATTERN-0' ]
        
        # Curves should be loaded
        curve = tblCurves.row
        cur_point = tblCurvePoints.row
        for label, obj in network._curves.items():
            curve['label']= label
            #    curve['curve_type'] = curve_type(obj.curve_type)
            for p in obj.points:
                cur_point['label'] = label
                cur_point['x'] = p[0]
                cur_point['y'] = p[1]
                cur_point.append()
            curve.append()
        tblCurvePoints.flush()
        tblCurves.flush()
        
        #
        iStatRow = tblInitStatus.row
        iQualRow = tblInitQuality.row
        
        # Load up the Junctions rows
        nRow = tblNodes.row
        jrow = tblJunctions.row
        jct = 0
        for label, junction in network._junctions.items():
            jrow['label'] = label
            xy = network.get_node_coordinates(label)
            jrow['x_coord'] = xy[0]
            jrow['y_coord'] = xy[1]
            jrow['elevation'] = junction.elevation
            jrow['base_demand'] = junction.base_demand
            jrow['demand_pattern'] = junction.demand_pattern_name
            nRow['label'] = label
            nRow['node_class'] = 0
            nRow['class_index'] = jct
            jct += 1
            jrow.append()
            nRow.append()
        tblNodes.flush()
        tblJunctions.flush()
        
        # Load up the Reservoirs rows
        rRow = tblReservoirs.row
        rct = 0
        for label, reservoir in network._reservoirs.items():
            rRow['label'] = label
            xy = network.get_node_coordinates(label)
            rRow['x_coord'] = xy[0]
            rRow['y_coord'] = xy[1]
            rRow['total_head'] = reservoir.base_head
            if reservoir.head_pattern_name is not None:
                rRow['head_pattern'] = reservoir.head_pattern_name
            nRow['label'] = label
            nRow['node_class'] = 1
            nRow['class_index'] = rct
            rct += 1
            rRow.append()
            nRow.append()
        tblNodes.flush()
        tblReservoirs.flush()
        
        # Load up the Tanks rows
        tRow = tblTanks.row
        tct = 0
        for label, tank in network._tanks.items():
            tRow['label'] = label
            xy = network.get_node_coordinates(label)
            tRow['x_coord'] = xy[0]
            tRow['y_coord'] = xy[1]
            tRow['elevation'] = tank.elevation
            tRow['minimum_level'] = tank.min_level
            tRow['maximum_level'] = tank.max_level
            tRow['diameter'] = tank.diameter
            tRow['minimum_volume'] = tank.min_vol
            if tank.vol_curve is not None:
                tRow['volume_curve'] = tank.vol_curve.name
            tRow['initial_level'] = tank.init_level
            nRow['label'] = label
            nRow['node_class'] = 2
            nRow['class_index'] = tct
            tct += 1
            tRow.append()
            nRow.append()
        tblNodes.flush()
        tblTanks.flush()
        
        # Load up the Pipes rows
        pRow = tblPipes.row
        lRow = tblLinks.row
        pct = 0
        for label, pipe in network._pipes.items():
            pRow['label'] = label
            pRow['start_node'] = pipe.start_node()
            pRow['end_node'] = pipe.end_node()
            pRow['length'] = pipe.length
            pRow['diameter'] = pipe.diameter
            pRow['roughness'] = pipe.roughness
            pRow['loss_coefficient'] = pipe.minor_loss
            lRow['label'] = label
            lRow['link_class'] = 0
            lRow['class_index'] = pct
            iStatRow['link_label'] = label
            iStatRow['link_status'] = pipe._base_status
            pct += 1
            pRow.append()
            lRow.append()
        tblLinks.flush()
        tblPipes.flush()
        
        # Load up the Pumps rows
        pRow = tblPumps.row
        pct = 0
        for label, pump in network._pumps.items():
            pRow['label'] = label
            pRow['start_node'] = pump.start_node()
            pRow['end_node'] = pump.end_node()
            pRow['power'] = pump._base_power
            if pump.curve is not None:
                pRow['head_curve'] = pump.curve.name
            pRow['speed'] = pump.speed
            pRow['speed_pattern'] = ''
            lRow['label'] = label
            lRow['link_class'] = 2
            lRow['class_index'] = pct
            iStatRow['link_label'] = label
            iStatRow['link_status'] = pump._base_status
            iStatRow['link_setting'] = np.nan
            iStatRow.append()
            pct += 1
            pRow.append()
            lRow.append()
        tblLinks.flush()
        tblPumps.flush()
        
        # Load up the Valves rows
        vRow = tblValves.row
        vct = 0
        for label, valve in network._valves.items():
            vRow['label'] = label
            vRow['start_node'] = valve.start_node()
            vRow['end_node'] = valve.end_node()
            vRow['diameter'] = valve.diameter
            vRow['valve_type'] = valve.valve_type
            vRow['setting'] = valve._base_setting
            vRow['gpv_pattern'] = ''
            vRow['loss_coefficient'] = valve.minor_loss
            lRow['label'] = label
            lRow['link_class'] = 1
            lRow['class_index'] = vct
            iStatRow['link_label'] = label
            iStatRow['link_status'] = valve._base_status
            iStatRow['link_setting'] = valve._base_setting
            iStatRow.append()
            vct += 1
            vRow.append()
            lRow.append()
        tblLinks.flush()
        tblValves.flush()
        
        
        cRow = tblControls.row
        for label, control in network._control_dict.items():
            if isinstance(control, ConditionalControl):
                cRow['link_label'] = control._control_action._target_obj_ref.name()
                cRow['status'] = control._control_action._value
                cRow['node_check'] = control._source_obj.name()
                if control._operation == np.less:
                    cRow['above_below'] = 1
                else:
                    cRow['above_below'] = 0
                cRow['threshold'] = control._threshold
                cRow.append()
            elif isinstance(control, TimeControl):
                pass
        tblControls.flush()
        h5file.close()
        
        
    def create_results_tables(self, mode='r+'):
        if self._filename is None:
            raise IOError('No filename supplied in WNMTablesFile.write_model()')
        h5file = tables.open_file(self._filename, mode=mode)
        rgrp = h5file.create_group(h5file.root,'results',"Simulation Results",filters=filters)
        h5file.create_earray(rgrp, 'node_head', Float32Atom(), (0,self.num_nodes,self.num_times),
                             "Junction, tank and res head", filters=filters)
        h5file.create_earray(rgrp, 'node_demand', Float32Atom(), (0,self.num_nodes,self.num_times),
                             "Junction, tank and res demand", filters=filters)
        h5file.create_earray(rgrp, 'node_pressure', Float32Atom(), (0,self.num_nodes,self.num_times),
                             "Junction, tank, and res pressure", filters=filters)
        h5file.create_earray(rgrp, 'node_quality', Float32Atom(), (0,self.num_nodes,self.num_times),
                             "Junction, tank and res. quality", filters=filters)
        h5file.create_earray(rgrp, 'link_flow', Float32Atom(), (0,self.num_links,self.num_times),
                             "Pipe, valve and pump flow", filters=filters)
        h5file.create_earray(rgrp, 'link_velocity', Float32Atom(), (0,self.num_links,self.num_times),
                             "Pipe, valve and pump velocity", filters=filters)
        h5file.close()
        
        
    def write_results(self, results, scenario_id, demand=True, head=True,
                        pressure=True, flow=True, velocity=True, quality=True):
        if self._filename is None:
            raise IOError('No filename supplied in WNMTablesFile.write_model()')
        h5file = tables.open_file(self._filename, mode='r+')
        grp_results = h5file.get_node('/','results')
        self.scenarios.append(scenario_id)
        grp_results._v_attrs['scenarios'] = np.array(self.scenarios)
        tbl_demands = h5file.get_node('/results','node_demand')
        tbl_head = h5file.get_node('/results','node_head')
        tbl_pressure = h5file.get_node('/results','node_pressure')
        tbl_quality =  h5file.get_node('/results','node_quality')
        tbl_flow =  h5file.get_node('/results','link_flow')
        tbl_velocity =  h5file.get_node('/results','link_velocity')
        if demand:
            tbl_demands.append([np.array(results.node['demand'].sort_index(1)).T])
        if head:
            tbl_head.append([np.array(results.node['head'].sort_index(1)).T])
        if pressure:
            tbl_pressure.append([np.array(results.node['pressure'].sort_index(1)).T])
        if flow:
            tbl_flow.append([np.array(results.link['flowrate'].sort_index(1)).T])
        if velocity:
            tbl_velocity.append([np.array(results.link['velocity'].sort_index(1)).T])
        if quality:
            tbl_quality.append([np.array(results.node['quality'].sort_index(1)).T])
        tbl_demands.flush()
        tbl_head.flush()
        tbl_pressure.flush()
        tbl_quality.flush()
        tbl_flow.flush()
        tbl_velocity.flush()
        h5file.close()
        
