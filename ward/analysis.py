from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .scenario import WaterScenario

# note this conversion i used: 1 m H2O = 1.42233433 psi (1 psi = 0.70306958 m)
METERS_TO_PSI = 1.4223343307119555
PSI_TO_METERS = 1.0 / METERS_TO_PSI

# target requirement: pressure strictly below 20.0 psi (~14.0614 m)
ARCHITECTURE_MIN_PRESSURE_PSI = 20.0


@dataclass(frozen=True)
class ImpactThresholds:
    """Thresholds for identifying and ranking affected nodes.

    Note: Provisional thresholds awaiting sponsor confirmation are explicitly
    tagged in metadata so reviewers and the dashboard can distinguish approved
    architecture limits from temporary demo parameters.
    """

    min_pressure_psi: float = ARCHITECTURE_MIN_PRESSURE_PSI
    pressure_drop_psi: float = 5.0
    min_demand_delivery_ratio: float = 0.95
    provisional_awaiting_sponsor_confirmation: bool = True

    def to_metadata_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["min_pressure_m"] = round(self.min_pressure_psi * PSI_TO_METERS, 6)
        data["pressure_drop_m"] = round(self.pressure_drop_psi * PSI_TO_METERS, 6)
        data["conversion_factors"] = {
            "meters_to_psi": METERS_TO_PSI,
            "psi_to_meters": PSI_TO_METERS,
        }
        data["provisional_fields"] = [
            "pressure_drop_psi",
            "min_demand_delivery_ratio",
            "summarized_window_rule",
        ]
        return data


def meters_to_psi(pressure_m: pd.DataFrame | pd.Series | float) -> Any:
    """Convert water pressure from meters of head to psi."""
    return pressure_m * METERS_TO_PSI


def _select_window_slice(
    frame: pd.DataFrame,
    start_time_sec: float | None,
    end_time_sec: float | None,
) -> pd.DataFrame:
    """Select timesteps inside the active outage window (start_time_sec, end_time_sec]."""
    if frame.empty:
        return frame
    mask = pd.Series(True, index=frame.index)
    if start_time_sec is not None:
        mask &= frame.index > start_time_sec
    if end_time_sec is not None:
        mask &= frame.index <= end_time_sec
    selected = frame.loc[mask]
    return selected if not selected.empty else frame


def _compute_step_durations_hours(
    full_index: pd.Index,
    window_index: pd.Index,
    start_time_sec: float | None,
    end_time_sec: float | None,
) -> pd.Series:
    """Compute duration in hours represented by each timestep in window_index."""
    if len(window_index) == 0:
        return pd.Series(dtype=float)

    all_times = sorted(float(t) for t in full_index)
    durations_sec: list[float] = []

    for t in window_index:
        t_val = float(t)
        pos = all_times.index(t_val)
        if pos > 0:
            prev_t = all_times[pos - 1]
            if start_time_sec is not None:
                prev_t = max(prev_t, float(start_time_sec))
            dt = max(0.0, t_val - prev_t)
        elif start_time_sec is not None and t_val > float(start_time_sec):
            dt = t_val - float(start_time_sec)
        elif len(all_times) > 1:
            dt = max(0.0, all_times[1] - all_times[0])
        else:
            dt = 0.0

        if end_time_sec is not None and t_val > float(end_time_sec):
            dt = max(0.0, dt - (t_val - float(end_time_sec)))
        durations_sec.append(dt)

    return pd.Series([d / 3600.0 for d in durations_sec], index=window_index)


def identify_affected_nodes(
    paired_results: dict[str, Any],
    scenario: WaterScenario | None = None,
    *,
    thresholds: ImpactThresholds | None = None,
    start_time_sec: float | None = None,
    end_time_sec: float | None = None,
    exclude_non_demand_nodes: bool = True,
) -> dict[str, Any]:
    """Compare attack simulation results against baseline and explain affected nodes.

    Parameters
    ----------
    paired_results:
        Output dictionary from ``run_paired_simulations()`` containing ``"baseline"``
        and ``"attack"`` entries with ``node["pressure"]`` (in meters) and optional
        ``node["demand"]`` (in m^3/s).
    scenario:
        Optional ``WaterScenario`` defining the outage timing window.
    thresholds:
        Optional ``ImpactThresholds`` overriding default pressure/service limits.
    start_time_sec / end_time_sec:
        Explicit outage window bounds in seconds (overrides ``scenario.timing`` if given).
    exclude_non_demand_nodes:
        When True and demand data is available, skips reservoirs/tanks that never have
        positive consumer demand in the baseline run.
    """
    active_thresholds = thresholds or ImpactThresholds()

    baseline_case = paired_results.get("baseline", {})
    attack_case = paired_results.get("attack", {})

    if not baseline_case.get("converged", True) or not attack_case.get(
        "converged", True
    ):
        raise ValueError(
            "Cannot analyze affected nodes from non-converged simulation results."
        )

    base_pressure_m: pd.DataFrame = baseline_case["node"]["pressure"]
    atk_pressure_m: pd.DataFrame = attack_case["node"]["pressure"]

    if base_pressure_m.empty or atk_pressure_m.empty:
        raise ValueError("Pressure result tables must not be empty.")

    common_times = base_pressure_m.index.intersection(atk_pressure_m.index)
    common_nodes = [n for n in base_pressure_m.columns if n in atk_pressure_m.columns]

    base_pressure_m = base_pressure_m.loc[common_times, common_nodes]
    atk_pressure_m = atk_pressure_m.loc[common_times, common_nodes]

    if scenario is not None:
        if start_time_sec is None:
            start_time_sec = float(scenario.timing.start_time_sec)
        if end_time_sec is None:
            end_time_sec = float(
                scenario.timing.start_time_sec + scenario.timing.duration_sec
            )

    win_base_m = _select_window_slice(base_pressure_m, start_time_sec, end_time_sec)
    win_atk_m = _select_window_slice(atk_pressure_m, start_time_sec, end_time_sec)

    win_base_psi = meters_to_psi(win_base_m)
    win_atk_psi = meters_to_psi(win_atk_m)
    step_hours = _compute_step_durations_hours(
        common_times, win_base_m.index, start_time_sec, end_time_sec
    )

    has_demand = (
        "demand" in baseline_case.get("node", {})
        and "demand" in attack_case.get("node", {})
        and not baseline_case["node"]["demand"].empty
        and not attack_case["node"]["demand"].empty
    )

    if has_demand:
        base_demand = baseline_case["node"]["demand"].loc[
            win_base_m.index, common_nodes
        ]
        atk_demand = attack_case["node"]["demand"].loc[win_base_m.index, common_nodes]
    else:
        base_demand = None
        atk_demand = None

    affected_nodes: list[dict[str, Any]] = []
    pre_existing_only_nodes: list[dict[str, Any]] = []

    for node_id in common_nodes:
        b_p_series = win_base_psi[node_id]
        a_p_series = win_atk_psi[node_id]

        # if no damange done to node, skip reservoirs if demand data is here
        if (
            has_demand
            and exclude_non_demand_nodes
            and float(base_demand[node_id].max()) <= 0.0
        ):
            continue

        b_min_psi = float(b_p_series.min())
        a_min_psi = float(a_p_series.min())
        b_mean_psi = float(b_p_series.mean())
        a_mean_psi = float(a_p_series.mean())

        drop_series_psi = b_p_series - a_p_series
        max_drop_psi = float(drop_series_psi.max())
        mean_drop_psi = float(drop_series_psi.mean())

        b_low_mask = b_p_series < active_thresholds.min_pressure_psi
        a_low_mask = a_p_series < active_thresholds.min_pressure_psi
        new_low_mask = (~b_low_mask) & a_low_mask
        drop_exceeded_mask = drop_series_psi >= active_thresholds.pressure_drop_psi

        baseline_had_low_pressure = bool(b_low_mask.any())
        attack_caused_new_low_pressure = bool(new_low_mask.any())
        significant_pressure_drop = bool(drop_exceeded_mask.any())

        min_delivery_ratio = 1.0
        demand_deficit_mask = pd.Series(False, index=win_base_m.index)
        if has_demand:
            b_d = base_demand[node_id]
            a_d = atk_demand[node_id]
            pos_mask = b_d > 1e-9
            if bool(pos_mask.any()):
                ratios = (a_d[pos_mask] / b_d[pos_mask]).clip(lower=0.0)
                min_delivery_ratio = float(ratios.min())
                full_ratios = pd.Series(1.0, index=win_base_m.index)
                full_ratios.loc[pos_mask] = ratios
                demand_deficit_mask = (
                    full_ratios < active_thresholds.min_demand_delivery_ratio
                )

        service_shortfall = bool(demand_deficit_mask.any())

        # before vs after impact
        reasons: list[str] = []
        if attack_caused_new_low_pressure:
            reasons.append(
                f"Pressure dropped below {active_thresholds.min_pressure_psi:.1f} psi "
                f"(to {a_min_psi:.2f} psi) from compliant baseline ({b_min_psi:.2f} psi)."
            )
        if baseline_had_low_pressure and (
            significant_pressure_drop or service_shortfall
        ):
            reasons.append(
                f"Pre-existing low pressure (< {active_thresholds.min_pressure_psi:.1f} psi in baseline: "
                f"{b_min_psi:.2f} psi) was worsened by the attack (min {a_min_psi:.2f} psi, "
                f"max drop {max_drop_psi:.2f} psi)."
            )
        if (
            significant_pressure_drop
            and not attack_caused_new_low_pressure
            and not baseline_had_low_pressure
        ):
            reasons.append(
                f"Attack reduced pressure by {max_drop_psi:.2f} psi (>= {active_thresholds.pressure_drop_psi:.1f} psi "
                f"drop threshold), from {b_min_psi:.2f} psi to {a_min_psi:.2f} psi."
            )
        if service_shortfall:
            reasons.append(
                f"Water service delivery fell to {min_delivery_ratio * 100.0:.1f}% of baseline demand "
                f"(< {active_thresholds.min_demand_delivery_ratio * 100.0:.1f}% threshold)."
            )

        impacted_step_mask = new_low_mask | drop_exceeded_mask | demand_deficit_mask
        impact_duration_hours = float(step_hours.loc[impacted_step_mask].sum())

        record = {
            "node_id": str(node_id),
            "baseline_min_pressure_psi": round(b_min_psi, 3),
            "attack_min_pressure_psi": round(a_min_psi, 3),
            "baseline_mean_pressure_psi": round(b_mean_psi, 3),
            "attack_mean_pressure_psi": round(a_mean_psi, 3),
            "baseline_min_pressure_m": round(b_min_psi * PSI_TO_METERS, 3),
            "attack_min_pressure_m": round(a_min_psi * PSI_TO_METERS, 3),
            "max_pressure_drop_psi": round(max_drop_psi, 3),
            "mean_pressure_drop_psi": round(mean_drop_psi, 3),
            "min_demand_delivery_ratio": round(min_delivery_ratio, 4),
            "duration_hours": round(impact_duration_hours, 3),
            "pre_existing_low_pressure": baseline_had_low_pressure,
            "attack_caused_impact": len(reasons) > 0,
            "reasons": reasons,
            "ranking_measure_name": "max_pressure_drop_psi",
            "ranking_measure_value": round(max_drop_psi, 3),
        }

        if len(reasons) > 0:
            if baseline_had_low_pressure:
                record["impact_category"] = "worsened_pre_existing_low_pressure"
            elif attack_caused_new_low_pressure:
                record["impact_category"] = "attack_induced_low_pressure"
            else:
                record["impact_category"] = "attack_induced_degradation"
            affected_nodes.append(record)
        elif baseline_had_low_pressure:
            record["impact_category"] = "pre_existing_low_pressure_unchanged"
            record["duration_hours"] = round(float(step_hours.loc[b_low_mask].sum()), 3)
            record["reasons"] = [
                (
                    f"Already below {active_thresholds.min_pressure_psi:.1f} psi in baseline "
                    f"({b_min_psi:.2f} psi) with no significant additional attack degradation."
                )
            ]
            pre_existing_only_nodes.append(record)

    # RANKING RULES:
    # 1. Largest max_pressure_drop_psi (descending)
    # 2. Longest duration_hours (descending)
    # 3. Lowest attack_min_pressure_psi (ascending)
    # 4. Lexicographical node_id (ascending) for exact ties
    affected_nodes.sort(
        key=lambda item: (
            -item["max_pressure_drop_psi"],
            -item["duration_hours"],
            item["attack_min_pressure_psi"],
            item["node_id"],
        )
    )

    for idx, item in enumerate(affected_nodes, start=1):
        item["rank"] = idx

    window_start_hr = (
        round(float(start_time_sec) / 3600.0, 3)
        if start_time_sec is not None
        else round(float(win_base_m.index.min()) / 3600.0, 3)
    )
    window_end_hr = (
        round(float(end_time_sec) / 3600.0, 3)
        if end_time_sec is not None
        else round(float(win_base_m.index.max()) / 3600.0, 3)
    )

    return {
        "scenario_id": scenario.scenario_id if scenario is not None else None,
        "summary": {
            "total_evaluated_nodes": len(common_nodes),
            "affected_node_count": len(affected_nodes),
            "pre_existing_only_node_count": len(pre_existing_only_nodes),
            "window_start_hours": window_start_hr,
            "window_end_hours": window_end_hr,
            "window_duration_hours": round(window_end_hr - window_start_hr, 3),
        },
        "thresholds": active_thresholds.to_metadata_dict(),
        "ranking_rules": {
            "primary_measure": "max_pressure_drop_psi (descending)",
            "tie_breakers": [
                "duration_hours (descending)",
                "attack_min_pressure_psi (ascending)",
                "node_id (ascending)",
            ],
        },
        "affected_nodes": affected_nodes,
        "pre_existing_only_nodes": pre_existing_only_nodes,
    }
