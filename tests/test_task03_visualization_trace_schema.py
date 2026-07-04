import json
import subprocess
import sys

import pytest

from pirl_navrl.evaluation.rollout_recorder import RolloutJsonlWriter
from tests.test_rollout_recorder import make_step_record


def test_task03_viewer_trace_schema_contains_required_fields(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    metadata = {
        "platform_id": "diagnostic_kinematic_env",
        "scenario_id": "task03_static_nav_v0",
        "seed": 0,
        "policy_id": "goal_seeking_velocity_debug",
        "scenario": {
            "start": [-4.0, 0.0, 1.0],
            "goal": [4.0, 0.0, 1.0],
            "bounds": {"x": [-5.0, 5.0], "y": [-5.0, 5.0], "z": [0.0, 3.0]},
            "static_obstacles": [],
            "dynamic_obstacles": [],
        },
    }
    with RolloutJsonlWriter(path, metadata) as writer:
        writer.write_step(make_step_record())

    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["record_type"] == "metadata"
    assert records[0]["scenario"]["bounds"]["x"] == [-5.0, 5.0]
    assert records[1]["record_type"] == "step"
    assert "position" in records[1]
    assert "action" in records[1]
    assert "goal" in records[1]


def test_task03_viewer_direct_mode_does_not_require_gui(tmp_path) -> None:
    pytest.importorskip("pybullet")
    path = tmp_path / "trace.jsonl"
    metadata = {
        "platform_id": "diagnostic_kinematic_env",
        "scenario_id": "task03_static_nav_v0",
        "seed": 0,
        "policy_id": "goal_seeking_velocity_debug",
        "scenario": {
            "start": [-4.0, 0.0, 1.0],
            "goal": [4.0, 0.0, 1.0],
            "bounds": {"x": [-5.0, 5.0], "y": [-5.0, 5.0], "z": [0.0, 3.0]},
            "static_obstacles": [],
            "dynamic_obstacles": [],
        },
    }
    with RolloutJsonlWriter(path, metadata) as writer:
        writer.write_step(make_step_record())

    subprocess.run(
        [sys.executable, "scripts/view_task03_rollout.py", "--trace", str(path), "--direct"],
        check=True,
    )

    assert not list(tmp_path.glob("*.mp4"))
    assert not list(tmp_path.glob("*.gif"))
