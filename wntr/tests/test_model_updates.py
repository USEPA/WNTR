from os.path import abspath, dirname, join

import pytest
import wntr
import numpy as np
import geopandas as gpd
from wntr.utils.constants import *
import pyproj

testdir = dirname(abspath(str(__file__)))
test_network_dir = join(testdir, "networks_for_testing")
test_data_dir = join(testdir, "data_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

def test_update_base_demands_dict():
    inp_file = join(ex_datadir, 'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)

    wn.update_base_demands_dict(new_demands_junctions={'10': 1.5, '15': 2.0})
    assert wn.get_node('10').base_demand == pytest.approx(1.5 / CMS_TO_GPM, abs=1e-5)
    assert wn.get_node('15').base_demand == pytest.approx(2. / CMS_TO_GPM, abs=1e-5)

    wn = wntr.network.WaterNetworkModel(inp_file)
    wn.update_base_demands_dict(all_junctions_demand_mult=5.)
    assert wn.get_node('10').base_demand == 0.
    assert wn.options.hydraulic.demand_multiplier == 5.

def test_create_model_gis():
    inp_file = join(ex_datadir, 'Net3.inp')
    pz_file = gpd.read_file(join(ex_datadir, 'PressureZone.shp'))
    wn = wntr.network.WaterNetworkModel(inp_file, pressure_zone_layer=pz_file)

    assert wn.get_node('225').pressure_zone == 'PZ1'
    assert wn.get_node('15').pressure_zone is None
    assert len(wn.nodes_gis) == len(wn.node_name_list)

def test_assign_elevation():
    inp_file = join(ex_datadir, 'Net4.inp')
    wn = wntr.network.WaterNetworkModel(inp_file, crs='epsg:2272')

    assert wn.get_node('4143').elevation == pytest.approx(147.64242799420802, 0.5) # 484.39 ft
    assert wn.get_node('6268').elevation == pytest.approx(153.64996275076803, 0.5) # 504.10 ft
    assert wn.get_node('23109').elevation == pytest.approx(155.71240423116, 0.5) # 510.86 ft
    