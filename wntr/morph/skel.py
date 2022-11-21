"""
The wntr.morph.skel module contains functions to skeletonize water
network models.
"""
import logging
import copy
import itertools
import networkx as nx
    
from wntr.network.elements import Pipe, Junction
from wntr.sim.core import WNTRSimulator
from wntr.sim import EpanetSimulator

logger = logging.getLogger(__name__)

def skeletonize(wn, pipe_diameter_threshold, branch_trim=True, series_pipe_merge=True, 
                parallel_pipe_merge=True, max_cycles=None, use_epanet=True, 
                return_map=False, return_copy=True):
    """
    Perform network skeletonization using branch trimming, series pipe merge, 
    and parallel pipe merge operations. Candidate pipes for removal is based 
    on a pipe diameter threshold.  
        
    Parameters
    -------------
    wn: wntr WaterNetworkModel
        Water network model
    pipe_diameter_threshold: float 
        Pipe diameter threshold used to determine candidate pipes for 
        skeletonization
    branch_trim: bool, optional
        If True, include branch trimming in skeletonization
    series_pipe_merge: bool, optional
        If True, include series pipe merge in skeletonization
    parallel_pipe_merge: bool, optional
        If True, include parallel pipe merge in skeletonization
    max_cycles: int or None, optional
        Maximum number of cycles in the skeletonization process. 
        One cycle performs branch trimming for all candidate pipes, followed
        by series pipe merging for all candidate pipes, followed by parallel 
        pipe merging for all candidate pipes. If max_cycles is set to None, 
        skeletonization will run until the network can no longer be reduced.
    use_epanet: bool, optional
        If True, use the EpanetSimulator to compute headloss in pipes.  
        If False, use the WNTRSimulator to compute headloss in pipes.
    return_map: bool, optional
        If True, return a skeletonization map. The map is a dictionary 
        that includes original nodes as keys and a list of skeletonized nodes 
        that were merged into each original node as values.
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    --------
    wntr WaterNetworkModel
        Skeletonized water network model
    dictionary
        Skeletonization map (if return_map = True) which includes original 
        nodes as keys and a list of skeletonized nodes that were merged into 
        each original node as values.
    """
    skel = _Skeletonize(wn, use_epanet, return_copy)
    
    skel.run(pipe_diameter_threshold, branch_trim, series_pipe_merge, 
             parallel_pipe_merge, max_cycles)
    
    if return_map:
        return skel.wn, skel.skeleton_map
    else:
        return skel.wn

		
class _Skeletonize(object):
    
    def __init__(self, wn, use_epanet, return_copy):
        
        if return_copy:
            # Get a copy of the WaterNetworkModel
            self.wn = copy.deepcopy(wn)
        else:
            self.wn = wn
        
        # Get the WaterNetworkModel graph
        G = self.wn.to_graph()
        G = G.to_undirected()
        self.G = G
        
        # Create a map of original nodes to skeletonized nodes
        skel_map = {}
        for node_name in self.wn.node_name_list:
            skel_map[node_name] = [node_name]
        self.skeleton_map = skel_map

        # Get a list of junction and pipe names that are associated with controls
        junc_with_controls = []
        pipe_with_controls = []
        for name, control in self.wn.controls():
            for req in control.requires():
                if isinstance(req, Junction):
                    junc_with_controls.append(req.name)
                elif isinstance(req, Pipe):
                    pipe_with_controls.append(req.name)
        self.junc_with_controls = list(set(junc_with_controls))
        self.pipe_with_controls = list(set(pipe_with_controls))
        
        # Calculate pipe headloss using a single period EPANET simulation
        duration = self.wn.options.time.duration
        if use_epanet:
            sim = EpanetSimulator(self.wn)
        else:
            sim = WNTRSimulator(self.wn)
        self.wn.options.time.duration = 0
        results = sim.run_sim()
        head = results.node['head']
        headloss = {}
        for link_name, link in self.wn.links():
            headloss[link_name] = float(abs(head.loc[0,link.start_node_name] - 
                                            head.loc[0,link.end_node_name]))
        self.headloss = headloss
        self.wn.options.time.duration = duration
    
        self.num_branch_trim = 0
        self.num_series_merge = 0
        self.num_parallel_merge = 0
        
		
    def run(self, pipe_threshold, branch_trim=True, series_pipe_merge=True, 
                parallel_pipe_merge=True, max_cycles=None):
        """
        Run iterative branch trim, series pipe merge, and parallel pipe merge 
        operations based on a pipe diameter threshold.  
        """
        num_junctions = self.wn.num_junctions
        iteration = 0
        flag = True
        
        while flag:
            if branch_trim:
                self.branch_trim(pipe_threshold)
            if series_pipe_merge:
                self.series_pipe_merge(pipe_threshold)
            if parallel_pipe_merge:
                self.parallel_pipe_merge(pipe_threshold)
            
            iteration = iteration + 1
            
            if (max_cycles is not None) and (iteration > max_cycles):
                flag = False
            if num_junctions == self.wn.num_junctions:
                flag = False
            else:
                num_junctions = self.wn.num_junctions

        return self.wn, self.skeleton_map
    
	
    def branch_trim(self, pipe_threshold):
        """
        Run a single branch trim operation based on a pipe diameter threshold.
        Branch trimming removes dead-end pipes smaller than the pipe 
        diameter threshold and redistributes demands (and associated demand 
        patterns) to the neighboring junction.
        """
        for junc_name in self.wn.junction_name_list:
            if junc_name in self.junc_with_controls:
                continue
            neighbors = list(nx.neighbors(self.G,junc_name))
            if len(neighbors) > 1:
                continue
            if len(neighbors) == 0:
                continue
            neigh_junc_name = neighbors[0] # only one neighbor
            nPipes = len(self.G.adj[junc_name][neigh_junc_name])
            if nPipes > 1:
                continue
            neigh_junc = self.wn.get_node(neigh_junc_name)
            if not (isinstance(neigh_junc, Junction)):
                continue
            pipe_name = list(self.G.adj[junc_name][neigh_junc_name].keys())[0] # only one pipe
            pipe = self.wn.get_link(pipe_name)
            if not ((isinstance(pipe, Pipe)) and \
                (pipe.diameter <= pipe_threshold) and \
                pipe_name not in self.pipe_with_controls):
                continue
            
            logger.info('Branch trim: '+ str(junc_name) + str(neighbors))
            
            # Update skeleton map        
            self.skeleton_map[neigh_junc_name].extend(self.skeleton_map[junc_name])
            self.skeleton_map[junc_name] = []
            
            # Move demand
            junc = self.wn.get_node(junc_name)
            for demand in junc.demand_timeseries_list:
                neigh_junc.demand_timeseries_list.append(demand)
            junc.demand_timeseries_list.clear()

            # Remove node and links from wn and G
            self.wn.remove_link(pipe_name, force=True)
            self.wn.remove_node(junc_name, force=True)
            self.G.remove_node(junc_name)
                    
            self.num_branch_trim +=1
            
        return self.wn, self.skeleton_map
    
	
    def series_pipe_merge(self, pipe_threshold):
        """
        Run a single series pipe merge operation based on a pipe diameter 
        threshold.  This operation combines pipes in series if both pipes are 
        smaller than the pipe diameter threshold. The larger diameter pipe is 
        retained, demands (and associated demand patterns) are redistributed 
        to the nearest junction.
        """
        for junc_name in self.wn.junction_name_list:
            if junc_name in self.junc_with_controls:
                continue
            neighbors = list(nx.neighbors(self.G,junc_name))
            if not (len(neighbors) == 2):
                continue
            neigh_junc_name0 = neighbors[0]
            neigh_junc_name1 = neighbors[1]
            neigh_junc0 = self.wn.get_node(neigh_junc_name0)
            neigh_junc1 = self.wn.get_node(neigh_junc_name1)
            if not ((isinstance(neigh_junc0, Junction)) or \
               (isinstance(neigh_junc1, Junction))):
                continue
            pipe_name0 = list(self.G.adj[junc_name][neigh_junc_name0].keys())
            pipe_name1 = list(self.G.adj[junc_name][neigh_junc_name1].keys())
            if (len(pipe_name0) > 1) or (len(pipe_name1) > 1):
                continue
            pipe_name0 = pipe_name0[0] # only one pipe
            pipe_name1 = pipe_name1[0] # only one pipe
            pipe0 = self.wn.get_link(pipe_name0)
            pipe1 = self.wn.get_link(pipe_name1)
            if not ((isinstance(pipe0, Pipe)) and \
                (isinstance(pipe1, Pipe)) and \
                ((pipe0.diameter <= pipe_threshold) and \
                (pipe1.diameter <= pipe_threshold)) and \
                pipe_name0 not in self.pipe_with_controls and \
                pipe_name1 not in self.pipe_with_controls):
                continue
            # Find closest neighbor junction
            if (isinstance(neigh_junc0, Junction)) and \
               (isinstance(neigh_junc1, Junction)):
                if pipe0.length < pipe1.length:
                    closest_junc = neigh_junc0
                else:
                    closest_junc = neigh_junc1
            elif (isinstance(neigh_junc0, Junction)):
                closest_junc = neigh_junc0
            elif (isinstance(neigh_junc1, Junction)):
                closest_junc = neigh_junc1
            else:
                continue
            
            logger.info('Series pipe merge: ' + str(junc_name) + str(neighbors))
                
            # Update skeleton map    
            self.skeleton_map[closest_junc.name].extend(self.skeleton_map[junc_name])
            self.skeleton_map[junc_name] = []
                
            # Move demand
            junc = self.wn.get_node(junc_name)
            for demand in junc.demand_timeseries_list:
                closest_junc.demand_timeseries_list.append(demand)
            junc.demand_timeseries_list.clear()

            # Remove node and links from wn and G
            self.wn.remove_link(pipe_name0, force=True)
            self.wn.remove_link(pipe_name1, force=True)
            self.wn.remove_node(junc_name, force=True)
            self.G.remove_node(junc_name)
            
            # Compute new pipe properties
            props = self._series_merge_properties(pipe0, pipe1)
            
            # Add new pipe to wn and G
            dominant_pipe = self._select_dominant_pipe(pipe0, pipe1)
            self.wn.add_pipe(dominant_pipe.name, 
                             start_node_name=neigh_junc_name0, 
                             end_node_name=neigh_junc_name1, 
                             length=props['length'], 
                             diameter=props['diameter'], 
                             roughness=props['roughness'], 
                             minor_loss=props['minorloss'],
                             initial_status=props['status']) 
            self.G.add_edge(neigh_junc_name0, 
                            neigh_junc_name1, 
                            dominant_pipe.name)
            
            self.num_series_merge +=1
            
        return self.wn, self.skeleton_map
        
		
    def parallel_pipe_merge(self, pipe_threshold):
        """
        Run a single parallel pipe merge operation based on a pipe diameter 
        threshold.  This operation combines pipes in parallel if both pipes are 
        smaller than the pipe diameter threshold. The larger diameter pipe is 
        retained.
        """
        
        for junc_name in self.wn.junction_name_list:
            if junc_name in self.junc_with_controls:
                continue
            neighbors = nx.neighbors(self.G,junc_name)
            for neighbor in [n for n in neighbors]:
                parallel_pipe_names = list(self.G.adj[junc_name][neighbor].keys())
                if len(parallel_pipe_names) == 1:
                    continue
                for (pipe_name0, pipe_name1) in itertools.combinations(parallel_pipe_names, 2):
                    try:
                        pipe0 = self.wn.get_link(pipe_name0)
                        pipe1 = self.wn.get_link(pipe_name1)
                    except:
                        continue # one of the pipes removed in previous loop
                    if not ((isinstance(pipe0, Pipe)) and \
                       (isinstance(pipe1, Pipe)) and \
                        ((pipe0.diameter <= pipe_threshold) and \
                        (pipe1.diameter <= pipe_threshold)) and \
                        pipe_name0 not in self.pipe_with_controls and \
                        pipe_name1 not in self.pipe_with_controls):
                        continue
                    
                    logger.info('Parallel pipe merge: '+ str(junc_name) + str((pipe_name0, pipe_name1)))

                    # Remove links from wn and G   
                    self.wn.remove_link(pipe_name0, force=True)
                    self.wn.remove_link(pipe_name1, force=True)
                    self.G.remove_edge(neighbor, junc_name, pipe_name0) 
                    self.G.remove_edge(junc_name, neighbor, pipe_name1)
            
                    # Compute new pipe properties
                    props = self._parallel_merge_properties(pipe0, pipe1)

                    # Add a new pipe to wn and G
                    dominant_pipe = self._select_dominant_pipe(pipe0, pipe1)
                    self.wn.add_pipe(dominant_pipe.name, 
                                     start_node_name=dominant_pipe.start_node_name, 
                                     end_node_name=dominant_pipe.end_node_name,
                                     length=props['length'], 
                                     diameter=props['diameter'], 
                                     roughness=props['roughness'], 
                                     minor_loss=props['minorloss'],
                                     initial_status=props['status']) 
                    self.G.add_edge(dominant_pipe.start_node_name, 
                                    dominant_pipe.end_node_name, 
                                    dominant_pipe.name)
                     
                    self.num_parallel_merge +=1
                    
        return self.wn, self.skeleton_map
    
	
    def _select_dominant_pipe(self, pipe0, pipe1):
	
        # Dominant pipe = larger diameter
        if pipe0.diameter >= pipe1.diameter:
            dominant_pipe = pipe0
        else:
            dominant_pipe = pipe1
            
        return dominant_pipe

		
    def _series_merge_properties(self, pipe0, pipe1):
        
        props = {}
        dominant_pipe = self._select_dominant_pipe(pipe0, pipe1)
            
        props['length'] = pipe0.length + pipe1.length
        props['diameter'] = dominant_pipe.diameter
        props['minorloss'] = dominant_pipe.minor_loss
        props['status'] = dominant_pipe.status
        
        props['roughness'] = (props['length']/(props['diameter']**4.87))**0.54 * \
            ((pipe0.length/((pipe0.diameter**4.87)*(pipe0.roughness**1.85))) + \
             (pipe1.length/((pipe1.diameter**4.87)*(pipe1.roughness**1.85))))**-0.54
        
        return props
         
		 
    def _parallel_merge_properties(self, pipe0, pipe1):
        
        props = {}
        dominant_pipe = self._select_dominant_pipe(pipe0, pipe1)
            
        props['length'] = dominant_pipe.length
        props['diameter'] = dominant_pipe.diameter
        props['minorloss'] = dominant_pipe.minor_loss
        props['status'] = dominant_pipe.status
        
        props['roughness'] = ((props['length']**0.54)/(props['diameter']**2.63)) * \
            ((pipe0.roughness*(pipe0.diameter**2.63))/(pipe0.length**0.54) + \
             (pipe1.roughness*(pipe1.diameter**2.63))/(pipe1.length**0.54))
        
        return props

