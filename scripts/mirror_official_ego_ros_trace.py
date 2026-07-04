#!/usr/bin/env python3
"""Record the official EGO-Planner simulator loop for a live PyBullet mirror.

This script runs inside the ROS Noetic container. It does not modify official
EGO-Planner code: the official planner, trajectory server, SO3 controller, and
quadrotor simulator stay upstream. For TASK_02 custom scenes it publishes
PyBullet-style obstacle pointclouds into EGO and streams selected topics to
JSONL for a host-side PyBullet viewer.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Optional

import rospy
import sensor_msgs.point_cloud2 as pc2
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from quadrotor_msgs.msg import PositionCommand
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header


class OfficialEgoMirrorRecorder:
    def __init__(
        self,
        output_path: Path,
        duration: float,
        rate_hz: float,
        goal: tuple[float, float, float],
        goal_delay: float,
        map_topic: str,
        map_points: int,
        scenario_id: str,
        obstacle_mode: str,
        scenario_notes: str,
        scenario_obstacles_json: str,
        source_launch: str,
        publish_custom_map: bool,
        custom_map_rate_hz: float,
        custom_map_resolution: float,
    ) -> None:
        self.output_path = output_path
        self.duration = duration
        self.rate_hz = rate_hz
        self.goal = goal
        self.goal_delay = goal_delay
        self.map_topic = map_topic
        self.map_points = map_points
        self.scenario_id = scenario_id
        self.obstacle_mode = obstacle_mode
        self.scenario_notes = scenario_notes
        self.scenario_obstacles = parse_json_list(scenario_obstacles_json)
        self.source_launch = source_launch
        self.publish_custom_map_enabled = publish_custom_map
        self.custom_map_rate_hz = custom_map_rate_hz
        self.custom_map_resolution = custom_map_resolution
        self.last_custom_map_publish = rospy.Time(0)
        self.start_time = rospy.Time.now()
        self.odom: Optional[Odometry] = None
        self.command: Optional[PositionCommand] = None
        self.map_received = False
        self.goal_published = False
        self.records = 0

        self.goal_pub = rospy.Publisher("/move_base_simple/goal", PoseStamped, queue_size=1, latch=True)
        self.custom_map_pub = rospy.Publisher(map_topic, PointCloud2, queue_size=1)
        self.odom_sub = rospy.Subscriber("/visual_slam/odom", Odometry, self.odom_callback, queue_size=20)
        self.cmd_sub = rospy.Subscriber("/planning/pos_cmd", PositionCommand, self.command_callback, queue_size=20)
        self.map_sub = rospy.Subscriber(map_topic, PointCloud2, self.map_callback, queue_size=1)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.output_path.open("w", encoding="utf-8")
        self.write_record(
            {
                "record_type": "metadata",
                "mode": "official_ego_original_loop_mirror",
                "odom_topic": "/visual_slam/odom",
                "command_topic": "/planning/pos_cmd",
                "map_topic": map_topic,
                "scenario_notes": scenario_notes,
                "scenario_obstacles": self.scenario_obstacles,
                "dynamic_obstacle_injection": dynamic_injection_status(obstacle_mode, publish_custom_map),
                "custom_map_publisher": publish_custom_map,
                "custom_map_resolution": custom_map_resolution,
            }
        )

    def close(self) -> None:
        self.handle.close()

    def odom_callback(self, msg: Odometry) -> None:
        self.odom = msg

    def command_callback(self, msg: PositionCommand) -> None:
        self.command = msg

    def map_callback(self, msg: PointCloud2) -> None:
        if self.map_received:
            return
        total_points = max(1, msg.width * msg.height)
        stride = max(1, total_points // max(1, self.map_points))
        points = []
        for index, point in enumerate(pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)):
            if index % stride != 0:
                continue
            points.append([round(float(point[0]), 3), round(float(point[1]), 3), round(float(point[2]), 3)])
            if len(points) >= self.map_points:
                break
        if not points:
            return
        self.map_received = True
        self.write_record(
            {
                "record_type": "map",
                "elapsed": self.elapsed_since_start(),
                "frame_id": msg.header.frame_id or "world",
                "source_topic": self.map_topic,
                "points": points,
                "sampled_points": len(points),
                "source_width": msg.width,
                "source_height": msg.height,
            }
        )

    def run(self) -> dict:
        rate = rospy.Rate(self.rate_hz)
        start_time = rospy.Time.now()
        while not rospy.is_shutdown():
            now = rospy.Time.now()
            elapsed = (now - start_time).to_sec()
            if elapsed >= self.duration:
                break
            self.publish_custom_map(now, elapsed)
            if elapsed >= self.goal_delay and not self.goal_published:
                self.publish_goal(now)
                self.goal_published = True
            self.write_state(elapsed)
            self.records += 1
            rate.sleep()

        final_position = self.odom_position()
        final_distance = distance(final_position, self.goal) if final_position is not None else None
        summary = {
            "records": self.records,
            "goal": list(self.goal),
            "goal_published": self.goal_published,
            "map_received": self.map_received,
            "command_received": self.command is not None,
            "final_position": final_position,
            "final_distance_to_goal": final_distance,
            "output_path": str(self.output_path),
        }
        self.write_record({"record_type": "summary", **summary})
        return summary

    def publish_goal(self, stamp: rospy.Time) -> None:
        goal = PoseStamped()
        goal.header.stamp = stamp
        goal.header.frame_id = "world"
        goal.pose.position.x = self.goal[0]
        goal.pose.position.y = self.goal[1]
        goal.pose.position.z = self.goal[2]
        goal.pose.orientation.w = 1.0
        self.goal_pub.publish(goal)

    def write_state(self, elapsed: float) -> None:
        odom_position = self.odom_position()
        odom_velocity = self.odom_velocity()
        command_position = self.command_position()
        command_velocity = self.command_velocity()
        record = {
            "record_type": "state",
            "step": self.records,
            "elapsed": elapsed,
            "odom_position": odom_position,
            "odom_velocity": odom_velocity,
            "ego_command_position": command_position,
            "ego_command_velocity": command_velocity,
            "obstacle_positions": obstacle_positions(self.scenario_obstacles, elapsed),
            "goal": list(self.goal),
            "goal_published": self.goal_published,
            "map_received": self.map_received,
            "command_received": self.command is not None,
            "distance_to_goal": distance(odom_position, self.goal) if odom_position is not None else None,
        }
        self.write_record(record)

    def write_record(self, record: dict) -> None:
        full_record = {
            "task_id": "TASK_02",
            "output_type": "diagnostic",
            "route": "official_ego_docker_sidecar",
            "source_launch": self.source_launch,
            "scenario_id": self.scenario_id,
            "obstacle_mode": self.obstacle_mode,
            "goal": list(self.goal),
            "timestamp": rospy.Time.now().to_sec(),
            "elapsed": self.elapsed_since_start(),
            **record,
        }
        self.handle.write(json.dumps(full_record, sort_keys=True) + "\n")
        self.handle.flush()

    def publish_custom_map(self, stamp: rospy.Time, elapsed: float) -> None:
        if not self.publish_custom_map_enabled:
            return
        min_period = 1.0 / max(self.custom_map_rate_hz, 0.1)
        if (stamp - self.last_custom_map_publish).to_sec() < min_period:
            return
        points = custom_obstacle_points(self.scenario_obstacles, elapsed, self.custom_map_resolution)
        header = Header()
        header.stamp = stamp
        header.frame_id = "world"
        self.custom_map_pub.publish(pc2.create_cloud_xyz32(header, points))
        self.last_custom_map_publish = stamp

    def elapsed_since_start(self) -> float:
        return (rospy.Time.now() - self.start_time).to_sec()

    def odom_position(self) -> Optional[list[float]]:
        if self.odom is None:
            return None
        position = self.odom.pose.pose.position
        return [position.x, position.y, position.z]

    def odom_velocity(self) -> Optional[list[float]]:
        if self.odom is None:
            return None
        velocity = self.odom.twist.twist.linear
        return [velocity.x, velocity.y, velocity.z]

    def command_position(self) -> Optional[list[float]]:
        if self.command is None:
            return None
        position = self.command.position
        return [position.x, position.y, position.z]

    def command_velocity(self) -> Optional[list[float]]:
        if self.command is None:
            return None
        velocity = self.command.velocity
        return [velocity.x, velocity.y, velocity.z]


def distance(left: list[float], right: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def parse_json_list(value: str) -> list:
    if not value:
        return []
    decoded = json.loads(value)
    if not isinstance(decoded, list):
        raise ValueError("scenario obstacles JSON must decode to a list")
    return decoded


def dynamic_injection_status(obstacle_mode: str, publish_custom_map: bool) -> str:
    if publish_custom_map:
        return f"custom_pointcloud_publisher_{obstacle_mode}"
    if obstacle_mode == "static":
        return "official_mockamap_static_cloud"
    return "not_supported_without_custom_pointcloud_publisher"


def obstacle_positions(obstacles: list[dict], elapsed: float) -> list[dict]:
    return [
        {
            "obstacle_id": obstacle.get("obstacle_id"),
            "kind": obstacle.get("kind"),
            "position": list(obstacle_position(obstacle, elapsed)),
            "radius": obstacle.get("radius"),
            "height": obstacle.get("height"),
            "motion_type": obstacle.get("motion_type", "static"),
        }
        for obstacle in obstacles
    ]


def custom_obstacle_points(obstacles: list[dict], elapsed: float, resolution: float) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for obstacle in obstacles:
        center = obstacle_position(obstacle, elapsed)
        kind = obstacle.get("kind")
        radius = float(obstacle.get("radius") or 0.5)
        height = float(obstacle.get("height") or 1.0)
        if kind == "sphere":
            points.extend(sample_sphere_points(center, radius, resolution))
        else:
            points.extend(sample_cylinder_points(center, radius, height, resolution))
    return points


def obstacle_position(obstacle: dict, elapsed: float) -> tuple[float, float, float]:
    initial = tuple(float(value) for value in obstacle["initial_position"])
    motion_type = obstacle.get("motion_type", "static")
    velocity = obstacle.get("velocity")
    if motion_type == "static" or velocity is None:
        return initial  # type: ignore[return-value]

    start_time = float(obstacle.get("start_time") or 0.0)
    active_time = elapsed - start_time
    if active_time <= 0.0:
        return initial  # type: ignore[return-value]
    vx, vy, vz = (float(value) for value in velocity)
    return (
        initial[0] + vx * active_time,
        initial[1] + vy * active_time,
        initial[2] + vz * active_time,
    )


def sample_cylinder_points(
    center: tuple[float, float, float],
    radius: float,
    height: float,
    resolution: float,
) -> list[tuple[float, float, float]]:
    columns = max(12, int(math.ceil(2.0 * math.pi * radius / resolution)))
    layers = max(3, int(math.ceil(height / resolution)))
    radial_steps = max(2, int(math.ceil(radius / resolution)))
    bottom = center[2] - height / 2.0
    points = []
    for layer in range(layers + 1):
        z = bottom + height * layer / layers
        points.append((center[0], center[1], z))
        for radial_index in range(1, radial_steps + 1):
            radial = radius * radial_index / radial_steps
            for column in range(columns):
                theta = 2.0 * math.pi * column / columns
                points.append((center[0] + radial * math.cos(theta), center[1] + radial * math.sin(theta), z))
    return points


def sample_sphere_points(
    center: tuple[float, float, float],
    radius: float,
    resolution: float,
) -> list[tuple[float, float, float]]:
    rings = max(6, int(math.ceil(math.pi * radius / resolution)))
    columns = max(12, int(math.ceil(2.0 * math.pi * radius / resolution)))
    points = []
    for ring in range(rings + 1):
        phi = math.pi * ring / rings
        z = center[2] + radius * math.cos(phi)
        radial = radius * math.sin(phi)
        for column in range(columns):
            theta = 2.0 * math.pi * column / columns
            points.append((center[0] + radial * math.cos(theta), center[1] + radial * math.sin(theta), z))
    return points


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=90.0)
    parser.add_argument("--rate-hz", type=float, default=30.0)
    parser.add_argument("--goal-x", type=float, default=-8.0)
    parser.add_argument("--goal-y", type=float, default=10.0)
    parser.add_argument("--goal-z", type=float, default=1.0)
    parser.add_argument("--goal-delay", type=float, default=6.0)
    parser.add_argument("--map-topic", default="/pirl_navrl/custom_scene_cloud")
    parser.add_argument("--map-points", type=int, default=20000)
    parser.add_argument("--scenario-id", default="ego_static_obstacle_v0")
    parser.add_argument("--obstacle-mode", default="static")
    parser.add_argument("--scenario-notes", default="")
    parser.add_argument("--scenario-obstacles-json", default="[]")
    parser.add_argument(
        "--source-launch",
        default="pirl_navrl/bridges/ego_planner_bridge/ego_custom_map_sidecar.launch",
    )
    parser.add_argument("--publish-custom-map", action="store_true")
    parser.add_argument("--custom-map-rate-hz", type=float, default=12.0)
    parser.add_argument("--custom-map-resolution", type=float, default=0.18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rospy.init_node("pirl_navrl_official_ego_mirror")
    recorder = OfficialEgoMirrorRecorder(
        output_path=args.output,
        duration=args.duration,
        rate_hz=args.rate_hz,
        goal=(args.goal_x, args.goal_y, args.goal_z),
        goal_delay=args.goal_delay,
        map_topic=args.map_topic,
        map_points=args.map_points,
        scenario_id=args.scenario_id,
        obstacle_mode=args.obstacle_mode,
        scenario_notes=args.scenario_notes,
        scenario_obstacles_json=args.scenario_obstacles_json,
        source_launch=args.source_launch,
        publish_custom_map=args.publish_custom_map,
        custom_map_rate_hz=args.custom_map_rate_hz,
        custom_map_resolution=args.custom_map_resolution,
    )
    try:
        summary = recorder.run()
    finally:
        recorder.close()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
