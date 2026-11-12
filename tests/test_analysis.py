import json
from pathlib import Path

import pandas as pd
import pytest

from ward.analysis import (
    PSI_TO_METERS,
    ImpactThresholds,
    identify_affected_nodes,
    meters_to_psi,
)
from ward.scenario import ScenarioTiming, WaterScenario
from ward.simulation import run_paired_simulations


def _make_paired_fixture(
    baseline_psi: dict[str, list[float]],
    attack_psi: dict[str, list[float]],
    baseline_demand: dict[str, list[float]] | None = None,
    attack_demand: dict[str, list[float]] | None = None,
    times_sec: list[float] | None = None,
) -> dict:
    if times_sec is None:
        times_sec = [3600.0, 7200.0, 10800.0]

    base_p_m = pd.DataFrame(
        {k: [v * PSI_TO_METERS for v in vals] for k, vals in baseline_psi.items()},
        index=times_sec,
    )
    atk_p_m = pd.DataFrame(
        {k: [v * PSI_TO_METERS for v in vals] for k, vals in attack_psi.items()},
        index=times_sec,
    )

    base_node = {"pressure": base_p_m}
    atk_node = {"pressure": atk_p_m}

    if baseline_demand is not None and attack_demand is not None:
        base_node["demand"] = pd.DataFrame(baseline_demand, index=times_sec)
        atk_node["demand"] = pd.DataFrame(attack_demand, index=times_sec)

    return {
        "baseline": {"converged": True, "node": base_node},
        "attack": {"converged": True, "node": atk_node},
    }


def test_hand_checked_thresholds_below_at_and_above():
    """Verify hand-calculated values below, strictly at, and above each threshold."""

    paired = _make_paired_fixture(
        baseline_psi={
            "N_below": [30.0, 30.0, 30.0],
            "N_at": [24.9, 24.9, 24.9],
            "N_above": [25.0, 25.0, 25.0],
            "N_drop_exact": [30.0, 30.0, 30.0],
            "N_pre_unchanged": [18.0, 18.0, 18.0],
            "N_pre_worsened": [18.0, 18.0, 18.0],
        },
        attack_psi={
            "N_below": [30.0, 19.9, 19.9],
            "N_at": [24.9, 20.0, 20.0],
            "N_above": [25.0, 20.1, 20.1],
            "N_drop_exact": [30.0, 25.0, 30.0],
            "N_pre_unchanged": [18.0, 17.5, 17.5],
            "N_pre_worsened": [18.0, 12.0, 12.0],
        },
    )

    scenario = WaterScenario(
        scenario_id="hand_check_01",
        name="Hand Check",
        attack_type="pump_off",
        model_id="synthetic",
        target_components=["P1"],
        timing=ScenarioTiming(start_time_sec=3600.0, duration_sec=7200.0),
        parameters={},
    )

    report = identify_affected_nodes(
        paired,
        scenario=scenario,
        thresholds=ImpactThresholds(min_pressure_psi=20.0, pressure_drop_psi=5.0),
    )

    # this is to make sure json works for teh fastAPI /dashboard
    serialized = json.dumps(report)
    assert '"affected_nodes"' in serialized

    affected_ids = [node["node_id"] for node in report["affected_nodes"]]
    assert affected_ids == ["N_below", "N_pre_worsened", "N_drop_exact"]

    n_below = report["affected_nodes"][0]
    assert n_below["rank"] == 1
    assert n_below["max_pressure_drop_psi"] == pytest.approx(10.1, abs=1e-3)
    assert n_below["attack_min_pressure_psi"] == pytest.approx(19.9, abs=1e-3)
    assert n_below["duration_hours"] == pytest.approx(2.0, abs=1e-3)
    assert n_below["impact_category"] == "attack_induced_low_pressure"
    assert n_below["pre_existing_low_pressure"] is False

    n_worsened = report["affected_nodes"][1]
    assert n_worsened["rank"] == 2
    assert n_worsened["max_pressure_drop_psi"] == pytest.approx(6.0, abs=1e-3)
    assert n_worsened["impact_category"] == "worsened_pre_existing_low_pressure"
    assert n_worsened["pre_existing_low_pressure"] is True

    n_drop = report["affected_nodes"][2]
    assert n_drop["rank"] == 3
    assert n_drop["max_pressure_drop_psi"] == pytest.approx(5.0, abs=1e-3)
    assert n_drop["duration_hours"] == pytest.approx(1.0, abs=1e-3)
    assert n_drop["impact_category"] == "attack_induced_degradation"

    pre_only_ids = [node["node_id"] for node in report["pre_existing_only_nodes"]]
    assert pre_only_ids == ["N_pre_unchanged"]


def test_equal_ranking_tie_breaking_is_deterministic():
    """Verify tie-breaking order: drop desc -> duration desc -> min pressure asc -> node_id asc."""
    paired = _make_paired_fixture(
        baseline_psi={
            "J_B": [30.0, 30.0, 30.0],
            "J_A": [30.0, 30.0, 30.0],
            "J_LONGER": [30.0, 30.0, 30.0],
        },
        attack_psi={
            "J_B": [30.0, 18.0, 30.0],  # 1hr
            "J_A": [30.0, 18.0, 30.0],  # 1hr
            "J_LONGER": [30.0, 18.0, 18.0],  # 2hrs
        },
    )

    report = identify_affected_nodes(
        paired, start_time_sec=3600.0, end_time_sec=10800.0
    )
    ranked_ids = [n["node_id"] for n in report["affected_nodes"]]
    assert ranked_ids == ["J_LONGER", "J_A", "J_B"]
    assert [n["rank"] for n in report["affected_nodes"]] == [1, 2, 3]


def test_demand_shortfall_flags_affected_node_even_above_20_psi():
    """Verify water-service delivery ratio below threshold flags a node."""
    paired = _make_paired_fixture(
        baseline_psi={"J1": [40.0, 40.0, 40.0]},
        attack_psi={"J1": [40.0, 38.0, 38.0]},  # Only 2.0 psi drop n well above 20 psi
        baseline_demand={"J1": [0.01, 0.01, 0.01]},
        attack_demand={"J1": [0.01, 0.008, 0.01]},  # 80% delivery (< 95% threshold)
    )

    report = identify_affected_nodes(
        paired, start_time_sec=3600.0, end_time_sec=10800.0
    )
    assert len(report["affected_nodes"]) == 1
    assert report["affected_nodes"][0]["node_id"] == "J1"
    assert report["affected_nodes"][0]["min_demand_delivery_ratio"] == pytest.approx(
        0.8
    )


def test_unit_conversion_20_psi_constant():
    assert meters_to_psi(20.0 * PSI_TO_METERS) == pytest.approx(20.0, abs=1e-9)
    assert 20.0 * PSI_TO_METERS == pytest.approx(14.06139, abs=1e-4)


def test_ctown_pump_demo_affected_nodes_integration():
    """Run bundled pump_poweroff_basic.json on C-Town and verify structured report."""
    ctown_path = (
        Path(__file__).resolve().parent.parent / "examples" / "networks" / "CTOWN.inp"
    )
    if not ctown_path.is_file():
        pytest.skip("CTOWN.inp not present in examples/networks")

    scenario_path = (
        Path(__file__).resolve().parent.parent
        / "ward"
        / "scenarios"
        / "pump_poweroff_basic.json"
    )
    scenario = WaterScenario.load_from_json(scenario_path)
    paired = run_paired_simulations(scenario_path, ctown_path)
    report = identify_affected_nodes(paired, scenario=scenario)

    assert report["scenario_id"] == "scenario_pump_01"
    assert report["thresholds"]["min_pressure_psi"] == 20.0
    assert report["thresholds"]["provisional_awaiting_sponsor_confirmation"] is True
    assert json.loads(json.dumps(report))["summary"]["total_evaluated_nodes"] > 0
