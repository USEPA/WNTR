"""
The wntr.morph.node module contains functions to modify node coordinates.
"""
import logging
import copy
import numpy as np
from scipy.spatial.distance import pdist
try:
    import utm
except:
    utm = None

logger = logging.getLogger(__name__)


def scale_node_coordinates(wn, scale, return_copy=True):
    """
    Scales node coordinates, using 1:scale
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        Water network model
    scale: float
        Coordinate scale multiplier, in meters
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    --------
    wntr WaterNetworkModel
        Water network model with updated node coordinates
    """
    if return_copy: # Get a copy of the WaterNetworkModel
        wn2 = copy.deepcopy(wn)
    else:
        wn2 = wn
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = (pos[0]*scale, pos[1]*scale)
    for name, link in wn2.links():
        if link.vertices:
            for k in range(len(link.vertices)):
                vertex = link.vertices[k]
                link.vertices[k] = (vertex[0]*scale, vertex[1]*scale)

    return wn2


def translate_node_coordinates(wn, offset_x, offset_y, return_copy=True):
    """
    Translate node coordinates
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        Water network model
    offset_x: tuple
        Translation in the x direction, in meters
    offset_y: float
        Translation in the y direction, in meters
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    --------
    wntr WaterNetworkModel
        Water network model with updated node coordinates
    """
    if return_copy: # Get a copy of the WaterNetworkModel
        wn2 = copy.deepcopy(wn)
    else:
        wn2 = wn
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = (pos[0]+offset_x, pos[1]+offset_y)
    for name, link in wn2.links():
        if link.vertices:
            for k in range(len(link.vertices)):
                vertex = link.vertices[k]
                link.vertices[k] = (vertex[0]+offset_x, vertex[1]+offset_y)

    return wn2
        

def rotate_node_coordinates(wn, theta, return_copy=True):
    """
    Rotate node coordinates counter-clockwise by theta degrees
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        Water network model
    theta: float
        Node rotation, in degrees
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    --------
    wntr WaterNetworkModel
        Water network model with updated node coordinates
    """
    if return_copy: # Get a copy of the WaterNetworkModel
        wn2 = copy.deepcopy(wn)
    else:
        wn2 = wn
    
    theta = np.radians(theta)
    R = np.array([[np.cos(theta),-np.sin(theta)], 
                  [np.sin(theta), np.cos(theta)]])
    for name, node in wn2.nodes():
        pos = node.coordinates
        node.coordinates = tuple(np.dot(R,pos))
    for name, link in wn2.links():
        if link.vertices:
            for k in range(len(link.vertices)):
                link.vertices[k] = tuple(np.dot(R,link.vertices[k]))
    
    return wn2


def convert_node_coordinates_UTM_to_longlat(wn, zone_number, zone_letter, return_copy=True):
    """
    Convert node coordinates from UTM coordinates to longitude, latitude coordinates
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        Water network model
    zone_number: int
       Zone number
    zone_letter: string
        Zone letter
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    --------
    wntr WaterNetworkModel
        Water network model with updated node coordinates (longitude, latitude)
    """
    if utm is None:
        raise ImportError('utm package is required')
    
    if return_copy: # Get a copy of the WaterNetworkModel
        wn2 = copy.deepcopy(wn)
    else:
        wn2 = wn
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        lat, long = utm.to_latlon(pos[0], pos[1], zone_number, zone_letter)
        node.coordinates = (long, lat)

    for name, link in wn2.links():
        if link.vertices:
            for k in range(len(link.vertices)):
                vertex = link.vertices[k]
                lat, long = utm.to_latlon(vertex[0], vertex[1], zone_number, zone_letter)
                link.vertices[k] = (long, lat)

    return wn2


def convert_node_coordinates_longlat_to_UTM(wn, return_copy=True):
    """
    Convert node longitude, latitude coordinates to UTM coordinates
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        Water network model
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    --------
    wntr WaterNetworkModel
        Water network model with updated node coordinates (easting, northing)
    """
    if utm is None:
        raise ImportError('utm package is required')
    
    if return_copy: # Get a copy of the WaterNetworkModel
        wn2 = copy.deepcopy(wn)
    else:
        wn2 = wn
    
    for name, node in wn2.nodes():
        pos = node.coordinates
        longitude = pos[0]
        latitude = pos[1]
        utm_coords = utm.from_latlon(latitude, longitude)
        easting = utm_coords[0]
        northing = utm_coords[1]
        node.coordinates = (easting, northing)
    for name, link in wn2.links():
        if link.vertices:
            for k in range(len(link.vertices)):
                vertex = link.vertices[k]
                longitude = vertex[0]
                latitude = vertex[1]
                utm_coords = utm.from_latlon(latitude, longitude)
                easting = utm_coords[0]
                northing = utm_coords[1]
                link.vertices[k] = (easting, northing)

    return wn2


def convert_node_coordinates_to_UTM(wn, utm_map, return_copy=True):
    """
    Convert node coordinates to UTM coordinates
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        Water network model
    utm_map: dictionary
        Dictionary containing two node names and their x, y coordinates in 
        UTM easting, northing in the format
        {'node name 1': (easting, northing), 'node name 2': (easting, northing)}
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    --------
    wntr WaterNetworkModel
        Water network model with updated node coordinates (easting, northing)
    """
    
    wn2 = _convert_with_map(wn, utm_map, 'UTM', return_copy)
    
    return wn2


def convert_node_coordinates_to_longlat(wn, longlat_map, return_copy=True):
    """
    Convert node coordinates to longitude, latitude coordinates
    
    Parameters
    -----------
    wn: wntr WaterNetworkModel
        Water network model
    longlat_map: dictionary
        Dictionary containing two node names and their x, y coordinates in
        longitude, latitude in the format
        {'node name 1': (longitude, latitude), 'node name 2': (longitude, latitude)}
    return_copy: bool, optional
        If True, modify and return a copy of the WaterNetworkModel object.
        If False, modify and return the original WaterNetworkModel object.
        
    Returns
    --------
    wntr WaterNetworkModel
        Water network model with updated node coordinates (longitude, latitude)
    """
    
    wn2 = _convert_with_map(wn, longlat_map, 'LONGLAT', return_copy)
    
    return wn2


def _convert_with_map(wn, node_map, flag, return_copy):
    
    if utm is None:
        raise ImportError('utm package is required')
    
    if not len(node_map.keys()) == 2:
        raise Exception('map must have exactly 2 entries')
    
    if return_copy: # Get a copy of the WaterNetworkModel
        wn2 = copy.deepcopy(wn)
    else:
        wn2 = wn
    
    node_names = list(node_map.keys())
    
    A = []
    B = []
    for node_name, coords in node_map.items():
        A.append(np.array(wn2.get_node(node_name).coordinates))
        if flag == 'LONGLAT':
            longitude = coords[0]
            latitude = coords[1]
            utm_coords = utm.from_latlon(latitude, longitude)
            zone_number = utm_coords[2]
            zone_letter = utm_coords[3] 
            B.append(np.array(utm_coords[0:2])) # B is in UTM coords
        elif flag == 'UTM':
            easting = coords[0]
            northing = coords[1]
            B.append(np.array(easting, northing)) # B is in UTM coords
    
    # Rotate, if needed
    vect1 = A[1] - A[0]
    vect2 = B[1] - B[0]
    vect1_unit = vect1/np.linalg.norm(vect1)
    vect2_unit = vect2/np.linalg.norm(vect2)
    dotproduct = np.dot(vect1_unit, vect2_unit)
    if dotproduct < 1:
        sign = np.sign(np.cross(vect1_unit, vect2_unit))
        angle = np.arccos(dotproduct)*180/np.pi
        wn2 = rotate_node_coordinates(wn2, sign*angle)
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
        if flag == 'LONGLAT':
            lat, long = utm.to_latlon(easting, northing, zone_number, zone_letter)
            node.coordinates = (long, lat)
        elif flag == 'UTM':
            node.coordinates = (easting, northing)

    for name, link in wn2.links():
        if link.vertices:
            for k in range(len(link.vertices)):
                pos = link.vertices[k]
                (easting, northing) = (np.array(pos) - cpA)*ratio + cpB
                if flag == 'LONGLAT':
                    lat, long = utm.to_latlon(easting, northing, zone_number, zone_letter)
                    link.vertices[k] = (long, lat)
                elif flag == 'UTM':
                    node.coordinates = (easting, northing)
    
    return wn2