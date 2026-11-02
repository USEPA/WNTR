"""Run hydraulic simulations and verify design constraints."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import tempfile
from typing import Any

from wntr.network import WaterNetworkModel
from wntr.sim import EpanetSimulator, WNTRSimulator

from .constraints import (
    evaluate_maximum_velocity,
    evaluate_minimum_pressure,
)
from .exceptions import IncompleteHydraulicResultsError
from .design import apply_pipe_design
from .models import (
    HydraulicScenario,
    PipeDesign,
    VerificationResult,
)
from .pumps import audit_head_pump_curves
from .scenarios import apply_hydraulic_scenario


def _validate_simulator_name(value: object) -> str:
    """Validate the WNTR hydraulic-simulator name."""
    assert isinstance(value, str)

    simulator_name = value.strip()

    assert simulator_name in (
        "WNTRSimulator",
        "EpanetSimulator",
    )

    return simulator_name


def _simulation_error_code(results: Any) -> int | None:
    """Extract a numeric simulator error code when available."""
    value = getattr(
        results,
        "error_code",
        None,
    )

    if value is None:
        return None

    value = getattr(
        value,
        "value",
        value,
    )

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def run_design_verification(
    wn: WaterNetworkModel,
    scenario: HydraulicScenario,
    *,
    design: PipeDesign | None = None,
    simulator: str = "WNTRSimulator",
    minimum_pressure_m: float = 15.0,
    maximum_velocity_mps: float = 2.5,
    required_compliance_pct: float = 100.0,
    pressure_tolerance_m: float = 0.0,
    velocity_tolerance_mps: float = 0.0,
) -> tuple[
    VerificationResult,
    Any,
    dict[str, object],
]:
    """Run one hydraulic design-verification assessment.

    The original network is protected from modification. Pipe-diameter
    changes and hydraulic simulation-option changes are applied to
    independent copies.

    Parameters
    ----------
    wn : WaterNetworkModel
        Original WNTR water-distribution network model.
    scenario : HydraulicScenario
        WNTR time and hydraulic simulation options to assess.
    design : PipeDesign or None, optional
        Optional pipe-diameter design. If omitted, the unchanged
        baseline network is assessed.
    simulator : str, optional
        Hydraulic simulation engine. Accepted values are
        ``WNTRSimulator`` and ``EpanetSimulator``.
    minimum_pressure_m : float, optional
        Minimum acceptable junction pressure in metres.
    maximum_velocity_mps : float, optional
        Maximum acceptable absolute pipe velocity in metres per second.
    required_compliance_pct : float, optional
        Required percentage of assessed node-time and pipe-time values
        satisfying each constraint.
    pressure_tolerance_m : float, optional
        Non-negative numerical tolerance applied below the minimum
        pressure limit. The default of zero preserves strict comparison
        behaviour.
    velocity_tolerance_mps : float, optional
        Non-negative numerical tolerance applied above the maximum
        absolute velocity limit. The default of zero preserves strict
        comparison behaviour.

    Returns
    -------
    verification : VerificationResult
        Structured pressure, velocity, pump and overall feasibility
        result.
    hydraulic_results : Any
        Raw WNTR hydraulic simulation results.
    audit : dict
        Record of the applied design, scenario, simulator and assessed
        components.
    """
    assert isinstance(wn, WaterNetworkModel)
    assert isinstance(scenario, HydraulicScenario)
    assert design is None or isinstance(design, PipeDesign)

    simulator_name = _validate_simulator_name(simulator)

    if design is None:
        design_wn = wn
        design_audit = None
        design_name = None
    else:
        design_wn, design_audit = apply_pipe_design(
            wn=wn,
            design=design,
        )
        design_name = design.name.strip()

    scenario_wn, scenario_audit = apply_hydraulic_scenario(
        wn=design_wn,
        scenario=scenario,
    )

    if simulator_name == "WNTRSimulator":
        hydraulic_simulator = WNTRSimulator(scenario_wn)
        hydraulic_results = hydraulic_simulator.run_sim(
            convergence_error=True,
        )
    else:
        with tempfile.TemporaryDirectory(
            prefix="wntr_design_verification_"
        ) as temporary_directory:
            file_prefix = str(
                Path(temporary_directory) / "verification"
            )
            hydraulic_simulator = EpanetSimulator(scenario_wn)
            hydraulic_results = hydraulic_simulator.run_sim(
                file_prefix=file_prefix,
                version=2.2,
                convergence_error=True,
            )

    try:
        pressure = hydraulic_results.node["pressure"]
    except (AttributeError, KeyError) as error:
        raise IncompleteHydraulicResultsError(
            "The simulation did not return node-pressure results."
        ) from error

    try:
        velocity = hydraulic_results.link["velocity"]
    except (AttributeError, KeyError) as error:
        raise IncompleteHydraulicResultsError(
            "The simulation did not return link-velocity results."
        ) from error

    try:
        flowrate = hydraulic_results.link["flowrate"]
    except (AttributeError, KeyError) as error:
        raise IncompleteHydraulicResultsError(
            "The simulation did not return link-flowrate results."
        ) from error

    status = hydraulic_results.link.get("status")
    setting = hydraulic_results.link.get("setting")

    junction_pressure = pressure.loc[
        :,
        scenario_wn.junction_name_list,
    ]

    pipe_velocity = velocity.loc[
        :,
        scenario_wn.pipe_name_list,
    ]

    pressure_result = evaluate_minimum_pressure(
        pressure=junction_pressure,
        minimum_pressure_m=minimum_pressure_m,
        required_compliance_pct=required_compliance_pct,
        pressure_tolerance_m=pressure_tolerance_m,
    )

    velocity_result = evaluate_maximum_velocity(
        velocity=pipe_velocity,
        maximum_velocity_mps=maximum_velocity_mps,
        required_compliance_pct=required_compliance_pct,
        velocity_tolerance_mps=velocity_tolerance_mps,
    )

    pump_result = audit_head_pump_curves(
        network=scenario_wn,
        flowrate=flowrate,
        status=status,
        setting=setting,
    )

    verification = VerificationResult(
        design_name=design_name,
        scenario_name=scenario.name.strip(),
        simulator_name=simulator_name,
        pressure_result=pressure_result,
        velocity_result=velocity_result,
        pump_result=pump_result,
        feasible=bool(
            pressure_result.feasible
            and velocity_result.feasible
            and pump_result.all_pumps_passed
        ),
        simulation_error_code=_simulation_error_code(
            hydraulic_results
        ),
    )

    audit: dict[str, object] = {
        "design": design_audit,
        "scenario": scenario_audit,
        "pump_curve_audit": asdict(pump_result),
        "simulator_name": simulator_name,
        "minimum_pressure_m": float(minimum_pressure_m),
        "maximum_velocity_mps": float(maximum_velocity_mps),
        "required_compliance_pct": float(required_compliance_pct),
        "pressure_tolerance_m": float(pressure_tolerance_m),
        "velocity_tolerance_mps": float(velocity_tolerance_mps),
        "expected_junction_count": len(
            scenario_wn.junction_name_list
        ),
        "assessed_junction_count": len(
            junction_pressure.columns
        ),
        "junctions_assessed": list(
            junction_pressure.columns
        ),
        "expected_pipe_count": len(
            scenario_wn.pipe_name_list
        ),
        "assessed_pipe_count": len(
            pipe_velocity.columns
        ),
        "pipes_assessed": list(
            pipe_velocity.columns
        ),
    }

    return verification, hydraulic_results, audit
