"""Rollout metric aggregation for TASK_06 diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

TASK06_MIN_GATE_CLEARANCE = 0.35


def load_jsonl_records(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def compute_rollout_metrics(path: str | Path) -> dict[str, Any]:
    records = load_jsonl_records(path)
    metadata = next((record for record in records if record.get("record_type") == "metadata"), {})
    steps = [record for record in records if record.get("record_type") == "step"]
    summary = next((record for record in reversed(records) if record.get("record_type") == "summary"), {})
    path_length = 0.0
    last_position = None
    action_norms = []
    step_min_clearances = []
    for step in steps:
        position = np.asarray(step["position"], dtype=np.float32)
        if last_position is not None:
            path_length += float(np.linalg.norm(position - last_position))
        last_position = position
        if "action" in step:
            action_norms.append(float(np.linalg.norm(np.asarray(step["action"], dtype=np.float32))))
        if "min_clearance" in step:
            step_min_clearances.append(float(step["min_clearance"]))
    summary_min_clearance = float(summary.get("min_clearance", np.inf))
    min_clearance = min([summary_min_clearance, *step_min_clearances]) if step_min_clearances else summary_min_clearance
    collision_radius = _collision_radius_from_metadata(metadata)
    collision = bool(summary.get("collision", False) or min_clearance <= collision_radius)
    success = bool(summary.get("success", False) and not collision)
    return {
        "trace_path": str(path),
        "steps": len(steps),
        "success": success,
        "collision": collision,
        "timeout": bool(summary.get("timeout", False)),
        "final_distance_to_goal": float(summary.get("final_distance_to_goal", np.inf)),
        "min_clearance": float(min_clearance),
        "collision_radius": float(collision_radius),
        "path_length": float(path_length),
        "mean_action_norm": float(np.mean(action_norms)) if action_norms else 0.0,
    }


def _collision_radius_from_metadata(metadata: dict[str, Any]) -> float:
    scenario = metadata.get("scenario") if isinstance(metadata, dict) else None
    configured = None
    if isinstance(scenario, dict):
        configured = scenario.get("collision_radius")
    if configured is None:
        configured = metadata.get("collision_radius") if isinstance(metadata, dict) else None
    try:
        configured_radius = float(configured)
    except (TypeError, ValueError):
        configured_radius = TASK06_MIN_GATE_CLEARANCE
    return max(TASK06_MIN_GATE_CLEARANCE, configured_radius)


def aggregate_rollout_metrics(paths: list[str | Path], *, scenario_group: str, checkpoint: str | None = None) -> dict[str, Any]:
    metrics = [compute_rollout_metrics(path) for path in paths]
    if not metrics:
        return {
            "scenario_group": scenario_group,
            "checkpoint": checkpoint,
            "num_eval_episodes": 0,
            "success_count": 0,
            "collision_count": 0,
            "timeout_count": 0,
            "mean_final_distance": None,
            "mean_min_clearance": None,
            "mean_path_length": None,
            "mean_action_norm": None,
            "debug_learning_effect": "not_evaluated",
            "notes": "no rollout traces provided",
        }
    return {
        "scenario_group": scenario_group,
        "checkpoint": checkpoint,
        "num_eval_episodes": len(metrics),
        "success_count": sum(int(item["success"]) for item in metrics),
        "collision_count": sum(int(item["collision"]) for item in metrics),
        "timeout_count": sum(int(item["timeout"]) for item in metrics),
        "mean_final_distance": float(np.mean([item["final_distance_to_goal"] for item in metrics])),
        "mean_min_clearance": float(np.mean([item["min_clearance"] for item in metrics])),
        "mean_path_length": float(np.mean([item["path_length"] for item in metrics])),
        "mean_action_norm": float(np.mean([item["mean_action_norm"] for item in metrics])),
        "debug_learning_effect": "diagnostic_only",
        "notes": "TASK_06 summary is not a formal benchmark success rate.",
    }
