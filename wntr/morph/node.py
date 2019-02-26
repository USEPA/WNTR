"""
The wntr.morph.node module contains functions to modify node coordinates.
"""
import logging
import sys
import copy
import numpy as np
from scipy.spatial.distance import pdist
try:
    import utm
except:
    utm = None

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
    
    wn2 = _deepcopy_wn(wn)
    
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
    
    wn2 = _deepcopy_wn(wn)
    
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
    
    wn2 = _deepcopy_wn(wn)
    
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