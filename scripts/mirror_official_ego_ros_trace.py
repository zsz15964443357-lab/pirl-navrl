#!/usr/bin/env python3
"""Record the official EGO-Planner simulator loop for a live PyBullet mirror.

This script runs inside the ROS Noetic container. It does not replace any part
of EGO-Planner: run_in_sim.launch owns mapping, local sensing, planning, SO3
control, and quadrotor dynamics. The script only publishes one manual goal and
streams selected topics to JSONL for a host-side PyBullet viewer.
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
    ) -> None:
        self.output_path = output_path
        self.duration = duration
        self.rate_hz = rate_hz
        self.goal = goal
        self.goal_delay = goal_delay
        self.map_topic = map_topic
        self.map_points = map_points
        self.odom: Optional[Odometry] = None
        self.command: Optional[PositionCommand] = None
        self.map_received = False
        self.goal_published = False
        self.records = 0

        self.goal_pub = rospy.Publisher("/move_base_simple/goal", PoseStamped, queue_size=1, latch=True)
        self.odom_sub = rospy.Subscriber("/visual_slam/odom", Odometry, self.odom_callback, queue_size=20)
        self.cmd_sub = rospy.Subscriber("/planning/pos_cmd", PositionCommand, self.command_callback, queue_size=20)
        self.map_sub = rospy.Subscriber(map_topic, PointCloud2, self.map_callback, queue_size=1)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.output_path.open("w", encoding="utf-8")
        self.write_record(
            {
                "record_type": "metadata",
                "task_id": "TASK_02",
                "mode": "official_ego_original_loop_mirror",
                "source_launch": "ego_planner/run_in_sim.launch",
                "odom_topic": "/visual_slam/odom",
                "command_topic": "/planning/pos_cmd",
                "map_topic": map_topic,
                "goal": list(goal),
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
            "goal": list(self.goal),
            "goal_published": self.goal_published,
            "map_received": self.map_received,
            "command_received": self.command is not None,
            "distance_to_goal": distance(odom_position, self.goal) if odom_position is not None else None,
        }
        self.write_record(record)

    def write_record(self, record: dict) -> None:
        self.handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.handle.flush()

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=90.0)
    parser.add_argument("--rate-hz", type=float, default=30.0)
    parser.add_argument("--goal-x", type=float, default=-8.0)
    parser.add_argument("--goal-y", type=float, default=10.0)
    parser.add_argument("--goal-z", type=float, default=1.0)
    parser.add_argument("--goal-delay", type=float, default=6.0)
    parser.add_argument("--map-topic", default="/map_generator/global_cloud")
    parser.add_argument("--map-points", type=int, default=20000)
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
    )
    try:
        summary = recorder.run()
    finally:
        recorder.close()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
