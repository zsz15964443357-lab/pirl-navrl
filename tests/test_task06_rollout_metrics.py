import json

from pirl_navrl.analysis.rollout_metrics import aggregate_rollout_metrics, compute_rollout_metrics


def _write_trace(path, *, success=False, collision=False, timeout=True, final_distance=1.2, min_clearance=0.4):
    records = [
        {"record_type": "metadata", "scenario_group": "static", "scenario": {"collision_radius": 0.35}},
        {"record_type": "initial_state", "position": [0, 0, 1], "distance_to_goal": 2.0},
        {
            "record_type": "step",
            "position": [1, 0, 1],
            "action": [1, 0, 0],
            "distance_to_goal": final_distance,
            "min_clearance": min_clearance,
        },
        {
            "record_type": "summary",
            "steps": 1,
            "final_distance_to_goal": final_distance,
            "min_clearance": min_clearance,
            "success": success,
            "collision": collision,
            "timeout": timeout,
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")


def test_task06_compute_rollout_metrics(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    _write_trace(path, final_distance=0.8, min_clearance=0.5)

    metrics = compute_rollout_metrics(path)

    assert metrics["steps"] == 1
    assert metrics["final_distance_to_goal"] == 0.8
    assert metrics["min_clearance"] == 0.5
    assert metrics["path_length"] == 0.0
    assert metrics["mean_action_norm"] == 1.0


def test_task06_aggregate_rollout_metrics(tmp_path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    _write_trace(first, success=True, timeout=False, final_distance=0.2)
    _write_trace(second, collision=True, timeout=False, final_distance=1.5)

    summary = aggregate_rollout_metrics([first, second], scenario_group="static", checkpoint="ckpt.zip")

    assert summary["scenario_group"] == "static"
    assert summary["num_eval_episodes"] == 2
    assert summary["success_count"] == 1
    assert summary["collision_count"] == 1
    assert summary["checkpoint"] == "ckpt.zip"


def test_task06_rollout_metrics_enforces_gate_clearance(tmp_path) -> None:
    path = tmp_path / "too_close_success.jsonl"
    _write_trace(path, success=True, collision=False, timeout=False, final_distance=0.2, min_clearance=0.32)

    metrics = compute_rollout_metrics(path)

    assert metrics["collision"] is True
    assert metrics["success"] is False
    assert metrics["collision_radius"] == 0.35
