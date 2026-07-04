import json
from pathlib import Path


def test_task03_debug_config_schema() -> None:
    config = json.loads(Path("configs/task03_static_nav_debug.json").read_text(encoding="utf-8"))

    assert config["task_id"] == "TASK_03"
    assert config["output_type"] == "diagnostic"
    assert config["scenario_id"] == "task03_static_nav_v0"
    assert config["seed"] == 0
    assert config["policy_id"] == "goal_seeking_velocity_debug"
    assert config["platform_id"] == "diagnostic_kinematic_env"
    assert config["output_path"].endswith(".jsonl")
    assert config["visualize"] is False
