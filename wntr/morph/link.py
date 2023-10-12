"""
The wntr.morph.link module contains functions to split/break pipes.
"""
import logging
import copy

import wntr.network
from wntr.network.elements import Reservoir, Pipe
from wntr.network import WaterNetworkModel

logger = logging.getLogger(__name__)


def split_pipe(wn, pipe_name_to_split, new_pipe_name, new_junction_name,
               add_pipe_at_end=True, split_at_point=0.5, return_copy=True):
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
    wn: wntr WaterNetworkModel
        Water network model
    pipe_name_to_split: string
        Name of the pipe to split.
    new_pipe_name: string
        Name of the new pipe to be added as the split part of the pipe.
    new_junction_name: string
        Name of the new junction to be added.
    add_pipe_at_end: bool, optional
        If True, add the new pipe between the new node and the original end node. 
        If False, add the new pipe between the original start node and the new node.
    split_at_point: float, optional
        Between 0 and 1, the position along the original pipe where the new 
        junction will be located.
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    -------
    wntr WaterNetworkModel
        Water network model with split pipe
    """
    wn2 = _split_or_break_pipe(wn, pipe_name_to_split, new_pipe_name,
                               [new_junction_name],
                               add_pipe_at_end, split_at_point, 'SPLIT', return_copy)

    return wn2


def break_pipe(wn, pipe_name_to_split, new_pipe_name, new_junction_name_old_pipe,
               new_junction_name_new_pipe, add_pipe_at_end=True,
               split_at_point=0.5, return_copy=True):
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
    wn: wntr WaterNetworkModel
        Water network model
    pipe_name_to_split: string
        Name of the pipe to split.
    new_pipe_name: string
        Name of the new pipe to be added as the split part of the pipe.
    new_junction_name_old_pipe: string
        Name of the new junction to be added to the original pipe
    new_junction_name_new_pipe: string
        Name of the new junction to be added to the new pipe
    add_pipe_at_end: bool, optional
        If True, add the new pipe at after the new junction. If False, add the 
        new pipe before the new junction
    split_at_point: float, optional
        Relative position (value between 0 and 1) along the original pipe 
        where the new junction will be located.
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    -------
    wntr WaterNetworkModel
        Water network model with pipe break
    """
    wn2 = _split_or_break_pipe(wn, pipe_name_to_split, new_pipe_name,
                               [new_junction_name_old_pipe, new_junction_name_new_pipe],
                               add_pipe_at_end, split_at_point, 'BREAK', return_copy)

    return wn2


def _split_or_break_pipe(wn, pipe_name_to_split, new_pipe_name,
                         new_junction_names, add_pipe_at_end, split_at_point,
                         flag, return_copy):
    if return_copy:  # Get a copy of the WaterNetworkModel
        wn2 = copy.deepcopy(wn)
    else:
        wn2 = wn

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

    # calculate the new coordinates and where each vertice belongs
    first_vertices = []
    last_vertices = []
    if pipe.vertices:
        # Extract pipe vertices including the start and end node coordinate
        pipe_vertices = [pipe.start_node.coordinates,
                         *pipe.vertices,
                         pipe.end_node.coordinates]
        segments = []
        subtotal = 0
        for i in range(len(pipe_vertices) - 1):
            start_pos = pipe_vertices[i]
            end_pos = pipe_vertices[i + 1]
            segment_length = (sum([(a - b) ** 2 for (a, b) in zip(start_pos, end_pos)])
                              ** 0.5)
            segments.append({'start_pos': start_pos,
                             'end_pos': end_pos,
                             'length': segment_length,
                             'subtotal': subtotal})

            subtotal += segment_length

        last_segment = segments[-1]
        length = last_segment['subtotal'] + last_segment['length']
        split_length = length * split_at_point

        # Loop over segments and assign vertices (start_pos) to the first or 
        # second pipe. Skip the first segment (its start_pos is not a vertice)
        for segment in segments:
            if segment['start_pos'] == pipe.start_node.coordinates:
                pass
            elif segment['subtotal'] < split_length:
                first_vertices.append(segment['start_pos'])
            else:
                last_vertices.append(segment['start_pos'])

        # Identify the segment that cross the split point and compute the new
        # junction coordinates
        for segment in segments:
            if segment['subtotal'] + segment['length'] >= split_length > segment['subtotal']:
                split_at = ((split_length - segment['subtotal'])
                            / segment['length'])
                x0 = segment['start_pos'][0]
                dx = segment['end_pos'][0] - x0
                y0 = segment['start_pos'][1]
                dy = segment['end_pos'][1] - y0
                junction_coordinates = (x0 + dx * split_at,
                                        y0 + dy * split_at)
    # calculate the new coordinates without vertices            
    else:
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
                     original_length * (1 - split_at_point), pipe.diameter,
                     pipe.roughness, pipe.minor_loss, pipe.status, pipe.check_valve)
        pipe.length = original_length * split_at_point
        pipe.vertices = first_vertices
        new_pipe = wn2.get_link(new_pipe_name)
        new_pipe.vertices = last_vertices
    else:  # add pipe at start
        pipe.start_node = wn2.get_node(j0)
        # add new pipe and change original length
        wn2.add_pipe(new_pipe_name, start_node.name, j1,
                     original_length * split_at_point, pipe.diameter,
                     pipe.roughness, pipe.minor_loss, pipe.status, pipe.check_valve)
        pipe.length = original_length * (1 - split_at_point)
        pipe.vertices = last_vertices
        new_pipe = wn2.get_link(new_pipe_name)
        new_pipe.vertices = first_vertices

    if pipe.check_valve:
        logger.warn('You are splitting a pipe with a check valve. The new \
                    pipe will not have a check valve.')

    return wn2


def reverse_link(wn: WaterNetworkModel, link_name: str, return_copy=True) -> WaterNetworkModel:
    """
    Reverse a link to switch between the start and end nodes
    The function can reverse any link (pipe, pump or valve)
    Vertices order will be reversed to maintain the link layout

    Parameters
    ----------
    wn:             WaterNetworkModel
                    The network object where link should be reversed.
    link_name:      string
                    The name of the link to revers.
    return_copy:    bool, optional
                    If True, modify and return a copy of the WaterNetworkModel object.
                    If False, modify and return the original WaterNetworkModel object.

    Returns
    -------
    WaterNetworkModel
    A network object after link was reversed
    """
    if return_copy:  # Get a copy of the WaterNetworkModel
        wn2 = copy.deepcopy(wn)
    else:
        wn2 = wn

    link = wn2.get_link(link_name)
    start_node = link.start_node
    end_node = link.end_node
    vertices = link.vertices

    link.start_node = end_node
    link.end_node = start_node
    link.vertices = vertices[::-1]

    return wn2
