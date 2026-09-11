"""Tests for automatic head-pump operating-curve auditing."""

from pathlib import Path

import pandas as pd
import pytest

import wntr
from wntr.extensions.design_verification.pumps import (
    audit_head_pump_curves,
)


pytestmark = pytest.mark.extensions


def _net3():
    network_path = (
        Path(wntr.__file__).resolve().parent
        / "library"
        / "networks"
        / "Net3.inp"
    )
    return wntr.network.WaterNetworkModel(network_path)


def _table(values_10, values_335):
    return pd.DataFrame(
        {
            "10": values_10,
            "335": values_335,
        },
        index=[0, 3600],
    )


def test_all_head_pumps_pass_within_curve_domains():
    network = _net3()

    result = audit_head_pump_curves(
        network,
        _table([0.10, 0.20], [0.50, 0.80]),
        status=_table([1, 1], [1, 1]),
        setting=_table([1.0, 1.0], [1.0, 1.0]),
    )

    assert result.head_pumps_in_network == 2
    assert result.head_pumps_evaluable == 2
    assert result.all_head_pumps_evaluable
    assert result.all_pumps_passed
    assert result.number_of_pumps_exceeding_curves == 0
    assert result.total_curve_exceedance_observations == 0


def test_all_head_pump_audit_detects_curve_exceedances():
    network = _net3()

    result = audit_head_pump_curves(
        network,
        _table([0.10, 0.30], [0.50, 0.90]),
        status=_table([1, 1], [1, 1]),
        setting=_table([1.0, 1.0], [1.0, 1.0]),
    )

    assert not result.all_pumps_passed
    assert result.number_of_pumps_exceeding_curves == 2
    assert result.total_curve_exceedance_observations == 2
    assert result.governing_pump_name == "10"
    assert result.maximum_pump_flow_ratio > 1.0


def test_pump_curve_limit_scales_with_operating_speed():
    network = _net3()

    result = audit_head_pump_curves(
        network,
        _table([0.10, 0.13], [0.40, 0.40]),
        status=_table([1, 1], [1, 1]),
        setting=_table([1.0, 0.5], [1.0, 1.0]),
    )

    details = {
        item.pump_name: item
        for item in result.pump_results
    }

    assert not details["10"].passed
    assert details["10"].exceedance_observations == 1
    assert details["10"].maximum_flow_ratio > 1.0
    assert details["335"].passed


def test_closed_pump_observations_are_not_curve_violations():
    network = _net3()

    result = audit_head_pump_curves(
        network,
        _table([0.30, 0.30], [0.90, 0.90]),
        status=_table([0, 0], [0, 0]),
        setting=_table([0.0, 0.0], [0.0, 0.0]),
    )

    assert result.all_pumps_passed
    assert result.total_curve_exceedance_observations == 0
    assert all(
        item.active_observations == 0
        for item in result.pump_results
    )

def test_single_point_curve_uses_generated_zero_head_flow():
    network = wntr.network.WaterNetworkModel()

    network.add_reservoir(
        "R1",
        base_head=100.0,
    )
    network.add_junction(
        "J1",
        base_demand=0.0,
        elevation=0.0,
    )
    network.add_curve(
        "curve1",
        "HEAD",
        [(0.10, 20.0)],
    )
    network.add_pump(
        "P1",
        "R1",
        "J1",
        pump_type="HEAD",
        pump_parameter="curve1",
    )

    flowrate = pd.DataFrame(
        {
            "P1": [0.15, 0.21],
        },
        index=[0, 3600],
    )
    status = pd.DataFrame(
        {
            "P1": [1, 1],
        },
        index=flowrate.index,
    )
    setting = pd.DataFrame(
        {
            "P1": [1.0, 1.0],
        },
        index=flowrate.index,
    )

    result = audit_head_pump_curves(
        network,
        flowrate,
        status=status,
        setting=setting,
    )

    pump_result = result.pump_results[0]

    assert pump_result.curve_maximum_flow_m3s == pytest.approx(
        0.20
    )
    assert pump_result.active_observations == 2
    assert pump_result.exceedance_observations == 1
    assert not pump_result.passed
    assert not result.all_pumps_passed

def test_active_pump_with_missing_flow_is_not_evaluable():
    network = _net3()

    result = audit_head_pump_curves(
        network,
        _table([0.10, float("nan")], [0.50, 0.80]),
        status=_table([1, 1], [1, 1]),
        setting=_table([1.0, 1.0], [1.0, 1.0]),
    )

    details = {
        item.pump_name: item
        for item in result.pump_results
    }
    pump_result = details["10"]

    assert not pump_result.evaluable
    assert not pump_result.passed
    assert pump_result.active_observations == 2
    assert pump_result.critical_time == 3600
    assert not result.all_head_pumps_evaluable
    assert not result.all_pumps_passed


def test_active_pump_with_invalid_speed_is_not_evaluable():
    network = _net3()

    result = audit_head_pump_curves(
        network,
        _table([0.10, 0.10], [0.50, 0.80]),
        status=_table([1, 1], [1, 1]),
        setting=_table([1.0, -0.5], [1.0, 1.0]),
    )

    details = {
        item.pump_name: item
        for item in result.pump_results
    }
    pump_result = details["10"]

    assert not pump_result.evaluable
    assert not pump_result.passed
    assert pump_result.active_observations == 2
    assert pump_result.critical_time == 3600
    assert not result.all_head_pumps_evaluable
    assert not result.all_pumps_passed
def test_active_pump_with_reverse_flow_is_not_evaluable():
    network = _net3()

    result = audit_head_pump_curves(
        network,
        _table([0.10, -0.05], [0.50, 0.80]),
        status=_table([1, 1], [1, 1]),
        setting=_table([1.0, 1.0], [1.0, 1.0]),
    )

    details = {
        item.pump_name: item
        for item in result.pump_results
    }
    pump_result = details["10"]

    assert not pump_result.evaluable
    assert not pump_result.passed
    assert pump_result.active_observations == 2
    assert pump_result.critical_time == 3600
    assert not result.all_head_pumps_evaluable
    assert not result.all_pumps_passed


@pytest.mark.parametrize(
    "invalid_status",
    [
        float("nan"),
        float("inf"),
        -1.0,
    ],
)
def test_invalid_pump_status_is_not_evaluable(
    invalid_status,
):
    """Reject missing, infinite, and negative pump-status values."""
    network = _net3()

    result = audit_head_pump_curves(
        network,
        _table([0.10, 0.10], [0.50, 0.80]),
        status=_table(
            [1.0, invalid_status],
            [1.0, 1.0],
        ),
        setting=_table(
            [1.0, 1.0],
            [1.0, 1.0],
        ),
    )

    details = {
        item.pump_name: item
        for item in result.pump_results
    }
    pump_result = details["10"]

    assert not pump_result.evaluable
    assert not pump_result.passed
    assert pump_result.active_observations == 1
    assert pump_result.critical_time == 3600
    assert not result.all_head_pumps_evaluable
    assert not result.all_pumps_passed
