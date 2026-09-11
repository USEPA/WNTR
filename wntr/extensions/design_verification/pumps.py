"""Head-pump operating-curve auditing for hydraulic verification."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Hashable

import pandas as pd

from wntr.network import WaterNetworkModel
from wntr.utils.check_values import _check_positive_or_zero_float
from .exceptions import InvalidConstraintError


@dataclass(frozen=True)
class PumpCurveResult:
    """Result of auditing one head pump against its operating curve."""

    pump_name: str
    curve_name: str | None
    evaluable: bool
    passed: bool
    active_observations: int
    exceedance_observations: int
    curve_maximum_flow_m3s: float | None
    maximum_active_flow_m3s: float | None
    maximum_allowed_flow_m3s: float | None
    maximum_flow_ratio: float | None
    critical_time: Hashable | None


@dataclass(frozen=True)
class AllPumpCurveResult:
    """Combined operating-curve result for every head pump."""

    head_pumps_in_network: int
    head_pumps_evaluable: int
    all_head_pumps_evaluable: bool
    all_pumps_passed: bool
    number_of_pumps_exceeding_curves: int
    total_curve_exceedance_observations: int
    governing_pump_name: str | None
    maximum_pump_flow_ratio: float | None
    pump_results: tuple[PumpCurveResult, ...]


def _numeric_series(
    table: pd.DataFrame | None,
    column: str,
    index: pd.Index,
) -> pd.Series | None:
    if table is None or column not in table.columns:
        return None

    return pd.to_numeric(
        table[column].reindex(index),
        errors="coerce",
    )


def _curve_maximum_flow(
    pump: object,
) -> tuple[str | None, float | None]:
    """Return the maximum flow represented by a head-pump curve.

    For a one-point curve, WNTR and EPANET generate an implied pump
    curve. Its zero-head flow is calculated from the generated
    A, B, and C coefficients.

    For curves containing two or more supplied points, the maximum
    supplied flow is treated as the explicit curve-domain boundary.
    """
    curve_name = getattr(pump, "pump_curve_name", None)

    try:
        curve = pump.get_pump_curve()
    except (AttributeError, KeyError, RuntimeError):
        return curve_name, None

    points = getattr(curve, "points", None)
    if not points:
        return curve_name, None

    curve_name = str(getattr(curve, "name", curve_name))

    valid_flows: list[float] = []

    for point in points:
        try:
            flow = float(point[0])
        except (TypeError, ValueError, IndexError):
            continue

        if math.isfinite(flow) and flow >= 0.0:
            valid_flows.append(flow)

    if not valid_flows:
        return curve_name, None

    if len(points) == 1:
        try:
            coefficient_a, coefficient_b, coefficient_c = (
                float(value)
                for value in pump.get_head_curve_coefficients()
            )
        except (
            AttributeError,
            RuntimeError,
            TypeError,
            ValueError,
            ZeroDivisionError,
        ):
            return curve_name, None

        coefficients_valid = (
            math.isfinite(coefficient_a)
            and math.isfinite(coefficient_b)
            and math.isfinite(coefficient_c)
            and coefficient_a > 0.0
            and coefficient_b > 0.0
            and coefficient_c > 0.0
        )

        if not coefficients_valid:
            return curve_name, None

        try:
            maximum_flow = (
                coefficient_a / coefficient_b
            ) ** (1.0 / coefficient_c)
        except (
            ArithmeticError,
            OverflowError,
            ValueError,
        ):
            return curve_name, None

        if not math.isfinite(maximum_flow) or maximum_flow <= 0.0:
            return curve_name, None

        return curve_name, maximum_flow

    return curve_name, max(valid_flows)


def audit_head_pump_curves(
    network: WaterNetworkModel,
    flowrate: pd.DataFrame,
    *,
    status: pd.DataFrame | None = None,
    setting: pd.DataFrame | None = None,
    relative_tolerance: float = 1.0e-9,
) -> AllPumpCurveResult:
    """Audit every head pump against the maximum flow in its curve.

    Pump affinity scaling is respected by multiplying the maximum
    curve-point flow by the pump speed reported in the hydraulic
    ``setting`` result. When no setting result is supplied, the pump's
    configured base speed is used.

    Parameters
    ----------
    network : WaterNetworkModel
        WNTR water-network model used for the simulation.
    flowrate : pd.DataFrame
        Link-flowrate results indexed by simulation time.
    status : pd.DataFrame or None, optional
        Optional link-status results. Positive values are treated as active.
    setting : pd.DataFrame or None, optional
        Optional link-setting results. For pumps, this represents speed.
    relative_tolerance : float, optional
        Relative numerical tolerance applied to the curve-domain limit.
    """
    if not isinstance(network, WaterNetworkModel):
        raise TypeError("network must be a WaterNetworkModel")

    if not isinstance(flowrate, pd.DataFrame):
        raise TypeError("flowrate must be a pandas DataFrame")

    tolerance = _check_positive_or_zero_float(
        relative_tolerance,
        "relative_tolerance",
    )

    if not math.isfinite(tolerance):
        raise InvalidConstraintError(
            "relative_tolerance must be finite."
        )

    pump_names = list(
        getattr(network, "head_pump_name_list", [])
    )
    pump_results: list[PumpCurveResult] = []

    for pump_name in pump_names:
        pump = network.get_link(pump_name)
        curve_name, curve_maximum_flow = _curve_maximum_flow(pump)

        flow = _numeric_series(
            flowrate,
            pump_name,
            flowrate.index,
        )

        if flow is None or curve_maximum_flow is None:
            pump_results.append(
                PumpCurveResult(
                    pump_name=str(pump_name),
                    curve_name=curve_name,
                    evaluable=False,
                    passed=False,
                    active_observations=0,
                    exceedance_observations=0,
                    curve_maximum_flow_m3s=curve_maximum_flow,
                    maximum_active_flow_m3s=None,
                    maximum_allowed_flow_m3s=None,
                    maximum_flow_ratio=None,
                    critical_time=None,
                )
            )
            continue

        pump_status = _numeric_series(
            status,
            pump_name,
            flowrate.index,
        )

        if pump_status is None:
            invalid_status = pd.Series(
                False,
                index=flowrate.index,
                dtype=bool,
            )
            active = flow.notna() & flow.abs().gt(0.0)
        else:
            invalid_status = (
                pump_status.isna()
                | ~pump_status.map(math.isfinite)
                | pump_status.lt(0.0)
            )
            active = pump_status.gt(0.0) & ~invalid_status

        pump_setting = _numeric_series(
            setting,
            pump_name,
            flowrate.index,
        )

        base_speed = float(getattr(pump, "base_speed", 1.0))
        if not math.isfinite(base_speed) or base_speed < 0.0:
            base_speed = 1.0

        if pump_setting is None:
            speed = pd.Series(
                base_speed,
                index=flowrate.index,
                dtype=float,
            )
        else:
            speed = pump_setting

        allowed_flow = curve_maximum_flow * speed

        active_observations = int(active.sum())

        invalid_observation = invalid_status | (
            active
            & (
                flow.isna()
                | ~flow.map(math.isfinite)
                | flow.lt(0.0)
                | speed.isna()
                | ~speed.map(math.isfinite)
                | speed.le(0.0)
                | allowed_flow.isna()
                | ~allowed_flow.map(math.isfinite)
                | allowed_flow.le(0.0)
            )
        )

        if bool(invalid_observation.any()):
            pump_results.append(
                PumpCurveResult(
                    pump_name=str(pump_name),
                    curve_name=curve_name,
                    evaluable=False,
                    passed=False,
                    active_observations=active_observations,
                    exceedance_observations=0,
                    curve_maximum_flow_m3s=curve_maximum_flow,
                    maximum_active_flow_m3s=None,
                    maximum_allowed_flow_m3s=None,
                    maximum_flow_ratio=None,
                    critical_time=invalid_observation.idxmax(),
                )
            )
            continue

        valid = active

        if active_observations == 0:
            pump_results.append(
                PumpCurveResult(
                    pump_name=str(pump_name),
                    curve_name=curve_name,
                    evaluable=True,
                    passed=True,
                    active_observations=0,
                    exceedance_observations=0,
                    curve_maximum_flow_m3s=curve_maximum_flow,
                    maximum_active_flow_m3s=0.0,
                    maximum_allowed_flow_m3s=None,
                    maximum_flow_ratio=0.0,
                    critical_time=None,
                )
            )
            continue

        active_flow = flow.loc[valid]
        active_allowed = allowed_flow.loc[valid]
        ratio = active_flow / active_allowed

        exceeded = ratio.gt(1.0 + tolerance)
        exceedance_observations = int(exceeded.sum())
        critical_time = ratio.idxmax()

        pump_results.append(
            PumpCurveResult(
                pump_name=str(pump_name),
                curve_name=curve_name,
                evaluable=True,
                passed=exceedance_observations == 0,
                active_observations=active_observations,
                exceedance_observations=exceedance_observations,
                curve_maximum_flow_m3s=curve_maximum_flow,
                maximum_active_flow_m3s=float(
                    active_flow.loc[critical_time]
                ),
                maximum_allowed_flow_m3s=float(
                    active_allowed.loc[critical_time]
                ),
                maximum_flow_ratio=float(
                    ratio.loc[critical_time]
                ),
                critical_time=critical_time,
            )
        )

    head_pumps_in_network = len(pump_results)
    head_pumps_evaluable = sum(
        result.evaluable for result in pump_results
    )

    evaluable_results = [
        result
        for result in pump_results
        if result.evaluable
    ]
    ratio_results = [
        result
        for result in evaluable_results
        if result.maximum_flow_ratio is not None
    ]

    governing_result = (
        max(
            ratio_results,
            key=lambda result: float(
                result.maximum_flow_ratio
            ),
        )
        if ratio_results
        else None
    )

    all_head_pumps_evaluable = (
        head_pumps_evaluable == head_pumps_in_network
    )

    all_pumps_passed = (
        all_head_pumps_evaluable
        and all(result.passed for result in pump_results)
    )

    return AllPumpCurveResult(
        head_pumps_in_network=head_pumps_in_network,
        head_pumps_evaluable=head_pumps_evaluable,
        all_head_pumps_evaluable=all_head_pumps_evaluable,
        all_pumps_passed=all_pumps_passed,
        number_of_pumps_exceeding_curves=sum(
            not result.passed
            for result in evaluable_results
        ),
        total_curve_exceedance_observations=sum(
            result.exceedance_observations
            for result in evaluable_results
        ),
        governing_pump_name=(
            governing_result.pump_name
            if governing_result is not None
            else None
        ),
        maximum_pump_flow_ratio=(
            governing_result.maximum_flow_ratio
            if governing_result is not None
            else None
        ),
        pump_results=tuple(pump_results),
    )
