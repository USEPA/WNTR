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
"""

try:
    from pyomo.environ import *
    from pyomo.core import *
    from pyomo.core.base.expr import Expr_if
    from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
except ImportError:
    raise ImportError('Error importing pyomo while running pyomo simulator.'
                      'Make sure pyomo is installed and added to path.')
import math
from WaterNetworkSimulator import *
import pandas as pd
from six import iteritems
import time

#from time_utils import * 
#from pyomo_utils import CheckInstanceFeasibility

class PyomoSimulator(WaterNetworkSimulator):
    """
    Pyomo simulator inherited from Water Network Simulator.
    """


    def __init__(self, wn, PD_or_DD='DEMAND DRIVEN'):
        """
        Pyomo simulator class.

        Parameters
        ---------
        wn : Water Network Model
            A water network model.
        """
        WaterNetworkSimulator.__init__(self, wn, PD_or_DD)

        # Global constants
        self._Hw_k = 10.67 # Hazen-Williams resistance coefficient in SI units = 4.727 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.
        self._Dw_k = 0.0826 # Darcy-Weisbach constant in SI units = 0.0252 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.
        self._Htol = 0.00015 # Head tolerance in meters.
        self._Qtol = 2.8e-5 # Flow tolerance in m^3/s.
        self._g = 9.81 # Acceleration due to gravity

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


    def build_hydraulic_model(self, modified_hazen_williams=True, external_link_statuses=None, calibrated_vars=None):
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
        first_timestep = 0 
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
                time_sec = t*model.timestep
                return 0.3048 if self.is_link_open(l,time_sec) else 0.0  # Flow in pipe initialized to 1 ft/s
            elif l in model.pumps:
                pump = wn.get_link(l)
                if pump.info_type == 'HEAD':
                    return pump.get_design_flow()
                else:
                    return 0.3048

        def flow_bounds_rule(model, l, t):
            if l in model.pumps:
                return (0.0, None)
            else:
                return (None, None)
                

        model.flow = Var(model.links, model.time, within=Reals, initialize=flow_init_rule, bounds = flow_bounds_rule)

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
        model.demand_actual = Var(model.junctions, model.time, within=Reals, initialize=init_demand_rule,bounds=(0.0,None))

        ############## CONSTRAINTS #####################
        t0 = time.time()
        
        def is_link_open(link_name, link_type, time_seconds):
            if external_link_statuses is None:
                return self.is_link_open(link_name,time_seconds)
            else:
                return True if external_link_statuses[link_type][link_name][time_seconds]==1 else False

        def get_link_status(link_name, link_type, time_seconds):
            if external_link_statuses is None:
                return self.give_link_status(link_name,time_seconds)
            else:
                if external_link_statuses[link_type][link_name][time_seconds]==1:
                    return 'OPEN'
                elif external_link_statuses[link_type][link_name][time_seconds]==2:
                    return 'ACTIVE'
                elif external_link_statuses[link_type][link_name][time_seconds]==0:
                    return 'CLOSED'
                else:
                    raise RuntimeError('Not valid case for link status function in build_hydraulic_model.')

        t0 = time.time()
        # Mass Balance
        if calibrated_vars is not None:
            model.demand_estimated_nodes = calibrated_vars['demand']
            model.unestimated_nodes = [n for n in model.junctions if n not in model.demand_estimated_nodes]
        else:
            model.unestimated_nodes = [n for n in model.junctions]

        for n in model.unestimated_nodes:
            for t in model.time:
                model.demand_actual[n,t].value = model.demand_required[n,t]
                model.demand_actual[n,t].fixed = True

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
                return expr == model.demand_actual[n,t]
            elif isinstance(node, Tank):
                return expr == model.tank_net_inflow[n,t]
            elif isinstance(node, Reservoir):
                return expr == model.reservoir_demand[n,t]

        model.node_mass_balance = Constraint(model.nodes, model.time, rule=node_mass_balance_rule)
        
        print "Time to build mass balance constraint: ", time.time()-t0

        t0 = time.time()
        # pipe roughness equations
        if calibrated_vars is not None:
            model.calibrate_pipes = calibrated_vars['roughness']
            model.uncalibrated_pipes = [l for l in model.pipes if l not in model.calibrate_pipes]
        else:
            model.calibrate_pipes = list()
            model.uncalibrated_pipes = [l for l in model.pipes]

        # variable for roughness calibration
        model.var_roughness = Var(model.pipes, within=NonNegativeReals, initialize=100)

        for l in model.uncalibrated_pipes:
            pipe = wn.get_link(l)
            model.var_roughness[l].value = pipe.roughness
            model.var_roughness[l].fixed = True

        model.pipe_headloss = ConstraintList()
        for l in model.pipes:
            pipe = wn.get_link(l)
            # initialize roughness 
            #model.var_roughness[l].value = pipe.roughness
            pipe_resistance_coeff = self._Hw_k*(model.var_roughness[l]**(-1.852))*(pipe.diameter**(-4.871))*pipe.length # Hazen-Williams
            start_node = pipe.start_node()
            end_node = pipe.end_node()
            for t in model.time:
                time_sec =t*self._hydraulic_step_sec
                if is_link_open(l,'pipe',time_sec):
                    #print l,t
                    if modified_hazen_williams:
                        #setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                        #                                              *pipe_resistance_coeff*LossFunc(abs(model.flow[l,t])) == model.head[start_node,t] - model.head[end_node,t]))
                        exprn = Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1) * pipe_resistance_coeff*LossFunc(abs(model.flow[l,t])) == model.head[start_node,t] - model.head[end_node,t]
                    else:
                        #setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=pipe_resistance_coeff*model.flow[l,t]*(abs(model.flow[l,t]))**0.852 == model.head[start_node,t] - model.head[end_node,t]))
                        exprn = pipe_resistance_coeff*model.flow[l,t]*(abs(model.flow[l,t]))**0.852 == model.head[start_node,t] - model.head[end_node,t]
                    model.pipe_headloss.add(exprn)

        # Head gain provided by the pump is implemented as negative headloss
        model.pump_headloss = ConstraintList()
        for l in model.pumps:
            pump = wn.get_link(l)
            start_node = pump.start_node()
            end_node = pump.end_node()
            if pump.info_type == 'HEAD':
                A, B, C = pump.get_head_curve_coefficients()
                for t in model.time:
                    time_sec = t*self._hydraulic_step_sec
                    if is_link_open(l,'pump',time_sec):
                        #setattr(model, 'pump_negative_headloss_'+str(l)+'_'+str(t), Constraint(expr=model.head[start_node,t] - model.head[end_node,t] == (-1.0*A + B*(model.flow[l,t]**C))))
                        exprn = model.head[start_node,t] - model.head[end_node,t] == (-1.0*A + B*(model.flow[l,t]**C))
                        model.pump_headloss.add(exprn)
                    else:
                        model.flow[l,t].value = 0.0
                        model.flow[l,t].fixed = True
            elif pump.info_type == 'POWER':
                power = pump.power
                for t in model.time:
                    time_sec = t*self._hydraulic_step_sec
                    if is_link_open(l,'pump',time_sec):
                        exprn = (model.head[start_node,t] - model.head[end_node,t])*model.flow[l,t]*self._g*1000.0 == -power
                        model.pump_headloss.add(exprn)
                    else:
                        model.flow[l,t].value = 0.0
                        model.flow[l,t].fixed = True
                        #setattr(model, 'pump_negative_headloss_'+str(l), Constraint(expr=(model.head[start_node] - model.head[end_node])*model.flow[l]*self._g*1000.0 == -pump.power))
        print "Time to build pipe-pump headloss constraints: ", time.time()-t0

        #print "Created Node balance: ", time.time() - t0
        
        """
        # Flow in a pump should always be positive
        def pump_positive_flow_rule(model,l,t):
            return model.flow[l,t] >= 0
        model.pump_positive_flow_bounds = Constraint(model.pumps, model.time, rule=pump_positive_flow_rule)
        """

        t0 = time.time()
        def tank_dynamics_rule(model, n, t):
            if t is first_timestep:
                return Constraint.Skip
            else:
                tank = wn.get_node(n)
                return (model.tank_net_inflow[n,t]*model.timestep*4.0)/(pi*(tank.diameter**2)) == model.head[n,t]-model.head[n,t-1]
        model.tank_dynamics = Constraint(model.tanks, model.time, rule=tank_dynamics_rule)
        print "Time to build tank Euler constraints: ", time.time()-t0

        t0 = time.time()
        model.valve_status = ConstraintList()
        for l in model.valves:
                valve = self._wn.get_link(l)
                start_node = valve.start_node()
                end_node = valve.end_node()
                pressure_setting = valve.setting

                # TO BE CHANGED to get status based on time controls!!
                for t in model.time:
                    time_with_units = t*self._hydraulic_step_sec
                    status = get_link_status(l,'valve',time_with_units)
                    if status == 'CLOSED':
                        model.flow[l,t].value = 0.0
                        model.flow[l,t].fixed = True
                    elif status == 'OPEN':
                        diameter = valve.diameter
                        valve_resistance_coefficient = 0.02*self._Dw_k*(diameter*2)/(diameter**5)
                        #setattr(model, 'valve_headloss_'+str(l), Constraint(expr=valve_resistance_coefficient*model.flow[l,t]**2 == model.head[start_node,t] - model.head[end_node,t]))
                        model.valve_status.add(valve_resistance_coefficient*model.flow[l,t]**2 == model.head[start_node,t] - model.head[end_node,t])
                    elif status == 'ACTIVE':
                        end_node_obj = self._wn.get_node(end_node)
                        model.head[end_node,t].value = pressure_setting + end_node_obj.elevation
                        model.head[end_node,t].fixed = True
        print "Time to build valve headloss constraints: ", time.time()-t0


        #print "Created Tank Dynamics: ", time.time() - t0

        return model


    def build_hydraulic_model_at_instant(self,
                                         last_tank_head,
                                         nodal_demands,
                                         first_timestep,
                                         links_closed,
                                         pumps_closed_by_outage,
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


        def pressure_dependent_demand_nl(full_demand, p, PF, P0):
            # Pressure driven demand equation
            delta = 0.1
            # Defining Line 1
            a1 = 1e-5
            b1 = full_demand

            def L1(x):
                return a1*x + b1

            # Defining PDD function

            def PDD(x):
                return full_demand*math.sqrt((x - P0)/(PF - P0))

            def PDD_deriv(x):
                return (full_demand/2)*(1/(PF - P0))*(1/math.sqrt((x - P0)/(PF - P0)))

            # Define Line 2
            a2 = 1e-5
            b2 = 0.0
            def L2(x):
                return a2*x + b2

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
            rhs1 = np.array([y1, y2, a2, PDD_deriv(x2)])
            c1 = np.linalg.solve(A1, rhs1)
            x3 = PF - x_gap*delta
            y3 = PDD(x3)
            x4 = PF + x_gap*delta
            y4 = L1(x4)
            A2 = A(x3, x4)
            rhs2 = np.array([y3, y4, PDD_deriv(x3), a1])
            c2 = np.linalg.solve(A2, rhs2)

            def smooth_polynomial_lhs(p_):
                return c1[0]*p_**3 + c1[1]*p_**2 + c1[2]*p_ + c1[3]

            def smooth_polynomial_rhs(p_):
                return c2[0]*p_**3 + c2[1]*p_**2 + c2[2]*p_ + c2[3]


            return Expr_if(IF=p <= x1, THEN=L2(p),
               ELSE=Expr_if(IF=p <= x2, THEN=smooth_polynomial_lhs(p),
                            ELSE=Expr_if(IF=p <= x3, THEN=PDD(p),
                                         ELSE=Expr_if(IF=p <= x4, THEN=smooth_polynomial_rhs(p),
                                                      ELSE=L1(p)))))

            """
            return Expr_if(IF=p <= x3, THEN=PDD(p),
                           ELSE=Expr_if(IF=p <= x4, THEN=smooth_polynomial_rhs(p),
                                        ELSE=L1(p)))
            """
            """
            return Expr_if(IF=p <= PF, THEN=PDD(p),
                           ELSE=L1(p))
            """


        def pressure_dependent_demand_linear(full_demand, p, PF, P0):

            delta = 0.1
            # Defining Line 1
            a1 = 1e-11
            b1 = full_demand

            def L1(x):
                return a1*x + b1

            # Defining PDD function
            """
            def PDD(x):
                return full_demand*math.sqrt((x - P0)/(PF - P0))

            def PDD_deriv(x):
                return (full_demand/2)*(1/(PF - P0))*(1/math.sqrt((x - P0)/(PF - P0)))
            """
            # Linear PDD Function
            def PDD(x):
                return full_demand*((x - P0)/(PF - P0))

            def PDD_deriv(x):
                return (full_demand)*(1/(PF - P0))

            # Define Line 2
            a2 = 1e-11
            b2 = 0.0
            def L2(x):
                return a2*x + b2

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
            rhs1 = np.array([y1, y2, a2, PDD_deriv(x2)])
            c1 = np.linalg.solve(A1, rhs1)
            x3 = PF - x_gap*delta
            y3 = PDD(x3)
            x4 = PF + x_gap*delta
            y4 = L1(x4)
            A2 = A(x3, x4)
            rhs2 = np.array([y3, y4, PDD_deriv(x3), a1])
            c2 = np.linalg.solve(A2, rhs2)

            def smooth_polynomial_lhs(p_):
                return c1[0]*p_**3 + c1[1]*p_**2 + c1[2]*p_ + c1[3]

            def smooth_polynomial_rhs(p_):
                return c2[0]*p_**3 + c2[1]*p_**2 + c2[2]*p_ + c2[3]

            """
            print "X1: ", x1
            print "X2: ", x2
            print "X3: ", x3
            print "X4: ", x4
            print "L1: ", a1, b1
            print "PDD: ", (full_demand)*(1/(PF - P0))
            print "L2: ", a2, b2
            print "P1: ", c1[0], c1[1], c1[2], c1[3]
            print "P2: ", c2[0], c2[1], c2[2], c2[3]
            exit()
            """

            return Expr_if(IF=p <= x1, THEN=L2(p),
               ELSE=Expr_if(IF=p <= x2, THEN=smooth_polynomial_lhs(p),
                            ELSE=Expr_if(IF=p <= x3, THEN=PDD(p),
                                         ELSE=Expr_if(IF=p <= x4, THEN=smooth_polynomial_rhs(p),
                                                      ELSE=L1(p)))))

            """
            return Expr_if(IF=p <= x3, THEN=PDD(p),
                           ELSE=Expr_if(IF=p <= x4, THEN=smooth_polynomial_rhs(p),
                                        ELSE=L1(p)))
            """
            """
            return Expr_if(IF=p <= PF, THEN=PDD(p),
                           ELSE=L1(p))
            """

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
        model.leaks = Set(initialize = [n for n, N in wn.nodes(Leak)])
        model.reservoirs = Set(initialize=[n for n, N in wn.nodes(Reservoir)])
        # LINKS
        model.links = Set(initialize=[name for name, link in wn.links()])
        model.pumps = Set(initialize=[l for l, L in wn.links(Pump)])
        model.valves = Set(initialize=[l for l, L in wn.links(Valve)])
        model.pipes = Set(initialize=[l for l, L in wn.links(Pipe)])

        #print "Created Sets: ", time.time() - t0

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
        def flow_bounds_rule(model, l):
            if l in model.pumps and l not in pumps_closed_by_outage:
                return (0.0, None)
            else:
                return (None, None)
        model.flow = Var(model.links, within=Reals, initialize=flow_init_rule, bounds=flow_bounds_rule)

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
            if n in model.junctions:
                if self._pressure_driven:
                    return wn.get_node(n).elevation + wn.get_node(n).PF
                else:
                    return wn.get_node(n).elevation
            elif n in model.tanks:
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
            if l in links_closed:
                pass
            else:
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
            if l not in links_closed:
                if l in pumps_closed_by_outage:
                    # replace pump by pipe of length 30m, diameter 10m, and roughness coefficient of 200
                    pipe_resistance_coeff = self._Hw_k*(200.0**(-1.852))*(10**(-4.871))*30.0 # Hazen-Williams
                    if modified_hazen_williams:
                        #setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=Expr_if(IF=model.flow[l]>0, THEN=1, ELSE=-1)
                        #        *pipe_resistance_coeff*LossFunc(abs(model.flow[l])) == model.head[start_node] - model.head[end_node]))
                        setattr(model, 'pipe_headloss_'+str(l), Constraint(expr= 0.0 == model.head[start_node] - model.head[end_node]))
                    else:
                        setattr(model, 'pipe_headloss_'+str(l), Constraint(expr=pipe_resistance_coeff*model.flow[l]*(abs(model.flow[l]))**0.852 == model.head[start_node] - model.head[end_node]))
                else:
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
            elif isinstance(node, Leak):
                return expr**2 == node.leak_discharge_coeff**2*node.area**2*(2*self._g)*(model.head[n])
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
            if model.demand_required[j] == 0.0:
                #return Constraint.Skip
                return model.demand_actual[j] == 0.0
            else:
                #return pressure_dependent_demand_nl(model.demand_required[j], model.head[j]-junction.elevation, junction.PF, junction.P0) == model.demand_actual[j]
                return pressure_dependent_demand_linear(model.demand_required[j], model.head[j]-junction.elevation, junction.PF, junction.P0) == model.demand_actual[j]

        def demand_driven_rule(model, j):
            return model.demand_actual[j] == model.demand_required[j]

        if self._pressure_driven:
            model.pressure_driven_demand = Constraint(model.junctions, rule=pressure_driven_demand_rule)
        else:
            model.pressure_driven_demand = Constraint(model.junctions, rule=demand_driven_rule)

        """
        # Fixed zero demand
        for j in model.junctions:
            if model.demand_required[j] == 0.0:
                model.demand_actual[j].value = 0.0
                model.demand_actual[j].fixed = True
        """
        """
        # Positive demand constraint
        def demand_bounds_rule(model, j):
            return model.demand_actual[j] >= 1e-4
        model.demand_bounds = Constraint(model.junctions, rule=demand_bounds_rule)
        """

        return model.create()



    def run_calibration(self,
                        measurements,
                        calibrated_vars, 
                        weights = {'tank_level':1.0, 'pressure':1.0,'head':1.0, 'flowrate':1.0, 'demand':1.0},
                        solver='ipopt', 
                        solver_options={}, 
                        modified_hazen_williams=True,
                        external_link_statuses=None,
                        init_dict = None,
                        regularization_dict = None):
        import numpy as np
       
        
        # Initialise demand dictionaries and link statuses
        self._initialize_simulation()

        if not calibrated_vars['demand'] and not calibrated_vars['roughness']:
            raise RuntimeError("List of node-names link-names for calibration is required.")

        # define base model
        model = self.build_hydraulic_model(modified_hazen_williams,
            external_link_statuses = external_link_statuses,
            calibrated_vars = calibrated_vars)
        # define base network
        wn = self._wn

        def is_link_open(link_name, link_type, time_seconds):
            if external_link_statuses is None:
                return self.is_link_open(link_name,time_seconds)
            else:
                return True if external_link_statuses[link_type][link_name][time_seconds]!=0 else False

        # Temporal the calibrator should check if initial values are provided if not they should be fixed

        # for the reservoir should look for the head at any time and fix it for all times...
        # Fix the head in a reservoir
        for n in model.reservoirs:
            reservoir_head = wn.get_node(n).base_head
            for t in model.time:
                model.head[n,t].value = reservoir_head
                model.head[n,t].fixed = True

        # Look for initial values in data. If not provided should exit calibration
        # Fix the initial head in a Tank
        """
        for n in model.tanks:
            tank = wn.get_node(n)
            tank_initial_head = tank.elevation + tank.init_level
            t = min(model.time)
            model.head[n,t].value = tank_initial_head
            model.head[n,t].fixed = True
        """
        if len(model.tanks)>0:
            if 'tank' not in measurements.keys():
                raise RuntimeError("Provide level of all tanks in measurements at one timestep.")
            else:    
                if 'head' not in measurements['tank'].keys():
                    raise RuntimeError("Provide level of all tanks in measurements at one timestep.")
                else:
                    measured_tanks = zip(*measurements['tank']['head'].keys())
                    names = measured_tanks[0]
                    for n in model.tanks:
                        if n not in names:
                            raise RuntimeError("Provide level of tank " + str(n) +" in the measurements at one timestep.")

        # Fix to zero the nodes that have base demand zero
        """
        junctions_zero_base = wn.query_node_attribute('base_demand', np.equal, 0.0, node_type=Junction).keys()
        for n in junctions_zero_base:
            for t in model.time:
                model.demand_actual[n,t].value = 0.0
                model.demand_actual[n,t].fixed = True
        """ 
               
        ############### OBJECTIVE ########################
        def initialize_from_dictionary(model, measurements):

            time_step_inverse = 1.0/self._hydraulic_step_sec
            # initialize variables to measurements
            for tm in measurements.keys():
                type_params = measurements[tm].keys()
                if tm == 'tank':
                    for tp in type_params:
                        time_node_tuples = measurements[tm][tp].keys()
                        if tp == 'demand':
                            for node_time in time_node_tuples:
                                n = node_time[0]
                                t = node_time[1]*time_step_inverse
                                model.tank_net_inflow[n,t].value = measurements[tm][tp][node_time]
                        elif tp == 'pressure':
                            for node_time in time_node_tuples:
                                n = node_time[0]
                                t = node_time[1]*time_step_inverse
                                model.head[n,t].value = measurements[tm][tp][node_time] + wn.get_node(n).elevation
                        elif tp == 'head':
                            for node_time in time_node_tuples:
                                n = node_time[0]
                                t = node_time[1]*time_step_inverse
                                model.head[n,t].value = measurements[tm][tp][node_time]
                        else:
                            print 'WARNING: ',tp, ' not supported as a measurement for ', tm

                elif tm == 'reservoir':
                    for tp in type_params:
                        time_node_tuples = measurements[tm][tp].keys()
                        if tp == 'demand':
                            for node_time in time_node_tuples:
                                n = node_time[0]
                                t = node_time[1]*time_step_inverse
                                model.reservoir_demand[n,t].value = measurements[tm][tp][node_time]
                        elif tp == 'head':
                            for node_time in time_node_tuples:
                                n = node_time[0]
                                t = node_time[1]*time_step_inverse
                                model.head[n,t].value = measurements[tm][tp][node_time]
                        else:
                            print 'WARNING: ',tp, ' not supported as a measurement for ', tm

                elif tm == 'junction':
                    for tp in type_params:
                        time_node_tuples = measurements[tm][tp].keys()
                        if tp == 'demand':
                            for node_time in time_node_tuples:
                                n = node_time[0]
                                t = node_time[1]*time_step_inverse
                                model.demand_actual[n,t].value = measurements[tm][tp][node_time]
                        elif tp == 'pressure':
                            for node_time in time_node_tuples:
                                n = node_time[0]
                                t = node_time[1]*time_step_inverse
                                model.head[n,t].value = measurements[tm][tp][node_time] + wn.get_node(n).elevation
                        elif tp == 'head':
                            for node_time in time_node_tuples:
                                n = node_time[0]
                                t = node_time[1]*time_step_inverse
                                model.head[n,t].value = measurements[tm][tp][node_time]
                        else:
                            print 'WARNING: ',tp, ' not supported as a measurement for ', tm

                else:
                    # this take care of pipes pumps and valves
                    for tp in type_params:
                        time_link_tuples = measurements[tm][tp].keys()
                        if tp == 'flowrate':
                            for link_time in time_link_tuples:
                                l = link_time[0]
                                t = link_time[1]*time_step_inverse                        
                                if is_link_open(l,tm,link_time[1]):
                                    model.flow[l,t].value =  measurements[tm][tp][link_time]
                                else:
                                    model.flow[l,t].value =  0.0
                        else:
                            print 'WARNING: ',tp, ' not supported as a measurement for ', tm


        def build_objective_expression(model, measurements):
            ts_inv = 1.0/self._hydraulic_step_sec
            obj_expr = 0
            tol = 1e-4
            r_weight = copy.deepcopy(measurements)
            for nt in r_weight.keys():
                for param in r_weight[nt].keys():
                    for node_time in r_weight[nt][param].keys():
                        if not r_weight[nt][param][node_time]<tol and not  r_weight[nt][param][node_time]>-tol:
                            r_weight[nt][param][node_time] = 1.0/(r_weight[nt][param][node_time]*1e3)
                        else:
                            r_weight[nt][param][node_time] = 10.0
            # junction measurements
            tm = 'junction'
            junction_measures = measurements.get(tm)
            if junction_measures is not None:
                params = junction_measures.keys()
                tp = 'demand'
                if tp in params:
                    # Regularization term
                    obj_expr += sum(r_weight[tm][tp][nt]*(junction_measures[tp][nt]-model.demand_actual[nt[0],nt[1]*ts_inv])**2 for nt in junction_measures[tp].keys())*weights[tp]
                tp = 'head'
                if tp in params:
                    obj_expr += sum(r_weight[tm][tp][nt]*(junction_measures[tp][nt]-model.head[nt[0],nt[1]*ts_inv])**2 for nt in junction_measures[tp].keys())*weights[tp]
                tp = 'pressure'
                if tp in params:
                    obj_expr += sum(r_weight[tm][tp][nt]*((junction_measures[tp][nt]+wn.get_node(nt[0]).elevation)-model.head[nt[0],nt[1]*ts_inv])**2 for nt in junction_measures[tp].keys())*weights[tp]

            # tank measurements
            tm = 'tank'
            tank_measures = measurements.get(tm)
            if tank_measures is not None:
                params = tank_measures.keys()
                tp = 'head'
                if tp in params:
                    obj_expr += sum(r_weight[tm][tp][nt]*(tank_measures[tp][nt]-model.head[nt[0],nt[1]*ts_inv])**2 for nt in tank_measures[tp].keys())*weights['tank_level']
                tp = 'pressure'
                if tp in params:
                    obj_expr += sum(r_weight[tm][tp][nt]*((tank_measures[tp][nt]+wn.get_node(nt[0]).elevation)-model.head[nt[0],nt[1]*ts_inv])**2 for nt in tank_measures[tp].keys())*weights[tp]

            # link measurements
            link_types = ['valve','pipe','pump']
            for lt in link_types:
                link_measures = measurements.get(lt)
                if link_measures is not None:
                    params = link_measures.keys()
                    tp = 'flowrate'
                    if tp in params:
                        obj_expr += sum(r_weight[lt][tp][link_time]*(link_measures[tp][link_time]-model.flow[link_time[0],link_time[1]*ts_inv])**2 for link_time in link_measures[tp].keys())*weights[tp]

            return obj_expr

        t0 = time.time()
        # Initialization of variables
        # initialize variables to simulation result
        if init_dict is not None:
            initialize_from_dictionary(model, init_dict)
        # Override inizialization of variables that were measured
        initialize_from_dictionary(model, measurements)

        # Objective expression
        obj_expr = build_objective_expression(model, measurements)
        # add regularization term
        if regularization_dict is not None:
            obj_expr += 0.5*build_objective_expression(model, regularization_dict)

        model.obj = Objective(expr=obj_expr, sense=minimize)
        print "Time to build the objective: ", time.time()-t0 

        ####### CREATE INSTANCE AND SOLVE ########
        #model.pipe_headloss.pprint()
        #instance = model.create()
        instance = model
        
        #import pyomo_utils as pyu
        #pyu.CheckInstanceFeasibility(instance,1e-3)
        t0 = time.time()
        opt = SolverFactory(solver,solver_io='nl')
        #opt = SolverFactory(solver)
        # Set solver options
        for key, val in solver_options.iteritems():
            opt.options[key]=val    

        #opt.options['print_options_documentation']='yes'
        # Solve pyomo model
        pyomo_results = opt.solve(instance, tee=True,keepfiles=False)

        print opt._problem_files
        print "Solving. Timing: ", time.time()-t0
        #print pyomo_results['Solution']_problem_files
        #help(pyomo_results['Solution'])
        #print "Created results: ", time.time() - t0
        instance.load(pyomo_results)
        #instance.pprint()
        
        #r2 = opt.solve(instance, tee=True,keepfiles=False)
        # Load pyomo results into results object
        results = self._read_pyomo_results(instance, pyomo_results)

        return results

    def run_sim(self, solver='ipopt', solver_options={}, modified_hazen_williams=True, fixed_demands = None):
        
        """
        # Do it in the constructor? make it an attribute?
        model = self.build_hydraulic_model(modified_hazen_williams)

        #######################TEMPORAL#############################
        dateToTimestep = lambda DateTime: (((DateTime.days*24+DateTime.hours)*60+DateTime.minutes)*60+DateTime.seconds)/self._hydraulic_step_sec
        if fixed_demands is not None:
            nodes = fixed_demands.node.index.get_level_values('node').drop_duplicates()
            for n in nodes:
                if self._get_node_type(n) == 'junction':
                    times = fixed_demands.node['demand'][n].index
                    for dt in times:
                        t = dateToTimestep(dt)
                        model.demand_actual[n,t].value = fixed_demands.node['demand'][n][dt]
                        model.demand_actual[n,t].fixed = True

        ####################################################


        # Initial conditions
        # Fix the head in a reservoir
        for n in model.reservoirs:
            reservoir_head = self._wn.get_node(n).base_head
            for t in model.time:
                model.head[n,t].value = reservoir_head
                model.head[n,t].fixed = True
        """

        #print link_status
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

        # Assert conditional controls are only provided for Tanks
        # self._verify_conditional_controls_for_tank()

        # List of closed pump ids
        pumps_closed_by_rule = set([]) # Set of pumps that are closed by level controls defined in inp file
        pumps_closed_by_outage = set([]) # Set of pump closed by pump outage times provided by user
        links_closed_by_tank_controls = set([])  # Set of pipes closed when tank level goes below min
        closed_check_valves = set([]) # Set of closed check valves
        pumps_closed_by_drain_to_reservoir = set([]) # Set of link close because of reverse flow into the reservoir
        pumps_closed_by_low_flow = set([])

        # Create solver instance
        opt = SolverFactory(solver)
        # Set solver options
        for key, val in solver_options.iteritems():
            opt.options[key]=val
        opt.options['bound_relax_factor'] = 0.0

        ######### MAIN SIMULATION LOOP ###############
        t = 0
        step_iter = 0
        valve_status_changed = False
        check_valve_status_changed = False
        reservoir_link_closed_flag = False
        low_flow_pumps_closed_flag = False
        instance = None
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

            links_closed_by_time = set([])

            # Get time controls
            for link_name, status in self._link_status.iteritems():
                if not status[t]:
                    links_closed_by_time.add(link_name)

            # Apply conditional controls, THESE WILL OVERIDE TIME CONTROLS
            if not first_timestep:
                self._apply_conditional_controls(instance,
                                                 pumps_closed_by_rule,
                                                 links_closed_by_time,
                                                 t)
                # Apply tank controls
                if self._tank_controls:
                    self._apply_tank_controls(instance, links_closed_by_tank_controls, links_closed_by_time, t)

            if self._pump_outage:
                reservoir_link_closed_flag = self._apply_pump_outage(instance,
                                                                     pumps_closed_by_outage,
                                                                     links_closed_by_time,
                                                                     pumps_closed_by_drain_to_reservoir,
                                                                     links_closed_by_tank_controls,
                                                                     t)
                #self._override_tank_controls(links_closed_by_tank_controls, pumps_closed_by_outage)


            """
            # print controls
            print "Links closed by time controls: "
            for i in links_closed_by_time:
                print "\tLink: ", i, " closed"
            print "Links closed by conditional controls: "
            for i in pumps_closed_by_rule:
                print "\tLink: ", i, " closed"
            print "Pumps closed by outage: "
            for i in pumps_closed_by_outage:
                print "\tLink: ", i, " closed"
            print "Links closed by tank controls: "
            for i in links_closed_by_tank_controls:
                print "\tLink: ", i, " closed"
            print "Links closed by drain to reservoir:"
            for i in pumps_closed_by_drain_to_reservoir:
                print "\tLink: ", i, " closed"
            print "Pumps closed by low flow:"
            for i in pumps_closed_by_low_flow:
                print "\tLink: ", i, " closed"
            print "Valve Status: "
            print self._valve_status
            """

            # Combine list of closed links
            #links_closed = links_closed_by_time.union(pumps_closed_by_rule.union(pumps_closed_by_outage.union(links_closed_by_tank_controls.union(closed_check_valves))))
            #links_closed = pumps_closed_by_drain_to_reservoir.union(links_closed_by_time.union(pumps_closed_by_rule.union(links_closed_by_tank_controls.union(closed_check_valves))))
            links_closed = pumps_closed_by_low_flow.union(pumps_closed_by_drain_to_reservoir.union(links_closed_by_time.union(pumps_closed_by_rule.union(links_closed_by_tank_controls.union(closed_check_valves)))))
            #links_closed = pumps_closed_by_drain_to_reservoir.union(links_closed_by_time.union(pumps_closed_by_rule.union(closed_check_valves)))


            timedelta = results.time[t]
            if step_iter == 0:
                print "Running Hydraulic Simulation at time", timedelta, " ... "
            else:
                print "\t Trial", str(step_iter+1), "Running Hydraulic Simulation at time", timedelta, " ..."
            t0 = time.time()
            # Do it in the constructor? make it an attribute?
            model = self.build_hydraulic_model_at_instant(last_tank_head,
                                                          current_demands,
                                                          first_timestep,
                                                          links_closed,
                                                          pumps_closed_by_outage,
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

            #t0 = time.time()
            #print "Created Obj: ", time.time() - t0
            ####### CREATE INSTANCE ########
            #instance = model.create()
            instance = model # Create does not need to be called for NLP ?
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
                    #instance.flow[l].value = self._Qtol/10.0
                    instance.flow[l].value = 0.0
                else:
                    instance.flow[l].fixed = False

            # Pressure Reducing Valve (PRV) constraints based on status
            for l in model.valves:
                valve = self._wn.get_link(l)
                start_node = valve.start_node()
                end_node = valve.end_node()
                pressure_setting = valve.setting
                status = self._valve_status[l]
                if status == 'CLOSED':
                    #model.flow[l].value = self._Qtol/10.0
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
                else:
                    raise RuntimeError("Valve Status not recognized.")

            pyomo_results = opt.solve(instance, tee=False, keepfiles=False)
            instance.load(pyomo_results)

            #CheckInstanceFeasibility(instance, 1e-6)

            if (pyomo_results.solver.status == SolverStatus.ok) and (pyomo_results.solver.termination_condition == TerminationCondition.optimal):
                low_flow_pumps_closed_flag = False
            else:
                low_flow_pumps_closed_flag = self._close_low_flow_pumps(instance, pumps_closed_by_low_flow, pumps_closed_by_outage)

            #print "Solution time: ", time.time() - t0

            #t0 = time.time()
            # Set valve status based on pyomo results
            if self._wn._num_valves != 0:
                valve_status_changed = self._set_valve_status(instance)
                check_valve_status_changed = self._set_check_valves_closed(instance, closed_check_valves)
            #print "Setting valve status: ", time.time() - t0

            #t0 = time.time()
            #print self._valve_status
            # Resolve the same timestep if the valve status has changed
            if valve_status_changed \
                    or check_valve_status_changed \
                    or reservoir_link_closed_flag \
                    or low_flow_pumps_closed_flag:
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
                                          end=str(self._sim_duration_sec) + ' seconds',
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
        expected_demand = []
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
                expected_demand = instance.demand_required[n]
                #if n=='101' or n=='10':
                #    print n,'  ',head_n, '  ', node.elevation
            elif isinstance(node, Reservoir):
                demand = instance.reservoir_demand[n].value
                expected_demand = instance.reservoir_demand[n].value
            elif isinstance(node, Tank):
                demand = instance.tank_net_inflow[n].value
                expected_demand = instance.tank_net_inflow[n].value
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
                        pumps_closed.remove(link_name_k)
                        #print "Pump ", link_name_k, " opened"
                        # Overriding time controls
                        if link_name_k in pipes_closed:
                            pipes_closed.remove(link_name_k)
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
                    pumps_closed.add(link_name_k)
                    #print "Pump ", link_name_k, " closed"
            # If link is closed and tank level goes above threshold, then open the link
            for i in open_above:
                node_name_i = i[0]
                value_i = i[1]
                tank_i = self._wn.get_node(node_name_i)
                current_tank_level = instance.head[node_name_i].value - tank_i.elevation
                if link_name_k in pumps_closed:
                    if current_tank_level >= value_i:
                        pumps_closed.remove(link_name_k)
                        #print "Pump ", link_name_k, " opened"
                        if link_name_k in pipes_closed:
                            pipes_closed.remove(link_name_k)
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
                    pumps_closed.add(link_name_k)
                    #print "Pump ", link_name_k, " closed"


    def _override_time_controls(self, links_closed_by_time_controls, link_name, t):
        # Override time controls
        if link_name in links_closed_by_time_controls:
            links_closed_by_time_controls.remove(link_name)
            #print " Overriding link ", link_name, "time control"
            # If the links base status is closed then
            # all rest of timestep should be opened
            link = self._wn.get_link(link_name)
            closed_times = self._wn.time_controls[link_name]['closed_times']
            if link.get_base_status().upper() == 'CLOSED' or \
                    (len(closed_times) == 1 and closed_times[0] == 0):
                #print " \t Overriding link ", link_name, "time control from time, ", t
                for tt in xrange(t, self._n_timesteps):
                    self._link_status[link_name][tt] = True

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

    def _apply_pump_outage(self, instance,
                           pumps_closed_by_outage,
                           links_closed_by_time_controls,
                           pumps_closed_by_drain_to_reserv,
                           links_closed_by_tank_controls,
                           t):

        time_t = self._hydraulic_step_sec*t
        reservoir_links_closed_flag = False

        for pump_name, time_tuple in self._pump_outage.iteritems():
            if time_t >= time_tuple[0] and time_t <= time_tuple[1]:
                #Check if pump being closed is next to a reservoir
                # If the flow in a reservoir pump is negative then the pump is closed
                # else the pump is replaced by a pipe
                if pump_name in self._reservoir_links.keys():
                    if instance is not None:
                        if instance.flow[pump_name].value < -self._Qtol:
                            if pump_name not in pumps_closed_by_drain_to_reserv:
                                pumps_closed_by_drain_to_reserv.add(pump_name)
                                reservoir_links_closed_flag = True
                            if pump_name in pumps_closed_by_outage:
                                pumps_closed_by_outage.remove(pump_name)
                        else:
                            pumps_closed_by_outage.add(pump_name)
                    else:
                        pumps_closed_by_outage.add(pump_name)
                else:
                    pumps_closed_by_outage.add(pump_name)
            elif pump_name in pumps_closed_by_outage:
                pumps_closed_by_outage.remove(pump_name)
                self._override_time_controls(links_closed_by_time_controls, pump_name, t)
                links_closed_by_tank_controls.clear()
            elif pump_name in pumps_closed_by_drain_to_reserv:
                pumps_closed_by_drain_to_reserv.remove(pump_name)
                self._override_time_controls(links_closed_by_time_controls, pump_name, t)
                links_closed_by_tank_controls.clear()

        return reservoir_links_closed_flag

    def _apply_tank_controls(self, instance, pipes_closed_by_tank, links_closed_by_time, t):

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
                #print link_name_to_tank, " closed because ", tank_name, " below ", min_tank_head
                pipes_closed_by_tank.add(link_name_to_tank)
            elif link_name_to_tank in pipes_closed_by_tank:
                pipes_closed_by_tank.remove(link_name_to_tank)
                self._override_time_controls(links_closed_by_time, link_name_to_tank, t)
                #print "Tank closed: ", tank_name

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

    def _set_check_valves_closed(self, instance, check_valves_closed):

        check_valve_status_changed = False
        # See EPANET2 Manual pg 191 for the description of the logic used below
        for pipe_name in self._wn._check_valves:
            pipe = self._wn.get_link(pipe_name)
            start_node = pipe.start_node()
            end_node = pipe.end_node()
            headloss = instance.head[start_node].value - instance.head[end_node].value
            if abs(headloss) > self._Htol:
                if headloss < -self._Htol:
                    if pipe_name not in check_valves_closed:
                        check_valves_closed.add(pipe_name)
                        check_valve_status_changed = True
                elif instance.flow[pipe_name].value < -self._Qtol:
                    if pipe_name not in check_valves_closed:
                        check_valves_closed.add(pipe_name)
                        check_valve_status_changed = True
                else:
                    if pipe_name in check_valves_closed:
                        check_valves_closed.remove(pipe_name)
                        check_valve_status_changed = True
            elif instance.flow[pipe_name].value < -self._Qtol:
                check_valves_closed.add(pipe_name)
                check_valve_status_changed = True

        #print check_valves_closed
        return check_valve_status_changed

    def _close_low_flow_pumps(self, instance, pumps_closed_by_low_flow, pumps_closed_by_outage):
        low_flow_pumps_closed_flag = False
        for pump in instance.pumps:
            if abs(instance.flow[pump].value) < 1e-6*self._Qtol:
                if pump not in pumps_closed_by_low_flow and pump not in pumps_closed_by_outage:
                    pumps_closed_by_low_flow.add(pump)
                    low_flow_pumps_closed_flag = True
            elif pump in pumps_closed_by_low_flow:
                pumps_closed_by_low_flow.remove(pump)
        for pump in pumps_closed_by_outage:
            pumps_closed_by_low_flow.discard(pump)

        return low_flow_pumps_closed_flag

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

