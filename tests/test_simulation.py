import csv
import json
from importlib.resources import files
from pathlib import Path

import numpy as np
import pytest

import wntr
from ward import simulation
from ward.simulation import (
    load_ctown,
    load_test_network,
    run_pump_attack,
    run_simulation,
)
from wntr.epanet.exceptions import ENSyntaxError


@pytest.mark.simulation
def test_paired_runs_match_when_run_order_is_reversed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    network_path = files("wntr.library").joinpath("networks", "Net1.inp")
    scenario = {
        "schema_version": "1.0",
        "scenario_id": "paired-run",
        "name": "Paired run test",
        "attack_type": "pump_off",
        "model_id": "net1",
        "target_components": ["9"],
        "timing": {"start_time_sec": 3600, "duration_sec": 3600},
        "parameters": {},
    }
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    forward = simulation.run_paired_simulations(scenario_path, network_path)
    reverse = simulation.run_paired_simulations(
        scenario_path, network_path, attack_first=True
    )

    assert forward["baseline"]["settings"] == forward["attack"]["settings"]
    assert forward["baseline"]["simulator"] == "WNTRSimulator"
    assert forward["baseline"]["wntr_version"] == wntr.__version__
    assert list(tmp_path.iterdir()) == [scenario_path]
    assert forward["baseline"]["link"]["status"].loc[7200, "9"] == 1
    assert forward["attack"]["link"]["status"].loc[7200, "9"] == 0
    for case in ("baseline", "attack"):
        assert forward[case]["converged"]
        assert forward[case]["failure"] is None
        for component in ("node", "link"):
            for metric, frame in forward[case][component].items():
                np.testing.assert_allclose(
                    frame, reverse[case][component][metric], rtol=0, atol=1e-12
                )

    run_pump_attack(scenario_path, network_path)
    with (tmp_path / "paired-run_results.csv").open(newline="") as output:
        rows = list(csv.DictReader(output))

    assert list(rows[0]) == [
        "time_sec",
        *[f"node_pressure_{name}" for name in forward["attack"]["node"]["pressure"]],
        *[f"link_flowrate_{name}" for name in forward["attack"]["link"]["flowrate"]],
    ]
    assert [int(row["time_sec"]) for row in rows] == list(
        forward["attack"]["node"]["pressure"].index
    )
    np.testing.assert_allclose(
        [float(row["link_flowrate_9"]) for row in rows],
        forward["attack"]["link"]["flowrate"]["9"],
        rtol=0,
        atol=1e-12,
    )


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


@pytest.mark.simulation
def test_pump_attack_closes_pump_during_scenario_window(tmp_path):
    scenario = {
        "schema_version": "1.0",
        "scenario_id": "pump-window-test",
        "name": "Pump outage timing test",
        "attack_type": "pump_off",
        "model_id": "net1",
        "target_components": ["9"],
        "timing": {"start_time_sec": 3600, "duration_sec": 3600},
        "parameters": {},
    }
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
    network_path = files("wntr.library").joinpath("networks", "Net1.inp")

    results = run_pump_attack(
        scenario_path=scenario_path,
        network_path=network_path,
        output_path=tmp_path / "results.csv",
    )

    pump_status = results.link["status"]["9"]
    # WNTR evaluates SimTimeCondition boundaries at hydraulic timesteps.
    # The pump is open at the start boundary, closed during the outage, and
    # reopened at the first timestep after its end boundary.
    assert pump_status.loc[3600] == 1
    assert pump_status.loc[7200] == 0
    assert pump_status.loc[10800] == 1
    assert (tmp_path / "results.csv").is_file()


@pytest.mark.simulation
def test_ctown_controls_cannot_reopen_pump_during_outage(tmp_path):
    network_path = Path(__file__).resolve().parents[1] / "examples/networks/CTOWN.inp"
    results = run_pump_attack(
        network_path=network_path,
        output_path=tmp_path / "results.csv",
    )

    pump_flow = results.link["flowrate"]["PU1"]
    assert pump_flow.loc[3600] > 0
    assert (pump_flow.loc[4500:10800] == 0).all()
    assert pump_flow.loc[11700] > 0


@pytest.mark.parametrize("target", ["missing-pump", "10"])
def test_pump_attack_rejects_invalid_target(tmp_path, target):
    scenario = {
        "schema_version": "1.0",
        "scenario_id": "invalid-target",
        "name": "Invalid pump target",
        "attack_type": "pump_off",
        "model_id": "net1",
        "target_components": [target],
        "timing": {"start_time_sec": 3600, "duration_sec": 3600},
        "parameters": {},
    }
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
    network_path = files("wntr.library").joinpath("networks", "Net1.inp")

    with pytest.raises(ValueError, match=f"Target '{target}' is not a pump"):
        run_pump_attack(
            scenario_path=scenario_path,
            network_path=network_path,
            output_path=tmp_path / "results.csv",
        )

    paired = simulation.run_paired_simulations(scenario_path, network_path)
    assert paired["baseline"]["converged"]
    assert not paired["attack"]["converged"]
    assert paired["attack"]["failure"] == {
        "type": "ValueError",
        "message": f"Target '{target}' is not a pump in the selected network",
    }


@pytest.mark.simulation
def test_pump_attack_changes_pressure_vs_normal_run(tmp_path):
    scenario = {
        "schema_version": "1.0",
        "scenario_id": "pump-pressure-test",
        "name": "Pump outage pressure test",
        "attack_type": "pump_off",
        "model_id": "net1",
        "target_components": ["9"],
        "timing": {"start_time_sec": 3600, "duration_sec": 3600},
        "parameters": {},
    }
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
    network_path = files("wntr.library").joinpath("networks", "Net1.inp")

    # Run the same network without an outage to get the normal pressure series.
    baseline_network = wntr.network.WaterNetworkModel(str(network_path))
    baseline_results = wntr.sim.WNTRSimulator(baseline_network).run_sim()

    # The attack function loads a fresh copy of the same network and applies
    # only the pump outage described in the scenario JSON.
    attack_results = run_pump_attack(
        scenario_path=scenario_path,
        network_path=network_path,
        output_path=tmp_path / "attack_results.csv",
    )

    baseline_pressure = baseline_results.node["pressure"]
    attack_pressure = attack_results.node["pressure"]
    common_times = baseline_pressure.index.intersection(attack_pressure.index)
    pressure_difference = (
        attack_pressure.loc[common_times] - baseline_pressure.loc[common_times]
    ).loc[3600:7200]

    # A 1 mm head difference filters out negligible floating-point noise.
    assert (pressure_difference.abs() > 0.001).to_numpy().any()


@pytest.mark.simulation
def test_pump_attack_results_are_identical_across_three_runs(
    tmp_path,
):  # tests repeatability of simulation results up to 1e-12 tolerance, slight differences will exist beyond this
    scenario = {
        "schema_version": "1.0",
        "scenario_id": "pump-repeatability-test",
        "name": "Repeatable pump outage test",
        "attack_type": "pump_off",
        "model_id": "net1",
        "target_components": ["9"],
        "timing": {"start_time_sec": 3600, "duration_sec": 3600},
        "parameters": {},
    }
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
    network_path = files("wntr.library").joinpath("networks", "Net1.inp")

    results = [
        run_pump_attack(
            scenario_path=scenario_path,
            network_path=network_path,
            output_path=tmp_path / f"run_{run_number}.csv",
        )
        for run_number in range(3)
    ]

    first_result = results[0]
    for result in results[1:]:
        assert result.node.keys() == first_result.node.keys()
        assert result.link.keys() == first_result.link.keys()
        for metric, first_frame in first_result.node.items():
            np.testing.assert_allclose(
                first_frame.to_numpy(),
                result.node[metric].to_numpy(),
                rtol=0,
                atol=1e-12,
            )
        for metric, first_frame in first_result.link.items():
            np.testing.assert_allclose(
                first_frame.to_numpy(),
                result.link[metric].to_numpy(),
                rtol=0,
                atol=1e-12,
            )
