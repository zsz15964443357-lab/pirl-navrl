# 第三方项目说明

本仓库会引用若干外部开源项目。默认不直接 vendor 它们的代码。

## gym-pybullet-drones

- 仓库：<https://github.com/learnsyslab/gym-pybullet-drones>
- 角色：第一阶段和早期方法验证的轻量级无人机 PyBullet 底座
- 说明：兼容 Gymnasium 和 Stable-Baselines3 的四旋翼仿真平台
- 当前使用方式：本地 clone 到 `external/gym-pybullet-drones/`，不提交其源码

## EGO-Planner

- 仓库：<https://github.com/ZJU-FAST-Lab/ego-planner>
- 角色：第二阶段 official ROS sidecar bridge 可行性验证对象
- 说明：传统局部规划强 baseline 候选，但官方项目是 ROS / catkin / C++ 工程，不是 Gymnasium policy
- 当前使用方式：本地 clone 到 `external/ego-planner/`，不提交其源码，不修改其核心 planner 算法
- 当前状态：只做 diagnostic bridge spike；是否发展为 official EGO baseline 取决于第二阶段结论

## NavRL

- 仓库：<https://github.com/Zhefan-Xu/NavRL>
- 角色：长期参考架构
- 参考内容：训练链路、代码结构、模块拆分、部署路径、动态导航设计、参数组织和实验记录方式
- 当前使用方式：本地 clone 到 `external/NavRL/`，不提交其源码
- 明确不作为：baseline、PyBullet baseline 迁移目标、当前训练依赖、论文主实验对比对象

## Stable-Baselines3

- 仓库：<https://github.com/DLR-RM/stable-baselines3>
- 角色：gym-pybullet-drones 示例中使用的强化学习训练基线/接口

## PyBullet / Bullet

- 仓库：<https://github.com/bulletphysics/bullet3>
- 角色：gym-pybullet-drones 的物理后端

## 旧仓库

旧 `pirl-nav-research` 不是第三方依赖，也不是本仓库的有效代码来源。