"""Apply proposed pipe-design changes to a WNTR model."""

from __future__ import annotations

import copy
import math

from wntr.network import WaterNetworkModel
from wntr.utils.check_values import _check_positive_non_zero_float

from .exceptions import InvalidDesignError
from .models import PipeDesign


def apply_pipe_design(
    wn: WaterNetworkModel,
    design: PipeDesign,
) -> tuple[WaterNetworkModel, list[dict[str, float | str]]]:
    """Apply selected pipe-diameter changes to a copied network.

    The original WaterNetworkModel is not modified.

    Parameters
    ----------
    wn : WaterNetworkModel
        Original WNTR water-distribution network model.
    design : PipeDesign
        Proposed pipe-diameter changes in metres.

    Returns
    -------
    trial_wn : WaterNetworkModel
        Independent copy of the original network containing the
        proposed diameter changes.
    audit_records : list of dict
        Records containing each pipe's original and proposed diameter.

    Raises
    ------
    TypeError
        If wn is not a WaterNetworkModel or design is not a
        PipeDesign.
    ValueError
        If the design name is empty, the design contains no changes,
        or a proposed diameter is invalid.
    KeyError
        If a named pipe does not exist in the network.
    """
    if not isinstance(wn, WaterNetworkModel):
        raise TypeError(
            "wn must be a WNTR WaterNetworkModel."
        )

    if not isinstance(design, PipeDesign):
        raise TypeError(
            "design must be a PipeDesign."
        )

    if not design.name.strip():
        raise InvalidDesignError(
            "design name cannot be empty."
        )

    if not design.diameters_m:
        raise InvalidDesignError(
            "design must contain at least one pipe-diameter change."
        )

    # Work on an independent copy so the original network is protected.
    trial_wn = copy.deepcopy(wn)

    audit_records: list[dict[str, float | str]] = []

    for pipe_name, proposed_diameter in design.diameters_m.items():
        if pipe_name not in trial_wn.pipe_name_list:
            raise KeyError(
                f"Pipe {pipe_name!r} does not exist in the network."
            )

        try:
            new_diameter_m = _check_positive_non_zero_float(
                proposed_diameter,
                f"Diameter for pipe {pipe_name!r}",
            )
        except ValueError as error:
            raise InvalidDesignError(str(error)) from error

        if not math.isfinite(new_diameter_m):
            raise InvalidDesignError(
                f"Diameter for pipe {pipe_name!r} must be finite."
            )

        pipe = trial_wn.get_link(pipe_name)
        old_diameter_m = float(pipe.diameter)

        pipe.diameter = new_diameter_m

        audit_records.append(
            {
                "pipe_name": pipe_name,
                "old_diameter_m": old_diameter_m,
                "new_diameter_m": new_diameter_m,
            }
        )

    return trial_wn, audit_records
