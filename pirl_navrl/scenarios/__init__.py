"""Diagnostic scenarios for PIRL-NavRL development."""

from pirl_navrl.scenarios.core import (
    Bounds3D,
    ObstacleConfig,
    ScenarioConfig,
    Vector3,
    make_scenario,
    make_task03_static_nav_v0,
)
from pirl_navrl.scenarios.curriculum import (
    CurriculumLevelConfig,
    ScenarioRandomizationConfig,
    load_curriculum_config,
    make_curriculum_scenario,
    sample_start_goal,
    sample_static_obstacles,
    validate_scenario,
)
from pirl_navrl.scenarios.ego_official_diagnostic_scenarios import (
    EgoDiagnosticObstacle,
    EgoOfficialDiagnosticScenario,
    make_ego_dynamic_obstacle_v0,
    make_ego_official_diagnostic_scenario,
    make_ego_static_obstacle_v0,
    make_ego_sudden_motion_obstacle_v0,
)

__all__ = [
    "Bounds3D",
    "CurriculumLevelConfig",
    "EgoDiagnosticObstacle",
    "EgoOfficialDiagnosticScenario",
    "ObstacleConfig",
    "ScenarioConfig",
    "ScenarioRandomizationConfig",
    "Vector3",
    "make_ego_dynamic_obstacle_v0",
    "make_ego_official_diagnostic_scenario",
    "make_ego_static_obstacle_v0",
    "make_ego_sudden_motion_obstacle_v0",
    "load_curriculum_config",
    "make_curriculum_scenario",
    "make_scenario",
    "make_task03_static_nav_v0",
    "sample_start_goal",
    "sample_static_obstacles",
    "validate_scenario",
]
