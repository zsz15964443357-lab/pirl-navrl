"""NavRL-guided multi-scenario curriculum for TASK_06 diagnostics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from pirl_navrl.scenarios.core import Bounds3D, ObstacleConfig, ScenarioConfig, Vector3
from pirl_navrl.scenarios.curriculum import validate_scenario

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TASK06_CURRICULUM_CONFIG = ROOT_DIR / "configs" / "task06_multiscenario_curriculum.json"
ScenarioGroup = Literal["static", "dynamic", "latent_dynamic", "mixed_static_dynamic"]


@dataclass(frozen=True)
class Task06LevelConfig:
    level_id: str
    scenario_group: ScenarioGroup
    goal_distance: tuple[float, float]
    max_steps: int
    static_obstacle_count: int
    dynamic_obstacle_count: int
    obstacle_radius: tuple[float, float]
    obstacle_height: tuple[float, float]
    dynamic_speed: tuple[float, float]
    trigger_step: int | None = None


@dataclass(frozen=True)
class Task06CurriculumConfig:
    bounds: Bounds3D
    dt: float
    success_radius: float
    collision_radius: float
    start_goal_z: tuple[float, float]
    start_goal_clearance: float
    obstacle_clearance: float
    max_dynamic_speed: float
    levels: dict[str, Task06LevelConfig]


def _pair(value: Any) -> tuple[float, float]:
    return (float(value[0]), float(value[1]))


def load_task06_curriculum_config(path: str | Path = DEFAULT_TASK06_CURRICULUM_CONFIG) -> Task06CurriculumConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    defaults = payload["defaults"]
    bounds = payload["arena_bounds"]
    levels = {}
    for item in payload["levels"]:
        levels[item["level_id"]] = Task06LevelConfig(
            level_id=item["level_id"],
            scenario_group=item["scenario_group"],
            goal_distance=_pair(item["goal_distance"]),
            max_steps=int(item["max_steps"]),
            static_obstacle_count=int(item["static_obstacle_count"]),
            dynamic_obstacle_count=int(item["dynamic_obstacle_count"]),
            obstacle_radius=_pair(item["obstacle_radius"]),
            obstacle_height=_pair(item["obstacle_height"]),
            dynamic_speed=_pair(item["dynamic_speed"]),
            trigger_step=None if item.get("trigger_step") is None else int(item["trigger_step"]),
        )
    return Task06CurriculumConfig(
        bounds=Bounds3D(x=_pair(bounds["x"]), y=_pair(bounds["y"]), z=_pair(bounds["z"])),
        dt=float(defaults["dt"]),
        success_radius=float(defaults["success_radius"]),
        collision_radius=float(defaults["collision_radius"]),
        start_goal_z=_pair(defaults["start_goal_z"]),
        start_goal_clearance=float(defaults["start_goal_clearance"]),
        obstacle_clearance=float(defaults["obstacle_clearance"]),
        max_dynamic_speed=float(defaults["max_dynamic_speed"]),
        levels=levels,
    )


def make_task06_scenario(
    level_id: str,
    seed: int,
    *,
    config_path: str | Path = DEFAULT_TASK06_CURRICULUM_CONFIG,
) -> ScenarioConfig:
    cfg = load_task06_curriculum_config(config_path)
    try:
        level = cfg.levels[level_id]
    except KeyError as exc:
        options = ", ".join(sorted(cfg.levels))
        raise ValueError(f"unknown TASK_06 level {level_id!r}; options: {options}") from exc
    rng = np.random.default_rng(int(seed))
    start, goal = sample_task06_start_goal(rng, cfg, level)
    static = sample_task06_static_obstacles(rng, cfg, level, start, goal)
    dynamic = sample_task06_dynamic_obstacles(rng, cfg, level, start, goal)
    scenario = ScenarioConfig(
        scenario_id=f"task06_{level.level_id}",
        seed=int(seed),
        start=start,
        goal=goal,
        bounds=cfg.bounds,
        static_obstacles=static,
        dynamic_obstacles=dynamic,
        max_steps=level.max_steps,
        dt=cfg.dt,
        success_radius=cfg.success_radius,
        collision_radius=cfg.collision_radius,
    )
    validate_scenario(scenario)
    return scenario


def sample_task06_start_goal(
    rng: np.random.Generator,
    cfg: Task06CurriculumConfig,
    level: Task06LevelConfig,
) -> tuple[Vector3, Vector3]:
    min_dist, max_dist = level.goal_distance
    for _ in range(500):
        start_xy = np.asarray(
            [
                rng.uniform(cfg.bounds.x[0] + 0.5, cfg.bounds.x[1] - 0.5),
                rng.uniform(cfg.bounds.y[0] + 0.5, cfg.bounds.y[1] - 0.5),
            ],
            dtype=np.float32,
        )
        angle = rng.uniform(-np.pi, np.pi)
        distance = rng.uniform(min_dist, max_dist)
        goal_xy = start_xy + np.asarray([np.cos(angle), np.sin(angle)], dtype=np.float32) * distance
        if cfg.bounds.x[0] + 0.5 <= goal_xy[0] <= cfg.bounds.x[1] - 0.5 and cfg.bounds.y[0] + 0.5 <= goal_xy[1] <= cfg.bounds.y[1] - 0.5:
            z = float(rng.uniform(cfg.start_goal_z[0], cfg.start_goal_z[1]))
            return (float(start_xy[0]), float(start_xy[1]), z), (float(goal_xy[0]), float(goal_xy[1]), z)
    raise RuntimeError(f"failed to sample TASK_06 start/goal for {level.level_id}")


def sample_task06_static_obstacles(
    rng: np.random.Generator,
    cfg: Task06CurriculumConfig,
    level: Task06LevelConfig,
    start: Vector3,
    goal: Vector3,
) -> tuple[ObstacleConfig, ...]:
    obstacles: list[ObstacleConfig] = []
    start_xy = np.asarray(start[:2], dtype=np.float32)
    goal_xy = np.asarray(goal[:2], dtype=np.float32)
    path = goal_xy - start_xy
    path_norm = float(np.linalg.norm(path))
    path_dir = path / max(path_norm, 1e-6)
    normal = np.asarray([-path_dir[1], path_dir[0]], dtype=np.float32)
    for index in range(level.static_obstacle_count):
        placed = False
        for _ in range(300):
            radius = float(rng.uniform(level.obstacle_radius[0], level.obstacle_radius[1]))
            height = float(rng.uniform(level.obstacle_height[0], level.obstacle_height[1]))
            t = rng.uniform(0.25, 0.75)
            if level.level_id == "static_obstacle_easy":
                offset = rng.choice([-1.0, 1.0]) * rng.uniform(0.85, 1.35)
            else:
                offset = rng.uniform(-0.55, 0.55) if index % 2 == 0 else rng.choice([-1.0, 1.0]) * rng.uniform(0.75, 1.6)
            xy = start_xy + path * t + normal * offset
            xy += rng.normal(0.0, 0.15, size=2).astype(np.float32)
            if not (cfg.bounds.x[0] + radius <= xy[0] <= cfg.bounds.x[1] - radius and cfg.bounds.y[0] + radius <= xy[1] <= cfg.bounds.y[1] - radius):
                continue
            pos = (float(xy[0]), float(xy[1]), max(height * 0.5, radius))
            if _clear_of_points(pos, radius, (start, goal), cfg) and _clear_of_existing_obstacles(pos, radius, tuple(obstacles), cfg):
                obstacles.append(
                    ObstacleConfig(
                        obstacle_id=f"task06_static_{index}",
                        kind="cylinder" if index % 2 == 0 else "sphere",
                        position=pos,
                        radius=radius,
                        height=None if index % 2 else height,
                    )
                )
                placed = True
                break
        if not placed:
            placed = _append_random_static_obstacle(rng, cfg, level, obstacles, start, goal, index)
        if not placed:
            raise RuntimeError(f"failed to sample static obstacle {index}")
    return tuple(obstacles)


def _append_random_static_obstacle(
    rng: np.random.Generator,
    cfg: Task06CurriculumConfig,
    level: Task06LevelConfig,
    obstacles: list[ObstacleConfig],
    start: Vector3,
    goal: Vector3,
    index: int,
) -> bool:
    for _ in range(600):
        radius = float(rng.uniform(level.obstacle_radius[0], level.obstacle_radius[1]))
        height = float(rng.uniform(level.obstacle_height[0], level.obstacle_height[1]))
        xy = np.asarray(
            [
                rng.uniform(cfg.bounds.x[0] + radius, cfg.bounds.x[1] - radius),
                rng.uniform(cfg.bounds.y[0] + radius, cfg.bounds.y[1] - radius),
            ],
            dtype=np.float32,
        )
        pos = (float(xy[0]), float(xy[1]), max(height * 0.5, radius))
        if _clear_of_points(pos, radius, (start, goal), cfg) and _clear_of_existing_obstacles(pos, radius, tuple(obstacles), cfg):
            obstacles.append(
                ObstacleConfig(
                    obstacle_id=f"task06_static_{index}",
                    kind="cylinder" if index % 2 == 0 else "sphere",
                    position=pos,
                    radius=radius,
                    height=None if index % 2 else height,
                )
            )
            return True
    return False


def sample_task06_dynamic_obstacles(
    rng: np.random.Generator,
    cfg: Task06CurriculumConfig,
    level: Task06LevelConfig,
    start: Vector3,
    goal: Vector3,
) -> tuple[ObstacleConfig, ...]:
    if level.dynamic_obstacle_count <= 0:
        return ()
    start_xy = np.asarray(start[:2], dtype=np.float32)
    goal_xy = np.asarray(goal[:2], dtype=np.float32)
    path = goal_xy - start_xy
    path_norm = float(np.linalg.norm(path))
    path_dir = path / max(path_norm, 1e-6)
    normal = np.asarray([-path_dir[1], path_dir[0]], dtype=np.float32)
    dynamic: list[ObstacleConfig] = []
    for index in range(level.dynamic_obstacle_count):
        radius = float(rng.uniform(level.obstacle_radius[0], level.obstacle_radius[1]))
        speed = float(rng.uniform(level.dynamic_speed[0], level.dynamic_speed[1]))
        crossing_center = start_xy + path * rng.uniform(0.35, 0.65)
        side = -1.0 if index % 2 == 0 else 1.0
        initial_xy = crossing_center + normal * side * 2.2
        velocity_xy = -normal * side * speed
        z = float(start[2])
        start_time = 0.0
        if level.scenario_group == "latent_dynamic":
            start_time = float(level.trigger_step or 45) * cfg.dt
        dynamic.append(
            ObstacleConfig(
                obstacle_id=f"task06_dynamic_{index}",
                kind="sphere",
                position=(float(initial_xy[0]), float(initial_xy[1]), z),
                radius=radius,
                motion_type="linear",
                velocity=(float(velocity_xy[0]), float(velocity_xy[1]), 0.0),
                start_time=start_time,
            )
        )
    return tuple(dynamic)


def _clear_of_points(position: Vector3, radius: float, points: tuple[Vector3, ...], cfg: Task06CurriculumConfig) -> bool:
    xy = np.asarray(position[:2], dtype=np.float32)
    for point in points:
        if float(np.linalg.norm(xy - np.asarray(point[:2], dtype=np.float32))) <= radius + cfg.collision_radius + cfg.start_goal_clearance:
            return False
    return True


def _clear_of_existing_obstacles(
    position: Vector3,
    radius: float,
    obstacles: tuple[ObstacleConfig, ...],
    cfg: Task06CurriculumConfig,
) -> bool:
    xy = np.asarray(position[:2], dtype=np.float32)
    for obstacle in obstacles:
        other_xy = np.asarray(obstacle.position[:2], dtype=np.float32)
        if float(np.linalg.norm(xy - other_xy)) <= radius + obstacle.radius + cfg.obstacle_clearance:
            return False
    return True


def task06_level_group(level_id: str, *, config_path: str | Path = DEFAULT_TASK06_CURRICULUM_CONFIG) -> ScenarioGroup:
    return load_task06_curriculum_config(config_path).levels[level_id].scenario_group
