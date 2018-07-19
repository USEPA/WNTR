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


def create_hydraulic_model(wn, mode='DD'):
    """
    Parameters
    ----------
    wn: WaterNetworkModel
    mode: str

    Returns
    -------
    m: wntr.aml.Model
    update_map: dict
    """
    m = aml.Model(model_type='wntr')
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

    # TODO: all expected_demand params need updated every timestep
    # TODO: all source_head params need updated every timestep
    # TODO: Document that changing a curve with controls does not do anything; you have to change the pump_curve_name attribute on the pump

    return m, model_updater


def initialize_results_dict():
    """

    Returns
    -------
    res: dict
    """
    res = dict()
    res['node_name'] = []
    res['node_type'] = []
    res['node_times'] = []
    res['node_head'] = []
    res['node_demand'] = []
    res['node_pressure'] = []
    res['leak_demand'] = []
    res['link_name'] = []
    res['link_type'] = []
    res['link_times'] = []
    res['link_flowrate'] = []
    res['link_velocity'] = []
    res['link_status'] = []
    return res


def set_network_inputs_by_id():
    # TODO: update model for isolated junctions and links
    # TODO: update tank and reservoir heads
    # TODO: update leak models if leak_status changed
    # TODO: update junction demands
    # TODO: update link status param
    # TODO: update link models if status changes???
    # TODO: update pipe minor loss params
    # TODO: update valve settings, valve minor losses, valve resistance coefficients
    # TODO: update pump speeds
    pass


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


class HydraulicModel(object):
    """
    Hydraulic model class.

    Parameters
    ----------
    wn : WaterNetworkModel object
        Water network model

    mode: string (optional)
        Specifies whether the simulation will be demand-driven (DD) or
        pressure dependent demand (PDD), default = DD
    """

    def save_results(self, x, results):
        head = x[:self.num_nodes]
        demand = x[self.num_nodes:2*self.num_nodes]
        flow = x[2*self.num_nodes:(2*self.num_nodes+self.num_links)]
        leak_demand = x[(2*self.num_nodes+self.num_links):]
        for node_id in self._junction_ids:
            head_n = head[node_id]
            self._sim_results['node_type'].append('Junction')
            self._sim_results['node_head'].append(head_n)
            self._sim_results['node_demand'].append(demand[node_id])
            if node_id in self.isolated_junction_ids:
                self._sim_results['node_pressure'].append(0.0)
            else:
                self._sim_results['node_pressure'].append(head_n - self.node_elevations[node_id])
            if node_id in self._leak_ids:
                leak_idx = self._leak_ids.index(node_id)
                leak_demand_n = leak_demand[leak_idx]
                self._sim_results['leak_demand'].append(leak_demand_n)
            else:
                self._sim_results['leak_demand'].append(0.0)
        for node_id in self._tank_ids:
            head_n = head[node_id]
            demand_n = demand[node_id]
            self._sim_results['node_type'].append('Tank')
            self._sim_results['node_head'].append(head_n)
            self._sim_results['node_demand'].append(demand_n)
            self._sim_results['node_pressure'].append(head_n - self.node_elevations[node_id])
            if node_id in self._leak_ids:
                leak_idx = self._leak_ids.index(node_id)
                leak_demand_n = leak_demand[leak_idx]
                self._sim_results['leak_demand'].append(leak_demand_n)
            else:
                self._sim_results['leak_demand'].append(0.0)
        for node_id in self._reservoir_ids:
            demand_n = demand[node_id]
            self._sim_results['node_type'].append('Reservoir')
            self._sim_results['node_head'].append(head[node_id])
            self._sim_results['node_demand'].append(demand_n)
            self._sim_results['node_pressure'].append(0.0)
            self._sim_results['leak_demand'].append(0.0)

        for link_id in self._pipe_ids:
            self._sim_results['link_type'].append(self.link_types[link_id].name)
            self._sim_results['link_flowrate'].append(flow[link_id])
            self._sim_results['link_velocity'].append(abs(flow[link_id])*4.0/(math.pi*self.pipe_diameters[link_id]**2.0))
            self._sim_results['link_status'].append(self.link_status[link_id])
        for link_id in self._pump_ids:
            self._sim_results['link_type'].append(self.link_types[link_id].name)
            self._sim_results['link_flowrate'].append(flow[link_id])
            self._sim_results['link_velocity'].append(0.0)
            self._sim_results['link_status'].append(self.link_status[link_id])
            if self.max_pump_flows[link_id] is not None:
                if flow[link_id]>self.max_pump_flows[link_id]:
                    link_name = self._link_id_to_name[link_id]
                    link = self._wn.get_link(link_name)
                    start_node_name = link.start_node_name
                    end_node_name = link.end_node_name
                    start_node_id = self._node_name_to_id[start_node_name]
                    end_node_id = self._node_name_to_id[end_node_name]
                    start_head = head[start_node_id]
                    end_head = head[end_node_id]
                    warnings.warn('Pump '+link_name+' has exceeded its maximum flow.')
                    logger.warning('Pump {0} has exceeded its maximum flow. Pump head: {1}; Pump flow: {2}; Max pump flow: {3}'.format(link_name,end_head-start_head, flow[link_id], self.max_pump_flows[link_id]))
        for link_id in self._valve_ids:
            self._sim_results['link_type'].append(self.link_types[link_id].name)
            self._sim_results['link_flowrate'].append(flow[link_id])
            self._sim_results['link_velocity'].append(abs(flow[link_id])*4.0/(math.pi*self.pipe_diameters[link_id]**2.0))
            self._sim_results['link_status'].append(self.link_status[link_id])

    def get_results(self,results):
        ntimes = len(results.time)
        nnodes = self.num_nodes
        nlinks = self.num_links
        tmp_node_names = self._junction_ids+self._tank_ids+self._reservoir_ids
        tmp_link_names = self._pipe_ids+self._pump_ids+self._valve_ids
        node_names = [self._node_id_to_name[i] for i in tmp_node_names]
        link_names = [self._link_id_to_name[i] for i in tmp_link_names]

        node_dictionary = {'demand': self._sim_results['node_demand'],
                           'head': self._sim_results['node_head'],
                           'pressure': self._sim_results['node_pressure'],
                           'leak_demand': self._sim_results['leak_demand']}
                           #'type': self._sim_results['node_type']}
        for key,value in node_dictionary.items():
            node_dictionary[key] = pd.DataFrame(data=np.array(value).reshape((ntimes,nnodes)), index=results.time, columns=node_names)
        results.node = node_dictionary 
        
        link_dictionary = {'flowrate':self._sim_results['link_flowrate'],
                           'velocity':self._sim_results['link_velocity'],
                           #'type':self._sim_results['link_type'],
                           'status':self._sim_results['link_status']}
        for key, value in link_dictionary.items():
            link_dictionary[key] = pd.DataFrame(data=np.array(value).reshape((ntimes, nlinks)), index=results.time, columns=link_names)
        results.link = link_dictionary 
        
    def store_results_in_network(self, x):
        head = x[:self.num_nodes]
        demand = x[self.num_nodes:self.num_nodes*2]
        flow = x[self.num_nodes*2:(2*self.num_nodes+self.num_links)]
        leak_demand = x[(2*self.num_nodes+self.num_links):]
        node_name_to_id = self._node_name_to_id
        link_name_to_id = self._link_name_to_id
        for name, node in self._wn.nodes(Junction):
            node_id = node_name_to_id[name]
            node.head = head[node_id]
            node.demand = demand[node_id]
            if node._leak:
                leak_idx = self._leak_ids.index(node_id)
                node.leak_demand = leak_demand[leak_idx]
            else:
                node.leak_demand = 0.0
        for name, node in self._wn.nodes(Tank):
            node_id = node_name_to_id[name]
            node.head = head[node_id]
            node.demand = demand[node_id]
            if node._leak:
                leak_idx = self._leak_ids.index(node_id)
                node.leak_demand = leak_demand[leak_idx]
            else:
                node.leak_demand = 0.0
        for name, node in self._wn.nodes(Reservoir):
            node_id = node_name_to_id[name]
            node.head = head[node_id]
            node.demand = demand[node_id]
            node.leak_demand = 0.0
        for link_name, link in self._wn.links():
            link_id = link_name_to_id[link_name]
            link._flow = flow[link_id]

    def check_jac(self, x):
        import copy
        approx_jac = np.matrix(np.zeros((self.num_nodes*2+self.num_links+self.num_leaks, self.num_nodes*2+self.num_links+self.num_leaks)))

        step = 0.00001

        resids = self.get_hydraulic_equations(x)

        x1 = copy.copy(x)
        x2 = copy.copy(x)
        print('shape = (',len(x),',',len(x),')')
        for i in range(len(x)):
            print('getting approximate derivative of column ',i)
            x1[i] = x1[i] + step
            x2[i] = x2[i] + 2*step
            resids1 = self.get_hydraulic_equations(x1)
            resids2 = self.get_hydraulic_equations(x2)
            deriv_column = (-3.0*resids+4.0*resids1-resids2)/(2*step)
            approx_jac[:,i] = np.matrix(deriv_column).transpose()
            x1[i] = x1[i] - step
            x2[i] = x2[i] - 2*step

        #import numdifftools as adt
        #adt_jac = adt.Jacobian(self.get_hydraulic_equations)
        #print 'using numdifftools to get jacobian'
        #approx_jac = adt_jac(x)
        #print 'converting approx_jac to csr matrix'
        #approx_jac = sparse.csr_matrix(approx_jac)

        jac = self.jacobian.tocsr()

        print('computing difference between jac and approx_jac')
        difference = approx_jac - jac

        success = True
        for i in range(jac.shape[0]):
            print('comparing values in row ',i,'with non-zeros from self.jacobain')
            row_nnz = jac.indptr[i+1] - jac.indptr[i]
            for k in range(row_nnz):
                j = jac.indices[jac.indptr[i]+k]
                if abs(approx_jac[i,j]-jac[i,j]) > 0.0001:
                    if i < self.num_nodes:
                        equation_type = 'node balance'
                        node_or_link = 'node'
                        node_or_link_name = self._node_id_to_name[i]
                    elif i < 2*self.num_nodes:
                        equation_type = 'demand/head equation'
                        node_or_link = 'node'
                        node_or_link_name = self._node_id_to_name[i - self.num_nodes]
                    elif i < 2*self.num_nodes + self.num_links:
                        equation_type = 'headloss'
                        node_or_link = 'link'
                        node_or_link_name = self._link_id_to_name[i - 2*self.num_nodes]
                        print('flow for link ',node_or_link_name,' = ',x[i])
                    else:
                        equation_type = 'leak demand'
                        node_or_link = 'node'
                        node_or_link_name = self._node_id_to_name[self._leak_ids[i - 2*self.num_nodes - self.num_links]]
                    if j < self.num_nodes:
                        wrt = 'head'
                        wrt_name = self._node_id_to_name[j]
                    elif j< 2*self.num_nodes:
                        wrt = 'demand'
                        wrt_name = self._node_id_to_name[j - self.num_nodes]
                    elif j < 2*self.num_nodes+self.num_links:
                        wrt = 'flow'
                        wrt_name = self._link_id_to_name[j - 2*self.num_nodes]
                    else:
                        wrt = 'leak_demand'
                        wrt_name = self._node_id_to_name[self._leak_ids[j - 2*self.num-nodes - self.num_links]]
                    print('jacobian entry for ',equation_type,' for ',node_or_link,' ',node_or_link_name,' with respect to ',wrt,wrt_name,' is incorrect.')
                    print('error = ',abs(approx_jac[i,j]-jac[i,j]))
                    print('approximation = ',approx_jac[i,j])
                    print('exact = ',jac[i,j])
                    success = False

        #if not success:
            #for node_name, node in self._wn.nodes():
            #    print 'head for node ',node_name,' = ',x[self._node_name_to_id[node_name]]
            #for node_name, node in self._wn.nodes():
            #    print 'demand for node ',node_name,' = ',x[self._node_name_to_id[node_name]+self.num_nodes]
            #for link_name, link in self._wn.links():
            #    print 'flow for link ',link_name,' = ',x[self._link_name_to_id[link_name]+2*self.num_nodes]
            #self.print_jacobian(self.jacobian)
            #self.print_jacobian(approx_jac)
            #self.print_jacobian(difference)

            #raise RuntimeError('Jacobian is not correct!')

    def check_infeasibility(self,x):
        resid = self.get_hydraulic_equations(x)
        for i in range(len(resid)):
            r = abs(resid[i])
            if r > 0.0001:
                if i >= 2*self.num_nodes:
                    print('residual for headloss equation for link ',self._link_id_to_name[i-2*self.num_nodes],' is ',r,'; flow = ',x[i])
                elif i >= self.num_nodes:
                    print('residual for demand/head eqn for node ',self._node_id_to_name[i-self.num_nodes],' is ',r)
                else:
                    print('residual for node balance for node ',self._node_id_to_name[i],' is ',r)
