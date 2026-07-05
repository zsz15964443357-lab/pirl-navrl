import json
from pathlib import Path


def test_task06_training_configs_are_diagnostic_and_ignored_output() -> None:
    for path in [
        Path("configs/task06_static_ppo.json"),
        Path("configs/task06_dynamic_ppo.json"),
        Path("configs/task06_latent_dynamic_ppo.json"),
        Path("configs/task06_navrl_style_static_ppo.json"),
        Path("configs/task06_navrl_style_dynamic_ppo.json"),
        Path("configs/task06_navrl_style_latent_dynamic_ppo.json"),
    ]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["task_id"] == "TASK_06"
        assert payload["output_type"] == "diagnostic_training"
        assert payload["output_root"] == "outputs/task06"
        assert payload["total_timesteps"] <= payload["max_timesteps"]
        assert payload["curriculum_level"]
        assert payload["reward_profile"] in {"static_avoidance", "dynamic_avoidance", "latent_risk"}
        assert payload.get("observation_style", "flat") in {"flat", "navrl_style"}
        if payload.get("observation_style") == "navrl_style":
            assert payload["ppo"]["policy"] == "MultiInputPolicy"
            assert payload["ppo"]["feature_extractor"] == "navrl_style"
            assert payload["max_speed"] == 2.0
            assert payload["num_envs"] >= 4
            assert payload["vec_env_type"] in {"dummy", "subproc"}
            assert payload["total_timesteps"] >= 1_000_000
            assert payload["curriculum_level"] in payload["curriculum_levels"]


def test_task06_case_selection_config_schema() -> None:
    payload = json.loads(Path("configs/task06_case_selection.json").read_text(encoding="utf-8"))

    assert payload["task_id"] == "TASK_06"
    assert payload["output_type"] == "diagnostic_case_selection_config"
    assert payload["case_output_root"] == "outputs/task06"
    assert "latent_trigger_failure" in payload["failure_types"]
