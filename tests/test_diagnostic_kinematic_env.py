from pirl_navrl.platforms.diagnostic_kinematic_env import DiagnosticKinematicEnv
from pirl_navrl.scenarios.core import Bounds3D, ObstacleConfig, ScenarioConfig, make_task03_static_nav_v0


def test_diagnostic_env_reset_and_step_updates_position() -> None:
    scenario = make_task03_static_nav_v0(seed=0)
    env = DiagnosticKinematicEnv(max_speed=1.0)

    observation = env.reset(scenario)
    assert observation["position"] == scenario.start

    observation, _reward, terminated, truncated, info = env.step((1.0, 0.0, 0.0))

    assert observation["position"][0] > scenario.start[0]
    assert info["velocity"] == (1.0, 0.0, 0.0)
    assert not terminated
    assert not truncated


def test_diagnostic_env_reports_collision_near_obstacle() -> None:
    scenario = ScenarioConfig(
        scenario_id="collision_test",
        seed=0,
        start=(0.0, 0.0, 1.0),
        goal=(2.0, 0.0, 1.0),
        bounds=Bounds3D(x=(-1.0, 3.0), y=(-1.0, 1.0), z=(0.0, 2.0)),
        static_obstacles=(
            ObstacleConfig(
                obstacle_id="near_sphere",
                kind="sphere",
                position=(0.1, 0.0, 1.0),
                radius=0.4,
            ),
        ),
        dynamic_obstacles=(),
        max_steps=10,
        dt=0.1,
        success_radius=0.2,
        collision_radius=0.2,
    )
    env = DiagnosticKinematicEnv(max_speed=1.0)
    env.reset(scenario)

    _observation, _reward, terminated, _truncated, info = env.step((0.0, 0.0, 0.0))

    assert terminated
    assert info["collision"] is True


def test_diagnostic_env_reports_success_near_goal() -> None:
    scenario = ScenarioConfig(
        scenario_id="success_test",
        seed=0,
        start=(0.0, 0.0, 1.0),
        goal=(0.05, 0.0, 1.0),
        bounds=Bounds3D(x=(-1.0, 1.0), y=(-1.0, 1.0), z=(0.0, 2.0)),
        static_obstacles=(),
        dynamic_obstacles=(),
        max_steps=10,
        dt=0.1,
        success_radius=0.2,
        collision_radius=0.2,
    )
    env = DiagnosticKinematicEnv(max_speed=1.0)
    env.reset(scenario)

    _observation, _reward, terminated, _truncated, info = env.step((0.0, 0.0, 0.0))

    assert terminated
    assert info["success"] is True
