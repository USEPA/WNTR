"""
QUESTIONS
"""

"""
TODO
1. Use in_edges and out_edges to write node balances on the pyomo model.
2. Use reporting timestep when creating the pyomo results object.
3. Support for check valves.
"""

try:
    from pyomo.core import *
    from pyomo.core.base.expr import Expr_if
    from pyomo.environ import *
    from pyomo.opt import SolverFactory
except ImportError:
    raise ImportError('Error importing pyomo while running pyomo simulator.'
                      'Make sure pyomo is installed and added to path.')
import math
from WaterNetworkSimulator import *
import pandas as pd
from six import iteritems

class PyomoSimulator(WaterNetworkSimulator):
    """
    Pyomo simulator inherited from Water Network Simulator.
    """


    def __init__(self, wn):
        """
        Pyomo simulator class.

        Parameters
        ---------
        wn : Water Network Model
            A water network model.
        """
        WaterNetworkSimulator.__init__(self, wn)

        # Global constants
        self._Hw_k = 10.67 # Hazen-Williams resistance coefficient in SI units = 4.727 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.
        self._Dw_k = 0.0826 # Darcy-Weisbach constant in SI units = 0.0252 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.
        self._Htol = 0.00015 # Head tolerance in meters.
        self._Qtol = 2.8e-5 # Flow tolerance in ft^3/s.
        self._g = 9.81 # Acceleration due to gravity

        self._n_timesteps = 0 # Number of hydraulic timesteps
        self._demand_dict = {} # demand dictionary
        self._link_status = {} # dictionary of link statuses
        self._valve_status = {} # dictionary of valve statuses

        self._initialize_results_dict()
        self._max_step_iter = 10 # maximum number of newton solves at each timestep.
                                 # model is resolved when a valve status changes.

        # Pressure driven demand parameters
        if 'NOMINAL PRESSURE' in self._wn.options and 'MINIMUM PRESSURE' in self._wn.options:
            self._P0 = self._wn.options['MINIMUM PRESSURE']
            self._PF = self._wn.options['NOMINAL PRESSURE']
            # Calculate polynomials for smoothing abrupt changes in PDD curve
            self._pdd_smoothing_polynomial_left = []  # left hand side smoothing curve parameters
            self._pdd_smoothing_polynomial_right = []  # right hand side smoothing curve parameters
            #self._smoothing_points = self._fit_smoothing_curve()
        else:
            self._P0 = None
            self._PF = None

    def _initialize_simulation(self):
        # Number of hydraulic timesteps
        self._n_timesteps = int(round(self._sim_duration_sec / self._hydraulic_step_sec)) + 1
        # Get all demand for complete time interval
        self._demand_dict = {}
        for node_name, node in self._wn.nodes():
            if isinstance(node, Junction):
                demand_values = self.get_node_demand(node_name)
                for t in range(self._n_timesteps):
                    self._demand_dict[(node_name, t)] = demand_values[t]
            else:
                for t in range(self._n_timesteps):
                    self._demand_dict[(node_name, t)] = 0.0

        # Create time controls dictionary
        self._link_status = {}
        for l, link in self._wn.links():
            status_l = []
            for t in xrange(self._n_timesteps):
                time_min = t * self._hydraulic_step_sec
                status_l_t = self.is_link_open(l, time_min)
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
        self._pyomo_sim_results['node_pressure'] = []
        self._pyomo_sim_results['link_name'] = []
        self._pyomo_sim_results['link_type'] = []
        self._pyomo_sim_results['link_times'] = []
        self._pyomo_sim_results['link_velocity'] = []
        self._pyomo_sim_results['link_flowrate'] = []

    def _initialize_from_pyomo_results(self, instance, last_instance):

        for l in instance.links:
            if l in instance.pumps:
                instance.flow[l].value = last_instance.flow[l].value + self._Qtol
            else:
                instance.flow[l].value = last_instance.flow[l].value
        for n in instance.nodes:
            instance.head[n].value = last_instance.head[n].value
            if n in instance.junctions:
                junction = self._wn.get_node(n)
                if instance.head[n].value - junction.elevation <= self._P0:
                    instance.demand_actual[n] = 0.0
                else:
                    instance.demand_actual[n] = abs(instance.demand_actual[n].value)

        for r in instance.reservoirs:
            instance.reservoir_demand[r].value = last_instance.reservoir_demand[r].value
        for t in instance.tanks:
            instance.tank_net_inflow[t].value = last_instance.tank_net_inflow[t].value


    def _fit_smoothing_curve(self):
        delta = 0.1
        smoothing_points = []
        # Defining Line 1
        a1 = 1e-3
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




    def build_hydraulic_model(self, modified_hazen_williams=True):
        """
        Build water network hadloss and node balance constraints.

        Optional Parameters
        --------
        modified_hazen_williams : bool
            Flag to use a slightly modified version of Hazen-Williams headloss
            equation for better stability
        """
        #t0 = time.time()

        pi = math.pi

        # The Hazen-Williams headloss curve is slightly modified to improve solution time.
        # The three functions defines below - f1, f2, Px - are used to ensure that the Jacobian
        # does not go to 0 close to zero flow.
        def f1(x):
            return 0.01*x

        def f2(x):
            return 1.0*x**1.852

        def Px(x):
            #return 1.05461308881e-05 + 0.0494234328901*x - 0.201070504673*x**2 + 15.3265906777*x**3
            return 2.45944613543e-06 + 0.0138413824671*x - 2.80374270811*x**2 + 430.125623753*x**3

        def LossFunc(Q):
            #q1 = 0.01
            #q2 = 0.05
            q1 = 0.00349347323944
            q2 = 0.00549347323944
            return Expr_if(IF = Q < q1, THEN = f1(Q), ELSE = Expr_if(IF = Q > q2, THEN = f2(Q), ELSE = Px(Q)))

        wn = self._wn
        model = ConcreteModel()
        model.timestep = self._hydraulic_step_sec
        model.duration = self._sim_duration_sec
        n_timesteps = int(round(model.duration/model.timestep))

        ###################### SETS #########################
        model.time = Set(initialize=range(0, n_timesteps+1))
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

        #print "Created Sets: ", time.time() - t0

        ####### Check for components that are not supported #######
        for l in model.links:
            link = wn.get_link(l)
            if link.get_base_status().upper() == 'CV':
                raise RuntimeError('Check valves are not supported by the Pyomo model.')

        ################### PARAMETERS #######################

        demand_dict = {}
        for n in model.junctions:
            demand_values = self.get_node_demand(n)
            for t in model.time:
                demand_dict[(n, t)] = demand_values[t]
        model.demand_required = Param(model.junctions, model.time, within=Reals, initialize=demand_dict)

        ################### VARIABLES #####################
        def flow_init_rule(model, l,t):
            if l in model.pipes or l in model.valves:
                return 0.3048  # Flow in pipe initialized to 1 ft/s
            elif l in model.pumps:
                pump = wn.get_link(l)
                return pump.get_design_flow()

        model.flow = Var(model.links, model.time, within=Reals, initialize=flow_init_rule)

        def init_headloss_rule(model, l, t):
            if l in model.pipes:
                pipe = wn.get_link(l)
                pipe_resistance_coeff = self._Hw_k*(pipe.roughness**(-1.852))*(pipe.diameter**(-4.871))*pipe.length # Hazen-Williams
                return pipe_resistance_coeff*LossFunc(abs(model.flow[l,t]))
            elif l in model.pumps:
                pump = wn.get_link(l)
                if pump.info_type == 'HEAD':
                    A, B, C = pump.get_head_curve_coefficients()
                    return -1.0*A + B*(model.flow[l,t]**C)
                elif pump.info_type == 'POWER':
                    return 10.0
            else:
                return 10.0
        #model.headloss = Var(model.links, model.time, within=Reals, initialize=10.0)

        def init_head_rule(model, n, t):
            if n in model.junctions or n in model.tanks:
                #print wn.get_node(n).elevation
                return wn.get_node(n).elevation
            else:
                return 100.0
        model.head = Var(model.nodes, model.time, initialize=init_head_rule)


        model.reservoir_demand = Var(model.reservoirs, model.time, within=Reals, initialize=0.1)
        model.tank_net_inflow = Var(model.tanks, model.time,within=Reals, initialize=0.1)

        def init_demand_rule(model,n,t):
            return model.demand_required[n,t]
        model.demand_actual = Var(model.junctions, model.time, within=Reals, initialize=init_demand_rule)

        ############## CONSTRAINTS #####################

        # Head loss inside pipes
        for l in model.pipes:
            pipe = wn.get_link(l)
            pipe_resistance_coeff = self._Hw_k*(pipe.roughness**(-1.852))*(pipe.diameter**(-4.871))*pipe.length # Hazen-Williams
            start_node = pipe.start_node()
            end_node = pipe.end_node()
            for t in model.time:
                if self.is_link_open(l,t*self._hydraulic_step_sec):
                    if modified_hazen_williams:
                        #setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                        #                                              *pipe_resistance_coeff*LossFunc(abs(model.flow[l,t])) == model.headloss[l,t]))
                        setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                                                                      *pipe_resistance_coeff*LossFunc(abs(model.flow[l,t])) == model.head[start_node,t] - model.head[end_node,t]))
                    else:
                        #setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                        #                                              *pipe_resistance_coeff*f2(abs(model.flow[l,t])) == model.headloss[l,t]))
                        #setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=pipe_resistance_coeff*model.flow[l,t]*(abs(model.flow[l,t]))**0.852 == model.head[start_node,t] - model.head[end_node,t]))
                        setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=pipe_resistance_coeff*model.flow[l,t]*(abs(model.flow[l,t]))**0.852 == model.head[start_node,t] - model.head[end_node,t]))

        #print "Created headloss: ", time.time() - t0
        # Head gain provided by the pump is implemented as negative headloss
        for l in model.pumps:
            pump = wn.get_link(l)
            start_node = pump.start_node()
            end_node = pump.end_node()
            if pump.info_type == 'HEAD':
                A, B, C = pump.get_head_curve_coefficients()
                for t in model.time:
                    #if self.is_link_open(l,t*self._hydraulic_step_sec):
                    #    setattr(model, 'pump_negative_headloss_'+str(l)+'_'+str(t), Constraint(expr=model.headloss[l,t] == (-1.0*A + B*(model.flow[l,t]**C))))
                    if self.is_link_open(l,t*self._hydraulic_step_sec):
                        setattr(model, 'pump_negative_headloss_'+str(l)+'_'+str(t), Constraint(expr=model.head[start_node,t] - model.head[end_node,t] == (-1.0*A + B*(model.flow[l,t]**C))))
            elif pump.info_type == 'POWER':
                power = pump.info_value
                for t in model.time:
                    if self.is_link_open(l,t*self._hydraulic_step_sec):
                        setattr(model, 'pump_negative_headloss_'+str(l)+'_'+str(t), Constraint(expr=(model.head[start_node,t] - model.head[end_node,t])*model.flow[l,t]*self._g == power))

        #print "Created head gain: ", time.time() - t0
        # Nodal head difference between start and end node of a link
        """
        for l in model.links:
            link = wn.get_link(l)
            start_node = link.start_node()
            end_node = link.end_node()
            for t in model.time:
                if self.is_link_open(l,t*self._hydraulic_step_sec):
                    setattr(model, 'head_difference_'+str(l)+'_'+str(t), Constraint(expr=model.headloss[l,t] == model.head[start_node,t] - model.head[end_node,t]))
        """
        #print "Created head_diff: ", time.time() - t0
        # Mass Balance
        def node_mass_balance_rule(model, n, t):
            expr = 0
            for l in wn.get_links_for_node(n):
                link = wn.get_link(l)
                if link.start_node() == n:
                    expr -= model.flow[l,t]
                elif link.end_node() == n:
                    expr += model.flow[l,t]
                else:
                    raise RuntimeError('Node link is neither start nor end node.')
            node = wn.get_node(n)
            if isinstance(node, Junction):
                #return expr == model.demand_actual[n,t]
                return expr == model.demand_required[n,t]
            elif isinstance(node, Tank):
                return expr == model.tank_net_inflow[n,t]
            elif isinstance(node, Reservoir):
                return expr == model.reservoir_demand[n,t]
        model.node_mass_balance = Constraint(model.nodes, model.time, rule=node_mass_balance_rule)
        #print "Created Node balance: ", time.time() - t0


        # Head in junctions should be greater or equal to the elevation
        for n in model.junctions:
            junction = wn.get_node(n)
            elevation_n = junction.elevation
            for t in model.time:
                setattr(model, 'junction_elevation_'+str(n)+'_'+str(t), Constraint(expr=model.head[n,t] >= elevation_n))

        # Bounds on the head inside a tank
        def tank_head_bounds_rule(model,n,t):
            tank = wn.get_node(n)
            return (tank.elevation + tank.min_level, model.head[n,t], tank.elevation + tank.max_level)
        model.tank_head_bounds = Constraint(model.tanks, model.time, rule=tank_head_bounds_rule)

        # Flow in a pump should always be positive
        def pump_positive_flow_rule(model,l,t):
            return model.flow[l,t] >= 0
        model.pump_positive_flow_bounds = Constraint(model.pumps, model.time, rule=pump_positive_flow_rule)

        def tank_dynamics_rule(model, n, t):
            if t is max(model.time):
                return Constraint.Skip
            else:
                tank = wn.get_node(n)
                return (model.tank_net_inflow[n,t]*model.timestep*4.0)/(pi*(tank.diameter**2)) == model.head[n,t+1]-model.head[n,t]
        model.tank_dynamics = Constraint(model.tanks, model.time, rule=tank_dynamics_rule)

        #print "Created Tank Dynamics: ", time.time() - t0

        return model.create()


    def build_hydraulic_model_at_instant(self,
                                         last_tank_head,
                                         nodal_demands,
                                         first_timestep,
                                         links_closed,
                                         modified_hazen_williams=True):
        """
        Build hydraulic constraints at a particular time instance.

        Parameters
        --------
        last_tank_head : dict of string: float
            Dictionary containing tank names and their respective head at the last timestep.
        nodal_demands : dict of string: float
            Dictionary containing junction names and their respective respective demand at current timestep.
        first_timestep : bool
            Flag indicating wheather its the first timestep
        links_closed : list of strings
            Mane of links that are closed.

        Optional Parameters
        --------
        modified_hazen_williams : bool
            Flag to use a slightly modified version of Hazen-Williams headloss
            equation for better stability
        """

        t0 = time.time()

        pi = math.pi

        # The Hazen-Williams headloss curve is slightly modified to improve solution time.
        # The three functions defines below - f1, f2, Px - are used to ensure that the Jacobian
        # does not go to 0 close to zero flow.
        def f1(x):
            return 0.01*x

        def f2(x):
            return 1.0*x**1.852

        def Px(x):
            return 2.45944613543e-06 + 0.0138413824671*x - 2.80374270811*x**2 + 430.125623753*x**3

        def LossFunc(Q):
            q1 = 0.00349347323944
            q2 = 0.00549347323944
            return Expr_if(IF = Q < q1, THEN = f1(Q), ELSE = Expr_if(IF = Q > q2, THEN = f2(Q), ELSE = Px(Q)))


        # Pressure driven demand equation
        def pressure_dependent_demand_square(head, elevation):
            p = head - elevation

            # Defining Line 1
            def L1(x):
                a_1 = 1e-3
                b_1 = 0
                return a_1*x + b_1

            # Defining Line 2
            def L2(x):
                a_2 = 1/(self._PF - self._P0)
                b_2 = -1*(self._P0/(self._PF - self._P0))
                #print "Line 1: ", a_2, b_2
                return a_2*x + b_2

            # Define Line 3
            def L3(x):
                a_3 = 0
                b_3 = 1
                #print "Line 2: ", a_3, b_3
                return a_3*x + b_3

            if len(self._smoothing_points) == 4:
                x1 = self._smoothing_points[0]
                x2 = self._smoothing_points[1]
                x3 = self._smoothing_points[2]
                x4 = self._smoothing_points[3]
            elif len(self._smoothing_points) == 2:
                x3 = self._smoothing_points[0]
                x4 = self._smoothing_points[1]
            else:
                raise RuntimeError("The PDD expression must have 4 or 2 points of switching.")

            if self._pdd_smoothing_polynomial_left:
                [a1, b1, c1, d1] = self._pdd_smoothing_polynomial_left
                def P1(x):
                    return a1*x**3 + b1*x**2 + c1*x + d1
                [a2, b2, c2, d2] = self._pdd_smoothing_polynomial_right
                def P2(x):
                    return a2*x**3 + b2*x**2 + c2*x + d2
                return Expr_if(IF=p <= x1, THEN=L1(p),
                               ELSE=Expr_if(IF=p <= x2, THEN=P1(p),
                                            ELSE=Expr_if(IF=p <= x3, THEN=L2(p),
                                                         ELSE=Expr_if(IF=p <= x4, THEN=P2(p),
                                                                      ELSE=L3(p)))))
            else:
                def P2(x):
                    [a2, b2, c2, d2] = self._pdd_smoothing_polynomial_right
                    #print "Polynomial: ", a2, b2, c2, d2
                    return a2*x**3 + b2*x**2 + c2*x + d2
                #print "Switch point 1: ", x3
                #print "Switch point 2:", x4
                return Expr_if(IF=p <= 1e-6, THEN=1e6*p, ELSE=Expr_if(IF=p <= x3, THEN=L2(p),
                                                                      ELSE=Expr_if(IF=p <= x4, THEN=P2(p),
                                                                      ELSE=L3(p))))

        def pressure_dependent_demand_nl(full_demand, p):

            delta = 0.1
            # Defining Line 1
            a1 = 1e-6
            b1 = full_demand

            def L1(x):
                return a1*x + b1

            # Defining PDD function
            def PDD(x):
                return full_demand*math.sqrt((x - self._P0)/(self._PF - self._P0))

            def PDD_deriv(x):
                return (full_demand/2)*(1/(self._PF - self._P0))*(1/math.sqrt((x - self._P0)/(self._PF - self._P0)))

            def A(x_1, x_2):
                return np.array([[x_1**3, x_1**2, x_1, 1],
                                [x_2**3, x_2**2, x_2, 1],
                                [3*x_1**2, 2*x_1,  1, 0],
                                [3*x_2**2, 2*x_2,  1, 0]])

            x_gap = self._PF - self._P0

            assert x_gap > delta, "Delta should be greater than the gap between nominal and minimum pressure."

            # Get parameters for the second polynomial
            x3 = self._PF - x_gap*delta
            y3 = PDD(x3)
            x4 = self._PF + x_gap*delta
            y4 = L1(x4)
            A2 = A(x3, x4)
            rhs2 = np.array([y3, y4, PDD_deriv(x3), a1])
            c2 = np.linalg.solve(A2, rhs2)

            def smooth_polynomial(p_):
                return c2[0]*p_**3 + c2[1]*p_**2 + c2[2]*p_ + c2[3]

            return Expr_if(IF=p <= x3, THEN=PDD(p),
                           ELSE=Expr_if(IF=p <= x4, THEN=smooth_polynomial(p),
                                        ELSE=L1(p)))

            #return Expr_if(IF=p <= self._PF, THEN=PDD(p),
            #               ELSE=L1(p))


        wn = self._wn
        model = ConcreteModel()
        model.timestep = self._hydraulic_step_sec
        #model.duration = self._sim_duration_sec
        #n_timesteps = int(round(model.duration/model.timestep))

        ###################### SETS #########################
        #model.time = Set(initialize=range(0, n_timesteps+1))
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

        #print "Created Sets: ", time.time() - t0

        ####### Check for components that are not supported #######
        for l in model.links:
            link = wn.get_link(l)
            if link.get_base_status().upper() == 'CV':
                raise RuntimeError('Check valves are not supported by the Pyomo model.')

        ################### PARAMETERS #######################

        model.demand_required = Param(model.junctions, within=Reals, initialize=nodal_demands)

        ################### VARIABLES #####################
        def flow_init_rule(model, l):
            if l in model.pipes or l in model.valves:
                return 0.3048  # Flow in pipe initialized to 1 ft/s
            elif l in model.pumps:
                pump = wn.get_link(l)
                if pump.info_type == 'HEAD':
                    return pump.get_design_flow()
                else:
                    return 0.3048
        model.flow = Var(model.links, within=Reals, initialize=flow_init_rule)

        def init_headloss_rule(model, l):
            if l in model.pipes:
                pipe = wn.get_link(l)
                pipe_resistance_coeff = self._Hw_k*(pipe.roughness**(-1.852))*(pipe.diameter**(-4.871))*pipe.length # Hazen-Williams
                return pipe_resistance_coeff*LossFunc(abs(model.flow[l,t]))
            elif l in model.pumps:
                pump = wn.get_link(l)
                if pump.info_type == 'HEAD':
                    A, B, C = pump.get_head_curve_coefficients()
                    return -1.0*A + B*(model.flow[l]**C)
                else:
                    return 10.0
            else:
                return 10.0
        #model.headloss = Var(model.links, model.time, within=Reals, initialize=10.0)

        def init_head_rule(model, n):
            if n in model.junctions or n in model.tanks:
                return wn.get_node(n).elevation
            else:
                return 100.0
        model.head = Var(model.nodes, initialize=init_head_rule)


        model.reservoir_demand = Var(model.reservoirs, within=Reals, initialize=0.1)
        model.tank_net_inflow = Var(model.tanks, within=Reals, initialize=0.1)

        def init_demand_rule(model,n):
            return model.demand_required[n]
        model.demand_actual = Var(model.junctions, within=Reals, initialize=init_demand_rule)

        #print "Initialized variables: ", time.time() - t0
        ############## CONSTRAINTS #####################

        # Head loss inside pipes
        for l in model.pipes:
            pipe = wn.get_link(l)
            pipe_resistance_coeff = self._Hw_k*(pipe.roughness**(-1.852))*(pipe.diameter**(-4.871))*pipe.length # Hazen-Williams
            start_node = pipe.start_node()
            end_node = pipe.end_node()
            if l not in links_closed:
                if modified_hazen_williams:
                    #setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                    #                                              *pipe_resistance_coeff*LossFunc(abs(model.flow[l,t])) == model.headloss[l,t]))
                    setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=Expr_if(IF=model.flow[l]>0, THEN=1, ELSE=-1)
                            *pipe_resistance_coeff*LossFunc(abs(model.flow[l])) == model.head[start_node] - model.head[end_node]))
                else:
                    #setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                    #                                              *pipe_resistance_coeff*f2(abs(model.flow[l,t])) == model.headloss[l,t]))
                    #setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=pipe_resistance_coeff*model.flow[l,t]*(abs(model.flow[l,t]))**0.852 == model.head[start_node,t] - model.head[end_node,t]))
                    setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=pipe_resistance_coeff*model.flow[l]*(abs(model.flow[l]))**0.852 == model.head[start_node] - model.head[end_node]))

        #print "Created headloss: ", time.time() - t0
        # Head gain provided by the pump is implemented as negative headloss
        for l in model.pumps:
            pump = wn.get_link(l)
            start_node = pump.start_node()
            end_node = pump.end_node()
            if pump.info_type == 'HEAD':
                A, B, C = pump.get_head_curve_coefficients()
                #if self.is_link_open(l,t*self._hydraulic_step_sec):
                #    setattr(model, 'pump_negative_headloss_'+str(l)+'_'+str(t), Constraint(expr=model.headloss[l,t] == (-1.0*A + B*(model.flow[l,t]**C))))
                if l not in links_closed:
                    setattr(model, 'pump_negative_headloss_'+str(l), Constraint(expr=model.head[start_node] - model.head[end_node] == (-1.0*A + B*((model.flow[l])**C))))
            elif pump.info_type == 'POWER':
                if l not in links_closed:
                    #print "Pump :", l, " power: ", pump.power
                    setattr(model, 'pump_negative_headloss_'+str(l), Constraint(expr=(model.head[start_node] - model.head[end_node])*model.flow[l]*self._g*1000.0 == -pump.power))
            else:
                raise RuntimeError('Pump info type not recognised. ' + l)

        #print "Created pump head constraint: ", time.time() - t0
        # Mass Balance
        def node_mass_balance_rule(model, n):
            expr = 0
            for l in wn.get_links_for_node(n):
                link = wn.get_link(l)
                if link.start_node() == n:
                    expr -= model.flow[l]
                elif link.end_node() == n:
                    expr += model.flow[l]
                else:
                    raise RuntimeError('Node link is neither start nor end node.')
            node = wn.get_node(n)
            if isinstance(node, Junction):
                return expr == model.demand_actual[n]
                #return expr == model.demand_required[n]
            elif isinstance(node, Tank):
                return expr == model.tank_net_inflow[n]
            elif isinstance(node, Reservoir):
                return expr == model.reservoir_demand[n]
        model.node_mass_balance = Constraint(model.nodes, rule=node_mass_balance_rule)
        #print "Created Node balance: ", time.time() - t0


        """
        # Head in junctions should be greater or equal to the elevation
        for n in model.junctions:
            junction = wn.get_node(n)
            elevation_n = junction.elevation
            setattr(model, 'junction_elevation_'+str(n), Constraint(expr=model.head[n] >= elevation_n))
        """
        """
        # Bounds on the head inside a tank
        def tank_head_bounds_rule(model,n):
            tank = wn.get_node(n)
            return (tank.elevation + tank.min_level, model.head[n], tank.elevation + tank.max_level)
        model.tank_head_bounds = Constraint(model.tanks, rule=tank_head_bounds_rule)
        """
        """
        # Flow in a pump should always be positive
        def pump_positive_flow_rule(model,l):
            return model.flow[l] >= 0
        model.pump_positive_flow_bounds = Constraint(model.pumps, rule=pump_positive_flow_rule)
        """


        def tank_dynamics_rule(model, n):
            if first_timestep:
                return Constraint.Skip
            else:
                tank = wn.get_node(n)
                return (model.tank_net_inflow[n]*model.timestep*4.0)/(pi*(tank.diameter**2)) == model.head[n]-last_tank_head[n]
        model.tank_dynamics = Constraint(model.tanks, rule=tank_dynamics_rule)


        #print "Created Tank Dynamics: ", time.time() - t0

        # Pressure driven demand constraint
        def pressure_driven_demand_rule(model, j):
            junction = wn.get_node(j)
            #print "Junction: ",j, "P0 = ", self._P0, "Pf = ", self._PF, "required_dem= ", model.demand_required[j], "Elevation: ", junction.elevation
            if model.demand_required[j] <= self._Qtol:
                return model.demand_actual[j] == model.demand_required[j]
            else:
                #return pressure_dependent_demand_square(model.head[j], junction.elevation) == (model.demand_actual[j]/model.demand_required[j])**2
                #return pressure_dependent_demand_square(model.head[j], junction.elevation) >= (model.demand_actual[j]/model.demand_required[j])**2
                return pressure_dependent_demand_nl(model.demand_required[j], model.head[j]-junction.elevation) == model.demand_actual[j]

        def demand_driven_rule(model, j):
            return model.demand_actual[j] == model.demand_required[j]

        if self._P0 == None and self._PF == None:
            model.pressure_driven_demand = Constraint(model.junctions, rule=demand_driven_rule)
        else:
            model.pressure_driven_demand = Constraint(model.junctions, rule=pressure_driven_demand_rule)

        """
        # Positive demand constraint
        def demand_bounds_rule(model, j):
            return model.demand_actual[j] >= 1e-4
        model.demand_bounds = Constraint(model.junctions, rule=demand_bounds_rule)
        """

        return model.create()



    def run_calibration(self,
                        measurements, 
                        weights = {'tank_level':1.0, 'pressure':1.0, 'flowrate':1.0, 'demand':1.0},
                        solver='ipopt', 
                        solver_options={}, 
                        modified_hazen_williams=True):
        import numpy as np

        # Initialise demand dictionaries and link statuses
        self._initialize_simulation()

        # Do it in the constructor? make it an attribute?
        model = self.build_hydraulic_model(modified_hazen_williams)
        wn = self._wn

        # Temporal the calibrator should check if initial values are provided if not they should be fixed
        # Fix the head in a reservoir
        for n in model.reservoirs:
            reservoir_head = wn.get_node(n).base_head
            for t in model.time:
                model.head[n,t].value = reservoir_head
                model.head[n,t].fixed = True

        # Fix the initial head in a Tank
        for n in model.tanks:
            tank = wn.get_node(n)
            tank_initial_head = tank.elevation + tank.init_level
            t = min(model.time)
            model.head[n,t].value = tank_initial_head
            model.head[n,t].fixed = True

        ############### OBJECTIVE ########################
        node_measurements = measurements.node
        link_measurements = measurements.link

        node_params = node_measurements.columns
        link_params = link_measurements.columns

        # helper function
        dateToTimestep = lambda DateTime: (((DateTime.days*24+DateTime.hours)*60+DateTime.minutes)*60+DateTime.seconds)/self._hydraulic_step_sec

        
        def obj_rule(model):
            
            levels_error = 0
            demand_error = 0
            pressure_error = 0
            node_ids = node_measurements.index.get_level_values('node').drop_duplicates()
            for n in node_ids:
                node_measure_times = list(node_measurements[node_params[0]][n].index)
                for dt in node_measure_times:
                    t = dateToTimestep(dt)
                    if t not in model.time or n not in model.nodes:
                        print "WARNING: The measurement at node", str(n),", at ",str(dt)," is ignored since it is not within the nodes and times of the model. \n"
                    else:
                        if self._get_node_type(n)=='junction':
                            if 'pressure' in node_params and not np.isnan(node_measurements['pressure'][n][dt]):
                                pressure_error += ((node_measurements['pressure'][n][dt]+wn.get_node(n).elevation)-model.head[n,t])**2
                            # Regularization term
                            if 'demand' in node_params and not np.isnan(node_measurements['demand'][n][dt]):
                                demand_error += (node_measurements['demand'][n][dt]-model.demand_actual[n,t])**2
                        elif self._get_node_type(n)=='tank':
                            if 'head' in node_params and not np.isnan(node_measurements['head'][n][dt]):
                                levels_error += (node_measurements['head'][n][dt]-model.head[n,t])**2
                            #if 'demand' in node_params and not np.isnan(node_measurements['demand'][n][dt]):
                            #    demand_error += (node_measurements['demand'][n][dt]-model.tank_net_inflow[n,t])**2
                        elif self._get_node_type(n)=='reservoir':
                            if 'demand' in node_params and not np.isnan(node_measurements['demand'][n][dt]):
                                demand_error += (node_measurements['demand'][n][dt]-model.reservoir_demand[n,t])**2
                            #if 'head' in node_params and not np.isnan(node_measurements['head'][n][dt]):
                            #    levels_error += (node_measurements['head'][n][dt]-model.head[n,t])**2
                            

            # Fitting flows
            link_ids = link_measurements.index.get_level_values('link').drop_duplicates()
            
            flow_error = 0
            for l in link_ids:
                link_measure_times = list(link_measurements[link_params[0]][l].index)
                for dt in link_measure_times:
                    t = dateToTimestep(dt)
                    if t not in model.time or l not in model.links:
                        print "WARNING: The measurement at link", str(l),", at ",str(dt)," is ignored since it is not within the links and times of the model. \n"
                    else:
                        if not np.isnan(link_measurements['flowrate'][l][dt]):
                            flow_error += (link_measurements['flowrate'][l][dt]-model.flow[l,t])**2
            
            # Objective expression
            expr = pressure_error*weights['pressure']
            expr += levels_error*weights['tank_level']
            expr += flow_error*weights['flowrate']
            expr += demand_error*weights['demand']

            #print "Pressure error\n",pressure_error,"\n"
            #print "Flow error \n",flow_error,"\n"
            #print "level error\n",levels_error,"\n"
            #print "demand error\n",demand_error,"\n"

            return expr
        model.obj = Objective(rule=obj_rule, sense=minimize)
        #print node_measurements

        #return NetResults()

        ####### CREATE INSTANCE AND SOLVE ########
        instance = model.create()

        opt = SolverFactory(solver)
        # Set solver options
        for key, val in solver_options.iteritems():
            opt.options[key]=val
        # Solve pyomo model
        pyomo_results = opt.solve(instance, tee=True)
        #print "Created results: ", time.time() - t0
        instance.load(pyomo_results)

        # Load pyomo results into results object
        results = self._read_pyomo_results(instance, pyomo_results)

        return results

    def run_sim(self, solver='ipopt', solver_options={}, modified_hazen_williams=True):
        

        #print link_status
        self._initialize_simulation()

        # Create results object
        results = NetResults()
        results.link = pd.DataFrame(columns=['time', 'link', 'flowrate', 'velocity', 'type'])
        results.node = pd.DataFrame(columns=['time', 'node', 'demand', 'head', 'pressure', 'type'])
        results.time = pd.timedelta_range(start='0 minutes',
                                          end=str(self._sim_duration_sec) + ' seconds',
                                          freq=str(self._hydraulic_step_sec/60) + 'min')

        # Load general simulation options into the results object
        self._load_general_results(results)

        # Assert conditional controls are only provided for Tanks
        self._verify_conditional_controls_for_tank()

        # List of closed pump ids
        pumps_closed_by_rule = [] # List of pumps that are closed by level controls defined in inp file
        pumps_closed_by_outage = [] # List of pump closed by pump outage times provided by user
        links_closed_by_tank_controls = []  # List of pipes closed when tank level goes below min

        # Create solver instance
        opt = SolverFactory(solver)
        # Set solver options
        for key, val in solver_options.iteritems():
            opt.options[key]=val

        ######### MAIN SIMULATION LOOP ###############
        t = 0
        step_iter = 0
        valve_status_changed = False
        while t < self._n_timesteps and step_iter < self._max_step_iter:
            if t == 0:
                first_timestep = True
                last_tank_head = {}
                for tank_name, tank in self._wn.nodes(Tank):
                    last_tank_head[tank_name] = tank.elevation + tank.init_level
            else:
                first_timestep = False

            # Get demands
            current_demands = {n_name: self._demand_dict[n_name, t] for n_name, n in self._wn.nodes(Junction)}

            links_closed_by_time = []
            # Get time controls
            for link_name, status in self._link_status.iteritems():
                if not status[t]:
                    links_closed_by_time.append(link_name)

            # Apply conditional controls, THESE WILL OVERIDE TIME CONTROLS
            if not first_timestep:
                [pumps_closed_by_rule, links_closed_by_time] = self._apply_conditional_controls(instance,
                                                                                                pumps_closed_by_rule,
                                                                                                links_closed_by_time,
                                                                                                t)
                # Apply tank controls
                if self._tank_controls:
                    links_closed_by_tank_controls = self._apply_tank_controls(instance)

            if self._pump_outage:
                pumps_closed_by_outage = self._apply_pump_outage(t)



            #print "Pumps closed: ", pumps_closed
            #print "Pipes Closed: ", pipes_closed

            # Combine list of closed links
            links_closed = links_closed_by_time \
                           + pumps_closed_by_rule \
                           + pumps_closed_by_outage \
                           + links_closed_by_tank_controls


            #for i in links_closed:
            #    print "Link: ", i, " closed"

            timedelta = results.time[t]
            if step_iter == 0:
                print "Running Hydraulic Simulation at time", timedelta, " ..."
            else:
                print "\t Trial", str(step_iter+1), "Running Hydraulic Simulation at time", timedelta, " ..."
            t0 = time.time()
            # Do it in the constructor? make it an attribute?
            model = self.build_hydraulic_model_at_instant(last_tank_head,
                                                          current_demands,
                                                          first_timestep,
                                                          links_closed,
                                                          modified_hazen_williams) # Modified Hazen-Williams function
            #print "####### Total build model time : ", time.time() - t0

            # Initial conditions
            # Fix the head in a reservoir
            for n in model.reservoirs:
                reservoir_head = self._wn.get_node(n).base_head
                model.head[n].value = reservoir_head
                model.head[n].fixed = True

            # Fix the initial head in a Tank
            if first_timestep:
                for n in model.tanks:
                    tank = self._wn.get_node(n)
                    tank_initial_head = tank.elevation + tank.init_level
                    model.head[n].value = tank_initial_head
                    model.head[n].fixed = True

            # Add OBJECTIVE
            def obj_rule(model):
                expr = 0
                for n in model.junctions:
                    #expr += (model.demand_actual[n]-model.demand_required[n])**2
                    expr += (model.demand_actual[n])**1
                return expr
            #model.obj = Objective(rule=obj_rule, sense=maximize)
            model.obj = Objective(expr=1, sense=minimize)

            #print "Created Obj: ", time.time() - t0
            ####### CREATE INSTANCE AND SOLVE ########
            instance = model.create()
            #print "Model creation: ", time.time() - t0

            # Initializing from previous timestep
            if not first_timestep:
                #instance.load(pyomo_results)
                self._initialize_from_pyomo_results(instance, last_instance)

            #print "Initializing pyomo instance: ", time.time() - t0

            # Set flow to 0 if link is closed
            for l in instance.links:
                if l in links_closed:
                    instance.flow[l].fixed = True
                    instance.flow[l].value = 0
                else:
                    instance.flow[l].fixed = False
                    #model.headloss[l,t].value = 0.0
                    #model.headloss[l,t].fixed = True

            #print "Fixing flow: ", time.time() - t0

            # Pressure Reducing Valve (PRV) constraints based on status
            for l in model.valves:
                valve = self._wn.get_link(l)
                start_node = valve.start_node()
                end_node = valve.end_node()
                pressure_setting = valve.setting
                status = self._valve_status[l]
                if status == 'CLOSED':
                    model.flow[l].value = 0.0
                    model.flow[l].fixed = True
                elif status == 'OPEN':
                    diameter = valve.diameter
                    valve_resistance_coefficient = 0.02*self._Dw_k*(diameter*2)/(diameter**5)
                    setattr(model, 'valve_headloss_'+str(l), Constraint(expr=valve_resistance_coefficient*model.flow[l]**2 == model.head[start_node] - model.head[end_node]))
                elif status == 'ACTIVE':
                    end_node_obj = self._wn.get_node(end_node)
                    model.head[end_node].value = pressure_setting + end_node_obj.elevation
                    model.head[end_node].fixed = True

            #print "PRV constraint: ", time.time() - t0


            #t0 = time.time()
            # Solve pyomo model
            #instance.pprint()
            pyomo_results = opt.solve(instance, tee=False)
            instance.load(pyomo_results)

            #print "Solution time: ", time.time() - t0

            #t0 = time.time()
            # Set valve status based on pyomo results
            if self._wn._num_valves != 0:
                valve_status_changed = self._set_valve_status(instance)
            #print "Setting valve status: ", time.time() - t0

            #t0 = time.time()
            #print self._valve_status
            # Resolve the same timestep if the valve status has changed
            if valve_status_changed:
                step_iter += 1
            else:
                step_iter = 0
                t += 1
                # Load last tank head
                for tank_name, tank in self._wn.nodes(Tank):
                    last_tank_head[tank_name] = instance.head[tank_name].value
                # Load results into self._pyomo_sim_results
                self._append_pyomo_results(instance, timedelta)
                last_instance = copy.copy(instance)
            #print "Appending pyomo results: ", time.time() - t0

        if step_iter == self._max_step_iter:
            raise RuntimeError('Simulation did not converge at timestep ' + str(t))

        ######## END OF MAIN SIMULATION LOOP ##########

        #opt.options['mu_strategy'] = 'monotone'
        #opt.options['mu_init'] = 1e-6

        #t0 = time.time()


        # Save results into the results object
        node_data_frame = pd.DataFrame({'time':     self._pyomo_sim_results['node_times'],
                                        'node':     self._pyomo_sim_results['node_name'],
                                        'demand':   self._pyomo_sim_results['node_demand'],
                                        'head':     self._pyomo_sim_results['node_head'],
                                        'pressure': self._pyomo_sim_results['node_pressure'],
                                        'type':     self._pyomo_sim_results['node_type']})

        node_pivot_table = pd.pivot_table(node_data_frame,
                                          values=['demand', 'head', 'pressure', 'type'],
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

        #print " Converting results to pivot table: ", time.time() - t0

        return results

    def _read_pyomo_results(self, instance, pyomo_results):
        """
        Reads pyomo results from a pyomo instance and loads them into
        a network results object.

        Parameters
        -------
        instance : Pyomo model instance
            Pyomo instance after instance.load() has been called.
        pyomo_results : Pyomo results object
            Pyomo results object

        Return
        ------
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
                                          end=str(self._sim_duration_sec) + ' minutes',
                                          freq=str(self._hydraulic_step_sec/60) + 'min')
        # Load link data
        link_name = []
        flowrate = []
        velocity = []
        times = []
        link_type = []
        for l in instance.links:
            link = self._wn.get_link(l)
            for t in instance.time:
                link_name.append(l)
                link_type.append(self._get_link_type(l))
                times.append(results.time[t])
                flow_l_t = instance.flow[l,t].value
                flowrate.append(flow_l_t)
                if isinstance(link, Pipe):
                    velocity_l_t = 4.0*abs(flow_l_t)/(math.pi*link.diameter**2)
                else:
                    velocity_l_t = 0.0
                velocity.append(velocity_l_t)

        link_data_frame = pd.DataFrame({'time': times,
                                        'link': link_name,
                                        'flowrate': flowrate,
                                        'velocity': velocity,
                                        'type': link_type})

        link_pivot_table = pd.pivot_table(link_data_frame,
                                              values=['flowrate', 'velocity', 'type'],
                                              index=['link', 'time'],
                                              aggfunc= lambda x: x)
        results.link = link_pivot_table

        # Load node data
        node_name = []
        head = []
        pressure = []
        demand = []
        times = []
        node_type = []
        for n in instance.nodes:
            node = self._wn.get_node(n)
            for t in instance.time:
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
                elif isinstance(node, Reservoir):
                    demand.append(instance.reservoir_demand[n,t].value)
                elif isinstance(node, Tank):
                    demand.append(instance.tank_net_inflow[n,t].value)
                else:
                    demand.append(0.0)

        node_data_frame = pd.DataFrame({'time': times,
                                        'node': node_name,
                                        'demand': demand,
                                        'head': head,
                                        'pressure': pressure,
                                        'type': node_type})

        node_pivot_table = pd.pivot_table(node_data_frame,
                                          values=['demand', 'head', 'pressure', 'type'],
                                          index=['node', 'time'],
                                          aggfunc= lambda x: x)
        results.node = node_pivot_table

        return results


    def _append_pyomo_results(self, instance, time):
        """
        Reads pyomo results from a pyomo instance and loads them into
        the pyomo_sim_results dictionary.

        Parameters
        -------
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
                pressure_n = abs(head_n - node.elevation)
            if isinstance(node, Junction):
                demand = instance.demand_actual[n].value
            elif isinstance(node, Reservoir):
                demand = instance.reservoir_demand[n].value
            elif isinstance(node, Tank):
                demand = instance.tank_net_inflow[n].value
            else:
                demand = 0.0

            if head_n < -1e4:
                pressure_n = 0.0
                head_n = node.elevation
            self._pyomo_sim_results['node_name'].append(node_name)
            self._pyomo_sim_results['node_type'].append(node_type)
            self._pyomo_sim_results['node_times'].append(time)
            self._pyomo_sim_results['node_head'].append(head_n)
            self._pyomo_sim_results['node_demand'].append(demand)
            self._pyomo_sim_results['node_pressure'].append(pressure_n)


    def _apply_conditional_controls(self, instance, pumps_closed, pipes_closed, t):
        for link_name_k, value in self._wn.conditional_controls.iteritems():
            open_above = value['open_above']
            open_below = value['open_below']
            closed_above = value['closed_above']
            closed_below = value['closed_below']
            # If link is closed and the tank level goes below threshold, then open the link
            for i in open_below:
                node_name_i = i[0]
                value_i = i[1]
                tank_i = self._wn.get_node(node_name_i)
                current_tank_level = instance.head[node_name_i].value - tank_i.elevation
                if link_name_k in pumps_closed:
                    if current_tank_level <= value_i:
                        pumps_closed = [j for j in pumps_closed if j != link_name_k]
                        #print "Pump ", link_name_k, " opened"
                        # Overriding time controls
                        if link_name_k in pipes_closed:
                            pipes_closed = [m for m in pipes_closed if m != link_name_k]
                            # If the links base status is closed then
                            # all rest of timestep should be opened
                            link = self._wn.get_link(link_name_k)
                            if link.get_base_status() == 'CLOSED':
                                for tt in xrange(t, self._n_timesteps):
                                    self._link_status[link_name_k][tt] = True

            # If link is open and the tank level goes above threshold, then close the link
            for i in closed_above:
                node_name_i = i[0]
                value_i = i[1]
                tank_i = self._wn.get_node(node_name_i)
                current_tank_level = instance.head[node_name_i].value - tank_i.elevation
                if link_name_k not in pumps_closed and current_tank_level >= value_i:
                    pumps_closed.append(link_name_k)
                    #print "Pump ", link_name_k, " closed"
            # If link is closed and tank level goes above threshold, then open the link
            for i in open_above:
                node_name_i = i[0]
                value_i = i[1]
                tank_i = self._wn.get_node(node_name_i)
                current_tank_level = instance.head[node_name_i].value - tank_i.elevation
                if link_name_k in pumps_closed:
                    if current_tank_level >= value_i:
                        pumps_closed = [j for j in pumps_closed if j != link_name_k]
                        #print "Pump ", link_name_k, " opened"
                        if link_name_k in pipes_closed:
                            pipes_closed = [m for m in pipes_closed if m != link_name_k]
                            # If the links base status is closed then
                            # all rest of timestep should be opened
                            link = self._wn.get_link(link_name_k)
                            if link.get_base_status() == 'CLOSED':
                                for tt in xrange(t, self._n_timesteps):
                                    self._link_status[link_name_k][tt] = True

            # If link is open and the tank level goes below threshold, then close the link
            for i in closed_below:
                node_name_i = i[0]
                value_i = i[1]
                tank_i = self._wn.get_node(node_name_i)
                current_tank_level = instance.head[node_name_i].value - tank_i.elevation
                if link_name_k not in pumps_closed and current_tank_level <= value_i:
                    pumps_closed.append(link_name_k)
                    #print "Pump ", link_name_k, " closed"

        return [pumps_closed, pipes_closed]

    def _apply_pump_outage(self, t):

        pumps_closed_by_outage = []
        time_t = self._hydraulic_step_sec*t

        for pump_name, time_tuple in self._pump_outage.iteritems():
            if time_t >= time_tuple[0] and time_t <= time_tuple[1]:
                pumps_closed_by_outage.append(pump_name)

        return pumps_closed_by_outage

    def _apply_tank_controls(self, instance):

        pipes_closed_by_tank = []

        for tank_name, control_info in self._tank_controls.iteritems():
            link_name_to_tank = control_info['link_name']
            link_to_tank = self._wn.get_link(link_name_to_tank)
            if isinstance(link_to_tank, Pump):
                warnings.warn('Pump is connected directly to tank!. '
                              'This may lead to issues when tank level goes'
                              'below minimum.')
            head_in_tank = instance.head[tank_name].value
            node_next_to_tank = control_info['node_name']
            min_tank_head = control_info['min_head']
            head_at_next_node = instance.head[node_next_to_tank].value
            # make link closed if the tank head is below min and
            # the head at connected node is below this minimum. That is,
            # flow will be out of the tank
            if head_in_tank <= min_tank_head and head_at_next_node <= head_in_tank:
                pipes_closed_by_tank.append(link_name_to_tank)

        return pipes_closed_by_tank

    def _set_valve_status(self, instance):
        """
        Change status of the valves based on the results obtained from pyomo
        simulation.

        Parameters
        -------
        instance : pyomo model instance

        Return
        ------
        valve_status_change : bool
            True if there was a change in valve status, False otherwise.

        """
        valve_status_changed = False
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
                    self._valve_status[valve_name] = 'CLOSED'
                    valve_status_changed = True
                elif instance.head[start_node].value < head_sp - self._Htol:
                    self._valve_status[valve_name] = 'OPEN'
                    valve_status_changed = True
            elif status == 'OPEN':
                if instance.flow[valve_name].value < -self._Qtol:
                    self._valve_status[valve_name] = 'CLOSED'
                    valve_status_changed = True
                elif instance.head[start_node].value > head_sp + self._Htol:
                    self._valve_status[valve_name] = 'ACTIVE'
                    valve_status_changed = True
            elif status == 'CLOSED':
                if instance.head[start_node].value > instance.head[end_node].value + self._Htol \
                    and instance.head[start_node].value < head_sp - self._Htol:
                    self._valve_status[valve_name] = 'OPEN'
                    valve_status_changed = True
                elif instance.head[start_node].value > instance.head[end_node].value + self._Htol \
                    and instance.head[end_node].value < head_sp - self._Htol:
                    self._valve_status[valve_name] = 'ACTIVE'
                    valve_status_changed = True

        return valve_status_changed

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
        results.simulator_options['type'] = 'PYOMO'
        results.simulator_options['start_time'] = self._sim_start_sec
        results.simulator_options['duration'] = self._sim_duration_sec
        results.simulator_options['pattern_start_time'] = self._pattern_start_sec
        results.simulator_options['hydraulic_time_step'] = self._hydraulic_step_sec
        results.simulator_options['pattern_time_step'] = self._pattern_step_sec

