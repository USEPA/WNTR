import wntr
import networkx as nx
import itertools
import copy
import logging

logger = logging.getLogger(__name__)

### TODO
"""
Add tests, check units
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

        # Get a list of components that are associated with controls
        comp_with_controls = []
        for name, control in wn.controls():
            comp_with_controls.append(control.requires())
        comp_with_controls = list(itertools.chain.from_iterable(comp_with_controls))
        self.comp_with_controls = list(set(comp_with_controls))
        
        # Calculate pipe headloss using a single period EPANET simulation
        duration = self.wn.options.time.duration
        sim = wntr.sim.EpanetSimulator(self.wn)
        self.wn.options.time.duration = 0
        results = sim.run_sim()
        head = results.node['head']
        headloss = {}
        for link_name, link in self.wn.links():
            headloss[link_name] = float(abs(head[link.start_node] - head[link.end_node]))
        self.headloss = headloss
        self.wn.options.time.duration = duration
    
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
            junc = self.wn.get_node(junc_name)
            if junc_name  in self.comp_with_controls:
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
                pipe not in self.comp_with_controls):
                continue
            
            logger.info('Branch trim:', junc_name, neighbors)
            
            # Update skeleton map        
            self.skeleton_map[neigh_junc_name].extend(self.skeleton_map[junc_name])
            self.skeleton_map[junc_name] = []
            
            # Move demand
            for demand in junc.demand_timeseries_list:
                neigh_junc.demand_timeseries_list.append(demand)
            junc.demand_timeseries_list.clear()

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
            junc = self.wn.get_node(junc_name)
            if junc in self.comp_with_controls:
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
                pipe0 not in self.comp_with_controls and \
                pipe1 not in self.comp_with_controls):
                continue
            # Find closest neighbor junction
            if (isinstance(neigh_junc0, wntr.network.Junction)) and \
               (isinstance(neigh_junc1, wntr.network.Junction)):
                if pipe0.length < pipe1.length:
                    closest_junc = neigh_junc0
                else:
                    closest_junc = neigh_junc1
            elif (isinstance(neigh_junc0, wntr.network.Junction)):
                closest_junc = neigh_junc0
            elif (isinstance(neigh_junc1, wntr.network.Junction)):
                closest_junc = neigh_junc1
            else:
                continue
            
            logger.info('Series pipe merge:', junc_name, neighbors)
                
            # Update skeleton map    
            self.skeleton_map[closest_junc.name].extend(self.skeleton_map[junc_name])
            self.skeleton_map[junc_name] = []
                
            # Move demand
            for demand in junc.demand_timeseries_list:
                closest_junc.demand_timeseries_list.append(demand)
            junc.demand_timeseries_list.clear()

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
            junc = self.wn.get_node(junc_name)
            if junc in self.comp_with_controls:
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
                        pipe0 not in self.comp_with_controls and \
                        pipe1 not in self.comp_with_controls):
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
