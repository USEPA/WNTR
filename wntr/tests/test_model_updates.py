from os.path import abspath, dirname, join
import wntr
import numpy as np
import geopandas as gpd

testdir = dirname(abspath(str(__file__)))
test_network_dir = join(testdir, "networks_for_testing")
test_data_dir = join(testdir, "data_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

def test_update_base_demands_dict():
    inp_file = 'Net3.inp'
    wn = wntr.network.WaterNetworkModel(inp_file)

    wn.update_base_demands_dict(new_demands_junctions={'10': 1.5, '15': 2.0})
    assert wn.get_node('10').base_demand == 1.5
    assert wn.get_node('15').base_demand == 2.

    wn.update_base_demands_dict(all_junctions_demand_mult=5.)
    assert wn.get_node('10').base_demand == 0.
    assert wn.get_node('121').base_demand == 41.63 * 5.