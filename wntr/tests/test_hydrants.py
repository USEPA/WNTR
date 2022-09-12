from multiprocessing import freeze_support
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

def test_create_model_hydrant_gis():
    inp_file = join(ex_datadir, 'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file, crs='epsg:4326')

    hydrants_gis = gpd.read_file(join(ex_datadir, 'Net3_hydrants.shp'))
    branch_line_gis = gpd.read_file(join(ex_datadir, 'Net3_hydrant_branch_lines.shp'))

    wn.parse_hydrants_from_gis(hydrants_gis, branch_line_gis, parallel=False)

    assert wn.hydrants_parser.hyd_juncs_gis.loc['hydrant3'].pipe_id == '131'
    assert wn.hydrants_parser.hyd_juncs_gis.loc['hydrant1'].pipe_id == '131'
    assert wn.hydrants_parser.hyd_juncs_gis.loc['hydrant2'].pipe_id == '163'

def test_add_hydrant_to_model():
    inp_file = join(ex_datadir, 'Net3.inp')
    wn = wntr.network.WaterNetworkModel(inp_file, crs='epsg:4326')

    wn.parse_hydrants_from_gis(gpd.read_file(join(ex_datadir, 'Net3_hydrants.shp')),
            gpd.read_file(join(ex_datadir, 'Net3_hydrant_branch_lines.shp')), parallel=False)

    wn.add_hydrant_to_pipe('hydrant2')
    
    assert '163_2' in wn.link_name_list
    assert 'branchline3' in wn.link_name_list
    assert 'hydrant2' in wn.node_name_list
    assert wn.get_node('hydrant2').elevation == pytest.approx(19.67, 1e-3)

if __name__ == '__main__':
    freeze_support()
    test_add_hydrant_to_model()