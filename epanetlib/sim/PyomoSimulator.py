"""
QUESTIONS
"""

"""
TODO
1. Use in_edges and out_edges to write node balances on the pyomo model.
2. Use reporting timestep when creating the pyomo results object.
3. Test behaviour of check valves. We may require a minimum of two trials at every timestep.
4. Check for negative pressure at leak node
5. Double check units of leak model
6. Leak model assumes all pressures are guage
7. Resolve first timestep/trial if conditional controls are not satisfied.
8. Check self._n_timesteps in _initialize_simulation
9. Check _apply_conditional_controls
10. In _build_hydraulic_model_at_instant, when setting constraints for head gain for pumps with outtage, why is headloss 0 if modified_hazen_williams is true?
11. Rewrite controls
12. Try out alternative leak implementation: have demand come out of existing nodes
13. Generalize tank controls for multiple pipes connected to tanks
14. Fix the PDD smoothing so that pressure is not negative when demand is 0
15. Update _apply_tank_controls since we now calculate tank levels based on flowrates from the previous timestep.
16. Why override time controls at the end of _apply_tank_controls?
17. Put in a check for negative pump head gain
18. Consider flowrates in L/s to reduce solve time
19. What happens to a node pressure if all links connected to that node are closed (actually closed, not just 0 flow)?
20. Think about controls in context of multiple trials for a single timestep
21. Is the pump low flow problem a low flow problem or a low suction pressure problem or both?
22. Currently, pumps closed for low flow never open back up. Fix this.
"""

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

import cProfile

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
Class for keeping approximation functions in a single place 
and avoid code duplications. Should be located in a better place
This is just a temporal implementation
"""
class ApproxFunctions():

    def __init__(self):
        self.q1 = 0.00349347323944
        self.q2 = 0.00549347323944
    # The Hazen-Williams headloss curve is slightly modified to improve solution time.
    # The three functions defines below - f1, f2, Px - are used to ensure that the Jacobian
    # does not go to 0 close to zero flow.
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


    def __init__(self, wn, PD_or_DD='DEMAND DRIVEN'):
        """
        Pyomo simulator class.

        Parameters
        ----------
        wn : Water Network Model
            A water network model.

        PD_or_DD: string, specifies whether the simulation will be demand driven or pressure driven
                  Options are 'DEMAND DRIVEN' or 'PRESSURE DRIVEN'

        """
        WaterNetworkSimulator.__init__(self, wn, PD_or_DD)

        # Global constants
        self._Hw_k = 10.666829500036352 # Hazen-Williams resistance coefficient in SI units = 4.727 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.
        self._Dw_k = 0.0826 # Darcy-Weisbach constant in SI units = 0.0252 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.
        self._Htol = 0.00015 # Head tolerance in meters.
        self._Qtol = 2.8e-5 # Flow tolerance in m^3/s.
        self._pump_zero_flow_tol = 2.8e-11 # Pump is closed below this flow in m^3/s
        self._g = 9.81 # Acceleration due to gravity
        self._slope_of_PDD_curve = 1e-11 # The flat lines in the PDD model are provided a small slope for numerical stability
        self._pdd_smoothing_delta = 0.1 # Tightness of polynomial used to smooth sharp changes in PDD model.

        self._n_timesteps = 0 # Number of hydraulic timesteps
        self._demand_dict = {} # demand dictionary
        self._link_status = {} # dictionary of link statuses
        self._valve_status = {} # dictionary of valve statuses

        self._initialize_results_dict()
        self._max_step_iter = 10 # maximum number of newton solves at each timestep.
                                 # model is resolved when a valve status changes.


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
        self._link_status = {}
        for l, link in self._wn.links():
            status_l = []
            for t in xrange(self._n_timesteps):
                time_sec = t * self._hydraulic_step_sec
                status_l_t = self.is_link_open(l, time_sec)
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
        self._pyomo_sim_results['link_name'] = []
        self._pyomo_sim_results['link_type'] = []
        self._pyomo_sim_results['link_times'] = []
        self._pyomo_sim_results['link_velocity'] = []
        self._pyomo_sim_results['link_flowrate'] = []

    def _initialize_from_pyomo_results(self, instance, last_instance):

        for l in instance.links:
            if abs(last_instance.flow[l].value) < self._Qtol:
                instance.flow[l].value = 100*self._Qtol
            else:
                if l in instance.pumps and last_instance.flow[l].value < -self._Qtol:
                    instance.flow[l].value = 100*self._Qtol
                else:
                    instance.flow[l].value = last_instance.flow[l].value + self._Qtol

        for n in instance.nodes:
            instance.head[n].value = last_instance.head[n].value
            if n in instance.junctions:
                junction = self._wn.get_node(n)
                if self._pressure_driven:
                    if instance.head[n].value - junction.elevation <= junction.P0:
                        instance.demand_actual[n] = 100*self._Qtol
                    else:
                        instance.demand_actual[n] = abs(instance.demand_actual[n].value) + self._Qtol
                else:
                    instance.demand_actual[n] = abs(instance.demand_actual[n].value) + self._Qtol

        for r in instance.reservoirs:
            if abs(last_instance.reservoir_demand[r].value) < self._Qtol:
                instance.reservoir_demand[r].value = 100*self._Qtol
            else:
                instance.reservoir_demand[r].value = last_instance.reservoir_demand[r].value + self._Qtol
        for t in instance.tanks:
            if abs(last_instance.tank_net_inflow[t].value) < self._Qtol:
                instance.tank_net_inflow[t].value = 100*self._Qtol
            else:
                instance.tank_net_inflow[t].value = last_instance.tank_net_inflow[t].value + self._Qtol


    def _fit_smoothing_curve(self):
        delta = 0.1
        smoothing_points = []
        # Defining Line 1
        a1 = 1e-6
        b1 = 0

        def L1(x):
            return a1*x + b1

        # Defining Line 2
        a2 = 1/(self._PF - self._P0)
        b2 = -1*(self._P0/(self._PF - self._P0))

        def L2(x):
            return a2*x + b2

        # Define Line 3
        a3 = 0
        b3 = 1

        def L3(x):
            return a3*x + b3

        def A(x_1, x_2):
            return np.array([[x_1**3, x_1**2, x_1, 1],
                            [x_2**3, x_2**2, x_2, 1],
                            [3*x_1**2, 2*x_1,  1, 0],
                            [3*x_2**2, 2*x_2,  1, 0]])

        # Calculating point of intersection of Line 1 & 2
        x_int_12 = (b2-b1)/(a1-a2)
        # Calculating point of intersection of Line 2 & 3
        x_int_13 = (b2-b3)/(a3-a2)

        #print x_int_12
        #print x_int_13

        assert x_int_12 < x_int_13, "Point of intersection of PDD curves are not in the right order. "

        x_gap = x_int_13 - x_int_12

        # If P0 in not close to zero, get parameters for first polynomial
        if x_int_12 > self._Htol:
            x1 = x_int_12 - x_int_12*delta
            y1 = L1(x1)
            x2 = x_int_12 + x_gap*delta
            y2 = L2(x2)
            #print x1
            #print x2
            # Creating a linear system Ac = rhs, and solving it
            # to get parameters of the 3rd order polynomial
            A1 = A(x1, x2)
            #print A1
            rhs1 = np.array([y1, y2, a1, a2])
            #print rhs1
            c1 = np.linalg.solve(A1, rhs1)
            #print c1
            self._pdd_smoothing_polynomial_left = list(c1)
            smoothing_points.append(x1)
            smoothing_points.append(x2)
            #print self._pdd_smoothing_polynomial_left

        # Get parameters for the second polynomial
        x3 = x_int_13 - x_gap*delta
        y3 = L2(x3)
        x4 = x_int_13 + x_gap*delta
        y4 = L3(x4)
        print x3, y3, x4, y4
        A2 = A(x3, x4)
        print A2
        rhs2 = np.array([y3, y4, a2, a3])
        print rhs2
        c2 = np.linalg.solve(A2, rhs2)
        print c2
        self._pdd_smoothing_polynomial_right = list(c2)
        smoothing_points.append(x3)
        smoothing_points.append(x4)
        print self._pdd_smoothing_polynomial_left
        print self._pdd_smoothing_polynomial_right


        return smoothing_points

    def _build_hydraulic_model_at_instant(self,
                                         last_tank_head,
                                         nodal_demands,
                                         first_timestep,
                                         links_closed,
                                         pumps_closed_by_outage,
                                         last_link_flows,
                                         modified_hazen_williams=True):
        """
        Build hydraulic constraints at a particular time instance.

        Parameters
        ----------
        last_tank_head : dict of string: float
            Dictionary containing tank names and their respective head at the last timestep.
        nodal_demands : dict of string: float
            Dictionary containing junction names and their respective respective demand at current timestep.
        first_timestep : bool
            Flag indicating wheather its the first timestep
        links_closed : list of strings
            Name of links that are closed.
        pumps_closed_by_outage : list of strings
            Name of pumps closed due to a power outage

        Other Parameters
        -------------------
        modified_hazen_williams : bool
            Flag to use a slightly modified version of Hazen-Williams headloss
            equation for better stability
        """

        t0 = time.time()

        # for the approximation of hazen williams equation
        approximator = ApproxFunctions()

        # Currently this function is being called for every node at every time step.
        # TODO : Refactor pressure_dependent_demand_linear so that its created only once for the entire simulation.
        def pressure_dependent_demand_nl(full_demand, p, PF, P0):
            # Pressure driven demand equation
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


        # Currently this function is being called for every node at every time step.
        # TODO : Refactor pressure_dependent_demand_linear so that its created only once for the entire simulation.
        def pressure_dependent_demand_linear(full_demand, p, PF, P0):

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
            delta = 1.0e-8
            L1_slope = -1.0e-11
            x1 = 1.0e-8
            x2 = 2.0*x1
            def L1(q,A):
                return L1_slope*q+A
            def pump_curve(q,A,B,C):
                return A-B*q**C
            def get_rhs(A,B,C):
                return np.matrix([[L1_slope*x1+A],[A-B*x2**C],[L1_slope],[-B*C*x2**(C-1.0)]])

            coeff_matrix = np.matrix([[x1**3, x1**2, x1, 1.0],[x2**3, x2**2, x2, 1.0],[3*x1**2, 2*x1, 1.0, 0.0],[3*x2**2, 2*x2, 1.0, 0.0]])
            poly_coeff = np.linalg.solve(coeff_matrix, get_rhs(A,B,C))

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
            delta = 1.0e-4
            L1_slope = 1.0e-11
            x1 = 0.0
            x2 = delta
            c = L1_slope
            d = 0.0
            def L1(p):
                return L1_slope*p
            def leak_model(p, Cd, A):
                return Cd*A*math.sqrt(2.0*self._g)*p**0.5
            def get_rhs(x, Cd, A):
                return np.matrix([[Cd*A*math.sqrt(2.0*self._g)*x**0.5-c*x-d],[0.5*Cd*A*math.sqrt(2.0*self._g)*x**(-0.5)-c]])

            coeff_matrix = np.matrix([[x2**3.0, x2**2.0],[3*x2**2.0, 2*x2]])

            poly_coeff = np.linalg.solve(coeff_matrix, get_rhs(x2, Cd, A))
            a = float(poly_coeff[0][0])
            b = float(poly_coeff[1][0])

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
        model.leaks = Set(initialize = [n for n, N in wn.nodes(Leak)])
        model.reservoirs = Set(initialize=[n for n, N in wn.nodes(Reservoir)])
        # LINKS
        model.links = Set(initialize=[name for name, link in wn.links()])
        model.pumps = Set(initialize=[l for l, L in wn.links(Pump)])
        model.valves = Set(initialize=[l for l, L in wn.links(Valve)])
        model.pipes = Set(initialize=[l for l, L in wn.links(Pipe)])

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
            if l in model.pumps and l not in pumps_closed_by_outage:
                return (0.0, None)
            else:
                return (None, None)
        model.flow = Var(model.links, within=Reals, initialize=flow_init_rule, bounds=flow_bounds_rule)

        def init_head_rule(model, n):
            node = wn.get_node(n)
            if n in model.junctions:
                if self._pressure_driven:
                    return node.elevation + node.PF
                else:
                    return node.elevation
            elif n in model.tanks:
                return node.elevation
            elif n in model.leaks:
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

        def init_leak_demand_rule(model,n):
            if n in self._active_leaks:
                node = wn.get_node(n)
                return node.leak_discharge_coeff*node.area*math.sqrt(2*self._g)*math.sqrt(model.head[n]-node.elevation)
            else:
                return 0.0
        model.leak_demand = Var(model.leaks, within = Reals, initialize=init_leak_demand_rule, bounds = (None, None))

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
                    self._constraint_names.add('pipe_headloss_'+str(l))
                else:
                    setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=pipe_resistance_coeff*model.flow[l]*(abs(model.flow[l]))**0.852 == model.head[start_node] - model.head[end_node]))
                    self._constraint_names.add('pipe_headloss_'+str(l))

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
                        setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=model.head[start_node] - model.head[end_node] == 0))
                        self._constraint_names.add('pipe_headloss_'+str(l))
                    else:
                        setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=pipe_resistance_coeff*model.flow[l]*(abs(model.flow[l]))**0.852 == model.head[start_node] - model.head[end_node]))
                        self._constraint_names.add('pipe_headloss_'+str(l))
                else:
                    if pump.info_type == 'HEAD':
                        A, B, C = pump.get_head_curve_coefficients()
                        if l not in links_closed:
                            setattr(model, 'pump_negative_headloss_'+str(l), Constraint(expr=model.head[end_node] - model.head[start_node] == (modified_pump_curve(model.flow[l],A,B,C))))
                            self._constraint_names.add('pump_negative_headloss_'+str(l))
                    elif pump.info_type == 'POWER':
                        if l not in links_closed:
                            setattr(model, 'pump_negative_headloss_'+str(l), Constraint(expr=(model.head[start_node] - model.head[end_node])*model.flow[l]*self._g*1000.0 == -pump.power))
                            self._constraint_names.add('pump_negative_headloss_'+str(l))
                    else:
                        raise RuntimeError('Pump info type not recognised. ' + l)

        # Mass Balance
        def node_mass_balance_rule(model, n):
            node = wn.get_node(n)
            if isinstance(node, Tank) and not first_timestep:
                expr = 0
                for l in wn.get_links_for_node(n):
                    link = wn.get_link(l)
                    if link.start_node() == n:
                        expr -= last_link_flows[l]
                    elif link.end_node() == n:
                        expr += last_link_flows[l]
                    else:
                        raise RuntimeError('Node link is neither start nor end node.')
            else:
                expr = 0
                for l in wn.get_links_for_node(n):
                    link = wn.get_link(l)
                    if link.start_node() == n:
                        expr -= model.flow[l]
                    elif link.end_node() == n:
                        expr += model.flow[l]
                    else:
                        raise RuntimeError('Node link is neither start nor end node.')
            if isinstance(node, Junction):
                return expr == model.demand_actual[n]
                #return expr == model.demand_required[n]
            elif isinstance(node, Tank):
                return expr == model.tank_net_inflow[n]
            elif isinstance(node, Reservoir):
                return expr == model.reservoir_demand[n]
            elif isinstance(node, Leak):
                return expr == model.leak_demand[n]
        model.node_mass_balance = Constraint(model.nodes, rule=node_mass_balance_rule)
        self._constraint_names.add('node_mass_balance')


        def tank_dynamics_rule(model, n):
            if first_timestep:
                return Constraint.Skip
            else:
                tank = wn.get_node(n)
                return (model.tank_net_inflow[n]*model.timestep*4.0)/(math.pi*(tank.diameter**2)) == model.head[n]-last_tank_head[n]
        model.tank_dynamics = Constraint(model.tanks, rule=tank_dynamics_rule)
        self._constraint_names.add('tank_dynamics')

        # Pressure driven demand constraint
        def pressure_driven_demand_rule(model, j):
            junction = wn.get_node(j)
            if model.demand_required[j] == 0.0:
                #return Constraint.Skip
                return model.demand_actual[j] == 0.0 # Using this constraint worked better than fixing this variable.
            else:
                return pressure_dependent_demand_nl(model.demand_required[j], model.head[j]-junction.elevation, junction.PF, junction.P0) == model.demand_actual[j]

        def demand_driven_rule(model, j):
            return model.demand_actual[j] == model.demand_required[j]

        if self._pressure_driven:
            model.pressure_driven_demand = Constraint(model.junctions, rule=pressure_driven_demand_rule)
            self._constraint_names.add('pressure_driven_demand')
        else:
            model.pressure_driven_demand = Constraint(model.junctions, rule=demand_driven_rule)
            self._constraint_names.add('pressure_driven_demand')

        # Leak demand constraint
        def leak_demand_rule(model, n):
            if n in self._active_leaks:
                leak = wn.get_node(n)
                return model.leak_demand[n] == piecewise_pipe_leak_demand(model.head[n]-leak.elevation, leak.leak_discharge_coeff, leak.area)
                #return model.leak_demand[n]**2 == leak.leak_discharge_coeff**2*leak.area**2*2*self._g*(model.head[n]-leak.elevation)
            elif n in self._inactive_leaks:
                return model.leak_demand[n] == 0.0
            else:
                raise RuntimeError('There is a bug.')
        model.leak_demand_con = Constraint(model.leaks, rule=leak_demand_rule)
        self._constraint_names.add('leak_demand_con')

        return model


    def run_sim(self, solver='ipopt', solver_options={}, modified_hazen_williams=True, fixed_demands=None, pandas_result=True):

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
        """

        # Add leak to network
        for leak_name in self._pipes_with_leaks.values():
            self._add_leak_to_wn_object(leak_name)
        self._update_tank_controls_for_leaks()
        self._update_links_next_to_reservoirs_for_leaks()
        self._update_time_controls_for_leaks()
        self._update_conditional_controls_for_leaks()

        # Create and initialize dictionaries containing demand values and link statuses
        if fixed_demands is None:
            self._initialize_simulation()
        else:
            self._initialize_simulation(fixed_demands)

        # Create results object
        results = NetResults()
        results.link = pd.DataFrame(columns=['time', 'link', 'flowrate', 'velocity', 'type'])
        results.node = pd.DataFrame(columns=['time', 'node', 'demand', 'expected_demand', 'head', 'pressure', 'type'])
        results.time = pd.timedelta_range(start='0 minutes',
                                          end=str(self._sim_duration_sec) + ' seconds',
                                          freq=str(self._hydraulic_step_sec/60) + 'min')

        # Load general simulation options into the results object
        self._load_general_results(results)

        # Create sets for storing closed links
        links_closed_by_controls = set([]) # Set of links that are closed by conditional or time controls defined in inp file
        pumps_closed_by_outage = set([]) # Set of pump closed by pump outage times provided by user
        links_closed_by_tank_controls = set([])  # Set of pipes closed when tank level goes below min
        closed_check_valves = set([]) # Set of closed check valves
        links_closed_by_drain_to_reservoir = set([]) # Set of links closed because of reverse flow into the reservoir
        pumps_closed_by_low_suction_pressure = set([]) # set of pumps closed because the suction pressure is low

        # monitor the status of leaks
        self._active_leaks = set([])
        self._inactive_leaks = set([leak_name for leak_name in self._leak_times.keys()])

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
        while t < self._n_timesteps and step_iter < self._max_step_iter:

            self._constraint_names = set([])
            if t == 0:
                first_timestep = True
                last_tank_head = {} # Tank head at previous timestep
                for tank_name, tank in self._wn.nodes(Tank):
                    last_tank_head[tank_name] = tank.elevation + tank.init_level
                last_link_flows = None # Link flowrates at previous timestep
            else:
                first_timestep = False

            # Get demands at current timestep
            current_demands = {n_name: self._demand_dict[n_name, t] for n_name, n in self._wn.nodes(Junction)}

            # activate/deactivate leaks
            for leak_name, leak_time_tuple in self._leak_times.iteritems():
                current_time_sec = t*self._hydraulic_step_sec
                leak_start = leak_time_tuple[0]
                leak_end = leak_time_tuple[1]
                if current_time_sec >= leak_start and current_time_sec < leak_end:
                    if leak_name not in self._active_leaks:
                        self._inactive_leaks.remove(leak_name)
                        self._active_leaks.add(leak_name)
                else:
                    if leak_name in self._active_leaks:
                        self._inactive_leaks.add(leak_name)
                        self._active_leaks.remove(leak_name)

            # Pre-solve controls
            # These controls depend on the results of the previous timestep,
            # and they do not require a resolve if activated
            if first_timestep:
                self._apply_controls(None, first_timestep, links_closed_by_controls, t) # time controls and conditional controls
            else:
                self._apply_controls(last_instance, first_timestep, links_closed_by_controls, t) # time controls and conditional controls
            if self._pump_outage:
                self._apply_pump_outage(pumps_closed_by_outage, t) # pump outage controls
            if not first_timestep and step_iter==0:
                self._close_all_links_for_tanks_below_min_head(last_instance, links_closed_by_tank_controls) # controls for closing links if the tank level gets too low or opening links if the tank level goes back above the minimum head

            # Combine list of closed links
            if not first_timestep:
                links_closed_last_step = links_closed
            links_closed = links_closed_by_drain_to_reservoir.union(
                           links_closed_by_controls.union(
                           links_closed_by_tank_controls.union(
                           closed_check_valves.union(
                           pumps_closed_by_low_suction_pressure))))

            # check that links with inactive leaks were opened properly (if they were opened)
            if not first_timestep:
                self._fully_open_links_with_inactive_leaks(links_closed_last_step, links_closed)

            timedelta = results.time[t]
            if step_iter == 0:
                print "Running Hydraulic Simulation at time", timedelta, " ... "
            else:
                print "\t Trial", str(step_iter+1), "Running Hydraulic Simulation at time", timedelta, " ..."

            #t0 = time.time()
            # Build the hydraulic constraints at current timestep
            # These constraints do not include valve flow constraints
            #print 'links_closed_by_drain_to_reservoir = ',links_closed_by_drain_to_reservoir
            #print 'links_closed_by_controls',links_closed_by_controls
            #print 'links_closed_by_tank_controls',links_closed_by_tank_controls
            #print 'closed_check_valves',closed_check_valves
            #print 'pumps_closed_by_low_suction_pressure',pumps_closed_by_low_suction_pressure
            #print 'links_closed = ',links_closed
            model = self._build_hydraulic_model_at_instant(last_tank_head,
                                                           current_demands,
                                                           first_timestep,
                                                           links_closed,
                                                           pumps_closed_by_outage,
                                                           last_link_flows,
                                                           modified_hazen_williams)
            #print "Total build model time : ", time.time() - t0

            # Add constant objective
            model.obj = Objective(expr=1, sense=minimize)
            #Create does not need to be called for NLP
            instance = model

            # Initialize instance from the results of previous timestep
            if not first_timestep:
                #instance.load(pyomo_results)
                self._initialize_from_pyomo_results(instance, last_instance)

            # Fix variables. This has to be done after the call to _initialize_from_pyomo_results above.
            self._fix_instance_variables(first_timestep, instance, links_closed)

            # Add Pressure Reducing Valve (PRV) constraints based on status
            self._add_valve_constraints(instance)

            # Check for isolated junctions. If all links connected to a junction are closed,
            # then the head is fixed to the elevation, the demand if fixed to 0, and
            # the mass balance for that junction is deactivated
            self._check_for_isolated_junctions(instance, links_closed)

            # Solve the instance and load results
            pyomo_results = opt.solve(instance, tee=False, keepfiles=False)
            instance.load(pyomo_results)
            #CheckInstanceFeasibility(instance, 1e-6)
            #self._check_constraint_violation(instance)

            # Post-solve controls
            # These controls depend on the current timestep,
            # and the current timestep needs resolved if they are activated.
            self._close_links_for_drain_to_reservoir(instance, links_closed_by_drain_to_reservoir)
            self._check_tank_controls(instance, links_closed_by_tank_controls)
            self._close_low_suction_pressure_pumps(instance, pumps_closed_by_low_suction_pressure, pumps_closed_by_outage)
            self._set_check_valves_closed(instance, closed_check_valves)

            #print 'links_closed_by_drain_to_reservoir = ',links_closed_by_drain_to_reservoir
            #print 'links_closed_by_controls',links_closed_by_controls
            #print 'links_closed_by_tank_controls',links_closed_by_tank_controls
            #print 'closed_check_valves',closed_check_valves
            #print 'pumps_closed_by_low_suction_pressure',pumps_closed_by_low_suction_pressure
            new_links_closed = links_closed_by_drain_to_reservoir.union(
                           links_closed_by_controls.union(
                           links_closed_by_tank_controls.union(
                           closed_check_valves.union(
                           pumps_closed_by_low_suction_pressure))))
            #print 'new_links_closed = ',new_links_closed

            # Set valve status based on pyomo results
            if self._wn._num_valves != 0:
                valve_status_changed = self._set_valve_status(instance)

            # Another trial at the same timestep is required if the following conditions are met:
            if valve_status_changed or new_links_closed!=links_closed:
                #print 'valve_status_changed = ',valve_status_changed
                #print 'new_links_closed!=links_closed = ',new_links_closed!=links_closed
                step_iter += 1
            else:
                step_iter = 0
                t += 1
                # Load last tank head
                for tank_name, tank in self._wn.nodes(Tank):
                    last_tank_head[tank_name] = instance.head[tank_name].value
                # Load last link flows
                if first_timestep:
                    last_link_flows = {}
                for link_name, link in self._wn.links():
                    last_link_flows[link_name] = instance.flow[link_name].value
                # Load results into self._pyomo_sim_results
                self._append_pyomo_results(instance, timedelta)

                # Copy last instance. Used to manually initialize next timestep.
                last_instance = copy.deepcopy(instance)

            if step_iter == self._max_step_iter:
                raise RuntimeError('Simulation did not converge at timestep ' + str(t) + ' in '+str(self._max_step_iter)+' trials.')

        ######## END OF MAIN SIMULATION LOOP ##########

        # Save results into the results object
        if pandas_result:
            node_data_frame = pd.DataFrame({'time':     self._pyomo_sim_results['node_times'],
                                            'node':     self._pyomo_sim_results['node_name'],
                                            'demand':   self._pyomo_sim_results['node_demand'],
                                            'expected_demand':   self._pyomo_sim_results['node_expected_demand'],
                                            'head':     self._pyomo_sim_results['node_head'],
                                            'pressure': self._pyomo_sim_results['node_pressure'],
                                            'type':     self._pyomo_sim_results['node_type']})

            node_pivot_table = pd.pivot_table(node_data_frame,
                                              values=['demand', 'expected_demand', 'head', 'pressure', 'type'],
                                              index=['node', 'time'],
                                              aggfunc= lambda x: x)
            results.node = node_pivot_table

            link_data_frame = pd.DataFrame({'time':     self._pyomo_sim_results['link_times'],
                                            'link':     self._pyomo_sim_results['link_name'],
                                            'flowrate': self._pyomo_sim_results['link_flowrate'],
                                            'velocity': self._pyomo_sim_results['link_velocity'],
                                            'type':     self._pyomo_sim_results['link_type']})

            link_pivot_table = pd.pivot_table(link_data_frame,
                                                  values=['flowrate', 'velocity', 'type'],
                                                  index=['link', 'time'],
                                                  aggfunc= lambda x: x)
            results.link = link_pivot_table
        else:
            node_dict = dict()
            node_types = set(self._pyomo_sim_results['node_type'])
            map_properties = dict()
            map_properties['node_demand'] = 'demand'
            map_properties['node_head'] = 'head'
            map_properties['node_pressure'] = 'pressure'
            map_properties['node_expected_demand'] = 'expected_demand'
            N = len(self._pyomo_sim_results['node_name'])
            n_nodes = len(self._wn._nodes.keys())
            hydraulic_time_step = float(copy.deepcopy(self._hydraulic_step_sec))
            T = N/n_nodes
            for node_type in node_types:
                node_dict[node_type] = dict()
                for prop, prop_name in map_properties.iteritems():
                    node_dict[node_type][prop_name] = dict()
                    for i in xrange(n_nodes):
                        node_name = self._pyomo_sim_results['node_name'][i]
                        n_type = self._get_node_type(node_name)
                        if n_type == node_type:
                            node_dict[node_type][prop_name][node_name] = dict()
                            for ts in xrange(T):
                                time_sec = hydraulic_time_step*ts
                                node_dict[node_type][prop_name][node_name][time_sec] = self._pyomo_sim_results[prop][i+n_nodes*ts]

            results.node = node_dict

            link_dict = dict()
            link_types = set(self._pyomo_sim_results['link_type'])
            map_properties = dict()
            map_properties['link_flowrate'] = 'flowrate'
            map_properties['link_velocity'] = 'velocity'
            N = len(self._pyomo_sim_results['link_name'])
            n_links = len(self._wn._links.keys())
            T = N/n_links
            for link_type in link_types:
                link_dict[link_type] = dict()
                for prop, prop_name in map_properties.iteritems():
                    link_dict[link_type][prop_name] = dict()
                    for i in xrange(n_links):
                        link_name = self._pyomo_sim_results['link_name'][i]
                        l_type = self._get_link_type(link_name)
                        if l_type == link_type:
                            link_dict[link_type][prop_name][link_name] = dict()
                            for ts in xrange(T):
                                time_sec = hydraulic_time_step*ts
                                link_dict[link_type][prop_name][link_name][time_sec] = self._pyomo_sim_results[prop][i+n_links*ts]

            results.link = link_dict

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
            pressure_setting = valve.setting
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
                self._constraint_names.add('valve_headloss_'+str(l))
            elif status == 'ACTIVE':
                end_node_obj = self._wn.get_node(end_node)
                model.head[end_node].value = pressure_setting + end_node_obj.elevation
                model.head[end_node].fixed = True
            else:
                raise RuntimeError("Valve Status not recognized.")

    def _read_pyomo_results(self, instance, pyomo_results, pandas_result = True):
        """
        Reads pyomo results from a pyomo instance and loads them into
        a network results object.

        Parameters
        ----------
        instance : Pyomo model instance
            Pyomo instance after instance.load() has been called.
        pyomo_results : Pyomo results object
            Pyomo results object

        Returns
        -------
        A NetworkResults object containing simulation results.
        """
        # Create results object
        results = NetResults()

        # Load general simulation options into the results object
        self._load_general_results(results)

        # Load pyomo solver statistics into the results object
        results.solver_statistics['name'] = pyomo_results.solver.name
        results.solver_statistics['status'] = pyomo_results.solver.status
        results.solver_statistics['statistics'] = pyomo_results.solver.statistics.items()

        # Create Delta time series
        results.time = pd.timedelta_range(start='0 minutes',
                                          end=str(self._sim_duration_sec) + ' seconds',
                                          freq=str(self._hydraulic_step_sec/60) + 'min')
        # Load link data
        link_name = []
        flowrate = []
        velocity = []
        link_times = []
        link_type = []
        for t in instance.time:
            for l in instance.links:
                link = self._wn.get_link(l)
                link_name.append(l)
                link_type.append(self._get_link_type(l))
                link_times.append(results.time[t])
                flow_l_t = instance.flow[l,t].value
                flowrate.append(flow_l_t)
                if isinstance(link, Pipe):
                    velocity_l_t = 4.0*abs(flow_l_t)/(math.pi*link.diameter**2)
                else:
                    velocity_l_t = 0.0
                velocity.append(velocity_l_t)

        # Load node data
        node_name = []
        head = []
        pressure = []
        demand = []
        expected_demand = []
        times = []
        node_type = []
        for t in instance.time:
            for n in instance.nodes:
                node = self._wn.get_node(n)
                node_name.append(n)
                node_type.append(self._get_node_type(n))
                times.append(results.time[t])
                head_n_t = instance.head[n, t].value
                if isinstance(node, Reservoir):
                    pressure_n_t = 0.0
                else:
                    pressure_n_t = head_n_t - node.elevation
                head.append(head_n_t)
                pressure.append(pressure_n_t)
                if isinstance(node, Junction):
                    demand.append(instance.demand_actual[n,t].value)
                    expected_demand.append(instance.demand_required[n,t])
                elif isinstance(node, Reservoir):
                    demand.append(instance.reservoir_demand[n,t].value)
                    expected_demand.append(instance.reservoir_demand[n,t].value)
                elif isinstance(node, Tank):
                    demand.append(instance.tank_net_inflow[n,t].value)
                    expected_demand.append(instance.tank_net_inflow[n,t].value)
                else:
                    demand.append(0.0)
                    expected_demand.append(0.0)
        
        if pandas_result:

            link_data_frame = pd.DataFrame({'time': link_times,
                                    'link': link_name,
                                    'flowrate': flowrate,
                                    'velocity': velocity,
                                    'type': link_type})

            link_pivot_table = pd.pivot_table(link_data_frame,
                                                  values=['flowrate', 'velocity', 'type'],
                                                  index=['link', 'time'],
                                                  aggfunc= lambda x: x)
            results.link = link_pivot_table

            node_data_frame = pd.DataFrame({'time': times,
                                            'node': node_name,
                                            'demand': demand,
                                            'expected_demand': expected_demand,
                                            'head': head,
                                            'pressure': pressure,
                                            'type': node_type})

            node_pivot_table = pd.pivot_table(node_data_frame,
                                              values=['demand', 'expected_demand', 'head', 'pressure', 'type'],
                                              index=['node', 'time'],
                                              aggfunc= lambda x: x)
            results.node = node_pivot_table
        else:
            pyomo_sim_results = {}
            pyomo_sim_results['node_name'] = node_name
            pyomo_sim_results['node_type'] = node_type
            pyomo_sim_results['node_head'] = head
            pyomo_sim_results['node_demand'] = demand
            pyomo_sim_results['node_expected_demand'] = expected_demand
            pyomo_sim_results['node_pressure'] = pressure
            pyomo_sim_results['link_name'] = link_name
            pyomo_sim_results['link_type'] = link_type
            pyomo_sim_results['link_velocity'] = velocity
            pyomo_sim_results['link_flowrate'] = flowrate

            hydraulic_time_step = float(copy.deepcopy(self._hydraulic_step_sec))
            node_dict = dict()
            node_types = set(pyomo_sim_results['node_type'])
            map_properties = dict()
            map_properties['node_demand'] = 'demand'
            map_properties['node_head'] = 'head'
            map_properties['node_pressure'] = 'pressure'
            map_properties['node_expected_demand'] = 'expected_demand'
            N = len(pyomo_sim_results['node_name'])
            n_nodes = len(self._wn._nodes.keys())
            T = N/n_nodes
            for node_type in node_types:
                node_dict[node_type] = dict()
                for prop, prop_name in map_properties.iteritems():
                    node_dict[node_type][prop_name] = dict()
                    for i in xrange(n_nodes):
                        node_name = pyomo_sim_results['node_name'][i]
                        n_type = self._get_node_type(node_name)
                        if n_type == node_type:
                            node_dict[node_type][prop_name][node_name] = dict()
                            for ts in xrange(T):
                                time_sec = hydraulic_time_step*ts
                                #print i+n_nodes*ts
                                node_dict[node_type][prop_name][node_name][time_sec] = pyomo_sim_results[prop][i+n_nodes*ts]

            results.node = node_dict

            link_dict = dict()
            link_types = set(pyomo_sim_results['link_type'])
            map_properties = dict()
            map_properties['link_flowrate'] = 'flowrate'
            map_properties['link_velocity'] = 'velocity'
            N = len(pyomo_sim_results['link_name'])
            n_links = len(self._wn._links.keys())
            T = N/n_links
            for link_type in link_types:
                link_dict[link_type] = dict()
                for prop, prop_name in map_properties.iteritems():
                    link_dict[link_type][prop_name] = dict()
                    for i in xrange(n_links):
                        link_name = pyomo_sim_results['link_name'][i]
                        l_type = self._get_link_type(link_name)
                        if l_type == link_type:
                            link_dict[link_type][prop_name][link_name] = dict()
                            for ts in xrange(T):
                                time_sec = hydraulic_time_step*ts
                                link_dict[link_type][prop_name][link_name][time_sec] = pyomo_sim_results[prop][i+n_links*ts]

            results.link = link_dict


        return results


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
        for l in instance.links:
            link = self._wn.get_link(l)
            link_name = l
            link_type = self._get_link_type(l)
            flowrate = instance.flow[l].value
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
        for n in instance.nodes:
            node = self._wn.get_node(n)
            node_name = n
            node_type = self._get_node_type(n)
            head_n = instance.head[n].value
            if isinstance(node, Reservoir):
                pressure_n = 0.0
            else:
                pressure_n = (head_n - node.elevation)
            if isinstance(node, Junction):
                demand = instance.demand_actual[n].value
                expected_demand = instance.demand_required[n]
                #if n=='101' or n=='10':
                #    print n,'  ',head_n, '  ', node.elevation
            elif isinstance(node, Reservoir):
                demand = instance.reservoir_demand[n].value
                expected_demand = instance.reservoir_demand[n].value
            elif isinstance(node, Tank):
                demand = instance.tank_net_inflow[n].value
                expected_demand = instance.tank_net_inflow[n].value
            elif isinstance(node, Leak):
                demand = instance.leak_demand[n].value
                expected_demand = instance.leak_demand[n].value
            else:
                demand = 0.0
                expected_demand = 0.0

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

    def _apply_controls(self, instance, first_timestep, links_closed_by_controls, t):

        # Get time controls
        for link_name, status in self._link_status.iteritems():
            if not status[t] and (status[t-1] or t==0):
                links_closed_by_controls.add(link_name)
            elif status[t] and not status[t-1]:
                links_closed_by_controls.remove(link_name)

        if not first_timestep:
            for link_name_k, value in self._wn.conditional_controls.iteritems():
                open_above = value['open_above']
	        open_below = value['open_below']
	        closed_above = value['closed_above']
	        closed_below = value['closed_below']
	
	        # If link is closed and the node level/pressure goes below threshold, then open the link
	        for i in open_below:
	            node_name_i = i[0]
	            value_i = i[1]
	            node_i = self._wn.get_node(node_name_i)
	            current_node_value = instance.head[node_name_i].value - node_i.elevation
	            if current_node_value <= value_i:
                        links_closed_by_controls.discard(link_name_k)
	
	        # If link is open and the node level/pressure goes above threshold, then close the link
	        for i in closed_above:
	            node_name_i = i[0]
	            value_i = i[1]
	            node_i = self._wn.get_node(node_name_i)
	            current_node_value = instance.head[node_name_i].value - node_i.elevation
	            if current_node_value >= value_i:
	                links_closed_by_controls.add(link_name_k)
	
	        # If link is closed and node level/pressure goes above threshold, then open the link
	        for i in open_above:
	            node_name_i = i[0]
	            value_i = i[1]
	            node_i = self._wn.get_node(node_name_i)
	            current_node_value = instance.head[node_name_i].value - node_i.elevation
	            if current_node_value >= value_i:
                        links_closed_by_controls.discard(link_name_k)
	
	        # If link is open and the node level/pressure goes below threshold, then close the link
	        for i in closed_below:
	            node_name_i = i[0]
	            value_i = i[1]
	            node_i = self._wn.get_node(node_name_i)
	            current_node_value = instance.head[node_name_i].value - node_i.elevation
	            if current_node_value <= value_i:
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

        time_t = self._hydraulic_step_sec*t

        for pump_name, time_tuple in self._pump_outage.iteritems():
            if time_t >= time_tuple[0] and time_t <= time_tuple[1]:
                pumps_closed_by_outage.add(pump_name)
            else:
                pumps_closed_by_outage.discard(pump_name)

    def _update_tank_controls_for_leaks(self):
        # Update tank controls
        for tank_name, tank_control_dict in self._tank_controls.iteritems():
            for i in range(len(tank_control_dict['link_names'])):
                link_next_to_tank = tank_control_dict['link_names'][i]
                if link_next_to_tank in self._pipes_with_leaks.keys():
                    self._tank_controls[tank_name]['node_names'][i] = self._pipes_with_leaks[link_next_to_tank]
                    tmp_link_next_to_tank = link_next_to_tank+'__A'
                    tmp_link = self._wn.get_link(tmp_link_next_to_tank)
                    tmp_start_node = tmp_link.start_node()
                    if tmp_start_node != tank_name:
                        tmp_link_next_to_tank = link_next_to_tank+'__B'
                        tmp_link = self._wn.get_link(tmp_link_next_to_tank)
                        tmp_end_node = tmp_link.end_node()
                        if tmp_end_node != tank_name:
                            raise RuntimeError('Could not find link next to tank after adding leak.')
                        else:
                            self._tank_controls[tank_name]['link_names'][i] = tmp_link_next_to_tank
                    else:
                        self._tank_controls[tank_name]['link_names'][i] = tmp_link_next_to_tank

    def _update_links_next_to_reservoirs_for_leaks(self):
        # Update links next to reservoirs
        for link_name, reserv_name in self._reservoir_links.iteritems():
            if link_name in self._pipes_with_leaks.keys():
                tmp_reserv_link_name = link_name+'__A'
                tmp_reserv_link = self._wn.get_link(tmp_reserv_link_name)
                tmp_start_node = tmp_reserv_link.start_node()
                if tmp_start_node != reserv_name:
                    tmp_reserv_link_name = link_name+'__B'
                    tmp_reserv_link = self._wn.get_link(tmp_reserv_link_name)
                    tmp_end_node = tmp_reserv_link.end_node()
                    if tmp_end_node != reserv_name:
                        raise RuntimeError('Could not find link next to reservoir after adding leak.')
                    else:
                        self._reservoir_links[tmp_reserv_link_name] = reserv_name
                        self._reservoir_links.pop(link_name)
                else:
                    self._reservoir_links[tmp_reserv_link_name] = reserv_name
                    self._reservoir_links.pop(link_name)

    def _update_time_controls_for_leaks(self):
        # Update time controls
        for control_link_name, control_dict in self._wn.time_controls.iteritems():
            if control_link_name in self._pipes_with_leaks.keys():
                leak_name = self._pipes_with_leaks[control_link_name]
                if self._leak_info[leak_name]['shutoff_valve_loc'] == 'START_NODE':
                    self._wn.time_controls[control_link_name+'__A'] = control_dict
                    self._wn.time_controls.pop(control_link_name)
                elif self._leak_info[leak_name]['shutoff_valve_loc'] == 'END_NODE':
                    self._wn.time_controls[control_link_name+'__B'] = control_dict
                    self._wn.time_controls.pop(control_link_name)
                elif self._leak_info[leak_name]['shutoff_valve_loc'] == 'ISOLATE':
                    self._wn.time_controls[control_link_name+'__A'] = control_dict
                    self._wn.time_controls[control_link_name+'__B'] = control_dict
                    self._wn.time_controls.pop(control_link_name)
                else:
                    raise ValueError('Shutoff valve location for leak is not recognized.')

    def _update_conditional_controls_for_leaks(self):
        # Update conditional controls
        for control_link_name, control_dict in self._wn.conditional_controls.iteritems():
            if control_link_name in self._pipes_with_leaks.keys():
                leak_name = self._pipes_with_leaks[control_link_name]
                if self._leak_info[leak_name]['shutoff_valve_loc'] == 'START_NODE':
                    self._wn.conditional_controls[control_link_name+'__A'] = control_dict
                    self._wn.conditional_controls.pop(control_link_name)
                elif self._leak_info[leak_name]['shutoff_valve_loc'] == 'END_NODE':
                    self._wn.conditional_controls[control_link_name+'__B'] = control_dict
                    self._wn.conditional_controls.pop(control_link_name)
                elif self._leak_info[leak_name]['shutoff_valve_loc'] == 'ISOLATE':
                    self._wn.conditional_controls[control_link_name+'__A'] = control_dict
                    self._wn.conditional_controls[control_link_name+'__B'] = control_dict
                    self._wn.conditional_controls.pop(control_link_name)
                else:
                    raise ValueError('Shutoff valve location for leak is not recognized.')
                

    def _add_leak_to_wn_object(self, leak_name):
        # Remove original pipe
        current_leak_info = self._leak_info[leak_name]
        orig_pipe = current_leak_info['original_pipe']
        self._wn.remove_pipe(orig_pipe._link_name)

        # Get start and end node info
        start_node = self._wn.get_node(orig_pipe.start_node())
        end_node = self._wn.get_node(orig_pipe.end_node())
        if isinstance(start_node, Reservoir):
            leak_elevation = end_node.elevation
        elif isinstance(end_node, Reservoir):
            leak_elevation = start_node.elevation
        else:
            leak_elevation = (start_node.elevation + end_node.elevation)/2.0

        # Add a leak node
        leak = Leak(leak_name, orig_pipe._link_name, current_leak_info['leak_area'], current_leak_info['leak_discharge_coeff'], leak_elevation)
        self._wn._nodes[leak_name] = leak
        self._wn._graph.add_node(leak_name)
        self._wn.set_node_type(leak_name, 'leak')
        leak_coordinates = ((self._wn._graph.node[orig_pipe.start_node()]['pos'][0] + self._wn._graph.node[orig_pipe.end_node()]['pos'][0])/2.0,(self._wn._graph.node[orig_pipe.start_node()]['pos'][1] + self._wn._graph.node[orig_pipe.end_node()]['pos'][1])/2.0)
        self._wn.set_node_coordinates(leak_name, leak_coordinates)

        # Add new pipes
        self._wn.add_pipe(orig_pipe._link_name+'__A', orig_pipe.start_node(), leak_name, orig_pipe.length/2.0, orig_pipe.diameter, orig_pipe.roughness, orig_pipe.minor_loss, orig_pipe._base_status)
        self._wn.add_pipe(orig_pipe._link_name+'__B', leak_name, orig_pipe.end_node(), orig_pipe.length/2.0, orig_pipe.diameter, orig_pipe.roughness, orig_pipe.minor_loss, orig_pipe._base_status)

    def _remove_leak_from_wn_object(self, leak_name):
        # Remove pipes on either side of leak
        current_leak_info = self._leak_info[leak_name]
        orig_pipe = current_leak_info['original_pipe']
        self._wn.remove_pipe(orig_pipe._link_name+'__A')
        self._wn.remove_pipe(orig_pipe._link_name+'__B')

        # Remove leak node
        self._wn._graph.remove_node(leak_name)
        self._wn._nodes.pop(leak_name)
        
        # Replace original pipe
        self._wn.add_pipe(orig_pipe._link_name, orig_pipe.start_node(), orig_pipe.end_node(), orig_pipe.length, orig_pipe.diameter, orig_pipe.roughness, orig_pipe.minor_loss, orig_pipe._base_status)

    def _close_all_links_for_tanks_below_min_head(self, instance, links_closed_by_tank_controls):
        for tank_name, control_info in self._tank_controls.iteritems():
            head_in_tank = instance.head[tank_name].value
            next_head_in_tank = self.predict_next_tank_head(tank_name, instance)
            min_tank_head = control_info['min_head']
            if next_head_in_tank <= min_tank_head and head_in_tank >= min_tank_head:
                for link_name in control_info['link_names']:
                    link = self._wn.get_link(link_name)
                    if isinstance(link, Valve):
                        raise NotImplementedError('Placing valves directly next to tanks is not yet supported.'+
                                                  'Try placing a dummy pipe and junction between the tank and valve.')
                    if isinstance(link, Pump) or link.get_base_status() == 'CV':
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
                    else: # the link is currently closed
                        if instance.head[node_name].value >= instance.head[tank_name].value + self._Htol:
                            links_closed_by_tank_controls.discard(link_name)

    def predict_next_tank_head(self,tank_name, instance):
        tank_net_inflow = 0.0
        tank = self._wn.get_node(tank_name)
        for l in self._wn.get_links_for_node(tank_name):
            link = self._wn.get_link(l)
            if link.start_node() == tank_name:
                tank_net_inflow -= instance.flow[l].value
            elif link.end_node() == tank_name:
                tank_net_inflow += instance.flow[l].value
            else:
                raise RuntimeError('Node link is neither start nor end node.')
        new_tank_head = instance.head[tank_name].value + tank_net_inflow*self._hydraulic_step_sec*4.0/(math.pi*tank.diameter**2)
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
            pressure_setting = valve.setting
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

    def _load_general_results(self, results):
        """
        Load general simulation options into the results object.

        Parameters
        ----------
        results : NetworkResults object
        """
        # Load general results
        results.network_name = self._wn.name

        # Load simulator options
        results.simulator_options['type'] = 'PYOMO'
        results.simulator_options['start_time'] = self._sim_start_sec
        results.simulator_options['duration'] = self._sim_duration_sec
        results.simulator_options['pattern_start_time'] = self._pattern_start_sec
        results.simulator_options['hydraulic_time_step'] = self._hydraulic_step_sec
        results.simulator_options['pattern_time_step'] = self._pattern_step_sec

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
                if (con_lower - con_value) >= 1.0e-6 or (con_value - con_upper) >= 1.0e-6:
                    print constraint_name,'[',constraint_key,']',' is not satisfied:'
                    print 'lower: ',con_lower, '\t body: ',con_value,'\t upper: ',con_upper 
                    con.pprint()

    def _close_links_for_drain_to_reservoir(self, instance, links_closed_by_drain_to_reservoir):
        for link_name, reservoir_name in self._reservoir_links.iteritems():
            link = self._wn.get_link(link_name)
            start_node_name = link.start_node()
            end_node_name = link.end_node()

            if start_node_name == reservoir_name:
                if instance.flow[link_name].value <= -self._Qtol:
                    links_closed_by_drain_to_reservoir.add(link_name)
                elif instance.head[reservoir_name].value >= instance.head[end_node_name].value:
                    links_closed_by_drain_to_reservoir.discard(link_name)
            elif end_node_name == reservoir_name:
                if instance.flow[link_name].value >= self._Qtol:
                    links_closed_by_drain_to_reservoir.add(link_name)
                elif instance.head[reservoir_name].value >= instance.head[start_node_name].value:
                    links_closed_by_drain_to_reservoir.discard(link_name)

    def _fully_open_links_with_inactive_leaks(self, links_closed_last_step, links_closed):
        # If a link with a leak got opened while the leak is inactive, we need to make sure both segments get opened.
        for link_name in links_closed_last_step:
            if link_name not in links_closed: # Link was closed last step and is open this step
                link = self._wn.get_link(link_name)
                start_node_name = link.start_node()
                end_node_name = link.end_node()
                if start_node_name in self._inactive_leaks:
                    leak_links = self._wn.get_links_for_node(start_node_name)
                    if len(leak_links) != 2:
                        raise RuntimeError('There is a bug.')
                    leak_links.remove(link_name)
                    other_segment = leak_links[0]
                    links_closed.discard(other_segment)
                elif end_node_name in self._inactive_leaks:
                    leak_links = self._wn.get_links_for_node(end_node_name)
                    if len(leak_links) != 2:
                        raise RuntimeError('There is a bug.')
                    leak_links.remove(link_name)
                    other_segment = leak_links[0]
                    links_closed.discard(other_segment)

    def _check_for_isolated_junctions(self, instance, links_closed):
        # Check for isolated junctions. If all links connected to a junction are closed,
        # then the head is fixed to the elevation, the demand if fixed to 0,
        # the mass balance for that junction is deactivated, and
        # the PDD constraint for that junction is deactivated

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
                instance.demand_actual[junction_name] = 0.0
                instance.demand_actual[junction_name].fixed = True
                instance.node_mass_balance[junction_name].deactivate()
                instance.pressure_driven_demand[junction_name].deactivate()
