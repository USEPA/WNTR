"""
QUESTIONS
"""

"""
TODO
1. Use in_edges and out_edges to write node balances on the pyomo model.
2. Check for rule based controls in pyomo model and throw an exception.
3. Use reporting timestep when creating the pyomo results object.
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
        # Hazen-Williams resistance coefficient
        self._Hw_k = 10.67 # SI units = 4.727 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.

    def run_sim(self, solver='ipopt', solver_options={}, modified_hazen_williams=True):
        """
        Run water network simulation using pyomo model.

        Optional Parameters
        --------
        solver : string
            Name of the NLP solver. Default is 'ipopt'.
        solver_options : dictionary
            Dictionary of NLP solver options. Default is empty.
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
        model.timestep = self._hydraulic_step_min
        model.duration = self._sim_duration_min
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

        model.head = Var(model.nodes, model.time, initialize=200.0)
        model.flow = Var(model.links, model.time, within=Reals, initialize=0.1)
        model.headloss = Var(model.links, model.time, within=Reals, initialize=0.1)
        model.reservoir_demand = Var(model.reservoirs, model.time, within=Reals, initialize=0.0)
        model.tank_net_inflow = Var(model.tanks, model.time,within=Reals, initialize=0.1)
    
        def init_demand_rule(model,n,t):
            return model.demand_required[n,t]
        model.demand_actual = Var(model.junctions, model.time, within=Reals, initialize=init_demand_rule)
    
        ############### OBJECTIVE ########################
        def obj_rule(model):
            expr = 0
            for n in model.junctions:
                for t in model.time:
                    expr += (model.demand_actual[n,t]-model.demand_required[n,t])**2
            return expr
        model.obj = Objective(rule=obj_rule, sense=minimize)

        #print "Created Obj: ", time.time() - t0
        ############## CONSTRAINTS #####################

        # Head loss inside pipes
        for l in model.pipes:
            pipe = wn.get_link(l)
            pipe_resistance_coeff = self._Hw_k*(pipe.roughness**(-1.852))*(pipe.diameter**(-4.871))*pipe.length # Hazen-Williams
            for t in model.time:
                if self.is_link_open(l,t*self._hydraulic_step_min):
                    if modified_hazen_williams:
                        setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                                                                      *pipe_resistance_coeff*LossFunc(abs(model.flow[l,t])) == model.headloss[l,t]))
                    else:
                        setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), Constraint(expr=Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                                                                      *pipe_resistance_coeff*f2(abs(model.flow[l,t])) == model.headloss[l,t]))

        #print "Created headloss: ", time.time() - t0
        # Head gain provided by the pump is implemented as negative headloss
        for l in model.pumps:
            pump = wn.get_link(l)
            A, B, C = pump.get_head_curve_coefficients()
            for t in model.time:
                if self.is_link_open(l,t*self._hydraulic_step_min):
                    setattr(model, 'pump_negative_headloss_'+str(l)+'_'+str(t), Constraint(expr=model.headloss[l,t] == (-1.0*A + B*(model.flow[l,t]**C))))

        #print "Created head gain: ", time.time() - t0
        # Nodal head difference between start and end node of a link
        for l in model.links:
            link = wn.get_link(l)
            start_node = link.start_node()
            end_node = link.end_node()
            for t in model.time:
                if self.is_link_open(l,t*self._hydraulic_step_min):
                    setattr(model, 'head_difference_'+str(l)+'_'+str(t), Constraint(expr=model.headloss[l,t] == model.head[start_node,t] - model.head[end_node,t]))

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
                return expr == model.demand_actual[n,t]
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
                return (model.tank_net_inflow[n,t]*model.timestep*60.0*4.0)/(pi*(tank.diameter**2)) == model.head[n,t+1]-model.head[n,t]
        model.tank_dynamics = Constraint(model.tanks, model.time, rule=tank_dynamics_rule)

        #print "Created Tank Dynamics: ", time.time() - t0

        # Set flow and headloss to 0 if link is closed
        for l in model.links:
            for t in model.time:
                if not self.is_link_open(l,t*self._hydraulic_step_min):
                    model.flow[l,t].value = 0.0
                    model.flow[l,t].fixed = True
                    model.headloss[l,t].value = 0.0
                    model.headloss[l,t].fixed = True

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


        ####### CREATE INSTANCE AND SOLVE ########

        instance = model.create()
        
        #print "Created instance: ", time.time() - t0

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
                                          end=str(self._sim_duration_min) + ' minutes',
                                          freq=str(self._hydraulic_step_min) + 'min')
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
                    velocity_l_t = 4.0*flow_l_t/(math.pi*link.diameter**2)
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
                head_n_t = instance.head[n,t].value
                if isinstance(node, Reservoir):
                    pressure_n_t = 0.0
                else:
                    pressure_n_t = head_n_t + node.elevation
                head.append(head_n_t)
                pressure.append(pressure_n_t)
                if isinstance(node, Junction):
                    demand.append(instance.demand_actual[n,t].value)
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
        results.simulator_options['start_time'] = self._sim_start_min
        results.simulator_options['duration'] = self._sim_duration_min
        results.simulator_options['pattern_start_time'] = self._pattern_start_min
        results.simulator_options['hydraulic_time_step'] = self._hydraulic_step_min
        results.simulator_options['pattern_time_step'] = self._pattern_step_min

