"""
The wntr.network.morph module contains functions to modify network morphology.
"""
import logging
import itertools
import sys
import copy
import numpy as np
import networkx as nx
from scipy.spatial.distance import pdist
try:
    import utm
except:
    utm = None
    
from wntr.network.elements import Reservoir, Pipe, Junction
from wntr.sim.core import WNTRSimulator

logger = logging.getLogger(__name__)


def scale_node_coordinates(wn, scale):
    """
    Scales node coordinates, using 1:scale (scale should be in meters)
    
    Parameters
    -----------
    scale : float
        Coordinate scale multiplier.
    """
    wn2 = copy.deepcopy(wn)
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = (pos[0]*scale, pos[1]*scale)

    return wn2

def translate_node_coordinates(wn, x, y):
    """
    Translate node coordinates
    """
    wn2 = copy.deepcopy(wn)
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = (pos[0]+x, pos[1]+y)
    
    return wn2
        
def rotate_node_coordinates(wn, theta):
    """
    Rotate node coordinates counterclockwise by theta degrees
    """
    wn2 = copy.deepcopy(wn)
    
    theta = np.radians(theta)
    R = np.array([[np.cos(theta),-np.sin(theta)], 
                  [np.sin(theta), np.cos(theta)]])
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = tuple(np.dot(R,pos))
    
    return wn2

def convert_node_coordinates_UTM_to_latlong(wn, zone_number, zone_letter):
    """
    Convert node coordinates from UTM to lat/long
    """
    if utm is None:
        raise ImportError('utm is required')
    
    wn2 = copy.deepcopy(wn)
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        lat, long = utm.to_latlon(pos[0], pos[1], zone_number, zone_letter)
        node.coordinates = (long, lat)

    return wn2

def convert_node_coordinates_to_latlong(wn, Am, Bm, Alatlong, Blatlong):
    """
    Convert node coordinates from UTM to lat/long
    """
    if utm is None:
        raise ImportError('utm is required')
    
    wn2 = copy.deepcopy(wn)
    
    A1 = Am
    B1 = Bm
    A2 = utm.from_latlon(Alatlong[0], Alatlong[1])
    B2 = utm.from_latlon(Blatlong[0], Blatlong[1])
    zone_number = A2[2]
    zone_letter = A2[3] 
    A2 = A2[0:2]
    B2 = B2[0:2]
    
    cp1 = ((A1[0] + B1[0])/2, (A1[1] + B1[1])/2)
    cp2 = ((A2[0] + B2[0])/2, (A2[1] + B2[1])/2)
    
    dist1 = np.mean([pdist(np.array([A1, cp1]))[0], pdist(np.array([B1, cp1]))[0]])     
    dist2 = np.mean([pdist(np.array([A2, cp2]))[0], pdist(np.array([B2, cp2]))[0]])
    
    ratio = dist2/dist1
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        scaled_vect = tuple(np.subtract(pos, cp1)*ratio)
        new_pos = tuple(np.add(scaled_vect, cp2))
        lat, long = utm.to_latlon(new_pos[0], new_pos[1], zone_number, zone_letter)
        node.coordinates = (long, lat)
    
    return wn2
        
def split_pipe(wn, pipe_name_to_split, new_pipe_name, new_junction_name,
               add_pipe_at_node='end', split_at_point=0.5):
    """Splits a pipe by adding a junction and one new pipe segment
    
    This method is convenient when adding leaks to a pipe. It provides 
    an initially zero-demand node at some point along the pipe and then
    reconnects the original pipe to this node and adds a new pipe to the
    other side. Hydraulic paths are maintained. The new junction can 
    then have a leak added to it.
    
    It is important to note that check valves are not added to the new
    pipe. By allowing the new pipe to be connected at either the start
    or the end of the old pipe, this allows the split to occur before
    or after the check valve. Additionally, no controls will be added
    to the new pipe; the old pipe will keep any controls. Again, this
    allows the split to occur before or after a "valve" that is controlled
    by opening or closing a pipe.
    
    This method keeps 'pipe_name_to_split', resizes it, and adds
    a new pipe to keep total length equal. The pipe will be split at 
    a new junction placed at a point 'split_at_point' of the way 
    between the start and end (in that direction). The new pipe can be
    added to 'add_pipe_at_node' of either ``start`` or ``end``. For
    example, if ``add_pipe_at_node='start'``, then the original pipe
    will go from the new junction to the original end node, and the
    new pipe will go from the original start node to the new junction.
    
    The new pipe will have the same diameter,
    roughness, minor loss, and base status of the original
    pipe. The new junction will have a base demand of 0,
    an elevation equal to the 'split_at_point' x 100% of the 
    elevation between the
    original start and end nodes, coordinates at 'split_at_point'
    between the original start and end nodes, and will use the
    default demand pattern.
    
    Parameters
    ----------
    pipe_name_to_split: string
        The name of the pipe to split.

    new_pipe_name: string
        The name of the new pipe to be added as the split part of the pipe.

    new_junction_name: string
        The name of the new junction to be added.

    add_pipe_at_node: string
        Either 'start' or 'end', 'end' is default. The new pipe goes between this
        original node and the new junction.
        
    split_at_point: float
        Between 0 and 1, the position along the original pipe where the new 
        junction will be located.
            
        
    Returns
    -------
    tuple
        returns (original_pipe, new_junction, new_pipe) objects
        
    Raises
    ------
    ValueError
        The link is not a pipe, `split_at_point` is out of bounds, `add_pipe_at_node` is invalid.
    RuntimeError
        The `new_junction_name` or `new_pipe_name` is already in use.
        
    """
    
    # Do sanity checks
    pipe = wn.get_link(pipe_name_to_split)
    if not isinstance(pipe, Pipe):
        raise ValueError('You can only split pipes.')
    if split_at_point < 0 or split_at_point > 1:
        raise ValueError('split_at_point must be between 0 and 1')
    if add_pipe_at_node.lower() not in ['end', 'start']:
        raise ValueError('add_pipe_at_node must be "end" or "start"')
    node_list = [node_name for node_name, node in wn.nodes()]
    link_list = [link_name for link_name, link in wn.links()]
    if new_junction_name in node_list:
        raise RuntimeError('The junction name you provided is already being used for another node.')
    if new_pipe_name in link_list:
        raise RuntimeError('The new link name you provided is already being used for another link.')

    # Get start and end node info
    start_node = pipe.start_node
    end_node = pipe.end_node
    
    # calculate the new elevation
    if isinstance(start_node, Reservoir):
        junction_elevation = end_node.elevation
    elif isinstance(end_node, Reservoir):
        junction_elevation = start_node.elevation
    else:
        e0 = start_node.elevation
        de = end_node.elevation - e0
        junction_elevation = e0 + de * split_at_point

    # calculate the new coordinates
    x0 = pipe.start_node.coordinates[0]
    dx = pipe.end_node.coordinates[0] - x0
    y0 = pipe.start_node.coordinates[1]
    dy = pipe.end_node.coordinates[1] - y0
    junction_coordinates = (x0 + dx * split_at_point,
                            y0 + dy * split_at_point)

    # add the new junction
    wn.add_junction(new_junction_name, base_demand=0.0, demand_pattern=None,
                      elevation=junction_elevation, coordinates=junction_coordinates)
    new_junction = wn.get_node(new_junction_name)

    # remove the original pipe from the graph (to be added back below)
    #self._graph.remove_edge(pipe.start_node, pipe.end_node, key=pipe_name_to_split)
    original_length = pipe.length

    if add_pipe_at_node.lower() == 'start':
        # add original pipe back to graph between new junction and original end
        pipe.start_node = new_junction_name
        # add new pipe and change original length
        wn.add_pipe(new_pipe_name, start_node.name, new_junction_name,
                      original_length*split_at_point, pipe.diameter, pipe.roughness,
                      pipe.minor_loss, pipe.status, pipe.cv)
        pipe.length = original_length * (1-split_at_point)

    elif add_pipe_at_node.lower() == 'end':
        # add original pipe back to graph between original start and new junction
        pipe.end_node = new_junction_name      
        # add new pipe and change original length
        wn.add_pipe(new_pipe_name, new_junction_name, end_node.name,
                      original_length*(1-split_at_point), pipe.diameter, pipe.roughness,
                      pipe.minor_loss, pipe.status, pipe.cv)
        pipe.length = original_length * split_at_point
    new_pipe = wn.get_link(new_pipe_name)
    if pipe.cv:
        logger.warn('You are splitting a pipe with a check valve. The new pipe will not have a check valve.')
    
    return wn #(pipe, new_junction, new_pipe)

def _break_pipe(wn, pipe_name_to_split, new_pipe_name, new_junction_name_old_pipe,
               new_junction_name_new_pipe,
               add_pipe_at_node='end', split_at_point=0.5):
    """BETA Breaks a pipe by adding a two unconnected junctions and one new pipe segment
    
    This method provides a true broken pipe -- i.e., there is no longer flow possible 
    from one side of the break to the other. This is more likely to break the model
    through non-convergable hydraulics than a simple split_pipe with a leak added.

    It is important to note that check valves are not added to the new
    pipe. By allowing the new pipe to be connected at either the start
    or the end of the old pipe, this allows the break to occur before
    or after the check valve. This may mean that one of the junctions will
    not have demand, as it would be inaccessible. No error checking is 
    performed to stop such a condition, it is left to the user.
    Additionally, no controls will be added
    to the new pipe; the old pipe will keep any controls. Again, this
    allows the break to occur before or after a "valve" that is controlled
    by opening or closing a pipe.
    
    This method keeps 'pipe_name_to_split', resizes it, and adds
    a new pipe to keep total length equal. Two junctions are added at the same position,
    but are not connected. The pipe will be split at 
    a point 'split_at_point' of the way 
    between the start and end (in that direction). The new pipe can be
    added to 'add_pipe_at_node' of either ``start`` or ``end``. For
    example, if ``add_pipe_at_node='start'``, then the original pipe
    will go from the first new junction to the original end node, and the
    new pipe will go from the original start node to the second new junction.
    
    The new pipe will have the same diameter,
    roughness, minor loss, and base status of the original
    pipe. The new junctions will have a base demand of 0,
    an elevation equal to the 'split_at_point' x 100% of the 
    elevation between the
    original start and end nodes, coordinates at 'split_at_point'
    between the original start and end nodes, and will use the
    default demand pattern. These junctions will be returned so that 
    a new demand (usually a leak) can be added to them.
    
    The original pipe will keep its controls.  
    The new pipe _will not_ have any controls automatically added;
    this includes not adding a check valve.
    
    Parameters
    ----------
    pipe_name_to_split: string
        The name of the pipe to split.

    new_pipe_name: string
        The name of the new pipe to be added as the split part of the pipe.

    new_junction_name_old_pipe: string
        The name of the new junction to be added to the original pipe

    new_junction_name_old_pipe: string
        The name of the new junction to be added to the new pipe

    add_pipe_at_node: string
        Either 'start' or 'end', 'end' is default. The new pipe goes between this
        original node and the new junction.
        
    split_at_point: float
        Between 0 and 1, the position along the original pipe where the new 
        junction will be located.
            
        
    Returns
    -------
    tuple
        Returns the new junctions that have been created, with the junction attached to the 
        original pipe as the first element of the tuple
        
    """
    
    # Do sanity checks
    pipe = wn.get_link(pipe_name_to_split)
    if not isinstance(pipe, Pipe):
        raise ValueError('You can only split pipes.')
    if split_at_point < 0 or split_at_point > 1:
        raise ValueError('split_at_point must be between 0 and 1')
    if add_pipe_at_node.lower() not in ['end', 'start']:
        raise ValueError('add_pipe_at_node must be "end" or "start"')
    node_list = [node_name for node_name, node in wn.nodes()]
    link_list = [link_name for link_name, link in wn.links()]
    if new_junction_name_old_pipe in node_list or new_junction_name_new_pipe in node_list:
        raise RuntimeError('The junction name you provided is already being used for another node.')
    if new_pipe_name in link_list:
        raise RuntimeError('The new link name you provided is already being used for another link.')

    # Get start and end node info
    start_node = wn.get_node(pipe.start_node)
    end_node = wn.get_node(pipe.end_node)
    
    # calculate the new elevation
    if isinstance(start_node, Reservoir):
        junction_elevation = end_node.elevation
    elif isinstance(end_node, Reservoir):
        junction_elevation = start_node.elevation
    else:
        e0 = start_node.elevation
        de = end_node.elevation - e0
        junction_elevation = e0 + de * split_at_point

    # calculate the new coordinates
    x0 = pipe.start_node.coordinates[0]
    dx = pipe.end_node.coordinates[0] - x0
    y0 = pipe.start_node.coordinates[1]
    dy = pipe.end_node.coordinates[1] - y0
    junction_coordinates = (x0 + dx * split_at_point,
                            y0 + dy * split_at_point)

    # add the new junction
    wn.add_junction(new_junction_name_old_pipe, base_demand=0.0, demand_pattern=None,
                      elevation=junction_elevation, coordinates=junction_coordinates)
    new_junction1 = wn.get_node(new_junction_name_old_pipe)
    wn.add_junction(new_junction_name_new_pipe, base_demand=0.0, demand_pattern=None,
                      elevation=junction_elevation, coordinates=junction_coordinates)
    new_junction2 = wn.get_node(new_junction_name_new_pipe)

    # remove the original pipe from the graph (to be added back below)
    wn._graph.remove_edge(pipe.start_node, pipe.end_node, key=pipe_name_to_split)
    original_length = pipe.length

    if add_pipe_at_node.lower() == 'start':
        # add original pipe back to graph between new junction and original end
        pipe.start_node_name = new_junction_name_old_pipe
        wn._graph.add_edge(new_junction_name_old_pipe, end_node.name, key=pipe_name_to_split)
        nx.set_edge_attributes(wn._graph, name='type', values={(new_junction_name_old_pipe, 
                                                      end_node.name,
                                                      pipe_name_to_split):'pipe'})
        # add new pipe and change original length
        wn.add_pipe(new_pipe_name, start_node.name, new_junction_name_new_pipe,
                      original_length*split_at_point, pipe.diameter, pipe.roughness,
                      pipe.minor_loss, pipe.status, pipe.cv)
        pipe.length = original_length * (1-split_at_point)

    elif add_pipe_at_node.lower() == 'end':
        # add original pipe back to graph between original start and new junction
        pipe.end_node_name = new_junction_name_old_pipe            
        wn._graph.add_edge(start_node.name, new_junction_name_old_pipe, key=pipe_name_to_split)
        nx.set_edge_attributes(wn._graph, name='type', values={(start_node.name,
                                                      new_junction_name_old_pipe,
                                                      pipe_name_to_split):'pipe'})
        # add new pipe and change original length
        wn.add_pipe(new_pipe_name, new_junction_name_new_pipe, end_node.name,
                      original_length*(1-split_at_point), pipe.diameter, pipe.roughness,
                      pipe.minor_loss, pipe.status, pipe.cv)
        pipe.length = original_length * split_at_point
    new_pipe = wn.get_link(new_pipe_name)
    if pipe.cv:
        logger.warn('You are splitting a pipe with a check valve. The new pipe will not have a check valve.')
    return wn #(pipe, new_junction1, new_junction2, new_pipe)


def skeletonize(wn, pipe_diameter_threshold, branch_trim=True, series_pipe_merge=True, 
                parallel_pipe_merge=True, max_cycles=None, return_map=False):
    """
    Perform network skeletonization using branch trimming, series pipe merge, 
    and parallel pipe merge operations. Candidate pipes for removal is based 
    on a pipe diameter threshold.  
        
    Parameters
    -------------
    wn: wntr WaterNetworkModel
        A WaterNetworkModel object
    
    pipe_diameter_threshold: float 
        Pipe diameter threshold used to determine candidate pipes for 
        skeletonization
    
    branch_trim: bool (optional, default = True)
        Include branch trimming in skeletonization
    
    series_pipe_merge: bool (optional, default = True)
        Include series pipe merge in skeletonization
        
    parallel_pipe_merge: bool (optional, default = True)
        Include parallel pipe merge in skeletonization
        
    max_cycles: int or None (optional, default = None)
        Defines the maximum number of cycles in the skeletonization process. 
        One cycle performs branch trimming for all candidate pipes, followed
        by series pipe merging for all candidate pipes, followed by parallel 
        pipe merging for all candidate pipes. If max_cycles is set to None, 
        skeletonization will run until the network can no longer be reduced.
        
    return_map: bool (optional, default = False)
        Return a skeletonization map.   The map is a dictionary 
        that includes original nodes as keys and a list of skeletonized nodes 
        that were merged into each original node as values.
                
    Returns
    --------
    A skeletonized WaterNetworkModel object and (if return_map = True) a 
    skeletonization map.
    """
    skel = _Skeletonize(wn)
    
    skel.run(pipe_diameter_threshold, branch_trim, series_pipe_merge, 
             parallel_pipe_merge, max_cycles)
    
    if return_map:
        return skel.wn, skel.skeleton_map
    else:
        return skel.wn

		
class _Skeletonize(object):
    
    def __init__(self, wn):
        
        # Get a copy of the WaterNetworkModel
        # Increase recursion limit for python 2.7 from 1000 to 3000
        recursion_limit = sys.getrecursionlimit()
        if sys.version_info.major < 3:
            sys.setrecursionlimit(3000) 
        self.wn = copy.deepcopy(wn)
        if sys.version_info.major < 3:
            sys.setrecursionlimit(recursion_limit)
        
        # Get the WaterNetworkModel graph
        G = self.wn.get_graph()
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
        for name, control in wn.controls():
            for req in control.requires():
                if isinstance(req, Junction):
                    junc_with_controls.append(req.name)
                elif isinstance(req, Pipe):
                    pipe_with_controls.append(req.name)
        self.junc_with_controls = list(set(junc_with_controls))
        self.pipe_with_controls = list(set(pipe_with_controls))
        
        # Calculate pipe headloss using a single period EPANET simulation
        duration = self.wn.options.time.duration
        sim = WNTRSimulator(self.wn)
        self.wn.options.time.duration = 0
        results = sim.run_sim()
        head = results.node['head']
        headloss = {}
        for link_name, link in self.wn.links():
            headloss[link_name] = float(abs(head[link.start_node_name] - head[link.end_node_name]))
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
            self.wn.remove_link(pipe_name)
            self.wn.remove_node(junc_name)
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
            self.wn.remove_link(pipe_name0)
            self.wn.remove_link(pipe_name1)
            self.wn.remove_node(junc_name)
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
                             status=props['status']) 
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
                    if not ((isinstance(pipe0, Pipe)) and \
                       (isinstance(pipe1, Pipe)) and \
                        ((pipe0.diameter <= pipe_threshold) and \
                        (pipe1.diameter <= pipe_threshold)) and \
                        pipe_name0 not in self.pipe_with_controls and \
                        pipe_name1 not in self.pipe_with_controls):
                        continue
                    
                    logger.info('Parallel pipe merge: '+ str(junc_name) + str((pipe_name0, pipe_name1)))

                    # Remove links from wn and G   
                    self.wn.remove_link(pipe_name0)
                    self.wn.remove_link(pipe_name1)
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
                                     status=props['status']) 
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

