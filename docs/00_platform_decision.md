# 平台决策

## 总结

PIRL-NavRL 当前采用分阶段平台路线：

1. **gym-pybullet-drones** 是第一阶段和早期方法验证的主轻量平台。
2. **EGO-Planner** 后续用于官方侧车桥接可行性验证，目标是判断它是否可以发展为 official EGO baseline。
3. **NavRL** 只作为长期参考架构，不作为 baseline，不进入对比表，不迁移为 PyBullet baseline。
4. Safety-Gymnasium / OmniSafe 作为 SafeRL benchmark 和算法组织参考，不作为当前 UAV 主平台。

## 为什么不直接用裸 PyBullet

裸 PyBullet 是物理引擎，不是完整的无人机强化学习研究平台。

如果直接从裸 PyBullet 开始，我们需要自己补齐：环境接口、任务定义、训练接入、日志、评估和图表。这会重新走回“自研平台”的路线。

## 为什么选择 gym-pybullet-drones

选择它的原因：

- 已有 PyBullet 四旋翼仿真
- 兼容 Gymnasium
- 兼容 Stable-Baselines3
- 有内置 PID 和 RL 示例
- 比 Isaac Sim 轻
- 后续可以作为迁移到更重平台前的轻量物理验证平台

## EGO-Planner 的位置

EGO-Planner 是传统局部规划强 baseline 候选，但官方项目本身是 ROS / catkin / C++ 工程，不是 Gymnasium/Python policy。

因此当前不把 EGO-Planner 直接重写进主方法代码，而是采用两步策略：

1. 第二阶段先做 official EGO-Planner ROS sidecar bridge spike，在 EGO-like PyBullet 简单场景中验证是否能跑通 state / obstacle / goal / command 闭环。
2. 如果桥接稳定，后续再决定是否把它作为 official EGO baseline；如果桥接成本过高，则回退到 EGO-style Python baseline。

第二阶段输出只允许标注为 diagnostic，不允许声称 EGO-Planner 论文结果复现。

## NavRL 的位置

NavRL 更接近长期目标，但它不是本项目 baseline。

NavRL 用于参考：

- 训练链路组织
- simulator-to-policy 接口
- perception / safety / navigation 模块拆分
- deployment / ROS / Isaac Sim 路径
- 动态导航场景设计
- 参数组织和实验记录方式

NavRL 不用于：

- baseline 对比
- PyBullet baseline 迁移
- 当前阶段训练依赖
- 论文主实验对比表
- 当前阶段 Isaac Sim / ROS 部署

## Safety-Gymnasium / OmniSafe 的位置

Safety-Gymnasium 和 OmniSafe 仍然是重要的 SafeRL benchmark 参考，但第一阶段和第二阶段优先考虑 UAV 物理相关性，因此选择 gym-pybullet-drones 与 EGO-Planner sidecar 路线。

## 第一阶段范围

第一阶段只做：

- 外部仓库 setup
- 本地环境配置
- import 检查
- 内置示例检查
- 一个围绕 gym-pybullet-drones 的简单 PIRL-NavRL adapter / risk / shield 演示

第一阶段不做论文结果。

## 第二阶段范围

第二阶段只做：

- EGO-Planner 官方 sidecar 可行性验证
- EGO-like 静态障碍 PyBullet 简单场景
- bridge I/O contract
- 最小 smoke test
- 小型 diagnostic JSONL
- 后续是否保留 official EGO bridge 的决策报告

第二阶段不做正式 baseline 对比，也不做 PIRL-NavRL 主方法。