"""Shared scenario schema for TASK_03 diagnostic rollouts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Vector3 = tuple[float, float, float]
ObstacleKind = Literal["cylinder", "sphere"]
ObstacleMotion = Literal["static", "linear"]


@dataclass(frozen=True)
class Bounds3D:
    x: tuple[float, float]
    y: tuple[float, float]
    z: tuple[float, float]

    def clamp(self, position: Vector3) -> Vector3:
        return (
            min(max(position[0], self.x[0]), self.x[1]),
            min(max(position[1], self.y[0]), self.y[1]),
            min(max(position[2], self.z[0]), self.z[1]),
        )

    def contains(self, position: Vector3) -> bool:
        return (
            self.x[0] <= position[0] <= self.x[1]
            and self.y[0] <= position[1] <= self.y[1]
            and self.z[0] <= position[2] <= self.z[1]
        )


@dataclass(frozen=True)
class ObstacleConfig:
    obstacle_id: str
    kind: ObstacleKind
    position: Vector3
    radius: float
    height: float | None = None
    motion_type: ObstacleMotion = "static"
    velocity: Vector3 | None = None
    start_time: float = 0.0

    def position_at(self, elapsed: float) -> Vector3:
        if self.motion_type == "static" or self.velocity is None or elapsed <= self.start_time:
            return self.position
        active_time = elapsed - self.start_time
        return (
            self.position[0] + self.velocity[0] * active_time,
            self.position[1] + self.velocity[1] * active_time,
            self.position[2] + self.velocity[2] * active_time,
        )


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    seed: int
    start: Vector3
    goal: Vector3
    bounds: Bounds3D
    static_obstacles: tuple[ObstacleConfig, ...]
    dynamic_obstacles: tuple[ObstacleConfig, ...]
    max_steps: int
    dt: float
    success_radius: float
    collision_radius: float

    def all_obstacles(self) -> tuple[ObstacleConfig, ...]:
        return self.static_obstacles + self.dynamic_obstacles

    def to_dict(self) -> dict:
        return asdict(self)


def make_task03_static_nav_v0(seed: int = 0) -> ScenarioConfig:
    """Create the first TASK_03 diagnostic navigation scene."""

    return ScenarioConfig(
        scenario_id="task03_static_nav_v0",
        seed=seed,
        start=(-4.0, 0.0, 1.0),
        goal=(4.0, 0.0, 1.0),
        bounds=Bounds3D(x=(-5.0, 5.0), y=(-5.0, 5.0), z=(0.0, 3.0)),
        static_obstacles=(
            ObstacleConfig(
                obstacle_id="center_cylinder",
                kind="cylinder",
                position=(-0.6, 0.0, 1.0),
                radius=0.65,
                height=2.0,
            ),
            ObstacleConfig(
                obstacle_id="upper_sphere",
                kind="sphere",
                position=(1.3, 1.0, 1.0),
                radius=0.45,
            ),
            ObstacleConfig(
                obstacle_id="lower_cylinder",
                kind="cylinder",
                position=(2.3, -1.0, 1.0),
                radius=0.42,
                height=2.0,
            ),
        ),
        dynamic_obstacles=(),
        max_steps=100,
        dt=0.15,
        success_radius=0.35,
        collision_radius=0.22,
    )


SCENARIO_FACTORIES = {
    "task03_static_nav_v0": make_task03_static_nav_v0,
}


def make_scenario(scenario_id: str, *, seed: int = 0) -> ScenarioConfig:
    try:
        return SCENARIO_FACTORIES[scenario_id](seed=seed)
    except KeyError as exc:
        options = ", ".join(sorted(SCENARIO_FACTORIES))
        raise ValueError(f"unknown scenario_id {scenario_id!r}; options: {options}") from exc
