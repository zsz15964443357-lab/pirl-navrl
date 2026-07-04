import json
from pathlib import Path


def test_task04_debug_config_schema() -> None:
    config = json.loads(Path("configs/task04_gym_pybullet_static_nav_debug.json").read_text(encoding="utf-8"))

    assert config["task_id"] == "TASK_04"
    assert config["output_type"] == "diagnostic"
    assert config["scenario_id"] == "task03_static_nav_v0"
    assert config["seed"] == 0
    assert config["policy_id"] == "goal_seeking_velocity_debug"
    assert config["platform_id"] == "gym_pybullet_drones_velocity_adapter_debug"
    assert config["output_path"].endswith(".jsonl")
    assert config["max_speed"] > 0.0
    assert config["live_gui"] is False
    assert config["replay_gui"] is False
