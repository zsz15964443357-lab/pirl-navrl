# EGO-Planner Sidecar Bridge

This directory contains only PIRL-NavRL bridge contracts and Python diagnostic
adapters. It does not vendor or modify EGO-Planner C++ planner code.

## Official Repository

Local checkout:

```bash
external/ego-planner/
```

Clone command:

```bash
GIT_CLONE_FLAGS="--depth 1" bash scripts/setup_external_repos.sh --include-ego
```

Official repository: <https://github.com/ZJU-FAST-Lab/ego-planner>

Local TASK_02 checkout recorded during implementation:

```text
bfda51284c8c1b476043255a8145ef925a3778a5
```

License observed in the local checkout: GNU GPL v3.

## Official Build Route

The official README requires Ubuntu with ROS desktop, catkin, and Armadillo.
The upstream route is:

```bash
sudo apt-get install libarmadillo-dev
cd external/ego-planner
catkin_make -DCMAKE_BUILD_TYPE=Release
source devel/setup.bash
roslaunch ego_planner rviz.launch
roslaunch ego_planner run_in_sim.launch
```

TASK_02 does not run or modify official planner internals. It documents the
sidecar interface and runs a mock bridge when ROS is unavailable.

## Local Docker Route On Ubuntu 22.04

The current host is Ubuntu 22.04, while official EGO-Planner targets ROS1 Noetic
on Ubuntu 20.04. Use the provided Docker wrapper:

```bash
bash scripts/run_ego_planner_noetic_docker.sh build
bash scripts/run_ego_planner_noetic_docker.sh headless
bash scripts/run_ego_planner_noetic_docker.sh rviz
```

Observed local status:

- `catkin_make -DCMAKE_BUILD_TYPE=Release` passes in `osrf/ros:noetic-desktop-full`.
- `roslaunch ego_planner run_in_sim.launch` starts the official sidecar nodes.
- Publishing `/move_base_simple/goal` produces `/planning/pos_cmd`.
- `roslaunch ego_planner simple_run.launch` starts RViz through X11.

## Local Smoke Test

```bash
python3 scripts/run_phase2_ego_like_smoke.py
```

Default output:

```text
results/task02_ego_like_smoke.jsonl
```

The output is diagnostic only and must not be treated as a paper-candidate
baseline result.

## Official EGO To PyBullet Visualization

Recommended route for checking original EGO behavior in PyBullet:

```bash
bash scripts/run_official_ego_pybullet_mirror.sh
```

This runs the official `ego_planner/run_in_sim.launch` unchanged in the Noetic
Docker container. That launch owns the original map generator, `pcl_render_node`
local sensing, EGO planner, `traj_server`, SO3 controller, and quadrotor
simulator. The host PyBullet window is only a live mirror of the official ROS
topics:

- red voxel columns: official `/map_generator/global_cloud`, downsampled into
  clear PyBullet obstacle blocks
- yellow sphere/line: official `/visual_slam/odom`
- green line: official `/planning/pos_cmd`
- green sphere: the published `/move_base_simple/goal`

Short local validation on this machine:

```json
{
  "command_received": true,
  "final_distance_to_goal": 0.2239981077623934,
  "final_position": [-8.099465204895884, 9.799844148774891, 0.9851858001733191],
  "goal": [-8.0, 10.0, 1.0],
  "map_received": true,
  "records": 720
}
```

This is the route to use when the question is whether the visualized behavior
matches the original repository. It mirrors original EGO simulator behavior
instead of replacing the original controller with a Python point-mass tracker.

The PyBullet mirror renders obstacle maps as regular voxel columns by default.
For debugging the raw pointcloud instead:

```bash
python3 scripts/view_official_ego_pybullet_mirror.py \
  --trace results/ego_official_mirror/live_trace.jsonl \
  --map-style points
```

## Simplified PyBullet Diagnostic Visualization

Run the end-to-end diagnostic bridge:

```bash
bash scripts/run_ego_pybullet_bridge_visual.sh
```

This starts the official EGO sidecar in the Noetic Docker container, publishes
the `ego_like_static_v0` odometry and synthetic pointcloud from the bridge node,
tracks `/planning/pos_cmd`, and renders the resulting PyBullet trace.

Outputs:

```text
results/ego_pybullet_bridge/official_ego_pybullet_trace.jsonl
results/ego_pybullet_bridge/official_ego_pybullet_bridge.gif
results/ego_pybullet_bridge/official_ego_pybullet_bridge.mp4
```

Observed diagnostic run:

- `/planning/pos_cmd` was received.
- Final goal distance was about `0.33 m`.
- Minimum clearance was negative, so this is a connectivity visualization, not
  a valid obstacle-avoidance result.

## Simplified Live PyBullet GUI

Run without generating GIF or video:

```bash
bash scripts/run_ego_pybullet_live_gui.sh
```

This starts the official EGO-Planner sidecar in Docker and opens a live PyBullet
GUI on the host. The default scene is `ego_mockamap_box_v0`, a small
mockamap-style box-obstacle scene. The GUI shows:

- red boxes: synthetic obstacle pointcloud source
- yellow sphere/line: tracked PyBullet diagnostic state
- green line: official EGO `/planning/pos_cmd`

No PyBullet debug text is shown by default because the GUI text rendering can
be misaligned or visually noisy.

Interface review status:

- Odometry topic: `/visual_slam/odom` remapped to EGO `/odom_world` and `/grid_map/odom`.
- Obstacle topic: `/pirl_navrl/cloud` remapped to EGO `/grid_map/cloud`.
- Goal topic: `/move_base_simple/goal` consumed by EGO `waypoint_generator`.
- Command topic: `/planning/pos_cmd` from EGO `traj_server`.
- Frame: `world`, matching EGO `grid_map/frame_id` and `traj_server` output.

Root cause of the poor visual/effect match in this simplified live bridge:

- The original EGO loop is `map_generator/mockamap -> pcl_render_node ->
  EGO grid map/planner -> traj_server -> so3_control ->
  quadrotor_simulator_so3 -> /visual_slam/odom`.
- This simplified bridge was `synthetic pointcloud -> EGO planner ->
  /planning/pos_cmd -> Python point-mass tracker -> synthetic odom`.
- Therefore it bypasses the original local sensing, SO3 controller, and
  quadrotor dynamics, so it can verify topic connectivity but not original
  avoidance quality.

Do not treat this simplified live view as a baseline-quality avoidance result.

For the original repository's visual quality and avoidance behavior, use the
official mirror or RViz route instead:

```bash
bash scripts/run_official_ego_pybullet_mirror.sh
bash scripts/run_ego_planner_noetic_docker.sh rviz
```
