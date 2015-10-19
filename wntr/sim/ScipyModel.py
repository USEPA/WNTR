from wntr import *
import pandas as pd
import numpy as np
import scipy.sparse as sparse
import math
from wntr.network.WaterNetworkModel import *
import copy
import warnings

class ScipyModel(object):
    def __init__(self, wn):

        self._wn = wn

        # Global constants
        self._initialize_global_constants()

        # Initialize dictionaries to map between node/link names and ids
        self._initialize_name_id_maps()

        # Number of nodes and links
        self.num_nodes = self._wn.num_nodes()
        self.num_links = self._wn.num_links()

        # Initialize residuals
        # Equations will be ordered:
        #    1.) Node mass balance residuals
        #    2.) Demand/head residuals
        #    3.) Headloss residuals
        self.node_balance_residual = np.ones(self.num_nodes)
        self.demand_or_head_residual = np.ones(self.num_nodes)
        self.headloss_residual = np.ones(self.num_links)

        # Set miscelaneous link and node attributes
        self._set_node_attributes()
        self._set_link_attributes()

        # network input objects
        # these objects use node/link ids rather than names
        self.prev_tank_head = {}
        self.tank_head = {}
        self.prev_reservoir_head = {}
        self.reservoir_head = {}
        self.prev_junction_demand = {}
        self.junction_demand = {}
        self.prev_link_status = {}
        self.link_status = {}
        self.prev_valve_settings = {}
        self.valve_settings = {}
        self.prev_pump_speeds = {}
        self.pump_speeds = {}

        # Initialize Jacobian
        self._set_jacobian_structure()

    def _initialize_global_constants(self):
        self._Hw_k = 10.666829500036352 # Hazen-Williams resistance coefficient in SI units (it equals 4.727 in EPANET GPM units). See Table 3.1 in EPANET 2 User manual.
        self._Dw_k = 0.0826 # Darcy-Weisbach constant in SI units (it equals 0.0252 in EPANET GPM units). See Table 3.1 in EPANET 2 User manual.
        self._g = 9.81 # Acceleration due to gravity

        # Constants for the modified hazen-williams formula
        # The names match the names used in the simulation white paper
        self.hw_q1 = 0.00349347323944
        self.hw_q2 = 0.00549347323944
        self.hw_a = 430.125623753
        self.hw_b = -2.80374270811
        self.hw_c = 0.0138413824671
        self.hw_d = 2.45944613543e-6
        self.hw_m = 0.01
        self.pump_m = -0.00000000001
        self.pump_q1 = 0.0
        self.pump_q2 = 1.0e-8

    def _initialize_name_id_maps(self):
        # ids are intergers
        self._node_id_to_name = {} # {id1: name1, id2: name2, etc.}
        self._node_name_to_id = {} # {name1: id1, name2: id2, etc.}
        self._link_id_to_name = {} # {id1: name1, id2: name2, etc.}
        self._link_name_to_id = {} # {name1: id1, name2: id2, etc.}

        # Lists of types of nodes
        # self._node_ids is ordered by increasing id. In fact, the index equals the id.
        # The ordering of the other lists is not significant.
        # Each node has only one id. For example, if 'Tank-5' has id 8, then 8 will be used
        # for 'Tank-5' in self._node_ids and self._tank_ids.
        self._node_ids = [] 
        self._junction_ids = [] 
        self._tank_ids = [] 
        self._reservoir_ids = [] 

        # Lists of types of links
        # self._link_ids is ordered by increasing id. In fact, the index equals the id.
        # The ordering of the other lists is not significant.
        # Each link has only one id. For example, if 'Pump-5' has id 8, then 8 will be used
        # for 'Pump-5' in self._link_ids and self._pump_ids.
        self._link_ids = [] 
        self._pipe_ids = []
        self._pump_ids = []
        self._valve_ids = []
        self._prv_ids = []
        self._psv_ids = []
        self._pbv_ids = []
        self._fcv_ids = []
        self._tcv_ids = []

        # Lists of types of nodes and links.
        # The values in the lists are attributes of the classes NodeTypes and LinkTypes
        # found in WaterNetworkModel.py. The index is the node/link id.
        self.node_types = []
        self.link_types = []

        n = 0
        for node_name, node in self._wn.nodes():
            self._node_id_to_name[n] = node_name
            self._node_name_to_id[node_name] = n
            self._node_ids.append(n)
            if isinstance(node, Tank):
                self._tank_ids.append(n)
                self.node_types.append(NodeTypes.tank)
            elif isinstance(node, Reservoir):
                self._reservoir_ids.append(n)
                self.node_types.append(NodeTypes.reservoir)
            elif isinstance(node, Junction):
                self._junction_ids.append(n)
                self.node_types.append(NodeTypes.junction)
            else:
                raise RuntimeError('Node is not a junction, tank, or reservoir.')
            n += 1

        l = 0
        for link_name, link in self._wn.links():
            self._link_id_to_name[l] = link_name
            self._link_name_to_id[link_name] = l
            self._link_ids.append(l)
            if isinstance(link, Pipe):
                self._pipe_ids.append(l)
                self.link_types.append(LinkTypes.pipe)
            elif isinstance(link, Pump):
                self._pump_ids.append(l)
                self.link_types.append(LinkTypes.pump)
            elif isinstance(link, Valve):
                self._valve_ids.append(l)
                self.link_types.append(LinkTypes.valve)
                if link.valve_type == 'PRV':
                    self._prv_ids.append(l)
                elif link.valve_type == 'PSV':
                    self._psv_ids.append(l)
                elif link.valve_type == 'PBV':
                    self._pbv_ids.append(l)
                elif link.valve_type == 'FCV':
                    self._fcv_ids.append(l)
                elif link.valve_type == 'TCV':
                    self._tcv_ids.append(l)
                else:
                    raise RuntimeError('Valve type not recognized: '+link.valve_type)
            else:
                raise RuntimeError('Link is not a pipe, pump, or valve.')
            l += 1


    def _set_node_attributes(self):
        self.out_link_ids_for_nodes = [[] for i in xrange(self.num_nodes)]
        self.in_link_ids_for_nodes = [[] for i in xrange(self.num_nodes)]
        self.node_elevations = range(self.num_nodes)

        for node_name, node in self._wn.nodes():
            node_id = self._node_name_to_id[node_name]
            connected_links = self._wn.get_links_for_node(node_name)
            for link_name in connected_links:
                link = self._wn.get_link(link_name)
                link_id = self._link_name_to_id[link_name]
                if link.start_node() == node_name:
                    self.out_link_ids_for_nodes[node_id].append(link_id)
                elif link.end_node() == node_name:
                    self.in_link_ids_for_nodes[node_id].append(link_id)
                else:
                    raise RuntimeError('Node is neither start nor end node.')
            if node_id in self._junction_ids:
                self.node_elevations[node_id] = node.elevation
            elif node_id in self._tank_ids:
                self.node_elevations[node_id] = node.elevation
            elif node_id in self._reservoir_ids:
                self.node_elevations[node_id] = 0.0
            else:
                raise RuntimeError('Node type not recognized.')

    def _set_link_attributes(self):
        self.link_start_nodes = range(self.num_links)
        self.link_end_nodes = range(self.num_links)
        self.pipe_resistance_coefficients = range(self.num_links)
        self.head_curve_coefficients = {}
        self.pump_poly_coefficients = {} # {pump_id: (a,b,c,d)} a*x**3 + b*x**2 + c*x + d
        self.pump_powers = {}

        for link_name, link in self._wn.links():
            link_id = self._link_name_to_id[link_name]
            start_node_name = link.start_node()
            start_node_id = self._node_name_to_id[start_node_name]
            end_node_name = link.end_node()
            end_node_id = self._node_name_to_id[end_node_name]
            self.link_start_nodes[link_id] = start_node_id
            self.link_end_nodes[link_id] = end_node_id
            if link_id in self._pipe_ids:
                self.pipe_resistance_coefficients[link_id] = self._Hw_k*(link.roughness**(-1.852))*(link.diameter**(-4.871))*link.length # Hazen-Williams
            elif link_id in self._valve_ids:
                self.pipe_resistance_coefficients[link_id] = self._Dw_k*0.02*link.diameter**(-5)*link.diameter*2
            else:
                self.pipe_resistance_coefficients[link_id] = 0
            if link_id in self._pump_ids:
                if link.info_type == 'HEAD':
                    A, B, C = link.get_head_curve_coefficients()
                    self.head_curve_coefficients[link_id] = (A,B,C)
                    a,b,c,d = self.get_pump_poly_coefficients(A,B,C)
                    self.pump_poly_coefficients[link_id] = (a,b,c,d)
                elif link.info_type == 'POWER':
                    self.pump_powers[link_id] = link.power


    def _set_jacobian_structure(self):
        # Create the jacobian as a scipy.sparse.csr_matrix
        # Initialize all jacobian entries that have the possibility to be non-zero

        # Structure of jacobian:
        #
        # H_n => Head for node id n
        # D_n => Demand for node id n
        # F_l => Flow for link id l
        # node_bal_n => node balance for node id n
        # D/H_n      => demand/head equation for node id n
        # headloss_l => headloss equation for link id l
        # in link refers to a link that has node_n as an end node
        # out link refers to a link that has node_n as a start node
        # * means 1 if the node is a tank or reservoir, 0 otherwise
        # ** means 1 if the node is a junction, 0 otherwise
        # NZ means could be non-zero, but depends on network status and/or variable values
        #
        # Variable          H_1   H_2   H_n   H_(N-1)   H_N   D_1   D_2   D_n   D_(N-1)   D_N   F_1   F_2   F_l   F_(L-1)   F_L
        # Equation
        # node_bal_1         0     0     0     0         0     -1    0     0     0         0    (1 for in link, -1 for out link) 
        # node_bal_2         0     0     0     0         0     0     -1    0     0         0    (1 for in link, -1 for out link) 
        # node_bal_n         0     0     0     0         0     0     0     -1    0         0    (1 for in link, -1 for out link) 
        # node_bal_(N-1)     0     0     0     0         0     0     0     0     -1        0    (1 for in link, -1 for out link) 
        # node_bal_N         0     0     0     0         0     0     0     0     0         -1   (1 for in link, -1 for out link) 
        # D/H_1              *     0     0     0         0     **    0     0     0         0     0      0     0    0         0   
        # D/H_2              0     *     0     0         0     0     **    0     0         0     0      0     0    0         0
        # D/H_n              0     0     *     0         0     0     0     **    0         0     0      0     0    0         0
        # D/H_(N-1)          0     0     0     *         0     0     0     0     **        0     0      0     0    0         0
        # D/H_N              0     0     0     0         *     0     0     0     0         **    0      0     0    0         0
        # headloss_1         (NZ for start node and end node)  0     0     0     0         0     NZ     0     0    0         0
        # headloss_2         (NZ for start node and end node)  0     0     0     0         0     0      NZ    0    0         0
        # headloss_l         (NZ for start node and end node)  0     0     0     0         0     0      0     NZ   0         0
        # headloss_(L-1)     (NZ for start node and end node)  0     0     0     0         0     0      0     0    NZ        0
        # headloss_L         (NZ for start node and end node)  0     0     0     0         0     0      0     0    0         NZ


        num_vars = self.num_nodes*2 + self.num_links
        self.jac_row = []
        self.jac_col = []
        self.jac_values = []
        self.jac_ndx_of_first_headloss = 0

        value_ndx = 0
        row_ndx = 0
        # Jacobian entries for the node balance equations
        for node_id in self._node_ids:
            self.jac_row.append(row_ndx)
            self.jac_col.append(self.num_nodes + node_id)
            self.jac_values.append(-1.0)
            value_ndx += 1
            for link_id in self.in_link_ids_for_nodes[node_id]:
                self.jac_row.append(row_ndx)
                self.jac_col.append(link_id + 2*self.num_nodes)
                self.jac_values.append(1.0)
                value_ndx += 1
            for link_id in self.out_link_ids_for_nodes[node_id]:
                self.jac_row.append(row_ndx)
                self.jac_col.append(link_id + 2*self.num_nodes)
                self.jac_values.append(-1.0)
                value_ndx += 1
            row_ndx += 1

        # Jacobian entries for demand/head equations
        for node_id in self._node_ids:
            if node_id in self._tank_ids or node_id in self._reservoir_ids:
                self.jac_row.append(row_ndx)
                self.jac_col.append(node_id)
                self.jac_values.append(1.0)
                value_ndx += 1
            elif node_id in self._junction_ids:
                self.jac_row.append(row_ndx)
                self.jac_col.append(node_id + self.num_nodes)
                self.jac_values.append(1.0)
                value_ndx += 1
            row_ndx += 1

        self.jac_ndx_of_first_headloss = value_ndx

        # Jacobian entries for the headloss equations
        for link_id in self._link_ids:
            start_node_id = self.link_start_nodes[link_id]
            end_node_id = self.link_end_nodes[link_id]
            self.jac_row.append(row_ndx)
            self.jac_col.append(start_node_id)
            self.jac_values.append(0.0)
            value_ndx += 1
            self.jac_row.append(row_ndx)
            self.jac_col.append(end_node_id)
            self.jac_values.append(0.0)
            value_ndx += 1
            self.jac_row.append(row_ndx)
            self.jac_col.append(link_id + 2*self.num_nodes)
            self.jac_values.append(0.0)
            value_ndx += 1
            row_ndx += 1

        self.jacobian = sparse.csr_matrix((self.jac_values, (self.jac_row,self.jac_col)),shape=(num_vars,num_vars))

        self.jac_values = self.jacobian.data

    def get_hydraulic_equations(self, x):
        head = x[:self.num_nodes]
        demand = x[self.num_nodes:self.num_nodes*2]
        flow = x[self.num_nodes*2:]
        self.get_node_balance_residual(flow, demand)
        self.get_demand_or_head_residual(head, demand)
        self.get_headloss_residual(head, flow)

        all_residuals = np.concatenate((self.node_balance_residual, self.demand_or_head_residual, self.headloss_residual))

        return all_residuals

    def set_jacobian_constants(self):
        # set the jacobian entries that depend on the network status
        # but do not depend on the value of any variable.

        # ordering is very important here
        # the csr_matrix data is stored by going though all columns of the first row, then all columns of the second row, etc
        # ex:
        # row = [0,1,2,0,1,2,0,1,2]
        # col = [0,0,0,1,1,1,2,2,2]
        # value = [0,1,2,3,4,5,6,7,8]
        # A = sparse.csr_matrix((value,(row,col)),shape=(3,3))
        #
        # then A=>
        #          0   3  6
        #          1   4  7
        #          2   5  8
        # and A.data =>
        #              [0, 3, 6, 1, 4, 7, 2, 5, 8]

        value_ndx = self.jac_ndx_of_first_headloss

        # Set jacobian entries for headloss equations
        # Each row in the jacobian associated with a headloss equation
        # has 3 entries: one for the start node head, one for the end node
        # head, and one for the flow in the link. However, the ordering of
        # the start and end node heads is unknown.
        for link_id in self._link_ids:
            start_node_id = self.link_start_nodes[link_id]
            end_node_id = self.link_end_nodes[link_id]
            if self.link_status[link_id] == wntr.network.LinkStatus.closed:
                self.jac_values[value_ndx] = 0.0 # entry for start node head variable
                value_ndx += 1
                self.jac_values[value_ndx] = 0.0 # entry for end node head variable
                value_ndx += 1
                self.jac_values[value_ndx] = 1.0 # entry for flow variable
                value_ndx += 1
            elif self.link_types[link_id] == wntr.network.LinkTypes.pipe:
                if start_node_id < end_node_id:
                    self.jac_values[value_ndx] = -1.0 # entry for start node head variable
                    value_ndx += 1
                    self.jac_values[value_ndx] = 1.0 # entry for end node head variable
                    value_ndx += 1
                else:
                    self.jac_values[value_ndx] = 1.0 # entry for end node head variable
                    value_ndx += 1
                    self.jac_values[value_ndx] = -1.0 # entry for start node head variable 
                    value_ndx += 1
                value_ndx += 1 # for the entry on that row for the flow variable
            elif self.link_types[link_id] == wntr.network.LinkTypes.pump:
                if link_id in self.head_curve_coefficients.keys():
                    if start_node_id < end_node_id:
                        self.jac_values[value_ndx] = 1.0 # entry for start node head variable
                        value_ndx += 1
                        self.jac_values[value_ndx] = -1.0 # entry for end node head variable
                        value_ndx += 1
                    else:
                        self.jac_values[value_ndx] = -1.0 # entry for end node head variable
                        value_ndx += 1
                        self.jac_values[value_ndx] = 1.0 # entry for start node head variable 
                        value_ndx += 1
                    value_ndx += 1 # for the entry on that row for the flow variable
                elif link_id in self.pump_powers.keys():
                    value_ndx += 3
                else:
                    raise RuntimeError('Developers missed a type of pump in set_jacobian_constants.')
            elif self.link_types[link_id] == wntr.network.LinkTypes.valve:
                if link_id in self._prv_ids:
                    if self.link_status[link_id] == LinkStatus.active: # Active
                        if start_node_id < end_node_id: # start node column comes first
                            self.jac_values[value_ndx] = 0.0
                            value_ndx += 1
                            self.jac_values[value_ndx] = 1.0
                            value_ndx += 1
                            self.jac_values[value_ndx] = 0.0
                            value_ndx += 1
                        else: # end node column comes first
                            self.jac_values[value_ndx] = 1.0
                            value_ndx += 1
                            self.jac_values[value_ndx] = 0.0
                            value_ndx += 1
                            self.jac_values[value_ndx] = 0.0
                            value_ndx += 1
                    elif self.link_status[link_id] == LinkStatus.opened:
                        if start_node_id < end_node_id: # start node column comes first
                            self.jac_values[value_ndx] = -1.0
                            value_ndx += 1
                            self.jac_values[value_ndx] = 1.0
                            value_ndx += 1
                            value_ndx += 1
                        else: # end node column comes first
                            self.jac_values[value_ndx] = 1.0
                            value_ndx += 1
                            self.jac_values[value_ndx] = -1.0
                            value_ndx += 1
                            value_ndx += 1
                    elif self.link_status[link_id] == LinkStatus.closed:
                        self.jac_values[value_ndx] = 0.0
                        value_ndx += 1
                        self.jac_values[value_ndx] = 0.0
                        value_ndx += 1
                        self.jac_values[value_ndx] = 1.0
                        value_ndx += 1
                    else:
                        raise RuntimeError('Valve setting not recognized.')
                else:
                    raise RuntimeError('Developers missed a type of valve.')
            else:
                raise RuntimeError('Developers missed a type of link in set_jacobian_constants')

        self.jacobian.data = self.jac_values

    def get_jacobian(self, x):

        value_ndx = self.jac_ndx_of_first_headloss
        flows = x[self.num_nodes*2:]

        # Set the jacobian entries that depend on variable values
        for link_id in self._link_ids:
            if self.link_status[link_id] == wntr.network.LinkStatus.closed:
                value_ndx += 3
            elif self.link_types[link_id] == wntr.network.LinkTypes.pipe:
                value_ndx += 2
                flow = flows[link_id]
                pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                if flow < -self.hw_q2:
                    self.jac_values[value_ndx] = 1.852*pipe_resistance_coeff*abs(flow)**0.852
                elif flow <= -self.hw_q1:
                    self.jac_values[value_ndx] = pipe_resistance_coeff*(3.0*self.hw_a*abs(flow)**2 + 2*self.hw_b*abs(flow) + self.hw_c)
                elif flow <= 0.0:
                    self.jac_values[value_ndx] = pipe_resistance_coeff*self.hw_m
                elif flow < self.hw_q1:
                    self.jac_values[value_ndx] = pipe_resistance_coeff*self.hw_m
                elif flow <= self.hw_q2:
                    self.jac_values[value_ndx] = pipe_resistance_coeff*(3.0*self.hw_a*flow**2 + 2*self.hw_b*flow + self.hw_c)
                else:
                    self.jac_values[value_ndx] = 1.852*pipe_resistance_coeff*flow**0.852
                value_ndx += 1
            elif self.link_types[link_id] == wntr.network.LinkTypes.pump:
                flow = flows[link_id]
                if link_id in self.head_curve_coefficients.keys():
                    value_ndx += 2
                    if flow <= self.pump_q1:
                        self.jac_values[value_ndx] = self.pump_m
                    elif flow <= self.pump_q2:
                        a,b,c,d = self.pump_poly_coefficients[link_id]
                        self.jac_values[value_ndx] = 3.0*a*flow**2.0 + 2.0*b*flow + c
                    else:
                        A,B,C = self.head_curve_coefficients[link_id]
                        self.jac_values[value_ndx] = -B*C*flow**(C-1.0)
                    value_ndx += 1
                elif link_id in self.pump_powers.keys():
                    start_node_id = self.link_start_nodes[link_id]
                    end_node_id = self.link_end_nodes[link_id]
                    if start_node_id < end_node_id: # start node head comes first
                        self.jac_values[value_ndx] = 1000.0*self._g*flow
                        value_ndx += 1
                        self.jac_values[value_ndx] = -1000.0*self._g*flow
                        value_ndx += 1
                    else:
                        self.jac_values[value_ndx] = -1000.0*self._g*flow
                        value_ndx += 1
                        self.jac_values[value_ndx] = 1000.0*self._g*flow
                        value_ndx += 1
                    self.jac_values[value_ndx] = 1000.0*self._g*x[start_node_id] - 1000.0*self._g*x[end_node_id]
                    value_ndx += 1
            elif self.link_types[link_id] == wntr.network.LinkTypes.valve:
                if link_id in self._prv_ids:
                    if self.link_status[link_id] == LinkStatus.active: # active valve
                        value_ndx += 3
                    elif self.link_status[link_id] == LinkStatus.opened:
                        value_ndx += 2
                        flow = flows[link_id]
                        pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                        self.jac_values[value_ndx] = 2.0*pipe_resistance_coeff*abs(flow)
                        value_ndx += 1
                    elif self.link_status[link_id] == LinkStatus.closed:
                        value_ndx += 3

        self.jacobian.data = self.jac_values
        #self.check_jac_for_zero_rows()
        #self.print_jacobian_nonzeros()
        #self.check_jac(x)
        return self.jacobian

    def get_node_balance_residual(self, flow, demand):
        """
        Mass balance at all the nodes

        Parameters
        ----------
        flow : list of floats
             List of flow values in each pipe

        Returns
        -------
        List of residuals of the node mass balances
        """

        for node_id in xrange(self.num_nodes):
            expr = 0
            for link_id in self.out_link_ids_for_nodes[node_id]:
                expr -= flow[link_id]
            for link_id in self.in_link_ids_for_nodes[node_id]:
                expr += flow[link_id]
            self.node_balance_residual[node_id] = expr - demand[node_id]

    def get_headloss_residual(self, head, flow):

        for link_id in self._pipe_ids:
            link_flow = flow[link_id]
            if self.link_status[link_id] == wntr.network.LinkStatus.closed:
                self.headloss_residual[link_id] = link_flow
            else:
                start_node_id = self.link_start_nodes[link_id]
                end_node_id = self.link_end_nodes[link_id]

                pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                if link_flow < -self.hw_q2:
                    pipe_headloss = -pipe_resistance_coeff*abs(link_flow)**1.852
                elif link_flow <= -self.hw_q1:
                    pipe_headloss = -pipe_resistance_coeff*(self.hw_a*abs(link_flow)**3 + self.hw_b*abs(link_flow)**2 + self.hw_c*abs(link_flow) + self.hw_d)
                elif link_flow <= 0.0:
                    pipe_headloss = -pipe_resistance_coeff*self.hw_m*abs(link_flow)
                elif link_flow < self.hw_q1:
                    pipe_headloss = pipe_resistance_coeff*self.hw_m*link_flow
                elif link_flow <= self.hw_q2:
                    pipe_headloss = pipe_resistance_coeff*(self.hw_a*link_flow**3 + self.hw_b*link_flow**2 + self.hw_c*link_flow + self.hw_d)
                else:
                    pipe_headloss = pipe_resistance_coeff*link_flow**1.852
                self.headloss_residual[link_id] = pipe_headloss - (head[start_node_id] - head[end_node_id])

        for link_id in self._pump_ids:
            link_flow = flow[link_id]
            if self.link_status[link_id] == wntr.network.LinkStatus.closed:
                self.headloss_residual[link_id] = link_flow
            else:
                start_node_id = self.link_start_nodes[link_id]
                end_node_id = self.link_end_nodes[link_id]

                if link_id in self.head_curve_coefficients.keys():
                    if link_flow <= self.pump_q1:
                        A,B,C = self.head_curve_coefficients[link_id]
                        pump_headgain = self.pump_m*link_flow + A
                    elif link_flow <= self.pump_q2:
                        a,b,c,d = self.pump_poly_coefficients[link_id]
                        pump_headgain = a*link_flow**3 + b*link_flow**2 + c*link_flow + d
                    else:
                        A,B,C = self.head_curve_coefficients[link_id]
                        pump_headgain = 1.0*A - B*link_flow**C
                    self.headloss_residual[link_id] = pump_headgain - (head[end_node_id] - head[start_node_id])
                elif link_id in self.pump_powers.keys():
                    self.headloss_residual[link_id] = self.pump_powers[link_id] - (head[end_node_id]-head[start_node_id])*flow[link_id]*self._g*1000.0
                else:
                    raise RuntimeError('Only power and head pumps are currently supported.')
                    
        for link_id in self._prv_ids:
            link_flow = flow[link_id]
            start_node_id = self.link_start_nodes[link_id]
            end_node_id = self.link_end_nodes[link_id]

            if self.link_status[link_id] == LinkStatus.active:
                self.headloss_residual[link_id] = head[end_node_id] - (self.valve_settings[link_id]+self.node_elevations[end_node_id])
            elif self.link_status[link_id] == LinkStatus.opened:
                pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                pipe_headloss = pipe_resistance_coeff*abs(flow)**2
                self.headloss_residual[link_id] = pipe_headloss - (head[start_node_id]-head[end_node_id])
            elif self.link_status[link_id] == wntr.network.LinkStatus.closed:
                self.headloss_residual[link_id] = link_flow

    def get_demand_or_head_residual(self, head, demand):

        for node_id in self._junction_ids:
            #if self._pressure_driven:
            #    node_elevation = self.node_elevations[node_id]
            #    raise NotImplementedError('PDD is not implemented yet.')
            #else:
            self.demand_or_head_residual[node_id] = demand[node_id] - self.junction_demand[node_id]
        for node_id in self._tank_ids:
            self.demand_or_head_residual[node_id] = head[node_id] - self.tank_head[node_id]
        for node_id in self._reservoir_ids:
            self.demand_or_head_residual[node_id] = head[node_id] - self.reservoir_head[node_id]

    def initialize_flow(self):
        flow = 0.001*np.ones(self.num_links)
        return flow

    def initialize_head(self):
        head = np.zeros(self.num_nodes)
        for junction_id in self._junction_ids:
            head[junction_id] = self.node_elevations[junction_id]
        for tank_id in self._tank_ids:
            head[tank_id] = self.tank_head[tank_id]
        for reservoir_id in self._reservoir_ids:
            head[reservoir_id] = self.reservoir_head[reservoir_id]
        return head

    def initialize_demand(self):
        demand = np.zeros(self.num_nodes)
        for junction_id in self._junction_ids:
            demand[junction_id] = self.junction_demand[junction_id]
        return demand

    def initialize_results_dict(self):
        # Data for results object
        self._sim_results = {}
        self._sim_results['node_name'] = []
        self._sim_results['node_type'] = []
        self._sim_results['node_times'] = []
        self._sim_results['node_head'] = []
        self._sim_results['node_demand'] = []
        self._sim_results['node_expected_demand'] = []
        self._sim_results['node_pressure'] = []
        self._sim_results['link_name'] = []
        self._sim_results['link_type'] = []
        self._sim_results['link_times'] = []
        self._sim_results['link_flowrate'] = []

    def save_results(self, x, results):
        head = x[:self.num_nodes]
        demand = x[self.num_nodes:2*self.num_nodes]
        flow = x[2*self.num_nodes:]
        for node_id in self._junction_ids:
            head_n = head[node_id]
            self._sim_results['node_type'].append('Junction')
            self._sim_results['node_head'].append(head_n)
            self._sim_results['node_demand'].append(demand[node_id])
            self._sim_results['node_expected_demand'].append(self.junction_demand[node_id])
            self._sim_results['node_pressure'].append(head_n - self.node_elevations[node_id])
        for node_id in self._tank_ids:
            head_n = head[node_id]
            demand_n = demand[node_id]
            self._sim_results['node_type'].append('Tank')
            self._sim_results['node_head'].append(head_n)
            self._sim_results['node_demand'].append(demand_n)
            self._sim_results['node_expected_demand'].append(demand_n)
            self._sim_results['node_pressure'].append(head_n - self.node_elevations[node_id])
        for node_id in self._reservoir_ids:
            demand_n = demand[node_id]
            self._sim_results['node_type'].append('Reservoir')
            self._sim_results['node_head'].append(head[node_id])
            self._sim_results['node_demand'].append(demand_n)
            self._sim_results['node_expected_demand'].append(demand_n)
            self._sim_results['node_pressure'].append(0.0)

        for link_id in self._link_ids:
            self._sim_results['link_type'].append(LinkTypes.link_type_to_str(self.link_types[link_id]))
            self._sim_results['link_flowrate'].append(flow[link_id])

    def get_results(self,results):
        ntimes = len(results.time)
        nnodes = self.num_nodes
        nlinks = self.num_links
        tmp_node_names = self._junction_ids+self._tank_ids+self._reservoir_ids
        node_names = [self._node_id_to_name[i] for i in tmp_node_names]
        link_names = [self._link_id_to_name[i] for i in self._link_ids]

        node_dictionary = {'demand': self._sim_results['node_demand'],
                           'expected_demand': self._sim_results['node_expected_demand'],
                           'head': self._sim_results['node_head'],
                           'pressure': self._sim_results['node_pressure'],
                           'type': self._sim_results['node_type']}
        for key,value in node_dictionary.iteritems():
            node_dictionary[key] = np.array(value).reshape((ntimes,nnodes))
        results.node = pd.Panel(node_dictionary, major_axis=results.time, minor_axis=node_names)

        link_dictionary = {'flowrate':self._sim_results['link_flowrate'],
                           'type':self._sim_results['link_type']}
        for key, value in link_dictionary.iteritems():
            link_dictionary[key] = np.array(value).reshape((ntimes, nlinks))
        results.link = pd.Panel(link_dictionary, major_axis=results.time, minor_axis=link_names)

    def set_network_inputs_by_id(self):
        for tank_name, tank in self._wn.tanks():
            tank_id = self._node_name_to_id[tank_name]
            self.tank_head[tank_id] = tank.head
        for reservoir_name, reservoir in self._wn.reservoirs():
            reservoir_id = self._node_name_to_id[reservoir_name]
            self.reservoir_head[reservoir_id] = reservoir.head
        for junction_name, junction in self._wn.junctions():
            junction_id = self._node_name_to_id[junction_name]
            self.junction_demand[junction_id] = junction.expected_demand
        for link_name, link in self._wn.links():
            link_id = self._link_name_to_id[link_name]
            self.link_status[link_id] = link.status
        for valve_name, valve in self._wn.valves():
            valve_id = self._link_name_to_id[valve_name]
            self.valve_settings[valve_id] = valve.setting
        for pump_name, pump in self._wn.pumps():
            pump_id = self._link_name_to_id[pump_name]
            self.pump_speeds[pump_id] = pump.speed

    def update_tank_heads(self):
        for tank_name, tank in self._wn.tanks():
            q_net = tank.prev_demand
            delta_h = 4.0*q_net*(self._wn.sim_time-self._wn.prev_sim_time)/(math.pi*tank.diameter**2)
            tank.head = tank.prev_head + delta_h

    def update_junction_demands(self, demand_dict):
        for junction_name, junction in self._wn.junctions():
            t = math.floor(self._wn.sim_time/self._wn.options.hydraulic_timestep)
            junction.expected_demand = demand_dict[(junction_name,t)]

    def update_network_previous_values(self):
        self._wn.prev_sim_time = self._wn.sim_time
        for name, node in self._wn.junctions():
            node.prev_head = node.head
            node.prev_demand = node.demand
            node.prev_expected_demand = node.expected_demand
        for name, node in self._wn.tanks():
            node.prev_head = node.head
            node.prev_demand = node.demand
        for name, node in self._wn.reservoirs():
            node.prev_head = node.head
            node.prev_demand = node.demand
        for link_name, link in self._wn.pipes():
            link.prev_status = link.status
            link.prev_flow = link.flow
        for link_name, link in self._wn.pumps():
            link.prev_status = link.status
            link.prev_flow = link.flow
            link.prev_speed = link.speed
        for link_name, link in self._wn.valves():
            link.prev_status = link.status
            link.prev_flow = link.flow
            link.prev_setting = link.setting

    def store_results_in_network(self, x):
        head = x[:self.num_nodes]
        demand = x[self.num_nodes:self.num_nodes*2]
        flow = x[self.num_nodes*2:]
        for name, node in self._wn.nodes():
            node_id = self._node_name_to_id[name]
            node.head = head[node_id]
            node.demand = demand[node_id]
        for link_name, link in self._wn.links():
            link_id = self._link_name_to_id[link_name]
            link.flow = flow[link_id]

    def update_previous_inputs(self):
        self.prev_tank_head = copy.copy(self.tank_head)
        self.prev_reservoir_head = copy.copy(self.reservoir_head)
        self.prev_junction_demand = copy.copy(self.junction_demand)
        self.prev_link_status = copy.copy(self.link_status)
        self.prev_valve_settings = copy.copy(self.valve_settings)
        self.prev_pump_speeds = copy.copy(self.pump_speeds)

    def check_inputs_changed(self):
        if self.prev_tank_head != self.tank_head:
            return True
        if self.prev_reservoir_head != self.reservoir_head:
            return True
        if self.prev_junction_demand != self.junction_demand:
            return True
        if self.prev_link_status != self.link_status:
            return True
        if self.prev_valve_settings != self.valve_settings:
            return True
        if self.prev_pump_speeds != self.pump_speeds:
            return True
        return False

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
        A = np.matrix([[x1**3.0, x1**2.0, x1, 1.0],
                       [x2**3.0, x2**2.0, x2, 1.0],
                       [3.0*x1**2.0, 2.0*x1, 1.0, 0.0],
                       [3.0*x2**2.0, 2.0*x2, 1.0, 0.0]])
        rhs = np.matrix([[f1],
                         [f2],
                         [df1],
                         [df2]])
        x = np.linalg.solve(A,rhs)
        return (float(x[0][0]), float(x[1][0]), float(x[2][0]), float(x[3][0]))

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

    def print_jacobian(self, jacobian):
        #np.set_printoptions(threshold='nan')
        #print jacobian.toarray()
            
        def construct_string(name, values):
            string = '{0:<10s}'.format(name)
            for i in xrange(len(values)):
                if type(values[i]) == str:
                    string = string+'{0:<6s}'.format(values[i])
                else:
                    string = string+'{0:<6.2f}'.format(values[i])
            return string

        print construct_string('variable',[node_name for node_name, node in self._wn.nodes()]+[node_name for node_name, node in self._wn.nodes()]+[link_name for link_name, link in self._wn.links()])
        for node_id in xrange(self.num_nodes):
            print construct_string(self._node_id_to_name[node_id], jacobian.getrow(node_id).toarray()[0])
        for node_id in xrange(self.num_nodes):
            print construct_string(self._node_id_to_name[node_id], jacobian.getrow(self.num_nodes+node_id).toarray()[0])
        for link_id in xrange(self.num_links):
            print construct_string(self._link_id_to_name[link_id], jacobian.getrow(2*self.num_nodes+link_id).toarray()[0])

    def print_jacobian_nonzeros(self):
        print('{0:<15s}{1:<15s}{2:<25s}{3:<25s}{4:<15s}'.format('row index','col index','eqnuation','variable','value'))
        for i in xrange(self.jacobian.shape[0]):
            row_nnz = self.jacobian.indptr[i+1] - self.jacobian.indptr[i]
            for k in xrange(row_nnz):
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
        approx_jac = np.matrix(np.zeros((self.num_nodes*2+self.num_links, self.num_nodes*2+self.num_links)))

        step = 0.0001

        resids = self.get_hydraulic_equations(x)

        print 'shape = (',len(x),',',len(x),')'
        for i in xrange(len(x)):
            print 'getting approximate derivative of column ',i
            x1 = copy.copy(x)
            x2 = copy.copy(x)
            x1[i] = x1[i] + step
            x2[i] = x2[i] + 2*step
            resids1 = self.get_hydraulic_equations(x1)
            resids2 = self.get_hydraulic_equations(x2)
            deriv_column = (-3.0*resids+4.0*resids1-resids2)/(2*step)
            approx_jac[:,i] = np.matrix(deriv_column).transpose()

        approx_jac = sparse.csr_matrix(approx_jac)

        difference = approx_jac - self.jacobian

        success = True
        for i in xrange(self.jacobian.shape[0]):
            print 'comparing values in row ',i,'with non-zeros from self.jacobain'
            row_nnz = self.jacobian.indptr[i+1] - self.jacobian.indptr[i]
            for k in xrange(row_nnz):
                j = self.jacobian.indices[self.jacobian.indptr[i]+k]
                if abs(approx_jac[i,j]-self.jacobian[i,j]) > 0.1:
                    if i < self.num_nodes:
                        equation_type = 'node balance'
                        node_or_link = 'node'
                        node_or_link_name = self._node_id_to_name[i]
                    elif i < 2*self.num_nodes:
                        equation_type = 'demand/head equation'
                        node_or_link = 'node'
                        node_or_link_name = self._node_id_to_name[i - self.num_nodes]
                    else:
                        equation_type = 'headloss'
                        node_or_link = 'link'
                        node_or_link_name = self._link_id_to_name[i - 2*self.num_nodes]
                        print 'flow for link ',node_or_link_name,' = ',x[i]
                    if j < self.num_nodes:
                        wrt = 'head'
                        wrt_name = self._node_id_to_name[j]
                    elif j< 2*self.num_nodes:
                        wrt = 'demand'
                        wrt_name = self._node_id_to_name[j - self.num_nodes]
                    else:
                        wrt = 'flow'
                        wrt_name = self._link_id_to_name[j - 2*self.num_nodes]
                    print 'jacobian entry for ',equation_type,' for ',node_or_link,' ',node_or_link_name,' with respect to ',wrt,wrt_name,' is incorrect.'
                    print 'error = ',abs(approx_jac[i,j]-self.jacobian[i,j])
                    print 'approximation = ',approx_jac[i,j]
                    print 'exact = ',self.jacobian[i,j]
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
        for i in xrange(self.jacobian.shape[0]):
            all_zero_flag = False
            row_nnz = self.jacobian.indptr[i+1] - self.jacobian.indptr[i]
            if row_nnz <= 0:
                all_zero_flag = True
            non_zero_flag = False
            for k in xrange(row_nnz):
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
                print 'jacobian row for ',equation_type,' for ',node_or_link_name,' has all zero entries.'
