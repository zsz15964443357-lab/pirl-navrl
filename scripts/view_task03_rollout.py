#!/usr/bin/env python3
"""Visualize a TASK_03 diagnostic rollout JSONL trace in PyBullet."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--realtime", type=float, default=0.04)
    return parser.parse_args()


def load_trace(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None]:
    metadata: dict[str, Any] = {}
    steps: list[dict[str, Any]] = []
    summary: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        record_type = record.get("record_type")
        if record_type == "metadata":
            metadata = record
        elif record_type in {"initial_state", "step"}:
            steps.append(record)
        elif record_type == "summary":
            summary = record
    return metadata, steps, summary


class Task03RolloutViewer:
    def __init__(self, trace_path: Path, *, direct: bool, realtime: float) -> None:
        self.trace_path = trace_path
        self.direct = direct
        self.realtime = realtime
        self.client = None
        self.drone = None
        self.last_position: list[float] | None = None
        self.last_action_line: int | None = None

    def run(self) -> None:
        try:
            import pybullet as p
            import pybullet_data
        except ImportError as exc:
            raise RuntimeError("PyBullet is required for TASK_03 visualization") from exc

        self.p = p
        self.client = p.connect(p.DIRECT if self.direct else p.GUI)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.client)
        p.resetSimulation(physicsClientId=self.client)
        p.setGravity(0, 0, -9.81, physicsClientId=self.client)
        if not self.direct:
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1, physicsClientId=self.client)
            p.resetDebugVisualizerCamera(
                cameraDistance=10.5,
                cameraYaw=-35,
                cameraPitch=-48,
                cameraTargetPosition=[0.0, 0.0, 1.0],
                physicsClientId=self.client,
            )
        p.loadURDF("plane.urdf", physicsClientId=self.client)

        metadata, steps, summary = load_trace(self.trace_path)
        scenario = metadata.get("scenario") or {}
        self.draw_scenario(scenario)
        for step in steps:
            self.update_step(step)
            p.stepSimulation(physicsClientId=self.client)
            if not self.direct:
                time.sleep(self.realtime)
        if summary is not None:
            self.draw_status(summary)
        if self.direct:
            p.disconnect(physicsClientId=self.client)
            return
        while p.isConnected(self.client):
            p.stepSimulation(physicsClientId=self.client)
            time.sleep(1.0 / 30.0)

    def draw_scenario(self, scenario: dict[str, Any]) -> None:
        self.draw_bounds(scenario.get("bounds") or {})
        start = scenario.get("start")
        goal = scenario.get("goal")
        if start is not None:
            self.create_sphere(start, 0.22, [0.1, 0.35, 0.95, 1.0])
        if goal is not None:
            self.create_sphere(goal, 0.32, [0.0, 0.8, 0.25, 1.0])
        for obstacle in scenario.get("static_obstacles") or []:
            self.create_obstacle(obstacle)
        for obstacle in scenario.get("dynamic_obstacles") or []:
            self.create_obstacle(obstacle)

    def draw_bounds(self, bounds: dict[str, Any]) -> None:
        x = bounds.get("x", [-5.0, 5.0])
        y = bounds.get("y", [-5.0, 5.0])
        z = 0.04
        corners = [[x[0], y[0], z], [x[1], y[0], z], [x[1], y[1], z], [x[0], y[1], z]]
        for index in range(4):
            self.p.addUserDebugLine(
                corners[index],
                corners[(index + 1) % 4],
                [0.35, 0.35, 0.35],
                1.5,
                physicsClientId=self.client,
            )

    def update_step(self, step: dict[str, Any]) -> None:
        position = step["position"]
        action = step.get("action") or [0.0, 0.0, 0.0]
        if self.drone is None:
            self.drone = self.create_sphere(position, 0.2, [1.0, 0.75, 0.05, 1.0])
        else:
            self.p.resetBasePositionAndOrientation(
                self.drone,
                position,
                [0, 0, 0, 1],
                physicsClientId=self.client,
            )
        if self.last_position is not None:
            self.p.addUserDebugLine(
                self.last_position,
                position,
                [1.0, 0.75, 0.05],
                2.0,
                physicsClientId=self.client,
            )
        self.last_position = position
        end = [position[i] + action[i] * 0.7 for i in range(3)]
        if self.last_action_line is not None:
            self.p.removeUserDebugItem(self.last_action_line, physicsClientId=self.client)
        self.last_action_line = self.p.addUserDebugLine(
            position,
            end,
            [0.0, 0.95, 1.0],
            3.0,
            physicsClientId=self.client,
        )

    def draw_status(self, summary: dict[str, Any]) -> None:
        status = "collision" if summary.get("collision") else "success" if summary.get("success") else "timeout"
        task_id = summary.get("task_id", "TASK")
        self.p.addUserDebugText(
            f"{task_id} {status} steps={summary.get('steps')} dist={summary.get('final_distance_to_goal'):.2f}",
            [-4.8, -4.8, 2.8],
            textColorRGB=[1.0, 1.0, 1.0],
            textSize=1.1,
            lifeTime=0,
            physicsClientId=self.client,
        )

    def create_obstacle(self, obstacle: dict[str, Any]) -> int:
        position = obstacle["position"]
        radius = float(obstacle.get("radius") or 0.5)
        if obstacle.get("kind") == "sphere":
            return self.create_sphere(position, radius, [0.86, 0.12, 0.06, 0.9])
        height = float(obstacle.get("height") or 1.0)
        collision = self.p.createCollisionShape(
            self.p.GEOM_CYLINDER,
            radius=radius,
            height=height,
            physicsClientId=self.client,
        )
        visual = self.p.createVisualShape(
            self.p.GEOM_CYLINDER,
            radius=radius,
            length=height,
            rgbaColor=[0.86, 0.12, 0.06, 0.9],
            physicsClientId=self.client,
        )
        return self.p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=position,
            physicsClientId=self.client,
        )

    def create_sphere(self, position: list[float], radius: float, color: list[float]) -> int:
        collision = self.p.createCollisionShape(
            self.p.GEOM_SPHERE,
            radius=radius,
            physicsClientId=self.client,
        )
        visual = self.p.createVisualShape(
            self.p.GEOM_SPHERE,
            radius=radius,
            rgbaColor=color,
            physicsClientId=self.client,
        )
        return self.p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=position,
            physicsClientId=self.client,
        )


def main() -> None:
    args = parse_args()
    viewer = Task03RolloutViewer(args.trace, direct=args.direct, realtime=args.realtime)
    viewer.run()


if __name__ == "__main__":
    main()
