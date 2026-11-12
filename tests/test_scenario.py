import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ward.scenario import WaterScenario

EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "ward"
    / "scenarios"
    / "pump_poweroff_basic.json"
)


def test_load_rejects_unsupported_scenario_version():
    path = Path(__file__).with_name("fixtures") / "scenario_unsupported_version.json"

    with pytest.raises(ValidationError, match="schema_version"):
        WaterScenario.load_from_json(path)


@pytest.mark.parametrize(
    ("field", "value", "location"),
    [
        ("name", None, ("name",)),
        ("scenario_id", " ", ("scenario_id",)),
        ("model_id", "", ("model_id",)),
        ("attack_type", "unknown", ("attack_type",)),
        ("start_time_sec", -1, ("timing", "start_time_sec")),
        ("duration_sec", 0, ("timing", "duration_sec")),
        ("start_time_sec", "NaN", ("timing", "start_time_sec")),
        ("duration_sec", "Infinity", ("timing", "duration_sec")),
    ],
)
def test_load_identifies_invalid_fields(tmp_path, field, value, location):
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    if value is None:
        del data[field]
    elif len(location) == 2:
        data["timing"][field] = value
    else:
        data[field] = value
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValidationError) as error:
        WaterScenario.load_from_json(path)

    assert error.value.errors()[0]["loc"] == location


@pytest.mark.parametrize("omit_version", [False, True])
def test_supported_scenario_round_trips(tmp_path, omit_version):
    path = tmp_path / "scenario.json"
    source = EXAMPLE
    if omit_version:
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del data["schema_version"]
        path.write_text(json.dumps(data), encoding="utf-8")
        source = path

    scenario = WaterScenario.load_from_json(source)
    scenario.save_to_json(path)

    assert scenario.schema_version == "1.0"
    assert WaterScenario.load_from_json(path) == scenario
