import math

from pirl_navrl.scenarios.dynamic_curriculum import (
    load_task06_curriculum_config,
    make_task06_scenario,
    task06_level_group,
)


def _dist_xy(left, right) -> float:
    return math.dist(left[:2], right[:2])


def test_task06_curriculum_has_required_groups() -> None:
    config = load_task06_curriculum_config("configs/task06_multiscenario_curriculum.json")

    groups = {level.scenario_group for level in config.levels.values()}
    assert {"static", "dynamic", "latent_dynamic", "mixed_static_dynamic"} <= groups


def test_task06_static_dynamic_latent_scenarios_are_seeded_and_valid() -> None:
    levels = ["static_obstacle_easy", "dynamic_crossing_easy", "latent_dynamic_easy"]
    for level in levels:
        first = make_task06_scenario(level, seed=7)
        second = make_task06_scenario(level, seed=7)
        assert first.to_dict() == second.to_dict()
        assert first.bounds.contains(first.start)
        assert first.bounds.contains(first.goal)
        assert _dist_xy(first.start, first.goal) > first.success_radius


def test_task06_dynamic_and_latent_obstacles_have_motion_contract() -> None:
    dynamic = make_task06_scenario("dynamic_crossing_easy", seed=0)
    latent = make_task06_scenario("latent_dynamic_easy", seed=0)

    assert task06_level_group("dynamic_crossing_easy") == "dynamic"
    assert len(dynamic.dynamic_obstacles) == 1
    assert dynamic.dynamic_obstacles[0].motion_type == "linear"
    assert dynamic.dynamic_obstacles[0].start_time == 0.0
    assert task06_level_group("latent_dynamic_easy") == "latent_dynamic"
    assert len(latent.dynamic_obstacles) == 1
    assert latent.dynamic_obstacles[0].motion_type == "linear"
    assert latent.dynamic_obstacles[0].start_time > 0.0
    assert latent.dynamic_obstacles[0].position_at(0.0) == latent.dynamic_obstacles[0].position
    assert latent.dynamic_obstacles[0].position_at(latent.dynamic_obstacles[0].start_time + 1.0) != latent.dynamic_obstacles[0].position


def test_task06_easy_dynamic_levels_isolate_moving_obstacles() -> None:
    dynamic = make_task06_scenario("dynamic_crossing_easy", seed=3)
    latent = make_task06_scenario("latent_dynamic_easy", seed=3)
    mixed = make_task06_scenario("mixed_static_dynamic_easy", seed=3)

    assert len(dynamic.static_obstacles) == 0
    assert len(dynamic.dynamic_obstacles) == 1
    assert len(latent.static_obstacles) == 0
    assert len(latent.dynamic_obstacles) == 1
    assert len(mixed.static_obstacles) > 0
    assert len(mixed.dynamic_obstacles) == 1


def test_task06_static_obstacles_are_not_on_start_or_goal() -> None:
    scenario = make_task06_scenario("static_obstacle_medium", seed=1)

    assert len(scenario.static_obstacles) == 4
    for obstacle in scenario.static_obstacles:
        clearance = obstacle.radius + scenario.collision_radius
        assert _dist_xy(obstacle.position, scenario.start) > clearance
        assert _dist_xy(obstacle.position, scenario.goal) > clearance


def test_task06_static_cylinders_cover_flight_height() -> None:
    scenario = make_task06_scenario("static_obstacle_easy", seed=2)

    flight_z = scenario.start[2]
    cylinders = [obstacle for obstacle in scenario.static_obstacles if obstacle.kind == "cylinder"]
    assert cylinders
    for obstacle in cylinders:
        assert obstacle.height is not None
        assert obstacle.position[2] - obstacle.height / 2.0 <= flight_z
        assert obstacle.position[2] + obstacle.height / 2.0 >= flight_z
