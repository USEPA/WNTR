import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, FiniteFloat, field_validator

# Define your allowed attack types here
ALLOWED_ATTACK_TYPES = {"valve_closure", "pipe_burst", "pump_failure", "pump_off"}


class ScenarioTiming(BaseModel):
    start_time_sec: FiniteFloat = Field(ge=0, description="Start time in seconds")
    duration_sec: FiniteFloat = Field(gt=0, description="Duration in seconds")


class WaterScenario(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    scenario_id: str
    name: str
    description: str = ""
    attack_type: str
    model_id: str
    target_components: list[str]
    timing: ScenarioTiming
    parameters: dict[str, Any]

    @field_validator("scenario_id", "model_id")
    @classmethod
    def validate_ids_not_empty(cls, v: str, info) -> str:
        """Rejects invalid or blank IDs/names."""
        if not v or not v.strip():
            raise ValueError(
                f"Field '{info.field_name}' cannot be empty or whitespace."
            )
        return v

    @field_validator("attack_type")
    @classmethod
    def validate_attack_type(cls, v: str) -> str:
        """Rejects unknown attack types."""
        if v not in ALLOWED_ATTACK_TYPES:
            raise ValueError(
                f"Unknown attack_type '{v}'. Must be one of: {', '.join(ALLOWED_ATTACK_TYPES)}"
            )
        return v

    def save_to_json(self, file_path: Path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load_from_json(cls, file_path: Path) -> "WaterScenario":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
