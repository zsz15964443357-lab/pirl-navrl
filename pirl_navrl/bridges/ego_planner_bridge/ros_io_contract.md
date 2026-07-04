# EGO-Planner Bridge I/O Contract

This contract is for TASK_02 diagnostics only. The active TASK_02 route runs
the official EGO-Planner ROS loop inside Docker Noetic. PyBullet is currently a
diagnostic scene/visualization helper, not the controller backend for official
EGO.

The conversion helpers in this package are retained as future
gym-pybullet-drones baseline preparation. They are not used to report planner
effect in the current TASK_02 route.

## Frames And Timing

- Official EGO world frame: `world`
- Future gym-pybullet bridge frame may use `map`, but must be remapped
  explicitly.
- Drone body frame: `base_link`
- Units: meters, seconds, radians
- Quaternion convention: `[x, y, z, w]`
- Time source: ROS time for the official Docker sidecar trace.

## State Bridge

Future direction: PyBullet drone state -> ROS odometry-shaped payload.

Required fields:

```json
{
  "frame_id": "world",
  "child_frame_id": "base_link",
  "timestamp": 0.0,
  "position": [-4.0, 0.0, 1.0],
  "velocity": [0.0, 0.0, 0.0],
  "orientation": [0.0, 0.0, 0.0, 1.0]
}
```

Target ROS shape for future sidecar work: `nav_msgs/Odometry`.

Current official route uses `/visual_slam/odom` from
`quadrotor_simulator_so3`; PIRL-NavRL records it but does not replace it.

## Obstacle Bridge

Future direction: PyBullet obstacle primitives -> synthetic pointcloud.

The first version samples only static `cylinder` and `sphere` primitives:

```json
{
  "frame_id": "map",
  "timestamp": 0.0,
  "points": [[-1.25, 0.0, 0.0], [-1.25, 0.0, 0.5]]
}
```

Target ROS shape for future sidecar work: `sensor_msgs/PointCloud2`.
Current TASK_02 custom-scene route publishes PyBullet-style obstacle pointclouds
to `/pirl_navrl/custom_scene_cloud`, remapped into official EGO `/grid_map/cloud`.
This supports static, continuously moving, and sudden-motion diagnostic
obstacles.

## Goal Bridge

Direction in current route: TASK_02 runner publishes one
`/move_base_simple/goal` to official EGO.

The first version supports one target point:

```json
{
  "frame_id": "world",
  "timestamp": 0.0,
  "position": [4.0, 0.0, 1.0]
}
```

Target ROS shape: `geometry_msgs/PoseStamped`.

## Command Bridge

Direction in current route: official EGO `traj_server` publishes
`quadrotor_msgs/PositionCommand` on `/planning/pos_cmd`; official
`so3_control` and `quadrotor_simulator_so3` consume it through the upstream
loop. PIRL-NavRL records command positions for diagnostics.

A later gym-pybullet-drones baseline may map EGO commands into a selected
velocity/RPM/action mode, but TASK_02 does not do that mapping as planner
effect evidence.

## TASK_02 Local Status

Active route:

- `route`: `official_ego_docker_sidecar`
- `source_launch`: `pirl_navrl/bridges/ego_planner_bridge/ego_custom_map_sidecar.launch`
- trace schema only; not baseline metrics
- PyBullet mirror is visualization/diagnostic only
