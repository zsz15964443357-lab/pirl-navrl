import math

import pytest

from pirl_navrl.scenarios.curriculum import make_curriculum_scenario, validate_scenario


def _xy_distance(left, right) -> float:
    return math.dist(left[:2], right[:2])


def test_task05_curriculum_same_seed_is_deterministic() -> None:
    first = make_curriculum_scenario("level_2_static_obstacle_easy", seed=11)
    second = make_curriculum_scenario("level_2_static_obstacle_easy", seed=11)

    assert first.to_dict() == second.to_dict()


def test_task05_curriculum_different_seed_changes_scene() -> None:
    first = make_curriculum_scenario("level_1_no_obstacle_long", seed=1)
    second = make_curriculum_scenario("level_1_no_obstacle_long", seed=2)

    assert first.start != second.start or first.goal != second.goal


def test_task05_level0_has_no_obstacles_and_is_valid() -> None:
    scenario = make_curriculum_scenario("level_0_no_obstacle_short", seed=0)

    validate_scenario(scenario)
    assert scenario.scenario_id == "task05_level_0_no_obstacle_short"
    assert scenario.static_obstacles == ()
    assert scenario.dynamic_obstacles == ()
    assert 2.0 <= _xy_distance(scenario.start, scenario.goal) <= 3.2


def test_task05_level2_has_non_overlapping_static_obstacles() -> None:
    scenario = make_curriculum_scenario("level_2_static_obstacle_easy", seed=0)

    validate_scenario(scenario)
    assert len(scenario.static_obstacles) == 3
    for obstacle in scenario.static_obstacles:
        assert obstacle.kind == "cylinder"
        assert 0.18 <= obstacle.radius <= 0.32
        assert _xy_distance(obstacle.position, scenario.start) > obstacle.radius + scenario.collision_radius
        assert _xy_distance(obstacle.position, scenario.goal) > obstacle.radius + scenario.collision_radius
    for index, left in enumerate(scenario.static_obstacles):
        for right in scenario.static_obstacles[index + 1 :]:
            assert _xy_distance(left.position, right.position) > left.radius + right.radius


def test_task05_unknown_curriculum_level_reports_options() -> None:
    with pytest.raises(ValueError, match="unknown curriculum level"):
        make_curriculum_scenario("missing", seed=0)
