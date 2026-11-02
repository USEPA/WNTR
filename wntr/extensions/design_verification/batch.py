"""Run reproducible batches of hydraulic design-verification experiments."""

from __future__ import annotations

import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from itertools import product
from typing import Any, Sequence

import pandas as pd
import wntr
from wntr.network import WaterNetworkModel

from .models import HydraulicScenario, PipeDesign
from .runner import run_design_verification


def _design_payload(
    design: PipeDesign | None,
) -> dict[str, object] | None:
    """Return a JSON-serializable pipe-diameter design description."""
    if design is None:
        return None

    return {
        "name": design.name.strip(),
        "diameters_m": dict(
            sorted(design.diameters_m.items())
        ),
    }


def _scenario_payload(
    scenario: HydraulicScenario,
) -> dict[str, object]:
    """Return the WNTR time and hydraulic options for a scenario."""
    return {
        "name": scenario.name.strip(),
        "time": dict(scenario.options.time),
        "hydraulic": dict(scenario.options.hydraulic),
    }


def _canonical_json(value: object) -> str:
    """Serialize configuration data deterministically."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _network_hash(wn: WaterNetworkModel) -> str:
    """Fingerprint the serialized water-network model."""
    return hashlib.sha256(
        _canonical_json(wn.to_dict()).encode("utf-8")
    ).hexdigest()


def _configuration_hash(
    *,
    network_hash: str,
    design: PipeDesign | None,
    scenario: HydraulicScenario,
    simulator: str,
    minimum_pressure_m: float,
    maximum_velocity_mps: float,
    required_compliance_pct: float,
    pressure_tolerance_m: float,
    velocity_tolerance_mps: float,
) -> tuple[str, str, str]:
    """Return a stable hash and serialized configuration records."""
    design_json = _canonical_json(_design_payload(design))
    scenario_json = _canonical_json(_scenario_payload(scenario))

    payload = {
        "network_hash": network_hash,
        "design": json.loads(design_json),
        "scenario": json.loads(scenario_json),
        "simulator": simulator.strip(),
        "minimum_pressure_m": float(minimum_pressure_m),
        "maximum_velocity_mps": float(maximum_velocity_mps),
        "required_compliance_pct": float(required_compliance_pct),
        "pressure_tolerance_m": float(pressure_tolerance_m),
        "velocity_tolerance_mps": float(velocity_tolerance_mps),
    }

    digest = hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()

    return digest, design_json, scenario_json


def _pump_summary_fields(
    pump_result: Any | None,
) -> dict[str, object]:
    """Return batch-summary fields from a pump-curve audit."""
    if pump_result is None:
        return {
            "pump_feasible": None,
            "head_pumps_in_network": None,
            "head_pumps_evaluable": None,
            "all_head_pumps_evaluable": None,
            "number_of_pumps_exceeding_curves": None,
            "total_curve_exceedance_observations": None,
            "governing_pump_name": None,
            "maximum_pump_flow_ratio": None,
        }

    return {
        "pump_feasible": (
            None
            if pump_result.head_pumps_in_network == 0
            else pump_result.all_pumps_passed
        ),
        "head_pumps_in_network": pump_result.head_pumps_in_network,
        "head_pumps_evaluable": pump_result.head_pumps_evaluable,
        "all_head_pumps_evaluable": (
            pump_result.all_head_pumps_evaluable
        ),
        "number_of_pumps_exceeding_curves": (
            pump_result.number_of_pumps_exceeding_curves
        ),
        "total_curve_exceedance_observations": (
            pump_result.total_curve_exceedance_observations
        ),
        "governing_pump_name": pump_result.governing_pump_name,
        "maximum_pump_flow_ratio": (
            pump_result.maximum_pump_flow_ratio
        ),
    }


def _base_row(
    *,
    experiment_id: str,
    configuration_hash: str,
    network_hash: str,
    design: PipeDesign | None,
    scenario: HydraulicScenario,
    simulator: str,
    design_json: str | None,
    scenario_json: str | None,
    started_at_utc: str,
    elapsed_s: float,
    minimum_pressure_m: float,
    maximum_velocity_mps: float,
    required_compliance_pct: float,
    pressure_tolerance_m: float,
    velocity_tolerance_mps: float,
) -> dict[str, object]:
    """Create fields shared by successful and failed experiments."""
    return {
        "experiment_id": experiment_id,
        "configuration_hash": configuration_hash,
        "network_hash": network_hash,
        "status": None,
        "started_at_utc": started_at_utc,
        "elapsed_s": elapsed_s,
        "design_name": (
            None if design is None else design.name.strip()
        ),
        "scenario_name": scenario.name.strip(),
        "simulator_name": simulator.strip(),
        "demand_multiplier": (
            scenario.options.hydraulic.demand_multiplier
        ),
        "demand_model": str(
            scenario.options.hydraulic.demand_model
        ),
        "duration_s": scenario.options.time.duration,
        "hydraulic_timestep_s": (
            scenario.options.time.hydraulic_timestep
        ),
        "report_timestep_s": (
            scenario.options.time.report_timestep
        ),
        "minimum_pressure_limit_m": float(minimum_pressure_m),
        "maximum_velocity_limit_mps": float(maximum_velocity_mps),
        "required_compliance_pct": float(required_compliance_pct),
        "pressure_tolerance_m": float(pressure_tolerance_m),
        "velocity_tolerance_mps": float(velocity_tolerance_mps),
        "design_configuration_json": design_json,
        "scenario_configuration_json": scenario_json,
        "python_version": platform.python_version(),
        "wntr_version": getattr(wntr, "__version__", "unknown"),
        "platform": platform.platform(),
    }


def run_verification_batch(
    wn: WaterNetworkModel,
    scenarios: Sequence[HydraulicScenario],
    *,
    designs: Sequence[PipeDesign | None] | None = None,
    simulators: Sequence[str] | str = ("WNTRSimulator",),
    minimum_pressure_m: float = 15.0,
    maximum_velocity_mps: float = 2.5,
    required_compliance_pct: float = 100.0,
    pressure_tolerance_m: float = 0.0,
    velocity_tolerance_mps: float = 0.0,
    continue_on_error: bool = True,
    retain_hydraulic_results: bool = False,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Run every requested design-scenario-simulator combination.

    Parameters
    ----------
    wn : WaterNetworkModel
        Original WNTR water-distribution network.
    scenarios : Sequence[HydraulicScenario]
        Hydraulic scenarios containing WNTR time and hydraulic options.
    designs : Sequence[PipeDesign | None] or None, optional
        Pipe-diameter designs to assess. Use ``None`` for the unchanged
        baseline network. When omitted, only the baseline is assessed.
    simulators : Sequence[str] or str, optional
        ``WNTRSimulator`` or ``EpanetSimulator``, or a sequence
        containing those names.
    minimum_pressure_m : float, optional
        Minimum acceptable junction pressure.
    maximum_velocity_mps : float, optional
        Maximum acceptable absolute pipe velocity.
    required_compliance_pct : float, optional
        Required pressure and velocity compliance percentage.
    pressure_tolerance_m : float, optional
        Numerical tolerance below the minimum pressure limit.
    velocity_tolerance_mps : float, optional
        Numerical tolerance above the maximum velocity limit.
    continue_on_error : bool, optional
        Record an experiment failure and continue when ``True``.
    retain_hydraulic_results : bool, optional
        Retain raw hydraulic result objects in returned records.

    Returns
    -------
    summary : pd.DataFrame
        One row per requested experiment.
    records : dict
        Detailed records keyed by experiment ID.
    """
    assert isinstance(wn, WaterNetworkModel)

    design_values = [None] if designs is None else list(designs)
    scenario_values = list(scenarios)
    simulator_values = (
        [simulators]
        if isinstance(simulators, str)
        else list(simulators)
    )

    assert design_values and all(
        design is None or isinstance(design, PipeDesign)
        for design in design_values
    ), "designs must contain PipeDesign objects or None"

    assert scenario_values and all(
        isinstance(scenario, HydraulicScenario)
        for scenario in scenario_values
    ), "scenarios must contain HydraulicScenario objects"

    assert simulator_values and all(
        isinstance(simulator, str)
        for simulator in simulator_values
    ), "simulators must be a string or sequence of strings"

    rows: list[dict[str, object]] = []
    records: dict[str, dict[str, Any]] = {}
    network_hash_cache: str | None = None

    combinations = product(
        design_values,
        scenario_values,
        simulator_values,
    )

    for experiment_number, (
        design,
        scenario,
        simulator,
    ) in enumerate(combinations, start=1):
        started_at_utc = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()

        network_hash = "unavailable"
        configuration_hash = "unavailable"
        design_json = None
        scenario_json = None
        experiment_id = (
            f"dv-{experiment_number:05d}-unavailable"
        )

        try:
            if network_hash_cache is None:
                network_hash_cache = _network_hash(wn)

            network_hash = network_hash_cache

            (
                configuration_hash,
                design_json,
                scenario_json,
            ) = _configuration_hash(
                network_hash=network_hash,
                design=design,
                scenario=scenario,
                simulator=simulator,
                minimum_pressure_m=minimum_pressure_m,
                maximum_velocity_mps=maximum_velocity_mps,
                required_compliance_pct=required_compliance_pct,
                pressure_tolerance_m=pressure_tolerance_m,
                velocity_tolerance_mps=velocity_tolerance_mps,
            )

            experiment_id = (
                f"dv-{experiment_number:05d}-"
                f"{configuration_hash[:12]}"
            )

            (
                verification,
                hydraulic_results,
                audit,
            ) = run_design_verification(
                wn=wn,
                scenario=scenario,
                design=design,
                simulator=simulator,
                minimum_pressure_m=minimum_pressure_m,
                maximum_velocity_mps=maximum_velocity_mps,
                required_compliance_pct=required_compliance_pct,
                pressure_tolerance_m=pressure_tolerance_m,
                velocity_tolerance_mps=velocity_tolerance_mps,
            )

            elapsed_s = time.perf_counter() - started

            row = _base_row(
                experiment_id=experiment_id,
                configuration_hash=configuration_hash,
                network_hash=network_hash,
                design=design,
                scenario=scenario,
                simulator=verification.simulator_name,
                design_json=design_json,
                scenario_json=scenario_json,
                started_at_utc=started_at_utc,
                elapsed_s=elapsed_s,
                minimum_pressure_m=minimum_pressure_m,
                maximum_velocity_mps=maximum_velocity_mps,
                required_compliance_pct=required_compliance_pct,
                pressure_tolerance_m=pressure_tolerance_m,
                velocity_tolerance_mps=velocity_tolerance_mps,
            )

            pressure_result = verification.pressure_result
            velocity_result = verification.velocity_result

            row.update(
                {
                    "status": "completed",
                    "overall_feasible": verification.feasible,
                    "pressure_feasible": pressure_result.feasible,
                    "velocity_feasible": velocity_result.feasible,
                    "minimum_pressure_m": pressure_result.critical_value,
                    "pressure_margin_m": (
                        pressure_result.critical_value
                        - float(minimum_pressure_m)
                    ),
                    "pressure_compliance_pct": (
                        pressure_result.compliance_pct
                    ),
                    "critical_pressure_component": (
                        pressure_result.critical_component
                    ),
                    "critical_pressure_time": (
                        pressure_result.critical_time
                    ),
                    "maximum_velocity_mps": velocity_result.critical_value,
                    "velocity_margin_mps": (
                        float(maximum_velocity_mps)
                        - velocity_result.critical_value
                    ),
                    "velocity_compliance_pct": (
                        velocity_result.compliance_pct
                    ),
                    "critical_velocity_component": (
                        velocity_result.critical_component
                    ),
                    "critical_velocity_time": (
                        velocity_result.critical_time
                    ),
                    "simulation_error_code": (
                        verification.simulation_error_code
                    ),
                    "error_type": None,
                    "error_message": None,
                }
            )

            row.update(
                _pump_summary_fields(verification.pump_result)
            )

            record: dict[str, Any] = {
                "verification": verification,
                "audit": audit,
                "error": None,
            }

            if retain_hydraulic_results:
                record["hydraulic_results"] = hydraulic_results

            records[experiment_id] = record

        except Exception as error:
            elapsed_s = time.perf_counter() - started

            if not continue_on_error:
                raise

            row = _base_row(
                experiment_id=experiment_id,
                configuration_hash=configuration_hash,
                network_hash=network_hash,
                design=design,
                scenario=scenario,
                simulator=simulator,
                design_json=design_json,
                scenario_json=scenario_json,
                started_at_utc=started_at_utc,
                elapsed_s=elapsed_s,
                minimum_pressure_m=minimum_pressure_m,
                maximum_velocity_mps=maximum_velocity_mps,
                required_compliance_pct=required_compliance_pct,
                pressure_tolerance_m=pressure_tolerance_m,
                velocity_tolerance_mps=velocity_tolerance_mps,
            )

            row.update(
                {
                    "status": "failed",
                    "overall_feasible": None,
                    "pressure_feasible": None,
                    "velocity_feasible": None,
                    "minimum_pressure_m": None,
                    "pressure_margin_m": None,
                    "pressure_compliance_pct": None,
                    "critical_pressure_component": None,
                    "critical_pressure_time": None,
                    "maximum_velocity_mps": None,
                    "velocity_margin_mps": None,
                    "velocity_compliance_pct": None,
                    "critical_velocity_component": None,
                    "critical_velocity_time": None,
                    "simulation_error_code": None,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )

            row.update(_pump_summary_fields(None))

            records[experiment_id] = {
                "verification": None,
                "audit": None,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                },
            }

        rows.append(row)

    return pd.DataFrame(rows), records
