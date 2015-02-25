import numpy as np
from epanetlib.network.WaterNetworkModel import *
from scipy.optimize import fsolve
import math
from NetworkResults import NetResults
import pandas as pd


class WaterNetworkSimulator(object):
    def __init__(self, water_network=None):
        """
        Water Network Simulator class.

        water_network: WaterNetwork object

        """
        self._wn = water_network

        # Simulation time options
        self._sim_start_min = self._wn.time_options['START CLOCKTIME']
        self._sim_duration = self._wn.time_options['DURATION']
        self._pattern_start_min = self._wn.time_options['PATTERN START']
        self._hydraulic_step_min = self._wn.time_options['HYDRAULIC TIMESTEP']
        self._pattern_step_min = self._wn.time_options['PATTERN TIMESTEP']
        self._hydraulic_times_min = range(0, self._sim_duration, self._hydraulic_step_min)

        if water_network is not None:
            self.init_time_params_from_model()

        # Hazen-Williams resistance coefficient
        self.Hw_k = 10.67 # SI units = 4.727 in EPANET GPM units. See Table 3.1 in EPANET 2 User manual.

    def set_water_network_model(self, water_network):
        """
        Set the WaterNetwork model for the simulator.

        Parameters
        ---------
        water_network : WaterNetwork object
            Water network model object
        """
        self._wn = water_network
        self.init_time_params_from_model()

    def _check_model_specified(self):
        assert (isinstance(self._wn, WaterNetworkModel)), "Water network model has not been set for the simulator" \
                                                          "use method set_water_network_model to set model."

    def is_open(self,link_name,time):
        link = self._wn.get_link(link_name)
        if link_name not in self._wn.time_controls:
            return link.get_base_status()
        else:
            open_times = self._wn.time_controls[link_name]['open_times']
            closed_times = self._wn.time_controls[link_name]['closed_times']
            if time<open_times[0] and time<closed_times[0]:
                return link.get_base_status()
            else:

                #Check open times
                left = 0
                right = len(open_times)-1
                if time >= open_times[right]:
                    min_open = time-open_times[right];
                elif time < open_times[left]:
                    min_open = float("inf");
                else:
                    middle = int(0.5*(right+left))
                    while(right-left>1):
                        if(open_times[middle]>time):
                            right = middle
                        else:
                            left = middle
                        middle = int(0.5*(right+left))
                    min_open = time-open_times[left];

                #Check Closed times
                left = 0
                right = len(closed_times)-1
                if time >= closed_times[right]:
                    min_closed = time-closed_times[right]
                elif time < closed_times[left]:
                    min_closed = float("inf")
                else:
                    middle = int(0.5*(right+left))
                    while(right-left>1):
                        if(closed_times[middle]>time):
                            right = middle
                        else:
                            left = middle
                        middle = int(0.5*(right+left))
                    min_closed = time-closed_times[left];
                """
                min_open = float("inf")
                for t in open_times:
                    if time>=t and min_open>=time-t:
                        min_open = time-t
                min_closed = float("inf")
                for t in closed_times:
                    if time>=t and min_closed>=time-t:
                        min_closed = time-t
                """
                return True if min_open<min_closed else False

    def min_to_timestep(self, min):
        """
        Convert minutes to hydraulic timestep.

        Parameters
        -------
        min : int
            Minutes to convert to hydraulic timestep.

        Return
        -------
        hydraulic timestep
        """
        return min/self._hydraulic_step_min

    def init_time_params_from_model(self):
        """
        Load simulation time parameters from the water network time options.
        """
        self._check_model_specified()
        try:
            self._sim_start_min = self._wn.time_options['START CLOCKTIME']
            self._sim_duration = self._wn.time_options['DURATION']
            self._pattern_start_min = self._wn.time_options['PATTERN START']
            self._hydraulic_step_min = self._wn.time_options['HYDRAULIC TIMESTEP']
            self._pattern_step_min = self._wn.time_options['PATTERN TIMESTEP']
            self._hydraulic_times_min = range(0, self._sim_duration, self._hydraulic_step_min)
        except KeyError:
            KeyError("Water network model used for simulation should contain time parameters. "
                     "Consider initializing the network model data. e.g. Use parser to read EPANET"
                     "inp file into the model.")

    def get_node_demand(self, node_name, start_time=None, end_time=None):
        """
        Calculates the demands at a node based on the demand pattern.

        Parameters
        ---------
        node_name : string
            Name of the node.
        start_time : float
            The start time of the demand values requested. Default is 0 min.
        end_time : float
            The end time of the demand values requested. Default is the simulation end time.

        Return
        -------
        demand_list : list of floats
           A list of demand values at each hydraulic timestep
        """

        self._check_model_specified()

        # Set start and end time for demand values to be returned
        if start_time is None:
            start_time = 0
        if end_time is None:
            end_time = self._sim_duration

        # Get node object
        try:
            node = self._wn.get_node(node_name)
        except KeyError:
            raise KeyError("Not a valid node name")
        # Make sure node object is a Junction
        assert(isinstance(node, Junction)), "Demands can only be calculated for Junctions"
        # Calculate demand pattern values
        base_demand = node.base_demand
        pattern_name = node.demand_pattern_name
        if pattern_name is None:
            pattern_name = self._wn.options['PATTERN']
        pattern_list = self._wn.get_pattern(pattern_name)
        pattern_length = len(pattern_list)
        offset = self._wn.time_options['PATTERN START']

        assert(offset == 0.0), "Only 0.0 Pattern Start time is currently supported. "

        demand_times_minutes = range(start_time, end_time + self._hydraulic_step_min, self._hydraulic_step_min)
        demand_pattern_values = [base_demand*i for i in pattern_list]

        demand_values = []
        for t in demand_times_minutes:
            # Modulus with the last pattern time to get time within pattern range
            pattern_index = t / self._pattern_step_min
            # Modulus with the pattern time step to get the pattern index
            pattern_index = pattern_index % pattern_length
            demand_values.append(demand_pattern_values[pattern_index])

        return demand_values


class PyomoSimulator(WaterNetworkSimulator):
    """
    Pyomo simulator inherited from Water Network Simulator.
    """
    try:
        import coopr.pyomo as pyomo
        from coopr.pyomo.base.expr import Expr_if
        from coopr.opt import SolverFactory
    except ImportError:
        raise ImportError('Error importing pyomo while running pyomo simulator.'
                          'Make sure pyomo is installed and added to path.')
    import math

    def __init__(self, wn=None):
        WaterNetworkSimulator.__init__(self, wn)

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
            return self.Expr_if(IF = Q < q1, THEN = f1(Q), ELSE = self.Expr_if(IF = Q > q2, THEN = f2(Q), ELSE = Px(Q)))

        wn = self._wn
        model = self.pyomo.ConcreteModel()
        model.timestep = self._hydraulic_step_min
        model.duration = self._sim_duration
        n_timesteps = int(round(model.duration/model.timestep)) 

        ###################### SETS #########################
        model.time = self.pyomo.Set(initialize=range(0, n_timesteps+1))
        # NODES
        model.nodes = self.pyomo.Set(initialize=[name for name, node in wn.nodes()])
        model.tanks = self.pyomo.Set(initialize=[n for n, N in wn.nodes(Tank)])
        model.junctions = self.pyomo.Set(initialize=[n for n, N in wn.nodes(Junction)])
        model.reservoirs = self.pyomo.Set(initialize=[n for n, N in wn.nodes(Reservoir)])
        # LINKS
        model.links = self.pyomo.Set(initialize=[name for name, link in wn.links()])
        model.pumps = self.pyomo.Set(initialize=[l for l, L in wn.links(Pump)])
        model.valves = self.pyomo.Set(initialize=[l for l, L in wn.links(Valve)])
        model.pipes = self.pyomo.Set(initialize=[l for l, L in wn.links(Pipe)])

        ################### PARAMETERS #######################

        demand_dict = {}
        for n in model.junctions:
            demand_values = self.get_node_demand(n)
            for t in model.time:
                demand_dict[(n, t)] = demand_values[t]
        model.demand_required = self.pyomo.Param(model.junctions, model.time, within=self.pyomo.Reals, initialize=demand_dict)

        ################### VARIABLES #####################

        model.head = self.pyomo.Var(model.nodes, model.time, initialize=200.0)
        model.flow = self.pyomo.Var(model.links, model.time, within=self.pyomo.Reals, initialize=0.1)
        model.headloss = self.pyomo.Var(model.links, model.time, within=self.pyomo.Reals, initialize=0.1)
        model.reservoir_demand = self.pyomo.Var(model.reservoirs, model.time, within=self.pyomo.Reals, initialize=0.0)
        model.tank_net_inflow = self.pyomo.Var(model.tanks, model.time,within=self.pyomo.Reals, initialize=0.1)
    
        def init_demand_rule(model,n,t):
            return model.demand_required[n,t]
        model.demand_actual = self.pyomo.Var(model.junctions, model.time, within=self.pyomo.Reals, initialize=init_demand_rule)
    
        ############### OBJECTIVE ########################
        def obj_rule(model):
            expr = 0
            for n in model.junctions:
                for t in model.time:
                    expr += (model.demand_actual[n,t]-model.demand_required[n,t])**2
            return expr
        model.obj = self.pyomo.Objective(rule=obj_rule, sense=self.pyomo.minimize)

        ############## CONSTRAINTS #####################

        # Head loss inside pipes
        for l in model.pipes:
            pipe = wn.get_link(l)
            pipe_resistance_coeff = self.Hw_k*(pipe.roughness**(-1.852))*(pipe.diameter**(-4.871))*pipe.length # Hazen-Williams
            for t in model.time:
                if modified_hazen_williams:
                    setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), self.pyomo.Constraint(expr=self.Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                                                                      *pipe_resistance_coeff*LossFunc(abs(model.flow[l,t])) == model.headloss[l,t]))
                else:
                    setattr(model, 'pipe_headloss_'+str(l)+'_'+str(t), self.pyomo.Constraint(expr=self.Expr_if(IF=model.flow[l,t]>0, THEN = 1, ELSE = -1)
                                                                      *pipe_resistance_coeff*f2(abs(model.flow[l,t])) == model.headloss[l,t]))

        # Head gain provided by the pump is implemented as negative headloss
        for l in model.pumps:
            pump = wn.get_link(l)
            A, B, C = pump.get_head_curve_coefficients()
            for t in model.time:
                setattr(model, 'pump_negative_headloss_'+str(l)+'_'+str(t), self.pyomo.Constraint(expr=model.headloss[l,t] == (-1.0*A + B*(model.flow[l,t]**C))))

        # Nodal head difference between start and end node of a link
        for l in model.links:
            link = wn.get_link(l)
            start_node = link.start_node()
            end_node = link.end_node()
            for t in model.time:
                setattr(model, 'head_difference_'+str(l)+'_'+str(t), self.pyomo.Constraint(expr=model.headloss[l,t] == model.head[start_node,t] - model.head[end_node,t]))

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
        model.node_mass_balance = self.pyomo.Constraint(model.nodes, model.time, rule=node_mass_balance_rule)

        # Head in junctions should be greater or equal to the elevation
        for n in model.junctions:
            junction = wn.get_node(n)
            elevation_n = junction.elevation
            for t in model.time:
                setattr(model, 'junction_elevation_'+str(n)+'_'+str(t), self.pyomo.Constraint(expr=model.head[n,t] >= elevation_n))

        # Bounds on the head inside a tank
        def tank_head_bounds_rule(model,n,t):
            tank = wn.get_node(n)
            return (tank.elevation + tank.min_level, model.head[n,t], tank.elevation + tank.max_level)
        model.tank_head_bounds = self.pyomo.Constraint(model.tanks, model.time, rule=tank_head_bounds_rule)

        # Flow in a pump should always be positive
        def pump_positive_flow_rule(model,l,t):
            return model.flow[l,t] >= 0
        model.pump_positive_flow_bounds = self.pyomo.Constraint(model.pumps, model.time, rule=pump_positive_flow_rule)

        def tank_dynamics_rule(model, n, t):
            if t is max(model.time):
                return self.pyomo.Constraint.Skip
            else:
                tank = wn.get_node(n)
                return (model.tank_net_inflow[n,t]*model.timestep*60.0*4.0)/(pi*(tank.diameter**2)) == model.head[n,t+1]-model.head[n,t]
        model.tank_dynamics = self.pyomo.Constraint(model.tanks, model.time, rule=tank_dynamics_rule)

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
        opt = self.SolverFactory(solver)
        # Set solver options
        for key, val in solver_options.iteritems():
            opt.options[key]=val
        # Solve pyomo model
        pyomo_results = opt.solve(instance, tee=True)
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
                                         end=str(self._sim_duration) + ' minutes',
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

    def _get_link_type(self, name):
        if isinstance(self._wn.get_link(name), Pipe):
            return 'pipe'
        elif isinstance(self._wn.get_link(name), Valve):
            return 'valve'
        elif isinstance(self._wn.get_link(name), Pump):
            return 'pump'
        else:
            raise RuntimeError('Link name ' + name + ' was not recognised as a pipe, valve, or pump.')

    def _get_node_type(self, name):
        if isinstance(self._wn.get_node(name), Junction):
            return 'junction'
        elif isinstance(self._wn.get_node(name), Tank):
            return 'tank'
        elif isinstance(self._wn.get_node(name), Reservoir):
            return 'reservoir'
        else:
            raise RuntimeError('Node name ' + name + ' was not recognised as a junction, tank, or reservoir.')

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
        results.simulator_options['duration'] = self._sim_duration
        results.simulator_options['pattern_start_time'] = self._pattern_start_min
        results.simulator_options['hydraulic_time_step'] = self._hydraulic_step_min
        results.simulator_options['pattern_time_step'] = self._pattern_step_min



