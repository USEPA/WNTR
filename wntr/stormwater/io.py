import logging
import pandas as pd
import pyswmm
import swmmio
from swmm.toolkit.shared_enum import NodeAttribute, LinkAttribute, \
                                     SubcatchAttribute, SystemAttribute

from wntr.sim import SimulationResults
from wntr.gis import WaterNetworkGIS

logger = logging.getLogger(__name__)


def to_graph(swn):

    G = swn._swmmio_model.network

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
    WaterNetworkGIS object that contains GeoDataFrames
        
    """
    gis_data = WaterNetworkGIS()
    
    # nodes
    gis_data.junctions = swn.nodes.loc[swn.junction_name_list,:]
    gis_data.outfalls = swn.nodes.loc[swn.outfall_name_list,:]
    gis_data.storages = swn.nodes.loc[swn.storage_name_list,:]
    
    # links
    gis_data.conduits = swn.links.loc[swn.conduit_name_list,:]
    gis_data.weirs = swn.links.loc[swn.weir_name_list,:]
    gis_data.orifices = swn.links.loc[swn.orifice_name_list,:]
    gis_data.pumps = swn.links.loc[swn.pump_name_list,:]
    
    # subcatchments
    gis_data.subcatchments = swn.subcatchments.loc[swn.subcatchment_name_list,:]

    return gis_data


def write_inpfile(swn, filename):

    swn._swmmio_model.inp.save(filename)


def read_inpfile(filename):

    model = swmmio.Model(filename)

    return model


def read_outfile(outfile):

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
    
    with pyswmm.Output(outfile) as out:
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