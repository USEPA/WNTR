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

        self.node_balance_residual = np.ones(self._wn.num_nodes())

        # Create dictionaries with node and link id's to names
        self._node_id_to_name = {}
        self._link_id_to_name = {}
        self._node_name_to_id = {}
        self._node_name_to_tank_id = {}
        self._tank_id_to_node_name = {}
        self._node_name_to_reservoir_id = {}
        self._link_name_to_id = {}
        self._junction_name_to_id = {}

        n = 0
        t = 0
        r = 0
        j = 0
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
            elif isinstance(node, Junction):
                self._junction_name_to_id[node_name] = j
                j += 1

        l = 0
        for link_name, link in self._wn.links():
            self._link_id_to_name[l] = link_name
            self._link_name_to_id[link_name] = l
            l += 1


    def run_eps(self):
        """
        Method to run an extended period simulation
        """


    def solve_hydraulics(self, net_status):
        """
        Method to solve the hydraulic equations given the network status

        Parameters
        ----------
        net_status: a NetworkStatus object
        """

    def _node_balance_residual(self, flow, tank_inflow, reservoir_demand, junction_demand):
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
        tank_inflow_offset = self._wn.num_links() + self._wn.num_nodes()
        reservoir_demand_offset = tank_inflow_offset + self._num_tanks
        junction_offset = self._wn.num_links() + self._wn.num_nodes() + self._num_tanks + self._num_reservoirs
        head_offset = self._wn.num_links()

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
                    #self._jac[self._jac_counter, link_id] = 1.0
                else:
                    raise RuntimeError('Node link is neither start nor end node.')
            if isinstance(node, Junction):
                #node_id = self._node_name_to_id[node_name]
                junction_id = self._junction_name_to_id[node_name]
                residual.append(expr - junction_demand[junction_id])
                #self._jac[self._jac_counter, junction_offset + junction_id] = -1.0
            elif isinstance(node, Tank):
                tank_id = self._node_name_to_tank_id[node_name]
                residual.append(expr - tank_inflow[tank_id])
                #self._jac[self._jac_counter, tank_inflow_offset+tank_id] = -1.0
            elif isinstance(node, Reservoir):
                reservoir_id = self._node_name_to_reservoir_id[node_name]
                residual.append(expr - reservoir_demand[reservoir_id])
                #self._jac[self._jac_counter, reservoir_demand_offset + reservoir_id] = -1.0
            else:
                raise RuntimeError('Node type not recognised.')
            # Increment jacobian counter
            #self._jac_counter += 1

        return residual
