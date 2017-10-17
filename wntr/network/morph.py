import wntr
import networkx as nx
import itertools
import copy
import logging

logger = logging.getLogger(__name__)

### TODO
"""
Add tests, check units, run simulation on new WN
"""

class Skeletonize(object):
    
    def __init__(self, wn):
        # Get a copy of the network
        self.wn = copy.deepcopy(wn)
        
        # Get a copy of the graph
        G = self.wn.get_graph_deep_copy()
        G = G.to_undirected()
        self.G = G
        
        # Create a map of original nodes to skeletonized nodes
        skel_map = {}
        for node_name in self.wn.node_name_list:
            skel_map[node_name] = [node_name]
        self.skeleton_map = skel_map
        
        # Create a map of demands (key = junction name, item = list of demand objects)
        demand_map = {j: [] for j in self.wn.junction_name_list}
        for name, demand in self.wn._demands.items():
            demand_map[demand.junction_name].append(demand)
        self._demand_map = demand_map
        self.new_demand_index = len([key for key in self.wn._demands.keys()])+1
        
        # Get a list of junctions and pipes that are associated with controls
        juncs = set()
        pipes = set()
        for control_name, control in self.wn._controls.items():
            objs = []
            try:
                objs.append(control._control_action._target_obj_ref)
            except: #IfThenElseControl
                for then_action in control._then_actions:
                    objs.append(then_action._target_obj_ref)
            for obj in objs:
                if isinstance(obj, wntr.network.Junction):
                    juncs.add(obj.name)
                if isinstance(obj, wntr.network.Pipe):
                    pipes.add(obj.name)
        self.juncs_with_controls = list(juncs)
        self.pipes_with_controls = list(pipes)

        # Calculate pipe headloss using a single period EPANET simulation
        duration = self.wn.options.duration
        sim = wntr.sim.EpanetSimulator(self.wn)
        self.wn.options.duration = 0
        results = sim.run_sim()
        head = results.node['head']
        headloss = {}
        for link_name, link in self.wn.links():
            headloss[link_name] = float(abs(head[link.start_node] - head[link.end_node]))
        self.headloss = headloss
        self.wn.options.duration = duration
    
        self.num_branch_trim = 0
        self.num_series_merge = 0
        self.num_parallel_merge = 0
        
    def run(self, pipe_threshold):
        """
        Run iterative branch trim, series pipe merge, and parallel pipe merge 
        operations based on a pipe diameter treshold.  
        
        Parameters
        -------------
        pipe_threshold: float 
            Pipe diameter threshold determines candidate pipes for skeleton 
            steps
            
        Returns
        --------
        wn : WaterNetworkModel object
            Skeletonized water network model
        
        skeleton_map : dict
            Dictonary with original nodes as keys and grouped nodes as values
        """
        num_junctions = self.wn.num_junctions
        flag = True
        
        while flag:
            self.branch_trim(pipe_threshold)
            self.series_pipe_merge(pipe_threshold)
            self.parallel_pipe_merge(pipe_threshold)
            
            if num_junctions == self.wn.num_junctions:
                flag = False
            else:
                num_junctions = self.wn.num_junctions
        
        return self.wn, self.skeleton_map
    
    def branch_trim(self, pipe_threshold):
        """
        Run a single branch trim operation based on a pipe diameter threshold.
        Branch trimming removes deadend pipes smaller than the pipe 
        diameter threshold and redistributes demands (and associated demand 
        patterns) to the neighboring junction.
        
        Returns
        --------
        wn : WaterNetworkModel object
            Skeletonized water network model
        
        skeleton_map : dict
            Dictonary with original nodes as keys and grouped nodes as values
        """
        for junc_name in self.wn.junction_name_list:
            if junc_name in self.juncs_with_controls:
                continue
            neighbors = list(nx.neighbors(self.G,junc_name))
            if len(neighbors) > 1:
                continue
            neigh_junc_name = neighbors[0] # only one neighbor
            nPipes = len(self.G.adj[junc_name][neigh_junc_name])
            if nPipes > 1:
                continue
            neigh_junc = self.wn.get_node(neigh_junc_name)
            if not (isinstance(neigh_junc, wntr.network.Junction)):
                continue
            pipe_name = list(self.G.adj[junc_name][neigh_junc_name].keys())[0] # only one pipe
            pipe = self.wn.get_link(pipe_name)
            if not ((isinstance(pipe, wntr.network.Pipe)) and \
                (pipe.diameter <= pipe_threshold) and \
                pipe not in self.pipes_with_controls):
                continue
            
            logger.info('Branch trim:', junc_name, neighbors)
            
            # Update skeleton map        
            self.skeleton_map[neigh_junc_name].extend(self.skeleton_map[junc_name])
            self.skeleton_map[junc_name] = []
            
            # Move demand
            self._move_demand(junc_name, neigh_junc_name)

            # Update demand map
            self._demand_map[neigh_junc_name].extend(self._demand_map[junc_name])
            self._demand_map[junc_name] = []
            
            # Remove node and links from wn and G
            self.wn.remove_link(pipe_name)
            self.wn.remove_node(junc_name)
            self.G.remove_node(junc_name)
                    
            self.num_branch_trim +=1
            
        return self.wn, self.skeleton_map
    
    def series_pipe_merge(self, pipe_threshold):
        """
        Run a single series pipe merge operation based on a pipe diameter 
        treshold.  This operation combines pipes in series if both pipes are 
        smaller than the pipe diameter threshold. The larger diameter pipe is 
        retained, demands (and associated demand patterns) are redistributed 
        to the nearest junction.
        
        Returns
        --------
        wn : WaterNetworkModel object
            Skeletonized water network model
        
        skeleton_map : dict
            Dictonary with original nodes as keys and grouped nodes as values
        """
        for junc_name in self.wn.junction_name_list:
            if junc_name in self.juncs_with_controls:
                continue
            neighbors = list(nx.neighbors(self.G,junc_name))
            if not (len(neighbors) == 2):
                continue
            neigh_junc_name0 = neighbors[0]
            neigh_junc_name1 = neighbors[1]
            neigh_junc0 = self.wn.get_node(neigh_junc_name0)
            neigh_junc1 = self.wn.get_node(neigh_junc_name1)
            if not ((isinstance(neigh_junc0, wntr.network.Junction)) or \
               (isinstance(neigh_junc1, wntr.network.Junction))):
                continue
            pipe_name0 = list(self.G.adj[junc_name][neigh_junc_name0].keys())
            pipe_name1 = list(self.G.adj[junc_name][neigh_junc_name1].keys())
            if (len(pipe_name0) > 1) or (len(pipe_name1) > 1):
                continue
            pipe_name0 = pipe_name0[0] # only one pipe
            pipe_name1 = pipe_name1[0] # only one pipe
            pipe0 = self.wn.get_link(pipe_name0)
            pipe1 = self.wn.get_link(pipe_name1)
            if not ((isinstance(pipe0, wntr.network.Pipe)) and \
                (isinstance(pipe1, wntr.network.Pipe)) and \
                (pipe0.diameter <= pipe_threshold) and \
                (pipe1.diameter <= pipe_threshold) and \
                pipe0 not in self.pipes_with_controls and \
                pipe1 not in self.pipes_with_controls):
                continue
            # Find closest neighbor junction
            if (isinstance(neigh_junc0, wntr.network.Junction)) and \
               (isinstance(neigh_junc1, wntr.network.Junction)):
                if pipe0.length < pipe1.length:
                    closest_junc_name = neigh_junc_name0
                else:
                    closest_junc_name = neigh_junc_name1
            elif (isinstance(neigh_junc0, wntr.network.Junction)):
                closest_junc_name = neigh_junc_name0
            elif (isinstance(neigh_junc1, wntr.network.Junction)):
                closest_junc_name = neigh_junc_name1
            else:
                continue
            
            logger.info('Series pipe merge:', junc_name, neighbors)
                
            # Update skeleton map    
            self.skeleton_map[closest_junc_name].extend(self.skeleton_map[junc_name])
            self.skeleton_map[junc_name] = []
                
            # Move demand
            self._move_demand(junc_name, closest_junc_name)
                
            # Update demand map
            self._demand_map[closest_junc_name].extend(self._demand_map[junc_name])
            self._demand_map[junc_name] = []

            # Remove node and links from wn and G
            self.wn.remove_link(pipe_name0)
            self.wn.remove_link(pipe_name1)
            self.wn.remove_node(junc_name)
            self.G.remove_node(junc_name)
            
            # Compute new pipe properties
            props = self._series_merge_properties(pipe0, pipe1)
            
            # Find larger diameter pipe
            if pipe0.diameter > pipe1.diameter:
                larger_pipe = pipe0
            else:
                larger_pipe = pipe1
                
            # Add new pipe to wn and G
            self.wn.add_pipe(larger_pipe.name, 
                             start_node_name=neigh_junc_name0, 
                             end_node_name=neigh_junc_name1, 
                             length=props['length'], 
                             diameter=props['diameter'], 
                             roughness=props['roughness'], 
                             minor_loss=props['minorloss'],
                             status=props['status']) 
            self.G.add_edge(neigh_junc_name0, 
                            neigh_junc_name1, 
                            larger_pipe.name)
            
            self.num_series_merge +=1
            
        return self.wn, self.skeleton_map
        
    def parallel_pipe_merge(self, pipe_threshold):
        """
        Run a single parallel pipe merge operation based on a pipe diameter 
        treshold.  This operation combines pipes in parallel if both pipes are 
        smaller than the pipe diameter threshold. The larger diameter pipe is 
        retained.
        
        Returns
        --------
        wn : WaterNetworkModel object
            Skeletonized water network model
        
        skeleton_map : dict
            Dictonary with original nodes as keys and grouped nodes as values
        """
        
        for junc_name in self.wn.junction_name_list:
            if junc_name in self.juncs_with_controls:
                continue
            neighbors = nx.neighbors(self.G,junc_name)
            for neighbor in neighbors:
                parallel_pipe_names = list(self.G.adj[junc_name][neighbor].keys())
                if len(parallel_pipe_names) == 1:
                    continue
                for (pipe_name0, pipe_name1) in itertools.combinations(parallel_pipe_names, 2):
                    try:
                        pipe0 = self.wn.get_link(pipe_name0)
                        pipe1 = self.wn.get_link(pipe_name1)
                    except:
                        continue # one of the pipes removed in previous loop
                    if not ((isinstance(pipe0, wntr.network.Pipe)) and \
                       (isinstance(pipe1, wntr.network.Pipe)) and \
                        (pipe0.diameter <= pipe_threshold) and \
                        (pipe1.diameter <= pipe_threshold) and \
                        pipe0 not in self.pipes_with_controls and \
                        pipe1 not in self.pipes_with_controls):
                        continue
                    
                    logger.info('Parallel pipe merge:', junc_name, (pipe_name0, pipe_name1))
                    
                    # Remove links from wn and G                 
                    self.wn.remove_link(pipe_name0)
                    self.wn.remove_link(pipe_name1)
                    self.G.remove_edge(neighbor, junc_name, pipe_name0) 
                    self.G.remove_edge(junc_name, neighbor, pipe_name1)
            
                    # Compute new pipe properties
                    props = self._parallel_merge_properties(pipe0, pipe1)
                    
                    # Find larger diameter pipe
                    if pipe0.diameter > pipe1.diameter:
                        larger_pipe = pipe0
                    else:
                        larger_pipe = pipe1
                        
                    # Add a new pipe to wn and G
                    self.wn.add_pipe(larger_pipe.name, 
                                     start_node_name=larger_pipe.start_node, 
                                     end_node_name=larger_pipe.end_node,
                                     length=props['length'], 
                                     diameter=props['diameter'], 
                                     roughness=props['roughness'], 
                                     minor_loss=props['minorloss'],
                                     status=props['status']) 
                    self.G.add_edge(larger_pipe.start_node, 
                                    larger_pipe.end_node, 
                                    larger_pipe.name)
                     
                    self.num_parallel_merge +=1
                    
        return self.wn, self.skeleton_map
    
    def _series_merge_properties(self, pipe0, pipe1):
        
        props = {}
        
        if pipe0.diameter > pipe1.diameter:
            larger_pipe = pipe0
        else:
            larger_pipe = pipe1
        
        props['length'] = pipe0.length + pipe1.length
        props['roughness'] = larger_pipe.roughness
             
        numer = props['length'] * pow((1/props['roughness']), -1.852)
        denom = ((pipe0.length * pow((1/pipe0.roughness), -1.852) * 
                  pow(pipe0.diameter, -4.871)) + \
                 (pipe1.length * pow((1/pipe1.roughness), -1.852) * 
                  pow(pipe1.diameter, -4.871)) )
        props['diameter'] = pow((numer/denom), (1.0/4.871)); 
            
        props['minorloss'] = larger_pipe.minor_loss
        props['status'] = larger_pipe.status
        
        return props
         
    def _parallel_merge_properties(self, pipe0, pipe1):
        
        props = {}
        
        if pipe0.diameter > pipe1.diameter:
            larger_pipe = pipe0
        else:
            larger_pipe = pipe1
        
        props['length'] = larger_pipe.length
        props['roughness'] = larger_pipe.roughness
             
        headloss = self.headloss[larger_pipe.name]
        numer = ( (pow(pipe0.length, -0.5*headloss)*(1/pipe0.roughness) * 
                   pow(pipe0.diameter, 2.63)) + \
                  (pow(pipe1.length, -0.5*headloss)*(1/pipe1.roughness) * 
                   pow(pipe1.diameter, 2.63)) )
        denom = pow(props['length'], 0.5*headloss)*(1/props['roughness'])
        props['diameter'] = pow((numer/denom) , 1.0/2.63)
        
        props['minorloss'] = larger_pipe.minor_loss
        props['status'] = larger_pipe.status
        
        return props
    
    def _move_demand(self, from_node_name, to_node_name):

        # Move demand from one node (in the JUNCTION object) to another (in the DEMAND object) 
        # Add the new DEMAND object to the demand map
        node = self.wn.get_node(from_node_name)
        if node.base_demand > 0:
            demand_pattern = node.demand_pattern_name
            if demand_pattern is None:
                demand_pattern = self.wn.options.pattern
            demand_name = 'INP'+str(self.new_demand_index)
            self.wn._add_demand(demand_name, 
                                to_node_name, 
                                base_demand=node.base_demand, 
                                demand_pattern_name=demand_pattern)
            self.new_demand_index += 1
            self._demand_map[to_node_name].append(self.wn._demands[demand_name])
            
        # Move demand from one node (in the DEMAND object) to another (in the DEMAND object) 
        for demand in self._demand_map[from_node_name]:
            self.wn._demands[demand.name].junction_name = to_node_name