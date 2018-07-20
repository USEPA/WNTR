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
from wntr import aml
from wntr.models import constants, var, param, constraint
from wntr.models.utils import ModelUpdater

logger = logging.getLogger(__name__)


def create_hydraulic_model(wn, mode='DD', model_type='wntr'):
    """
    Parameters
    ----------
    wn: WaterNetworkModel
    mode: str
    model_type: str
        'wntr' or 'ipopt'

    Returns
    -------
    m: wntr.aml.Model
    model_updater: wntr.models.utils.ModelUpdater
    """
    m = aml.Model(model_type=model_type)
    if model_type == 'ipopt':
        m.const_obj = aml.create_objective(aml.create_param(value=1.0))
    model_updater = ModelUpdater()

    # Global constants
    constants.hazen_williams_constants(m)
    constants.head_pump_constants(m)
    constants.leak_constants(m)
    constants.pdd_constants(m)

    param.source_head_param(m, wn)
    param.expected_demand_param(m, wn)
    if mode == 'DD':
        pass
    elif mode == 'PDD':
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

    if mode == 'DD':
        pass
    elif mode == 'PDD':
        var.demand_var(m, wn)
    var.flow_var(m, wn)
    var.head_var(m, wn)
    var.leak_rate_var(m, wn)

    if mode == 'DD':
        constraint.mass_balance_constraint.build(m, wn, model_updater)
    elif mode == 'PDD':
        constraint.pdd_mass_balance_constraint.build(m, wn, model_updater)
        constraint.pdd_constraint.build(m, wn, model_updater)
    else:
        raise ValueError('mode not recognized: ' + str(mode))
    constraint.hazen_williams_headloss_constraint.build(m, wn, model_updater)
    constraint.head_pump_headloss_constraint.build(m, wn, model_updater)
    constraint.power_pump_headloss_constraint.build(m, wn, model_updater)
    constraint.prv_headloss_constraint.build(m, wn, model_updater)
    constraint.tcv_headloss_constraint.build(m, wn, model_updater)
    constraint.fcv_headloss_constraint.build(m, wn, model_updater)
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
    for tank_name, tank in wn.tanks():
        q_net = tank.demand
        delta_h = 4.0 * q_net * (wn.sim_time - wn._prev_sim_time) / (math.pi * tank.diameter ** 2)
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


def store_results_in_network(wn, m, mode='DD'):
    """

    Parameters
    ----------
    wn: wntr.network.WaterNetworkModel
    m: wntr.aml.Model
    mode: str
    """
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
            if mode == 'PDD':
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
        node.head = node.head_timeseries(wn.sim_time)
        node.leak_demand = 0
        node.demand = (sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'INLET')) -
                       sum(wn.get_link(link_name).flow for link_name in wn.get_links_for_node(name, 'OUTLET')))


# def check_jac(self, x):
#     import copy
#     approx_jac = np.matrix(np.zeros((self.num_nodes*2+self.num_links+self.num_leaks, self.num_nodes*2+self.num_links+self.num_leaks)))
#
#     step = 0.00001
#
#     resids = self.get_hydraulic_equations(x)
#
#     x1 = copy.copy(x)
#     x2 = copy.copy(x)
#     print('shape = (',len(x),',',len(x),')')
#     for i in range(len(x)):
#         print('getting approximate derivative of column ',i)
#         x1[i] = x1[i] + step
#         x2[i] = x2[i] + 2*step
#         resids1 = self.get_hydraulic_equations(x1)
#         resids2 = self.get_hydraulic_equations(x2)
#         deriv_column = (-3.0*resids+4.0*resids1-resids2)/(2*step)
#         approx_jac[:,i] = np.matrix(deriv_column).transpose()
#         x1[i] = x1[i] - step
#         x2[i] = x2[i] - 2*step
#
#     #import numdifftools as adt
#     #adt_jac = adt.Jacobian(self.get_hydraulic_equations)
#     #print 'using numdifftools to get jacobian'
#     #approx_jac = adt_jac(x)
#     #print 'converting approx_jac to csr matrix'
#     #approx_jac = sparse.csr_matrix(approx_jac)
#
#     jac = self.jacobian.tocsr()
#
#     print('computing difference between jac and approx_jac')
#     difference = approx_jac - jac
#
#     success = True
#     for i in range(jac.shape[0]):
#         print('comparing values in row ',i,'with non-zeros from self.jacobain')
#         row_nnz = jac.indptr[i+1] - jac.indptr[i]
#         for k in range(row_nnz):
#             j = jac.indices[jac.indptr[i]+k]
#             if abs(approx_jac[i,j]-jac[i,j]) > 0.0001:
#                 if i < self.num_nodes:
#                     equation_type = 'node balance'
#                     node_or_link = 'node'
#                     node_or_link_name = self._node_id_to_name[i]
#                 elif i < 2*self.num_nodes:
#                     equation_type = 'demand/head equation'
#                     node_or_link = 'node'
#                     node_or_link_name = self._node_id_to_name[i - self.num_nodes]
#                 elif i < 2*self.num_nodes + self.num_links:
#                     equation_type = 'headloss'
#                     node_or_link = 'link'
#                     node_or_link_name = self._link_id_to_name[i - 2*self.num_nodes]
#                     print('flow for link ',node_or_link_name,' = ',x[i])
#                 else:
#                     equation_type = 'leak demand'
#                     node_or_link = 'node'
#                     node_or_link_name = self._node_id_to_name[self._leak_ids[i - 2*self.num_nodes - self.num_links]]
#                 if j < self.num_nodes:
#                     wrt = 'head'
#                     wrt_name = self._node_id_to_name[j]
#                 elif j< 2*self.num_nodes:
#                     wrt = 'demand'
#                     wrt_name = self._node_id_to_name[j - self.num_nodes]
#                 elif j < 2*self.num_nodes+self.num_links:
#                     wrt = 'flow'
#                     wrt_name = self._link_id_to_name[j - 2*self.num_nodes]
#                 else:
#                     wrt = 'leak_demand'
#                     wrt_name = self._node_id_to_name[self._leak_ids[j - 2*self.num-nodes - self.num_links]]
#                 print('jacobian entry for ',equation_type,' for ',node_or_link,' ',node_or_link_name,' with respect to ',wrt,wrt_name,' is incorrect.')
#                 print('error = ',abs(approx_jac[i,j]-jac[i,j]))
#                 print('approximation = ',approx_jac[i,j])
#                 print('exact = ',jac[i,j])
#                 success = False
#
#     #if not success:
#         #for node_name, node in self._wn.nodes():
#         #    print 'head for node ',node_name,' = ',x[self._node_name_to_id[node_name]]
#         #for node_name, node in self._wn.nodes():
#         #    print 'demand for node ',node_name,' = ',x[self._node_name_to_id[node_name]+self.num_nodes]
#         #for link_name, link in self._wn.links():
#         #    print 'flow for link ',link_name,' = ',x[self._link_name_to_id[link_name]+2*self.num_nodes]
#         #self.print_jacobian(self.jacobian)
#         #self.print_jacobian(approx_jac)
#         #self.print_jacobian(difference)
#
#         #raise RuntimeError('Jacobian is not correct!')
#
# def check_infeasibility(self,x):
#     resid = self.get_hydraulic_equations(x)
#     for i in range(len(resid)):
#         r = abs(resid[i])
#         if r > 0.0001:
#             if i >= 2*self.num_nodes:
#                 print('residual for headloss equation for link ',self._link_id_to_name[i-2*self.num_nodes],' is ',r,'; flow = ',x[i])
#             elif i >= self.num_nodes:
#                 print('residual for demand/head eqn for node ',self._node_id_to_name[i-self.num_nodes],' is ',r)
#             else:
#                 print('residual for node balance for node ',self._node_id_to_name[i],' is ',r)
