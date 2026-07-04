# TASK_02 计划：EGO-Planner 官方 Docker sidecar 与简单障碍场景诊断

## 1. 阶段定位

TASK_02 不是论文结果阶段，也不是正式 baseline 对比阶段。

当前只保留一条主路线：

```text
official EGO planner/controller/simulator nodes inside Docker Noetic
        |
        | official ROS topics
        v
PIRL-NavRL trace recorder
        |
        | JSONL trace
        v
PyBullet diagnostic mirror
```

PyBullet 在本阶段只做可视化和诊断辅助，不替代 official EGO 的感知、
控制器或四旋翼动力学。

## 2. 外部项目角色

- gym-pybullet-drones / PyBullet：后续 baseline 接入准备和当前可视化辅助。
- EGO-Planner：TASK_02 唯一主要 planner 路线，作为 Docker/ROS sidecar 运行。
- NavRL：长期代码参考，不进入 TASK_02 执行。

## 3. 当前保留脚本

```text
scripts/run_ego_planner_noetic_docker.sh
scripts/run_official_ego_diagnostic_scene.sh
scripts/run_official_ego_pybullet_mirror.sh
scripts/mirror_official_ego_ros_trace.py
scripts/view_official_ego_pybullet_mirror.py
```

## 4. Diagnostic Scene Suite

场景定义在：

```text
pirl_navrl/scenarios/ego_official_diagnostic_scenarios.py
```

场景 ID：

- `ego_static_obstacle_v0`
  - 将固定柱状障碍点云注入 official EGO。
- `ego_dynamic_obstacle_v0`
  - 将连续横向运动柱状障碍点云注入 official EGO。
- `ego_sudden_motion_obstacle_v0`
  - 将“先静止、后横向运动”的柱状障碍点云注入 official EGO。

运行：

```bash
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_static_obstacle_v0
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_dynamic_obstacle_v0
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_sudden_motion_obstacle_v0
```

## 5. Trace Contract

TASK_02 生成 JSONL trace，不生成 baseline metrics。

每条记录包含或继承：

```json
{
  "task_id": "TASK_02",
  "output_type": "diagnostic",
  "route": "official_ego_docker_sidecar",
  "source_launch": "pirl_navrl/bridges/ego_planner_bridge/ego_custom_map_sidecar.launch",
  "scenario_id": "ego_static_obstacle_v0",
  "obstacle_mode": "static",
  "goal": [6.0, 0.0, 1.0],
  "record_type": "state",
  "timestamp": 0.0,
  "elapsed": 0.0,
  "odom_position": [-18.0, 0.0, 0.0],
  "ego_command_position": null,
  "distance_to_goal": null
}
```

## 6. 明确删除/降级项

以下内容不再作为 TASK_02 主路线：

- early EGO-like waypoint experiment
- synthetic waypoint trajectory effect test
- early interface experiment 的目标距离/clearance 效果报告
- 简化 Python point-mass tracker 作为避障效果判断

保留的 bridge helper 仅用于 future gym-pybullet-drones baseline 接入准备。

## 7. 验收标准

TASK_02 当前验收标准：

1. 官方 EGO-Planner repo 已本地 clone，并记录 commit。
2. Docker Noetic build/run 路线完整。
3. custom-map official sidecar 能启动并输出 `/planning/pos_cmd`。
4. trace recorder 生成 TASK_02 official route JSONL。
5. PyBullet mirror 能显示 official odom、command 和 map。
6. 三个 diagnostic scenario 均通过自定义 pointcloud 注入 official EGO。
7. 不把当前输出作为论文 baseline。
