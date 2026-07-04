# NavRL 参考范围

## 1. 定位

NavRL 是 PIRL-NavRL 的重要工程与算法实现参考源，不是 baseline。

本项目可以仔细阅读 NavRL 的详细代码，参考其模块划分、方法设计、参数组织、训练流程、动态导航实现、日志评估和部署边界。目标是把有价值的设计经验适配进 PIRL-NavRL 自己的 gym-pybullet-drones 主线，而不是把 NavRL 整包迁移成本项目实现，也不是在当前阶段训练、复现或比较 NavRL。

## 2. 可以参考的内容

NavRL 可以用于参考：

- 训练链路组织：simulator、environment、policy、rollout、training script、evaluation、checkpoint、deployment。
- simulator-to-policy 接口：观察量、动作、控制层级、状态管理和 rollout 管理。
- 模块拆分：perception、safety、navigation、policy、deployment 等模块边界。
- 部署路径：Isaac Sim、ROS1、ROS2、虚拟环境和真实机器人部署组织方式。
- 动态导航场景设计：静态障碍、动态障碍、规模化并行训练和评估思路。
- 参数组织：训练参数、环境参数、安全参数、部署参数的结构化管理方式。
- 实验记录：运行配置、seed、平台、指标来源和产物管理方式。
- 可视化与 debug workflow：轨迹、障碍物、状态量、控制量和评估摘要的组织方式。
- 具体模块方法：policy wrapper、runner、reward helper、observation adapter、deployment adapter 等实现思路。

## 3. 代码借鉴与复制边界

允许：

- 仔细检查 NavRL 代码并总结设计模式。
- 复制小段通用 helper、schema、adapter pattern、参数组织方式或无项目强绑定的工具函数。
- 对复制内容进行重命名、改写、类型适配、平台适配和测试适配。
- 参考 NavRL 的参数范围作为工程初值，但不要把这些初值包装成论文结论。
- 在必要位置补充 attribution / license note。
- 在 `docs/` 中记录哪些设计参考了 NavRL。
- TASK_03 可以用 NavRL 的 runner、policy interface、rollout recorder、
  visualization 和 deployment boundary 作为设计参考，但落地实现必须保持
  PIRL-NavRL 自己的模块、命名、测试和许可证边界。

禁止：

- 将 NavRL 作为 baseline。
- 将 NavRL 整包迁移为 PyBullet baseline。
- 训练 NavRL。
- 复现 NavRL 论文结果。
- 把 NavRL 结果放进 PIRL-NavRL baseline matrix。
- 未经适配和测试直接把 NavRL 代码复制进 `pirl_navrl/` 主源码。
- 复制来源不明、许可证不清楚或 attribution 不明确的代码。
- 将当前项目主平台切换到 NavRL / Isaac Sim。

## 4. 与 EGO-Planner 的区别

EGO-Planner 是传统局部规划强 baseline 候选，TASK_02 已冻结为 official Docker/ROS sidecar diagnostic 与 baseline-readiness spike。

NavRL 与 EGO-Planner 的角色不同：

| 项目 | 当前角色 | 是否 baseline | 当前是否执行迁移 |
|---|---|---|---|
| gym-pybullet-drones | 主平台候选 | 否 | 是，作为训练/验证底座 |
| EGO-Planner | official sidecar diagnostic / future baseline candidate | 候选 | TASK_02 已验证 sidecar diagnostic，暂时冻结 |
| NavRL | 详细工程与算法实现参考源 | 否 | 否，不整包迁移；允许阅读、借鉴和适配小段实现 |

## 5. 后续可能转化为项目设计的内容

NavRL 中值得转化为 PIRL-NavRL 自己结构的内容包括：

- `PlatformAdapter`：隔离不同仿真/部署平台。
- `ObservationAdapter`：把平台状态转为方法输入。
- `PolicyInterface`：统一策略输入输出。
- `SafetyModule` / `ShieldModule`：把风险评估和动作修正独立出来。
- `RolloutRecorder`：统一记录平台、seed、策略、指标和诊断信息。
- `VisualizationAdapter`：统一显示场景、轨迹、障碍物和控制量。
- `DeploymentProfile`：为未来 ROS / Isaac / real-world 路线预留配置边界。

这些内容应作为 PIRL-NavRL 自己的抽象设计。允许参考和适配代码，但必须改写到本项目语义、补测试、处理 attribution / license，不得直接整包迁移。

## 6. 写作边界

论文和报告中可以说：

```text
NavRL is used as a detailed engineering and implementation reference for UAV navigation pipeline organization, dynamic navigation modules, and deployment-oriented system design.
```

不能说：

```text
We compare against NavRL.
```

除非未来另开任务，使用官方 NavRL 代码、官方配置或明确 transfer protocol 进行独立实验。当前计划中不做该事项。
