from wntr import *
import numpy as np
import scipy.sparse as sparse


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

        # Initialize Jacobian
        self._set_jacobian_structure()

    def _initialize_global_constants(self):
        self._Hw_k = 10.666829500036352 # Hazen-Williams resistance coefficient in SI units (it equals 4.727 in EPANET GPM units). See Table 3.1 in EPANET 2 User manual.
        self._Dw_k = 0.0826 # Darcy-Weisbach constant in SI units (it equals 0.0252 in EPANET GPM units). See Table 3.1 in EPANET 2 User manual.
        self._g = 9.81 # Acceleration due to gravity

    def _initialize_name_id_maps(self):
        self._node_id_to_name = {}
        self._node_name_to_id = {}
        self._link_id_to_name = {}
        self._link_name_to_id = {}
        self._node_ids = []
        self._junction_ids = []
        self._tank_ids = []
        self._reservoir_ids = []
        self._link_ids = []
        self._pipe_ids = []
        self._pump_ids = []
        self._valve_ids = []
        self._prv_ids = []
        self._psv_ids = []
        self._pbv_ids = []
        self._fcv_ids = []
        self._tcv_ids = []

        n = 0
        for node_name, node in self._wn.nodes():
            self._node_id_to_name[n] = node_name
            self._node_name_to_id[node_name] = n
            self._node_ids.append(n)
            if isinstance(node, Tank):
                self._tank_ids.append(n)
            elif isinstance(node, Reservoir):
                self._reservoir_ids.append(n)
            elif isinstance(node, Junction):
                self._junction_ids.append(n)
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
            elif isinstance(link, Pump):
                self._pump_ids.append(l)
            elif isinstance(link, Valve):
                self._valve_ids.append(l)
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
                self.pipe_resistance_coefficients[link_id] = self._Dw_k*0.02*link.diameter**(-5)*link_diameter*2
            else:
                self.pipe_resistance_coefficients[link_id] = 0
            if link_id in self._pump_ids:
                if link.info_type == 'HEAD':
                    A, B, C = link.get_head_curve_coefficients()
                    self.head_curve_coefficients[link_id] = (A,B,C)
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

        print self.jacobian.toarray()

    def get_hydraulic_equations(self, x):
        head = x[:self.num_nodes]
        demand = x[self.num_nodes:self.num_nodes*2]
        flow = x[self.num_nodes*2:]
        self.get_node_balance_residual(flow, demand)
        self.get_demand_or_head_residual(head, demand)
        self.get_headloss_residual(head, flow)

        all_residuals = np.concatenate((self.node_balance_residual, self.demand_or_head_residual, self.headloss_residual))

        return all_residuals

    def set_jacobian_constants(self, links_closed, valve_settings):
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
            if link_id in links_closed:
                self.jac_values[value_ndx] = 0.0 # entry for start node head variable
                value_ndx += 1
                self.jac_values[value_ndx] = 0.0 # entry for end node head variable
                value_ndx += 1
                self.jac_values[value_ndx] = 1.0 # entry for flow variable
                value_ndx += 1
            elif link_id in self._pipe_ids:
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
            elif link_id in self._pump_ids:
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
            elif link_id in self._valve_ids:
                if link_id in self._prv_ids:
                    if type(valve_settings[link_id]) == float: # Active
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
                    elif valve_settings[link_id] == 'OPEN':
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
                    elif valve_settings[link_id] == 'CLOSED':
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

    def get_jacobian(self, x, links_closed, valve_settings):

        value_ndx = self.jac_ndx_of_first_headloss
        flows = x[self.num_nodes*2:]

        # Set the jacobian entries that depend on variable values
        for link_id in self._link_ids:
            if link_id in links_closed:
                value_ndx += 3
            elif link_id in self._pipe_ids:
                value_ndx += 2
                flow = flows[link_id]
                pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                if flow < -self.hw_q2:
                    self.jac_values[value_ndx] = -1.852*pipe_resistance_coeff*abs(flow)**0.852
                elif flow <= -self.hw_q1:
                    self.jac_values[value_ndx] = -pipe_resistance_coeff*(3.0*self.hw_a*abs(flow)**2 + 2*self.hw_b*abs(flow) + self.hw_c)
                elif flow <= 0.0:
                    self.jac_values[value_ndx] = -pipe_resistance_coeff*self.hw_m
                elif flow < self.hw_q1:
                    self.jac_values[value_ndx] = pipe_resistance_coeff*self.hw_m
                elif flow <= self.hw_q2:
                    self.jac_values[value_ndx] = pipe_resistance_coeff*(3.0*self.hw_a*flow**2 + 2*self.hw_b*flow + self.hw_c)
                else:
                    self.jac_values[value_ndx] = 1.852*pipe_resistance_coeff*flow**0.852
                value_ndx += 1
            elif link_id in self._pump_ids:
                flow = flows[link_id]
                if link_id in self.head_curve_coefficients.keys():
                    value_ndx += 2
                    head_curve_tuple = self.head_curve_coefficients[link_id]
                    B = head_curve_tuple[1]
                    C = head_curve_tuple[2]
                    self.jac_values[value_ndx] = -B*C*abs(flow)**(C-1.0)
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
            elif link_id in self._valve_ids:
                if link_id in self._prv_ids:
                    if type(valve_settings[link_id]) == float: # active valve
                        value_ndx += 3
                    elif valve_settings[link_id] == 'OPEN':
                        value_ndx += 2
                        flow = flows[link_id]
                        pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                        self.jac_values[value_ndx] = 2.0*pipe_resistance_coeff*abs(flow)
                        value_ndx += 1
                    elif valve_settings[link_id] == 'CLOSED':
                        value_ndx += 3

        self.jacobian.data = self.jac_values
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
            for l in self.out_link_ids_for_nodes[node_id]:
                expr -= flow[link_id]
            for l in self.in_link_ids_for_nodes[node_id]:
                expr += flow[link_id]
            self.node_balance_residual[node_id] = expr - demand[node_id]

    def get_headloss_residual(self, head, flow, links_closed, valve_settings):

        for link_id in xrange(self.num_links):
            link_flow = flow[link_id]
            start_node_id = self.link_start_nodes[link_id]
            end_node_id = self.link_end_nodes[link_id]

            if link_id in links_closed:
                self.headloss_residual[link_id] = link_flow

            elif link_id in self._pipe_ids:
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

            elif link_id in self._pump_ids:
                if link_id in self.head_curve_coefficients.keys():
                    head_curve_tuple = self.head_curve_coefficients[link_id]
                    A = head_curve_tuple[0]
                    B = head_curve_tuple[1]
                    C = head_curve_tuple[2]
                    pump_headgain = 1.0*A - B*abs(link_flow)**C
                    self.headloss_residual[link_id] = pump_headgain - (head[end_node_id] - head[start_node_id])
                elif link_id in self.pump_powers.keys():
                    self.headloss_residual[link_id] = self.pump_powers[link_id] - (head[end_node_id]-head[start_node_id])*flow[link_id]*self._g*1000.0
                else:
                    raise RuntimeError('Only power and head pumps are currently supported.')
                    

            elif link_id in self._valve_ids:
                if link_id in self._prv_ids:
                    if type(valve_settings[link_id]) == float:
                        self.headloss_residual[link_id] = head[end_node_id] - (valve_settings[link_id]+self.node_elevations[end_node_id])
                    elif valve_settings[link_id] == 'OPEN':
                        pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                        pipe_headloss = pipe_resistance_coeff*abs(flow)**2
                        self.headloss_residual[link_id] = pipe_headloss - (head[start_node_id]-head[end_node_id])
                    elif valve_settings[link_id] == 'CLOSED':
                        self.headloss_residual[link_id] = link_flow
                else:
                    raise RuntimeError('Only PRV valves are currently supported.')

            else:
                raise RuntimeError('Type of link is not recognized')

    def get_demand_or_head_residual(self, head, demand, expected_demands, tank_heads, reservoir_heads):

        for node_id in xrange(self.num_nodes):
            if node_id in self._junction_ids:
                if self._pressure_driven:
                    node_elevation = self.node_elevations[node_id]
                    raise NotImplementedError('PDD is not implemented yet.')
                else:
                    self.demand_or_head_residual[node_id] = demand[node_id] - expected_demands[node_id]
            elif node_id in self._tank_ids:
                self.demand_or_head_residual[node_id] = head[node_id] - tank_heads[node_id]
            elif node_id in self._reservoir_ids:
                self.demand_or_head_residual[node_id] = head[node_id] - reservoir_heads[node_id]
