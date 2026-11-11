"""Tests for batch hydraulic design verification."""

from __future__ import annotations

import pandas as pd

import pytest
import wntr
import wntr.extensions.design_verification.batch as batch_module

from wntr.extensions.design_verification import (
    HydraulicScenario,
    PipeDesign,
    run_verification_batch,
)


pytestmark = pytest.mark.extensions


def build_small_network():
    """Build a small network suitable for fast batch tests."""
    wn = wntr.network.WaterNetworkModel()

    wn.add_reservoir(
        "R1",
        base_head=50.0,
        coordinates=(0.0, 0.0),
    )

    wn.add_junction(
        "J1",
        base_demand=0.01,
        demand_pattern=None,
        elevation=10.0,
        coordinates=(100.0, 0.0),
    )

    wn.add_pipe(
        "P1",
        start_node_name="R1",
        end_node_name="J1",
        length=100.0,
        diameter=0.150,
        roughness=100.0,
        minor_loss=0.0,
    )

    return wn


def build_scenarios():
    """Return two small hydraulic scenarios."""
    baseline_options = wntr.network.Options()
    baseline_options.time.duration = 0
    baseline_options.time.hydraulic_timestep = 3600
    baseline_options.time.report_timestep = 3600
    baseline_options.hydraulic.demand_multiplier = 1.0
    baseline_options.hydraulic.demand_model = "DD"

    higher_demand_options = wntr.network.Options()
    higher_demand_options.time.duration = 0
    higher_demand_options.time.hydraulic_timestep = 3600
    higher_demand_options.time.report_timestep = 3600
    higher_demand_options.hydraulic.demand_multiplier = 1.2
    higher_demand_options.hydraulic.demand_model = "DD"

    return [
        HydraulicScenario(
            name="Baseline",
            options=baseline_options,
        ),
        HydraulicScenario(
            name="Higher demand",
            options=higher_demand_options,
        ),
    ]


def test_batch_returns_every_requested_combination():
    """Confirm that every design-scenario combination is assessed."""
    wn = build_small_network()

    designs = [
        None,
        PipeDesign(
            name="Larger pipe",
            diameters_m={"P1": 0.200},
        ),
    ]

    summary, records = run_verification_batch(
        wn=wn,
        scenarios=build_scenarios(),
        designs=designs,
        simulators=["WNTRSimulator"],
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
        pressure_tolerance_m=1.0e-6,
        velocity_tolerance_mps=1.0e-8,
    )

    assert len(summary) == 4
    assert summary["experiment_id"].is_unique
    assert set(summary["status"]) == {"completed"}
    assert set(summary["scenario_name"]) == {
        "Baseline",
        "Higher demand",
    }
    assert summary["design_name"].isna().any()
    assert "Larger pipe" in set(
        summary["design_name"].dropna()
    )
    assert set(summary["overall_feasible"]) == {True}
    assert summary[
        "pressure_tolerance_m"
    ].tolist() == pytest.approx(
        [1.0e-6] * 4
    )
    assert summary[
        "velocity_tolerance_mps"
    ].tolist() == pytest.approx(
        [1.0e-8] * 4
    )
    assert set(records) == set(summary["experiment_id"])


def test_batch_preserves_original_network():
    """Confirm that batch assessment does not modify the input model."""
    wn = build_small_network()
    original_diameter = wn.get_link("P1").diameter

    run_verification_batch(
        wn=wn,
        scenarios=build_scenarios(),
        designs=[
            PipeDesign(
                name="Larger pipe",
                diameters_m={"P1": 0.200},
            )
        ],
        simulators="WNTRSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
    )

    assert wn.get_link("P1").diameter == pytest.approx(
        original_diameter
    )


def test_batch_records_failure_and_continues():
    """Confirm that one failed experiment does not stop the batch."""
    wn = build_small_network()

    summary, records = run_verification_batch(
        wn=wn,
        scenarios=[build_scenarios()[0]],
        simulators=["WNTRSimulator", "unsupported"],
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
        continue_on_error=True,
    )

    assert len(summary) == 2
    assert set(summary["status"]) == {
        "completed",
        "failed",
    }

    failed_row = summary.loc[
        summary["status"] == "failed"
    ].iloc[0]

    assert failed_row["error_type"] == "AssertionError"

    failed_record = records[
        failed_row["experiment_id"]
    ]

    assert failed_record["verification"] is None
    assert failed_record["error"]["type"] == "AssertionError"




def test_network_hash_is_stable_for_equivalent_networks():
    """Equivalent independently built networks have the same hash."""
    wn_one = build_small_network()
    wn_two = build_small_network()

    assert (
        batch_module._network_hash(wn_one)
        == batch_module._network_hash(wn_two)
    )


def test_network_hash_changes_with_network_configuration():
    """A network-property change produces a different fingerprint."""
    wn_one = build_small_network()
    wn_two = build_small_network()

    wn_two.get_link("P1").diameter = 0.200

    assert (
        batch_module._network_hash(wn_one)
        != batch_module._network_hash(wn_two)
    )


def test_batch_configuration_hash_includes_network_hash():
    """Different networks produce different batch configuration hashes."""
    wn_one = build_small_network()
    wn_two = build_small_network()

    wn_two.get_link("P1").diameter = 0.200

    summary_one, _ = run_verification_batch(
        wn=wn_one,
        scenarios=[build_scenarios()[0]],
        simulators="WNTRSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
    )

    summary_two, _ = run_verification_batch(
        wn=wn_two,
        scenarios=[build_scenarios()[0]],
        simulators="WNTRSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
    )

    row_one = summary_one.iloc[0]
    row_two = summary_two.iloc[0]

    assert row_one["network_hash"] != row_two["network_hash"]
    assert (
        row_one["configuration_hash"]
        != row_two["configuration_hash"]
    )





def test_batch_configuration_hash_includes_tolerances():
    """Different tolerances produce different configuration hashes."""
    wn = build_small_network()
    scenario = build_scenarios()[0]

    strict_summary, _ = run_verification_batch(
        wn=wn,
        scenarios=[scenario],
        simulators="WNTRSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
        pressure_tolerance_m=0.0,
        velocity_tolerance_mps=0.0,
    )

    tolerant_summary, _ = run_verification_batch(
        wn=wn,
        scenarios=[scenario],
        simulators="WNTRSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
        pressure_tolerance_m=1.0e-6,
        velocity_tolerance_mps=1.0e-8,
    )

    strict_row = strict_summary.iloc[0]
    tolerant_row = tolerant_summary.iloc[0]

    assert (
        strict_row["network_hash"]
        == tolerant_row["network_hash"]
    )
    assert (
        strict_row["configuration_hash"]
        != tolerant_row["configuration_hash"]
    )
    assert strict_row[
        "pressure_tolerance_m"
    ] == pytest.approx(0.0)
    assert strict_row[
        "velocity_tolerance_mps"
    ] == pytest.approx(0.0)
    assert tolerant_row[
        "pressure_tolerance_m"
    ] == pytest.approx(1.0e-6)
    assert tolerant_row[
        "velocity_tolerance_mps"
    ] == pytest.approx(1.0e-8)



def test_batch_records_network_hash_failure_and_continues(
    monkeypatch,
):
    """Record a network-hash failure and continue the batch."""
    wn = build_small_network()

    original_network_hash = batch_module._network_hash
    call_count = 0

    def fail_first_network_hash(network):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            raise RuntimeError(
                "network hash failed"
            )

        return original_network_hash(network)

    monkeypatch.setattr(
        batch_module,
        "_network_hash",
        fail_first_network_hash,
    )

    summary, records = run_verification_batch(
        wn=wn,
        scenarios=build_scenarios(),
        simulators="WNTRSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
        continue_on_error=True,
    )

    assert len(summary) == 2
    assert list(summary["status"]) == [
        "failed",
        "completed",
    ]

    failed_row = summary.iloc[0]

    assert (
        failed_row["experiment_id"]
        == "dv-00001-unavailable"
    )
    assert failed_row["network_hash"] == "unavailable"
    assert (
        failed_row["configuration_hash"]
        == "unavailable"
    )
    assert failed_row["error_type"] == "RuntimeError"
    assert (
        failed_row["error_message"]
        == "network hash failed"
    )

    failed_record = records[
        failed_row["experiment_id"]
    ]

    assert failed_record["verification"] is None
    assert failed_record["audit"] is None
    assert (
        failed_record["error"]["type"]
        == "RuntimeError"
    )

    completed_row = summary.iloc[1]

    assert completed_row["status"] == "completed"
    assert (
        completed_row["network_hash"]
        != "unavailable"
    )
    assert (
        completed_row["configuration_hash"]
        != "unavailable"
    )
    assert completed_row["experiment_id"].startswith(
        "dv-00002-"
    )



def test_batch_records_hash_failure_and_continues(
    monkeypatch,
):
    """Record a hash failure and continue with the next experiment."""
    wn = build_small_network()

    original_configuration_hash = (
        batch_module._configuration_hash
    )
    call_count = 0

    def fail_first_configuration_hash(**kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            raise RuntimeError(
                "configuration hash failed"
            )

        return original_configuration_hash(**kwargs)

    monkeypatch.setattr(
        batch_module,
        "_configuration_hash",
        fail_first_configuration_hash,
    )

    summary, records = run_verification_batch(
        wn=wn,
        scenarios=build_scenarios(),
        simulators="WNTRSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
        continue_on_error=True,
    )

    assert len(summary) == 2
    assert list(summary["status"]) == [
        "failed",
        "completed",
    ]

    failed_row = summary.iloc[0]

    assert (
        failed_row["experiment_id"]
        == "dv-00001-unavailable"
    )
    assert (
        failed_row["configuration_hash"]
        == "unavailable"
    )
    assert failed_row["error_type"] == "RuntimeError"
    assert (
        failed_row["error_message"]
        == "configuration hash failed"
    )

    failed_record = records[
        failed_row["experiment_id"]
    ]

    assert failed_record["verification"] is None
    assert failed_record["audit"] is None
    assert (
        failed_record["error"]["type"]
        == "RuntimeError"
    )
    assert (
        failed_record["error"]["message"]
        == "configuration hash failed"
    )

    completed_row = summary.iloc[1]

    assert completed_row["status"] == "completed"
    assert completed_row["experiment_id"].startswith(
        "dv-00002-"
    )
    assert (
        completed_row["experiment_id"]
        != "dv-00002-unavailable"
    )


def test_batch_reraises_hash_failure_when_requested(
    monkeypatch,
):
    """Re-raise configuration-hash failures when requested."""
    wn = build_small_network()

    def fail_configuration_hash(**kwargs):
        raise RuntimeError(
            "configuration hash failed"
        )

    monkeypatch.setattr(
        batch_module,
        "_configuration_hash",
        fail_configuration_hash,
    )

    with pytest.raises(
        RuntimeError,
        match="configuration hash failed",
    ):
        run_verification_batch(
            wn=wn,
            scenarios=[build_scenarios()[0]],
            simulators="WNTRSimulator",
            minimum_pressure_m=0.0,
            maximum_velocity_mps=10.0,
            continue_on_error=False,
        )


def test_batch_can_raise_immediately_on_failure():
    """Confirm that continue_on_error=False re-raises an error."""
    wn = build_small_network()

    with pytest.raises(AssertionError):
        run_verification_batch(
            wn=wn,
            scenarios=[build_scenarios()[0]],
            simulators=["unsupported"],
            minimum_pressure_m=0.0,
            maximum_velocity_mps=10.0,
            continue_on_error=False,
        )


def test_batch_includes_pump_diagnostics():
    """Include pump-audit fields in completed batch rows."""
    wn = build_small_network()

    summary, _ = run_verification_batch(
        wn=wn,
        scenarios=[build_scenarios()[0]],
        simulators="WNTRSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
    )

    expected_columns = {
        "pump_feasible",
        "head_pumps_in_network",
        "head_pumps_evaluable",
        "all_head_pumps_evaluable",
        "number_of_pumps_exceeding_curves",
        "total_curve_exceedance_observations",
        "governing_pump_name",
        "maximum_pump_flow_ratio",
    }

    assert expected_columns.issubset(summary.columns)

    row = summary.iloc[0]

    assert pd.isna(row["pump_feasible"])
    assert row["head_pumps_in_network"] == 0
    assert row["head_pumps_evaluable"] == 0
    assert bool(row["all_head_pumps_evaluable"])
    assert row["number_of_pumps_exceeding_curves"] == 0
    assert row["total_curve_exceedance_observations"] == 0
    assert pd.isna(row["governing_pump_name"])
    assert pd.isna(row["maximum_pump_flow_ratio"])


def test_failed_batch_row_has_empty_pump_diagnostics():
    """Leave pump fields empty when verification cannot run."""
    wn = build_small_network()

    summary, _ = run_verification_batch(
        wn=wn,
        scenarios=[build_scenarios()[0]],
        simulators=["unsupported"],
        minimum_pressure_m=0.0,
        maximum_velocity_mps=10.0,
        continue_on_error=True,
    )

    row = summary.iloc[0]

    assert row["status"] == "failed"

    pump_columns = [
        "pump_feasible",
        "head_pumps_in_network",
        "head_pumps_evaluable",
        "all_head_pumps_evaluable",
        "number_of_pumps_exceeding_curves",
        "total_curve_exceedance_observations",
        "governing_pump_name",
        "maximum_pump_flow_ratio",
    ]

    assert all(
        pd.isna(row[column])
        for column in pump_columns
    )
