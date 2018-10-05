import logging
import numpy as np
import networkx as nx
import copy
from scipy.spatial.distance import pdist
try:
    import utm
except:
    utm = None
    
from .elements import Reservoir, Pipe

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
