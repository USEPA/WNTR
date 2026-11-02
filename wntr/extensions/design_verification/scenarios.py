"""Apply hydraulic simulation options to WNTR models."""

from __future__ import annotations

import copy

from wntr.network import WaterNetworkModel

from .models import HydraulicScenario


def apply_hydraulic_scenario(
    wn: WaterNetworkModel,
    scenario: HydraulicScenario,
) -> tuple[WaterNetworkModel, dict[str, object]]:
    """Apply hydraulic simulation options to an independent network copy.

    The verification scenario changes only the WNTR ``time`` and
    ``hydraulic`` simulation option groups. The original
    ``WaterNetworkModel`` is not modified.

    Parameters
    ----------
    wn : WaterNetworkModel
        Original WNTR water-distribution network model.
    scenario : HydraulicScenario
        Scenario containing the WNTR simulation options to apply.

    Returns
    -------
    scenario_wn : WaterNetworkModel
        Independent network copy containing the selected time and
        hydraulic simulation options.
    audit : dict
        Dictionary recording the original and applied simulation
        options.
    """
    assert isinstance(wn, WaterNetworkModel)
    assert isinstance(scenario, HydraulicScenario)
    assert isinstance(scenario.name, str)
    assert scenario.name.strip()

    scenario_wn = copy.deepcopy(wn)

    original_options = {
        "time": dict(scenario_wn.options.time),
        "hydraulic": dict(scenario_wn.options.hydraulic),
    }

    scenario_wn.options.time = copy.deepcopy(
        scenario.options.time
    )
    scenario_wn.options.hydraulic = copy.deepcopy(
        scenario.options.hydraulic
    )

    applied_options = {
        "time": dict(scenario_wn.options.time),
        "hydraulic": dict(scenario_wn.options.hydraulic),
    }

    audit = {
        "scenario_name": scenario.name.strip(),
        "original_options": original_options,
        "applied_options": applied_options,
    }

    return scenario_wn, audit
