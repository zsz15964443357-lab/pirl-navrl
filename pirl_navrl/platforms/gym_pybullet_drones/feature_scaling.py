"""Feature scaling helpers for TASK_06 diagnostic training."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pirl_navrl.platforms.gym_pybullet_drones.observation_adapter import flatten_observation
from pirl_navrl.scenarios.core import ScenarioConfig


@dataclass(frozen=True)
class FeatureScalingConfig:
    arena_size: float = 5.0
    max_speed: float = 1.0
    max_distance: float = 10.0
    max_dynamic_speed: float = 1.0
    lidar_range: float = 4.0
    lidar_hbeams: int = 36
    lidar_vbeams: int = 4
    dyn_obs_num: int = 5


def scale_task04_flat_observation(obs_dict: dict[str, Any], config: FeatureScalingConfig | None = None) -> np.ndarray:
    cfg = config or FeatureScalingConfig()
    flat = flatten_observation(obs_dict).astype(np.float32)
    scaled = flat.copy()
    scaled[0:3] /= cfg.arena_size
    scaled[3:6] /= cfg.max_speed
    scaled[6:9] /= cfg.arena_size
    scaled[9:12] /= cfg.arena_size
    scaled[12] /= cfg.max_distance
    scaled[13:16] /= cfg.arena_size
    scaled[16] /= cfg.max_distance
    scaled[17] = np.clip(scaled[17] / cfg.arena_size, -1.0, 1.0)
    scaled[18] = np.clip(scaled[18], 0.0, 1.0)
    return np.clip(scaled, -10.0, 10.0).astype(np.float32)


def dynamic_obstacle_relative_features(
    *,
    scenario: ScenarioConfig,
    position,
    velocity,
    elapsed: float,
    config: FeatureScalingConfig | None = None,
) -> np.ndarray:
    cfg = config or FeatureScalingConfig()
    pos = np.asarray(position, dtype=np.float32).reshape(3)
    vel = np.asarray(velocity, dtype=np.float32).reshape(3)
    best = np.zeros(6, dtype=np.float32)
    best_distance = np.inf
    for obstacle in scenario.dynamic_obstacles:
        obstacle_pos = np.asarray(obstacle.position_at(elapsed), dtype=np.float32)
        obstacle_vel = np.asarray(obstacle.velocity or (0.0, 0.0, 0.0), dtype=np.float32)
        if elapsed <= obstacle.start_time:
            obstacle_vel = np.zeros(3, dtype=np.float32)
        relative = obstacle_pos - pos
        distance = float(np.linalg.norm(relative))
        if distance < best_distance:
            best_distance = distance
            best[:3] = relative / cfg.arena_size
            best[3:] = (obstacle_vel - vel) / cfg.max_dynamic_speed
    return np.clip(best, -10.0, 10.0).astype(np.float32)


def navrl_goal_frame_basis(relative_goal) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    goal = np.asarray(relative_goal, dtype=np.float32).reshape(3)
    x_axis = goal.copy()
    x_axis[2] = 0.0
    norm = float(np.linalg.norm(x_axis))
    if norm < 1e-6:
        x_axis = np.asarray([1.0, 0.0, 0.0], dtype=np.float32)
    else:
        x_axis = x_axis / norm
    z_axis = np.asarray([0.0, 0.0, 1.0], dtype=np.float32)
    y_axis = np.cross(z_axis, x_axis).astype(np.float32)
    y_norm = float(np.linalg.norm(y_axis))
    if y_norm < 1e-6:
        y_axis = np.asarray([0.0, 1.0, 0.0], dtype=np.float32)
    else:
        y_axis = y_axis / y_norm
    return x_axis.astype(np.float32), y_axis.astype(np.float32), z_axis


def vec_to_navrl_goal_frame(vector, relative_goal) -> np.ndarray:
    vec = np.asarray(vector, dtype=np.float32).reshape(3)
    x_axis, y_axis, z_axis = navrl_goal_frame_basis(relative_goal)
    return np.asarray([np.dot(vec, x_axis), np.dot(vec, y_axis), np.dot(vec, z_axis)], dtype=np.float32)


def vec_from_navrl_goal_frame(vector, relative_goal) -> np.ndarray:
    vec = np.asarray(vector, dtype=np.float32).reshape(3)
    x_axis, y_axis, z_axis = navrl_goal_frame_basis(relative_goal)
    return (x_axis * vec[0] + y_axis * vec[1] + z_axis * vec[2]).astype(np.float32)


def navrl_style_observation(
    *,
    obs_dict: dict[str, Any],
    scenario: ScenarioConfig,
    elapsed: float,
    config: FeatureScalingConfig | None = None,
    pybullet_client: int | None = None,
    ignore_body_ids: set[int] | None = None,
) -> dict[str, np.ndarray]:
    """Build a NavRL-shaped observation for the TASK_06 PyBullet adapter.

    NavRL's Isaac environment uses state, lidar, direction, and nearest dynamic
    obstacle tensors. This helper keeps the same tensor contract while using the
    available PyBullet raycast data when a live client is available. Schema
    tests and offline helpers fall back to scenario geometry.
    """

    cfg = config or FeatureScalingConfig()
    position = np.asarray(obs_dict["position"], dtype=np.float32).reshape(3)
    velocity = np.asarray(obs_dict["velocity"], dtype=np.float32).reshape(3)
    relative_goal = np.asarray(obs_dict["relative_goal"], dtype=np.float32).reshape(3)
    distance = max(float(np.linalg.norm(relative_goal)), 1e-6)
    distance_2d = float(np.linalg.norm(relative_goal[:2]))
    relative_goal_g = vec_to_navrl_goal_frame(relative_goal / distance, relative_goal)
    velocity_g = vec_to_navrl_goal_frame(velocity, relative_goal) / max(cfg.max_speed, 1e-6)
    state = np.concatenate(
        [
            relative_goal_g,
            np.asarray([distance_2d / cfg.max_distance, relative_goal[2] / cfg.arena_size], dtype=np.float32),
            velocity_g,
        ]
    ).astype(np.float32)
    direction = relative_goal.copy()
    direction[2] = 0.0
    direction_norm = float(np.linalg.norm(direction))
    if direction_norm > 1e-6:
        direction /= direction_norm
    if pybullet_client is None:
        lidar = _navrl_lidar_like_scan(position, relative_goal, scenario, elapsed, cfg)
    else:
        lidar = _navrl_pybullet_raycast_scan(
            position=position,
            relative_goal=relative_goal,
            pybullet_client=pybullet_client,
            ignore_body_ids=ignore_body_ids or set(),
            cfg=cfg,
        )
    dynamic = _navrl_dynamic_obstacle_tensor(position, velocity, relative_goal, scenario, elapsed, cfg)
    return {
        "state": np.clip(state, -10.0, 10.0).astype(np.float32),
        "lidar": lidar.astype(np.float32),
        "direction": direction.reshape(1, 3).astype(np.float32),
        "dynamic_obstacle": dynamic.astype(np.float32),
    }


def _navrl_pybullet_raycast_scan(
    *,
    position: np.ndarray,
    relative_goal: np.ndarray,
    pybullet_client: int,
    ignore_body_ids: set[int],
    cfg: FeatureScalingConfig,
) -> np.ndarray:
    try:
        import pybullet as p
    except ImportError:
        return np.zeros((1, cfg.lidar_hbeams, cfg.lidar_vbeams), dtype=np.float32)

    origin = np.asarray(position, dtype=np.float32).reshape(3)
    x_axis, y_axis, z_axis = navrl_goal_frame_basis(relative_goal)
    horizontal_angles = np.linspace(-np.pi, np.pi, cfg.lidar_hbeams, endpoint=False, dtype=np.float32)
    vertical_angles = np.linspace(np.deg2rad(-10.0), np.deg2rad(20.0), cfg.lidar_vbeams, dtype=np.float32)
    ray_from: list[list[float]] = []
    ray_to: list[list[float]] = []
    for horizontal in horizontal_angles:
        for vertical in vertical_angles:
            direction_goal = np.asarray(
                [
                    np.cos(vertical) * np.cos(horizontal),
                    np.cos(vertical) * np.sin(horizontal),
                    np.sin(vertical),
                ],
                dtype=np.float32,
            )
            direction_world = (
                x_axis * direction_goal[0]
                + y_axis * direction_goal[1]
                + z_axis * direction_goal[2]
            ).astype(np.float32)
            direction_world /= max(float(np.linalg.norm(direction_world)), 1e-6)
            start = origin + direction_world * 0.08
            end = origin + direction_world * cfg.lidar_range
            ray_from.append(start.tolist())
            ray_to.append(end.tolist())
    results = p.rayTestBatch(ray_from, ray_to, physicsClientId=pybullet_client)
    scan = np.zeros((1, cfg.lidar_hbeams, cfg.lidar_vbeams), dtype=np.float32)
    for flat_index, hit in enumerate(results):
        body_id = int(hit[0])
        if body_id < 0 or body_id in ignore_body_ids:
            continue
        hit_fraction = float(hit[2])
        if not np.isfinite(hit_fraction) or hit_fraction < 0.0 or hit_fraction > 1.0:
            continue
        h_index = flat_index // cfg.lidar_vbeams
        v_index = flat_index % cfg.lidar_vbeams
        hit_distance = hit_fraction * cfg.lidar_range
        scan[0, h_index, v_index] = max(0.0, cfg.lidar_range - hit_distance) / cfg.lidar_range
    return np.clip(scan, 0.0, 1.0).astype(np.float32)


def _navrl_lidar_like_scan(
    position: np.ndarray,
    relative_goal: np.ndarray,
    scenario: ScenarioConfig,
    elapsed: float,
    cfg: FeatureScalingConfig,
) -> np.ndarray:
    scan = np.zeros((1, cfg.lidar_hbeams, cfg.lidar_vbeams), dtype=np.float32)
    horizontal_res = 2.0 * np.pi / float(cfg.lidar_hbeams)
    vertical_angles = np.linspace(np.deg2rad(-10.0), np.deg2rad(20.0), cfg.lidar_vbeams)
    for obstacle in scenario.all_obstacles():
        center = np.asarray(obstacle.position_at(elapsed), dtype=np.float32)
        relative_world = center - position
        relative = vec_to_navrl_goal_frame(relative_world, relative_goal)
        distance = float(np.linalg.norm(relative))
        if distance <= 1e-6 or distance > cfg.lidar_range + obstacle.radius:
            continue
        horizontal = float(np.arctan2(relative[1], relative[0]))
        h_index = int(np.floor((horizontal + np.pi) / horizontal_res)) % cfg.lidar_hbeams
        vertical = float(np.arctan2(relative[2], max(np.linalg.norm(relative[:2]), 1e-6)))
        v_index = int(np.argmin(np.abs(vertical_angles - vertical)))
        clearance = max(0.0, distance - float(obstacle.radius))
        value = max(0.0, cfg.lidar_range - clearance) / cfg.lidar_range
        h_spread = max(1, int(np.ceil(float(obstacle.radius) / max(distance * horizontal_res, 1e-6))))
        v_spread = cfg.lidar_vbeams if obstacle.kind == "cylinder" else 1
        for h_offset in range(-h_spread, h_spread + 1):
            h = (h_index + h_offset) % cfg.lidar_hbeams
            for v_offset in range(-v_spread, v_spread + 1):
                v = int(np.clip(v_index + v_offset, 0, cfg.lidar_vbeams - 1))
                scan[0, h, v] = max(scan[0, h, v], value)
    return np.clip(scan, 0.0, 1.0).astype(np.float32)


def _navrl_dynamic_obstacle_tensor(
    position: np.ndarray,
    velocity: np.ndarray,
    relative_goal: np.ndarray,
    scenario: ScenarioConfig,
    elapsed: float,
    cfg: FeatureScalingConfig,
) -> np.ndarray:
    rows: list[tuple[float, np.ndarray]] = []
    for obstacle in scenario.dynamic_obstacles:
        center = np.asarray(obstacle.position_at(elapsed), dtype=np.float32)
        rel_world = center - position
        distance_2d_raw = float(np.linalg.norm(rel_world[:2]))
        if distance_2d_raw > cfg.lidar_range:
            continue
        rel_goal = vec_to_navrl_goal_frame(rel_world, relative_goal)
        center_distance = max(float(np.linalg.norm(rel_goal)), 1e-6)
        rel_goal_unit = rel_goal / center_distance
        obs_vel = np.asarray(obstacle.velocity or (0.0, 0.0, 0.0), dtype=np.float32)
        if elapsed <= obstacle.start_time:
            obs_vel = np.zeros(3, dtype=np.float32)
        rel_vel_goal = vec_to_navrl_goal_frame(obs_vel - velocity, relative_goal) / max(cfg.max_dynamic_speed, 1e-6)
        width_category = min(max(float(obstacle.radius * 2.0) / 0.25 - 1.0, 0.0), 3.0) / 3.0
        height_value = float(obstacle.height or obstacle.radius * 2.0)
        height_category = 0.0 if height_value > 1.0 else height_value
        row = np.concatenate(
            [
                rel_goal_unit,
                np.asarray([distance_2d_raw / cfg.lidar_range, rel_goal[2] / cfg.arena_size], dtype=np.float32),
                rel_vel_goal,
                np.asarray([width_category, height_category], dtype=np.float32),
            ]
        ).astype(np.float32)
        rows.append((distance_2d_raw, row))
    rows.sort(key=lambda item: item[0])
    output = np.zeros((1, cfg.dyn_obs_num, 10), dtype=np.float32)
    for index, (_distance, row) in enumerate(rows[: cfg.dyn_obs_num]):
        output[0, index, :] = np.clip(row, -10.0, 10.0)
    return output
