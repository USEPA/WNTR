"""WNTR Simulator hydraulics model."""

import pandas as pd
import numpy as np
import scipy.sparse as sparse
import math
import warnings
import logging
from wntr.network.model import WaterNetworkModel
from wntr.network.base import NodeType, LinkType, LinkStatus
from wntr.network.elements import Junction, Tank, Reservoir, Pipe, Pump, HeadPump, PowerPump, PRValve, PSValve, FCValve, \
    TCValve, GPValve, PBValve
from collections import OrderedDict
from wntr.utils.ordered_set import OrderedSet
from wntr.sim import aml
from wntr.sim.models import constants, var, param, constraint
from wntr.sim.models.utils import ModelUpdater

logger = logging.getLogger(__name__)


def create_hydraulic_model(wn, HW_approx='default'):
    """
    Parameters
    ----------
    wn: WaterNetworkModel
    mode: str
    HW_approx: str
        Specifies which Hazen-Williams headloss approximation to use. Options are 'default' and 'piecewise'. Please
        see the WNTR documentation on hydraulics for details.

    Returns
    -------
    m: wntr.aml.Model
    model_updater: wntr.models.utils.ModelUpdater
    """
    m = aml.Model()
    model_updater = ModelUpdater()

    # Global constants
    constants.hazen_williams_constants(m)
    constants.head_pump_constants(m)
    constants.leak_constants(m)
    constants.pdd_constants(m)

    param.source_head_param(m, wn)
    param.expected_demand_param(m, wn)
    mode = wn.options.hydraulic.demand_model
    if mode in ['DD', 'DDA']:
        pass
    elif mode in ['PDD', 'PDA']:
        param.pmin_param.build(m, wn, model_updater)
        param.pnom_param.build(m, wn, model_updater)
        param.pdd_poly_coeffs_param.build(m, wn, model_updater)
    param.leak_coeff_param.build(m, wn, model_updater)
    param.leak_area_param.build(m, wn, model_updater)
    param.leak_poly_coeffs_param.build(m, wn, model_updater)
    param.elevation_param.build(m, wn, model_updater)
    if wn.options.hydraulic.headloss == 'C-M':
        raise NotImplementedError('C-M headloss is not currently supported in the WNTRSimulator')
    if wn.options.hydraulic.headloss == 'D-W':
        raise NotImplementedError('D-W headloss is not currently supported in the WNTRSimulator')
    param.hw_resistance_param.build(m, wn, model_updater)
    param.minor_loss_param.build(m, wn, model_updater)
    param.tcv_resistance_param.build(m, wn, model_updater)
    param.pump_power_param.build(m, wn, model_updater)
    param.valve_setting_param.build(m, wn, model_updater)

    if mode in ['DD','DDA']:
        pass
    elif mode in ['PDD','PDA']:
        var.demand_var(m, wn)
    var.flow_var(m, wn)
    var.head_var(m, wn)
    var.leak_rate_var(m, wn)

    if mode in ['DD','DDA']:
        constraint.mass_balance_constraint.build(m, wn, model_updater)
    elif mode in ['PDD','PDA']:
        constraint.pdd_mass_balance_constraint.build(m, wn, model_updater)
        constraint.pdd_constraint.build(m, wn, model_updater)
    else:
        raise ValueError('mode not recognized: ' + str(mode))
    if HW_approx == 'default':
        constraint.approx_hazen_williams_headloss_constraint.build(m, wn, model_updater)
    elif HW_approx == 'piecewise':
        constraint.piecewise_hazen_williams_headloss_constraint.build(m, wn, model_updater)
    else:
        raise ValueError('Unexpected value for HW_approx: ' + str(HW_approx))
    constraint.head_pump_headloss_constraint.build(m, wn, model_updater)
    constraint.power_pump_headloss_constraint.build(m, wn, model_updater)
    constraint.prv_headloss_constraint.build(m, wn, model_updater)
    constraint.psv_headloss_constraint.build(m, wn, model_updater)
    constraint.tcv_headloss_constraint.build(m, wn, model_updater)
    constraint.fcv_headloss_constraint.build(m, wn, model_updater)
    if len(wn.pbv_name_list) > 0:
        raise NotImplementedError('PBV valves are not currently supported in the WNTRSimulator')
    if len(wn.gpv_name_list) > 0:
        raise NotImplementedError('GPV valves are not currently supported in the WNTRSimulator')
    constraint.leak_constraint.build(m, wn, model_updater)

    # TODO: Document that changing a curve with controls does not do anything; you have to change the pump_curve_name attribute on the pump

    return m, model_updater


def update_model_for_controls(m, wn, model_updater, change_tracker):
    """

    Parameters
    ----------
    m: wntr.sim.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    model_updater: wntr.sim.models.utils.ModelUpdater
    change_tracker: wntr.network.controls.ControlChangeTracker
    """
    for obj, attr in change_tracker.get_changes(ref_point='model'):
        model_updater.update(m, wn, obj, attr)
    change_tracker.reset_reference_point(key='model')


def update_model_for_isolated_junctions_and_links(m, wn, model_updater, prev_isolated_junctions, prev_isolated_links,
                                                  isolated_junctions, isolated_links):
    """

    Parameters
    ----------
    m: wntr.sim.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    model_updater: wntr.sim.models.utils.ModelUpdater
    prev_isolated_junctions: set
    prev_isolated_links: set
    isolated_junctions: set
    isolated_links: set
    """
    j1 = prev_isolated_junctions - isolated_junctions
    j2 = isolated_junctions - prev_isolated_junctions
    j = j1.union(j2)
    for _j in j:
        junction = wn.get_node(_j)
        model_updater.update(m, wn, junction, '_is_isolated')

    l1 = prev_isolated_links - isolated_links
    l2 = isolated_links - prev_isolated_links
    l = l1.union(l2)
    for _l in l:
        link = wn.get_link(_l)
        model_updater.update(m, wn, link, '_is_isolated')


def update_network_previous_values(wn):
    """
    Parameters
    ----------
    wn: wntr.network.model.WaterNetworkModel
    """
    wn._prev_sim_time = wn.sim_time
    for link_name, link in wn.valves():
        link._prev_setting = link.setting
    for tank_name, tank in wn.tanks():
        tank._prev_head = tank.head

def update_tank_heads(wn):
    """
    Parameters
    ----------
    wn: wntr.network.model.WaterNetworkModel
    """
    dt = wn.sim_time - wn._prev_sim_time   

    for tank_name, tank in wn.tanks():
        q_net = tank.demand
        dV = q_net * dt
        
        if tank.vol_curve is None:    
            delta_h = 4.0 * dV / (math.pi * tank.diameter ** 2)
        else:
            vcurve = np.array(tank.vol_curve.points)
            level_x = vcurve[:,0]
            volume_y = vcurve[:,1]
            
            # I had to include this because the _prev_head is the reference
            # point needed if the tank.head (and tank.level) have already
            # been updated. This isn't a problem for cases with no volume curve.
            if tank.head == tank._prev_head:
                cur_level = tank.level
            else:
                cur_level = tank._prev_head - (tank.head - tank.level)
                            
            V0 = np.interp(cur_level,level_x,volume_y)
            V1 = V0 + dV
            level_new = np.interp(V1,volume_y,level_x)
            delta_h = level_new - cur_level
                
        tank._head = tank._prev_head + delta_h
            


def initialize_results_dict(wn):
    """
    Parameters
    ----------
    wn: wntr.network.model.WaterNetworkModel

    Returns
    -------
    res: dict
    """
    node_res = OrderedDict()
    link_res = OrderedDict()

    node_res['head'] = OrderedDict((name, list()) for name, obj in wn.nodes())
    node_res['demand'] = OrderedDict((name, list()) for name, obj in wn.nodes())
    node_res['pressure'] = OrderedDict((name, list()) for name, obj in wn.nodes())
    node_res['leak_demand'] = OrderedDict((name, list()) for name, obj in wn.nodes())

    link_res['flowrate'] = OrderedDict((name, list()) for name, obj in wn.links())
    link_res['velocity'] = OrderedDict((name, list()) for name, obj in wn.links())
    link_res['status'] = OrderedDict((name, list()) for name, obj in wn.links())
    link_res['setting'] = OrderedDict((name, list()) for name, obj in wn.links())

    return node_res, link_res


def save_results(wn, node_res, link_res):
    """
    Parameters
    ----------
    wn: wntr.network.model.WaterNetworkModel
    node_res: collections.OrderedDict
    link_res: collections.OrderedDict
    """
    for name, node in wn.junctions():
        node_res['head'][name].append(node.head)
        node_res['demand'][name].append(node.demand)
        if node._is_isolated:
            node_res['pressure'][name].append(0.0)
        else:
            node_res['pressure'][name].append(node.head - node.elevation)
        node_res['leak_demand'][name].append(node.leak_demand)

    for name, node in wn.tanks():
        node_res['head'][name].append(node.head)
        node_res['demand'][name].append(node.demand)
        node_res['pressure'][name].append(node.head - node.elevation)
        node_res['leak_demand'][name].append(node.leak_demand)

    for name, node in wn.reservoirs():
        node_res['head'][name].append(node.head)
        node_res['demand'][name].append(node.demand)
        node_res['pressure'][name].append(0.0)
        node_res['leak_demand'][name].append(0.0)

    for name, link in wn.pipes():
        link_res['flowrate'][name].append(link.flow)
        link_res['velocity'][name].append(abs(link.flow)*4.0 / (math.pi*link.diameter**2))
        link_res['status'][name].append(link.status)
        link_res['setting'][name].append(link.roughness)

    for name, link in wn.head_pumps():
        link_res['flowrate'][name].append(link.flow)
        link_res['velocity'][name].append(0)
        link_res['status'][name].append(link.status)
        link_res['setting'][name].append(1)
        
        A, B, C = link.get_head_curve_coefficients()
        if link.flow > (A/B)**(1.0/C):
            start_node_name = link.start_node_name
            end_node_name = link.end_node_name
            start_node = wn.get_node(start_node_name)
            end_node = wn.get_node(end_node_name)
            start_head = start_node.head
            end_head = end_node.head
            warnings.warn('Pump ' + name + ' has exceeded its maximum flow.')
            logger.warning(
                'Pump {0} has exceeded its maximum flow. Pump head: {1}; Pump flow: {2}; Max pump flow: {3}'.format(
                    name, end_head - start_head, link.flow, (A/B)**(1.0/C)))

    for name, link in wn.power_pumps():
        link_res['flowrate'][name].append(link.flow)
        link_res['velocity'][name].append(0)
        link_res['status'][name].append(link.status)
        link_res['setting'][name].append(1) # power pumps have no speed

    for name, link in wn.valves():
        link_res['flowrate'][name].append(link.flow)
        link_res['velocity'][name].append(abs(link.flow)*4.0 / (math.pi*link.diameter**2))
        link_res['status'][name].append(link.status)
        link_res['setting'][name].append(link.setting)


def get_results(wn, results, node_res, link_res):
    """
    Parameters
    ----------
    wn: wntr.network.model.WaterNetworkModel
    results: wntr.sim.results.SimulationResults
    node_res: collections.OrderedDict
    link_res: collections.OrderedDict
    """
    ntimes = len(results.time)
    nnodes = wn.num_nodes
    nlinks = wn.num_links
    node_names = wn.junction_name_list + wn.tank_name_list + wn.reservoir_name_list
    link_names = wn.pipe_name_list + wn.head_pump_name_list + wn.power_pump_name_list + wn.valve_name_list

    for key, value in node_res.items():
        node_res[key] = pd.DataFrame(data=np.array([node_res[key][name] for name in node_names]).transpose(), index=results.time,
                                     columns=node_names)
    results.node = node_res

    for key, value in link_res.items():
        link_res[key] = pd.DataFrame(data=np.array([link_res[key][name] for name in link_names]).transpose(), index=results.time,
                                            columns=link_names)
    results.link = link_res
    
    # Add headloss to results.link -- removed for now, this is slow
    #headloss = pd.DataFrame(data=None, index=results.time, columns=link_names)
    # for name, link in wn.links():
    #     start_node = link.start_node_name
    #     end_node = link.end_node_name
    #     start_head = results.node['head'].loc[:,start_node]
    #     end_head = results.node['head'].loc[:,end_node]
    #     if isinstance(link, Pipe):
    #         # Unit headloss for pipes
    #         headloss.loc[:,name] = abs(end_head - start_head)/link.length
    #     elif isinstance(link, Pump):
    #         # Negative of head gain for pumps 
    #         head_gain = -(end_head - start_head)
    #         head_gain[head_gain > 0] = 0
    #         headloss.loc[:,name] = head_gain
    #     else:
    #         # Total head loss for valves
    #         headloss.loc[:,name] = (end_head - start_head)
            
    #     # Headloss is 0 if the link is closed
    #     headloss.loc[results.link['status'].loc[:,name] == 0,name] = 0
        
    #results.link['headloss'] = headloss

def store_results_in_network(wn, m):
    """

    Parameters
    ----------
    wn: wntr.network.model.WaterNetworkModel
    m: wntr.sim.aml.aml.Model

    """
    mode = wn.options.hydraulic.demand_model
    for name, link in wn.links():
        if link._is_isolated:
            link._flow = 0
        else:
            link._flow = m.flow[name].value

    for name, link in wn.valves():
        link._setting = m.valve_setting[name].value

    for name, node in wn.junctions():
        if node._is_isolated:
            node._head = 0
            node._demand = 0
            node._pressure = 0
            node._leak_demand = 0
        else:
            node._head = m.head[name].value
            node._pressure = m.head[name].value - node.elevation
            if mode in ['PDD', 'PDA']:
                node._demand = m.demand[name].value
            else:
                node._demand = m.expected_demand[name].value
            if node.leak_status:
                node._leak_demand = m.leak_rate[name].value
            else:
                node._leak_demand = 0

    for name, node in wn.tanks():
        if node.leak_status:
            node._leak_demand = m.leak_rate[name].value
        else:
            node._leak_demand = 0
        node._demand = (sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'INLET')) -
                       sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'OUTLET')) -
                       node._leak_demand)

    for name, node in wn.reservoirs():
        node._head = node.head_timeseries.at(wn.sim_time)
        node._leak_demand = 0
        node._demand = (sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'INLET')) -
                       sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'OUTLET')))
