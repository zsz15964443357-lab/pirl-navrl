"""TASK_02 official EGO-Planner diagnostic scenario definitions."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Literal

Vector3 = tuple[float, float, float]
ObstacleKind = Literal["cylinder", "sphere", "pointcloud_cluster"]
MotionType = Literal["static", "linear", "sudden_linear"]


@dataclass(frozen=True)
class EgoDiagnosticObstacle:
    obstacle_id: str
    kind: ObstacleKind
    initial_position: Vector3
    radius: float
    height: float | None = None
    motion_type: MotionType = "static"
    velocity: Vector3 | None = None
    start_time: float | None = None

    def obstacle_mode(self) -> str:
        return self.motion_type


@dataclass(frozen=True)
class EgoOfficialDiagnosticScenario:
    scenario_id: str
    seed: int
    start: Vector3
    goal: Vector3
    map_size: Vector3
    duration: float
    obstacles: tuple[EgoDiagnosticObstacle, ...]
    notes: str

    @property
    def obstacle_mode(self) -> str:
        modes = {obstacle.motion_type for obstacle in self.obstacles}
        if modes == {"static"}:
            return "static"
        if "sudden_linear" in modes:
            return "sudden_linear"
        return "linear"

    def to_trace_metadata(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "start": list(self.start),
            "goal": list(self.goal),
            "map_size": list(self.map_size),
            "duration": self.duration,
            "obstacle_mode": self.obstacle_mode,
            "obstacles": [asdict(obstacle) for obstacle in self.obstacles],
            "notes": self.notes,
        }


def make_ego_static_obstacle_v0(seed: int = 127) -> EgoOfficialDiagnosticScenario:
    """Small custom static-obstacle scene injected as an EGO global cloud."""

    return EgoOfficialDiagnosticScenario(
        scenario_id="ego_static_obstacle_v0",
        seed=seed,
        start=(-6.0, 0.0, 1.0),
        goal=(6.0, 0.0, 1.0),
        map_size=(16.0, 10.0, 3.0),
        duration=55.0,
        obstacles=(
            EgoDiagnosticObstacle(
                obstacle_id="static_center_post",
                kind="cylinder",
                initial_position=(-0.5, 0.0, 1.0),
                radius=0.65,
                height=2.0,
                motion_type="static",
            ),
            EgoDiagnosticObstacle(
                obstacle_id="static_offset_post",
                kind="cylinder",
                initial_position=(2.1, -0.75, 1.0),
                radius=0.48,
                height=2.0,
                motion_type="static",
            ),
        ),
        notes=(
            "Custom TASK_02 scene. PIRL-NavRL publishes these PyBullet-style "
            "obstacle primitives as /pirl_navrl/custom_scene_cloud, remapped to "
            "official EGO /grid_map/cloud; planner, SO3 control, and simulator "
            "remain upstream."
        ),
    )


def make_ego_dynamic_obstacle_v0(seed: int = 127) -> EgoOfficialDiagnosticScenario:
    """Small custom scene with one continuously moving crossing obstacle."""

    return EgoOfficialDiagnosticScenario(
        scenario_id="ego_dynamic_obstacle_v0",
        seed=seed,
        start=(-6.0, 0.0, 1.0),
        goal=(6.0, 0.0, 1.0),
        map_size=(16.0, 10.0, 3.0),
        duration=60.0,
        obstacles=(
            EgoDiagnosticObstacle(
                obstacle_id="dynamic_crossing_post",
                kind="cylinder",
                initial_position=(-0.2, -2.0, 1.0),
                radius=0.55,
                height=2.0,
                motion_type="linear",
                velocity=(0.0, 0.22, 0.0),
                start_time=0.0,
            ),
            EgoDiagnosticObstacle(
                obstacle_id="dynamic_static_reference_post",
                kind="cylinder",
                initial_position=(2.3, 0.9, 1.0),
                radius=0.45,
                height=2.0,
                motion_type="static",
            ),
        ),
        notes=(
            "Custom TASK_02 dynamic scene. PIRL-NavRL continuously republishes a "
            "moving obstacle cloud to official EGO's /grid_map/cloud."
        ),
    )


def make_ego_sudden_motion_obstacle_v0(seed: int = 127) -> EgoOfficialDiagnosticScenario:
    """Small custom scene where a crossing obstacle starts moving after delay."""

    return EgoOfficialDiagnosticScenario(
        scenario_id="ego_sudden_motion_obstacle_v0",
        seed=seed,
        start=(-6.0, 0.0, 1.0),
        goal=(6.0, 0.0, 1.0),
        map_size=(16.0, 10.0, 3.0),
        duration=60.0,
        obstacles=(
            EgoDiagnosticObstacle(
                obstacle_id="sudden_crossing_post",
                kind="cylinder",
                initial_position=(2.8, -1.7, 1.0),
                radius=0.55,
                height=2.0,
                motion_type="sudden_linear",
                velocity=(0.0, 0.4, 0.0),
                start_time=7.0,
            ),
            EgoDiagnosticObstacle(
                obstacle_id="sudden_static_reference_post",
                kind="cylinder",
                initial_position=(2.4, -0.9, 1.0),
                radius=0.45,
                height=2.0,
                motion_type="static",
            ),
        ),
        notes=(
            "Custom TASK_02 sudden-motion scene. The main obstacle is stationary "
            "at first and then moves laterally while official EGO keeps running."
        ),
    )


SCENARIO_FACTORIES = {
    "ego_static_obstacle_v0": make_ego_static_obstacle_v0,
    "ego_dynamic_obstacle_v0": make_ego_dynamic_obstacle_v0,
    "ego_sudden_motion_obstacle_v0": make_ego_sudden_motion_obstacle_v0,
}


def make_ego_official_diagnostic_scenario(
    scenario_id: str,
    *,
    seed: int = 127,
) -> EgoOfficialDiagnosticScenario:
    try:
        return SCENARIO_FACTORIES[scenario_id](seed=seed)
    except KeyError as exc:
        options = ", ".join(sorted(SCENARIO_FACTORIES))
        raise ValueError(f"unknown TASK_02 scenario {scenario_id!r}; options: {options}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_id", choices=sorted(SCENARIO_FACTORIES))
    parser.add_argument("--seed", type=int, default=127)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario = make_ego_official_diagnostic_scenario(args.scenario_id, seed=args.seed)
    print(json.dumps(scenario.to_trace_metadata(), sort_keys=True))


if __name__ == "__main__":
    main()
