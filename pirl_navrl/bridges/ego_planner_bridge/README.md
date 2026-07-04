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

TASK_02 does not run or modify official planner internals. The current active
route is the official EGO-Planner Docker/ROS sidecar diagnostic.

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

## Official EGO Diagnostic Scene Runner

Main TASK_02 route:

```bash
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_static_obstacle_v0
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_dynamic_obstacle_v0
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_sudden_motion_obstacle_v0
```

This runs official EGO planner/controller/simulator nodes in the Noetic Docker
container through `ego_custom_map_sidecar.launch`. PIRL-NavRL publishes the
custom PyBullet-style obstacle scene as `/pirl_navrl/custom_scene_cloud`, which
is remapped into EGO `/grid_map/cloud`. The host PyBullet window mirrors the
same diagnostic scene and official ROS topics:

- red cylinders/spheres: custom TASK_02 obstacles, including dynamic motion
- yellow sphere/line: official `/visual_slam/odom`
- green line: official `/planning/pos_cmd`
- green sphere: the published `/move_base_simple/goal`

The compatibility shortcut below runs the static scenario:

```bash
bash scripts/run_official_ego_pybullet_mirror.sh
```

Short local validation on this machine:

```json
{
  "command_received": true,
  "final_distance_to_goal": 0.020337071346071958,
  "goal": [6.0, 0.0, 1.0],
  "map_received": true,
  "max_abs_odom_y_static_smoke": 1.2102761799812451
}
```

This is the route to use when the question is whether the visualized behavior
matches the original repository. It mirrors original EGO simulator behavior
instead of replacing the original controller with a Python point-mass tracker.

The PyBullet mirror renders obstacle maps as regular voxel columns by default.
For debugging the raw pointcloud instead:

```bash
python3 scripts/view_official_ego_pybullet_mirror.py \
  --trace results/official_ego_diagnostic/ego_static_obstacle_v0/trace.jsonl \
  --map-style points
```

## Diagnostic Scene Suite

Scenario definitions live in
`pirl_navrl/scenarios/ego_official_diagnostic_scenarios.py`.

- `ego_static_obstacle_v0`: injects fixed custom cylinders into official EGO.
- `ego_dynamic_obstacle_v0`: injects a continuously crossing cylinder.
- `ego_sudden_motion_obstacle_v0`: injects a cylinder that starts stationary
  and then moves laterally.

These scenarios demonstrate that our simple PyBullet-style scene can call
official EGO as planner through ROS pointcloud/goal topics. They are still
diagnostic scenes, not baseline experiments.

## Removed Simplified PyBullet Bridge

The earlier mock EGO-like route and simplified ROS/PyBullet bridge were removed
from the active TASK_02 route because they were useful only for early
interface/debug experiments and produced misleading planner-effect narratives:

- The original EGO loop is `map_generator/mockamap -> pcl_render_node ->
  EGO grid map/planner -> traj_server -> so3_control ->
  quadrotor_simulator_so3 -> /visual_slam/odom`.
- This simplified bridge was `synthetic pointcloud -> EGO planner ->
  /planning/pos_cmd -> Python point-mass tracker -> synthetic odom`.
- Therefore it bypasses the original local sensing, SO3 controller, and
  quadrotor dynamics, so it can verify topic connectivity but not original
  avoidance quality.

For original repository behavior, use only the official mirror or RViz route:

```bash
bash scripts/run_official_ego_pybullet_mirror.sh
bash scripts/run_ego_planner_noetic_docker.sh rviz
```
