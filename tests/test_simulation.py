import numpy as np
import pytest

from ward.simulation import load_ctown, load_test_network, run_simulation
from wntr.epanet.exceptions import ENSyntaxError


@pytest.mark.simulation
def test_short_simulation_returns_pressures_and_flows(tmp_path):
    network = load_test_network()
    network.options.time.duration = 3600
    network.options.time.report_timestep = 3600

    results = run_simulation(network, tmp_path / "net1")

    pressure = results.node["pressure"]
    flow = results.link["flowrate"]
    assert results.error_code is None
    assert pressure.index.tolist() == [0, 3600]
    assert flow.index.tolist() == [0, 3600]
    assert pressure.shape == (2, 11)
    assert flow.shape == (2, 13)
    assert np.isfinite(pressure.to_numpy()).all()
    assert np.isfinite(flow.to_numpy()).all()


def test_load_ctown():
    network = load_ctown()

    assert network.options.time.duration == 86400
    assert network.num_nodes == 396
    assert network.num_links == 444
    assert network.num_junctions == 388
    assert network.num_pipes == 429
    assert network.num_pumps == 11
    assert network.num_valves == 4
    assert network.num_tanks == 7
    assert network.num_reservoirs == 1


def test_load_ctown_missing_file(tmp_path):
    missing_file = tmp_path / "missing.inp"

    with pytest.raises(FileNotFoundError):
        load_ctown(missing_file)


def test_load_ctown_malformed_file(tmp_path):
    malformed_file = tmp_path / "malformed.inp"
    malformed_file.write_text("This is not a valid EPANET network file")

    with pytest.raises(ENSyntaxError):
        load_ctown(malformed_file)
