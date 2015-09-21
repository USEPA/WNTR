from wntr import *
import numpy as np
import scipy.sparse as sparse
import warnings


class ScipySimulator(WaterNetworkSimulator):
    """
    Run simulation using custom newton solver and linear solvers from scipy.sparse.
    """

    def __init__(self, wn):
        """
        Simulator object to be used for running scipy simulations.

        Parameters
        ----------
        wn : WaterNetworkModel
            A water network
        """

        WaterNetworkSimulator.__init__(self.wn)

        # Global constants
        self._initialize_global_constants()

        # Initialize dictionaries to map between node/link names and ids
        self._initialize_name_id_maps()

        # Number of nodes and links
        self.num_nodes = len(self._node_id_to_name.keys())
        self.num_links = len(self._link_id_to_name.keys())

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
        self._init_jacobian()

    def _initialize_global_constants(self):
        self._Hw_k = 10.666829500036352 # Hazen-Williams resistance coefficient in SI units (it equals 4.727 in EPANET GPM units). See Table 3.1 in EPANET 2 User manual.
        self._Dw_k = 0.0826 # Darcy-Weisbach constant in SI units (it equals 0.0252 in EPANET GPM units). See Table 3.1 in EPANET 2 User manual.
        self._Htol = 0.00015 # Head tolerance in meters.
        self._Qtol = 2.8e-5 # Flow tolerance in m^3/s.
        self._g = 9.81 # Acceleration due to gravity
        self._slope_of_PDD_curve = 1e-11 # The flat lines in the PDD model are provided a small slope for numerical stability
        self._pdd_smoothing_delta = 0.1 # Tightness of polynomial used to smooth sharp changes in PDD model.

    def _initialize_name_id_maps(self):
        self._node_id_to_name = {}
        self._node_name_to_id = {}
        self._link_id_to_name = {}
        self._link_name_to_id = {}
        self._junction_ids = []
        self._tank_ids = []
        self._reservoir_ids = []
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

    def _init_jacobian(self):
        # TODO: There is no need to loop over all columns - we know which ones matter

        # Create the jacobian as a scipy.sparse.csr_matrix
        # Initialize with any jacobian entry that has the possibility to be non-zero as 1.0
        num_vars = self.num_nodes*2 + self.num_links
        row = []
        col = []
        data = []

        % csrm.data[4] = 6.2
        


        row_idx = 0
        # create the node balance equations
        for n in Nodes:
            add.some_stuff()
            row_idx += 1

        # create the pipe headloss equations
        for p in Pipes:
            add_some_other_stuff
            row_idx += 1

        for i in xrange(num_vars): # Equations/rows
            for j in xrange(num_vars): # Variabls/Columns
                if i < self.num_nodes: # Node balances
                    if j == self.num_nodes + i:
                        row.append(i)
                        col.append(j)
                        data.append(-1.0)
                    elif j >= 2*self.num_nodes:
                        link_id = j - 2*self.num_nodes
                        node_id = i
                        if link_id in self.in_link_ids_for_nodes[node_id]:
                            row.append(i)
                            col.append(j)
                            data.append(1.0)
                        elif link_id in self.out_link_ids_for_nodes[node_id]:
                            row.append(i)
                            col.append(j)
                            data.append(-1.0)
                elif i < 2*self.num_nodes: # Demand/Head equations
                    node_id = i - self.num_nodes
                    if node_id in self._tank_ids or node_id in self._reservoir_ids:
                        if j == node_id:
                            row.append(i)
                            col.append(j)
                            data.append(1.0)
                    elif node_id in self._junction_ids:
                        if j == i:
                            row.append(i)
                            col.append(j)
                            data.append(1.0)
                elif i < 2*self.num_nodes + self.num_links: # Headloss equations
                    link_id = i - 2*self.num_nodes
                    if j == self.link_start_nodes[link_id] or j == self.link_end_nodes[link_id]:
                        row.append(i)
                        col.append(j)
                        data.append(1.0)
                    elif i == j:
                        row.append(i)
                        col.append(j)
                        data.append(1.0)
                
        self.jacobian = sparse.csr_matrix((data, (row,col)),shape=(num_vars,num_vars))

        print self.jacobian.toarray()

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


    def run_sim(self):
        """
        Method to run an extended period simulation
        """
        # Create NetworkStatus object
        net_status = NetworkStatus(self._wn)
        self.solver = NewtonSolver()

        # Initialize X
        # Vars will be ordered:
        #    1.) head
        #    2.) demand
        #    3.) flow
        self.head0 = np.zeros(self.num_nodes)
        self.demand0 = np.zeros(self.num_nodes)
        self.flow0 = np.zeros(self.num_links)
        self._initialize_head(net_status)
        self._initialize_demand(net_status)
        self._initialize_flow(net_status)
        self._X_init = np.concatenate((self.head0, self.demand0, self.flow0))

        while net_status.time_sec <= self._wn.time_options['DURATION']:
            self.set_jacobian_constants()
            self._X = self.solve_hydraulics(net_status)
            results = self.save_results(self._X)
            net_status.update_network_status(results)

    def solve_hydraulics(self, x0, net_status):
        """
        Method to solve the hydraulic equations given the network status

        Parameters
        ----------
        net_status: a NetworkStatus object
        """

        self.solver.solve(self._hydraulic_equations, self.get_jacobian, x0)

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
        for i in xrange(self.num_nodes*2, self.num_nodes*2+self.num_links): # Equations/rows
            link_id = i - 2*self.num_nodes
            start_node_id = self.link_start_nodes[link_id]
            end_node_id = self.link_end_nodes[link_id]
            if link_id in links_closed:
                self.jacobian[i,start_node_id] = 0.0
                self.jacobian[i,end_node_id] = 0.0
                self.jacobian[i,i] = 1.0
            elif link_id in self._pipe_ids:
                self.jacobian[i,start_node_id] = -1.0
                self.jacobian[i,end_node_id] = 1.0
            elif link_id in self._pump_ids:
                if link_id in self.head_curve_coefficients.keys():
                    self.jacobian[i,start_node_id] = 1.0
                    self.jacobian[i,end_node_id] = -1.0
            elif link_id in self._valve_ids:
                if link_id in self._prv_ids:
                    if type(valve_settings[link_id]) == float: # Active
                        self.jacobian[i,start_node_id] = 0.0
                        self.jacobian[i,end_node_id] = 1.0
                        self.jacobian[i,i] = 0.0
                    elif valve_settings[link_id] == 'OPEN':
                        self.jacobian[i,start_node_id] = -1.0
                        self.jacobian[i,end_node_id] = 1.0
                    elif valve_settings[link_id] == 'CLOSED':
                        self.jacobian[i,start_node_id] = 0.0
                        self.jacobian[i,end_node_id] = 0.0
                        self.jacobian[i,i] = 1.0
                


    def get_jacobian(self, x, links_closed, valve_settings):
        for i in xrange(self.num_nodes*2, self.num_nodes*2+self.num_links): # Equations/rows
            link_id = i - 2*self.num_nodes
            if link_id in links_closed:
                pass
            elif link_id in self._pipe_ids:
                flow = x[i]
                pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                if flow < -self.hw_q2:
                    self.jacobian[i,i] = -1.852*pipe_resistance_coeff*abs(flow)**0.852
                elif flow <= -self.hw_q1:
                    self.jacobian[i,i] = -pipe_resistance_coeff*(3.0*self.hw_a*abs(flow)**2 + 2*self.hw_b*abs(flow) + self.hw_c)
                elif flow <= 0.0:
                    self.jacobian[i,i] = -pipe_resistance_coeff*self.hw_m
                elif flow < self.hw_q1:
                    self.jacobian[i,i] = pipe_resistance_coeff*self.hw_m
                elif flow <= self.hw_q2:
                    self.jacobian[i,i] = pipe_resistance_coeff*(3.0*self.hw_a*flow**2 + 2*self.hw_b*flow + self.hw_c)
                else:
                    self.jacobian[i,i] = 1.852*pipe_resistance_coeff*flow**0.852
            elif link_id in self._pump_ids:
                flow = x[i]
                if link_id in self.head_curve_coefficients.keys():
                    head_curve_tuple = self.head_curve_coefficients[link_id]
                    B = head_curve_tuple[1]
                    C = head_curve_tuple[2]
                    self.jacobian[i,i] = -B*C*abs(flow)**(C-1.0)
                elif link_id in self.pump_powers.keys():
                    start_node_id = self.link_start_nodes[link_id]
                    end_node_id = self.link_end_nodes[link_id]
                    self.jacobian[i,start_node_id] = 1000.0*self._g*flow
                    self.jacobian[i,end_node_id] = -1000.0*self._g*flow
                    self.jacobian[i,i] = 1000.0*self._g*x[start_node_id] - 1000.0*self._g*x[end_node_id]
            elif link_id in self._valve_ids:
                if link_id in self._prv_ids:
                    if valve_settings[link_id] == 'OPEN':
                        flow = x[i]
                        pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                        self.jacobian[i,i] = 2.0*pipe_resistance_coeff*abs(flow)

        return self.jacobian    

    def get_node_balance_residual(self, x):
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

        demand = x[self.num_nodes:self.num_nodes*2]
        flow = x[self.num_nodes*2:]

        for node_id in xrange(self.num_nodes):
            expr = 0
            for l in self.out_link_ids_for_nodes[node_id]:
                expr -= flow[link_id]
            for l in self.in_link_ids_for_nodes[node_id]:
                expr += flow[link_id]
            self.node_balance_residual[node_id] = expr - demand[node_id]

    def get_headloss_residual(self, x, links_closed, valve_settings):

        head = x[:self.num_nodes]
        flow = x[self.num_nodes*2:]

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

    def get_demand_or_head_residual(self, x, expected_demands, tank_heads, reservoir_heads):

        head = x[:self.num_nodes]
        demand = x[self.num_nodes:self.num_nodes*2]

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
            

    def _initialize_flow(self, net_status):
        for link_name in net_status.links_closed:
            self.flow0[self._link_name_to_id[link_name]] = 0.0

    def _initialize_head(self, net_status):
        for node_id in self._junction_ids:
            self.head0[node_id] = self.node_elevations[node_id]
        for tank_name in net_status.tank_heads.keys():
            tank_id = self._node_name_to_id[tank_name]
            self.head0[tank_id] = net_status.tank_heads[tank_name]
        for reservoir_name in net_status.reservoir_heads.keys():
            reservoir_id = self._node_name_to_id[reservoir_name]
            self.head0[reservoir_id] = net_status.reservoir_heads[reservoir_name]

    def _initialize_demand(self, net_status):
        for junction_name in net_status.expected_demands.keys():
            junction_id = self._node_name_to_id[junction_name]
            self.demand0[junction_id] = net_status.expected_demands[junction_name]
            
