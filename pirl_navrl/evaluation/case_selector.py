"""Case selection for TASK_06 diagnostic rollouts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pirl_navrl.analysis.rollout_metrics import compute_rollout_metrics


def select_task06_cases(trace_paths: list[str | Path]) -> dict[str, Any]:
    metrics = [compute_rollout_metrics(path) for path in trace_paths]
    if not metrics:
        raise ValueError("at least one trace is required for TASK_06 case selection")
    successes = [item for item in metrics if item["success"] and not item["collision"]]
    if successes:
        best = sorted(successes, key=lambda item: (item["final_distance_to_goal"], item["path_length"]))[0]
        best_case_type = "success_case"
        reason = "success_found"
    else:
        best = sorted(metrics, key=lambda item: (item["collision"], item["final_distance_to_goal"], -item["min_clearance"]))[0]
        best_case_type = "best_non_success_case"
        reason = "no_success_found"
    failures = [item for item in metrics if item["collision"] or item["timeout"] or not item["success"]]
    if failures:
        failure = sorted(failures, key=lambda item: (not item["collision"], item["final_distance_to_goal"]))[0]
        failure_case = {
            **failure,
            "case_type": "failure_case",
            "failure_type": classify_failure(failure),
            "failure_step": failure.get("steps"),
            "suspected_cause": suspected_cause(failure),
            "next_suggested_fix": next_suggested_fix(failure),
        }
    else:
        failure_case = {
            **best,
            "case_type": "no_failure_case",
            "failure_type": "none",
            "failure_step": None,
            "suspected_cause": "all selected rollouts satisfied strict success criteria",
            "next_suggested_fix": "increase obstacle count or scenario complexity after gate review",
        }
    return {
        "case_type": best_case_type,
        "reason": reason,
        "best_case": {**best, "case_type": best_case_type, "reason": reason},
        "failure_case": failure_case,
    }


def classify_failure(metrics: dict[str, Any]) -> str:
    trace_path = str(metrics.get("trace_path", ""))
    if metrics.get("collision"):
        return "collision_failure"
    if metrics.get("min_clearance", 1.0) < 0.1:
        return "near_miss_failure"
    if "latent_dynamic" in trace_path and metrics.get("timeout"):
        return "latent_trigger_failure"
    if "dynamic" in trace_path and metrics.get("timeout"):
        return "dynamic_late_reaction_failure"
    if metrics.get("path_length", 0.0) > 20.0:
        return "control_instability_failure"
    if metrics.get("timeout"):
        return "timeout_failure"
    return "timeout_failure"


def suspected_cause(metrics: dict[str, Any]) -> str:
    if metrics.get("collision"):
        return "policy entered obstacle safety radius"
    if metrics.get("timeout"):
        return "policy did not reach goal before max_steps"
    return "diagnostic rollout did not satisfy success criteria"


def next_suggested_fix(metrics: dict[str, Any]) -> str:
    failure_type = classify_failure(metrics)
    if failure_type in {"dynamic_late_reaction_failure", "latent_trigger_failure"}:
        return "inspect dynamic obstacle features and increase dynamic risk shaping"
    if failure_type == "near_miss_failure":
        return "increase clearance reward and verify obstacle scaling"
    return "verify reward progress signal, action scaling, and VecNormalize settings"


def write_case_selection_summary(trace_paths: list[str | Path], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(select_task06_cases(trace_paths), indent=2, sort_keys=True), encoding="utf-8")
    return output
