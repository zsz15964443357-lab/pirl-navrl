from pirl_navrl.scenarios.core import Bounds3D, make_task03_static_nav_v0


def test_task03_scenario_config_builds_expected_static_scene() -> None:
    scenario = make_task03_static_nav_v0(seed=7)

    assert scenario.scenario_id == "task03_static_nav_v0"
    assert scenario.seed == 7
    assert scenario.start == (-4.0, 0.0, 1.0)
    assert scenario.goal == (4.0, 0.0, 1.0)
    assert scenario.bounds == Bounds3D(x=(-5.0, 5.0), y=(-5.0, 5.0), z=(0.0, 3.0))
    assert len(scenario.static_obstacles) == 3
    assert scenario.dynamic_obstacles == ()
    assert scenario.max_steps == 100
    assert scenario.dt > 0.0


def test_task03_scenario_seed_is_controlled() -> None:
    left = make_task03_static_nav_v0(seed=3)
    right = make_task03_static_nav_v0(seed=3)
    other = make_task03_static_nav_v0(seed=4)

    assert left == right
    assert left.seed != other.seed
