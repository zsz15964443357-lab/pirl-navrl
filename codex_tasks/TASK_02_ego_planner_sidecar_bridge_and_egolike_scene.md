# TASK 02：EGO-Planner 官方侧车桥接与 EGO-like PyBullet 简单场景验证

## 0. 状态

状态：计划中。

本任务整理第二阶段方向。原则上应在 `TASK_01` 完成、审查并确认后执行；如需提前执行，必须由项目负责人明确批准。

## 1. 背景

PIRL-NavRL 第一阶段以 gym-pybullet-drones 作为轻量级 UAV PyBullet 底座。第二阶段先验证官方 EGO-Planner 在近似场景中的桥接可行性，而不是直接进入正式论文 baseline 对比。

EGO-Planner 是传统局部规划强 baseline 候选，但官方项目是 ROS / catkin / C++ 工程，不是 Gymnasium policy。因此第二阶段只做 official sidecar bridge spike。

NavRL 不作为 baseline。NavRL 仅用于参考训练链路、代码结构、模块划分、部署路径、动态导航设计和参数组织方式。

## 2. 目标

1. 在 `external/` 下本地准备 EGO-Planner 官方仓库，并记录 commit、许可证、build/run 指令。
2. 在 gym-pybullet-drones / PyBullet 中实现一个 `ego_like_static_v0` 简单静态障碍场景。
3. 设计并实现最小 EGO bridge I/O contract：state、obstacle、goal、command。
4. 尝试将 PyBullet state / obstacle / goal 桥接到官方 EGO-Planner ROS sidecar。
5. 将 EGO 输出的 trajectory / command 转换为 gym-pybullet-drones 可执行的 desired velocity / action。
6. 完成最小 smoke test，生成小型 diagnostic JSONL。
7. 给出是否继续发展 official EGO baseline 的决策建议。

## 3. 必做范围

- 更新或补充 `external/README.md` 中 EGO-Planner 的本地克隆说明。
- 记录 EGO-Planner 官方仓库 commit。
- 编写 bridge I/O contract 文档。
- 搭建 `ego_like_static_v0` 简单场景。
- 实现或 mock 四类桥接：state bridge、obstacle bridge、goal bridge、command bridge。
- 运行一个短 horizon smoke test。
- 输出小型 diagnostic JSONL。
- 写任务完成报告。

## 4. 禁止项

本任务禁止：

- 不做正式 baseline 论文对比。
- 不做 PIRL-NavRL 主方法训练。
- 不做多 seed 论文级统计。
- 不做动态障碍正式评估。
- 不做语义分割。
- 不做 NavRL baseline。
- 不训练 NavRL。
- 不迁移 NavRL 为 PyBullet baseline。
- 不使用 Isaac Sim 训练。
- 不把 EGO-Planner 官方 C++ 核心代码复制进 `pirl_navrl/` 主源码。
- 不修改 EGO-Planner 核心 planner 算法。
- 不提交 checkpoint、视频、GIF、TensorBoard、wandb 或大型 rollout。
- 不声称 EGO-Planner 论文结果复现。
- 不把本任务输出标注为 paper-candidate。

## 5. 建议实现结构

允许按任务需要创建最小源码结构：

```text
pirl_navrl/
  bridges/
    ego_planner_bridge/
      README.md
      ros_io_contract.md
      pybullet_to_ego.py
      ego_to_pybullet.py
  scenarios/
    ego_like_static_v0.py
  evaluation/
    diagnostic_logger.py
```

如果实际实现中需要调整结构，必须在完成报告中说明原因。

## 6. EGO-like 场景定义

第一版场景只用于 bridge smoke test：

```text
scenario_id: ego_like_static_v0
space: 10m x 10m x 3m
start: [-4.0, 0.0, 1.0]
goal: [4.0, 0.0, 1.0]
obstacles: static cylinders or spheres
seed: fixed first, random later
max_episode_steps: short diagnostic horizon
```

不要求严格复现 EGO-Planner 官方场景，只要求是 EGO-like static obstacle scene。

## 7. Bridge I/O contract

- State bridge：PyBullet drone state -> ROS odometry。至少包含 position、velocity、orientation、timestamp、frame id。
- Obstacle bridge：PyBullet obstacle primitives -> synthetic pointcloud。第一版优先走 pointcloud，不做 depth image。
- Goal bridge：PyBullet goal -> EGO planning target。第一版只支持单目标点。
- Command bridge：EGO trajectory / position command -> desired_velocity -> gym-pybullet-drones action。

第一版 tracker 可采用：

```text
desired_velocity = kp * (next_waypoint - current_position)
desired_velocity = clip(desired_velocity, max_speed)
```

## 8. Diagnostic JSONL 要求

每条记录至少包含：task_id、output_type、platform_id、external_planner、ego_planner_commit、scenario_id、seed、step、position、goal、desired_velocity、min_clearance、bridge_status。

输出文件必须小型、可审查，不得提交大型 rollout dump。

## 9. 验收标准

任务完成必须满足：

1. EGO-Planner 官方仓库 clone 路线和 commit 已记录。
2. EGO-Planner build/run 路线已记录。
3. `ego_like_static_v0` 能启动或有明确阻塞说明。
4. bridge I/O contract 已写清楚。
5. 至少完成真实 ROS bridge smoke test，或在环境不支持 ROS 时完成 mock bridge 并记录真实 bridge 阻塞原因。
6. 能生成小型 diagnostic JSONL。
7. 完成报告明确说明是否建议后续发展 official EGO baseline。
8. 如果不建议继续 official bridge，必须给出 EGO-style Python baseline 回退方案。

## 10. 完成报告必须包含

- 修改文件列表
- 运行命令
- 测试结果
- 外部依赖和版本
- EGO-Planner commit
- 生成产物路径
- 当前限制
- 是否建议继续 official EGO sidecar
- 是否需要回退 EGO-style Python baseline
- 下一步人工决策点

## 11. 输出性质

本任务全部输出均为 `diagnostic`，不得标注为 `paper-candidate`。
