from pathlib import Path

from pirl_navrl.scenarios.curriculum import load_curriculum_config
from pirl_navrl.training.sb3_ppo_debug import load_training_config


def test_task05_curriculum_config_schema() -> None:
    config = load_curriculum_config("configs/task05_curriculum_levels.json")

    assert set(config.levels) == {
        "level_0_no_obstacle_short",
        "level_1_no_obstacle_long",
        "level_2_static_obstacle_easy",
    }
    assert config.arena_bounds.x == (-5.0, 5.0)
    assert config.collision_radius > 0.0


def test_task05_ppo_debug_training_config_schema() -> None:
    config = load_training_config("configs/task05_ppo_debug_train.json")

    assert config.task_id == "TASK_05"
    assert config.output_type == "diagnostic_training"
    assert config.curriculum_level == "level_0_no_obstacle_short"
    assert 10000 <= config.total_timesteps <= 50000
    assert config.ppo["policy"] == "MlpPolicy"
    assert config.ppo["n_steps"] in {512, 1024}
    assert str(config.output_root).startswith("outputs/task05")
    assert "results" not in Path(config.output_root).parts
