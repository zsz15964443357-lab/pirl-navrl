#!/usr/bin/env python3
"""Host-side PyBullet mirror for the official EGO-Planner simulator loop."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import pybullet as p
import pybullet_data


class OfficialEgoMirrorViewer:
    def __init__(
        self,
        trace_path: Path,
        *,
        direct: bool,
        idle_timeout: float,
        startup_timeout: float,
        show_text: bool,
        point_size: float,
        map_style: str,
        voxel_size: float,
        max_voxels: int,
    ) -> None:
        self.trace_path = trace_path
        self.direct = direct
        self.idle_timeout = idle_timeout
        self.startup_timeout = startup_timeout
        self.show_text = show_text
        self.point_size = point_size
        self.map_style = map_style
        self.voxel_size = voxel_size
        self.max_voxels = max_voxels
        self.client = None
        self.drone = None
        self.goal_marker = None
        self.last_position = None
        self.last_command_position = None
        self.last_record_time = time.monotonic()
        self.scene_ready = False
        self.state_count = 0
        self.custom_map_publisher = False
        self.obstacle_bodies: dict[str, int] = {}

    def run(self) -> None:
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = p.connect(p.DIRECT if self.direct else p.GUI)
        self.configure_scene()

        offset = 0
        start_wait = time.monotonic()
        saw_record = False
        while True:
            if self.trace_path.exists():
                with self.trace_path.open("r", encoding="utf-8") as handle:
                    handle.seek(offset)
                    lines = handle.readlines()
                    offset = handle.tell()
                for line in lines:
                    if not line.strip():
                        continue
                    self.update(json.loads(line))
                    saw_record = True
                    self.last_record_time = time.monotonic()
            p.stepSimulation(physicsClientId=self.client)
            if not saw_record and time.monotonic() - start_wait > self.startup_timeout:
                raise TimeoutError(f"no records appeared in {self.trace_path} within {self.startup_timeout}s")
            if self.scene_ready and time.monotonic() - self.last_record_time > self.idle_timeout:
                break
            time.sleep(1.0 / 40.0)

    def close(self) -> None:
        if self.client is not None:
            p.disconnect(self.client)

    def configure_scene(self) -> None:
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.client)
        p.resetSimulation(physicsClientId=self.client)
        p.setGravity(0, 0, -9.81, physicsClientId=self.client)
        if not self.direct:
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1, physicsClientId=self.client)
            p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, physicsClientId=self.client)
            p.configureDebugVisualizer(p.COV_ENABLE_RGB_BUFFER_PREVIEW, 0, physicsClientId=self.client)
            p.configureDebugVisualizer(p.COV_ENABLE_DEPTH_BUFFER_PREVIEW, 0, physicsClientId=self.client)
            p.configureDebugVisualizer(p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW, 0, physicsClientId=self.client)
            p.resetDebugVisualizerCamera(
                cameraDistance=12.5,
                cameraYaw=-35,
                cameraPitch=-52,
                cameraTargetPosition=[0.0, 0.0, 1.0],
                physicsClientId=self.client,
            )
        p.loadURDF("plane.urdf", physicsClientId=self.client)
        self.create_axes()

    def update(self, record: dict) -> None:
        record_type = record.get("record_type", "state")
        if record_type == "metadata":
            self.custom_map_publisher = bool(record.get("custom_map_publisher"))
            self.create_goal_marker(record.get("goal"))
            return
        if record_type == "map":
            self.create_map(record["points"])
            self.scene_ready = True
            return
        if record_type != "state":
            return

        position = record.get("odom_position")
        if position is None:
            return
        self.update_obstacles(record.get("obstacle_positions") or [])
        self.scene_ready = True
        if self.drone is None:
            self.drone = self.create_sphere(position, 0.28, [1.0, 0.78, 0.02, 1.0])
        else:
            p.resetBasePositionAndOrientation(self.drone, position, [0, 0, 0, 1], physicsClientId=self.client)
        if self.last_position is not None:
            p.addUserDebugLine(
                self.last_position,
                position,
                lineColorRGB=[1.0, 0.82, 0.05],
                lineWidth=3.0,
                lifeTime=0,
                physicsClientId=self.client,
            )
        self.last_position = position

        command_position = record.get("ego_command_position")
        if command_position is not None:
            if self.last_command_position is not None:
                p.addUserDebugLine(
                    self.last_command_position,
                    command_position,
                    lineColorRGB=[0.1, 0.9, 0.25],
                    lineWidth=2.0,
                    lifeTime=0,
                    physicsClientId=self.client,
                )
            self.last_command_position = command_position

        self.state_count += 1
        if self.show_text and self.state_count % 25 == 0:
            distance_to_goal = record.get("distance_to_goal")
            distance_text = "nan" if distance_to_goal is None else f"{distance_to_goal:.2f}"
            p.addUserDebugText(
                f"official EGO  dist={distance_text}  cmd={record.get('command_received')}",
                [-21.0, -10.0, 3.2],
                textColorRGB=[1.0, 1.0, 1.0],
                textSize=1.2,
                lifeTime=1.0,
                physicsClientId=self.client,
            )

    def create_map(self, points: list[list[float]]) -> None:
        if not points:
            return
        if self.custom_map_publisher and self.map_style == "voxels":
            return
        if self.map_style in {"voxels", "both"}:
            self.create_voxel_map(points)
        if self.map_style in {"points", "both"}:
            colors = [[0.9, 0.18, 0.08] for _ in points]
            p.addUserDebugPoints(
                points,
                colors,
                pointSize=self.point_size,
                lifeTime=0,
                physicsClientId=self.client,
            )

    def create_voxel_map(self, points: list[list[float]]) -> None:
        columns = voxel_columns(points, self.voxel_size, self.max_voxels)
        for center, half_extents in columns:
            visual = p.createVisualShape(
                p.GEOM_BOX,
                halfExtents=half_extents,
                rgbaColor=[0.86, 0.12, 0.06, 0.88],
                physicsClientId=self.client,
            )
            p.createMultiBody(
                baseMass=0.0,
                baseCollisionShapeIndex=-1,
                baseVisualShapeIndex=visual,
                basePosition=center,
                physicsClientId=self.client,
            )

    def update_obstacles(self, obstacles: list[dict]) -> None:
        for obstacle in obstacles:
            obstacle_id = str(obstacle.get("obstacle_id"))
            position = obstacle.get("position")
            if position is None:
                continue
            if obstacle_id not in self.obstacle_bodies:
                self.obstacle_bodies[obstacle_id] = self.create_obstacle_body(obstacle)
            p.resetBasePositionAndOrientation(
                self.obstacle_bodies[obstacle_id],
                position,
                [0, 0, 0, 1],
                physicsClientId=self.client,
            )

    def create_obstacle_body(self, obstacle: dict) -> int:
        kind = obstacle.get("kind")
        radius = float(obstacle.get("radius") or 0.5)
        height = float(obstacle.get("height") or 1.0)
        if kind == "sphere":
            collision = p.createCollisionShape(p.GEOM_SPHERE, radius=radius, physicsClientId=self.client)
            visual = p.createVisualShape(
                p.GEOM_SPHERE,
                radius=radius,
                rgbaColor=[0.86, 0.12, 0.06, 0.9],
                physicsClientId=self.client,
            )
        else:
            collision = p.createCollisionShape(
                p.GEOM_CYLINDER,
                radius=radius,
                height=height,
                physicsClientId=self.client,
            )
            visual = p.createVisualShape(
                p.GEOM_CYLINDER,
                radius=radius,
                length=height,
                rgbaColor=[0.86, 0.12, 0.06, 0.9],
                physicsClientId=self.client,
            )
        return p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=obstacle.get("position", [0, 0, 1]),
            physicsClientId=self.client,
        )

    def create_goal_marker(self, goal: list[float] | None) -> None:
        if goal is None or self.goal_marker is not None:
            return
        self.goal_marker = self.create_sphere(goal, 0.42, [0.05, 0.85, 0.25, 1.0])

    def create_axes(self) -> None:
        p.addUserDebugLine([-22, 0, 0.03], [2, 0, 0.03], [0.7, 0.7, 0.7], 1.0, physicsClientId=self.client)
        p.addUserDebugLine([-18, -12, 0.03], [-18, 14, 0.03], [0.7, 0.7, 0.7], 1.0, physicsClientId=self.client)
        p.addUserDebugLine([-7, 0, 0.05], [7, 0, 0.05], [0.35, 0.35, 0.35], 1.2, physicsClientId=self.client)
        p.addUserDebugLine([0, -4, 0.05], [0, 4, 0.05], [0.35, 0.35, 0.35], 1.2, physicsClientId=self.client)

    def create_sphere(self, position: list[float], radius: float, color: list[float]) -> int:
        collision = p.createCollisionShape(p.GEOM_SPHERE, radius=radius, physicsClientId=self.client)
        visual = p.createVisualShape(p.GEOM_SPHERE, radius=radius, rgbaColor=color, physicsClientId=self.client)
        return p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=position,
            physicsClientId=self.client,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--idle-timeout", type=float, default=10.0)
    parser.add_argument("--startup-timeout", type=float, default=90.0)
    parser.add_argument("--show-text", action="store_true")
    parser.add_argument("--point-size", type=float, default=2.2)
    parser.add_argument("--map-style", choices=("voxels", "points", "both"), default="voxels")
    parser.add_argument("--voxel-size", type=float, default=0.85)
    parser.add_argument("--max-voxels", type=int, default=900)
    return parser.parse_args()


def voxel_columns(
    points: list[list[float]],
    voxel_size: float,
    max_voxels: int,
) -> list[tuple[list[float], list[float]]]:
    bins: dict[tuple[int, int], list[float]] = {}
    for point in points:
        ix = math.floor(point[0] / voxel_size)
        iy = math.floor(point[1] / voxel_size)
        key = (ix, iy)
        z_value = point[2]
        if key not in bins:
            bins[key] = [point[0], point[1], z_value, z_value, 1.0]
            continue
        item = bins[key]
        item[0] += point[0]
        item[1] += point[1]
        item[2] = min(item[2], z_value)
        item[3] = max(item[3], z_value)
        item[4] += 1.0

    ranked = sorted(bins.values(), key=lambda item: (-item[4], item[0] / item[4], item[1] / item[4]))
    columns = []
    half_xy = voxel_size * 0.43
    for item in ranked[:max_voxels]:
        count = item[4]
        x = item[0] / count
        y = item[1] / count
        z_min = max(0.0, item[2])
        z_max = max(z_min + voxel_size * 0.7, item[3])
        center = [x, y, (z_min + z_max) / 2.0]
        half_extents = [half_xy, half_xy, max(0.18, (z_max - z_min) / 2.0)]
        columns.append((center, half_extents))
    return columns


def main() -> None:
    args = parse_args()
    viewer = OfficialEgoMirrorViewer(
        args.trace,
        direct=args.direct,
        idle_timeout=args.idle_timeout,
        startup_timeout=args.startup_timeout,
        show_text=args.show_text,
        point_size=args.point_size,
        map_style=args.map_style,
        voxel_size=args.voxel_size,
        max_voxels=args.max_voxels,
    )
    try:
        viewer.run()
    finally:
        viewer.close()


if __name__ == "__main__":
    main()
