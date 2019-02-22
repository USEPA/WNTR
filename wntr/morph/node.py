"""
The wntr.morph.node module contains functions to modify node coordinates.
"""
import logging
import sys
import copy
import numpy as np
    
logger = logging.getLogger(__name__)


def _deepcopy_wn(wn):
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
    wn2 = _deepcopy_wn(wn)
    
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
    wn2 = _deepcopy_wn(wn)
    
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
    wn2 = _deepcopy_wn(wn)
    
    theta = np.radians(theta)
    R = np.array([[np.cos(theta),-np.sin(theta)], 
                  [np.sin(theta), np.cos(theta)]])
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = tuple(np.dot(R,pos))
    
    return wn2
