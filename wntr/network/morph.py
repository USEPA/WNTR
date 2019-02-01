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
from wntr.sim import EpanetSimulator

logger = logging.getLogger(__name__)

def _deepcopy(wn):
    """
    Increase recursion limit for python 2.7 from 1000 to 3000
    """
    recursion_limit = sys.getrecursionlimit()
    
    if sys.version_info.major < 3:
        sys.setrecursionlimit(3000) 
        
    wn2 = copy.deepcopy(wn)
    
    if sys.version_info.major < 3:
        sys.setrecursionlimit(recursion_limit)
    
    return wn2

def scale_node_coordinates(wn, scale):
    """
    Scales node coordinates, using 1:scale
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        A WaterNetworkModel object
    
    scale: float
        Coordinate scale multiplier, in meters
    
    Returns
    --------
    A WaterNetworkModel object with updated node coordinates
    """
    wn2 = _deepcopy(wn)
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = (pos[0]*scale, pos[1]*scale)

    return wn2


def translate_node_coordinates(wn, offset_x, offset_y):
    """
    Translate node coordinates
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        A WaterNetworkModel object
    
    offset_x: tuple
        Translation in the x direction, in meters
    
    offset_y: float
        Translation in the y direction, in meters
    
    Returns
    --------
    A WaterNetworkModel object with updated node coordinates
    """
    wn2 = _deepcopy(wn)
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = (pos[0]+offset_x, pos[1]+offset_y)
    
    return wn2
        

def rotate_node_coordinates(wn, theta):
    """
    Rotate node coordinates counter-clockwise by theta degrees
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        A WaterNetworkModel object
    
    theta: float
        Node rotation, in degrees
    
    Returns
    --------
    A WaterNetworkModel object with updated node coordinates
    """
    wn2 = _deepcopy(wn)
    
    theta = np.radians(theta)
    R = np.array([[np.cos(theta),-np.sin(theta)], 
                  [np.sin(theta), np.cos(theta)]])
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = tuple(np.dot(R,pos))
    
    return wn2


def convert_node_coordinates_UTM_to_latlong(wn, zone_number, zone_letter):
    """
    Convert node coordinates from UTM coordinates to lat/long coordinates
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        A WaterNetworkModel object
    
    zone_number: int
       Zone number
    
    zone_letter: string
        Zone letter
    
    Returns
    --------
    A WaterNetworkModel object with updated node coordinates (latitude, longitude)
    """
    if utm is None:
        raise ImportError('utm package is required')
    
    wn2 = _deepcopy(wn)
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        lat, long = utm.to_latlon(pos[0], pos[1], zone_number, zone_letter)
        node.coordinates = (lat, long)

    return wn2


def convert_node_coordinates_latlong_to_UTM(wn):
    """
    Convert node coordinates lat/long coordinates to UTM coordinates
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        A WaterNetworkModel object
    
    Returns
    --------
    A WaterNetworkModel object with updated node coordinates (easting, northing)
    """
    if utm is None:
        raise ImportError('utm package is required')
    
    wn2 = _deepcopy(wn)
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        utm_coords = utm.from_latlon(pos[0], pos[1])
        easting = utm_coords[0]
        northing = utm_coords[1]
        node.coordinates = (easting, northing)

    return wn2


def convert_node_coordinates_to_UTM(wn, utm_map):
    """
    Convert node coordinates to UTM coordinates
    
    Parameters
    -----------
    utm_map: dictionary
        Dictionary containing two node names and their x, y coordinates in 
        UTM easting, northing in the format
        {'node name 1': (easting, northing), 'node name 2': (easting, northing)}
    
    Returns
    --------
    A WaterNetworkModel object with updated node coordinates (easting, northing)
    """
    
    wn2 = _convert_with_map(wn, utm_map, 'UTM')
    
    return wn2


def convert_node_coordinates_to_latlong(wn, latlong_map):
    """
    Convert node coordinates to lat/long coordinates
    
    Parameters
    -----------
    latlong_map: dictionary
        Dictionary containing two node names and their x, y coordinates in
        latitude, longitude in the format
        {'node name 1': (latitude, longitude), 'node name 2': (latitude, longitude)}
    
    Returns
    --------
    A WaterNetworkModel object with updated node coordinates (latitude, longitude)
    """
    
    wn2 = _convert_with_map(wn, latlong_map, 'LATLONG')
    
    return wn2

def _convert_with_map(wn, node_map, flag):
    
    if utm is None:
        raise ImportError('utm package is required')
    
    if not len(node_map.keys()) == 2:
        print('map must have exactly 2 entries')
        return
    
    wn2 = _deepcopy(wn)
    
    node_names = list(node_map.keys())
    
    A = []
    B = []
    for node_name, coords in node_map.items():
        A.append(np.array(wn2.get_node(node_name).coordinates))
        if flag == 'LATLONG':
            utm_coords = utm.from_latlon(coords[0], coords[1])
            zone_number = utm_coords[2]
            zone_letter = utm_coords[3] 
            B.append(np.array(utm_coords[0:2])) # B is in UTM coords
        elif flag == 'UTM':
            B.append(np.array(coords[0], coords[1])) # B is in UTM coords
    
    # Rotate, if needed
    vect1 = A[1] - A[0]
    vect2 = B[1] - B[0]
    vect1_unit = vect1/np.linalg.norm(vect1)
    vect2_unit = vect2/np.linalg.norm(vect2)
    dotproduct = np.dot(vect1_unit, vect2_unit)
    if dotproduct < 1:
        angle = np.arccos(dotproduct)*180/np.pi
        #print('angle', angle)
        wn2 = rotate_node_coordinates(wn2, angle)
        A[0] = np.array(wn2.get_node(node_names[0]).coordinates)
        A[1] = np.array(wn2.get_node(node_names[1]).coordinates)
        
    # Compute center points
    cpA = np.mean(A, axis=0)
    cpB = np.mean(B, axis=0)
    
    # Compute distance to each center point
    distA = np.mean([pdist([A[0], cpA])[0], pdist([A[1], cpA])[0]])     
    distB = np.mean([pdist([B[0], cpB])[0], pdist([B[1], cpB])[0]])
    
    # Compute ratio
    ratio = distB/distA
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        (easting, northing) = (np.array(pos) - cpA)*ratio + cpB
        if flag == 'LATLONG':
            lat, long = utm.to_latlon(easting, northing, zone_number, zone_letter)
            node.coordinates = (lat, long)
        elif flag == 'UTM':
            node.coordinates = (easting, northing)
    
    return wn2


def split_pipe(wn, pipe_name_to_split, new_pipe_name, new_junction_name,
               add_pipe_at_end=True, split_at_point=0.5):
    """
    Split a pipe by adding a junction and one new pipe segment.
    
    This function splits the original pipe into two pipes by adding a new 
    junction and new pipe to the model.  
    The updated model retains the original length of the pipe section. 
    The split occurs at a user specified distance between the 
    original start and end nodes of the pipe (in that direction). 
    The new pipe can be added to either end of the original pipe. 
    
    * The new junction has a base demand of 0 and the default demand pattern.
      The elevation and coordinates of the new junction are based on a linear 
      interpolation between the end points of the original pipe.
    
    * The new pipe has the same diameter, roughness, minor loss, 
      and base status of the original pipe. 

    * Check valves are not added to the new
      pipe. Since the new pipe can be connected at either the start
      or the end of the original pipe, the user can control if the split occurs before
      or after a check valve. 
    
    * No controls are added to the new pipe; the original pipe keeps any controls. 
    
    Parameters
    ----------
    pipe_name_to_split: string
        Name of the pipe to split.

    new_pipe_name: string
        Name of the new pipe to be added as the split part of the pipe.

    new_junction_name: string
        Name of the new junction to be added.

    add_pipe_at_end: bool (optional)
        If True, add the new pipe between the new node and the original end node. 
        If False, add the new pipe between the original start node and the new node.
        
    split_at_point: float (optional)
        Between 0 and 1, the position along the original pipe where the new 
        junction will be located.
        
    Returns
    -------
    A WaterNetworkModel object with split pipe
    """
    wn2 = _split_or_break_pipe(wn, pipe_name_to_split, new_pipe_name, 
                            [new_junction_name],
                            add_pipe_at_end, split_at_point, 'SPLIT')
    
    return wn2
    

def break_pipe(wn, pipe_name_to_split, new_pipe_name, new_junction_name_old_pipe,
               new_junction_name_new_pipe, add_pipe_at_end=True, split_at_point=0.5):
    """
    Break a pipe by adding a two unconnected junctions and one new pipe segment.
    
    
    
    This function splits the original pipe into two disconnected pipes by 
    adding two new junctions and new pipe to the model.  
    **This provides a true broken pipe -- i.e., there is no longer flow 
    possible from one side of the break to the other. This is more likely to 
    introduce non-convergable hydraulics than a simple split_pipe with a leak 
    added.**
    The updated model retains the original length of the pipe section. 
    The split occurs at a user specified distance between the 
    original start and end nodes of the pipe (in that direction). 
    The new pipe can be added to either end of the original pipe. 
    
    * The new junction has a base demand of 0 and the default demand pattern.
      The elevation and coordinates of the new junction are based on a linear 
      interpolation between the end points of the original pipe.
    
    * The new pipe has the same diameter, roughness, minor loss, 
      and base status of the original pipe. 

    * Check valves are not added to the new
      pipe. Since the new pipe can be connected at either the start
      or the end of the original pipe, the user can control if the split occurs before
      or after a check valve. 
    
    * No controls are added to the new pipe; the original pipe keeps any controls. 
    
    Parameters
    ----------
    pipe_name_to_split: string
        Name of the pipe to split.

    new_pipe_name: string
        Name of the new pipe to be added as the split part of the pipe.

    new_junction_name_old_pipe: string
        Name of the new junction to be added to the original pipe

    new_junction_name_old_pipe: string
        Name of the new junction to be added to the new pipe

    add_pipe_at_node: string
        Either 'START' or 'END', 'END' is default. The new pipe goes between this
        original node and the new junction.
        
    split_at_point: float
        Between 0 and 1, the position along the original pipe where the new 
        junction will be located.

    Returns
    -------
    A WaterNetworkModel object with pipe break
    """
    wn2 = _split_or_break_pipe(wn, pipe_name_to_split, new_pipe_name, 
                            [new_junction_name_old_pipe, new_junction_name_new_pipe],
                            add_pipe_at_end, split_at_point, 'BREAK')
    
    return wn2

def _split_or_break_pipe(wn, pipe_name_to_split, new_pipe_name, 
                         new_junction_names, add_pipe_at_end, split_at_point,
                         flag):
    
    wn2 = _deepcopy(wn)
    
    pipe = wn2.get_link(pipe_name_to_split)
    
    # Do sanity checks
    if not isinstance(pipe, Pipe):
        raise ValueError('You can only split pipes.')
    if split_at_point < 0 or split_at_point > 1:
        raise ValueError('split_at_point must be between 0 and 1')
    node_list = [node_name for node_name, node in wn2.nodes()]
    link_list = [link_name for link_name, link in wn2.links()]
    for new_junction_name in new_junction_names:
        if new_junction_name in node_list:
            raise RuntimeError('The junction name you provided is already \
                               being used for another node.')
    if new_pipe_name in link_list:
        raise RuntimeError('The new link name you provided is already being \
                           used for another link.')

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
    for new_junction_name in new_junction_names:
        wn2.add_junction(new_junction_name, base_demand=0.0, 
                         demand_pattern=None, elevation=junction_elevation, 
                         coordinates=junction_coordinates)

    original_length = pipe.length

    if flag == 'BREAK':
        j0 = new_junction_names[0]
        j1 = new_junction_names[1]
    elif flag == 'SPLIT':
        j0 = new_junction_names[0]
        j1 = new_junction_names[0]
            
    if add_pipe_at_end:
        pipe.end_node = wn2.get_node(j0) 
        # add new pipe and change original length
        wn2.add_pipe(new_pipe_name, j1, end_node.name,
                     original_length*(1-split_at_point), pipe.diameter, 
                     pipe.roughness, pipe.minor_loss, pipe.status, pipe.cv)
        pipe.length = original_length*split_at_point
    else: # add pipe at start
        pipe.start_node = wn2.get_node(j0) 
        # add new pipe and change original length
        wn2.add_pipe(new_pipe_name, start_node.name, j1, 
                     original_length*split_at_point, pipe.diameter, 
                     pipe.roughness, pipe.minor_loss, pipe.status, pipe.cv)
        pipe.length = original_length*(1-split_at_point)
        
    if pipe.cv:
        logger.warn('You are splitting a pipe with a check valve. The new \
                    pipe will not have a check valve.')
    
    return wn2 


def skeletonize(wn, pipe_diameter_threshold, branch_trim=True, series_pipe_merge=True, 
                parallel_pipe_merge=True, max_cycles=None, use_epanet=True, 
                return_map=False):
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
    
    use_epanet: bool (optional)
        If True, use the EpanetSimulator to compute headloss in pipes.  If False, 
        use the WNTRSimulator to compute headloss in pipes
    
    return_map: bool (optional, default = False)
        Return a skeletonization map.   The map is a dictionary 
        that includes original nodes as keys and a list of skeletonized nodes 
        that were merged into each original node as values.
                
    Returns
    --------
    A skeletonized WaterNetworkModel object and (if return_map = True) a 
    skeletonization map.
    """
    skel = _Skeletonize(wn, use_epanet)
    
    skel.run(pipe_diameter_threshold, branch_trim, series_pipe_merge, 
             parallel_pipe_merge, max_cycles)
    
    if return_map:
        return skel.wn, skel.skeleton_map
    else:
        return skel.wn

		
class _Skeletonize(object):
    
    def __init__(self, wn, use_epanet):
        
        # Get a copy of the WaterNetworkModel
        self.wn = _deepcopy(wn)
        
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

