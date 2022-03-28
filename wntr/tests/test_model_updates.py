from os.path import abspath, dirname, join

import pytest
import wntr
import numpy as np
import geopandas as gpd
from wntr.utils.constants import *
import pyproj
import matplotlib.pyplot as plt

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
    assert wn.get_node('121').base_demand == pytest.approx(41.63 * 5 / CMS_TO_GPM, abs=1e-5)

def test_create_model_gis():
    inp_file = join(ex_datadir, 'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file)
    pz_file = join(ex_datadir, 'PressureZone.shp')
    wn.create_model_gis(gis_path=pz_file)

    assert wn.get_node('225').pressure_zone == 'PZ1'
    assert wn.get_node('15').pressure_zone is None