try:
    from pyomo.environ import *
    from pyomo.core import *
    from pyomo.core.base.expr import Expr_if
    from pyomo.core.base.expr import exp as pyomoexp
    from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
except ImportError:
    raise ImportError('Error importing pyomo while running pyomo simulator.'
                      'Make sure pyomo is installed and added to path.')
import math
from WaterNetworkSimulator import *
import pandas as pd
from six import iteritems
import warnings

import cProfile, pstats, StringIO
import gc

def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.print_stats()
    return profiled_func
import time


"""
Issues to be aware of:
1. Negative pressures:
     We see negative pressures in the following scenarios:

          - A tank level drops to a negative pressue (because we
            haven't yet implemented adaptive timesteps)

          - The current implementation of the PDD constraint requires
            the pressure to be negative for the demand to be 0. We are
            trying an alternative PDD constraint (see
            pressure_dependent_demand_nl_alt) to correct this, but it
            is not finished.

          - If a pipe has drained of water, our model doesn't know
            it. Consider the case where the flowrate in a pipe is
            0. The start node has an actual demand of 0, so the
            pressure is close to 0. Because the flowrate is 0, the
            head at the end node has to be the same as the head at the
            start node.  However, if the end node is at a higher
            elevation than the start node, then the pressure will be
            lower than the pressure at the start node by the
            difference in elevation. (Remember, here, pressure =
            head-elevation)

          - The outlet pressure of a pump is low. If the outlet
            pressure is less than the pump head, then the inlet
            pressure will be negative.

     I think if we simply put a lower bound on the pressue and
     implemented an adaptive timestep, all of these problems would be
     solved except the one where a pipe has drained all water out of
     it and the model doesn't know it. I don't know how to solve that
     problem yet.

2. Infeasible problems due to pumps: 
     Orinially, we were seeing ampl evaluation errors for pumps
     becuase the first or second derivative is undefined when q = 0
     (for some pumps - it depends on the particular pump curve). We
     decided to close pumps with low flow rates and resolve the
     problem. However, we didn't have any criteria to open these pumps
     back up. We stopped closing pumps for low flow rates and modified
     the pump curve to be a piecewise function with a line with a
     small slope when q is close to 0. There was another problem. If
     the pressure at the end node of the pump needs to be larger than
     what the pump can provide, then the problem becomes infeasible
     because we placed a lower bound of 0.0 on the pump flow
     rate. Thus, we made the lower bound -0.1 and started treating
     pumps as check valves.  Reducing the lower bound allows the flow
     rate to become negative, and then we have a way to identify
     whether or not the pump should be closed. If we completely
     removed the lower bound on the pump flow rate or reduced it too
     much, then Ipopt had trouble solving some problems. I am not sure
     why though. This way, the pumps can be reopened when the start
     node head plus the maximum pump head is greater than or equal to
     the end node head.

3. Leaks:
     Originally, we placed a lower bound on the leak flow rate of 0.0
     (i.e., we did not want to allow flow into the network). However,
     this implied a lower bound on the pressure at the leak node of
     0.0. In cases where the pressure at the leak node needed to be
     negative, this caused the problem to be infeasible. Thus, we made
     the constraint relating the pressure at the leak to the leak flow
     rate a piecewise function. When P<=0, the leak flow rate is
     1E-11*P. When P>=delta, the normal model is used. In between, a
     smoothing polynomial is used.

"""

"""
Class for keeping approximation functions in a single place 
and avoid code duplications. Should be located in a better place
This is just a temporal implementation
"""
class ApproxFunctions():

    def __init__(self):
        self.q1 = 0.00349347323944
        self.q2 = 0.00549347323944
    # The Hazen-Williams headloss curve is slightly modified to improve solution time.
    # The three functions defined below - f1, f2, Px - are used to ensure that the Jacobian
    # is well defined at zero flow.
    def leftFunct(self,x):
        return 0.01*x

    def rightFunct(self,x):
        return 1.0*x**1.852

    def middleFunct(self,x):
        #return 1.05461308881e-05 + 0.0494234328901*x - 0.201070504673*x**2 + 15.3265906777*x**3
        return 2.45944613543e-06 + 0.0138413824671*x - 2.80374270811*x**2 + 430.125623753*x**3

    # discontinuous approximation of hazen williams headloss function
    def hazenWDisc(self,Q):
        return Expr_if(IF = Q < self.q1, THEN = self.leftFunct(Q), 
            ELSE = Expr_if(IF = Q > self.q2, THEN = self.rightFunct(Q), 
                ELSE = self.middleFunct(Q)))

    # could be a lambda function
    def sigmoidFunction(self,x,switch_x,alpha=1e-5):
        return 1.0 / (1.0 + pyomoexp(-(x-switch_x)/alpha))

    def leftLayer(self,x,alpha=1e-5):
        switch_x = self.q1
        return (1-self.sigmoidFunction(x,switch_x,alpha))*self.leftFunct(x)+ self.sigmoidFunction(x,switch_x,alpha)*self.middleFunct(x)

    def hazenWCont(self,x, alpha=1e-5):
        switch_x = self.q2
        sigma = self.sigmoidFunction(x,switch_x,alpha)
        return  (1-sigma)*self.leftLayer(x,alpha)+sigma*self.rightFunct(x)

    def hazenWDisc2(self,Q):
        return Expr_if(IF = Q < self.q2, THEN =  self.leftLayer(Q,1e-5),
            ELSE = self.rightFunct(Q))


class PyomoSimulator(WaterNetworkSimulator):
    """
    Pyomo simulator inherited from Water Network Simulator.
    """


    def __init__(self, wn, pressure_dependent = False):
        """
        Pyomo simulator class.

        Parameters
        ----------
        wn : WaterNetwork object

        pressure_dependent: bool 
            Specifies whether the simulation will be demand-driven or
            pressure-driven. True means the simulation will be
            pressure-driven.

        """
        super(PyomoSimulator, self).__init__(wn, pressure_dependent)

        # Global constants
        self._Hw_k = 10.666829500036352 # Hazen-Williams resistance coefficient in SI units (it equals 4.727 in EPANET GPM units). See Table 3.1 in EPANET 2 User manual.
        self._Dw_k = 0.0826 # Darcy-Weisbach constant in SI units (it equals 0.0252 in EPANET GPM units). See Table 3.1 in EPANET 2 User manual.
        self._Htol = 0.00015 # Head tolerance in meters.
        self._Qtol = 2.8e-5 # Flow tolerance in m^3/s.
        self._g = 9.81 # Acceleration due to gravity
        self._slope_of_PDD_curve = 1e-11 # The flat lines in the PDD model are provided a small slope for numerical stability
        self._pdd_smoothing_delta = 0.1 # Tightness of polynomial used to smooth sharp changes in PDD model.

        self._n_timesteps = 0 # Number of hydraulic timesteps
        self._demand_dict = {} # demand dictionary
        self._link_status = {} # dictionary of link statuses. 0 means close link, 1 means open link, 2 means take no action
        self._valve_status = {} # dictionary of valve statuses

        self._initialize_results_dict()
        self._max_step_iter = 10 # maximum number of newton solves at each timestep.
                                 # model is resolved when a valve status changes, the links closed changes, or the solver does not converge.

        # Timing
        self.prep_time_before_main_loop = 0.0
        self.solve_step = {}
        self.build_model_time = {}
        self.time_per_step = []

    def _initialize_simulation(self, fixed_demands=None):

        # Initialize time parameters
        #self.init_time_params_from_model()

        # Number of hydraulic timesteps
        self._n_timesteps = int(round(self._sim_duration_sec / self._hydraulic_step_sec)) + 1

        # Get all demand for complete time interval
        self._demand_dict = {}
        if fixed_demands is None:
            for node_name, node in self._wn.nodes():
                if isinstance(node, Junction):
                    demand_values = self.get_node_demand(node_name)
                    for t in range(self._n_timesteps):
                        self._demand_dict[(node_name, t)] = demand_values[t]
                else:
                    for t in range(self._n_timesteps):
                        self._demand_dict[(node_name, t)] = 0.0
        else:
            nodes_to_fix = fixed_demands.keys()
            for node_name, node in self._wn.nodes():
                if isinstance(node, Junction):
                    demand_values = self.get_node_demand(node_name)
                    for t in range(self._n_timesteps):
                        if (node_name,t) in nodes_to_fix:
                            self._demand_dict[(node_name, t)] = fixed_demands[(node_name,t)]
                        else:
                            self._demand_dict[(node_name, t)] = demand_values[t]
                else:
                    for t in range(self._n_timesteps):
                        self._demand_dict[(node_name, t)] = 0.0

        # Create time controls dictionary
        # Format: {link_name:list}
        # Where list can contain 0, 1, or 2
        # Each entry in the list corresponds to a timestep
        #    0: link should be closed at corresponding timestep
        #    1: link should be opened at corresponding timestep
        #    2: no action should be taken at corresponding timestep
        self._link_status = {}
        self._correct_time_controls_for_timestep() # should only be used until the simulator can take partial timesteps
        for l, link in self._wn.links():
            status_l = []
            for t in xrange(self._n_timesteps):
                time_sec = t * self._hydraulic_step_sec
                status_l_t = self.link_action(l, time_sec)
                status_l.append(status_l_t)
            self._link_status[l] = status_l

        # Create valve status dictionary
        self._valve_status = {}
        for valve_name, valve in self._wn.links(Valve):
            self._valve_status[valve_name] = 'ACTIVE'

    def _initialize_results_dict(self):
        # Data for results object
        self._pyomo_sim_results = {}
        self._pyomo_sim_results['node_name'] = []
        self._pyomo_sim_results['node_type'] = []
        self._pyomo_sim_results['node_times'] = []
        self._pyomo_sim_results['node_head'] = []
        self._pyomo_sim_results['node_demand'] = []
        self._pyomo_sim_results['node_expected_demand'] = []
        self._pyomo_sim_results['node_pressure'] = []
        self._pyomo_sim_results['leak_flow'] = []
        self._pyomo_sim_results['link_name'] = []
        self._pyomo_sim_results['link_type'] = []
        self._pyomo_sim_results['link_times'] = []
        self._pyomo_sim_results['link_velocity'] = []
        self._pyomo_sim_results['link_flowrate'] = []

    def _initialize_from_pyomo_results(self, instance, last_instance_results):

        for l in instance.links:
            if abs(last_instance_results['flow'][l]) < self._Qtol:
                instance.flow[l].value = 100*self._Qtol
            else:
                if l in instance.pumps and last_instance_results['flow'][l] < -self._Qtol:
                    instance.flow[l].value = 100*self._Qtol
                else:
                    instance.flow[l].value = last_instance_results['flow'][l] + self._Qtol

        for n in instance.nodes:
            instance.head[n].value = last_instance_results['head'][n]
            if n in instance.junctions:
                junction = self._wn.get_node(n)
                if self.pressure_dependent:
                    if instance.head[n].value - junction.elevation <= junction.minimum_pressure:
                        instance.demand_actual[n] = 100*self._Qtol
                    else:
                        instance.demand_actual[n] = abs(instance.demand_actual[n].value) + self._Qtol
                else:
                    instance.demand_actual[n] = abs(instance.demand_actual[n].value) + self._Qtol

        for r in instance.reservoirs:
            if abs(last_instance_results['reservoir_demand'][r]) < self._Qtol:
                instance.reservoir_demand[r].value = 100*self._Qtol
            else:
                instance.reservoir_demand[r].value = last_instance_results['reservoir_demand'][r] + self._Qtol
        for t in instance.tanks:
            if abs(last_instance_results['tank_net_inflow'][t]) < self._Qtol:
                instance.tank_net_inflow[t].value = 100*self._Qtol
            else:
                instance.tank_net_inflow[t].value = last_instance_results['tank_net_inflow'][t] + self._Qtol

        for n in instance.tanks_with_leaks:
            node = self._wn.get_node(n)
            if last_instance_results['head'][n]-node.elevation >= 0.0:
                instance.tank_leak_demand[n].value = node.leak_discharge_coeff*node.leak_area*math.sqrt(2*self._g)*math.sqrt(last_instance_results['head'][n]-node.elevation)
            else:
                instance.tank_leak_demand[n].value = 0.0

        for n in instance.junctions_with_leaks:
            node = self._wn.get_node(n)
            if last_instance_results['head'][n]-node.elevation >= 0.0:
                instance.junction_leak_demand[n].value = node.leak_discharge_coeff*node.leak_area*math.sqrt(2*self._g)*math.sqrt(last_instance_results['head'][n]-node.elevation)
            else:
                instance.junction_leak_demand[n].value = 0.0

    def _read_instance_results(self,instance):
        # Initialize dictionary
        last_instance_results = {}
        last_instance_results['flow'] = {}
        last_instance_results['head'] = {}
        last_instance_results['demand_actual'] = {}
        last_instance_results['reservoir_demand'] = {}
        last_instance_results['tank_net_inflow'] = {}
        # Load results into dictionary
        for l in instance.links:
            last_instance_results['flow'][l] = instance.flow[l].value
        for n in instance.nodes:
            last_instance_results['head'][n] = instance.head[n].value
            if n in instance.junctions:
                last_instance_results['demand_actual'][n] = instance.demand_actual[n].value
        for r in instance.reservoirs:
            last_instance_results['reservoir_demand'][r] = instance.reservoir_demand[r].value
        for t in instance.tanks:
            last_instance_results['tank_net_inflow'][t] = instance.tank_net_inflow[t].value
        return last_instance_results
        
    def _build_hydraulic_model_at_instant(self,
                                          t,
                                          last_tank_head,
                                          nodal_demands,
                                          first_timestep,
                                          links_closed,
                                          pumps_closed_by_outage,
                                          last_tank_net_inflows,
                                          modified_hazen_williams=True):
        """
        Build hydraulic constraints at a particular time.

        Parameters
        ----------
        last_tank_head : dict of string: float
            Dictionary containing tank names and their respective head at the last timestep.
        nodal_demands : dict of string: float
            Dictionary containing junction names and their respective respective expected demand at current timestep.
        first_timestep : bool
            Flag indicating wheather its the first timestep
        links_closed : list of strings
            Name of links that are closed.
        pumps_closed_by_outage : list of strings
            Name of pumps closed due to a power outage
        last_tank_net_inflows: dict of string: float
            Dictionary containing tank names and their respective net inflows at the last timestep.

        Other Parameters
        -------------------
        modified_hazen_williams : bool
            Flag to use a slightly modified version of Hazen-Williams headloss
            equation for better stability
        """

        current_time_sec = t*self._hydraulic_step_sec
        t0 = time.time()

        # for the approximation of hazen williams equation
        approximator = ApproxFunctions()

        # Currently this function is being called for every node at every time step.
        # TODO : Refactor pressure_dependent_demand_linear so that its created only once for the entire simulation.
        def pressure_dependent_demand_nl(full_demand, p, PF, P0):
            # Pressure driven demand equation
            # Returns the right hand side of the equation
            #
            #            0                                 if p<= P0
            # D_actual = full_demand*sqrt((p-P0)/(PF-P0))  if P0 <= p <= PF
            #            full_demand                       if p >= PF
            #
            # But with smoothing polynomials between the functions
            # Additionally, the first and last functions have small slopes
            delta = self._pdd_smoothing_delta
            # Defining Line 1 - demand above nominal pressure
            def L1(p):
                return self._slope_of_PDD_curve*p + full_demand
            # Defining PDD function
            def PDD(p):
                return full_demand*math.sqrt((p - P0)/(PF - P0))
            def PDD_deriv(p):
                return (full_demand/2)*(1/(PF - P0))*(1/math.sqrt((p - P0)/(PF - P0)))
            # Define Line 2 - demand below minimum pressure
            def L2(p):
                return self._slope_of_PDD_curve*p

            ## The parameters of the smoothing polynomials are estimated by solving a
            ## set of linear equation Ax=b.
            # Define A matrix as a function of 2 points on the polynomial.
            def A(x_1, x_2):
                return np.array([[x_1**3, x_1**2, x_1, 1],
                                [x_2**3, x_2**2, x_2, 1],
                                [3*x_1**2, 2*x_1,  1, 0],
                                [3*x_2**2, 2*x_2,  1, 0]])

            x_gap = PF - P0
            assert x_gap > delta, "Delta should be greater than the gap between nominal and minimum pressure."

            # Get parameters for the second polynomial
            x1 = P0 - x_gap*delta
            y1 = L2(x1)
            x2 = P0 + x_gap*delta
            y2 = PDD(x2)
            A1 = A(x1, x2)
            rhs1 = np.array([y1, y2, 0.0, PDD_deriv(x2)])
            c1 = np.linalg.solve(A1, rhs1)
            x3 = PF - x_gap*delta
            y3 = PDD(x3)
            x4 = PF + x_gap*delta
            y4 = L1(x4)
            A2 = A(x3, x4)
            rhs2 = np.array([y3, y4, PDD_deriv(x3), self._slope_of_PDD_curve])
            c2 = np.linalg.solve(A2, rhs2)

            def smooth_polynomial_lhs(p_):
                return c1[0]*p_**3 + c1[1]*p_**2 + c1[2]*p_ + c1[3]

            def smooth_polynomial_rhs(p_):
                return c2[0]*p_**3 + c2[1]*p_**2 + c2[2]*p_ + c2[3]

            def PDD_pyomo(p):
                return full_demand*sqrt((p - P0)/(PF - P0))

            return Expr_if(IF=p <= x1, THEN=L2(p),
               ELSE=Expr_if(IF=p <= x2, THEN=smooth_polynomial_lhs(p),
                            ELSE=Expr_if(IF=p <= x3, THEN=PDD_pyomo(p),
                                         ELSE=Expr_if(IF=p <= x4, THEN=smooth_polynomial_rhs(p),
                                                      ELSE=L1(p)))))

        def pressure_dependent_demand_nl_alt(full_demand, p, PF, P0):
            # Pressure driven demand equation
            # Alternative version of pressure_dependent_demand_nl
            # The original version doesn't get to 0 demand until the pressure gets down to about x1, which may be significantly negative
            # This version was made in an attempt to correct this. However, it doesn't work.

            assert (PF-P0) >= 0.1, "Minimum pressure and nominal pressure are too close."

            x1 = P0 - 1e-4
            x2 = P0 - 1e-8
            x3 = P0 + 1e-8
            x4 = P0 + 1e-4
            x5 = PF - 1e-4
            x6 = PF

            def F1(p):
                b = y1 - self._slope_of_PDD_curve*x1
                return self._slope_of_PDD_curve*p + b
            def F2(p):
                return p-P0
            def F3(p):
                return full_demand*math.sqrt((p - P0)/(PF - P0))
            def F4(p):
                b = full_demand - self._slope_of_PDD_curve*PF
                return self._slope_of_PDD_curve*p + b

            def F1_deriv(p):
                return self._slope_of_PDD_curve
            def F2_deriv(p):
                return 1.0
            def F3_deriv(p):
                return (full_demand/2)*(1/(PF - P0))*(1/math.sqrt((p - P0)/(PF - P0)))
            def F4_deriv(p):
                return self._slope_of_PDD_curve


            ## The parameters of the smoothing polynomials are estimated by solving a
            ## set of linear equation Ax=b.
            # Define A matrix as a function of 2 points on the polynomial.
            def A(x_1, x_2):
                return np.array([[x_1**3, x_1**2, x_1, 1],
                                [x_2**3, x_2**2, x_2, 1],
                                [3*x_1**2, 2*x_1,  1, 0],
                                [3*x_2**2, 2*x_2,  1, 0]])

            y1 = -1e-6
            y2 = -1e-8
            y3 = 1e-8
            y4 = F3(x4)
            y5 = F3(x5)
            y6 = full_demand

            A1 = A(x1, x2)
            A2 = A(x3, x4)
            A3 = A(x5, x6)

            rhs1 = np.array([y1, y2, F1_deriv(x1), F2_deriv(x2)])
            rhs2 = np.array([y3, y4, F2_deriv(x3), F3_deriv(x4)])
            rhs3 = np.array([y5, y6, F3_deriv(x5), F4_deriv(x6)])

            c1 = np.linalg.solve(A1, rhs1)
            c2 = np.linalg.solve(A2, rhs2)
            c3 = np.linalg.solve(A3, rhs3)

            def smooth_polynomial_1(p_):
                return c1[0]*p_**3 + c1[1]*p_**2 + c1[2]*p_ + c1[3]

            def smooth_polynomial_2(p_):
                return c2[0]*p_**3 + c2[1]*p_**2 + c2[2]*p_ + c2[3]

            def smooth_polynomial_3(p_):
                return c3[0]*p_**3 + c3[1]*p_**2 + c3[2]*p_ + c3[3]

            def PDD_pyomo(p):
                return full_demand*sqrt((p - P0)/(PF - P0))

            return Expr_if(IF=p <= x1, THEN=F1(p),
               ELSE=Expr_if(IF=p <= x2, THEN=smooth_polynomial_1(p),
                            ELSE=Expr_if(IF=p <= x3, THEN=F2(p),
                                         ELSE=Expr_if(IF=p <= x4, THEN=smooth_polynomial_2(p),
                                                      ELSE=Expr_if(IF=p <= x5, THEN=PDD_pyomo(p),
                                                                   ELSE=Expr_if(IF=p <=x6, THEN=smooth_polynomial_3(p),
                                                                                ELSE=F4(p)))))))


        # Currently this function is being called for every node at every time step.
        # TODO : Refactor pressure_dependent_demand_linear so that its created only once for the entire simulation.
        def pressure_dependent_demand_linear(full_demand, p, PF, P0):
            # This is a linear version of pressure_dependent_demand_nl

            delta = self._pdd_smoothing_delta
            # Defining Line 1 - demand above nominal pressure
            def L1(p):
                return self._slope_of_PDD_curve*p + full_demand
            # Defining Linear PDD Function
            def PDD(p):
                return full_demand*((p - P0)/(PF - P0))
            def PDD_deriv(x):
                return (full_demand)*(1/(PF - P0))
            # Define Line 2 - demand below minimum pressure
            def L2(p):
                return self._slope_of_PDD_curve*p

            ## The parameters of the smoothing polynomials are estimated by solving a
            ## set of linear equation Ax=b.
            # Define A matrix as a function of 2 points on the polynomial.
            def A(x_1, x_2):
                return np.array([[x_1**3, x_1**2, x_1, 1],
                                [x_2**3, x_2**2, x_2, 1],
                                [3*x_1**2, 2*x_1,  1, 0],
                                [3*x_2**2, 2*x_2,  1, 0]])
            x_gap = PF - P0
            assert x_gap > delta, "Delta should be greater than the gap between nominal and minimum pressure."

            # Solve for parameters of the LHS polynomial
            x1 = P0 - x_gap*delta
            y1 = L2(x1)
            x2 = P0 + x_gap*delta
            y2 = PDD(x2)
            A1 = A(x1, x2)
            rhs1 = np.array([y1, y2, self._slope_of_PDD_curve, PDD_deriv(x2)])
            c1 = np.linalg.solve(A1, rhs1)

            # Solve for parameters of the RHS polynomial
            x3 = PF - x_gap*delta
            y3 = PDD(x3)
            x4 = PF + x_gap*delta
            y4 = L1(x4)
            A2 = A(x3, x4)
            rhs2 = np.array([y3, y4, PDD_deriv(x3), self._slope_of_PDD_curve])
            c2 = np.linalg.solve(A2, rhs2)

            # Create smoothing polynomial functions
            def smooth_polynomial_lhs(p_):
                return c1[0]*p_**3 + c1[1]*p_**2 + c1[2]*p_ + c1[3]
            def smooth_polynomial_rhs(p_):
                return c2[0]*p_**3 + c2[1]*p_**2 + c2[2]*p_ + c2[3]

            return Expr_if(IF=p <= x1, THEN=L2(p),
               ELSE=Expr_if(IF=p <= x2, THEN=smooth_polynomial_lhs(p),
                            ELSE=Expr_if(IF=p <= x3, THEN=PDD(p),
                                         ELSE=Expr_if(IF=p <= x4, THEN=smooth_polynomial_rhs(p),
                                                      ELSE=L1(p)))))

        def modified_pump_curve(q, A, B, C):
            # The pump curve is
            #
            #      H = A-B*q**C
            #
            # However, if C is not an integer and is less than 2, then either the first or
            # second derivative with respect to q is undefined when q=0. Thus, we modify
            # the pump curve near q = 0 to be a line. Then we place a smoothing polynomial
            # between the line and the actual pump curve.
            L1_slope = -1.0e-11
            x1 = 1.0e-8
            x2 = 2.0*x1

            # The line for q<=x1
            def L1(q,A):
                return L1_slope*q+A
            # The actual pump curve
            def pump_curve(q,A,B,C):
                return A-B*q**C

            # Get the coefficients of the smoothing polynomial
            def get_rhs(A,B,C):
                return np.matrix([[L1_slope*x1+A],[A-B*x2**C],[L1_slope],[-B*C*x2**(C-1.0)]])
            coeff_matrix = np.matrix([[x1**3, x1**2, x1, 1.0],[x2**3, x2**2, x2, 1.0],[3*x1**2, 2*x1, 1.0, 0.0],[3*x2**2, 2*x2, 1.0, 0.0]])
            poly_coeff = np.linalg.solve(coeff_matrix, get_rhs(A,B,C))

            # The smoothing polynomial
            def smooth_poly(q):
                a = float(poly_coeff[0][0])
                b = float(poly_coeff[1][0])
                c = float(poly_coeff[2][0])
                d = float(poly_coeff[3][0])
                return a*q**3 + b*q**2 + c*q + d

            return Expr_if(IF=q <= x1, THEN=L1(q,A),
                           ELSE=Expr_if(IF=q <= x2, THEN=smooth_poly(q),
                                        ELSE=pump_curve(q,A,B,C)))

        def piecewise_pipe_leak_demand(p, Cd, A):
            # This is needed so that the pressure at a leak node can be negative
            # without having water flow into the network through the leak.
            # When the pressure is <= 0, the demand is close to zero (we use
            # a line with a very small slope). A smoothing polynomial is used
            # between the line and the actual leak model.
            #
            # Originally, we were placing a lower bound on the leak demand.
            # However, that implicitly placed a lower bound on the pressure.
            # In extreme scenarios, the pressure may need to be negative, so
            # we occasionally ran into infeasible problems when we used a
            # lower bound.
            delta = 1.0e-4
            L1_slope = 1.0e-11
            x1 = 0.0
            x2 = delta

            # Two of the polynomial coefficients are known
            c = L1_slope
            d = 0.0

            # The line for p <= 0
            def L1(p):
                return L1_slope*p
            # The leak demand model
            def leak_model(p, Cd, A):
                return Cd*A*math.sqrt(2.0*self._g)*p**0.5

            # Get the smoothing polynomial coefficients
            def get_rhs(x, Cd, A):
                return np.matrix([[Cd*A*math.sqrt(2.0*self._g)*x**0.5-c*x-d],[0.5*Cd*A*math.sqrt(2.0*self._g)*x**(-0.5)-c]])
            coeff_matrix = np.matrix([[x2**3.0, x2**2.0],[3*x2**2.0, 2*x2]])
            poly_coeff = np.linalg.solve(coeff_matrix, get_rhs(x2, Cd, A))
            a = float(poly_coeff[0][0])
            b = float(poly_coeff[1][0])

            # The smoothing polynomial
            def smooth_poly(p):
                return a*p**3 + b*p**2 + c*p + d

            return Expr_if(IF=p <= x1, THEN=L1(p),
                           ELSE=Expr_if(IF=p <= x2, THEN=smooth_poly(p),
                                        ELSE=leak_model(p,Cd,A)))

        ######## MAIN HYDRAULIC MODEL EQUATIONS ##########

        wn = self._wn
        model = ConcreteModel()
        model.timestep = self._hydraulic_step_sec

        ###################### SETS #########################
        # Sets are being created for easy access to results without the need of querying the network model.
        # NODES
        model.nodes = Set(initialize=[name for name, node in wn.nodes()])
        model.tanks = Set(initialize=[n for n, N in wn.nodes(Tank)])
        model.junctions = Set(initialize=[n for n, N in wn.nodes(Junction)])
        model.reservoirs = Set(initialize=[n for n, N in wn.nodes(Reservoir)])

        # LINKS
        model.links = Set(initialize=[name for name, link in wn.links()])
        model.pumps = Set(initialize=[l for l, L in wn.links(Pump)])
        model.valves = Set(initialize=[l for l, L in wn.links(Valve)])
        model.pipes = Set(initialize=[l for l, L in wn.links(Pipe)])

        # Tanks with leaks
        model.tanks_with_leaks = Set(initialize=[n for n, N in wn.nodes(Tank) if N.leak_present()==True and current_time_sec >= N.leak_start_time and current_time_sec < N.leak_end_time])

        # Junctions with leaks
        model.junctions_with_leaks = Set(initialize=[n for n, N in wn.nodes(Junction) if N.leak_present()==True and current_time_sec>=N.leak_start_time and current_time_sec<N.leak_end_time])

        ################### PARAMETERS #######################
        # Params are being created for easy access to results without the need of querying the network.
        model.demand_required = Param(model.junctions, within=Reals, initialize=nodal_demands)

        ################### VARIABLES #####################
        def flow_init_rule(model, l):
            if l in model.pipes or l in model.valves:
                return 0.3048
            elif l in model.pumps:
                pump = wn.get_link(l)
                if pump.info_type == 'HEAD':
                    return pump.get_design_flow()
                else:
                    return 0.3048
        def flow_bounds_rule(model, l):
            # If the link is a pump and is not closed by an outage, then the bounds
            # should be (0.0, None). If the pump is closed by an outage, then it is
            # replaced by a pipe (although this should change soon), so there should
            # not be any bounds on it.
            if l in model.pumps and l not in pumps_closed_by_outage:
                pump = self._wn.get_link(l)
                if pump.info_type == 'POWER':
                    return (0.0, None)
                # If the pump uses a pump curve, the we have to make the lower bound
                # slightly negative and treat the pump as a check valve. The reason
                # for this is that if the outlet pressure needs to be higher than
                # the pump can provide, then the problem will be infeasible. Thus,
                # we let the flow rate go slightly negative and resolve the problem
                # with the pump closed. Allowing the flow rate to go slightly negative
                # provides a way to identify the pumps that need closed.
                elif pump.info_type == 'HEAD':
                    return (-0.01, None)
                    #return (0.0, None)
                else:
                    raise ValueError('Pump info type not recognized: '+pump.info_type)
            # If the link is not a pump, or the pump is closed by an outage, then there
            # should not be any bounds on the flow rate.
            else:
                return (None, None)
        model.flow = Var(model.links, within=Reals, initialize=flow_init_rule, bounds=flow_bounds_rule)

        def init_head_rule(model, n):
            node = wn.get_node(n)
            if n in model.junctions:
                if self.pressure_dependent:
                    return node.elevation + node.nominal_pressure
                else:
                    return node.elevation
            elif n in model.tanks:
                return node.elevation
            else:
                return 100.0
        model.head = Var(model.nodes, initialize=init_head_rule)

        model.reservoir_demand = Var(model.reservoirs, within=Reals, initialize=0.1)
        model.tank_net_inflow = Var(model.tanks, within=Reals, initialize=0.1)

        # Initialize actual demand to required demand
        def init_demand_rule(model,n):
            return model.demand_required[n]
        model.demand_actual = Var(model.junctions, within=Reals, initialize=init_demand_rule)

        # Declare variables for leaks in tanks and junctions.
        def init_tank_leak_rule(model,n):
            node = wn.get_node(n)
            if model.head[n].value-node.elevation >= 0.0:
                return node.leak_discharge_coeff*node.leak_area*math.sqrt(2*self._g)*math.sqrt(model.head[n]-node.elevation)
            else:
                return 0.0
        model.tank_leak_demand = Var(model.tanks_with_leaks, within=Reals, initialize=init_tank_leak_rule, bounds=(None,None))

        def init_junction_leak_rule(model,n):
            node = wn.get_node(n)
            if model.head[n].value-node.elevation >= 0.0:
                return node.leak_discharge_coeff*node.leak_area*math.sqrt(2*self._g)*math.sqrt(model.head[n]-node.elevation)
            else:
                return 0.0
        model.junction_leak_demand = Var(model.junctions_with_leaks, within=Reals, initialize=init_junction_leak_rule, bounds=(None,None))

        ############## CONSTRAINTS #####################

        # Head loss inside pipes
        for l in model.pipes:
            pipe = wn.get_link(l)
            pipe_resistance_coeff = self._Hw_k*(pipe.roughness**(-1.852))*(pipe.diameter**(-4.871))*pipe.length # Hazen-Williams
            start_node = pipe.start_node()
            end_node = pipe.end_node()
            if l in links_closed:
                pass
            else:
                if modified_hazen_williams:
                    setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=Expr_if(IF=model.flow[l]>0, THEN=1, ELSE=-1)
                                                                       *pipe_resistance_coeff*approximator.hazenWDisc(abs(model.flow[l])) == model.head[start_node] - model.head[end_node]))
                else:
                    setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=Expr_if(IF=model.flow[l]>0, THEN=1, ELSE=-1)*pipe_resistance_coeff*(abs(model.flow[l]))**1.852 == model.head[start_node] - model.head[end_node]))

        # Head gain provided by the pump is implemented as negative headloss
        for l in model.pumps:
            pump = wn.get_link(l)
            start_node = pump.start_node()
            end_node = pump.end_node()
            if l not in links_closed:
                if l in pumps_closed_by_outage:
                    # replace pump by pipe of length 10m, diameter 1m, and roughness coefficient of 200
                    pipe_resistance_coeff = self._Hw_k*(200.0**(-1.852))*(1**(-4.871))*10.0 # Hazen-Williams coefficient
                    if modified_hazen_williams:
                        setattr(model, 'pipe_headloss_'+str(l), Constraint(expr= Expr_if(IF=model.flow[l]>0, THEN=1, ELSE=-1)
                                                                           *pipe_resistance_coeff*approximator.hazenWDisc(abs(model.flow[l])) == model.head[start_node] - model.head[end_node]))
                    else:
                        setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=pipe_resistance_coeff*model.flow[l]*(abs(model.flow[l]))**0.852 == model.head[start_node] - model.head[end_node]))
                else:
                    if pump.info_type == 'HEAD':
                        A, B, C = pump.get_head_curve_coefficients()
                        if l not in links_closed:
                            setattr(model, 'pump_negative_headloss_'+str(l), Constraint(expr=model.head[end_node] - model.head[start_node] == (modified_pump_curve(model.flow[l],A,B,C))))
                    elif pump.info_type == 'POWER':
                        if l not in links_closed:
                            setattr(model, 'pump_negative_headloss_'+str(l), Constraint(expr=(model.head[start_node] - model.head[end_node])*model.flow[l]*self._g*1000.0 == -pump.power))
                    else:
                        raise RuntimeError('Pump info type not recognised. ' + l)

        # Mass Balance
        def node_mass_balance_rule(model, n):
            node = wn.get_node(n)
            expr = 0
            for l in wn.get_links_for_node(n,'INLET'):
                expr += model.flow[l]
            for l in wn.get_links_for_node(n,'OUTLET'):
                expr -= model.flow[l]
            if isinstance(node, Junction):
                if n in model.junctions_with_leaks:
                    return expr == model.demand_actual[n] + model.junction_leak_demand[n]
                else:
                    return expr == model.demand_actual[n]
            elif isinstance(node, Tank):
                if n in model.tanks_with_leaks:
                    return expr - model.tank_leak_demand[n] == model.tank_net_inflow[n]
                else:
                    return expr == model.tank_net_inflow[n]
            elif isinstance(node, Reservoir):
                return expr == model.reservoir_demand[n]
            else:
                raise RuntimeError('Node type not recognized.')
        model.node_mass_balance = Constraint(model.nodes, rule=node_mass_balance_rule)


        def tank_dynamics_rule(model, n):
            # The tank level at the first timestep is known
            if first_timestep:
                return Constraint.Skip
            # The tank level for the current timestep is calculated from the flow rates
            # of the previous timestep
            else:
                tank = wn.get_node(n)
                return (last_tank_net_inflows[n]*model.timestep*4.0)/(math.pi*(tank.diameter**2)) == model.head[n]-last_tank_head[n]
        model.tank_dynamics = Constraint(model.tanks, rule=tank_dynamics_rule)

        # Pressure driven demand constraint
        def pressure_driven_demand_rule(model, j):
            junction = wn.get_node(j)
            if model.demand_required[j] == 0.0:
                #return Constraint.Skip
                return model.demand_actual[j] == 0.0 # Using this constraint worked better than fixing this variable.
            else:
                return pressure_dependent_demand_nl(model.demand_required[j], model.head[j]-junction.elevation, junction.nominal_pressure, junction.minimum_pressure) == model.demand_actual[j]

        def demand_driven_rule(model, j):
            return model.demand_actual[j] == model.demand_required[j]

        if self.pressure_dependent:
            model.pressure_driven_demand = Constraint(model.junctions, rule=pressure_driven_demand_rule)
        else:
            model.pressure_driven_demand = Constraint(model.junctions, rule=demand_driven_rule)

        # Tank leak demand constraint
        def tank_leak_rule(model, n):
            node = wn.get_node(n)
            return model.tank_leak_demand[n] == piecewise_pipe_leak_demand(model.head[n]-node.elevation, node.leak_discharge_coeff, node.leak_area)
        model.tank_leak_con = Constraint(model.tanks_with_leaks, rule=tank_leak_rule)

        # Junction leak demand constraint
        def junction_leak_rule(model, n):
            node = wn.get_node(n)
            return model.junction_leak_demand[n]==piecewise_pipe_leak_demand(model.head[n]-node.elevation,node.leak_discharge_coeff,node.leak_area)
        model.junction_leak_con = Constraint(model.junctions_with_leaks, rule=junction_leak_rule)

        return model

    def run_sim(self, solver='ipopt', solver_options={}, modified_hazen_williams=True, fixed_demands=None):

        """
        Other Parameters
        -------------------
        solver : String
            Name of the nonlinear programming solver to be used for solving the hydraulic equations.
            Default is 'ipopt'.
        solver_options : Dictionary
            A dictionary of solver options.
        modified_hazen_williams : Bool
            Flag used to turn on/off small modifications to the Hazen-Williams equation. These modifications are usually
            necessary for stability of the nonlinear solver. Default value is True.
        fixed_demands: Dictionary (node_name, time_step): demand value
            An external dictionary of demand values can be provided using this parameter. This option is used in the
            calibration work.
        demo: string
            Filename of pickled results object. If provided, the simulation is not run. Instead, the pickled results
            object is returned.
        """

        start_run_sim_time = time.time()

        # Create and initialize dictionaries containing demand values and link statuses
        if fixed_demands is None:
            self._initialize_simulation()
        else:
            self._initialize_simulation(fixed_demands)

        # Create results object and load general simulation options. 
        results = NetResults()
        results.time = np.arange(0, self._sim_duration_sec+self._report_step_sec, self._report_step_sec)

        # Create sets for storing closed links
        links_closed_by_controls = set([]) # Set of links that are closed by conditional or time controls
        pumps_closed_by_outage = set([]) # Set of pumps closed by pump outage times provided by user
        links_closed_by_tank_controls = set([])  # Set of pipes closed when tank level goes below min
        closed_check_valves = set([]) # Set of closed check valves

        # Create solver instance
        opt = SolverFactory(solver)
        # Set solver options
        for key, val in solver_options.iteritems():
            opt.options[key]=val
        opt.options['bound_relax_factor'] = 0.0 # This is necessary to prevent pump flow from becoming slightly -ve.
                                                # Since it is raised to a fractional power.

        ######### MAIN SIMULATION LOOP ###############
        # Initialize counters and flags
        t = 0 # timestep
        step_iter = 0 # trial
        instance = None
        valve_status_changed = False
        first_timestep = True
        start_main_loop_time = time.time()
        self.prep_time_before_main_loop = start_main_loop_time - start_run_sim_time
        while t < self._n_timesteps and step_iter < self._max_step_iter:
            if step_iter == 0:
                start_step_time = time.time()

            # HACK to work around circular references here and the
            # fact that 2.7.10 does not appear to collect memory as
            # frequently.  This is harmless, except for the small
            # amount of time it takes to run the GC.
            #gc.collect()

            if t == 0:
                first_timestep = True
                last_tank_head = {} # Tank head at previous timestep
                for tank_name, tank in self._wn.nodes(Tank):
                    last_tank_head[tank_name] = tank.elevation + tank.init_level
                last_tank_net_inflows = None # Tank net inflows at previous timestep
            else:
                first_timestep = False

            # Get demands at current timestep
            current_demands = {n_name: self._demand_dict[n_name, t] for n_name, n in self._wn.nodes(Junction)}

            # Pre-solve controls
            # These controls depend on the results of the previous timestep,
            # and they do not require a resolve if activated
            if step_iter == 0: # the step_iter == 0 is very important so that the post-solve controls are not overwritten
                if first_timestep:
                    self._apply_controls(None, first_timestep, links_closed_by_controls, t) # For the first timestep, we only apply time controls and None is passed in place of last_instance_results
                else:
                    self._apply_controls(last_instance_results, first_timestep, links_closed_by_controls, t) # time controls and conditional controls
                if self._pump_outage:
                    self._apply_pump_outage(pumps_closed_by_outage, t) # pump outage controls
                if not first_timestep: 
                    self._close_all_links_for_tanks_below_min_head(last_instance_results, links_closed_by_tank_controls) # controls for closing links if the tank level gets too low or opening links if the tank level goes back above the minimum head

            # Create a copy of the links closed during the last timestep
            # This is used for the method _fully_open_links_with_inactive_leaks
            if not first_timestep:
                links_closed_last_step = links_closed

            # Combine list of closed links. If a link is closed by any
            # of these sets, then the link is closed no matter what
            # the other sets say.
            links_closed = links_closed_by_controls.union(
                           links_closed_by_tank_controls.union(
                           closed_check_valves))

            timedelta = results.time[t]
            if step_iter == 0:
                #pass
                print "Running Hydraulic Simulation at time", timedelta, " ... "
            else:
                #pass
                print "\t Trial", str(step_iter+1), "Running Hydraulic Simulation at time", timedelta, " ..."

            # Build the hydraulic constraints at current timestep
            # These constraints do not include valve flow constraints
            start_build_model = time.time()
            model = self._build_hydraulic_model_at_instant(t,
                                                           last_tank_head,
                                                           current_demands,
                                                           first_timestep,
                                                           links_closed,
                                                           pumps_closed_by_outage,
                                                           last_tank_net_inflows,
                                                           modified_hazen_williams)

            # Add constant objective
            model.obj = Objective(expr=1, sense=minimize)
            
            end_build_model = time.time()
            if step_iter == 0:
                self.build_model_time[t] = end_build_model - start_build_model
            else:
                self.build_model_time[t] += end_build_model - start_build_model

            #Create does not need to be called for NLP
            instance = model

            # Initialize instance from the results of previous timestep
            if not first_timestep:
                self._initialize_from_pyomo_results(instance, last_instance_results)

            # Fix variables. This has to be done after the call to _initialize_from_pyomo_results above.
            self._fix_instance_variables(first_timestep, instance, links_closed)

            # Add Pressure Reducing Valve (PRV) constraints based on status
            self._add_valve_constraints(instance)

            # Check for isolated junctions if the simulation is demand
            # driven. If all links connected to a junction are closed,
            # then the head is fixed to the elevation and the
            # constraint requiring the demand to be equal to the
            # requested demand is deactivated.
            if not self.pressure_dependent:
                self._check_for_isolated_junctions(instance, links_closed)

            # Solve the instance and load results
            start_solve_step = time.time()
            pyomo_results = opt.solve(instance, tee=False, keepfiles=False)
            end_solve_step = time.time()
            if step_iter == 0:
                self.solve_step[t] = end_solve_step - start_solve_step
            else:
                self.solve_step[t] += end_solve_step - start_solve_step
            instance.load(pyomo_results)

            # Post-solve controls 
            #
            # These controls depend on the current timestep, and the
            # current timestep needs resolved if they are activated.
            self._check_tank_controls(instance, links_closed_by_tank_controls)
            self._set_check_valves_closed(instance, closed_check_valves) # HEAD pumps are also treated as check valves

            # Raise warning if water is flowing into a reservoir
            self._raise_warning_for_drain_to_reservoir(instance)

            # Combine the sets of closed links into new_links_closed
            # This is used for comparison with links_closed to see if 
            # the timestep needs to be resolved.
            new_links_closed = links_closed_by_controls.union(
                           links_closed_by_tank_controls.union(
                           closed_check_valves))

            # Set valve status based on pyomo results
            if self._wn._num_valves != 0:
                valve_status_changed = self._set_valve_status(instance)

            # Another trial at the same timestep is required if the following conditions are met:
            if valve_status_changed or new_links_closed!=links_closed or pyomo_results.solver.status!=SolverStatus.ok or pyomo_results.solver.termination_condition!=TerminationCondition.optimal:
                step_iter += 1
            else:
                step_iter = 0
                t += 1
                # Load last tank head
                for tank_name, tank in self._wn.nodes(Tank):
                    last_tank_head[tank_name] = instance.head[tank_name].value
                # Load last link flows
                if first_timestep:
                    last_tank_net_inflows = {}
                for tank_name, tank in self._wn.nodes(Tank):
                    last_tank_net_inflows[tank_name] = instance.tank_net_inflow[tank_name].value
                # Load results into self._pyomo_sim_results
                self._append_pyomo_results(instance, timedelta)

                # Copy last instance. Used to manually initialize next timestep.
                last_instance_results = self._read_instance_results(instance)

            if step_iter == self._max_step_iter:
                #if pyomo_results.solver.status!=SolverStatus.ok or pyomo_results.solver.termination_condition!=TerminationCondition.optimal:
                #    self._check_constraint_violation(instance)
                #    instance.pprint()
                #    for node_name, node in self._wn.nodes():
                #        if not isinstance(node, Reservoir):
                #            print node_name,' pressure: ',instance.head[node_name].value - node.elevation
                #    raise RuntimeError('Solver did not converge.')

                raise RuntimeError('Simulation did not converge at timestep ' + str(t) + ' in '+str(self._max_step_iter)+' trials.')

            if step_iter == 0:
                self.time_per_step.append(time.time()-start_step_time)

        ######## END OF MAIN SIMULATION LOOP ##########

        ntimes = len(results.time)  
        nnodes = self._wn.num_nodes()
        nlinks = self._wn.num_links()
        node_names = [name for name, node in self._wn.nodes()]
        link_names = [name for name, link in self._wn.links()]
        
        node_dictonary = {'demand':   self._pyomo_sim_results['node_demand'],
                          'expected_demand':   self._pyomo_sim_results['node_expected_demand'],
                          'head':     self._pyomo_sim_results['node_head'],
                          'pressure': self._pyomo_sim_results['node_pressure'],
                          'leak_flow': self._pyomo_sim_results['leak_flow'],
                          'type':     self._pyomo_sim_results['node_type']}
        for key, value in node_dictonary.iteritems():
            node_dictonary[key] = np.array(value).reshape((ntimes, nnodes))
        results.node = pd.Panel(node_dictonary, major_axis=results.time, minor_axis=node_names)
        
        link_dictonary = {'flowrate': self._pyomo_sim_results['link_flowrate'],
                          'velocity': self._pyomo_sim_results['link_velocity'],
                          'type':     self._pyomo_sim_results['link_type']}
        for key, value in link_dictonary.iteritems():
            link_dictonary[key] = np.array(value).reshape((ntimes, nlinks))
        results.link = pd.Panel(link_dictonary, major_axis=results.time, minor_axis=link_names)
        
        return results

    def _fix_instance_variables(self, first_timestep, instance, links_closed):
        # Fix the head in a reservoir
        for n in instance.reservoirs:
            reservoir_head = self._wn.get_node(n).base_head
            instance.head[n].value = reservoir_head
            instance.head[n].fixed = True
        # Fix the initial head in a Tank
        if first_timestep:
            for n in instance.tanks:
                tank = self._wn.get_node(n)
                tank_initial_head = tank.elevation + tank.init_level
                instance.head[n].value = tank_initial_head
                instance.head[n].fixed = True
        # Set flow to 0 if link is closed
        for l in instance.links:
            if l in links_closed:
                instance.flow[l].fixed = True
                # instance.flow[l].value = self._Qtol/10.0
                instance.flow[l].value = 0.0
            else:
                instance.flow[l].fixed = False

    def _add_valve_constraints(self, model):
        for l in model.valves:
            valve = self._wn.get_link(l)
            start_node = valve.start_node()
            end_node = valve.end_node()
            pressure_setting = valve.base_setting
            status = self._valve_status[l]
            if status == 'CLOSED':
                # model.flow[l].value = self._Qtol/10.0
                model.flow[l].value = 0.0
                model.flow[l].fixed = True
            elif status == 'OPEN':
                diameter = valve.diameter
                # Darcy-Weisbach model for valves
                valve_resistance_coefficient = 0.02 * self._Dw_k * (diameter * 2) / (diameter ** 5)
                setattr(model, 'valve_headloss_' + str(l), Constraint(
                    expr=valve_resistance_coefficient * model.flow[l] ** 2 == model.head[start_node] - model.head[
                        end_node]))
            elif status == 'ACTIVE':
                end_node_obj = self._wn.get_node(end_node)
                model.head[end_node].value = pressure_setting + end_node_obj.elevation
                model.head[end_node].fixed = True
            else:
                raise RuntimeError("Valve Status not recognized.")

    def _append_pyomo_results(self, instance, time):
        """
        Reads pyomo results from a pyomo instance and loads them into
        the pyomo_sim_results dictionary.

        Parameters
        ----------
        instance : Pyomo model instance
            Pyomo instance after instance.load() has been called.
        time : time string
            Current sim time in 'Day HH:MM:SS' format
        """

        # Load link data
        for link_name, link in self._wn.links():
            link_type = self._get_link_type(link_name)
            flowrate = instance.flow[link_name].value
            if isinstance(link, Pipe):
                velocity_l = 4.0*abs(flowrate)/(math.pi*link.diameter**2)
            else:
                velocity_l = 0.0
            self._pyomo_sim_results['link_name'].append(link_name)
            self._pyomo_sim_results['link_type'].append(link_type)
            self._pyomo_sim_results['link_times'].append(time)
            self._pyomo_sim_results['link_velocity'].append(velocity_l)
            self._pyomo_sim_results['link_flowrate'].append(flowrate)

        # Load node data
        for node_name, node in self._wn.nodes():
            node_type = self._get_node_type(node_name)
            head_n = instance.head[node_name].value
            if isinstance(node, Reservoir):
                pressure_n = 0.0
            else:
                pressure_n = (head_n - node.elevation)
            if isinstance(node, Junction):
                demand = instance.demand_actual[node_name].value
                expected_demand = instance.demand_required[node_name]
                if node_name in instance.junctions_with_leaks:
                    leak_flow = instance.junction_leak_demand[node_name].value
                else:
                    leak_flow = 0.0
                #if n=='101' or n=='10':
                #    print n,'  ',head_n, '  ', node.elevation
            elif isinstance(node, Reservoir):
                demand = instance.reservoir_demand[node_name].value
                expected_demand = instance.reservoir_demand[node_name].value
                leak_flow = 0.0
            elif isinstance(node, Tank):
                demand = instance.tank_net_inflow[node_name].value
                expected_demand = instance.tank_net_inflow[node_name].value
                if node_name in instance.tanks_with_leaks:
                    leak_flow = instance.tank_leak_demand[node_name].value
                else:
                    leak_flow = 0.0
            else:
                demand = 0.0
                expected_demand = 0.0
                leak_flow = 0.0

            #if head_n < -1e4:
            #    pressure_n = 0.0
            #    head_n = node.elevation
            self._pyomo_sim_results['node_name'].append(node_name)
            self._pyomo_sim_results['node_type'].append(node_type)
            self._pyomo_sim_results['node_times'].append(time)
            self._pyomo_sim_results['node_head'].append(head_n)
            self._pyomo_sim_results['node_demand'].append(demand)
            self._pyomo_sim_results['node_expected_demand'].append(expected_demand)
            self._pyomo_sim_results['node_pressure'].append(pressure_n)
            self._pyomo_sim_results['leak_flow'].append(leak_flow)

    def _apply_controls(self, instance, first_timestep, links_closed_by_controls, t):

        # Activate/deactivate time controls
        # From self._link_status,
        #     0 means close the link
        #     1 means open the link
        #     2 means take no action
        for link_name, status in self._link_status.iteritems():
            if status[t] == 0:
                links_closed_by_controls.add(link_name)
            elif status[t] == 1:
                links_closed_by_controls.discard(link_name)
            elif status[t] == 2:
                continue
            else:
                raise RuntimeError('This appears to be a bug. Please report this error tot he developers.')

        # Check the conditional controls. If the conditional controls
        # say that a pipe should be opened or closed, it overrides the 
        # time controls.

        # Conditional controls are based on the results from the previous
        # timestep, so they are not applied during the first timestep.
        if not first_timestep:
            for link_name_k, value in self._wn.conditional_controls.iteritems():
                open_above = value['open_above']
	        open_below = value['open_below']
	        closed_above = value['closed_above']
	        closed_below = value['closed_below']
	
                # Tank levels are calculated from the flow rates of the previous timestep. Therefore,
                # if a conditional control is based on a tank level, then we calculate the tank level
                # before solving the current timestep. If the threshold will be crossed, then we open 
                # or close the specified links.

                # If the conditional control is based on a junction pressure, then we open or close
                # the specified pipe based on the results from the previous timestep.

	        # If link is closed and the node level/pressure goes below threshold, then open the link
	        for i in open_below:
	            node_name_i = i[0]
	            value_i = i[1]
	            node_i = self._wn.get_node(node_name_i)
                    if isinstance(node_i, Tank):
                        next_head_in_tank = self.predict_next_tank_head(node_name_i, instance)
                        node_value = next_head_in_tank - node_i.elevation
                    else:
                        node_value = instance['head'][node_name_i] - node_i.elevation
	            if node_value <= value_i:
                        links_closed_by_controls.discard(link_name_k)
	
	        # If link is open and the node level/pressure goes above threshold, then close the link
	        for i in closed_above:
	            node_name_i = i[0]
	            value_i = i[1]
	            node_i = self._wn.get_node(node_name_i)
                    if isinstance(node_i, Tank):
                        next_head_in_tank = self.predict_next_tank_head(node_name_i, instance)
                        node_value = next_head_in_tank - node_i.elevation
                    else:
                        node_value = instance['head'][node_name_i] - node_i.elevation
	            if node_value >= value_i:
	                links_closed_by_controls.add(link_name_k)
	
	        # If link is closed and node level/pressure goes above threshold, then open the link
	        for i in open_above:
	            node_name_i = i[0]
	            value_i = i[1]
	            node_i = self._wn.get_node(node_name_i)
                    if isinstance(node_i, Tank):
                        next_head_in_tank = self.predict_next_tank_head(node_name_i, instance)
                        node_value = next_head_in_tank - node_i.elevation
                    else:
                        node_value = instance['head'][node_name_i] - node_i.elevation
	            if node_value >= value_i:
                        links_closed_by_controls.discard(link_name_k)
	
	        # If link is open and the node level/pressure goes below threshold, then close the link
	        for i in closed_below:
	            node_name_i = i[0]
	            value_i = i[1]
	            node_i = self._wn.get_node(node_name_i)
                    if isinstance(node_i, Tank):
                        next_head_in_tank = self.predict_next_tank_head(node_name_i, instance)
                        node_value = next_head_in_tank - node_i.elevation
                    else:
                        node_value = instance['head'][node_name_i] - node_i.elevation
	            if node_value <= value_i:
	                links_closed_by_controls.add(link_name_k)

    def _override_tank_controls(self, links_closed_by_tank_controls, pumps_closed_by_outage):
        #links_closed_by_tank_controls.clear()
        for pump_name, pump in self._wn.links(Pump):
            if pump_name in pumps_closed_by_outage and pump_name in self._wn.conditional_controls.keys():
                #print pump_name , "opened, tanks filled by this pump are: ",  self._wn.conditional_controls[pump_name]['open_below']
                tank_filled_by_pump = self._wn.conditional_controls[pump_name]['open_below'][0][0]
                #print "\t", "Opening link next to tank: ", tank_filled_by_pump
                link_next_to_tank = self._tank_controls[tank_filled_by_pump]['link_name']
                if link_next_to_tank in links_closed_by_tank_controls:
                    #print "\t\t", "Link opened: ", link_next_to_tank
                    links_closed_by_tank_controls.remove(link_next_to_tank)

    def _apply_pump_outage(self, pumps_closed_by_outage, t):
        # If the time is within the time period of the pump outage,
        # then add the pump name to the pumps_closed_by_outage set.

        time_t = self._hydraulic_step_sec*t

        for pump_name, time_tuple in self._pump_outage.iteritems():
            if time_t >= time_tuple[0] and time_t <= time_tuple[1]:
                pumps_closed_by_outage.add(pump_name)
            else:
                pumps_closed_by_outage.discard(pump_name)

    def _close_all_links_for_tanks_below_min_head(self, instance, links_closed_by_tank_controls):
        """
        If the tank head goes below min_head, then close all links
        connected to the tank except check valves and pumps that can
        only allow flow into the tank.
        
        If the tank head goes above mind_head, open all the links
        connected to the tank.
        
        Tank levels, are calculated from the flow rates of the
        previous timestep, so this method uses the tank level for the
        next timestep.
        """
 
        for tank_name, control_info in self._tank_controls.iteritems():
            head_in_tank = instance['head'][tank_name]
            next_head_in_tank = self.predict_next_tank_head(tank_name, instance)
            min_tank_head = control_info['min_head']
            """
            Only close the links if the tank level crosses the
            threshold.  We do not close the links if the level was and
            is below the threshold. The reason for this is that a link
            may get opened in the post-solve controls
            (_check_tank_controls), and we do not want to overwrite
            that.
            """
            if next_head_in_tank <= min_tank_head and head_in_tank >= min_tank_head:
                for link_name in control_info['link_names']:
                    link = self._wn.get_link(link_name)
                    if isinstance(link, Valve):
                        raise NotImplementedError('Placing valves directly next to tanks is not yet supported.'+
                                                  'Try placing a dummy pipe and junction between the tank and valve.')
                    if isinstance(link, Pump) or link.get_base_status() == LinkStatus.cv:
                        if link.end_node() == tank_name:
                            continue
                        else:
                            links_closed_by_tank_controls.add(link_name)
                    else:
                        links_closed_by_tank_controls.add(link_name)
            elif next_head_in_tank >= min_tank_head and head_in_tank <= min_tank_head:
                for link_name in control_info['link_names']:
                    links_closed_by_tank_controls.discard(link_name)
                
    def _check_tank_controls(self, instance, links_closed_by_tank_controls):
        """
        Generally, if a tank level drops below its minimum, then the
        links connected to the tank get closed. The idea here is to
        open links that would allow flow into the tank if the link
        were open. This is done by comparing the head at the node next
        to the tank to the head in the tank. Also, if an open link is
        allowing water to flow out of a tank below its minimum level,
        then that link is closed.
        """
        for tank_name, control_info in self._tank_controls.iteritems():
            head_in_tank = instance.head[tank_name].value
            min_tank_head = control_info['min_head']
            if head_in_tank <= min_tank_head:
                link_names = control_info['link_names']
                node_names = control_info['node_names']
                for i in range(len(link_names)):
                    link_name = link_names[i]
                    node_name = node_names[i]
                    if link_name not in links_closed_by_tank_controls: # the link is currently open
                        if instance.head[node_name].value + self._Htol <= instance.head[tank_name].value:
                            links_closed_by_tank_controls.add(link_name)
                        link = self._wn.get_link(link_name)
                        start_node_name = link.start_node()
                        end_node_name = link.end_node()
                        if start_node_name == tank_name:
                            if instance.flow[link_name].value >= 0.0:
                                links_closed_by_tank_controls.add(link_name)
                        elif end_node_name == tank_name:
                            if instance.flow[link_name].value <= 0.0:
                                links_closed_by_tank_controls.add(link_name)
                    else: # the link is currently closed
                        if instance.head[node_name].value >= instance.head[tank_name].value + self._Htol:
                            links_closed_by_tank_controls.discard(link_name)

    def predict_next_tank_head(self,tank_name, instance):
        tank_net_inflow = 0.0
        tank = self._wn.get_node(tank_name)
        for l in self._wn.get_links_for_node(tank_name):
            link = self._wn.get_link(l)
            if link.start_node() == tank_name:
                tank_net_inflow -= instance['flow'][l]
            elif link.end_node() == tank_name:
                tank_net_inflow += instance['flow'][l]
            else:
                raise RuntimeError('Node link is neither start nor end node.')
        new_tank_head = instance['head'][tank_name] + tank_net_inflow*self._hydraulic_step_sec*4.0/(math.pi*tank.diameter**2)
        return new_tank_head

    def _set_valve_status(self, instance):
        """
        Change status of the valves based on the results obtained from pyomo
        simulation.

        Parameters
        ----------
        instance : pyomo model instance

        Returns
        -------
        valve_status_change : bool
            True if there was a change in valve status, False otherwise.

        """
        valve_status_changed = False
        # See EPANET2 Manual pg 191 for the description of the logic used below
        for valve_name in instance.valves:
            status = self._valve_status[valve_name]
            valve = self._wn.get_link(valve_name)
            pressure_setting = valve.base_setting
            start_node = valve.start_node()
            start_node_elevation = self._wn.get_node(start_node).elevation
            end_node = valve.end_node()

            head_sp = pressure_setting + start_node_elevation
            if status == 'ACTIVE':
                if instance.flow[valve_name].value < -self._Qtol:
                    #print "----- Valve ", valve_name, " closed:  ", instance.flow[valve_name].value, " < ", -self._Qtol
                    self._valve_status[valve_name] = 'CLOSED'
                    valve_status_changed = True
                elif instance.head[start_node].value < head_sp - self._Htol:
                    #print "----- Valve ", valve_name, " opened:  ", instance.head[start_node].value, " < ", head_sp - self._Htol
                    self._valve_status[valve_name] = 'OPEN'
                    valve_status_changed = True
            elif status == 'OPEN':
                if instance.flow[valve_name].value < -self._Qtol:
                    #print "----- Valve ", valve_name, " closed:  ", instance.flow[valve_name].value, " < ", -self._Qtol
                    self._valve_status[valve_name] = 'CLOSED'
                    valve_status_changed = True
                elif instance.head[start_node].value > head_sp + self._Htol:
                    #print "----- Valve ", valve_name, " active:  ", instance.head[start_node].value, " > ", head_sp + self._Htol
                    self._valve_status[valve_name] = 'ACTIVE'
                    valve_status_changed = True
            elif status == 'CLOSED':
                if instance.head[start_node].value > instance.head[end_node].value + self._Htol \
                    and instance.head[start_node].value < head_sp - self._Htol:
                    #print "----- Valve ", valve_name, " opened: from closed"
                    self._valve_status[valve_name] = 'OPEN'
                    valve_status_changed = True
                elif instance.head[start_node].value > instance.head[end_node].value + self._Htol \
                    and instance.head[end_node].value < head_sp - self._Htol:
                    #print "----- Valve ", valve_name, " active from closed"
                    self._valve_status[valve_name] = 'ACTIVE'
                    valve_status_changed = True
        return valve_status_changed

    def _set_check_valves_closed(self, instance, closed_check_valves):
        # See EPANET2 Manual pg 191 for the description of the logic used below
        # Also, treat HEAD pumps as check valves because the lower bound on the flow rate is not set to 0.0
        for pipe_name in self._wn._check_valves:
            pipe = self._wn.get_link(pipe_name)
            start_node = pipe.start_node()
            end_node = pipe.end_node()
            headloss = instance.head[start_node].value - instance.head[end_node].value
            if abs(headloss) > self._Htol:
                if headloss < -self._Htol:
                    closed_check_valves.add(pipe_name)
                elif instance.flow[pipe_name].value < -self._Qtol:
                    closed_check_valves.add(pipe_name)
                else:
                    closed_check_valves.discard(pipe_name)
            elif instance.flow[pipe_name].value < -self._Qtol:
                closed_check_valves.add(pipe_name)
        for pump_name, pump in self._wn.links(Pump):
            if pump.info_type == 'HEAD':
                start_node = pump.start_node()
                end_node = pump.end_node()
                A, B, C = pump.get_head_curve_coefficients()
                headloss = instance.head[start_node].value + A - instance.head[end_node].value
                if abs(headloss) > self._Htol/10.0:
                    if headloss < -self._Htol/10.0:
                        closed_check_valves.add(pump_name)
                    elif instance.flow[pump_name].value < -self._Qtol/10.0:
                        closed_check_valves.add(pump_name)
                    else:
                        closed_check_valves.discard(pump_name)
                elif instance.flow[pump_name].value < -self._Qtol/10.0:
                    closed_check_valves.add(pump_name)

    def _close_low_suction_pressure_pumps(self, instance, pumps_closed_by_low_suction_pressure, pumps_closed_by_outage):
        for pump_name in instance.pumps:
            pump = self._wn.get_link(pump_name)
            start_node_name = pump.start_node()
            start_node = self._wn.get_node(start_node_name)
            if isinstance(start_node, Reservoir):
                continue
            if (instance.head[start_node_name].value - start_node.elevation) <= self._Htol:
                if pump_name not in pumps_closed_by_outage:
                    pumps_closed_by_low_suction_pressure.add(pump_name)
            elif (instance.head[start_node_name].value - start_node.elevation) >= 1.0:
                pumps_closed_by_low_suction_pressure.discard(pump_name)
        for pump_name in pumps_closed_by_outage:
            pumps_closed_by_low_suction_pressure.discard(pump_name)

    def _check_constraint_violation(self, instance):
        constraint_names = set([])
        for (constraint_name, idx, con) in instance.active_component_data(Constraint, descend_into=True, sort=True):
            constraint_names.add(constraint_name)
        for constraint_name in constraint_names:
            con = getattr(instance, constraint_name)
            for constraint_key in con.keys():
                con_value = value(con[constraint_key].body)
                con_lower = value(con[constraint_key].lower)
                con_upper = value(con[constraint_key].upper)
                if (con_lower - con_value) >= 1.0e-5 or (con_value - con_upper) >= 1.0e-5:
                    print constraint_name,'[',constraint_key,']',' is not satisfied:'
                    print 'lower: ',con_lower, '\t body: ',con_value,'\t upper: ',con_upper 
                    print 'lower: ',con[constraint_key].lower, '\t body: ',con[constraint_key].body,'\t upper: ',con[constraint_key].upper 

    def _raise_warning_for_drain_to_reservoir(self, instance):
        """
        Raise a warning if water is flowing into a reservoir. Suggest
        the use of a check valve.
        """

        for link_name, reservoir_name in self._reservoir_links.iteritems():
            link = self._wn.get_link(link_name)
            start_node_name = link.start_node()
            end_node_name = link.end_node()

            if start_node_name == reservoir_name:
                if instance.flow[link_name].value <= -self._Qtol:
                    warnings.warn('Water is flowing into reservoir '+start_node_name+'. \n'
                                  'If you do not want this to happen, consider adding a \n'
                                  'check valve to the pipe connected to the reservoir.')
            elif end_node_name == reservoir_name:
                if instance.flow[link_name].value >= self._Qtol:
                    warnings.warn('Water is flowing into reservoir '+end_node_name+'. \n'
                                  'If you do not want this to happen, consider adding a \n'
                                  'check valve to the pipe connected to the reservoir.')

    def _check_for_isolated_junctions(self, instance, links_closed):
        """
        Check for isolated junctions. If all links connected to a
        junction are closed, then the head is fixed to the elevation
        and the constraint for that junction requiring the demand to
        be equal to the requested demand is deactivated.

        If all of the links connected to a junction are are closed,
        and the simulation is demand driven, then the junction head is
        a variable that does not appear in any constraints and Ipopt
        throws a too few degrees of freedom error. To fix this
        problem, we added the _check_for_isolated_junctions
        method. 
        """

        for junction_name in instance.junctions:
            junction = self._wn.get_node(junction_name)
            connected_links = self._wn.get_links_for_node(junction_name)
            isolated = True
            for link_name in connected_links:
                if link_name not in links_closed:
                    isolated = False
            if isolated:
                instance.head[junction_name] = junction.elevation
                instance.head[junction_name].fixed = True
                instance.pressure_driven_demand[junction_name].deactivate()
