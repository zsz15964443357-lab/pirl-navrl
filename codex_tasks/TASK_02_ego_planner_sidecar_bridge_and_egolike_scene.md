# TASK_02：EGO-Planner 官方 Docker sidecar 与简单障碍场景诊断

状态：继续优化中，当前主路线为 official EGO-Planner Docker/ROS sidecar
diagnostic。

## 目标

1. 在 Docker Noetic 中运行官方 EGO-Planner。
2. PyBullet 仅作为场景/可视化/诊断辅助。
3. 记录 official EGO trace JSONL。
4. 构造简单 diagnostic scenario suite：
   - `ego_static_obstacle_v0`
   - `ego_dynamic_obstacle_v0`
   - `ego_sudden_motion_obstacle_v0`
5. 保持 diagnostic 性质，不进入论文结果，不新建 TASK_03。

## 当前主入口

```bash
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_static_obstacle_v0
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_dynamic_obstacle_v0
bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_sudden_motion_obstacle_v0
```

## 当前保留文件

```text
pirl_navrl/scenarios/ego_official_diagnostic_scenarios.py
pirl_navrl/bridges/ego_planner_bridge/ros_io_contract.md
scripts/run_ego_planner_noetic_docker.sh
scripts/run_official_ego_diagnostic_scene.sh
scripts/mirror_official_ego_ros_trace.py
scripts/view_official_ego_pybullet_mirror.py
```

## 删除/降级内容

以下内容不再作为 TASK_02 当前路线：

- early EGO-like waypoint experiment
- synthetic waypoint trajectory effect test
- early interface experiment final distance / clearance 效果报告
- 简化 point-mass tracker 避障效果判断

## 动态障碍注入

`ego_dynamic_obstacle_v0` 和 `ego_sudden_motion_obstacle_v0` 已通过
`/pirl_navrl/custom_scene_cloud` 注入 official EGO 的 `/grid_map/cloud`。
它们用于诊断“我们自建 PyBullet-style 场景能否调用 EGO-Planner”，不是论文
baseline。

## Trace 字段

JSONL 记录至少包含或继承：

- `task_id: TASK_02`
- `output_type: diagnostic`
- `route: official_ego_docker_sidecar`
- `source_launch`
- `scenario_id`
- `obstacle_mode`
- `goal`
- `record_type`
- `timestamp`
- `elapsed` where applicable
- `odom_position` where available
- `ego_command_position` where available
- `distance_to_goal` where available
