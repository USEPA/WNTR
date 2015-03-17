"""
QUESTIONS
"""

"""
TODO
1. Support for valves.
2. Support for reservoir head patterns.
"""

import epanetlib as en
from epanetlib.units import convert
import tempfile
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import fsolve
import warnings

from WaterNetworkSimulator import *
from epanetlib.network.WaterNetworkModel import Junction, Tank, Reservoir, Pipe, Pump
import pandas as pd

class ScipySimulator(WaterNetworkSimulator):
    """
    Run simulations using scipy.optimize.
    """

    def __init__(self, wn):
        """
        Simulator object to be used for running scipy simulations.

        Parameters
        ---------
        wn : WaterNetworkModel
            A water network
        """
        WaterNetworkSimulator.__init__(self, wn)

        print self._sim_duration_min
        print self._hydraulic_step_min
        print self._pattern_step_min

        # Hazen-Williams resistance coefficient
        self._Hw_k = 10.67 # SI units = 4.727 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.

        # Create dictionaries with node and link id's to names
        self._node_id_to_name = {}
        self._link_id_to_name = {}
        self._node_name_to_id = {}
        self._node_name_to_tank_id = {}
        self._tank_id_to_node_name = {}
        self._node_name_to_reservoir_id = {}
        self._link_name_to_id = {}
        n = 0
        t = 0
        r = 0
        for node_name, node in self._wn.nodes():
            self._node_id_to_name[n] = node_name
            self._node_name_to_id[node_name] = n
            n += 1
            if isinstance(node, Tank):
                self._node_name_to_tank_id[node_name] = t
                self._tank_id_to_node_name[t] = node_name
                t += 1
            elif isinstance(node, Reservoir):
                self._node_name_to_reservoir_id[node_name] = r
                r += 1
        l = 0
        for link_name, link in self._wn.links():
            self._link_id_to_name[l] = link_name
            self._link_name_to_id[link_name] = l
            l += 1

    def run_sim(self):

        n_timesteps = int(round(self._sim_duration_min/self._hydraulic_step_min))+1

        # Get all demand for complete time interval
        demand_dict = {}
        for node_name, node in self._wn.nodes():
            if isinstance(node, Junction):
                demand_values = self.get_node_demand(node_name)
                for t in range(n_timesteps):
                    demand_dict[(node_name, t)] = demand_values[t]
            else:
                for t in range(n_timesteps):
                    demand_dict[(node_name, t)] = 0.0

        num_tanks = getattr(self._wn, '_num_tanks')
        num_tanks = getattr(self._wn, '_num_tanks')
        num_reservoirs = getattr(self._wn, '_num_reservoirs')

        # Initial guesses for variables
        flow_0 = 0.1*np.ones(self._wn.num_links())
        headloss_0 = 10.0*np.ones(self._wn.num_links())
        head_0 = 200.0*np.ones(self._wn.num_nodes())
        tank_inflow_0 = 0.1*np.ones(num_tanks)
        reservoir_demand_0 = np.ones(num_reservoirs)

        # Length of variables
        num_flows = self._wn.num_links()
        num_headloss = self._wn.num_links()
        num_heads = self._wn.num_nodes()

        # data for results object
        node_name = []
        node_type = []
        node_times = []
        node_head = []
        node_demand = []
        node_pressure = []
        link_name = []
        link_type = []
        link_times = []
        link_velocity = []
        link_flowrate = []

        # Create results object
        results = NetResults()

        # Load general simulation options into the results object
        self._load_general_results(results)

        # Create Delta time series
        results.time = pd.timedelta_range(start='0 minutes',
                                          end=str(self._sim_duration_min) + ' minutes',
                                          freq=str(self._hydraulic_step_min) + 'min')

        # Main simulation level
        for t in xrange(n_timesteps):
            if t == 0:
                first_timestep = True
                last_tank_head = []
                for tank_id in xrange(num_tanks):
                    tank = self._wn.get_node(self._tank_id_to_node_name[tank_id])
                    last_tank_head.append(tank.elevation + tank.init_level)
            else:
                first_timestep = False

            current_demands = [demand_dict[(self._node_id_to_name[n],t)] for n in xrange(self._wn.num_nodes())]

            # Concatenate inital guess vector
            x_0 = np.concatenate((flow_0, headloss_0, head_0, tank_inflow_0, reservoir_demand_0))

            # Use scipy to solve
            x = fsolve(self._hydraulic_equations, x_0, args=(last_tank_head, current_demands, first_timestep))

            # Load results from scipy
            flow = x[0:num_flows]
            headloss = x[num_flows:num_flows+num_headloss]
            head = x[num_flows+num_headloss:num_flows+num_headloss+num_heads]
            tank_inflow = x[num_flows+num_headloss+num_heads:num_flows+num_headloss+num_heads+num_tanks]
            reservoir_demand = x[num_flows+num_headloss+num_heads+num_tanks:num_flows+num_headloss+num_heads+num_tanks+num_reservoirs]
            for tank_id in xrange(num_tanks):
                node_id = self._node_name_to_id[self._tank_id_to_node_name[tank_id]]
                last_tank_head[tank_id] = head[node_id]

            # Load all node results
            timedelta = results.time[t]
            print "Running Hydraulic Simulation at time ", timedelta, " ..."
            for n in xrange(self._wn.num_nodes()):
                name = self._node_id_to_name[n]
                node = self._wn.get_node(name)
                node_name.append(name)
                node_type.append(self._get_node_type(name))
                node_times.append(timedelta)
                node_head.append(head[n])
                # Add node demand
                if isinstance(node, Junction):
                    node_demand.append(current_demands[n])
                elif isinstance(node, Reservoir):
                    reserv_id = self._node_name_to_reservoir_id[name]
                    node_demand.append(reservoir_demand[reserv_id])
                elif isinstance(node, Tank):
                    tank_id = self._node_name_to_tank_id[name]
                    node_demand.append(tank_inflow[tank_id])
                else:
                    node_demand.append(0.0)
                # Add pressure
                if isinstance(node, Reservoir):
                    pressure_n_t = 0.0
                else:
                    pressure_n_t = head[n] - node.elevation
                node_pressure.append(pressure_n_t)

            # Load all link results
            for l in xrange(self._wn.num_links()):
                name = self._link_id_to_name[l]
                link = self._wn.get_link(name)
                link_name.append(name)
                link_type.append(self._get_link_type(name))
                link_times.append(timedelta)
                link_flowrate.append(flow[l])
                if isinstance(link, Pipe):
                    velocity_l_t = 4.0*abs(flow[l])/(math.pi*link.diameter**2)
                else:
                    velocity_l_t = 0.0
                link_velocity.append(velocity_l_t)

            # Initial guesses for variables
            flow_0 = flow
            headloss_0 = headloss
            head_0 = head
            tank_inflow_0 = tank_inflow
            reservoir_demand_0 = reservoir_demand


        # END MAIN SIM LOOP

        node_data_frame = pd.DataFrame({'time': node_times,
                                        'node': node_name,
                                        'demand': node_demand,
                                        'head': node_head,
                                        'pressure': node_pressure,
                                        'type': node_type})

        node_pivot_table = pd.pivot_table(node_data_frame,
                                          values=['demand', 'head', 'pressure', 'type'],
                                          index=['node', 'time'],
                                          aggfunc= lambda x: x)
        results.node = node_pivot_table

        link_data_frame = pd.DataFrame({'time': link_times,
                                        'link': link_name,
                                        'flowrate': link_flowrate,
                                        'velocity': link_velocity,
                                        'type': link_type})

        link_pivot_table = pd.pivot_table(link_data_frame,
                                              values=['flowrate', 'velocity', 'type'],
                                              index=['link', 'time'],
                                              aggfunc= lambda x: x)
        results.link = link_pivot_table

        return results

    def _hydraulic_equations(self, x, last_tank_head, nodal_demands, first_timestep):

        # Get number of network components
        num_nodes = self._wn.num_nodes()
        num_links = self._wn.num_links()
        #num_junctions = getattr(self._wn, '_num_junctions')
        num_tanks = getattr(self._wn, '_num_tanks')
        num_reservoirs = getattr(self._wn, '_num_reservoirs')
        #num_pipes = getattr(self._wn, '_num_pipes')
        #num_pumps = getattr(self._wn, '_num_pumps')
        #num_valves = getattr(self._wn, '_num_valves')


        # Calculate number of variables
        num_flows = num_links
        num_headloss = num_links
        num_heads = num_nodes

        # Variables
        # x is concatination of following variables = [flow(each link), headloss(each link), head(each node), tank_inflow(each tank), reservoir_demand(each reservoir)]
        flow = x[0:num_flows]
        headloss = x[num_flows:num_flows+num_headloss]
        head = x[num_flows+num_headloss:num_flows+num_headloss+num_heads]
        tank_inflow = x[num_flows+num_headloss+num_heads:num_flows+num_headloss+num_heads+num_tanks]
        reservoir_demand = x[num_flows+num_headloss+num_heads+num_tanks:num_flows+num_headloss+num_heads+num_tanks+num_reservoirs]


        # Node balance
        node_balance_residual = self._node_balance_residual(flow, tank_inflow, reservoir_demand, nodal_demands)

        # Headloss balance
        headloss_residual = self._headloss_residual(headloss, flow)

        # Node head definition
        head_residual = self._head_residual(head, headloss)

        # Tank head
        tank_head_residual = self._tank_head_residual(head, tank_inflow, last_tank_head, first_timestep)

        # Reservoir head residual
        reservoir_head_residual = self._reservoir_head_residual(head)

        all_residuals = np.concatenate((node_balance_residual,
                         headloss_residual,
                         head_residual,
                         tank_head_residual,
                         reservoir_head_residual))


        return all_residuals

    def _node_balance_residual(self, flow, tank_inflow, reservoir_demand, nodal_demands):
        """
        Mass balance at all the nodes

        Parameters
        ---------
        flow : list of floats
             List of flow values in each pipe

        Return
        --------
        List of residuals of the node mass balances
        """
        residual = []

        for node_name, node in self._wn.nodes():
            node_id = self._node_name_to_id[node_name]
            connected_links = self._wn.get_links_for_node(node_name)
            expr = 0
            for l in connected_links:
                link = self._wn.get_link(l)
                if link.start_node() == node_name:
                    link_id = self._link_name_to_id[l]
                    expr -= flow[link_id]
                elif link.end_node() == node_name:
                    link_id = self._link_name_to_id[l]
                    expr += flow[link_id]
                else:
                    raise RuntimeError('Node link is neither start nor end node.')
            if isinstance(node, Junction):
                residual.append(nodal_demands[node_id] - expr)
            elif isinstance(node, Tank):
                tank_id = self._node_name_to_tank_id[node_name]
                residual.append(tank_inflow[tank_id] - expr)
            elif isinstance(node, Reservoir):
                reservoir_id = self._node_name_to_reservoir_id[node_name]
                residual.append(reservoir_demand[reservoir_id] - expr)
            else:
                raise RuntimeError('Node type not recognised.')
        return residual

    def _headloss_residual(self, headloss, flow):

        residual = []

        for link_name, link in self._wn.links():
            link_id = self._link_name_to_id[link_name]
            if isinstance(link, Pipe):
                pipe_resistance_coeff = self._Hw_k*(link.roughness**(-1.852))*(link.diameter**(-4.871))*link.length # Hazen-Williams
                pipe_headloss = pipe_resistance_coeff*flow[link_id]*(abs(flow[link_id]))**0.852
                residual.append(pipe_headloss - headloss[link_id])
            elif isinstance(link, Pump):
                A, B, C = link.get_head_curve_coefficients()
                pump_headgain = -1.0*A + B*flow[link_id]**C
                residual.append(pump_headgain - headloss[link_id])
            else:
                residual.append(0.0 - headloss[link_id])
                warnings.warn('Valves are not supported')

        return residual

    def _head_residual(self, head, headloss):

        residual = []

        for link_name, link in self._wn.links():
            link_id = self._link_name_to_id[link_name]
            start_node_id = self._node_name_to_id[link.start_node()]
            end_node_id = self._node_name_to_id[link.end_node()]
            link_head_residual = headloss[link_id] - (head[start_node_id] - head[end_node_id])
            residual.append(link_head_residual)

        return residual

    def _tank_head_residual(self, head, tank_inflow, last_tank_head, first_timestep):

        residual = []

        for tank_name, tank in self._wn.nodes(Tank):
            tank_id = self._node_name_to_tank_id[tank_name]
            node_id = self._node_name_to_id[tank_name]
            if first_timestep:
                tank_residual = head[node_id] - (tank.init_level + tank.elevation)
            else:
                tank_residual = (tank_inflow[tank_id]*self._hydraulic_step_min*60.0*4.0)/(math.pi*(tank.diameter**2)) - (head[node_id]-last_tank_head[tank_id])
            residual.append(tank_residual)

        return residual

    def _reservoir_head_residual(self, head):

        residual = []

        for reservoir_name, reservoir in self._wn.nodes(Reservoir):
            node_id = self._node_name_to_id[reservoir_name]
            residual.append(head[node_id] - reservoir.base_head)

        return residual

    def _load_general_results(self, results):
        """
        Load general simulation options into the results object.

        Parameter
        ------
        results : NetworkResults object
        """
        # Load general results
        results.network_name = self._wn.name

        # Load simulator options
        results.simulator_options['type'] = 'SCIPY'
        results.simulator_options['start_time'] = self._sim_start_min
        results.simulator_options['duration'] = self._sim_duration_min
        results.simulator_options['pattern_start_time'] = self._pattern_start_min
        results.simulator_options['hydraulic_time_step'] = self._hydraulic_step_min
        results.simulator_options['pattern_time_step'] = self._pattern_step_min
