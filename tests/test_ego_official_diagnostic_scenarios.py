from pirl_navrl.scenarios.ego_official_diagnostic_scenarios import (
    make_ego_dynamic_obstacle_v0,
    make_ego_official_diagnostic_scenario,
    make_ego_static_obstacle_v0,
    make_ego_sudden_motion_obstacle_v0,
)


def test_static_official_scenario_metadata() -> None:
    scenario = make_ego_static_obstacle_v0(seed=127)
    metadata = scenario.to_trace_metadata()

    assert scenario.scenario_id == "ego_static_obstacle_v0"
    assert scenario.obstacle_mode == "static"
    assert metadata["goal"] == [6.0, 0.0, 1.0]
    assert metadata["map_size"] == [16.0, 10.0, 3.0]
    assert metadata["obstacles"][0]["kind"] == "cylinder"


def test_dynamic_scenarios_define_real_custom_cloud_motion() -> None:
    dynamic = make_ego_dynamic_obstacle_v0()
    sudden = make_ego_sudden_motion_obstacle_v0()

    assert dynamic.obstacle_mode == "linear"
    assert sudden.obstacle_mode == "sudden_linear"
    assert dynamic.obstacles[0].velocity == (0.0, 0.22, 0.0)
    assert sudden.obstacles[0].velocity == (0.0, 0.4, 0.0)
    assert sudden.obstacles[0].start_time == 7.0
    assert "republishes a moving obstacle cloud" in dynamic.notes


def test_scenario_factory_rejects_unknown_id() -> None:
    scenario = make_ego_official_diagnostic_scenario("ego_static_obstacle_v0")
    assert scenario.scenario_id == "ego_static_obstacle_v0"

    try:
        make_ego_official_diagnostic_scenario("missing")
    except ValueError as exc:
        assert "unknown TASK_02 scenario" in str(exc)
    else:
        raise AssertionError("expected unknown scenario to fail")
