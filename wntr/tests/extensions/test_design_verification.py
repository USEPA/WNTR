"""Tests for the design-verification extension."""

import pandas as pd
import pytest
import wntr

from wntr.extensions.design_verification import (
    HydraulicScenario,
    PipeDesign,
    VerificationResult,
    apply_hydraulic_scenario,
    apply_pipe_design,
    AllPumpCurveResult,
    evaluate_maximum_velocity,
    evaluate_minimum_pressure,
    run_design_verification,
)


def test_minimum_pressure_summary():
    """Identify the minimum pressure and its location."""
    pressure = pd.DataFrame(
        data=[
            [20.0, 14.0],
            [15.0, 16.0],
        ],
        index=[0, 3600],
        columns=["J1", "J2"],
    )

    result = evaluate_minimum_pressure(
        pressure=pressure,
        minimum_pressure_m=15.0,
    )

    assert result.critical_value == pytest.approx(14.0)
    assert result.compliance_pct == pytest.approx(75.0)
    assert result.feasible is False
    assert result.critical_component == "J2"
    assert result.critical_time == 0


def test_maximum_velocity_uses_absolute_value():
    """Use velocity magnitude when identifying violations."""
    velocity = pd.DataFrame(
        data=[
            [1.0, -2.7],
            [2.5, 0.5],
        ],
        index=[0, 3600],
        columns=["P1", "P2"],
    )

    result = evaluate_maximum_velocity(
        velocity=velocity,
        maximum_velocity_mps=2.5,
    )

    assert result.critical_value == pytest.approx(2.7)
    assert result.compliance_pct == pytest.approx(75.0)
    assert result.feasible is False
    assert result.critical_component == "P2"
    assert result.critical_time == 0



def test_pressure_within_tolerance_is_compliant():
    """Accept a pressure shortfall within the stated tolerance."""
    pressure = pd.DataFrame(
        data=[[14.9999995]],
        columns=["J1"],
    )

    result = evaluate_minimum_pressure(
        pressure=pressure,
        minimum_pressure_m=15.0,
        pressure_tolerance_m=1.0e-6,
    )

    assert result.critical_value == pytest.approx(
        14.9999995
    )
    assert result.compliance_pct == pytest.approx(100.0)
    assert result.feasible is True


def test_pressure_beyond_tolerance_is_not_compliant():
    """Reject a pressure shortfall larger than the tolerance."""
    pressure = pd.DataFrame(
        data=[[14.999]],
        columns=["J1"],
    )

    result = evaluate_minimum_pressure(
        pressure=pressure,
        minimum_pressure_m=15.0,
        pressure_tolerance_m=1.0e-6,
    )

    assert result.compliance_pct == pytest.approx(0.0)
    assert result.feasible is False


def test_velocity_within_tolerance_is_compliant():
    """Accept a velocity exceedance within the stated tolerance."""
    velocity = pd.DataFrame(
        data=[[2.500000005]],
        columns=["P1"],
    )

    result = evaluate_maximum_velocity(
        velocity=velocity,
        maximum_velocity_mps=2.5,
        velocity_tolerance_mps=1.0e-8,
    )

    assert result.critical_value == pytest.approx(
        2.500000005
    )
    assert result.compliance_pct == pytest.approx(100.0)
    assert result.feasible is True


def test_velocity_beyond_tolerance_is_not_compliant():
    """Reject a velocity exceedance larger than the tolerance."""
    velocity = pd.DataFrame(
        data=[[2.5001]],
        columns=["P1"],
    )

    result = evaluate_maximum_velocity(
        velocity=velocity,
        maximum_velocity_mps=2.5,
        velocity_tolerance_mps=1.0e-8,
    )

    assert result.compliance_pct == pytest.approx(0.0)
    assert result.feasible is False


@pytest.mark.parametrize(
    "tolerance",
    [
        -1.0,
        float("nan"),
        float("inf"),
    ],
)
def test_invalid_pressure_tolerance_is_rejected(
    tolerance,
):
    """Reject negative or non-finite pressure tolerances."""
    pressure = pd.DataFrame(
        data=[[15.0]],
        columns=["J1"],
    )

    with pytest.raises(
        ValueError,
        match="pressure_tolerance_m",
    ):
        evaluate_minimum_pressure(
            pressure=pressure,
            minimum_pressure_m=15.0,
            pressure_tolerance_m=tolerance,
        )


@pytest.mark.parametrize(
    "tolerance",
    [
        -1.0,
        float("nan"),
        float("inf"),
    ],
)
def test_invalid_velocity_tolerance_is_rejected(
    tolerance,
):
    """Reject negative or non-finite velocity tolerances."""
    velocity = pd.DataFrame(
        data=[[2.5]],
        columns=["P1"],
    )

    with pytest.raises(
        ValueError,
        match="velocity_tolerance_mps",
    ):
        evaluate_maximum_velocity(
            velocity=velocity,
            maximum_velocity_mps=2.5,
            velocity_tolerance_mps=tolerance,
        )



def test_partial_pressure_compliance():
    """Accept a result that meets a reduced compliance requirement."""
    pressure = pd.DataFrame(
        data=[
            [20.0, 14.0],
            [15.0, 16.0],
        ],
        columns=["J1", "J2"],
    )

    result = evaluate_minimum_pressure(
        pressure=pressure,
        minimum_pressure_m=15.0,
        required_compliance_pct=75.0,
    )

    assert result.compliance_pct == pytest.approx(75.0)
    assert result.feasible is True


def test_invalid_velocity_limit_is_rejected():
    """Reject a zero maximum-velocity limit."""
    velocity = pd.DataFrame(
        data=[[1.0]],
        columns=["P1"],
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        evaluate_maximum_velocity(
            velocity=velocity,
            maximum_velocity_mps=0.0,
        )


def test_invalid_compliance_percentage_is_rejected():
    """Reject compliance requirements greater than 100 percent."""
    velocity = pd.DataFrame(
        data=[[1.0]],
        columns=["P1"],
    )

    with pytest.raises(
        ValueError,
        match="between 0 and 100",
    ):
        evaluate_maximum_velocity(
            velocity=velocity,
            maximum_velocity_mps=2.5,
            required_compliance_pct=101.0,
        )

def build_small_network():
    """Create a small network for pipe-design tests."""
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


def test_apply_pipe_design_changes_copied_network():
    """Apply a diameter change to the copied network."""
    wn = build_small_network()

    design = PipeDesign(
        name="Alternative A",
        diameters_m={
            "P1": 0.250,
        },
    )

    trial_wn, audit = apply_pipe_design(
        wn=wn,
        design=design,
    )

    assert trial_wn.get_link("P1").diameter == pytest.approx(
        0.250
    )

    assert len(audit) == 1
    assert audit[0]["pipe_name"] == "P1"
    assert audit[0]["old_diameter_m"] == pytest.approx(
        0.150
    )
    assert audit[0]["new_diameter_m"] == pytest.approx(
        0.250
    )


def test_apply_pipe_design_preserves_original_network():
    """Confirm that the original model is not modified."""
    wn = build_small_network()

    original_diameter = wn.get_link("P1").diameter

    design = PipeDesign(
        name="Alternative A",
        diameters_m={
            "P1": 0.250,
        },
    )

    trial_wn, _ = apply_pipe_design(
        wn=wn,
        design=design,
    )

    assert wn.get_link("P1").diameter == pytest.approx(
        original_diameter
    )

    assert trial_wn.get_link("P1").diameter == pytest.approx(
        0.250
    )

    assert trial_wn is not wn


def test_apply_pipe_design_rejects_missing_pipe():
    """Reject a design containing an unknown pipe name."""
    wn = build_small_network()

    design = PipeDesign(
        name="Invalid alternative",
        diameters_m={
            "MissingPipe": 0.250,
        },
    )

    with pytest.raises(
        KeyError,
        match="does not exist",
    ):
        apply_pipe_design(
            wn=wn,
            design=design,
        )


def test_apply_pipe_design_rejects_negative_diameter():
    """Reject a proposed diameter that is not positive."""
    wn = build_small_network()

    design = PipeDesign(
        name="Invalid alternative",
        diameters_m={
            "P1": -0.250,
        },
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        apply_pipe_design(
            wn=wn,
            design=design,
        )


def test_apply_pipe_design_rejects_empty_design():
    """Reject a design containing no pipe changes."""
    wn = build_small_network()

    design = PipeDesign(
        name="Empty alternative",
        diameters_m={},
    )

    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        apply_pipe_design(
            wn=wn,
            design=design,
        )


def _make_scenario(
    name,
    *,
    demand_model=None,
    demand_multiplier=None,
    duration_s=None,
    hydraulic_timestep_s=None,
    report_timestep_s=None,
    minimum_pressure_m=None,
    required_pressure_m=None,
    pressure_exponent=None,
):
    """Build a HydraulicScenario using WNTR's native Options class."""
    options = wntr.network.Options()

    if duration_s is not None:
        options.time.duration = duration_s
    if hydraulic_timestep_s is not None:
        options.time.hydraulic_timestep = hydraulic_timestep_s
    if report_timestep_s is not None:
        options.time.report_timestep = report_timestep_s
    if demand_model is not None:
        options.hydraulic.demand_model = demand_model
    if demand_multiplier is not None:
        options.hydraulic.demand_multiplier = demand_multiplier
    if minimum_pressure_m is not None:
        options.hydraulic.minimum_pressure = minimum_pressure_m
    if required_pressure_m is not None:
        options.hydraulic.required_pressure = required_pressure_m
    if pressure_exponent is not None:
        options.hydraulic.pressure_exponent = pressure_exponent

    return HydraulicScenario(
        name=name,
        options=options,
    )


def test_apply_hydraulic_scenario_changes_copied_network():
    """Apply WNTR simulation options to an independent network copy."""
    wn = build_small_network()

    scenario = _make_scenario(
        "Peak demand PDD",
        demand_multiplier=1.40,
        demand_model="PDD",
        duration_s=86400,
        hydraulic_timestep_s=3600,
        report_timestep_s=3600,
        minimum_pressure_m=0.0,
        required_pressure_m=15.0,
    )

    scenario_wn, audit = apply_hydraulic_scenario(
        wn=wn,
        scenario=scenario,
    )

    assert scenario_wn is not wn
    assert (
        scenario_wn.options.hydraulic.demand_multiplier
        == pytest.approx(1.40)
    )
    assert str(
        scenario_wn.options.hydraulic.demand_model
    ).upper() in {"PDD", "PDA"}
    assert scenario_wn.options.time.duration == 86400
    assert (
        scenario_wn.options.time.hydraulic_timestep
        == 3600
    )
    assert (
        scenario_wn.options.time.report_timestep
        == 3600
    )
    assert (
        scenario_wn.options.hydraulic.minimum_pressure
        == pytest.approx(0.0)
    )
    assert (
        scenario_wn.options.hydraulic.required_pressure
        == pytest.approx(15.0)
    )
    assert isinstance(audit, dict)


def test_apply_hydraulic_scenario_preserves_original_network():
    """Confirm scenario application does not change the original model."""
    wn = build_small_network()

    original_multiplier = (
        wn.options.hydraulic.demand_multiplier
    )
    original_duration = wn.options.time.duration
    original_demand_model = str(
        wn.options.hydraulic.demand_model
    )

    scenario = _make_scenario(
        "Peak demand",
        demand_multiplier=1.50,
        demand_model="PDD",
        duration_s=86400,
        hydraulic_timestep_s=3600,
        report_timestep_s=3600,
        minimum_pressure_m=0.0,
        required_pressure_m=15.0,
    )

    scenario_wn, _ = apply_hydraulic_scenario(
        wn=wn,
        scenario=scenario,
    )

    assert scenario_wn is not wn
    assert (
        wn.options.hydraulic.demand_multiplier
        == pytest.approx(original_multiplier)
    )
    assert wn.options.time.duration == original_duration
    assert (
        str(wn.options.hydraulic.demand_model)
        == original_demand_model
    )
    assert (
        scenario_wn.options.hydraulic.demand_multiplier
        == pytest.approx(1.50)
    )


def test_apply_hydraulic_scenario_uses_wntr_options():
    """Confirm HydraulicScenario is driven by native WNTR Options."""
    options = wntr.network.Options()
    options.time.duration = 24 * 3600
    options.hydraulic.demand_model = "PDD"
    options.hydraulic.demand_multiplier = 1.25
    options.hydraulic.required_pressure = 15.0
    options.hydraulic.pressure_exponent = 0.5

    scenario = HydraulicScenario(
        name="Options scenario",
        options=options,
    )

    assert scenario.options is options


def test_run_design_verification_returns_feasible_result():
    """Run a complete feasible verification with WNTRSimulator."""
    wn = build_small_network()

    scenario = _make_scenario(
        "Baseline DD",
        demand_model="DD",
        duration_s=0,
        hydraulic_timestep_s=3600,
        report_timestep_s=3600,
    )

    verification, results, audit = run_design_verification(
        wn=wn,
        scenario=scenario,
        simulator="WNTRSimulator",
        minimum_pressure_m=15.0,
        maximum_velocity_mps=2.5,
        pressure_tolerance_m=1.0e-6,
        velocity_tolerance_mps=1.0e-8,
    )

    assert isinstance(
        verification,
        VerificationResult,
    )
    assert verification.design_name is None
    assert verification.scenario_name == "Baseline DD"
    assert verification.simulator_name == "WNTRSimulator"
    assert verification.pressure_result.feasible is True
    assert verification.velocity_result.feasible is True
    assert verification.feasible is True

    assert verification.pressure_result.critical_component == "J1"
    assert verification.velocity_result.critical_component == "P1"

    assert audit["junctions_assessed"] == ["J1"]
    assert audit["pipes_assessed"] == ["P1"]
    assert audit["expected_junction_count"] == 1
    assert audit["assessed_junction_count"] == 1
    assert audit["expected_pipe_count"] == 1
    assert audit["assessed_pipe_count"] == 1

    assert "pressure" in results.node
    assert "velocity" in results.link

    assert verification.pump_result is not None
    assert verification.pump_result.all_pumps_passed
    assert "pump_curve_audit" in audit


def test_run_design_verification_includes_pump_failure(
    monkeypatch,
):
    """Include pump-curve failure in overall feasibility."""
    wn = build_small_network()

    scenario = _make_scenario(
        "Pump failure",
        demand_model="DD",
        duration_s=0,
        hydraulic_timestep_s=3600,
        report_timestep_s=3600,
    )

    failed_pump_result = AllPumpCurveResult(
        head_pumps_in_network=1,
        head_pumps_evaluable=1,
        all_head_pumps_evaluable=True,
        all_pumps_passed=False,
        number_of_pumps_exceeding_curves=1,
        total_curve_exceedance_observations=1,
        governing_pump_name="PU1",
        maximum_pump_flow_ratio=1.2,
        pump_results=(),
    )

    monkeypatch.setattr(
        "wntr.extensions.design_verification.runner."
        "audit_head_pump_curves",
        lambda **kwargs: failed_pump_result,
    )

    verification, _, audit = run_design_verification(
        wn=wn,
        scenario=scenario,
        simulator="WNTRSimulator",
        minimum_pressure_m=15.0,
        maximum_velocity_mps=2.5,
    )

    assert verification.pressure_result.feasible is True
    assert verification.velocity_result.feasible is True
    assert verification.pump_result is failed_pump_result
    assert verification.pump_result.all_pumps_passed is False
    assert verification.feasible is False
    assert audit["pump_curve_audit"]["all_pumps_passed"] is False


def test_run_design_verification_applies_pipe_design():
    """Apply a proposed pipe diameter before simulation."""
    wn = build_small_network()

    design = PipeDesign(
        name="Larger pipe",
        diameters_m={
            "P1": 0.250,
        },
    )

    scenario = _make_scenario(
        "Baseline DD",
        demand_model="DD",
    )

    verification, _, audit = run_design_verification(
        wn=wn,
        scenario=scenario,
        design=design,
        simulator="WNTRSimulator",
        minimum_pressure_m=15.0,
        maximum_velocity_mps=2.5,
    )

    assert verification.design_name == "Larger pipe"
    assert audit["design"] is not None
    assert len(audit["design"]) == 1
    assert audit["design"][0]["pipe_name"] == "P1"
    assert (
        audit["design"][0]["old_diameter_m"]
        == pytest.approx(0.150)
    )
    assert (
        audit["design"][0]["new_diameter_m"]
        == pytest.approx(0.250)
    )


def test_run_design_verification_preserves_original_network():
    """Protect the original network during complete verification."""
    wn = build_small_network()

    original_diameter = wn.get_link("P1").diameter
    original_multiplier = (
        wn.options.hydraulic.demand_multiplier
    )

    design = PipeDesign(
        name="Larger pipe",
        diameters_m={
            "P1": 0.250,
        },
    )

    scenario = _make_scenario(
        "Peak demand",
        demand_multiplier=1.40,
        demand_model="PDD",
        minimum_pressure_m=0.0,
        required_pressure_m=15.0,
    )

    run_design_verification(
        wn=wn,
        scenario=scenario,
        design=design,
        simulator="WNTRSimulator",
        minimum_pressure_m=15.0,
        maximum_velocity_mps=2.5,
    )

    assert (
        wn.get_link("P1").diameter
        == pytest.approx(original_diameter)
    )
    assert (
        wn.options.hydraulic.demand_multiplier
        == pytest.approx(original_multiplier)
    )


def test_run_design_verification_detects_pressure_failure():
    """Mark verification infeasible when pressure is too low."""
    wn = build_small_network()

    scenario = _make_scenario(
        "Pressure failure",
        demand_model="DD",
    )

    verification, _, _ = run_design_verification(
        wn=wn,
        scenario=scenario,
        simulator="WNTRSimulator",
        minimum_pressure_m=45.0,
        maximum_velocity_mps=2.5,
    )

    assert verification.pressure_result.feasible is False
    assert verification.velocity_result.feasible is True
    assert verification.feasible is False
    assert (
        verification.pressure_result.critical_value
        < 45.0
    )


def test_run_design_verification_detects_velocity_failure():
    """Mark verification infeasible when velocity is too high."""
    wn = build_small_network()

    scenario = _make_scenario(
        "Velocity failure",
        demand_model="DD",
    )

    verification, _, _ = run_design_verification(
        wn=wn,
        scenario=scenario,
        simulator="WNTRSimulator",
        minimum_pressure_m=15.0,
        maximum_velocity_mps=0.10,
    )

    assert verification.pressure_result.feasible is True
    assert verification.velocity_result.feasible is False
    assert verification.feasible is False
    assert (
        verification.velocity_result.critical_value
        > 0.10
    )


def test_apply_hydraulic_scenario_applies_pressure_exponent():
    """Apply a pressure exponent through WNTR hydraulic options."""
    wn = build_small_network()
    original_pressure_exponent = (
        wn.options.hydraulic.pressure_exponent
    )

    scenario = _make_scenario(
        "Custom PDD exponent",
        demand_model="PDD",
        minimum_pressure_m=0.0,
        required_pressure_m=15.0,
        pressure_exponent=0.65,
    )

    scenario_wn, _ = apply_hydraulic_scenario(
        wn=wn,
        scenario=scenario,
    )

    assert (
        scenario_wn.options.hydraulic.pressure_exponent
        == pytest.approx(0.65)
    )
    assert (
        wn.options.hydraulic.pressure_exponent
        == pytest.approx(original_pressure_exponent)
    )


def test_run_design_verification_with_epanet():
    """Run a complete hydraulic verification using EpanetSimulator."""
    wn = build_small_network()

    original_diameter = wn.get_link("P1").diameter
    original_multiplier = (
        wn.options.hydraulic.demand_multiplier
    )

    scenario = _make_scenario(
        "EPANET baseline DD",
        demand_model="DD",
        duration_s=0,
        hydraulic_timestep_s=3600,
        report_timestep_s=3600,
    )

    verification, results, audit = run_design_verification(
        wn=wn,
        scenario=scenario,
        simulator="EpanetSimulator",
        minimum_pressure_m=15.0,
        maximum_velocity_mps=2.5,
    )

    assert isinstance(
        verification,
        VerificationResult,
    )
    assert verification.simulator_name == "EpanetSimulator"
    assert verification.scenario_name == "EPANET baseline DD"
    assert verification.pressure_result.feasible is True
    assert verification.velocity_result.feasible is True
    assert verification.feasible is True

    assert audit["simulator_name"] == "EpanetSimulator"
    assert audit["junctions_assessed"] == ["J1"]
    assert audit["pipes_assessed"] == ["P1"]

    assert "pressure" in results.node
    assert "velocity" in results.link
    assert "flowrate" in results.link

    assert verification.pump_result is not None
    assert (
        verification.pump_result.head_pumps_in_network
        == 0
    )

    assert (
        wn.get_link("P1").diameter
        == pytest.approx(original_diameter)
    )
    assert (
        wn.options.hydraulic.demand_multiplier
        == pytest.approx(original_multiplier)
    )


def test_run_design_verification_with_epanet_pump_audit():
    """Pass EPANET pump results through the curve-domain audit."""
    wn = wntr.network.WaterNetworkModel()

    wn.add_reservoir(
        "R1",
        base_head=20.0,
    )
    wn.add_junction(
        "J1",
        base_demand=0.0,
        elevation=0.0,
    )
    wn.add_junction(
        "J2",
        base_demand=0.01,
        elevation=0.0,
    )

    wn.add_curve(
        "curve1",
        "HEAD",
        [
            (0.005, 30.0),
            (0.015, 20.0),
            (0.030, 0.0),
        ],
    )
    wn.add_pump(
        "PU1",
        "R1",
        "J1",
        pump_type="HEAD",
        pump_parameter="curve1",
    )
    wn.add_pipe(
        "L1",
        start_node_name="J1",
        end_node_name="J2",
        length=100.0,
        diameter=0.150,
        roughness=100.0,
        minor_loss=0.0,
    )

    scenario = _make_scenario(
        "EPANET pump audit",
        demand_model="DD",
        duration_s=0,
        hydraulic_timestep_s=3600,
        report_timestep_s=3600,
    )

    verification, results, audit = run_design_verification(
        wn=wn,
        scenario=scenario,
        simulator="EpanetSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=5.0,
    )

    pump_result = verification.pump_result

    assert pump_result is not None
    assert pump_result.head_pumps_in_network == 1
    assert pump_result.head_pumps_evaluable == 1
    assert pump_result.all_head_pumps_evaluable
    assert pump_result.all_pumps_passed
    assert (
        pump_result.number_of_pumps_exceeding_curves
        == 0
    )
    assert len(pump_result.pump_results) == 1

    pump_detail = pump_result.pump_results[0]

    assert pump_detail.pump_name == "PU1"
    assert pump_detail.evaluable
    assert pump_detail.passed
    assert pump_detail.active_observations >= 1
    assert (
        pump_detail.curve_maximum_flow_m3s
        == pytest.approx(0.030)
    )
    assert pump_detail.maximum_flow_ratio < 1.0

    assert verification.pressure_result.feasible
    assert verification.velocity_result.feasible
    assert verification.feasible

    assert "flowrate" in results.link
    assert "status" in results.link
    assert "setting" in results.link
    assert results.link["flowrate"]["PU1"].iloc[0] > 0.0

    assert (
        audit["pump_curve_audit"][
            "head_pumps_in_network"
        ]
        == 1
    )
    assert (
        audit["pump_curve_audit"][
            "all_pumps_passed"
        ]
        is True
    )


def test_epanet_pump_curve_exceedance_fails_verification():
    """Reject EPANET operation beyond the supplied pump-curve domain."""
    wn = wntr.network.WaterNetworkModel()

    wn.add_reservoir(
        "R1",
        base_head=20.0,
    )
    wn.add_junction(
        "J1",
        base_demand=0.0,
        elevation=0.0,
    )
    wn.add_junction(
        "J2",
        base_demand=0.020,
        elevation=0.0,
    )

    wn.add_curve(
        "restricted_curve",
        "HEAD",
        [
            (0.005, 60.0),
            (0.010, 50.0),
            (0.015, 40.0),
        ],
    )
    wn.add_pump(
        "PU1",
        "R1",
        "J1",
        pump_type="HEAD",
        pump_parameter="restricted_curve",
    )
    wn.add_pipe(
        "L1",
        start_node_name="J1",
        end_node_name="J2",
        length=100.0,
        diameter=0.200,
        roughness=120.0,
        minor_loss=0.0,
    )

    scenario = _make_scenario(
        "EPANET pump exceedance",
        demand_model="DD",
        duration_s=0,
        hydraulic_timestep_s=3600,
        report_timestep_s=3600,
    )

    verification, results, audit = run_design_verification(
        wn=wn,
        scenario=scenario,
        simulator="EpanetSimulator",
        minimum_pressure_m=0.0,
        maximum_velocity_mps=5.0,
    )

    pump_result = verification.pump_result

    assert pump_result is not None
    assert pump_result.head_pumps_in_network == 1
    assert pump_result.head_pumps_evaluable == 1
    assert pump_result.all_head_pumps_evaluable
    assert not pump_result.all_pumps_passed
    assert (
        pump_result.number_of_pumps_exceeding_curves
        == 1
    )
    assert (
        pump_result.total_curve_exceedance_observations
        >= 1
    )
    assert pump_result.governing_pump_name == "PU1"
    assert pump_result.maximum_pump_flow_ratio > 1.0

    assert len(pump_result.pump_results) == 1

    pump_detail = pump_result.pump_results[0]

    assert pump_detail.pump_name == "PU1"
    assert pump_detail.evaluable
    assert not pump_detail.passed
    assert pump_detail.exceedance_observations >= 1
    assert (
        pump_detail.curve_maximum_flow_m3s
        == pytest.approx(0.015)
    )
    assert pump_detail.maximum_flow_ratio > 1.0

    assert verification.pressure_result.feasible
    assert verification.velocity_result.feasible
    assert not verification.feasible

    simulated_flow = results.link["flowrate"]["PU1"].iloc[0]
    assert simulated_flow > 0.015

    assert (
        audit["pump_curve_audit"][
            "number_of_pumps_exceeding_curves"
        ]
        == 1
    )
    assert (
        audit["pump_curve_audit"][
            "all_pumps_passed"
        ]
        is False
    )
