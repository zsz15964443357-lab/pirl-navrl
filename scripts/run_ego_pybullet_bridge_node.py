#!/usr/bin/env python3
"""ROS-side bridge node for official EGO-Planner -> PyBullet diagnostics.

This file intentionally avoids importing the Python package because ROS Noetic
uses Python 3.8 while the main project targets Python 3.10+.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import rospy
import sensor_msgs.point_cloud2 as pc2
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from quadrotor_msgs.msg import PositionCommand
from sensor_msgs.msg import PointCloud2


START = (-4.0, 0.0, 1.0)
GOAL = (4.0, 0.0, 1.0)
OBSTACLES = (
    {"kind": "cylinder", "center": (-1.7, -0.25, 1.0), "radius": 0.45, "height": 2.0},
    {"kind": "cylinder", "center": (0.25, 0.35, 1.0), "radius": 0.55, "height": 2.0},
    {"kind": "sphere", "center": (1.85, -0.45, 1.15), "radius": 0.45, "height": None},
)
MOCKAMAP_BOX_START = (-4.2, 0.0, 1.0)
MOCKAMAP_BOX_GOAL = (4.2, 0.0, 1.0)
MOCKAMAP_BOX_OBSTACLES = (
    {"kind": "box", "center": (-1.6, -0.15, 1.0), "size": (0.8, 2.0, 2.0)},
    {"kind": "box", "center": (0.55, 0.75, 1.0), "size": (0.8, 1.9, 2.0)},
    {"kind": "box", "center": (2.25, -0.45, 1.0), "size": (0.75, 1.7, 2.0)},
)
SCENES = {
    "ego_like_static_v0": {
        "start": START,
        "goal": GOAL,
        "obstacles": OBSTACLES,
        "bounds": ((-5.0, 5.0), (-5.0, 5.0), (0.0, 3.0)),
    },
    "ego_mockamap_box_v0": {
        "start": MOCKAMAP_BOX_START,
        "goal": MOCKAMAP_BOX_GOAL,
        "obstacles": MOCKAMAP_BOX_OBSTACLES,
        "bounds": ((-5.0, 5.0), (-3.0, 3.0), (0.0, 3.0)),
    },
}


class EgoPybulletBridgeNode:
    def __init__(
        self,
        output_path: Path,
        duration: float,
        rate_hz: float,
        kp: float,
        max_speed: float,
        goal_delay: float,
        scene_id: str,
        pybullet_gui: bool,
    ) -> None:
        self.output_path = output_path
        self.duration = duration
        self.rate_hz = rate_hz
        self.kp = kp
        self.max_speed = max_speed
        self.goal_delay = goal_delay
        self.scene_id = scene_id
        self.scene = SCENES[scene_id]
        self.goal_published = False
        self.position = list(self.scene["start"])
        self.velocity = [0.0, 0.0, 0.0]
        self.last_command = None
        self.records = 0
        self.min_clearance = float("inf")
        self.pybullet_gui = pybullet_gui
        self.pybullet = None
        self.pybullet_client = None
        self.drone_body = None
        self.trail_counter = 0
        self.odom_pub = rospy.Publisher("/visual_slam/odom", Odometry, queue_size=10)
        self.cloud_pub = rospy.Publisher("/pirl_navrl/cloud", PointCloud2, queue_size=3)
        self.goal_pub = rospy.Publisher("/move_base_simple/goal", PoseStamped, queue_size=1, latch=True)
        self.cmd_sub = rospy.Subscriber("/planning/pos_cmd", PositionCommand, self.command_callback, queue_size=10)
        self.pointcloud_points = sample_obstacle_points(self.scene["obstacles"], resolution=0.2)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.output_path.open("w", encoding="utf-8")
        if self.pybullet_gui:
            self.start_pybullet_gui()

    def command_callback(self, msg: PositionCommand) -> None:
        self.last_command = msg

    def close(self) -> None:
        self.handle.close()
        if self.pybullet is not None and self.pybullet_client is not None:
            self.pybullet.disconnect(self.pybullet_client)

    def run(self) -> dict:
        rate = rospy.Rate(self.rate_hz)
        start_time = rospy.Time.now()
        previous_time = start_time
        while not rospy.is_shutdown():
            now = rospy.Time.now()
            elapsed = (now - start_time).to_sec()
            if elapsed >= self.duration:
                break
            dt = max((now - previous_time).to_sec(), 1.0 / self.rate_hz)
            previous_time = now

            desired_velocity = self.compute_desired_velocity()
            self.velocity = list(desired_velocity)
            self.position = clamp_position(
                (
                    self.position[0] + self.velocity[0] * dt,
                    self.position[1] + self.velocity[1] * dt,
                    self.position[2] + self.velocity[2] * dt,
                )
            )
            clearance = min_clearance(self.position)
            self.min_clearance = min(self.min_clearance, clearance)
            distance_to_goal = distance(self.position, self.scene["goal"])

            self.publish_odom(now)
            self.publish_cloud(now)
            if elapsed >= self.goal_delay and not self.goal_published:
                self.publish_goal(now)
                self.goal_published = True
            self.update_pybullet_gui()
            self.write_record(elapsed, desired_velocity, clearance, distance_to_goal)
            self.records += 1
            if distance_to_goal < 0.35 and self.last_command is not None:
                break
            rate.sleep()

        summary = {
            "records": self.records,
            "final_position": self.position,
            "final_distance_to_goal": distance(self.position, self.scene["goal"]),
            "min_clearance": self.min_clearance,
            "command_received": self.last_command is not None,
            "output_path": str(self.output_path),
            "scene_id": self.scene_id,
        }
        return summary

    def compute_desired_velocity(self) -> tuple[float, float, float]:
        if self.last_command is None:
            return (0.0, 0.0, 0.0)
        target = (
            self.last_command.position.x,
            self.last_command.position.y,
            self.last_command.position.z,
        )
        feed_forward = (
            self.last_command.velocity.x,
            self.last_command.velocity.y,
            self.last_command.velocity.z,
        )
        raw = tuple(feed_forward[i] + self.kp * (target[i] - self.position[i]) for i in range(3))
        return clip_norm(raw, self.max_speed)

    def publish_odom(self, stamp: rospy.Time) -> None:
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = "world"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = self.position[0]
        odom.pose.pose.position.y = self.position[1]
        odom.pose.pose.position.z = self.position[2]
        odom.pose.pose.orientation.w = 1.0
        odom.twist.twist.linear.x = self.velocity[0]
        odom.twist.twist.linear.y = self.velocity[1]
        odom.twist.twist.linear.z = self.velocity[2]
        self.odom_pub.publish(odom)

    def publish_cloud(self, stamp: rospy.Time) -> None:
        header = rospy.Header()
        header.stamp = stamp
        header.frame_id = "world"
        cloud = pc2.create_cloud_xyz32(header, self.pointcloud_points)
        self.cloud_pub.publish(cloud)

    def publish_goal(self, stamp: rospy.Time) -> None:
        goal = PoseStamped()
        goal.header.stamp = stamp
        goal.header.frame_id = "world"
        goal.pose.position.x = self.scene["goal"][0]
        goal.pose.position.y = self.scene["goal"][1]
        goal.pose.position.z = self.scene["goal"][2]
        goal.pose.orientation.w = 1.0
        self.goal_pub.publish(goal)

    def start_pybullet_gui(self) -> None:
        import pybullet as pybullet
        import pybullet_data

        self.pybullet = pybullet
        self.pybullet_client = pybullet.connect(pybullet.GUI)
        pybullet.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.pybullet_client)
        pybullet.resetSimulation(physicsClientId=self.pybullet_client)
        pybullet.setGravity(0, 0, -9.81, physicsClientId=self.pybullet_client)
        pybullet.configureDebugVisualizer(pybullet.COV_ENABLE_GUI, 1, physicsClientId=self.pybullet_client)
        pybullet.loadURDF("plane.urdf", physicsClientId=self.pybullet_client)
        pybullet.resetDebugVisualizerCamera(
            cameraDistance=8.5,
            cameraYaw=0,
            cameraPitch=-52,
            cameraTargetPosition=[0.0, 0.0, 1.0],
            physicsClientId=self.pybullet_client,
        )
        for obstacle in self.scene["obstacles"]:
            self.create_obstacle_body(obstacle)
        self.create_sphere(self.scene["start"], 0.13, [0.1, 0.45, 1.0, 1.0])
        self.create_sphere(self.scene["goal"], 0.16, [0.1, 0.85, 0.25, 1.0])
        self.drone_body = self.create_sphere(self.position, 0.14, [1.0, 0.82, 0.08, 1.0])

    def create_obstacle_body(self, obstacle: dict[str, Any]) -> None:
        pybullet = self.pybullet
        assert pybullet is not None and self.pybullet_client is not None
        if obstacle["kind"] == "box":
            half_extents = [value / 2.0 for value in obstacle["size"]]
            collision = pybullet.createCollisionShape(
                pybullet.GEOM_BOX,
                halfExtents=half_extents,
                physicsClientId=self.pybullet_client,
            )
            visual = pybullet.createVisualShape(
                pybullet.GEOM_BOX,
                halfExtents=half_extents,
                rgbaColor=[0.78, 0.2, 0.16, 1.0],
                physicsClientId=self.pybullet_client,
            )
        elif obstacle["kind"] == "cylinder":
            collision = pybullet.createCollisionShape(
                pybullet.GEOM_CYLINDER,
                radius=obstacle["radius"],
                height=obstacle["height"],
                physicsClientId=self.pybullet_client,
            )
            visual = pybullet.createVisualShape(
                pybullet.GEOM_CYLINDER,
                radius=obstacle["radius"],
                length=obstacle["height"],
                rgbaColor=[0.78, 0.2, 0.16, 1.0],
                physicsClientId=self.pybullet_client,
            )
        else:
            collision = pybullet.createCollisionShape(
                pybullet.GEOM_SPHERE,
                radius=obstacle["radius"],
                physicsClientId=self.pybullet_client,
            )
            visual = pybullet.createVisualShape(
                pybullet.GEOM_SPHERE,
                radius=obstacle["radius"],
                rgbaColor=[0.18, 0.3, 0.82, 1.0],
                physicsClientId=self.pybullet_client,
            )
        pybullet.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=obstacle["center"],
            physicsClientId=self.pybullet_client,
        )

    def create_sphere(self, position, radius: float, color: list[float]) -> int:
        pybullet = self.pybullet
        assert pybullet is not None and self.pybullet_client is not None
        collision = pybullet.createCollisionShape(pybullet.GEOM_SPHERE, radius=radius, physicsClientId=self.pybullet_client)
        visual = pybullet.createVisualShape(
            pybullet.GEOM_SPHERE,
            radius=radius,
            rgbaColor=color,
            physicsClientId=self.pybullet_client,
        )
        return pybullet.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=position,
            physicsClientId=self.pybullet_client,
        )

    def update_pybullet_gui(self) -> None:
        if self.pybullet is None or self.pybullet_client is None or self.drone_body is None:
            return
        self.pybullet.resetBasePositionAndOrientation(
            self.drone_body,
            self.position,
            [0, 0, 0, 1],
            physicsClientId=self.pybullet_client,
        )
        self.trail_counter += 1
        if self.trail_counter % 8 == 0:
            self.create_sphere(self.position, 0.035, [1.0, 0.9, 0.1, 0.85])
        if self.last_command is not None and self.trail_counter % 12 == 0:
            self.create_sphere(
                [
                    self.last_command.position.x,
                    self.last_command.position.y,
                    self.last_command.position.z,
                ],
                0.03,
                [0.1, 0.9, 0.25, 0.9],
            )
        self.pybullet.stepSimulation(physicsClientId=self.pybullet_client)

    def write_record(
        self,
        elapsed: float,
        desired_velocity: tuple[float, float, float],
        clearance: float,
        distance_to_goal: float,
    ) -> None:
        command_position = None
        command_velocity = None
        if self.last_command is not None:
            command_position = [
                self.last_command.position.x,
                self.last_command.position.y,
                self.last_command.position.z,
            ]
            command_velocity = [
                self.last_command.velocity.x,
                self.last_command.velocity.y,
                self.last_command.velocity.z,
            ]
        record = {
            "task_id": "TASK_02",
            "output_type": "diagnostic",
            "platform_id": "gym_pybullet_drones_pybullet",
            "external_planner": "ego_planner_official_sidecar",
            "bridge_status": "official_ego_ros_sidecar",
            "planner_mode": "official_ego_planner",
            "scenario_id": self.scene_id,
            "seed": 0,
            "step": self.records,
            "elapsed": elapsed,
            "position": self.position,
            "goal": list(self.scene["goal"]),
            "desired_velocity": list(desired_velocity),
            "ego_command_position": command_position,
            "ego_command_velocity": command_velocity,
            "command_received": self.last_command is not None,
            "goal_published": self.goal_published,
            "min_clearance": clearance,
            "distance_to_goal": distance_to_goal,
            "obstacles": self.scene["obstacles"],
            "pointcloud_points": len(self.pointcloud_points),
        }
        self.handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.handle.flush()


def sample_obstacle_points(obstacles, resolution: float) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for obstacle in obstacles:
        if obstacle["kind"] == "box":
            points.extend(sample_box_points(obstacle["center"], obstacle["size"], resolution))
            continue
        center = obstacle["center"]
        radius = obstacle["radius"]
        if obstacle["kind"] == "sphere":
            rings = max(4, int(math.ceil(math.pi * radius / resolution)))
            columns = max(8, int(math.ceil(2.0 * math.pi * radius / resolution)))
            for ring in range(rings + 1):
                phi = math.pi * ring / rings
                z = center[2] + radius * math.cos(phi)
                radial = radius * math.sin(phi)
                for column in range(columns):
                    theta = 2.0 * math.pi * column / columns
                    points.append((center[0] + radial * math.cos(theta), center[1] + radial * math.sin(theta), z))
        else:
            height = obstacle["height"] or 2.0
            columns = max(8, int(math.ceil(2.0 * math.pi * radius / resolution)))
            layers = max(2, int(math.ceil(height / resolution)))
            bottom = center[2] - height / 2.0
            for layer in range(layers + 1):
                z = bottom + height * layer / layers
                for column in range(columns):
                    theta = 2.0 * math.pi * column / columns
                    points.append((center[0] + radius * math.cos(theta), center[1] + radius * math.sin(theta), z))
    return points


def sample_box_points(center, size, resolution: float) -> list[tuple[float, float, float]]:
    sx, sy, sz = size
    nx = max(2, int(math.ceil(sx / resolution)))
    ny = max(2, int(math.ceil(sy / resolution)))
    nz = max(2, int(math.ceil(sz / resolution)))
    xs = [center[0] - sx / 2.0 + sx * i / nx for i in range(nx + 1)]
    ys = [center[1] - sy / 2.0 + sy * i / ny for i in range(ny + 1)]
    zs = [center[2] - sz / 2.0 + sz * i / nz for i in range(nz + 1)]
    points: list[tuple[float, float, float]] = []
    for x in xs:
        for y in ys:
            for z in zs:
                on_surface = (
                    x in (xs[0], xs[-1])
                    or y in (ys[0], ys[-1])
                    or z in (zs[0], zs[-1])
                )
                if on_surface:
                    points.append((x, y, z))
    return points


def clip_norm(vector: tuple[float, float, float], max_norm: float) -> tuple[float, float, float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0 or norm <= max_norm:
        return vector
    scale = max_norm / norm
    return (vector[0] * scale, vector[1] * scale, vector[2] * scale)


def clamp_position(position: tuple[float, float, float]) -> list[float]:
    bounds = ACTIVE_BOUNDS
    return [
        min(max(position[0], bounds[0][0]), bounds[0][1]),
        min(max(position[1], bounds[1][0]), bounds[1][1]),
        min(max(position[2], bounds[2][0]), bounds[2][1]),
    ]


def min_clearance(position: list[float]) -> float:
    return min(clearance_to_obstacle(position, obstacle) for obstacle in ACTIVE_OBSTACLES)


def clearance_to_obstacle(position: list[float], obstacle: dict) -> float:
    center = obstacle["center"]
    if obstacle["kind"] == "box":
        dx = abs(position[0] - center[0]) - obstacle["size"][0] / 2.0
        dy = abs(position[1] - center[1]) - obstacle["size"][1] / 2.0
        dz = abs(position[2] - center[2]) - obstacle["size"][2] / 2.0
        outside = math.sqrt(sum(max(value, 0.0) ** 2 for value in (dx, dy, dz)))
        inside = min(max(dx, max(dy, dz)), 0.0)
        return outside + inside
    if obstacle["kind"] == "sphere":
        return distance(position, center) - obstacle["radius"]
    height = obstacle["height"] or 2.0
    horizontal = math.hypot(position[0] - center[0], position[1] - center[1]) - obstacle["radius"]
    vertical_excess = max(abs(position[2] - center[2]) - height / 2.0, 0.0)
    if vertical_excess == 0.0:
        return horizontal
    return math.hypot(max(horizontal, 0.0), vertical_excess)


def distance(left, right) -> float:
    return math.sqrt(sum((left[i] - right[i]) ** 2 for i in range(3)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=18.0)
    parser.add_argument("--rate-hz", type=float, default=20.0)
    parser.add_argument("--kp", type=float, default=1.4)
    parser.add_argument("--max-speed", type=float, default=1.25)
    parser.add_argument("--goal-delay", type=float, default=3.0)
    parser.add_argument("--scene", choices=sorted(SCENES), default="ego_mockamap_box_v0")
    parser.add_argument("--pybullet-gui", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global ACTIVE_BOUNDS, ACTIVE_OBSTACLES
    ACTIVE_BOUNDS = SCENES[args.scene]["bounds"]
    ACTIVE_OBSTACLES = SCENES[args.scene]["obstacles"]
    rospy.init_node("pirl_navrl_ego_pybullet_bridge")
    node = EgoPybulletBridgeNode(
        args.output,
        args.duration,
        args.rate_hz,
        args.kp,
        args.max_speed,
        args.goal_delay,
        args.scene,
        args.pybullet_gui,
    )
    try:
        summary = node.run()
    finally:
        node.close()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
