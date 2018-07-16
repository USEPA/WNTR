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

logger = logging.getLogger(__name__)


def _nodes_with_leaks(wn):
    """

    Parameters
    ----------
    wn: wntr.network.WaterNetworkModel

    Returns
    -------
    res: list of str

    """
    res = []
    for _n, node in wn.junctions:
        if node.leak_status:
            res.append(_n)
    for _n, node in wn.tanks:
        if node.leak_status:
            res.append(_n)
    return res


def create_hydraulic_model(wn, mode='DD'):
    """
    Parameters
    ----------
    wn: WaterNetworkModel
    mode: str

    Returns
    -------
    m: wntr.aml.Model
    """
    m = aml.Model(model_type='wntr')

    # Global constants
    constants.hazen_williams_constants(m)
    constants.head_pump_constants(m)
    constants.leak_constants(m)
    constants.pdd_constants(m)

    leak_nodes = _nodes_with_leaks(wn)

    param.source_head_param(m, wn)
    param.expected_demand_param(m, wn)
    if mode == 'DD':
        pass
    elif mode == 'PDD':
        param.pmin_param(m, wn)
        param.pnom_param(m, wn)
        param.pdd_poly_coeffs_param(m, wn)
    param.leak_coeff_param(m, wn, index_over=leak_nodes)
    param.leak_area_param(m, wn, index_over=leak_nodes)
    param.leak_poly_coeffs_param(m, wn, index_over=leak_nodes)
    param.elevation_param(m, wn)
    param.hw_resistance_param(m, wn)
    param.minor_loss_param(m, wn)
    param.tcv_resistance_param(m, wn)
    param.status_param(m, wn)
    param.pump_power_param(m, wn)
    param.valve_setting_param(m, wn)

    if mode == 'DD':
        pass
    elif mode == 'PDD':
        var.demand_var(m, wn)
    var.flow_var(m, wn)
    var.head_var(m, wn)
    var.leak_rate_var(m, wn, index_over=leak_nodes)

    if mode == 'DD':
        constraint.mass_balance_constraint(m, wn)
    elif mode == 'PDD':
        constraint.pdd_mass_balance_constraint(m, wn)
        constraint.pdd_constraint(m, wn)
    else:
        raise ValueError('mode not recognized: ' + str(mode))
    constraint.hazen_williams_headloss_constraint(m, wn)
    constraint.head_pump_headloss_constraint(m, wn)
    constraint.power_pump_headloss_constraint(m, wn)
    constraint.prv_headloss_constraint(m, wn)
    constraint.tcv_headloss_constraint(m, wn)
    constraint.fcv_headloss_constraint(m, wn)
    constraint.leak_constraint(m, wn, index_over=leak_nodes)
    return m


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
        
    def reset_isolated_junctions(self):
        self.isolated_junction_names = set()
        self.isolated_link_names = set()

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

    def compute_polynomial_coefficients(self, x1, x2, f1, f2, df1, df2):
        """
        Method to compute the coefficients of a smoothing polynomial.

        Parameters
        ----------
        x1: float
            point on the x-axis at which the smoothing polynomial begins
        x2: float
            point on the x-axis at which the smoothing polynomial ens
        f1: float
            function evaluated at x1
        f2: float
            function evaluated at x2
        df1: float
            derivative evaluated at x1
        df2: float
            derivative evaluated at x2

        Returns
        -------
        A tuple with the smoothing polynomail coefficients starting with the cubic term.
        """
        # A = np.matrix([[x1**3.0, x1**2.0, x1, 1.0],
        #                [x2**3.0, x2**2.0, x2, 1.0],
        #                [3.0*x1**2.0, 2.0*x1, 1.0, 0.0],
        #                [3.0*x2**2.0, 2.0*x2, 1.0, 0.0]])
        # rhs = np.matrix([[f1],
        #                  [f2],
        #                  [df1],
        #                  [df2]])
        # x = np.linalg.solve(A,rhs)
        a = (2*(f1-f2) - (x1-x2)*(df2+df1))/(x2**3-x1**3+3*x1*x2*(x1-x2))
        b = (df1 - df2 + 3*(x2**2-x1**2)*a)/(2*(x1-x2))
        c = df2 - 3*x2**2*a - 2*x2*b
        d = f2 - x2**3*a - x2**2*b - x2*c
        # print 'a: ',a,float(x[0][0])
        # print 'b: ',b,float(x[1][0])
        # print 'c: ',c,float(x[2][0])
        # print 'd: ',d,float(x[3][0])
        # assert (abs(a-float(x[0][0])) <= 1e-2)
        # assert (abs(b-float(x[1][0])) <= 1e-3)
        # assert (abs(c-float(x[2][0])) <= 1e-5)
        # assert (abs(d-float(x[3][0])) <= 1e-6)
        # return (float(x[0][0]), float(x[1][0]), float(x[2][0]), float(x[3][0]))
        return a, b, c, d

    def get_leak_poly_coeffs(self, node, node_id):
        x1 = 0.0
        f1 = 0.0
        df1 = 1.0e-11
        x2 = 1.0e-4
        f2 = node.leak_discharge_coeff*node.leak_area*math.sqrt(2.0*self._g*x2)
        df2 = 0.5*node.leak_discharge_coeff*node.leak_area*math.sqrt(2.0*self._g)*(x2)**(-0.5)
        a,b,c,d = self.compute_polynomial_coefficients(x1,x2,f1,f2,df1,df2)
        self.leak_poly_coeffs[node_id] = (a,b,c,d)

    def get_pdd_poly1_coeffs(self, node, node_id):
        Pmin = self.minimum_pressures[node_id]
        Pnom = self.nominal_pressures[node_id]
        x1 = Pmin
        f1 = 0.0
        x2 = Pmin+self._pdd_smoothing_delta
        f2 = ((x2-Pmin)/(Pnom-Pmin))**0.5
        df1 = self._slope_of_pdd_curve
        df2 = 0.5*((x2-Pmin)/(Pnom-Pmin))**(-0.5)*1.0/(Pnom-Pmin)
        a,b,c,d = self.compute_polynomial_coefficients(x1,x2,f1,f2,df1,df2)
        self.pdd_poly1_coeffs[node_id] = (a,b,c,d)
        self.pdd_poly1_coeffs_a[node_id] = a
        self.pdd_poly1_coeffs_b[node_id] = b
        self.pdd_poly1_coeffs_c[node_id] = c
        self.pdd_poly1_coeffs_d[node_id] = d

    def get_pdd_poly2_coeffs(self, node, node_id):
        Pmin = self.minimum_pressures[node_id]
        Pnom = self.nominal_pressures[node_id]
        x1 = Pnom-self._pdd_smoothing_delta
        f1 = ((x1-Pmin)/(Pnom-Pmin))**0.5
        x2 = Pnom
        f2 = 1.0
        df1 = 0.5*((x1-Pmin)/(Pnom-Pmin))**(-0.5)*1.0/(Pnom-Pmin)
        df2 = self._slope_of_pdd_curve
        a,b,c,d = self.compute_polynomial_coefficients(x1,x2,f1,f2,df1,df2)
        self.pdd_poly2_coeffs[node_id] = (a,b,c,d)
        self.pdd_poly2_coeffs_a[node_id] = a
        self.pdd_poly2_coeffs_b[node_id] = b
        self.pdd_poly2_coeffs_c[node_id] = c
        self.pdd_poly2_coeffs_d[node_id] = d

    def get_pump_poly_coefficients(self, A, B, C):
        q1 = self.pump_q1
        q2 = self.pump_q2
        m = self.pump_m

        f1 = m*q1 + A
        f2 = A - B*q2**C
        df1 = m
        df2 = -B*C*q2**(C-1.0)

        a,b,c,d = self.compute_polynomial_coefficients(q1, q2, f1, f2, df1, df2)

        if a <= 0.0 and b <= 0.0:
            return (a,b,c,d)
        elif a > 0.0 and b > 0.0:
            if df2 < 0.0:
                return (a,b,c,d)
            else:
                warnings.warn('Pump smoothing polynomial is not monotonically decreasing.')
                return (a,b,c,d)
        elif a > 0.0 and b <= 0.0:
            if df2 < 0.0:
                return (a,b,c,d)
            else:
                warnings.warn('Pump smoothing polynomial is not monotonically decreasing.')
                return (a,b,c,d)
        elif a <= 0.0 and b > 0.0:
            if q2 <= -2.0*b/(6.0*a) and df2 < 0.0:
                return (a,b,c,d)
            else:
                warnings.warn('Pump smoothing polynomial is not monotonically decreasing.')
                return (a,b,c,d)
        else:
            warnings.warn('Pump smoothing polynomial is not monotonically decreasing.')
            return (a,b,c,d)

    def get_pump_line_params(self, A, B, C):
        q_bar = (self.pump_m/(-B*C))**(1.0/(C-1.0))
        h_bar = A - B*q_bar**C
        return q_bar, h_bar

    def print_jacobian(self, jacobian):
        #np.set_printoptions(threshold='nan')
        #print jacobian.toarray()

        def construct_string(name, values):
            string = '{0:<10s}'.format(name)
            for i in range(len(values)):
                if type(values[i]) == str:
                    string = string+'{0:<6s}'.format(values[i])
                else:
                    string = string+'{0:<6.2f}'.format(values[i])
            return string

        print(construct_string('variable',[node_name for node_name, node in self._wn.nodes()]+[node_name for node_name, node in self._wn.nodes()]+[link_name for link_name, link in self._wn.links()]+[self._node_id_to_name[node_id] for node_id in self._leak_ids]))
        for node_id in range(self.num_nodes):
            print(construct_string(self._node_id_to_name[node_id], jacobian.getrow(node_id).toarray()[0]))
        for node_id in range(self.num_nodes):
            print(construct_string(self._node_id_to_name[node_id], jacobian.getrow(self.num_nodes+node_id).toarray()[0]))
        for link_id in range(self.num_links):
            print(construct_string(self._link_id_to_name[link_id], jacobian.getrow(2*self.num_nodes+link_id).toarray()[0]))
        for node_id in self._leak_ids:
            print(construct_string(self._node_id_to_name[node_id], jacobian.getrow(2*self.num_nodes+self.num_links+self._leak_ids.index(node_id)).toarray()[0]))

    def print_jacobian_nonzeros(self):
        print('{0:<15s}{1:<15s}{2:<25s}{3:<25s}{4:<15s}'.format('row index','col index','eqnuation','variable','value'))
        for i in range(self.jacobian.shape[0]):
            row_nnz = self.jacobian.indptr[i+1] - self.jacobian.indptr[i]
            for k in range(row_nnz):
                j = self.jacobian.indices[self.jacobian.indptr[i]+k]
                if i < self.num_nodes:
                    equation_type = 'node balance'
                    node_or_link = 'node'
                    node_or_link_name = self._node_id_to_name[i]
                elif i < 2*self.num_nodes:
                    equation_type = 'demand/head'
                    node_or_link = 'node'
                    node_or_link_name = self._node_id_to_name[i - self.num_nodes]
                else:
                    equation_type = 'headloss'
                    node_or_link = 'link'
                    node_or_link_name = self._link_id_to_name[i - 2*self.num_nodes]
                if j < self.num_nodes:
                    wrt = 'head'
                    wrt_name = self._node_id_to_name[j]
                elif j< 2*self.num_nodes:
                    wrt = 'demand'
                    wrt_name = self._node_id_to_name[j - self.num_nodes]
                else:
                    wrt = 'flow'
                    wrt_name = self._link_id_to_name[j - 2*self.num_nodes]
                print('{0:<15d}{1:<15d}{2:<25s}{3:<25s}{4:<15.5e}'.format(i,j,equation_type+node_or_link_name,wrt+wrt_name,self.jacobian[i,j]))

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

    def check_jac_for_zero_rows(self):
        for i in range(self.jacobian.shape[0]):
            all_zero_flag = False
            row_nnz = self.jacobian.indptr[i+1] - self.jacobian.indptr[i]
            if row_nnz <= 0:
                all_zero_flag = True
            non_zero_flag = False
            for k in range(row_nnz):
                j = self.jacobian.indices[self.jacobian.indptr[i]+k]
                if self.jacobian[i,j] != 0:
                    non_zero_flag = True
                else:
                    continue
            if non_zero_flag == False:
                all_zero_flag = True
            if all_zero_flag:
                if i < self.num_nodes:
                    equation_type = 'node balance'
                    node_or_link_name = self._node_id_to_name[i]
                elif i < 2*self.num_nodes:
                    equation_type = 'demand/head equation'
                    node_or_link_name = self._node_id_to_name[i - self.num_nodes]
                else:
                    equation_type = 'headloss'
                    node_or_link_name = self._link_id_to_name[i - 2*self.num_nodes]
                print('jacobian row for ',equation_type,' for ',node_or_link_name,' has all zero entries.')

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
