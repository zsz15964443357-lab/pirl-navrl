"""JSONL rollout recorder for diagnostic pipelines."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True)
class RolloutInitialStateRecord:
    task_id: str
    output_type: str
    platform_id: str
    scenario_id: str
    seed: int
    policy_id: str
    step: int
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    goal: tuple[float, float, float]
    distance_to_goal: float
    min_clearance: float
    collision: bool
    success: bool
    timeout: bool
    record_type: str = "initial_state"

    def __post_init__(self) -> None:
        if self.output_type != "diagnostic":
            raise ValueError("diagnostic rollout initial states must use output_type='diagnostic'")


@dataclass(frozen=True)
class RolloutStepRecord:
    task_id: str
    output_type: str
    platform_id: str
    scenario_id: str
    seed: int
    policy_id: str
    step: int
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    goal: tuple[float, float, float]
    action: tuple[float, float, float]
    distance_to_goal: float
    min_clearance: float
    collision: bool
    success: bool
    timeout: bool
    safety_collision: bool | None = None
    physical_collision: bool | None = None
    custom_obstacles_physical: bool | None = None
    obstacle_body_ids: dict[str, int] | None = None
    platform_terminated: bool | None = None
    platform_truncated: bool | None = None
    onboard_camera: dict[str, Any] | None = None
    record_type: str = "step"

    def __post_init__(self) -> None:
        if self.output_type != "diagnostic":
            raise ValueError("diagnostic rollout records must use output_type='diagnostic'")


@dataclass(frozen=True)
class RolloutSummary:
    task_id: str
    output_type: str
    platform_id: str
    scenario_id: str
    seed: int
    policy_id: str
    steps: int
    final_distance_to_goal: float
    min_clearance: float
    collision: bool
    success: bool
    timeout: bool
    record_type: str = "summary"

    def __post_init__(self) -> None:
        if self.output_type != "diagnostic":
            raise ValueError("diagnostic rollout summaries must use output_type='diagnostic'")


class RolloutJsonlWriter:
    """Write diagnostic metadata, step records, and summary records as JSONL."""

    def __init__(self, path: str | Path, metadata: dict[str, Any]) -> None:
        self.path = Path(path)
        self.metadata = {"output_type": "diagnostic", **metadata}
        if self.metadata["output_type"] != "diagnostic":
            raise ValueError("diagnostic rollout output_type must be diagnostic")
        self.records = 0

    def __enter__(self) -> "RolloutJsonlWriter":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("w", encoding="utf-8")
        self.write({"record_type": "metadata", **self.metadata})
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.handle.close()

    def write_initial_state(self, record: RolloutInitialStateRecord) -> None:
        self.write(record)

    def write_step(self, record: RolloutStepRecord) -> None:
        self.write(record)

    def write_summary(self, summary: RolloutSummary) -> None:
        self.write(summary)

    def write(self, payload: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **_jsonable(payload),
        }
        self.handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.handle.flush()
        self.records += 1
