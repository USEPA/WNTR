import numpy as np
from epanetlib.network.WaterNetworkModel import *
from scipy.optimize import fsolve
import math

class WaterNetworkSimulator(object):
    def __init__(self, water_network=None):
        """
        Water Network Simulator class.

        water_network: WaterNetwork object

        """
        self._wn = water_network
        if water_network is not None:
            self.init_time_params_from_model()

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

    def min_to_timestep(self, min):
        """
        Convert minutes to hydraulic timestep.

        Parameters
        --------
        min : int
            Minutes to convert to hydraulic timestep.

        Return
        -------
        hydraulic timestep
        """
        return min/self._hydraulic_step_min

    def init_time_params_from_model(self):
        self._check_model_specified()
        try:
            self._sim_start_min = self._wn.time_options['START CLOCKTIME']
            self._sim_end_min = self._wn.time_options['DURATION'] + self._wn.time_options['HYDRAULIC TIMESTEP']
            self._pattern_start_min = self._wn.time_options['PATTERN START']
            self._hydraulic_step_min = self._wn.time_options['HYDRAULIC TIMESTEP']
            self._pattern_step_min = self._wn.time_options['PATTERN TIMESTEP']
            self._hydraulic_times_min = range(self._sim_start_min, self._sim_end_min, self._hydraulic_step_min)
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
        demand_list : dictionary of floats indexed by floats
            A dictionary of demand values indexed by each hydraulic timestep(min) between
            start_time and end_time.
        """

        self._check_model_specified()

        # Set start and end time for demand values to be returned
        if start_time is None:
            start_time = 0
        if end_time is None:
            end_time = self._sim_end_min

        # Get node object
        try:
            node = self._wn.nodes[node_name]
        except KeyError:
            raise KeyError("Not a valid node name")
        # Make sure node object is a Junction
        assert(isinstance(node, Junction)), "Demands can only be calculated for Junctions"
        # Calculate demand pattern values
        base_demand = node.base_demand
        pattern_name = node.demand_pattern_name
        if pattern_name is None:
            pattern_name = self._wn.options['PATTERN']
        pattern_list = self._wn.patterns[pattern_name]
        pattern_length = len(pattern_list)
        #offset = self._wn.time_options['PATTERN START']

        demand_times_minutes = range(start_time, end_time, self._hydraulic_step_min)
        demand_pattern_values = [base_demand*i for i in pattern_list]

        demand_values = []
        for t in demand_times_minutes:
            # Modulus with the last pattern time to get time within pattern range
            pattern_index = t / self._pattern_step_min
            # Modulus with the pattern time step to get the pattern index
            pattern_index = pattern_index % pattern_length
            demand_values.append(demand_pattern_values[pattern_index])

        return demand_values

    def buildPyomoConcreteModel(self):
        import coopr.pyomo as pyomo
        from coopr.pyomo.base.expr import Expr_if
        from coopr.opt import SolverFactory
        import math

        Hw_k = 10.67
        pi = math.pi

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

        print "BUILDING THE MODEL..."
        wn = self._wn
        model = pyomo.ConcreteModel()
        model.timestep = wn.time_options['HYDRAULIC TIMESTEP']
        model.duration = wn.time_options['DURATION']
        n_timesteps = int(round(model.duration/model.timestep)) 
        # Define times
    
        ######### should the last one be included?
        model.time = pyomo.Set(initialize = range(0,n_timesteps+1))
        model.time.pprint()
        
        ###################### SETS #########################
        list_nodes = wn.nodes.values()
        model.num_nodes = pyomo.Set(initialize = [0,1]) # remove this later
        model.nodes = pyomo.Set(initialize = [n.name for n in list_nodes])
        model.tank_nodes = pyomo.Set(initialize = [n.name for n in list_nodes if isinstance(n,Tank)])
        # ask about this one may be change names for something self explanatory
        model.dnodes = pyomo.Set(initialize = [n.name for n in list_nodes if isinstance(n,Junction)])
        model.rnodes = pyomo.Set(initialize = [n.name for n in list_nodes if isinstance(n,Reservoir)])
        
        # Define link sets
        list_links = wn.links.values()
        model.links = pyomo.Set(initialize = [l.link_name for l in list_links])
        model.pumplinks = pyomo.Set(initialize = [l.link_name for l in list_links if isinstance(l,Pump)])
        model.valvelinks = pyomo.Set(initialize = [l.link_name for l in list_links if isinstance(l,Valve)])
        model.pipelinks = pyomo.Set(initialize = [l.link_name for l in list_links if isinstance(l,Pipe)])
    
        #missing
        model.curves = pyomo.Set(initialize = wn.curves.keys())
        model.curvesp = pyomo.Set(initialize = ['A', 'B', 'C'])
    
        print "Nodes"
        model.nodes.pprint()
        model.tank_nodes.pprint()
        model.dnodes.pprint()
        model.rnodes.pprint()
        print "Links"
        model.links.pprint()
        model.valvelinks.pprint()
        model.pumplinks.pprint()
        model.curves.pprint()

        ################### PARAMETERS #######################
        #def valve_status_rule(model,l,t):
        #    if wn.time_controls.has_key(l):
        #        control = wn.time_controls.get(l)
        #        if t in control.get('open_times'):
        #            return 1 
        #        elif t in control.get('closed_times'):
        #            return 0
        #        else:
        #            return 1 if wn.links[l].setting == 'Open' else 0
        #    else:
        #        return 1 if wn.links[l].setting == 'Open' else 0
        model.valvestatus = pyomo.Param(model.valvelinks, model.time, 
            within = pyomo.Binary, initialize = 1)
    
        ####### n is a binary...should we keep it as 1 or 2?
        def link_nodes_rule(model,l,n):
            return wn.links.get(l).start_node_name if n==0 else wn.links.get(l).end_node_name
        model.link_nodes = pyomo.Param(model.links, model.num_nodes, initialize = link_nodes_rule, within = model.nodes)
    
        ####### map to time step of the pattern?
        demand_dict = {}
        for n in model.dnodes:
            demand_values = self.get_node_demand(n)
            for t in model.time:
                demand_dict[(n,t)] = demand_values[t]

        #def demand_req_rule(model,n,t):
        #    if wn.nodes.get(n).demand_pattern_name is not None:
        #        pattern_name = wn.nodes.get(n).demand_pattern_name
        #        return wn.patterns[pattern_name][t]
        #    else:
        #        return wn.nodes.get(n).base_demand
        model.demand_req = pyomo.Param(model.dnodes, model.time, 
            within = pyomo.Reals, initialize = demand_dict)

        model.demand_req.pprint()
    
        def elevation_rule(model,n):
            return wn.nodes.get(n).elevation
        model.elev = pyomo.Param((model.dnodes|model.tank_nodes), 
            within = pyomo.Reals, initialize = elevation_rule)
    
        def roughness_rule(model,l):
            return wn.links.get(l).roughness
        model.link_rough = pyomo.Param((model.pipelinks|model.valvelinks), 
            within = pyomo.NonNegativeReals, initialize = roughness_rule)
        model.link_rough.pprint()

        def diameter_rule(model,l):
            return wn.links.get(l).diameter 
        model.link_dia = pyomo.Param((model.pipelinks|model.valvelinks), 
            within = pyomo.NonNegativeReals, initialize = diameter_rule)
        model.link_dia.pprint()

        def length_rule(model,l):
            return wn.links.get(l).length 
        model.link_len = pyomo.Param((model.pipelinks|model.valvelinks), 
            within = pyomo.NonNegativeReals, initialize = length_rule)
        model.link_len.pprint()

        # support pattern??????????? some error
        def reservoir_head_rule(model,n):
            #if wn.nodes.get(n).head_pattern_name is not None:
            #    pattern_name = wn.nodes.get(n).head_pattern_name
            #    #return wn.patterns[pattern_name][t]
            #    return wn.nodes.get(n).base_head
            #else:
            return wn.nodes.get(n).base_head
        model.res_heads = pyomo.Param(model.rnodes, 
            within = pyomo.NonNegativeReals, initialize = reservoir_head_rule)
    
        model.res_heads.pprint()

        def tank_min_level_rule(model,n):
            return wn.nodes.get(n).min_level
        model.min_level = pyomo.Param(model.tank_nodes,
            within = pyomo.NonNegativeReals, initialize = tank_min_level_rule)
    
        def tank_max_level_rule(model,n):
            return wn.nodes.get(n).max_level
        model.max_level = pyomo.Param(model.tank_nodes,
            within = pyomo.NonNegativeReals, initialize = tank_max_level_rule) 
    
        def tank_diameter_rule(model,n):
            return wn.nodes.get(n).diameter
        model.tank_dia = pyomo.Param(model.tank_nodes,
            within = pyomo.NonNegativeReals, initialize = tank_diameter_rule)
    
        def tank_init_level_rule(model,n):
            return wn.nodes.get(n).init_level
        model.tank_inhead = pyomo.Param(model.tank_nodes,
            within = pyomo.NonNegativeReals, initialize = tank_init_level_rule)
    
        # Missing
        curveparam_dict = {}
        curve_pump_dict = {}
        for link_name, link in wn.links.iteritems():
            if wn.isPump(link_name):
                curve_name = link.curve_name
                curve_pump_dict[link_name] = curve_name
                coeff = wn.get_pump_coefficients(link_name) 
                curveparam_dict[(curve_name, 'A')] = coeff[0]
                curveparam_dict[(curve_name, 'B')] = coeff[1]
                curveparam_dict[(curve_name, 'C')] = coeff[2]

        model.curvesp.pprint()
        print "Cureve param dict: ", curveparam_dict
        print "curve pumop dict: ", curve_pump_dict

        
        model.curveparam = pyomo.Param(model.curves, model.curvesp, initialize=curveparam_dict)
        model.puculinks = pyomo.Param(model.pumplinks, initialize=curve_pump_dict)
        #model.timestep = pyomo.Param(model.time,within = pyomo.NonNegativeReals)
    
        model.link_nodes.pprint()
        model.valvestatus.pprint()
        model.curveparam.pprint()
        model.puculinks.pprint()
    
        ###################VARIABLES#####################
        model.head = pyomo.Var(model.nodes, model.time, initialize = 200.0)
        model.flow = pyomo.Var(model.links, model.time, within = pyomo.Reals, initialize = 0.1)
        # why is rdemand?
        model.rdemand = pyomo.Var(model.rnodes, model.time, within = pyomo.Reals, initialize = 0.0)
        model.tnet_inflow = pyomo.Var(model.tank_nodes,model.time,within = pyomo.Reals, initialize = 0.1)
    
        # this should be changes to allow user to pass this too
        def init_demand_rule(model,n,t):
            return model.demand_req[n,t]
        model.demand_actual = pyomo.Var(model.dnodes, model.time, 
            within = pyomo.Reals, initialize = init_demand_rule)
    
        def obj_rule(model):
            expr = 0
            for i in model.dnodes:
                for j in model.time:
                    expr += (model.demand_actual[i,j]-model.demand_req[i,j])**2
                    #expr += 1
            return expr
        #return sum(((model.demand_actual[i,j]-model.demand_req[i,j])**2 for i in model.dnodes) for j in model.time)
        model.obj = pyomo.Objective(rule = obj_rule, sense = pyomo.minimize)
        
        def headloss_rule(model,k,l):
            if k in model.pumplinks:
                return ((-1.0*(model.curveparam[model.puculinks[k],'A'] - model.curveparam[model.puculinks[k],'B']*(model.flow[k,l]**model.curveparam[model.puculinks[k],'C']))) == model.head[model.link_nodes[k,0],l] - model.head[model.link_nodes[k,1],l])
            elif k in model.valvelinks:
                if model.valvestatus[k,l] == 1:
                    return (Expr_if(IF = model.flow[k,l] > 0, THEN = 1, ELSE = -1))*Hw_k*((model.link_rough[k])**(-1.852))*((model.link_dia[k])**(-4.871))*model.link_len[k]*LossFunc(abs(model.flow[k,l])) == (model.head[model.link_nodes[k,0],l] - model.head[model.link_nodes[k,1],l])
                else:
                    return pyomo.Constraint.Skip
            else:
                return (Expr_if(IF = model.flow[k,l] > 0, THEN = 1, ELSE = -1))*Hw_k*((model.link_rough[k])**(-1.852))*((model.link_dia[k])**(-4.871))*model.link_len[k]*LossFunc(abs(model.flow[k,l])) == (model.head[model.link_nodes[k,0],l] - model.head[model.link_nodes[k,1],l])
                #return ((Expr_if(IF = model.flow[k,l] > 0, THEN = 1, ELSE = -1))*Hw_k*((model.link_rough[k])**(-1.852))*((model.link_dia[k])**(-4.871))*model.link_len[k]*((abs(model.flow[k,l]))**1.852)) == (model.head[model.link_nodes[k,0],l] - model.head[model.link_nodes[k,1],l])
        model.headloss = pyomo.Constraint(model.links,model.time, rule = headloss_rule)
        
        def nodebalance_rule(model,i,l):
            exprs = 0
            if i in model.dnodes:
                for link in model.links:
                    if model.link_nodes[link,0] == i :
                        exprs -=  model.flow[link,l]
                    elif model.link_nodes[link,1] == i :
                        exprs +=  model.flow[link,l]
                return exprs == model.demand_actual[i,l]
            elif i in model.rnodes:
                for link in model.links:
                    if model.link_nodes[link,0] == i :
                        exprs -= model.flow[link,l]
                    elif model.link_nodes[link,1] == i:
                        exprs +=  model.flow[link,l]
                return exprs == model.rdemand[i,l]
            elif i in model.tank_nodes:
                for link in model.links:
                    if model.link_nodes[link,0] == i :
                        exprs -= model.flow[link,l]
                    elif model.link_nodes[link,1] == i:
                        exprs += model.flow[link,l]
                return exprs == model.tnet_inflow[i,l]
        model.nodebalance = pyomo.Constraint(model.nodes,model.time, rule = nodebalance_rule)
        
        def elevation_rule(model,i,l):
            return model.head[i,l] - model.elev[i] >= 0
        model.elevation = pyomo.Constraint(model.dnodes,model.time, rule = elevation_rule)
        
        def tankelev_rule(model,i,l):
            return (model.elev[i]+model.min_level[i],model.head[i,l],model.elev[i]+model.max_level[i])
        model.tankelev = pyomo.Constraint(model.tank_nodes,model.time,rule = tankelev_rule)
        
        def pumplinkflow_rule(model,i,l):
            return model.flow[i,l] >= 0
        model.pumplinkflow = pyomo.Constraint(model.pumplinks|model.valvelinks,model.time, rule = pumplinkflow_rule)
        
        def resheadfix_rule(model,i,l):
            model.head[i,l].value = model.res_heads[i]
            model.head[i,l].fixed = True
        model.resheadfix = pyomo.BuildAction(model.rnodes,model.time, rule = resheadfix_rule)
        
        def tankheadinit_rule(model,i,l):
            if l is min(model.time):
                model.head[i,l] = model.elev[i]+model.tank_inhead[i]
                model.head[i,l].fixed = True
        model.tankheadinit = pyomo.BuildAction(model.tank_nodes,model.time, rule = tankheadinit_rule)
        
        def tankheadvar_rule(model,i,l):
            if l is max(model.time):
                return pyomo.Constraint.Skip
            else:
                return (model.tnet_inflow[i,l]*wn.time_options['HYDRAULIC TIMESTEP']*60.0*4.0)/(pi*(model.tank_dia[i]**2)) == model.head[i,l+1]-model.head[i,l]
        model.tankheadvar = pyomo.Constraint(model.tank_nodes,model.time, rule = tankheadvar_rule)        
                
        def valvelinkflow_rule(model,i,l):
            if model.valvestatus[i,l] == 1:
                return pyomo.Constraint.Skip
            else:
                return model.flow[i,l] == 0
        model.valvelinkflow = pyomo.Constraint(model.valvelinks,model.time, rule = valvelinkflow_rule)

        instance = model.create()
        opt = SolverFactory('ipopt')
        results = opt.solve(instance, tee=True)
        #results.write()
