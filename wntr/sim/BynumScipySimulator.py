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
        #    2.) Headloss residuals
        #    3.) Demand/head residuals
        self.node_balance_residual = np.ones(self.num_nodes)
        self.headloss_residual = np.ones(self.num_links)
        self.demand_or_head_residual = np.ones(self.num_nodes)

        # Set miscelaneous link and node attributes
        self._set_node_attributes()
        self._set_link_attributes()

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
                self.junction_ids.append(n)
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


    def run_eps(self):
        """
        Method to run an extended period simulation
        """
        # Create NetworkStatus object
        net_status = NetworkStatus(self._wn)
        self.solver = NewtonSolver()

        # Initialize X
        # Vars will be ordered:
        #    1.) flow
        #    2.) head
        #    3.) demand
        self.flow0 = np.zeros(self.num_links)
        self.head0 = np.zeros(self.num_nodes)
        self.demand0 = np.zeros(self.num_nodes)
        self._initialize_flow(net_status)
        self._initialize_head(net_status)
        self._initialize_demand(net_status)
        self._X_init = np.concatenate((self.flow0, self.head0, self.demand0))

        


    def solve_hydraulics(self, net_status):
        """
        Method to solve the hydraulic equations given the network status

        Parameters
        ----------
        net_status: a NetworkStatus object
        """


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
            
