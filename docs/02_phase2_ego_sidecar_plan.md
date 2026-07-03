# 第二阶段计划：EGO-Planner 官方侧车桥接与 EGO-like PyBullet 简单场景

## 1. 阶段定位

第二阶段不是论文结果阶段，也不是正式 baseline 对比阶段。

第二阶段是一个工程可行性验证阶段，目标是回答：

1. 官方 EGO-Planner 是否能作为外部 ROS sidecar 接入 gym-pybullet-drones / PyBullet？
2. 是否能在一个 EGO-like 静态障碍简单场景中完成最小闭环飞行诊断？
3. 这个 bridge 后续是否值得发展成 official EGO baseline？
4. 如果 bridge 成本过高，是否应回退到 EGO-style Python baseline？

## 2. 外部项目角色

### 2.1 gym-pybullet-drones

主轻量平台，用于 PyBullet 四旋翼仿真、任务包装、状态读取和 action 执行。

### 2.2 EGO-Planner

第二阶段的 official sidecar bridge 对象。

EGO-Planner 不直接写入 PIRL-NavRL 主源码，不修改其核心 planner 算法，不声称复现其论文结果。

### 2.3 NavRL

NavRL 不作为 baseline。

NavRL 仅作为长期参考架构，用于参考：

- 训练链路
- simulator-to-policy 接口
- perception / safety / navigation 模块划分
- deployment / ROS / Isaac Sim 路线
- 参数组织方式
- 实验管理方式

NavRL 不进入第二阶段执行任务，不训练，不迁移为 PyBullet baseline。

## 3. 总体架构

```text
gym-pybullet-drones / PyBullet
        |
        | drone state / obstacles / goal
        v
PIRL-NavRL bridge layer
        |
        | ROS odometry / pointcloud / planning target
        v
official EGO-Planner ROS sidecar
        |
        | trajectory / position command
        v
tracker / command adapter
        |
        | desired_velocity / platform action
        v
gym-pybullet-drones / PyBullet
```

第二阶段的重点不是 planner 内部实现，而是 state、obstacle、goal、command 四类接口是否能形成闭环。

## 4. EGO-like PyBullet 简单场景 v0

第一版场景只用于 bridge smoke test。

建议定义：

```text
scenario_id: ego_like_static_v0
space: 10m x 10m x 3m
start: [-4.0, 0.0, 1.0]
goal: [4.0, 0.0, 1.0]
obstacles: static cylinders or spheres
seed: fixed first, random later
max_episode_steps: short diagnostic horizon
```

第一版不做：

- 动态障碍
- 语义标签
- RGB / depth 视觉
- 真实传感器仿真
- 多场景评估
- 多 seed 统计

如果使用 PyBullet primitive obstacle，需要在 bridge 层转换为 EGO 可消费的 synthetic pointcloud 或后续可扩展的 map representation。

## 5. Bridge I/O contract

### 5.1 State bridge

```text
PyBullet drone state -> ROS odometry
```

至少包含：

- position
- velocity
- orientation
- timestamp
- frame id

### 5.2 Obstacle bridge

```text
PyBullet obstacle primitives -> synthetic pointcloud
```

第一版优先使用 pointcloud，不做 depth image。

### 5.3 Goal bridge

```text
PyBullet goal -> EGO planning target
```

第一版只支持单目标点。

### 5.4 Command bridge

```text
EGO trajectory / position command -> desired_velocity -> gym-pybullet-drones action
```

第一版 tracker 可采用：

```text
desired_velocity = kp * (next_waypoint - current_position)
desired_velocity = clip(desired_velocity, max_speed)
```

## 6. 推荐目录

第二阶段开始实现时，允许在任务需要范围内创建源码、脚本、配置和测试。

推荐最小结构：

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

如果实现环境暂时不支持 ROS，则可以先完成 mock bridge，但必须记录阻塞原因。

## 7. 诊断日志

第二阶段只生成小型 diagnostic JSONL。

每条记录至少包含：

```json
{
  "task_id": "TASK_02",
  "output_type": "diagnostic",
  "platform_id": "gym_pybullet_drones",
  "external_planner": "ego_planner_official_sidecar",
  "ego_planner_commit": "<commit>",
  "scenario_id": "ego_like_static_v0",
  "seed": 0,
  "step": 0,
  "position": [0.0, 0.0, 1.0],
  "goal": [4.0, 0.0, 1.0],
  "desired_velocity": [0.0, 0.0, 0.0],
  "min_clearance": null,
  "bridge_status": "ok"
}
```

## 8. 明确禁止项

第二阶段禁止：

- 正式 baseline 论文对比
- PIRL-NavRL 主方法训练
- 多 seed 论文级统计
- 动态障碍正式评估
- 语义分割
- NavRL baseline
- NavRL 训练栈
- Isaac Sim 训练
- 把 EGO-Planner 官方 C++ 核心代码复制进主源码
- 修改 EGO-Planner 核心 planner 算法
- 提交 checkpoint、视频、GIF、TensorBoard、wandb 或大型 rollout
- 声称 EGO-Planner 论文结果复现

## 9. 验收标准

第二阶段完成时必须提交完成报告，至少说明：

1. EGO-Planner 官方仓库是否已本地 clone，并记录 commit。
2. 官方 build / run 路线是否记录完整。
3. `ego_like_static_v0` 是否能启动。
4. bridge I/O contract 是否写清楚。
5. 真实 ROS bridge 是否跑通；如果未跑通，mock bridge 是否完成，并记录阻塞原因。
6. 是否能生成小型 diagnostic JSONL。
7. 是否观察到基本目标推进和静态避障趋势。
8. 是否建议后续发展成 official EGO baseline。
9. 如果不建议，是否给出 EGO-style Python baseline 回退方案。

## 10. 阶段结束后的决策

| 结果 | 后续路线 |
|---|---|
| bridge 跑通且稳定 | 后续保留 official EGO sidecar baseline |
| bridge 能跑但脆弱 | 只作为诊断或附录候选 |
| bridge 成本过高 | 回退到 EGO-style Python baseline |
| 场景复刻困难 | 先固定自己的 local navigation protocol |
| command 转换困难 | 增加 tracker 或降低 official baseline 优先级 |
