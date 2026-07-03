#!/usr/bin/env python3
"""Live PyBullet viewer for an official EGO -> PyBullet bridge trace."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pybullet as p
import pybullet_data


def main() -> None:
    args = parse_args()
    viewer = LiveTraceViewer(args.trace, direct=args.direct, show_text=args.show_text)
    try:
        viewer.run()
    finally:
        viewer.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--idle-timeout", type=float, default=8.0)
    parser.add_argument("--show-text", action="store_true")
    return parser.parse_args()


class LiveTraceViewer:
    def __init__(
        self,
        trace_path: Path,
        *,
        direct: bool = False,
        idle_timeout: float = 8.0,
        show_text: bool = False,
    ) -> None:
        self.trace_path = trace_path
        self.direct = direct
        self.idle_timeout = idle_timeout
        self.show_text = show_text
        self.client = None
        self.drone = None
        self.scene_ready = False
        self.last_position = None
        self.last_command_position = None
        self.line_counter = 0
        self.last_record_time = time.monotonic()

    def run(self) -> None:
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = p.connect(p.DIRECT if self.direct else p.GUI)
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
                cameraDistance=7.6,
                cameraYaw=8,
                cameraPitch=-48,
                cameraTargetPosition=[0.0, 0.0, 1.0],
                physicsClientId=self.client,
            )

        offset = 0
        while True:
            if self.trace_path.exists():
                with self.trace_path.open("r", encoding="utf-8") as handle:
                    handle.seek(offset)
                    lines = handle.readlines()
                    offset = handle.tell()
                for line in lines:
                    if line.strip():
                        self.update(json.loads(line))
                        self.last_record_time = time.monotonic()
            p.stepSimulation(physicsClientId=self.client)
            if time.monotonic() - self.last_record_time > self.idle_timeout and self.scene_ready:
                break
            time.sleep(1.0 / 30.0)

    def close(self) -> None:
        if self.client is not None:
            p.disconnect(self.client)

    def update(self, record: dict) -> None:
        if not self.scene_ready:
            self.create_scene(record)
            self.scene_ready = True
        position = record["position"]
        if self.drone is not None:
            p.resetBasePositionAndOrientation(self.drone, position, [0, 0, 0, 1], physicsClientId=self.client)
        if self.last_position is not None:
            p.addUserDebugLine(
                self.last_position,
                position,
                lineColorRGB=[1.0, 0.84, 0.08],
                lineWidth=2.5,
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
                    lineColorRGB=[0.05, 0.9, 0.25],
                    lineWidth=1.5,
                    lifeTime=0,
                    physicsClientId=self.client,
                )
            self.last_command_position = command_position

        self.line_counter += 1
        if self.show_text and self.line_counter % 20 == 0:
            text = (
                f"step={record['step']} dist={record['distance_to_goal']:.2f} "
                f"clearance={record['min_clearance']:.2f} command={record['command_received']}"
            )
            p.addUserDebugText(
                text,
                [-5.7, 3.65, 2.7],
                textColorRGB=[1, 1, 1],
                textSize=1.1,
                lifeTime=1.0,
                physicsClientId=self.client,
            )

    def create_scene(self, record: dict) -> None:
        p.loadURDF("plane.urdf", physicsClientId=self.client)
        for obstacle in record["obstacles"]:
            self.create_obstacle(obstacle)
        self.create_sphere(record["position"], 0.13, [0.05, 0.35, 1.0, 1.0])
        self.create_sphere(record["goal"], 0.2, [0.05, 0.85, 0.25, 1.0])
        self.drone = self.create_sphere(record["position"], 0.17, [1.0, 0.78, 0.02, 1.0])

    def create_obstacle(self, obstacle: dict) -> None:
        if obstacle["kind"] == "box":
            half_extents = [value / 2.0 for value in obstacle["size"]]
            collision = p.createCollisionShape(p.GEOM_BOX, halfExtents=half_extents, physicsClientId=self.client)
            visual = p.createVisualShape(
                p.GEOM_BOX,
                halfExtents=half_extents,
                rgbaColor=[0.72, 0.18, 0.15, 1.0],
                physicsClientId=self.client,
            )
        elif obstacle["kind"] == "cylinder":
            collision = p.createCollisionShape(
                p.GEOM_CYLINDER,
                radius=obstacle["radius"],
                height=obstacle["height"],
                physicsClientId=self.client,
            )
            visual = p.createVisualShape(
                p.GEOM_CYLINDER,
                radius=obstacle["radius"],
                length=obstacle["height"],
                rgbaColor=[0.72, 0.18, 0.15, 1.0],
                physicsClientId=self.client,
            )
        else:
            collision = p.createCollisionShape(
                p.GEOM_SPHERE,
                radius=obstacle["radius"],
                physicsClientId=self.client,
            )
            visual = p.createVisualShape(
                p.GEOM_SPHERE,
                radius=obstacle["radius"],
                rgbaColor=[0.18, 0.3, 0.82, 1.0],
                physicsClientId=self.client,
            )
        p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=obstacle["center"],
            physicsClientId=self.client,
        )

    def create_sphere(self, position, radius: float, color: list[float]) -> int:
        collision = p.createCollisionShape(p.GEOM_SPHERE, radius=radius, physicsClientId=self.client)
        visual = p.createVisualShape(p.GEOM_SPHERE, radius=radius, rgbaColor=color, physicsClientId=self.client)
        return p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=position,
            physicsClientId=self.client,
        )


if __name__ == "__main__":
    main()
