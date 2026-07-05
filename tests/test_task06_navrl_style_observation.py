import numpy as np
import pytest

from pirl_navrl.platforms.gym_pybullet_drones.feature_scaling import (
    navrl_style_observation,
    vec_from_navrl_goal_frame,
    vec_to_navrl_goal_frame,
)
from pirl_navrl.scenarios.dynamic_curriculum import make_task06_scenario
from pirl_navrl.scenarios.core import Bounds3D, ObstacleConfig, ScenarioConfig


def test_task06_navrl_style_observation_contract() -> None:
    scenario = make_task06_scenario("dynamic_crossing_easy", seed=0)
    obs_dict = {
        "position": np.asarray(scenario.start, dtype=np.float32),
        "velocity": np.zeros(3, dtype=np.float32),
        "goal": np.asarray(scenario.goal, dtype=np.float32),
        "relative_goal": np.asarray(scenario.goal, dtype=np.float32) - np.asarray(scenario.start, dtype=np.float32),
        "distance_to_goal": 1.0,
        "nearest_obstacle_relative_position": np.zeros(3, dtype=np.float32),
        "nearest_obstacle_distance": 1.0,
        "min_clearance": 1.0,
        "step_fraction": 0.0,
    }

    obs = navrl_style_observation(obs_dict=obs_dict, scenario=scenario, elapsed=0.0)

    assert obs["state"].shape == (8,)
    assert obs["lidar"].shape == (1, 36, 4)
    assert obs["direction"].shape == (1, 3)
    assert obs["dynamic_obstacle"].shape == (1, 5, 10)
    assert np.all(np.isfinite(obs["state"]))
    assert 0.0 <= float(obs["lidar"].min()) <= float(obs["lidar"].max()) <= 1.0


def test_task06_navrl_goal_frame_round_trip() -> None:
    relative_goal = np.asarray([0.0, 3.0, 0.4], dtype=np.float32)
    world_vector = np.asarray([0.2, 0.7, -0.1], dtype=np.float32)

    goal_frame = vec_to_navrl_goal_frame(world_vector, relative_goal)
    reconstructed = vec_from_navrl_goal_frame(goal_frame, relative_goal)

    np.testing.assert_allclose(reconstructed, world_vector, atol=1e-6)


def test_task06_navrl_style_observation_uses_pybullet_raycast_lidar() -> None:
    p = pytest.importorskip("pybullet")
    client = p.connect(p.DIRECT)
    try:
        collision = p.createCollisionShape(p.GEOM_SPHERE, radius=0.25, physicsClientId=client)
        p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            basePosition=[1.0, 0.0, 1.0],
            physicsClientId=client,
        )
        scenario = ScenarioConfig(
            scenario_id="task06_raycast_lidar_unit",
            seed=0,
            start=(0.0, 0.0, 1.0),
            goal=(3.0, 0.0, 1.0),
            bounds=Bounds3D(x=(-2.0, 4.0), y=(-2.0, 2.0), z=(0.0, 3.0)),
            static_obstacles=(
                ObstacleConfig(
                    obstacle_id="raycast_hit",
                    kind="sphere",
                    position=(1.0, 0.0, 1.0),
                    radius=0.25,
                ),
            ),
            dynamic_obstacles=(),
            max_steps=10,
            dt=0.1,
            success_radius=0.35,
            collision_radius=0.22,
        )
        obs_dict = {
            "position": np.asarray(scenario.start, dtype=np.float32),
            "velocity": np.zeros(3, dtype=np.float32),
            "goal": np.asarray(scenario.goal, dtype=np.float32),
            "relative_goal": np.asarray(scenario.goal, dtype=np.float32) - np.asarray(scenario.start, dtype=np.float32),
            "distance_to_goal": 3.0,
            "nearest_obstacle_relative_position": np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            "nearest_obstacle_distance": 1.0,
            "min_clearance": 0.75,
            "step_fraction": 0.0,
        }

        obs = navrl_style_observation(
            obs_dict=obs_dict,
            scenario=scenario,
            elapsed=0.0,
            pybullet_client=client,
        )

        assert obs["lidar"].shape == (1, 36, 4)
        assert float(obs["lidar"].max()) > 0.0
    finally:
        p.disconnect(client)
