from wntr import *
import pandas as pd
import numpy as np
import scipy.sparse as sparse
import math
from wntr.network.WaterNetworkModel import *
import copy
import warnings
import logging

logger = logging.getLogger('wntr.sim.HydraulicModel')

class HydraulicModel(object):
    def __init__(self, wn, pressure_driven=False):
        """
        Class to create hyrdaulic models.

        Parameters
        ----------
        wn : class
            water network model class
        pressure_driven : bool
            Determines if the network will be pressure driven or demand driven.
        """
        self._wn = wn
        self.pressure_driven = pressure_driven

        # Global constants
        self._initialize_global_constants()

        # Initialize dictionaries to map between node/link names and ids
        self._initialize_name_id_maps()

        # Number of nodes and links
        self.num_nodes = self._wn.num_nodes()
        self.num_links = self._wn.num_links()
        self.num_leaks = len(self._leak_ids)
        self.num_junctions = self._wn.num_junctions()
        self.num_tanks = self._wn.num_tanks()
        self.num_reservoirs = self._wn.num_reservoirs()
        self.num_pipes = self._wn.num_pipes()
        self.num_pumps = self._wn.num_pumps()
        self.num_valves = self._wn.num_valves()

        # Initialize residuals
        # Equations will be ordered:
        #    1.) Node mass balance residuals
        #    2.) Demand/head residuals
        #    3.) Headloss residuals
        self.node_balance_residual = np.ones(self.num_nodes)
        self.demand_or_head_residual = np.ones(self.num_nodes)
        self.headloss_residual = np.ones(self.num_links)
        self.leak_demand_residual = np.ones(self.num_leaks)

        # Set miscelaneous link and node attributes
        self._set_node_attributes()
        self._set_link_attributes()
        self._form_node_balance_matrix()
        self._form_link_headloss_matrix()

        # network input objects
        # these objects use node/link ids rather than names
        # self.prev_tank_head = {}
        self.tank_head = {}
        # self.prev_reservoir_head = {}
        self.reservoir_head = {}
        # self.prev_junction_demand = {}
        self.junction_demand = np.zeros(self.num_junctions)
        # self.prev_link_status = {}
        self.link_status = {}
        self.closed_links = set()
        # self.prev_valve_settings = {}
        self.valve_settings = {}
        # self.prev_pump_speeds = {}
        self.pump_speeds = {}

        self.isolated_junction_names = []
        self.isolated_junction_ids = []
        self.isolated_link_names = []
        self.isolated_link_ids = []

        # Initialize Jacobian
        self._set_jacobian_structure()

    def _initialize_global_constants(self):
        # Hazen-Williams resistance coefficient in SI units (it equals 4.727 in EPANET GPM units).
        # See Table 3.1 in EPANET 2 User manual.
        self._Hw_k = 10.666829500036352
        # Darcy-Weisbach constant in SI units (it equals 0.0252 in EPANET GPM units).
        # See Table 3.1 in EPANET 2 User manual.
        self._Dw_k = 0.0826
        self._g = 9.81  # Acceleration due to gravity

        # Constants for the modified hazen-williams formula
        # The names match the names used in the simulation white paper
        # self.hw_q1 = 0.00349347323944
        # self.hw_q2 = 0.00549347323944
        # self.hw_m = 0.01
        self.hw_q1 = 0.0002
        self.hw_q2 = 0.0004
        self.hw_m = 0.001
        x1 = self.hw_q1
        x2 = self.hw_q2
        f1 = self.hw_m*self.hw_q1
        f2 = self.hw_q2**1.852
        df1 = self.hw_m
        df2 = 1.852*self.hw_q2**0.852
        a, b, c, d = self.compute_polynomial_coefficients(x1, x2, f1, f2, df1, df2)
        self.hw_a = a
        self.hw_b = b
        self.hw_c = c
        self.hw_d = d

        # Constants for the modified pump curves
        self.pump_m = -0.00000000001
        self.pump_q1 = 0.0
        self.pump_q2 = 1.0e-8

        # constants for the modified pdd function
        # I have created plots of the PDD function with these
        # parameters, and they look pretty good. Additionally,
        # the smoothing is not very sensitive to Pmin or Pnom.
        self._pdd_smoothing_delta = 0.2
        self._slope_of_pdd_curve = 1e-11

    def _initialize_name_id_maps(self):
        # ids are intergers
        self._node_id_to_name = {}  # {id1: name1, id2: name2, etc.}
        self._node_name_to_id = {}  # {name1: id1, name2: id2, etc.}
        self._link_id_to_name = {}  # {id1: name1, id2: name2, etc.}
        self._link_name_to_id = {}  # {name1: id1, name2: id2, etc.}

        # Lists of types of nodes
        # self._node_ids is ordered by increasing id. In fact, the index equals the id.
        # The ordering of the other lists is not significant.
        # Each node has only one id. For example, if 'Tank-5' has id 8, then 8 will be used
        # for 'Tank-5' in self._node_ids and self._tank_ids.
        self._node_ids = []  # ordering is vital! Must be junctions then tanks then reservoirs
        self._junction_ids = []
        self._tank_ids = []
        self._reservoir_ids = []
        self._leak_ids = []
        # {node_id: index_of_node_in_leak_ids}; e.g. _leak_ids = [0, 4, 18], _leak_idx = {0:0, 4:1, 18:2}
        self._leak_idx = {}

        # Lists of types of links
        # self._link_ids is ordered by increasing id. In fact, the index equals the id.
        # The ordering of the other lists is not significant.
        # Each link has only one id. For example, if 'Pump-5' has id 8, then 8 will be used
        # for 'Pump-5' in self._link_ids and self._pump_ids.
        self._link_ids = []  # ordering is viatl! Must be pipes the pumps then valves
        self._pipe_ids = []
        self._pump_ids = []
        self.power_pump_ids = []
        self.head_pump_ids = []
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
        # Dictionary indicating whether or not the leak is active. False means inactive, True means active. 
        self.leak_status = {}
        # Dictionary indicating whether or not the node could have a leak; True if node._leak is True;
        # False if node._leak is False
        self.could_have_leak = {}

        n = 0
        for node_name, node in self._wn.nodes(Junction):
            self._node_id_to_name[n] = node_name
            self._node_name_to_id[node_name] = n
            self._node_ids.append(n)
            self._junction_ids.append(n)
            self.node_types.append(NodeTypes.junction)
            if node._leak:
                self._leak_idx[n] = len(self._leak_ids)
                self._leak_ids.append(n)
                self.leak_status[n] = False
                self.could_have_leak[n] = True
            else:
                self.leak_status[n] = False
                self.could_have_leak[n] = False
            n += 1

        for node_name, node in self._wn.nodes(Tank):
            self._node_id_to_name[n] = node_name
            self._node_name_to_id[node_name] = n
            self._node_ids.append(n)
            self._tank_ids.append(n)
            self.node_types.append(NodeTypes.tank)
            if node._leak:
                self._leak_idx[n] = len(self._leak_ids)
                self._leak_ids.append(n)
                self.leak_status[n] = False
                self.could_have_leak[n] = True
            else:
                self.leak_status[n] = False
                self.could_have_leak[n] = False
            n += 1

        for node_name, node in self._wn.nodes(Reservoir):
            self._node_id_to_name[n] = node_name
            self._node_name_to_id[node_name] = n
            self._node_ids.append(n)
            self._reservoir_ids.append(n)
            self.node_types.append(NodeTypes.reservoir)
            self.leak_status[n] = False
            self.could_have_leak[n] = False
            n += 1

        l = 0
        for link_name, link in self._wn.links(Pipe):
            self._link_id_to_name[l] = link_name
            self._link_name_to_id[link_name] = l
            self._link_ids.append(l)
            self._pipe_ids.append(l)
            self.link_types.append(LinkTypes.pipe)
            l += 1

        for link_name, link in self._wn.links(Pump):
            self._link_id_to_name[l] = link_name
            self._link_name_to_id[link_name] = l
            self._link_ids.append(l)
            self._pump_ids.append(l)
            self.link_types.append(LinkTypes.pump)
            if link.info_type == 'POWER':
                self.power_pump_ids.append(l)
            elif link.info_type == 'HEAD':
                self.head_pump_ids.append(l)
            else:
                raise RuntimeError('Pump type not recognized.')
            l += 1

        for link_name, link in self._wn.links(Valve):
            self._link_id_to_name[l] = link_name
            self._link_name_to_id[link_name] = l
            self._link_ids.append(l)
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
            l += 1

    def _set_node_attributes(self):
        self.out_link_ids_for_nodes = [[] for i in xrange(self.num_nodes)]
        self.in_link_ids_for_nodes = [[] for i in xrange(self.num_nodes)]
        self.node_elevations = np.zeros(self.num_nodes)
        self.nominal_pressures = np.ones(self.num_junctions)
        self.minimum_pressures = np.zeros(self.num_junctions)
        # {junction_id: (a,b,c,d)} where the ordering of the coefficients goes from the 3rd order term to 0th
        # order term; these are the coefficients for the polynomial between Pmin and the normal pdd function
        self.pdd_poly1_coeffs = {}
        # {junction_id: (a,b,c,d)} where the ordering of the coefficients goes from the 3rd order term to 0th
        # order term; these are the coefficients for the polynomial between the normal pdd function and Pmax
        self.pdd_poly2_coeffs = {}
        self.pdd_poly1_coeffs_a = np.zeros(self.num_junctions)
        self.pdd_poly1_coeffs_b = np.zeros(self.num_junctions)
        self.pdd_poly1_coeffs_c = np.zeros(self.num_junctions)
        self.pdd_poly1_coeffs_d = np.zeros(self.num_junctions)
        self.pdd_poly2_coeffs_a = np.zeros(self.num_junctions)
        self.pdd_poly2_coeffs_b = np.zeros(self.num_junctions)
        self.pdd_poly2_coeffs_c = np.zeros(self.num_junctions)
        self.pdd_poly2_coeffs_d = np.zeros(self.num_junctions)
        self.leak_Cd = {}  # {node_id: leak_discharge_coeff}
        self.leak_area = {}  # {node_id: leak_area}
        # {node_id: (a,b,c,d)} where the ordering of the coefficients goes from the 3rd order term to the 0th order term
        self.leak_poly_coeffs = {}

        for node_name, node in self._wn.nodes(wntr.network.Junction):
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
            self.node_elevations[node_id] = node.elevation
            self.nominal_pressures[node_id] = node.nominal_pressure
            self.minimum_pressures[node_id] = node.minimum_pressure
            self.get_pdd_poly1_coeffs(node, node_id)
            self.get_pdd_poly2_coeffs(node, node_id)
            if node._leak:
                self.leak_Cd[node_id] = node.leak_discharge_coeff
                self.leak_area[node_id] = node.leak_area
                self.get_leak_poly_coeffs(node, node_id)

        for node_name, node in self._wn.nodes(wntr.network.Tank):
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
            self.node_elevations[node_id] = node.elevation
            if node._leak:
                self.leak_Cd[node_id] = node.leak_discharge_coeff
                self.leak_area[node_id] = node.leak_area
                self.get_leak_poly_coeffs(node, node_id)

        for node_name, node in self._wn.nodes(wntr.network.Reservoir):
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
            self.node_elevations[node_id] = 0.0

    def _set_link_attributes(self):
        self.link_start_nodes = range(self.num_links)
        self.link_end_nodes = range(self.num_links)
        self.pipe_resistance_coefficients = np.zeros(self.num_links)
        self.pipe_diameters = {}
        self.head_curve_coefficients = {}
        self.max_pump_flows = {}
        self.pump_poly_coefficients = {}  # {pump_id: (a,b,c,d)} a*x**3 + b*x**2 + c*x + d
        self.pump_line_params = {} # {pump_id: (q_bar, h_bar)} h = pump_m*(q-q_bar)+h_bar
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
                self.pipe_resistance_coefficients[link_id] = (self._Hw_k*(link.roughness**(-1.852)) *
                                                              (link.diameter**(-4.871))*link.length)  # Hazen-Williams
                self.pipe_diameters[link_id] = link.diameter
            elif link_id in self._valve_ids:
                self.pipe_resistance_coefficients[link_id] = self._Dw_k*0.02*link.diameter**(-5)*link.diameter*2
            else:
                self.pipe_resistance_coefficients[link_id] = 0
            if link_id in self._pump_ids:
                if link.info_type == 'HEAD':
                    A, B, C = link.get_head_curve_coefficients()
                    self.head_curve_coefficients[link_id] = (A, B, C)
                    self.max_pump_flows[link_id] = (A/B)**(1.0/C)
                    if C <= 1:
                        a, b, c, d = self.get_pump_poly_coefficients(A, B, C)
                        self.pump_poly_coefficients[link_id] = (a, b, c, d)
                    else:
                        q_bar, h_bar = self.get_pump_line_params(A, B, C)
                        self.pump_line_params[link_id] = (q_bar, h_bar)
                elif link.info_type == 'POWER':
                    self.pump_powers[link_id] = link.power
                    self.max_pump_flows[link_id] = None

    def _form_node_balance_matrix(self):
        # The node balance matrix should never be modified! It is also used in the jacobian!
        values = []
        rows = []
        cols = []
        for node_id in self._node_ids:
            for out_link_id in self.out_link_ids_for_nodes[node_id]:
                values.append(-1.0)
                rows.append(node_id)
                cols.append(out_link_id)
            for in_link_id in self.in_link_ids_for_nodes[node_id]:
                values.append(1.0)
                rows.append(node_id)
                cols.append(in_link_id)
        self.node_balance_matrix = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_nodes, self.num_links))

    def _form_link_headloss_matrix(self):
        headloss_matrix = np.matrix(np.zeros((self.num_links, self.num_nodes)))
        for link_id in self._link_ids:
            headloss_matrix[link_id, self.link_start_nodes[link_id]] = 1.0
            headloss_matrix[link_id, self.link_end_nodes[link_id]] = -1.0
        self.link_headloss_matrix = sparse.coo_matrix(headloss_matrix)

    def _set_jacobian_structure(self):
        """
        Create the jacobian as a scipy.sparse.csr_matrix
        Initialize all jacobian entries that have the possibility to be non-zero

        Structure of jacobian:

        H_n => Head for node id n
        D_n => Demand for node id n
        F_l => Flow for link id l
        node_bal_n => node balance for node id n
        D/H_n      => demand/head equation for node id n
        headloss_l => headloss equation for link id l
        in link refers to a link that has node_n as an end node
        out link refers to a link that has node_n as a start node

        Note that there will only be leak variables and equations for nodes with leaks. Thus some of the rows and columns below may be missing. The leak id is equal to the node id though.

        Variable          H_1   H_2   H_n   H_(N-1)   H_N   D_1   D_2   D_n   D_(N-1)   D_N   F_1   F_2   F_l   F_(L-1)   F_L      Dleak1  Dleak2  Dleakn  Dleak(N-1)  DleakN
        Equation
        node_bal_1         0     0     0     0         0     -1    0     0     0         0    (1 for in link, -1 for out link)       -1      0        0        0          0
        node_bal_2         0     0     0     0         0     0     -1    0     0         0    (1 for in link, -1 for out link)        0     -1        0        0          0
        node_bal_n         0     0     0     0         0     0     0     -1    0         0    (1 for in link, -1 for out link)        0      0       -1        0          0
        node_bal_(N-1)     0     0     0     0         0     0     0     0     -1        0    (1 for in link, -1 for out link)        0      0        0       -1          0
        node_bal_N         0     0     0     0         0     0     0     0     0         -1   (1 for in link, -1 for out link)        0      0        0        0         -1
        D/H_1              *1    0     0     0         0     *2    0     0     0         0     0      0     0    0         0          0      0        0        0          0
        D/H_2              0     *1    0     0         0     0     *2    0     0         0     0      0     0    0         0          0      0        0        0          0
        D/H_n              0     0     *1    0         0     0     0     *2    0         0     0      0     0    0         0          0      0        0        0          0
        D/H_(N-1)          0     0     0     *1        0     0     0     0     *2        0     0      0     0    0         0          0      0        0        0          0
        D/H_N              0     0     0     0         *1    0     0     0     0         *2    0      0     0    0         0          0      0        0        0          0
        headloss_1         (NZ for start/end node *3    )    0     0     0     0         0     *4     0     0    0         0          0      0        0        0          0
        headloss_2         (NZ for start/end node *3    )    0     0     0     0         0     0      *4    0    0         0          0      0        0        0          0
        headloss_l         (NZ for start/end node *3    )    0     0     0     0         0     0      0     *4   0         0          0      0        0        0          0
        headloss_(L-1)     (NZ for start/end node *3    )    0     0     0     0         0     0      0     0    *4        0          0      0        0        0          0
        headloss_L         (NZ for start/end node *3    )    0     0     0     0         0     0      0     0    0         *4         0      0        0        0          0
        leak flow 1        *5    0     0     0         0     0     0     0     0         0     0      0     0    0         0          1      0        0        0          0
        leak flow 2        0     *5    0     0         0     0     0     0     0         0     0      0     0    0         0          0      1        0        0          0
        leak flow n        0     0     *5    0         0     0     0     0     0         0     0      0     0    0         0          0      0        1        0          0
        leak flow N-1      0     0     0     *5        0     0     0     0     0         0     0      0     0    0         0          0      0        0        1          0
        leak flow N        0     0     0     0         *5    0     0     0     0         0     0      0     0    0         0          0      0        0        0          1


        *1: 1 for tanks and reservoirs
            1 for isolated junctions
            0 for junctions if the simulation is demand-driven and the junction is not isolated
            f(H) for junctions if the simulation is pressure-driven and the junction is not isolated
        *2: 0 for tanks and reservoirs
            1 for non-isolated junctions
            0 for isolated junctions
        *3: 0 for closed/isolated links
                         pipes   head_pumps  power_pumps  active_PRV   open_prv
            start node    -1        1            f(F)        0             -1
            end node       1       -1            f(F)        1              1
        *4: 1 for closed/isolated links
            f(F) for pipes
            f(F) for head pumps
            f(Hstart,Hend) for power pumps
            0 for active PRVs
            f(F) for open PRVs
        *5: 0 for inactive leaks
            0 for leaks at isolated junctions
            f(H-z) otherwise
        """

        big_jac_values = np.array([])
        big_jac_rows = np.array([])
        big_jac_cols = np.array([])

        values = -1.0*np.ones(self.num_nodes)
        rows = range(self.num_nodes)
        cols = range(self.num_nodes)
        self.jac_A = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_nodes, self.num_nodes))
        big_jac_values = np.concatenate((big_jac_values, self.jac_A.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_A.row))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_A.col+self.num_nodes))

        # This object is used for things other than the jacobian; Don't modify it!
        self.jac_B = self.node_balance_matrix
        big_jac_values = np.concatenate((big_jac_values, self.jac_B.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_B.row))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_B.col+2*self.num_nodes))

        values = -1.0*np.ones(self.num_leaks)
        rows = list(self._leak_ids)
        cols = range(self.num_leaks)
        self.jac_C = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_nodes, self.num_leaks))
        big_jac_values = np.concatenate((big_jac_values, self.jac_C.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_C.row))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_C.col+(2*self.num_nodes+self.num_links)))

        values = [0.0 for i in self._junction_ids]+[1.0 for i in self._tank_ids]+[1.0 for i in self._reservoir_ids]
        rows = range(self.num_nodes)
        cols = range(self.num_nodes)
        self.jac_D = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_nodes, self.num_nodes))
        big_jac_values = np.concatenate((big_jac_values, self.jac_D.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_D.row+self.num_nodes))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_D.col))

        values = [1.0 for i in self._junction_ids]+[0.0 for i in self._tank_ids]+[0.0 for i in self._reservoir_ids]
        rows = range(self.num_nodes)
        cols = range(self.num_nodes)
        self.jac_E = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_nodes, self.num_nodes))
        big_jac_values = np.concatenate((big_jac_values, self.jac_E.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_E.row+self.num_nodes))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_E.col+self.num_nodes))

        # jac_F will be a coo_matrix for easy updating.
        # Note that it might need to be converted to csr before doing arithmetic
        values = []
        rows = []
        cols = []
        for link_id in self._pipe_ids:
            values.append(-1.0)
            rows.append(link_id)
            cols.append(self.link_start_nodes[link_id])
        for link_id in self._pump_ids:
            values.append(1.0)
            rows.append(link_id)
            cols.append(self.link_start_nodes[link_id])
        for link_id in self._valve_ids:
            values.append(-1.0)
            rows.append(link_id)
            cols.append(self.link_start_nodes[link_id])
        for link_id in self._pipe_ids:
            values.append(1.0)
            rows.append(link_id)
            cols.append(self.link_end_nodes[link_id])
        for link_id in self._pump_ids:
            values.append(-1.0)
            rows.append(link_id)
            cols.append(self.link_end_nodes[link_id])
        for link_id in self._valve_ids:
            values.append(1.0)
            rows.append(link_id)
            cols.append(self.link_end_nodes[link_id])
        self.jac_F = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_links, self.num_nodes))
        self.standard_jac_F_data = np.array(values)
        big_jac_values = np.concatenate((big_jac_values, self.jac_F.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_F.row+(2*self.num_nodes)))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_F.col))

        values = np.ones(self.num_links)
        rows = range(self.num_links)
        cols = range(self.num_links)
        self.jac_G = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_links, self.num_links))
        big_jac_values = np.concatenate((big_jac_values, self.jac_G.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_G.row+(2*self.num_nodes)))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_G.col+(2*self.num_nodes)))

        values = np.zeros(self.num_leaks)
        rows = range(self.num_leaks)
        cols = list(self._leak_ids)
        self.jac_H = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_leaks, self.num_nodes))
        big_jac_values = np.concatenate((big_jac_values, self.jac_H.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_H.row+(2*self.num_nodes+self.num_links)))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_H.col))

        values = np.ones(self.num_leaks)
        rows = range(self.num_leaks)
        cols = range(self.num_leaks)
        self.jac_I = sparse.coo_matrix((values, (rows, cols)), shape=(self.num_leaks, self.num_leaks))
        big_jac_values = np.concatenate((big_jac_values, self.jac_I.data))
        big_jac_rows = np.concatenate((big_jac_rows, self.jac_I.row+(2*self.num_nodes+self.num_links)))
        big_jac_cols = np.concatenate((big_jac_cols, self.jac_I.col+(2*self.num_nodes+self.num_links)))

        self.jacobian_values = big_jac_values
        self.jacobian_rows = big_jac_rows
        self.jacobian_cols = big_jac_cols
        self.jacobian_shape = (2*self.num_nodes+self.num_links+self.num_leaks, 2*self.num_nodes+self.num_links+self.num_leaks)
        self.jacobian = sparse.coo_matrix((self.jacobian_values, (self.jacobian_rows, self.jacobian_cols)),
                                          shape=self.jacobian_shape)

        # self.jac_AinvB = self.jac_A*self.jac_B
        # self.jac_AinvC = self.jac_A*self.jac_C

    def get_hydraulic_equations(self, x):
        """
        Parameters
        ----------
        x : numpy array
            values of heads, demands, flows, and leak flowrates
        Returns
        -------
        residuals: numpy array
            Returns residuals for hyrdaulic equations.
        """
        head = x[:self.num_nodes]
        demand = x[self.num_nodes:self.num_nodes*2]
        flow = x[self.num_nodes*2:(2*self.num_nodes+self.num_links)]
        leak_demand = x[(2*self.num_nodes+self.num_links):]
        self.get_node_balance_residual(flow, demand, leak_demand)
        self.get_demand_or_head_residual(head, demand)
        self.get_headloss_residual(head, flow)
        self.get_leak_demand_residual(head, leak_demand)

        all_residuals = np.concatenate((self.node_balance_residual, self.demand_or_head_residual,
                                        self.headloss_residual, self.leak_demand_residual))

        return all_residuals

    def set_jacobian_constants(self):
        """
        set the jacobian entries that depend on the network status
        but do not depend on the value of any variable.

        ordering is very important here
        the csr_matrix data is stored by going though all columns of the first row,
        then all columns of the second row, etc
        ex:
        row = [0,1,2,0,1,2,0,1,2]
        col = [0,0,0,1,1,1,2,2,2]
        value = [0,1,2,3,4,5,6,7,8]
        A = sparse.csr_matrix((value,(row,col)),shape=(3,3))

        then A=>
                 0   3  6
                 1   4  7
                 2   5  8
        and A.data =>
                     [0, 3, 6, 1, 4, 7, 2, 5, 8]
        """

        if not self.pressure_driven:
            self.jac_D.data[:self.num_junctions] = self.isolated_junction_array

        self.jac_E.data[:self.num_junctions] = 1.0-self.isolated_junction_array

        self.jac_F.data[:self.num_links] = ((1.0-self.isolated_link_array)*self.closed_link_array *
                                            self.standard_jac_F_data[:self.num_links])
        self.jac_F.data[self.num_links:] = ((1.0-self.isolated_link_array)*self.closed_link_array *
                                            self.standard_jac_F_data[self.num_links:])
        for link_id in self._prv_ids:
            if self.link_status[link_id] == LinkStatus.active:
                self.jac_F.data[link_id] = 0

        # self.jac_G.data = (self.isolated_link_array + (1.0 - self.closed_link_array) -
        #                        self.isolated_link_array * (1.0 - self.closed_link_array))

    def get_jacobian(self, x):
        """
        Parameters
        ----------
        x : numpy array
            values of heads, demands, flows, and leak flowrates
        Returns
        -------
        jacobian: scipy.sparse.coo_matrix
            Returns the jacobian headloss equations.
        """

        heads = x[:self.num_nodes]
        flows = x[self.num_nodes*2:2*self.num_nodes+self.num_links]

        if self.pressure_driven:
            minP = self.minimum_pressures
            nomP = self.nominal_pressures
            j_d = self.junction_demand
            m = self._slope_of_pdd_curve
            delta = self._pdd_smoothing_delta
            n_j = self.num_junctions
            P = heads[:n_j]-self.node_elevations[:n_j]
            self.jac_D.data[:n_j] = self.isolated_junction_array + \
                                    (1.0-self.isolated_junction_array)*(
                                        ((P <= minP)+(P > nomP))*(-m)*j_d*heads[:n_j] +
                                        ((P > minP)*(P <= (minP+delta)))*(-j_d)*(
                                            3.0*self.pdd_poly1_coeffs_a*P**2 +
                                            2.0*self.pdd_poly1_coeffs_b*P +
                                            self.pdd_poly1_coeffs_c
                                        ) +
                                        (P > (nomP-delta))*(P <= nomP)*(-j_d)*(
                                            3.0*self.pdd_poly2_coeffs_a*P**2 +
                                            2.0*self.pdd_poly2_coeffs_b*P +
                                            self.pdd_poly2_coeffs_c
                                        )
                                    )
            # for the last segment, assignment is required because 0*np.nan does not equal 0 (same with np.inf)
            last_segment = (-0.5)*j_d/(nomP-minP)*((P-minP)/(nomP-minP))**(-0.5)
            last_segment[np.bitwise_not((P > (minP+delta))*(P <= (nomP-delta)))] = 0.0
            self.jac_D.data[:n_j] = self.jac_D.data[:n_j] + last_segment*(1-self.isolated_junction_array)

        for link_id in self.power_pump_ids:
            self.jac_F.data[link_id] = 1000.0*self._g*flows[link_id]
            self.jac_F.data[self.num_links+link_id] = -1000.0*self._g*flows[link_id]

        pf = abs(flows[:self.num_pipes])
        coeff = self.pipe_resistance_coefficients[:self.num_pipes]
        self.jac_G.data[:self.num_pipes] = ((self.isolated_link_array[:self.num_pipes] +
                                            (1.0 - self.closed_link_array[:self.num_pipes]) -
                                            (self.isolated_link_array[:self.num_pipes] *
                                             (1.0 - self.closed_link_array[:self.num_pipes])
                                             )
                                             ) +
                                            (1.0-self.isolated_link_array[:self.num_pipes])*
                                            self.closed_link_array[:self.num_pipes]*(
                                                (pf > self.hw_q2)*1.852*coeff*pf**0.852 +
                                                (pf <= self.hw_q2)*(pf >= self.hw_q1)*coeff*(
                                                    3.0*self.hw_a*pf**2 + 2.0*self.hw_b*pf + self.hw_c
                                                ) +
                                                (pf < self.hw_q1)*coeff*self.hw_m
                                            )
                                            )

        for link_id in self.head_pump_ids:
            if self.isolated_link_array[link_id] == 1 or self.closed_link_array[link_id] == 0:
                self.jac_G.data[link_id] = 1.0
            else:
                A,B,C = self.head_curve_coefficients[link_id]
                if C > 1:
                    q_bar, h_bar = self.pump_line_params[link_id]
                    if flows[link_id] >= q_bar:
                        self.jac_G.data[link_id] = (-B * C * flows[link_id] ** (C - 1.0))
                    else:
                        self.jac_G.data[link_id] = self.pump_m
                else:
                    if flows[link_id] <= self.pump_q1:
                        self.jac_G.data[link_id] = self.pump_m
                    elif flows[link_id] <= self.pump_q2:
                        a,b,c,d = self.pump_poly_coefficients[link_id]
                        self.jac_G.data[link_id] = (3.0 * a * flows[link_id] ** 2 + 2.0 * b * flows[link_id] + c)
                    else:
                        self.jac_G.data[link_id] = (-B * C * flows[link_id] ** (C - 1.0))
                # self.jac_G_inv.data[link_id] = 1.0 / self.jac_G_inv.data[link_id]
        for link_id in self.power_pump_ids:
            if self.isolated_link_array[link_id] == 1 or self.closed_link_array[link_id] == 0:
                self.jac_G.data[link_id] = 1.0
            else:
                start_node_id = self.link_start_nodes[link_id]
                end_node_id = self.link_end_nodes[link_id]
                self.jac_G.data[link_id] = (1000.0*self._g*heads[start_node_id] - 1000.0*self._g*heads[end_node_id])
                # self.jac_G_inv.data[link_id] = 1.0 / self.jac_G_inv.data[link_id]
        for link_id in self._prv_ids:
            if self.isolated_link_array[link_id] ==1 or self.closed_link_array[link_id] == 0:
                self.jac_G.data[link_id] = 1.0
            elif self.link_status[link_id] == LinkStatus.opened:
                self.jac_G.data[link_id] = 2.0*self.pipe_resistance_coefficients[link_id]*abs(flows[link_id])
                # self.jac_G_inv.data[link_id] = 1.0 / self.jac_G_inv.data[link_id]
            elif self.link_status[link_id] == LinkStatus.active:
                self.jac_G.data[link_id] = 0.0

        for ndx, node_id in enumerate(self._leak_ids):
            if not self.leak_status[node_id]:
                self.jac_H.data[ndx] = 0.0
            elif self.node_types[node_id] == NodeTypes.junction:
                if self.isolated_junction_array[node_id] == 1:
                    self.jac_H.data[ndx] = 0.0
                else:
                    m = 1.0e-11
                    P = heads[node_id] - self.node_elevations[node_id]
                    if P <= 0.0:
                        self.jac_H.data[ndx] = -m
                    elif P <= 1.0e-4:
                        a,b,c,d = self.leak_poly_coeffs[node_id]
                        self.jac_H.data[ndx] = -3.0*a*P**2 - 2.0*b*P - c
                    else:
                        self.jac_H.data[ndx] = -0.5*self.leak_Cd[node_id]*self.leak_area[node_id]*\
                                               math.sqrt(2.0*self._g)*P**(-0.5)
            else:
                m = 1.0e-11
                P = heads[node_id] - self.node_elevations[node_id]
                if P <= 0.0:
                    self.jac_H.data[ndx] = -m
                elif P <= 1.0e-4:
                    a,b,c,d = self.leak_poly_coeffs[node_id]
                    self.jac_H.data[ndx] = -3.0*a*P**2 - 2.0*b*P - c
                else:
                    self.jac_H.data[ndx] = -0.5*self.leak_Cd[node_id]*self.leak_area[node_id]*\
                                           math.sqrt(2.0*self._g)*P**(-0.5)

        self.jacobian_values = np.concatenate((self.jac_A.data,self.jac_B.data,self.jac_C.data,self.jac_D.data,
                                             self.jac_E.data,self.jac_F.data,self.jac_G.data,self.jac_H.data,
                                             self.jac_I.data))

        self.jacobian = sparse.coo_matrix((self.jacobian_values, (self.jacobian_rows, self.jacobian_cols)),
                                          shape=self.jacobian_shape)


        # return (self.jac_A, self.jac_B, self.jac_C, self.jac_D, self.jac_E, self.jac_F, self.jac_G_inv, self.jac_H,
        #         self.jac_I, self.jac_AinvB, self.jac_AinvC)
        # self.check_jac(x)
        return self.jacobian

    def get_node_balance_residual(self, flow, demand, leak_demand):
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

        self.node_balance_residual = self.node_balance_matrix*flow - demand
        for node_id in self._leak_ids:
            self.node_balance_residual[node_id] -= leak_demand[self._leak_idx[node_id]]

    def get_headloss_residual(self, head, flow):

        head_diff_vector = self.link_headloss_matrix*head

        def get_pipe_headloss_residual():

            n_p = self.num_pipes
            pf = flow[:n_p]
            abs_f = abs(pf)
            sign_coeff = np.sign(pf)*self.pipe_resistance_coefficients[:n_p]
            self.headloss_residual[:n_p] = (
                (
                    self.isolated_link_array[:n_p] + (1.0 - self.closed_link_array[:n_p]) -
                    self.isolated_link_array[:n_p] * (1.0 - self.closed_link_array[:n_p])
                ) * pf +
                (
                    (1.0 - self.isolated_link_array[:n_p]) * self.closed_link_array[:n_p]
                ) *
                (
                    (abs_f > self.hw_q2) * (sign_coeff * abs_f**1.852 - head_diff_vector[:n_p]) +
                    (abs_f <= self.hw_q2) * (abs_f >= self.hw_q1) * (sign_coeff *
                                                                     (self.hw_a*abs_f**3 + self.hw_b*abs_f**2 +
                                                                      self.hw_c*abs_f + self.hw_d) -
                                                                     head_diff_vector[:n_p]) +
                    (abs_f < self.hw_q1) * (sign_coeff * self.hw_m*abs_f - head_diff_vector[:n_p])
                )
            )

        get_pipe_headloss_residual()

        def get_pump_headloss_residual():
            for link_id in self._pump_ids:
                link_flow = flow[link_id]
                if self.link_status[link_id] == wntr.network.LinkStatus.closed or link_id in self.isolated_link_ids:
                    self.headloss_residual[link_id] = link_flow
                else:
                    start_node_id = self.link_start_nodes[link_id]
                    end_node_id = self.link_end_nodes[link_id]

                    if link_id in self.head_curve_coefficients.keys():
                        A,B,C = self.head_curve_coefficients[link_id]
                        if C > 1:
                            q_bar, h_bar = self.pump_line_params[link_id]
                            if link_flow >= q_bar:
                                pump_headgain = A - B*link_flow**C
                            else:
                                pump_headgain = self.pump_m*(link_flow - q_bar) + h_bar
                        else:
                            if link_flow <= self.pump_q1:
                                pump_headgain = self.pump_m*link_flow + A
                            elif link_flow <= self.pump_q2:
                                a, b, c, d = self.pump_poly_coefficients[link_id]
                                pump_headgain = a*link_flow**3 + b*link_flow**2 + c*link_flow + d
                            else:
                                pump_headgain = A - B*link_flow**C
                        self.headloss_residual[link_id] = pump_headgain - (head[end_node_id] - head[start_node_id])
                    elif link_id in self.pump_powers.keys():
                        self.headloss_residual[link_id] = self.pump_powers[link_id] + (head_diff_vector[link_id])*flow[link_id]*self._g*1000.0
                    else:
                        raise RuntimeError('Only power and head pumps are currently supported.')
        get_pump_headloss_residual()

        def get_valve_headloss_residual():
            for link_id in self._prv_ids:
                link_flow = flow[link_id]
                start_node_id = self.link_start_nodes[link_id]
                end_node_id = self.link_end_nodes[link_id]

                if self.link_status[link_id] == wntr.network.LinkStatus.closed or link_id in self.isolated_link_ids:
                    self.headloss_residual[link_id] = link_flow
                elif self.link_status[link_id] == LinkStatus.active:
                    self.headloss_residual[link_id] = head[end_node_id] - (self.valve_settings[link_id]+self.node_elevations[end_node_id])
                elif self.link_status[link_id] == LinkStatus.opened:
                    pipe_resistance_coeff = self.pipe_resistance_coefficients[link_id]
                    pipe_headloss = pipe_resistance_coeff*abs(flow[link_id])**2
                    self.headloss_residual[link_id] = pipe_headloss - (head_diff_vector[link_id])
        get_valve_headloss_residual()
        # print self.headloss_residual
        # raise RuntimeError('just stopping')

    def get_demand_or_head_residual(self, head, demand):

        if self.pressure_driven:
            minP = self.minimum_pressures
            nomP = self.nominal_pressures
            j_d = self.junction_demand
            m = self._slope_of_pdd_curve
            delta = self._pdd_smoothing_delta
            n_j = self.num_junctions
            P = head[:n_j] - self.node_elevations[:n_j]
            H = head[:n_j]
            Dact = demand[:n_j]

            self.demand_or_head_residual[:n_j] = (
                self.isolated_junction_array * H + (1.0 - self.isolated_junction_array)*(
                    (P <= minP) * (Dact - j_d*m*(P-minP)) +
                    (P > minP) * (P <= (minP + delta)) * (
                        Dact - j_d*(
                            self.pdd_poly1_coeffs_a*P**3 +
                            self.pdd_poly1_coeffs_b*P**2 +
                            self.pdd_poly1_coeffs_c*P +
                            self.pdd_poly1_coeffs_d
                        )
                    ) +
                    (P > (nomP - delta)) * (P <= nomP) * (
                        Dact - j_d*(
                            self.pdd_poly2_coeffs_a*P**3 +
                            self.pdd_poly2_coeffs_b*P**2 +
                            self.pdd_poly2_coeffs_c*P +
                            self.pdd_poly2_coeffs_d
                        )
                    ) +
                    (P > nomP) * (Dact - j_d * (m*(P-nomP) + 1.0))
                )
            )
            # for the last segment, assignment is required because 0*np.nan does not equal 0 (same with np.inf)
            last_segment = (Dact - j_d*((P-minP)/(nomP-minP))**0.5)
            last_segment[np.bitwise_not((P > (minP + delta))*(P <= (nomP - delta)))] = 0.0
            self.demand_or_head_residual[:n_j] = (self.demand_or_head_residual[:n_j] +
                                                  last_segment*(1.0-self.isolated_junction_array))
        else:
            self.demand_or_head_residual[:self.num_junctions] = (
                self.isolated_junction_array * head[:self.num_junctions] +
                (1.0 - self.isolated_junction_array) * (demand[:self.num_junctions] - self.junction_demand)
            )
        for node_id in self._tank_ids:
            self.demand_or_head_residual[node_id] = head[node_id] - self.tank_head[node_id]
        for node_id in self._reservoir_ids:
            self.demand_or_head_residual[node_id] = head[node_id] - self.reservoir_head[node_id]

    def get_leak_demand_residual(self, head, leak_demand):
        m = 1.0e-11
        for node_id in self._leak_ids:
            leak_idx = self._leak_idx[node_id]
            if self.leak_status[node_id] and node_id not in self.isolated_junction_ids:
                p = head[node_id] - self.node_elevations[node_id]
                if p <= 0:
                    self.leak_demand_residual[leak_idx] = leak_demand[leak_idx] - m*p
                elif p <= 1.0e-4:
                    a,b,c,d = self.leak_poly_coeffs[node_id]
                    self.leak_demand_residual[leak_idx] = leak_demand[leak_idx] - (a*p**3+b*p**2+c*p+d)
                else:
                    self.leak_demand_residual[leak_idx] = leak_demand[leak_idx] - self.leak_Cd[node_id]*self.leak_area[node_id]*math.sqrt(2.0*self._g*p)
            else:
                self.leak_demand_residual[leak_idx] = leak_demand[leak_idx]

    def correct_step(self,d_head,d_demand,d_flow,d_leak,x):
        heads = x[:self.num_nodes]
        demands = x[self.num_nodes:2*self.num_nodes]
        flows = x[2*self.num_nodes:2*self.num_nodes+self.num_links]
        leaks = x[2*self.num_nodes+self.num_links:]

        for link_id in self._prv_ids:
            end_node_id = self.link_end_nodes[link_id]
            in_links = self.in_link_ids_for_nodes[end_node_id]
            out_links = self.out_link_ids_for_nodes[end_node_id]
            d_head[end_node_id] = self.valve_settings[link_id]+self.node_elevations[end_node_id] - heads[end_node_id]
            if link_id in in_links:
                d_flow[link_id] = demands[end_node_id] + sum(flows[out_link_id] for out_link_id in out_links) - \
                                  sum(flows[in_link_id] for in_link_id in in_links if in_link_id!=link_id) - \
                                  flows[link_id]
            else:
                d_flow[link_id] = sum(flows[in_link_id] for in_link_id in in_links) - demands[end_node_id] - \
                                  sum(flows[out_link_id] for out_link_id in out_links if out_link_id!=link_id) - \
                                  flows[link_id]
            if end_node_id in self._leak_ids:
                raise RuntimeError('Leaks at the end nodes of PRVs is not allowed.')
                # d_flow[link_id] += leaks[end_node_id]
        for node_id in self._tank_ids:
            in_links = self.in_link_ids_for_nodes[node_id]
            out_links = self.out_link_ids_for_nodes[node_id]
            d_demand[node_id] = sum(flows[in_link_id] for in_link_id in in_links) - \
                                sum(flows[out_link_id] for out_link_id in out_links) - demands[node_id]
            if node_id in self._leak_ids:
                d_demand[node_id] -= leaks[self._leak_idx[node_id]]
        for node_id in self._reservoir_ids:
            in_links = self.in_link_ids_for_nodes[node_id]
            out_links = self.out_link_ids_for_nodes[node_id]
            d_demand[node_id] = sum(flows[in_link_id] for in_link_id in in_links) - \
                                sum(flows[out_link_id] for out_link_id in out_links) - demands[node_id]
        d_demand[:self.num_junctions] = d_demand[:self.num_junctions] - \
                                        self.isolated_junction_array*demands[:self.num_junctions]
        return d_head,d_demand,d_flow,d_leak

    def initialize_flow(self):
        flow = 0.001*np.ones(self.num_links)
        for name, link in self._wn.links():
            if link.flow is None:
                continue
            else:
                link_id = self._link_name_to_id[name]
                flow[link_id] = link.flow
        return flow

    def initialize_head(self):
        head = np.zeros(self.num_nodes)
        for name, node in self._wn.nodes(Junction):
            node_id = self._node_name_to_id[name]
            if node.head is None:
                head[node_id] = self.node_elevations[node_id]
            else:
                head[node_id] = node.head
        for name, node in self._wn.nodes(Tank):
            node_id = self._node_name_to_id[name]
            head[node_id] = node.head
        for name, node in self._wn.nodes(Reservoir):
            node_id = self._node_name_to_id[name]
            head[node_id] = node.head
        return head

    def initialize_demand(self):
        demand = np.zeros(self.num_nodes)
        for name, node in self._wn.nodes(Junction):
            node_id = self._node_name_to_id[name]
            if node.demand is None:
                demand[node_id] = self.junction_demand[node_id]
            else:
                demand[node_id] = node.demand
        for name, node in self._wn.nodes(Tank):
            if node.demand is None:
                continue
            else:
                node_id = self._node_name_to_id[name]
                demand[node_id] = node.demand
        for name, node in self._wn.nodes(Reservoir):
            if node.demand is None:
                continue
            else:
                node_id = self._node_name_to_id[name]
                demand[node_id] = node.demand
        return demand

    def initialize_leak_demand(self):
        leak_demand = np.zeros(self.num_leaks)
        for node_id in self._leak_ids:
            name = self._node_id_to_name[node_id]
            node = self._wn.get_node(name)
            if node.leak_demand is None:
                continue
            else:
                leak_demand[self._leak_idx[node_id]] = node.leak_demand
        return leak_demand

    def update_initializations(self, x):
        #head = x[:self.num_nodes]
        #demand = x[self.num_nodes:self.num_nodes*2]
        #flow = x[self.num_nodes*2:(2*self.num_nodes+self.num_links)]
        #leak_demand = x[(2*self.num_nodes+self.num_links):]

        for junction_id in self.isolated_junction_ids:
            x[junction_id] = 0.0 # head = 0
            x[self.num_nodes+junction_id] = 0.0 # demand = 0
        for link_id in self._pipe_ids:
            if self.link_status[link_id]==wntr.network.LinkStatus.closed or link_id in self.isolated_link_ids:
                x[2*self.num_nodes+link_id] = 0.0 # flow = 0
        for link_id in self._pump_ids:
            if self.link_status[link_id]==wntr.network.LinkStatus.closed or link_id in self.isolated_link_ids:
                x[2*self.num_nodes+link_id] = 0.0 # flow = 0
        for link_id in self._valve_ids:
            if self.link_status[link_id]==wntr.network.LinkStatus.closed or link_id in self.isolated_link_ids:
                x[2*self.num_nodes+link_id] = 0.0 # flow = 0
        for node_id in self._leak_ids:
            if node_id in self.isolated_junction_ids or self.leak_status[node_id]==False:
                leak_idx = self._leak_idx[node_id]
                x[2*self.num_nodes+self.num_links+leak_idx] = 0.0
        return x

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
        self._sim_results['leak_demand'] = []
        self._sim_results['link_name'] = []
        self._sim_results['link_type'] = []
        self._sim_results['link_times'] = []
        self._sim_results['link_flowrate'] = []
        self._sim_results['link_velocity'] = []
        self._sim_results['link_status'] = []

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
            self._sim_results['node_expected_demand'].append(self.junction_demand[node_id])
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
            self._sim_results['node_expected_demand'].append(demand_n)
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
            self._sim_results['node_expected_demand'].append(demand_n)
            self._sim_results['node_pressure'].append(0.0)
            self._sim_results['leak_demand'].append(0.0)

        for link_id in self._pipe_ids:
            self._sim_results['link_type'].append(LinkTypes.link_type_to_str(self.link_types[link_id]))
            self._sim_results['link_flowrate'].append(flow[link_id])
            self._sim_results['link_velocity'].append(abs(flow[link_id])*4.0/(math.pi*self.pipe_diameters[link_id]**2.0))
            self._sim_results['link_status'].append(self.link_status[link_id])
        for link_id in self._pump_ids:
            self._sim_results['link_type'].append(LinkTypes.link_type_to_str(self.link_types[link_id]))
            self._sim_results['link_flowrate'].append(flow[link_id])
            self._sim_results['link_velocity'].append(0.0)
            self._sim_results['link_status'].append(self.link_status[link_id])
            if self.max_pump_flows[link_id] is not None:
                if flow[link_id]>self.max_pump_flows[link_id]:
                    link_name = self._link_id_to_name[link_id]
                    link = self._wn.get_link(link_name)
                    start_node_name = link.start_node()
                    end_node_name = link.end_node()
                    start_node_id = self._node_name_to_id[start_node_name]
                    end_node_id = self._node_name_to_id[end_node_name]
                    start_head = head[start_node_id]
                    end_head = head[end_node_id]
                    warnings.warn('Pump '+link_name+' has exceeded its maximum flow.')
                    logger.warning('Pump {0} has exceeded its maximum flow. Pump head: {1}; Pump flow: {2}; Max pump flow: {3}'.format(link_name,end_head-start_head, flow[link_id], self.max_pump_flows[link_id]))
        for link_id in self._valve_ids:
            self._sim_results['link_type'].append(LinkTypes.link_type_to_str(self.link_types[link_id]))
            self._sim_results['link_flowrate'].append(flow[link_id])
            self._sim_results['link_velocity'].append(0.0)
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
                           'expected_demand': self._sim_results['node_expected_demand'],
                           'head': self._sim_results['node_head'],
                           'pressure': self._sim_results['node_pressure'],
                           'leak_demand': self._sim_results['leak_demand'],
                           'type': self._sim_results['node_type']}
        for key,value in node_dictionary.iteritems():
            node_dictionary[key] = np.array(value).reshape((ntimes,nnodes))
        results.node = pd.Panel(node_dictionary, major_axis=results.time, minor_axis=node_names)

        link_dictionary = {'flowrate':self._sim_results['link_flowrate'],
                           'velocity':self._sim_results['link_velocity'],
                           'type':self._sim_results['link_type'],
                           'status':self._sim_results['link_status']}
        for key, value in link_dictionary.iteritems():
            link_dictionary[key] = np.array(value).reshape((ntimes, nlinks))
        results.link = pd.Panel(link_dictionary, major_axis=results.time, minor_axis=link_names)

    def set_network_inputs_by_id(self):
        self.isolated_junction_ids = []
        self.isolated_link_ids = []
        self.closed_links = set()
        self.isolated_junction_array = np.zeros(self.num_junctions) # 1 if it is isolated, 0 if it is not isolated
        self.isolated_link_array = np.zeros(self.num_links) # 1 if it is isolated, 0 if it is not isolated
        self.closed_link_array = np.ones(self.num_links) # 0 if it is closed, 1 if it is open/active
        for junction_name in self.isolated_junction_names:
            self.isolated_junction_ids.append(self._node_name_to_id[junction_name])
            self.isolated_junction_array[self._node_name_to_id[junction_name]] = 1.0
        for link_name in self.isolated_link_names:
            self.isolated_link_ids.append(self._link_name_to_id[link_name])
            self.isolated_link_array[self._link_name_to_id[link_name]] = 1.0

        for tank_name, tank in self._wn.nodes(Tank):
            tank_id = self._node_name_to_id[tank_name]
            self.tank_head[tank_id] = tank.head
            if tank._leak:
                self.leak_status[tank_id] = tank.leak_status
        for reservoir_name, reservoir in self._wn.nodes(Reservoir):
            reservoir_id = self._node_name_to_id[reservoir_name]
            self.reservoir_head[reservoir_id] = reservoir.head
        for junction_name, junction in self._wn.nodes(Junction):
            junction_id = self._node_name_to_id[junction_name]
            #if junction_id in self.isolated_junction_ids:
            #    self.junction_demand[junction_id] = 0.0
            #else:
            self.junction_demand[junction_id] = junction.expected_demand
            if junction._leak:
                self.leak_status[junction_id] = junction.leak_status
        for link_name, link in self._wn.links():
            link_id = self._link_name_to_id[link_name]
            self.link_status[link_id] = link.status
        for valve_name, valve in self._wn.links(Valve):
            valve_id = self._link_name_to_id[valve_name]
            self.valve_settings[valve_id] = valve.setting
            self.link_status[valve_id] = valve._status
        for pump_name, pump in self._wn.links(Pump):
            pump_id = self._link_name_to_id[pump_name]
            self.pump_speeds[pump_id] = pump.speed
            if pump._cv_status == wntr.network.LinkStatus.closed:
                self.link_status[pump_id] = pump._cv_status
        for link_id in self._link_ids:
            if self.link_status[link_id] == wntr.network.LinkStatus.closed:
                self.closed_links.add(link_id)
                self.closed_link_array[link_id] = 0.0

    def update_tank_heads(self):
        for tank_name, tank in self._wn.nodes(Tank):
            q_net = tank.prev_demand
            delta_h = 4.0*q_net*(self._wn.sim_time-self._wn.prev_sim_time)/(math.pi*tank.diameter**2)
            tank.head = tank.prev_head + delta_h

    def update_junction_demands(self, demand_dict):
        t = math.floor(self._wn.sim_time/self._wn.options.hydraulic_timestep)
        for junction_name, junction in self._wn.nodes(Junction):
            junction.expected_demand = demand_dict[(junction_name,t)]

    def reset_isolated_junctions(self):
        self.isolated_junction_names = set()
        self.isolated_link_names = set()

    def identify_isolated_junctions(self, isolated_junction_names, isolated_link_names):
        # self.isolated_junction_names, self.isolated_link_names = self._wn._get_isolated_junctions()
        self.isolated_junction_names = isolated_junction_names
        self.isolated_link_names = isolated_link_names
        if len(self.isolated_junction_names)>0:
            logger.warning('There are {0} isolated junctions.'.format(len(self.isolated_junction_names)))
            # logger.debug('{0}'.format(self.isolated_junction_names))
            logger.warning('There are {0} isolated links.'.format(len(self.isolated_link_names)))
            # logger.debug('{0}'.format(self.isolated_link_names))

    def update_network_previous_values(self):
        self._wn.prev_sim_time = self._wn.sim_time
        for name, node in self._wn.nodes(Junction):
            node.prev_head = node.head
            node.prev_demand = node.demand
            node.prev_expected_demand = node.expected_demand
            node.prev_leak_demand = node.leak_demand
        for name, node in self._wn.nodes(Tank):
            node.prev_head = node.head
            node.prev_demand = node.demand
            node.prev_leak_demand = node.leak_demand
        for name, node in self._wn.nodes(Reservoir):
            node.prev_head = node.head
            node.prev_demand = node.demand
        for link_name, link in self._wn.links(Pipe):
            link.prev_flow = link.flow
        for link_name, link in self._wn.links(Pump):
            link.prev_flow = link.flow
            link._prev_power_outage = link._power_outage
        for link_name, link in self._wn.links(Valve):
            link.prev_flow = link.flow

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
            link.flow = flow[link_id]

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
            for i in xrange(len(values)):
                if type(values[i]) == str:
                    string = string+'{0:<6s}'.format(values[i])
                else:
                    string = string+'{0:<6.2f}'.format(values[i])
            return string

        print construct_string('variable',[node_name for node_name, node in self._wn.nodes()]+[node_name for node_name, node in self._wn.nodes()]+[link_name for link_name, link in self._wn.links()]+[self._node_id_to_name[node_id] for node_id in self._leak_ids])
        for node_id in xrange(self.num_nodes):
            print construct_string(self._node_id_to_name[node_id], jacobian.getrow(node_id).toarray()[0])
        for node_id in xrange(self.num_nodes):
            print construct_string(self._node_id_to_name[node_id], jacobian.getrow(self.num_nodes+node_id).toarray()[0])
        for link_id in xrange(self.num_links):
            print construct_string(self._link_id_to_name[link_id], jacobian.getrow(2*self.num_nodes+link_id).toarray()[0])
        for node_id in self._leak_ids:
            print construct_string(self._node_id_to_name[node_id], jacobian.getrow(2*self.num_nodes+self.num_links+self._leak_ids.index(node_id)).toarray()[0])

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
        approx_jac = np.matrix(np.zeros((self.num_nodes*2+self.num_links+self.num_leaks, self.num_nodes*2+self.num_links+self.num_leaks)))

        step = 0.00001

        resids = self.get_hydraulic_equations(x)

        x1 = copy.copy(x)
        x2 = copy.copy(x)
        print 'shape = (',len(x),',',len(x),')'
        for i in xrange(len(x)):
            print 'getting approximate derivative of column ',i
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

        print 'computing difference between jac and approx_jac'
        difference = approx_jac - jac

        success = True
        for i in xrange(jac.shape[0]):
            print 'comparing values in row ',i,'with non-zeros from self.jacobain'
            row_nnz = jac.indptr[i+1] - jac.indptr[i]
            for k in xrange(row_nnz):
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
                        print 'flow for link ',node_or_link_name,' = ',x[i]
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
                    print 'jacobian entry for ',equation_type,' for ',node_or_link,' ',node_or_link_name,' with respect to ',wrt,wrt_name,' is incorrect.'
                    print 'error = ',abs(approx_jac[i,j]-jac[i,j])
                    print 'approximation = ',approx_jac[i,j]
                    print 'exact = ',jac[i,j]
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

    def check_infeasibility(self,x):
        resid = self.get_hydraulic_equations(x)
        for i in xrange(len(resid)):
            r = abs(resid[i])
            if r > 0.0001:
                if i >= 2*self.num_nodes:
                    print 'residual for headloss equation for link ',self._link_id_to_name[i-2*self.num_nodes],' is ',r,'; flow = ',x[i]
                elif i >= self.num_nodes:
                    print 'residual for demand/head eqn for node ',self._node_id_to_name[i-self.num_nodes],' is ',r
                else:
                    print 'residual for node balance for node ',self._node_id_to_name[i],' is ',r
