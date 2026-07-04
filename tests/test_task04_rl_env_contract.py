import numpy as np
import pytest
from dataclasses import replace


def test_task04_rl_env_reset_step_contract() -> None:
    pytest.importorskip("gym_pybullet_drones")
    from pirl_navrl.platforms.gym_pybullet_drones.rl_env import Task04GymPybulletDronesRLEnv

    env = Task04GymPybulletDronesRLEnv(gui=False)
    try:
        obs, info = env.reset(seed=0)
        assert env.observation_space.contains(obs)
        assert env.action_space.shape == (3,)
        assert info["platform_id"] == "gym_pybullet_drones_velocity_adapter_debug"

        next_obs, reward, terminated, truncated, info = env.step(np.zeros(3, dtype=np.float32))

        assert env.observation_space.contains(next_obs)
        assert isinstance(float(reward), float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert terminated == bool(info["success"] or info["collision"])
        assert truncated == bool(info["timeout"])
        assert "platform_terminated" in info
        assert "platform_truncated" in info
        assert "reward_terms" in info
        assert info["scenario_id"] == "task03_static_nav_v0"
        assert info["custom_obstacles_physical"] is True
        assert info["obstacle_body_ids"]
        assert "physical_collision" in info
        assert "safety_collision" in info
    finally:
        env.close()


def test_task04_adapter_creates_pybullet_obstacle_bodies() -> None:
    pytest.importorskip("gym_pybullet_drones")
    from pirl_navrl.platforms.gym_pybullet_drones.simple_adapter import GymPybulletDronesSimpleAdapter
    from pirl_navrl.scenarios.core import make_task03_static_nav_v0

    scenario = make_task03_static_nav_v0(seed=0)
    adapter = GymPybulletDronesSimpleAdapter(gui=False)
    try:
        adapter.reset(scenario)

        assert len(adapter.obstacle_body_ids) == len(scenario.static_obstacles)
        assert adapter.pybullet_client is not None
        assert adapter.drone_body_id is not None
    finally:
        adapter.close()


def test_task04_rl_env_reset_preserves_scenario_overrides() -> None:
    pytest.importorskip("gym_pybullet_drones")
    from pirl_navrl.platforms.gym_pybullet_drones.rl_env import Task04GymPybulletDronesRLEnv
    from pirl_navrl.scenarios.core import make_task03_static_nav_v0

    scenario = replace(make_task03_static_nav_v0(seed=0), goal=(3.0, 2.0, 1.0), max_steps=12)
    env = Task04GymPybulletDronesRLEnv(scenario=scenario, gui=False)
    try:
        _obs, _info = env.reset(seed=5)

        assert env.scenario.seed == 5
        assert env.scenario.goal == (3.0, 2.0, 1.0)
        assert env.scenario.max_steps == 12
    finally:
        env.close()


def test_task04_rl_env_reports_onboard_camera_when_enabled() -> None:
    pytest.importorskip("gym_pybullet_drones")
    from pirl_navrl.platforms.gym_pybullet_drones.rl_env import Task04GymPybulletDronesRLEnv

    env = Task04GymPybulletDronesRLEnv(gui=False, enable_onboard_camera=True)
    try:
        _obs, _info = env.reset(seed=0)
        _next_obs, _reward, _terminated, _truncated, info = env.step(np.zeros(3, dtype=np.float32))

        assert info["onboard_camera"]["enabled"] is True
        assert info["onboard_camera"]["available"] is True
        assert info["onboard_camera"]["width"] > 0
        assert info["onboard_camera"]["height"] > 0
        assert np.isfinite(info["onboard_camera"]["rgb_mean"])
        assert np.isfinite(info["onboard_camera"]["depth_min"])
        assert np.isfinite(info["onboard_camera"]["depth_max"])
    finally:
        env.close()
