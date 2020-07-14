from __future__ import print_function
import pandas as pd
import numpy as np
import scipy.sparse as sparse
import math
import warnings
import logging
from wntr.network.model import WaterNetworkModel
from wntr.network.base import NodeType, LinkType, LinkStatus
from wntr.network.elements import Junction, Tank, Reservoir, Pipe, HeadPump, PowerPump, PRValve, PSValve, FCValve, \
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


def update_model_for_controls(m, wn, model_updater, control_manager):
    """

    Parameters
    ----------
    m: wntr.aml.Model
    wn: wntr.network.WaterNetworkModel
    model_updater: wntr.models.utils.ModelUpdater
    control_manager: wntr.network.controls.ControlManager
    """
    for obj, attr in control_manager.get_changes():
        model_updater.update(m, wn, obj, attr)
    # TODO: update model for isolated junctions and links


def update_model_for_isolated_junctions_and_links(m, wn, model_updater, prev_isolated_junctions, prev_isolated_links,
                                                  isolated_junctions, isolated_links):
    """

    Parameters
    ----------
    m: wntr.aml.Model
    wn: wntr.network.WaterNetworkModel
    model_updater: wntr.models.utils.ModelUpdater
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
    wn: wntr.network.WaterNetworkModel
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
    wn: wntr.network.WaterNetworkModel
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
                
        tank.head = tank._prev_head + delta_h
            


def initialize_results_dict(wn):
    """
    Parameters
    ----------
    wn: wntr.network.WaterNetworkModel

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

    return node_res, link_res


def save_results(wn, node_res, link_res):
    """
    Parameters
    ----------
    wn: wntr.network.WaterNetworkModel
    node_res: OrderedDict
    link_res: OrderedDict
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

    for name, link in wn.head_pumps():
        link_res['flowrate'][name].append(link.flow)
        link_res['velocity'][name].append(0)
        link_res['status'][name].append(link.status)

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

    for name, link in wn.valves():
        link_res['flowrate'][name].append(link.flow)
        link_res['velocity'][name].append(abs(link.flow)*4.0 / (math.pi*link.diameter**2))
        link_res['status'][name].append(link.status)


def get_results(wn, results, node_res, link_res):
    """
    Parameters
    ----------
    wn: wntr.network.WaterNetworkModel
    results: wntr.sim.results.SimulationResults
    node_res: OrderedDict
    link_res: OrderedDict
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


def store_results_in_network(wn, m):
    """

    Parameters
    ----------
    wn: wntr.network.WaterNetworkModel
    m: wntr.aml.Model

    """
    mode = wn.options.hydraulic.demand_model
    for name, link in wn.links():
        if link._is_isolated:
            link._flow = 0
        else:
            link._flow = m.flow[name].value

    for name, node in wn.junctions():
        if node._is_isolated:
            node.head = 0
            node.demand = 0
            node.leak_demand = 0
        else:
            node.head = m.head[name].value
            if mode in ['PDD', 'PDA']:
                node.demand = m.demand[name].value
            else:
                node.demand = m.expected_demand[name].value
            if node.leak_status:
                node.leak_demand = m.leak_rate[name].value
            else:
                node.leak_demand = 0

    for name, node in wn.tanks():
        if node.leak_status:
            node.leak_demand = m.leak_rate[name].value
        else:
            node.leak_demand = 0
        node.demand = (sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'INLET')) -
                       sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'OUTLET')) -
                       node.leak_demand)

    for name, node in wn.reservoirs():
        node.head = node.head_timeseries.at(wn.sim_time)
        node.leak_demand = 0
        node.demand = (sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'INLET')) -
                       sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'OUTLET')))
