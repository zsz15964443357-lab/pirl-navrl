"""Seeded curriculum scenario generation for TASK_05 debug training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pirl_navrl.scenarios.core import Bounds3D, ObstacleConfig, ScenarioConfig, Vector3

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CURRICULUM_CONFIG = ROOT_DIR / "configs" / "task05_curriculum_levels.json"


@dataclass(frozen=True)
class CurriculumLevelConfig:
    level_id: str
    description: str
    goal_distance: tuple[float, float]
    max_steps: int
    static_obstacle_count: int
    obstacle_radius: tuple[float, float]
    obstacle_height: tuple[float, float]


@dataclass(frozen=True)
class ScenarioRandomizationConfig:
    arena_bounds: Bounds3D
    dt: float
    success_radius: float
    collision_radius: float
    start_goal_clearance: float
    obstacle_clearance: float
    start_goal_z: tuple[float, float]
    levels: dict[str, CurriculumLevelConfig]


def _pair(value: Any) -> tuple[float, float]:
    return (float(value[0]), float(value[1]))


def load_curriculum_config(path: str | Path = DEFAULT_CURRICULUM_CONFIG) -> ScenarioRandomizationConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    defaults = payload["defaults"]
    bounds = payload["arena_bounds"]
    levels = {
        item["level_id"]: CurriculumLevelConfig(
            level_id=item["level_id"],
            description=item["description"],
            goal_distance=_pair(item["goal_distance"]),
            max_steps=int(item["max_steps"]),
            static_obstacle_count=int(item["static_obstacle_count"]),
            obstacle_radius=_pair(item["obstacle_radius"]),
            obstacle_height=_pair(item["obstacle_height"]),
        )
        for item in payload["levels"]
    }
    return ScenarioRandomizationConfig(
        arena_bounds=Bounds3D(x=_pair(bounds["x"]), y=_pair(bounds["y"]), z=_pair(bounds["z"])),
        dt=float(defaults["dt"]),
        success_radius=float(defaults["success_radius"]),
        collision_radius=float(defaults["collision_radius"]),
        start_goal_clearance=float(defaults["start_goal_clearance"]),
        obstacle_clearance=float(defaults["obstacle_clearance"]),
        start_goal_z=_pair(defaults["start_goal_z"]),
        levels=levels,
    )


def _sample_xy(rng: np.random.Generator, bounds: Bounds3D, margin: float = 0.0) -> np.ndarray:
    return np.asarray(
        [
            rng.uniform(bounds.x[0] + margin, bounds.x[1] - margin),
            rng.uniform(bounds.y[0] + margin, bounds.y[1] - margin),
        ],
        dtype=np.float32,
    )


def sample_start_goal(
    rng: np.random.Generator,
    config: ScenarioRandomizationConfig,
    level: CurriculumLevelConfig,
) -> tuple[Vector3, Vector3]:
    """Sample start/goal in the fixed arena with a target planar distance band."""

    min_dist, max_dist = level.goal_distance
    for _ in range(500):
        start_xy = _sample_xy(rng, config.arena_bounds, margin=0.35)
        angle = rng.uniform(-np.pi, np.pi)
        distance = rng.uniform(min_dist, max_dist)
        goal_xy = start_xy + np.asarray([np.cos(angle), np.sin(angle)], dtype=np.float32) * distance
        if not (
            config.arena_bounds.x[0] + 0.35 <= goal_xy[0] <= config.arena_bounds.x[1] - 0.35
            and config.arena_bounds.y[0] + 0.35 <= goal_xy[1] <= config.arena_bounds.y[1] - 0.35
        ):
            continue
        z = float(rng.uniform(config.start_goal_z[0], config.start_goal_z[1]))
        return (
            (float(start_xy[0]), float(start_xy[1]), z),
            (float(goal_xy[0]), float(goal_xy[1]), z),
        )
    raise RuntimeError(f"failed to sample start/goal for curriculum level {level.level_id!r}")


def _distance_xy(a: Vector3 | np.ndarray, b: Vector3 | np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(a, dtype=np.float32)[:2] - np.asarray(b, dtype=np.float32)[:2]))


def sample_static_obstacles(
    rng: np.random.Generator,
    config: ScenarioRandomizationConfig,
    level: CurriculumLevelConfig,
    start: Vector3,
    goal: Vector3,
) -> tuple[ObstacleConfig, ...]:
    obstacles: list[ObstacleConfig] = []
    if level.static_obstacle_count <= 0:
        return ()
    for index in range(level.static_obstacle_count):
        for _ in range(300):
            radius = float(rng.uniform(level.obstacle_radius[0], level.obstacle_radius[1]))
            height = float(rng.uniform(level.obstacle_height[0], level.obstacle_height[1]))
            xy = _sample_xy(rng, config.arena_bounds, margin=radius + 0.25)
            position = (float(xy[0]), float(xy[1]), max(height * 0.5, radius))
            clearance = radius + config.collision_radius + config.start_goal_clearance
            if _distance_xy(position, start) <= clearance or _distance_xy(position, goal) <= clearance:
                continue
            overlaps = False
            for obstacle in obstacles:
                min_sep = radius + obstacle.radius + config.obstacle_clearance
                if _distance_xy(position, obstacle.position) <= min_sep:
                    overlaps = True
                    break
            if overlaps:
                continue
            obstacles.append(
                ObstacleConfig(
                    obstacle_id=f"task05_static_{index}",
                    kind="cylinder",
                    position=position,
                    radius=radius,
                    height=height,
                )
            )
            break
        else:
            raise RuntimeError(f"failed to sample obstacle {index} for curriculum level {level.level_id!r}")
    return tuple(obstacles)


def validate_scenario(scenario: ScenarioConfig) -> None:
    if not scenario.bounds.contains(scenario.start):
        raise ValueError("scenario start is outside arena bounds")
    if not scenario.bounds.contains(scenario.goal):
        raise ValueError("scenario goal is outside arena bounds")
    if _distance_xy(scenario.start, scenario.goal) <= scenario.success_radius:
        raise ValueError("scenario start and goal are too close")
    for obstacle in scenario.static_obstacles:
        if obstacle.radius <= 0.0:
            raise ValueError(f"obstacle {obstacle.obstacle_id} radius must be positive")
        if not scenario.bounds.contains(obstacle.position):
            raise ValueError(f"obstacle {obstacle.obstacle_id} is outside arena bounds")
        required = obstacle.radius + scenario.collision_radius
        if _distance_xy(obstacle.position, scenario.start) <= required:
            raise ValueError(f"obstacle {obstacle.obstacle_id} overlaps start safety radius")
        if _distance_xy(obstacle.position, scenario.goal) <= required:
            raise ValueError(f"obstacle {obstacle.obstacle_id} overlaps goal safety radius")
    for left_index, left in enumerate(scenario.static_obstacles):
        for right in scenario.static_obstacles[left_index + 1 :]:
            if _distance_xy(left.position, right.position) <= left.radius + right.radius:
                raise ValueError(f"obstacles {left.obstacle_id} and {right.obstacle_id} overlap")


def make_curriculum_scenario(
    level_id: str,
    seed: int,
    *,
    config_path: str | Path = DEFAULT_CURRICULUM_CONFIG,
) -> ScenarioConfig:
    randomization = load_curriculum_config(config_path)
    try:
        level = randomization.levels[level_id]
    except KeyError as exc:
        options = ", ".join(sorted(randomization.levels))
        raise ValueError(f"unknown curriculum level {level_id!r}; options: {options}") from exc
    rng = np.random.default_rng(int(seed))
    start, goal = sample_start_goal(rng, randomization, level)
    obstacles = sample_static_obstacles(rng, randomization, level, start, goal)
    scenario = ScenarioConfig(
        scenario_id=f"task05_{level_id}",
        seed=int(seed),
        start=start,
        goal=goal,
        bounds=randomization.arena_bounds,
        static_obstacles=obstacles,
        dynamic_obstacles=(),
        max_steps=level.max_steps,
        dt=randomization.dt,
        success_radius=randomization.success_radius,
        collision_radius=randomization.collision_radius,
    )
    validate_scenario(scenario)
    return scenario
