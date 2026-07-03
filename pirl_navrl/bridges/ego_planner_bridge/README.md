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

## Live PyBullet GUI

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

Current limitation: this live bridge receives official EGO commands and shows
clear lateral replanning behavior, but the simple PyBullet point-mass tracker
does not yet reproduce the official EGO simulator's SO3-controlled behavior.
Do not treat the current live view as a baseline-quality avoidance result.

For the original repository's visual quality and avoidance behavior, use the
official simulator/RViz route instead:

```bash
bash scripts/run_ego_planner_noetic_docker.sh rviz
```
