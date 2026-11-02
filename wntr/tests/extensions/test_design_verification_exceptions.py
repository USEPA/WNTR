"""Focused validation tests for the design-verification extension.

These tests intentionally use standard Python exception categories rather
than private helper functions or extension-specific exception classes.
"""

import pandas as pd
import pytest
import wntr

from wntr.extensions.design_verification import (
    HydraulicScenario,
    PipeDesign,
    apply_pipe_design,
    audit_head_pump_curves,
    evaluate_minimum_pressure,
    run_verification_batch,
)


pytestmark = pytest.mark.extensions


def _valid_scenario():
    """Return a minimal scenario using WNTR's native Options class."""
    options = wntr.network.Options()
    options.time.duration = 0
    options.time.hydraulic_timestep = 3600
    options.time.report_timestep = 3600
    options.hydraulic.demand_model = "DD"

    return HydraulicScenario(
        name="Baseline",
        options=options,
    )


def test_constraint_validation_raises_value_error():
    """Reject a non-finite minimum-pressure requirement."""
    pressure = pd.DataFrame(
        data=[[20.0]],
        columns=["J1"],
    )

    with pytest.raises(ValueError):
        evaluate_minimum_pressure(
            pressure=pressure,
            minimum_pressure_m=float("nan"),
        )


def test_design_validation_raises_value_error():
    """Reject a pipe design containing no diameter changes."""
    wn = wntr.network.WaterNetworkModel()

    design = PipeDesign(
        name="Empty design",
        diameters_m={},
    )

    with pytest.raises(ValueError):
        apply_pipe_design(
            wn=wn,
            design=design,
        )


def test_empty_design_batch_raises_assertion():
    """Reject an empty design collection."""
    wn = wntr.network.WaterNetworkModel()

    with pytest.raises(AssertionError):
        run_verification_batch(
            wn=wn,
            scenarios=[_valid_scenario()],
            designs=[],
            simulators="WNTRSimulator",
        )


def test_empty_scenario_batch_raises_assertion():
    """Reject an empty scenario collection."""
    wn = wntr.network.WaterNetworkModel()

    with pytest.raises(AssertionError):
        run_verification_batch(
            wn=wn,
            scenarios=[],
            simulators="WNTRSimulator",
        )


def test_empty_simulator_batch_raises_assertion():
    """Reject an empty simulator collection."""
    wn = wntr.network.WaterNetworkModel()

    with pytest.raises(AssertionError):
        run_verification_batch(
            wn=wn,
            scenarios=[_valid_scenario()],
            simulators=[],
        )


def test_unsupported_simulator_raises_assertion():
    """Reject simulator names outside WNTR's supported class names."""
    wn = wntr.network.WaterNetworkModel()

    with pytest.raises(AssertionError):
        run_verification_batch(
            wn=wn,
            scenarios=[_valid_scenario()],
            simulators=["unsupported"],
            continue_on_error=False,
        )


@pytest.mark.parametrize(
    "tolerance",
    [
        -1.0,
        float("nan"),
        float("inf"),
        "invalid",
    ],
)
def test_invalid_pump_tolerance_raises_value_error(
    tolerance,
):
    """Reject invalid pump-curve relative tolerances."""
    wn = wntr.network.WaterNetworkModel()
    flowrate = pd.DataFrame(index=[0])

    with pytest.raises(ValueError):
        audit_head_pump_curves(
            network=wn,
            flowrate=flowrate,
            relative_tolerance=tolerance,
        )
