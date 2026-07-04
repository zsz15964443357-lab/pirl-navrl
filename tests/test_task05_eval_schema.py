import json

import pytest


def test_task05_random_eval_writes_rollout_schema(tmp_path) -> None:
    pytest.importorskip("gym_pybullet_drones")
    from pirl_navrl.training.eval import run_task05_eval

    output = tmp_path / "task05_eval.jsonl"
    run_task05_eval(
        output_path=output,
        curriculum_level="level_0_no_obstacle_short",
        seed=3,
        random_policy=True,
        max_steps=2,
    )

    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert records[0]["record_type"] == "metadata"
    assert records[0]["task_id"] == "TASK_05"
    assert records[0]["policy_id"] == "random_policy_debug"
    assert records[0]["checkpoint_path"] is None
    assert records[0]["curriculum_level"] == "level_0_no_obstacle_short"
    assert records[1]["record_type"] == "initial_state"
    assert records[1]["task_id"] == "TASK_05"
    assert records[2]["record_type"] == "step"
    assert "platform_terminated" in records[2]
    assert "platform_truncated" in records[2]
    assert records[-1]["record_type"] == "summary"
    assert records[-1]["output_type"] == "diagnostic"
