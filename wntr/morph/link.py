"""
The wntr.morph.link module contains functions to split/break pipes.
"""
import logging

from wntr.network.elements import Reservoir, Pipe
from wntr.morph.node import _deepcopy_wn

logger = logging.getLogger(__name__)

        
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
    
    wn2 = _deepcopy_wn(wn)
    
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
