# NavRL 参考范围

## 1. 定位

NavRL 是 PIRL-NavRL 的长期参考架构，不是 baseline。

本项目参考 NavRL 的目标是理解成熟 UAV safe navigation 项目的工程链路、模块拆分、训练组织和部署路径，而不是把 NavRL 迁移成 PyBullet baseline，也不是在当前阶段训练或复现 NavRL。

## 2. 可以参考的内容

NavRL 可以用于参考：

- 训练链路组织：simulator、environment、policy、rollout、training script、evaluation、checkpoint、deployment。
- simulator-to-policy 接口：观察量、动作、控制层级、状态管理和 rollout 管理。
- 模块拆分：perception、safety、navigation、policy、deployment 等模块边界。
- 部署路径：Isaac Sim、ROS1、ROS2、虚拟环境和真实机器人部署组织方式。
- 动态导航场景设计：静态障碍、动态障碍、规模化并行训练和评估思路。
- 参数组织：训练参数、环境参数、安全参数、部署参数的结构化管理方式。
- 实验记录：运行配置、seed、平台、指标来源和产物管理方式。

## 3. 禁止使用方式

当前阶段禁止：

- 将 NavRL 作为 baseline。
- 将 NavRL 迁移为 PyBullet baseline。
- 训练 NavRL。
- 复现 NavRL 论文结果。
- 把 NavRL 结果放进 PIRL-NavRL baseline matrix。
- 把 NavRL 官方代码复制进 `pirl_navrl/` 主源码。
- 将当前项目主平台切换到 NavRL / Isaac Sim。

## 4. 与 EGO-Planner 的区别

EGO-Planner 是传统局部规划强 baseline 候选，第二阶段可以作为 official ROS sidecar bridge spike 进行可行性验证。

NavRL 与 EGO-Planner 的角色不同：

| 项目 | 当前角色 | 是否 baseline | 当前是否执行迁移 |
|---|---|---|---|
| gym-pybullet-drones | 早期主平台 | 否 | 是，作为训练/验证底座 |
| EGO-Planner | official sidecar bridge 可行性验证对象 | 候选 | 第二阶段验证 bridge |
| NavRL | 长期参考架构 | 否 | 否，只参考链路和结构 |

## 5. 后续可能转化为项目设计的内容

NavRL 中值得转化为 PIRL-NavRL 自己结构的内容包括：

- `PlatformAdapter`：隔离不同仿真/部署平台。
- `ObservationAdapter`：把平台状态转为方法输入。
- `PolicyInterface`：统一策略输入输出。
- `SafetyModule` / `ShieldModule`：把风险评估和动作修正独立出来。
- `RolloutRecorder`：统一记录平台、seed、策略、指标和诊断信息。
- `DeploymentProfile`：为未来 ROS / Isaac / real-world 路线预留配置边界。

这些内容应作为 PIRL-NavRL 自己的抽象设计，不直接复制 NavRL 代码。

## 6. 写作边界

论文和报告中可以说：

```text
NavRL is used as a reference for UAV navigation pipeline organization and deployment-oriented system design.
```

不能说：

```text
We compare against NavRL.
```

除非未来另开任务，使用官方 NavRL 代码、官方配置或明确 transfer protocol 进行独立实验。当前计划中不做该事项。
