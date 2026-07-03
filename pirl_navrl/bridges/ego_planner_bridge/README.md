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
