# TASK_02 完成报告

## 结论

TASK_02 已完成 diagnostic 版本：EGO-Planner 官方仓库已本地准备，bridge I/O contract 已写清楚，`ego_like_static_v0` PyBullet 静态障碍场景和 mock EGO-like bridge smoke test 已跑通。

主机 Ubuntu 22.04 未安装 ROS/catkin，检测不到 `roscore` 和 `catkin_make`。后续已用 `osrf/ros:noetic-desktop-full` Docker 容器完成官方 EGO-Planner `catkin_make`，并验证 `run_in_sim.launch`、`simple_run.launch` 能启动；发布 `/move_base_simple/goal` 后可从 `/planning/pos_cmd` 读到官方 EGO 输出。本轮结果仍然只作为 bridge spike 诊断，不是论文 baseline，不是 paper-candidate。

## 修改文件

- `configs/phase2_ego_like_smoke.json`
- `pirl_navrl/bridges/ego_planner_bridge/README.md`
- `pirl_navrl/bridges/ego_planner_bridge/ros_io_contract.md`
- `pirl_navrl/bridges/ego_planner_bridge/pybullet_to_ego.py`
- `pirl_navrl/bridges/ego_planner_bridge/ego_to_pybullet.py`
- `pirl_navrl/scenarios/ego_like_static_v0.py`
- `pirl_navrl/evaluation/diagnostic_logger.py`
- `scripts/run_phase2_ego_like_smoke.py`
- `scripts/run_ego_planner_noetic_docker.sh`
- `tests/test_ego_bridge_contract.py`
- `tests/test_ego_like_static_scenario.py`
- `tests/test_task02_diagnostic_schema.py`
- `external/README.md`
- `THIRD_PARTY_NOTICES.md`

## 外部仓库和版本

- EGO-Planner repo: <https://github.com/ZJU-FAST-Lab/ego-planner>
- Local path: `external/ego-planner/`
- Local commit: `bfda51284c8c1b476043255a8145ef925a3778a5`
- License observed locally: GNU GPL v3
- Build route recorded from official README:

```bash
sudo apt-get install libarmadillo-dev
cd external/ego-planner
catkin_make -DCMAKE_BUILD_TYPE=Release
source devel/setup.bash
roslaunch ego_planner rviz.launch
roslaunch ego_planner run_in_sim.launch
```

Python/local dependency observations:

- `pirl_navrl==0.1.0`
- `stable_baselines3==2.9.0`
- `torch==2.8.0+cpu`
- `gym_pybullet_drones` import OK
- `pybullet` import OK
- `roscore`: missing
- `catkin_make`: missing
- Docker image for official sidecar: `osrf/ros:noetic-desktop-full`

## 运行命令

```bash
GIT_CLONE_FLAGS="--depth 1" bash scripts/setup_external_repos.sh --include-ego
python3 scripts/run_phase2_ego_like_smoke.py
python3 -m pytest -q
bash scripts/run_ego_planner_noetic_docker.sh build
bash scripts/run_ego_planner_noetic_docker.sh headless
bash scripts/run_ego_planner_noetic_docker.sh rviz
```

## 测试结果

```text
13 passed in 0.05s
```

Smoke summary:

```json
{
  "bridge_status": "mock_ros_unavailable",
  "ego_planner_commit": "bfda51284c8c1b476043255a8145ef925a3778a5",
  "final_distance_to_goal": 0.304814881480228,
  "min_clearance": 0.8033887817835024,
  "output_path": "/home/zsz/pirl-navrl/results/task02_ego_like_smoke.jsonl",
  "records": 47
}
```

Official EGO sidecar Docker validation:

- `catkin_make -DCMAKE_BUILD_TYPE=Release`: passed.
- Built executables include `devel/lib/ego_planner/ego_planner_node` and `devel/lib/ego_planner/traj_server`.
- `roslaunch ego_planner run_in_sim.launch`: starts ROS master and EGO nodes.
- `/planning/pos_cmd`: produced after publishing `/move_base_simple/goal`.
- `roslaunch ego_planner simple_run.launch`: starts RViz through X11.

## 生成产物

- `results/task02_ego_like_smoke.jsonl`

每条 JSONL 记录包含 TASK_02 要求字段：`task_id`、`output_type`、`platform_id`、`external_planner`、`ego_planner_commit`、`scenario_id`、`seed`、`step`、`position`、`goal`、`desired_velocity`、`min_clearance`、`bridge_status`。

## 当前限制

- 主机原生 ROS sidecar 未安装；官方 EGO sidecar 目前通过 Docker Noetic 运行。
- 当前 Python command bridge 只输出 desired velocity 和 normalized action-like vector，还没有绑定到具体 gym-pybullet-drones action mode。
- Obstacle bridge 第一版只支持静态 cylinder/sphere -> synthetic pointcloud。
- `ego_like_static_v0` 是工程诊断场景，不是 EGO 官方场景复现。
- Mock planner 只用于闭环与日志验证，不代表 EGO-Planner 算法行为。

## 后续建议

不建议立即把 official EGO sidecar 升级为正式 baseline。建议先完成以下人工决策点：

1. 是否接受 Docker Noetic 作为 official sidecar 标准运行方式，或另建 Ubuntu 20.04/ROS Noetic 原生环境。
2. 通过 `rqt_graph` 和 `rosnode info` 确认 EGO topic 名称，再把本轮 contract 映射到真实 ROS topic。
3. 验证 EGO trajectory 输出频率和 PyBullet control step 是否匹配。
4. 若 ROS 维护成本过高，回退到 EGO-style Python baseline：保留本轮 state/pointcloud/goal/command contract，替换 mock waypoint planner 为纯 Python 的局部轨迹优化或采样式避障 baseline。

本任务输出性质保持为 `diagnostic`。
