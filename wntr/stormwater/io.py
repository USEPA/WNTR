import logging
import pandas as pd
import networkx as nx
import pyswmm
import swmmio
from swmm.toolkit.shared_enum import NodeAttribute, LinkAttribute, \
                                     SubcatchAttribute, SystemAttribute

from wntr.sim import SimulationResults
from wntr.stormwater.gis import StormWaterNetworkGIS
import wntr.stormwater

logger = logging.getLogger(__name__)


def to_graph(swn):
    """
    Convert a StormWaterNetworkModel into a NetworkX graph
    
    Parameters
    ----------
    swn : StormWaterNetworkModel
        Storm water network model
        
    Returns
    -------
    NetworkX graph
    
    """
    G = swn._swmmio_model.network
    geom = nx.get_node_attributes(G, 'geometry')
    pos = dict([(k,v['coordinates']) for k,v in geom.items()])
    nx.set_node_attributes(G, pos, 'pos')
    return G


def to_gis(swn, crs=None):
    """
    Convert a StormWaterNetworkModel into GeoDataFrames
    
    Parameters
    ----------
    swn : WaterNetworkModel
        Water network model
    crs : str, optional
        Coordinate reference system, by default None

    Returns
    -------
    StormWaterNetworkGIS object that contains GeoDataFrames
        
    """
    gis_data = StormWaterNetworkGIS()
    gis_data._create_gis(swn, crs)
    return gis_data


def write_inpfile(swn, filename):
    """
    Write the StormWaterNetworkModel to an EPANET INP file
    
    Parameters
    ----------
    swn : WaterNetworkModel
        Water network model
    filename : string
       Name of the inp file
    """
    swn._swmmio_model.inp.save(filename)

def read_inpfile(filename):
    """
    Create a StormWaterNetworkModel from an SWMM INP file
    
    Parameters
    ----------
    filename : string
       Name of the inp file
       
    Returns
    -------
    StormWaterNetworkModel
    """
    swn = wntr.stormwater.network.StormWaterNetworkModel(filename)

    return swn


def read_outfile(filename):
    """
    Read a SWMM binary output file

    Parameters
    ----------
    filename : string
       Name of the SWMM binary output file
    
    Returns
    -------
    SimulationResults
    """
    results = SimulationResults()
    
    # Node results = INVERT_DEPTH, HYDRAULIC_HEAD, PONDED_VOLUME, 
    # LATERAL_INFLOW, TOTAL_INFLOW, FLOODING_LOSSES, POLLUT_CONC_0
    results.node = {}
    
    # Link results = FLOW_RATE, FLOW_DEPTH, FLOW_VELOCITY, FLOW_VOLUME, 
    # CAPACITY, POLLUT_CONC_0
    results.link = {}
    
    # Subcatchment results = RAINFALL, SNOW_DEPTH, EVAP_LOSS, INFIL_LOSS, 
    # RUNOFF_RATE, GW_OUTFLOW_RATE, GW_TABLE_ELEV, SOIL_MOISTURE, 
    # POLLUT_CONC_0
    results.subcatch = {}
    
    # System results = AIR_TEMP, RAINFALL, SNOW_DEPTH, EVAP_INFIL_LOSS, 
    # RUNOFF_FLOW, DRY_WEATHER_INFLOW, GW_INFLOW, RDII_INFLOW, DIRECT_INFLOW,
    # TOTAL_LATERAL_INFLOW, FLOOD_LOSSES, OUTFALL_FLOWS, VOLUME_STORED, 
    # EVAP_RATE
    results.system = {}
    
    with pyswmm.Output(filename) as out:
        times = out.times
        
        for attribute in NodeAttribute:
            temp = {}
            for node_name in out.nodes.keys():
                ts = out.node_series(node_name, attribute)
                temp[node_name] = ts.values()
            results.node[attribute.name] = pd.DataFrame(data=temp, index=times)
        
        for attribute in LinkAttribute:
            temp = {}
            for link_name in out.links.keys():
                ts = out.link_series(link_name, attribute)
                temp[link_name] = ts.values()
            results.link[attribute.name] = pd.DataFrame(data=temp, index=times)
            
        for attribute in SubcatchAttribute:
            temp = {}
            for subcatch_name in out.subcatchments.keys():
                ts = out.subcatch_series(subcatch_name, attribute)
                temp[subcatch_name] = ts.values()
            results.subcatch[attribute.name] = pd.DataFrame(data=temp, index=times)
        
        for attribute in SystemAttribute:
            ts = out.system_series(attribute)
            temp[attribute] = ts.values()
        results.system = pd.DataFrame(data=temp, index=times)
        
    return results

def write_geojson(swn, prefix: str, crs=None):
    """
    Write the StormWaterNetworkModel to a set of GeoJSON files, one file for each
    network element.

    Parameters
    ----------
    swn : wntr StormWaterNetworkModel
        Storm water network model
    prefix : str
        File prefix
    crs : str, optional
        Coordinate reference system, by default None
    """

    swn_gis = swn.to_gis(crs)
    swn_gis.write_geojson(prefix=prefix)
